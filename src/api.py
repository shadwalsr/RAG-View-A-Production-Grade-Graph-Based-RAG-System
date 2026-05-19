import os

from dotenv import load_dotenv

load_dotenv(override=True)
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Path,
    Query,
    Request,
    Security,
    status,
)
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.database import db
from src.graph_updater import GraphUpdateState, graph_updater
from src.qa import graph_rag_generator
from src.retriever import retriever
from src.scorer import ConfidenceReport, confidence_scorer
from src.verifier import graph_citation_verifier

logger = logging.getLogger(__name__)

# --- Pydantic Schemas for OpenAPI Spec ---.

class AskRequest(BaseModel):
    query: str = Field(..., json_schema_extra={"examples": ["What company did Shadwal Singh found that focuses on AI education?"]})

class AskResponse(BaseModel):
    query: str = Field(..., description="The original user query")
    answer: str = Field(..., description="The verified, graph-grounded answer")
    confidence_report: ConfidenceReport = Field(..., description="Structured confidence metrics including graph_coverage")
    relationships: List[str] = Field(default=[], description="List of graph relationships retrieved for the query")

class IngestRequest(BaseModel):
    text: str = Field(..., json_schema_extra={"examples": ["WhySchool is an educational startup founded in 2024 by Shadwal Singh."]})
    source_name: str = Field(default="api_upload", json_schema_extra={"examples": ["whyschool_press_release"]})

class IngestResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"examples": ["queued"]})
    job_id: str = Field(..., json_schema_extra={"examples": ["job_123456"]})
    message: str = Field(..., json_schema_extra={"examples": ["Document ingestion queued successfully."]})

class JobStatusResponse(BaseModel):
    job_id: str = Field(..., json_schema_extra={"examples": ["job_123456"]})
    status: str = Field(..., json_schema_extra={"examples": ["completed"]}, description="Current status: queued, processing, completed, or failed")
    source_name: str = Field(..., json_schema_extra={"examples": ["whyschool_press_release"]})
    created_at: str = Field(..., json_schema_extra={"examples": ["2026-05-17T12:00:00Z"]})
    completed_at: Optional[str] = Field(default=None, json_schema_extra={"examples": ["2026-05-17T12:01:00Z"]})
    state: Optional[GraphUpdateState] = Field(default=None, description="Graph state after successful completion")
    error: Optional[str] = Field(default=None, description="Error message if failed")

class EntityRelationship(BaseModel):
    predicate: str = Field(..., json_schema_extra={"examples": ["FOUNDED_IN"]})
    target: Optional[str] = Field(default=None, json_schema_extra={"examples": ["2024"]})
    source: Optional[str] = Field(default=None, json_schema_extra={"examples": ["WhySchool"]})
    weight: float = Field(default=1.0, json_schema_extra={"examples": [1.5]})

class EntityInspectResponse(BaseModel):
    name: str = Field(..., json_schema_extra={"examples": ["WhySchool"]})
    type: str = Field(..., json_schema_extra={"examples": ["ORG"]})
    description: str = Field(..., json_schema_extra={"examples": ["Educational startup focused on AI"]})
    aliases: List[str] = Field(default=[], json_schema_extra={"examples": [["WhySchool Academy"]]})
    source_chunk_ids: List[str] = Field(default=[], json_schema_extra={"examples": [["chunk_123"]]})
    outgoing_relationships: List[EntityRelationship] = Field(default=[])
    incoming_relationships: List[EntityRelationship] = Field(default=[])

class ShortestPathResponse(BaseModel):
    from_entity: str = Field(..., json_schema_extra={"examples": ["Shadwal Singh"]})
    to_entity: str = Field(..., json_schema_extra={"examples": ["AI Education"]})
    path_found: bool = Field(..., json_schema_extra={"examples": [True]})
    path_nodes: List[str] = Field(default=[], json_schema_extra={"examples": [["Shadwal Singh", "WhySchool", "AI Education"]]})
    path_relationships: List[str] = Field(default=[], json_schema_extra={"examples": [["FOUNDED", "FOCUSES_ON"]]})

# --- FastAPI App Initialization ---.

# --- Security & API Key Auth ---.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
EXPECTED_API_KEY = os.getenv("API_KEY", "YOUR_API_KEY_HERE")  # Set via .env; do not hardcode secrets

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != EXPECTED_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key

# --- Redis Caching Setup ---.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client: Optional[redis.Redis] = None
fallback_cache: Dict[str, Any] = {}
fallback_entity_to_queries: Dict[str, set] = {}


# --- Rate Limiting Setup ---.
limiter_storage = REDIS_URL if not os.getenv("DRY_RUN") else "memory://"
limiter = Limiter(key_func=get_remote_address, storage_uri=limiter_storage)

try:
    if not os.getenv("DRY_RUN"):
        redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        redis_client.ping()
        logger.info("Connected to Redis for query caching.")
    else:
        logger.info("DRY_RUN enabled: Using in-memory fallback cache instead of Redis.")
except Exception as e:
    logger.warning(f"Redis connection failed ({e}). Falling back to in-memory cache.")
    redis_client = None

def get_cached_query(query: str) -> Optional[Dict[str, Any]]:
    cache_key = f"cache:query:{query.strip().lower()}"
    if redis_client:
        try:
            data = redis_client.get(cache_key)
            if data:
                logger.info(f"Cache hit from Redis for query: '{query}'")
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
    else:
        if cache_key in fallback_cache:
            logger.info(f"Cache hit from fallback cache for query: '{query}'")
            return fallback_cache[cache_key]
    return None

def set_cached_query(query: str, response_data: Dict[str, Any]):
    cache_key = f"cache:query:{query.strip().lower()}"
    # 1 hour = 3600 seconds.
    if redis_client:
        try:
            redis_client.setex(cache_key, 3600, json.dumps(response_data))
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
    else:
        fallback_cache[cache_key] = response_data

    # Extract entity names from query
    entity_names = set()
    try:
        from src.query_linker import query_linker
        for ent in query_linker.extract_entities(query):
            entity_names.add(ent.strip().lower())
    except Exception as e:
        logger.warning(f"Error extracting entities from query for caching: {e}")

    # Extract entity names from returned relationships
    for rel_str in response_data.get("relationships", []):
        try:
            if " --[" in rel_str and "]--> " in rel_str:
                parts = rel_str.split(" --[")
                ent1 = parts[0].strip().lower()
                ent2 = parts[1].split("]--> ")[1].strip().lower()
                entity_names.add(ent1)
                entity_names.add(ent2)
        except Exception as e:
            logger.warning(f"Error extracting entities from relationship string '{rel_str}': {e}")

    # Map the cache_key to entities
    for entity_name in entity_names:
        if redis_client:
            try:
                redis_key = f"cache:entity_to_queries:{entity_name}"
                redis_client.sadd(redis_key, cache_key)
                redis_client.expire(redis_key, 86400)
            except Exception as e:
                logger.warning(f"Redis sadd/expire error for entity '{entity_name}': {e}")
        else:
            if entity_name not in fallback_entity_to_queries:
                fallback_entity_to_queries[entity_name] = set()
            fallback_entity_to_queries[entity_name].add(cache_key)


app = FastAPI(
    title="RAG-View Graph Intelligence API",
    version="0.1.0",
    description="Production-grade FastAPI service providing advanced GraphRAG generation, incremental ingestion, and direct knowledge graph inspection endpoints.",
    openapi_tags=[
        {"name": "Generation", "description": "Graph-grounded QA generation and confidence scoring"},
        {"name": "Ingestion", "description": "Incremental document ingestion and graph weight maintenance"},
        {"name": "Knowledge Graph", "description": "Direct graph inspection and shortest path traversal"}
    ],
    dependencies=[Security(get_api_key)]
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---.

@app.post("/v1/ask", response_model=AskResponse, tags=["Generation"], summary="Graph-Grounded QA Generation")
@limiter.limit("10/minute")
def ask_endpoint(request: Request, payload: AskRequest):
    """
    Executes the full GraphRAG generation pipeline:
    1. Orchestrates parallel hybrid retrieval (Vector + BM25 + Graph Traversal) via RRF.
    2. Generates a grounded answer using the structured three-section prompt.
    3. Verifies claims against direct Neo4j node properties, appending [N ⚠️ UNVERIFIED] if unsupported.
    4. Calculates multi-dimensional confidence scores including the graph_coverage metric.
    """
    logger.info(f"API /v1/ask received query: '{payload.query}'")
    try:
        # 0.
        cached_result = get_cached_query(payload.query)
        if cached_result:
            return AskResponse(**cached_result)

        # 1.
        fused_context = retriever.retrieve(payload.query)
        
        # 1b.
        from src.graph_retriever import graph_retriever
        from src.query_linker import query_linker
        query_entities = query_linker.extract_entities(payload.query)
        graph_data = graph_retriever.traverse(query_entities)
        rels = graph_data.get("relationships", [])
        
        # 2.
        raw_answer = graph_rag_generator.generate_answer(payload.query, fused_context)
        
        # 3.
        verified_answer = graph_citation_verifier.verify(payload.query, raw_answer, fused_context)
        
        # 4.
        report = confidence_scorer.score(payload.query, verified_answer, fused_context)
        
        response_data = {
            "query": payload.query,
            "answer": verified_answer,
            "confidence_report": report.model_dump(),
            "relationships": rels
        }
        
        # Cache the result.
        set_cached_query(payload.query, response_data)
        
        return AskResponse(**response_data)
    except Exception as e:
        logger.error(f"API /v1/ask failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation pipeline failed: {e}")

@app.post("/v1/ask/stream", tags=["Generation"], summary="Graph-Grounded QA Streaming Generation")
@limiter.limit("10/minute")
def ask_stream_endpoint(request: Request, payload: AskRequest):
    """
    Executes the full GraphRAG generation pipeline and streams the generated tokens.
    1. Checks Redis query cache before streaming.
    2. Orchestrates parallel hybrid retrieval (Vector + BM25 + Graph Traversal) via RRF.
    3. Streams the answer token by token.
    4. Post-verifies the accumulated response.
    5. Calculates confidence metrics and yields the final metadata block.
    """
    logger.info(f"API /v1/ask/stream received query: '{payload.query}'")
    
    # 0. Check cache first
    cached_result = get_cached_query(payload.query)
    if cached_result:
        logger.info(f"Stream cache hit for query: '{payload.query}'")
        answer = cached_result.get("answer", "")
        report = cached_result.get("confidence_report", {})
        rels = cached_result.get("relationships", [])
        
        def stream_cached():
            try:
                words = answer.split(" ")
                for i, word in enumerate(words):
                    token = word + (" " if i < len(words) - 1 else "")
                    chunk = {"type": "token", "content": token}
                    yield f"data: {json.dumps(chunk)}\n\n"
                    import time
                    time.sleep(0.01)
                
                metadata_chunk = {
                    "type": "metadata",
                    "verified_answer": answer,
                    "confidence_score": report.get("retrieval_confidence", 0.0),
                    "grounding_confidence": report.get("grounding_confidence", 0.0),
                    "graph_coverage": report.get("graph_coverage", 0.0),
                    "relationships": rels
                }
                yield f"data: {json.dumps(metadata_chunk)}\n\n"
            except Exception as e:
                logger.error(f"Error during cached stream: {e}")
                
        return StreamingResponse(stream_cached(), media_type="text/event-stream")

    # 1. Missed cache. Retrieve resources.
    try:
        fused_context = retriever.retrieve(payload.query)
        
        from src.graph_retriever import graph_retriever
        from src.query_linker import query_linker
        query_entities = query_linker.extract_entities(payload.query)
        graph_data = graph_retriever.traverse(query_entities)
        rels = graph_data.get("relationships", [])
    except Exception as e:
        logger.error(f"Retrieval failed before streaming: {e}")
        # Yield the error block immediately
        def stream_error():
            err_chunk = {"type": "token", "content": f"❌ Retrieval pipeline failed: {str(e)}"}
            yield f"data: {json.dumps(err_chunk)}\n\n"
        return StreamingResponse(stream_error(), media_type="text/event-stream")

    def stream_generation():
        accumulated_answer = ""
        try:
            # 2. Generate answer stream
            for token in graph_rag_generator.generate_answer_stream(payload.query, fused_context):
                accumulated_answer += token
                chunk = {"type": "token", "content": token}
                yield f"data: {json.dumps(chunk)}\n\n"
            
            # 3. Post-verification
            verified_answer = graph_citation_verifier.verify(payload.query, accumulated_answer, fused_context)
            
            # 4. Confidence scoring
            report = confidence_scorer.score(payload.query, verified_answer, fused_context)
            
            response_data = {
                "query": payload.query,
                "answer": verified_answer,
                "confidence_report": report.model_dump(),
                "relationships": rels
            }
            
            # Cache the result.
            set_cached_query(payload.query, response_data)
            
            # Send the final metadata block
            metadata_chunk = {
                "type": "metadata",
                "verified_answer": verified_answer,
                "confidence_score": report.retrieval_confidence,
                "grounding_confidence": report.grounding_confidence,
                "graph_coverage": report.graph_coverage,
                "relationships": rels
            }
            yield f"data: {json.dumps(metadata_chunk)}\n\n"
            
        except Exception as e:
            logger.error(f"Error during stream generation: {e}")
            err_chunk = {"type": "token", "content": f"\n❌ Generation failed: {str(e)}"}
            yield f"data: {json.dumps(err_chunk)}\n\n"

    return StreamingResponse(stream_generation(), media_type="text/event-stream")

# --- Redis-Backed Job Queue Storage ---
# Implements Redis persistence with seamless in-memory fallback.
class RedisJobsStore:
    def __init__(self):
        self._fallback = {}

    def _get_key(self, job_id: str) -> str:
        return f"rag_view:job:{job_id}"

    def __contains__(self, job_id: str) -> bool:
        if redis_client:
            try:
                return redis_client.exists(self._get_key(job_id)) > 0
            except Exception as e:
                logger.warning(f"Redis jobs exists error: {e}")
        return job_id in self._fallback

    def __getitem__(self, job_id: str) -> Dict[str, Any]:
        if redis_client:
            try:
                data = redis_client.get(self._get_key(job_id))
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis jobs get error: {e}")
        if job_id in self._fallback:
            return self._fallback[job_id]
        raise KeyError(f"Job {job_id} not found.")

    def __setitem__(self, job_id: str, value: Dict[str, Any]):
        val_copy = dict(value)
        if val_copy.get("state") and hasattr(val_copy["state"], "model_dump"):
            val_copy["state"] = val_copy["state"].model_dump()
        
        if redis_client:
            try:
                # Store with 7 days TTL (604800 seconds) so old jobs are automatically pruned
                redis_client.setex(self._get_key(job_id), 604800, json.dumps(val_copy))
                return
            except Exception as e:
                logger.warning(f"Redis jobs set error: {e}")
        self._fallback[job_id] = val_copy

    def get(self, job_id: str, default=None):
        try:
            return self[job_id]
        except KeyError:
            return default

jobs_store = RedisJobsStore()

def purge_query_cache(job_id: str, entities: Optional[List[str]] = None):
    global fallback_cache, fallback_entity_to_queries
    logger.info(f"Job {job_id}: Purging query cache with entities={entities}")
    
    if entities:
        # Granular invalidation
        for ent in entities:
            ent_norm = ent.strip().lower()
            if redis_client:
                try:
                    redis_ent_key = f"cache:entity_to_queries:{ent_norm}"
                    # Retrieve all query cache keys mapped to this entity
                    query_keys = redis_client.smembers(redis_ent_key)
                    if query_keys:
                        # Delete query keys from Redis
                        redis_client.delete(*query_keys)
                        logger.info(f"Deleted {len(query_keys)} query keys for entity '{ent_norm}' from Redis.")
                    # Delete the entity-to-query set itself
                    redis_client.delete(redis_ent_key)
                except Exception as e:
                    logger.warning(f"Failed to purge Redis cache for entity '{ent_norm}': {e}")
            else:
                if ent_norm in fallback_entity_to_queries:
                    query_keys = fallback_entity_to_queries[ent_norm]
                    for qk in query_keys:
                        if qk in fallback_cache:
                            del fallback_cache[qk]
                    del fallback_entity_to_queries[ent_norm]
                    logger.info(f"Deleted {len(query_keys)} query keys for entity '{ent_norm}' from fallback cache.")
    else:
        # Full purge
        fallback_cache.clear()
        fallback_entity_to_queries.clear()
        if redis_client:
            try:
                # Delete all cache:query:* keys
                keys_to_delete = []
                for key in redis_client.scan_iter(match="cache:query:*"):
                    keys_to_delete.append(key)
                for key in redis_client.scan_iter(match="cache:entity_to_queries:*"):
                    keys_to_delete.append(key)
                
                if keys_to_delete:
                    redis_client.delete(*keys_to_delete)
                    logger.info(f"Successfully deleted {len(keys_to_delete)} cached keys from Redis.")
                else:
                    logger.info("No cached keys found in Redis to purge.")
            except Exception as e:
                logger.warning(f"Failed to purge Redis query cache: {e}")


def process_ingestion_job(job_id: str, text: str, source_name: str):
    logger.info(f"Job {job_id}: Starting background ingestion for source '{source_name}'")
    
    job_data = jobs_store[job_id]
    job_data["status"] = "processing"
    jobs_store[job_id] = job_data
    
    try:
        state = graph_updater.ingest_document(text, source_name)
        
        job_data = jobs_store[job_id]
        job_data["status"] = "completed"
        job_data["state"] = state
        job_data["completed_at"] = datetime.utcnow().isoformat() + "Z"
        jobs_store[job_id] = job_data
        
        logger.info(f"Job {job_id}: Successfully completed ingestion for '{source_name}'")
        
        # Purge Redis query cache after successful ingestion!
        purge_query_cache(job_id, entities=state.extracted_entities)
        
    except Exception as e:
        logger.error(f"Job {job_id}: Ingestion failed with error: {e}")
        
        job_data = jobs_store[job_id]
        job_data["status"] = "failed"
        job_data["error"] = str(e)
        job_data["completed_at"] = datetime.utcnow().isoformat() + "Z"
        jobs_store[job_id] = job_data

@app.post("/v1/ingest", response_model=IngestResponse, tags=["Ingestion"], summary="Incremental Document Ingestion (Async)")
@limiter.limit("5/minute")
def ingest_endpoint(request: Request, payload: IngestRequest, background_tasks: BackgroundTasks):
    """
    Orchestrates the incremental graph update pipeline asynchronously:
    1. Generates a unique job_id and queues the document ingestion task.
    2. Returns the job_id immediately to the client.
    3. Background worker chunks raw text, extracts entities/relationships, upserts to Neo4j/ChromaDB, and updates graph weights.
    4. Check status via GET /v1/jobs/{job_id}.
    """
    logger.info(f"API /v1/ingest received document from source: '{payload.source_name}', queuing job.")
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now = datetime(2026, 5, 17, 12, 0, 0).isoformat() + "Z" if db.is_dry_run else datetime.utcnow().isoformat() + "Z"
    
    jobs_store[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "source_name": payload.source_name,
        "created_at": now,
        "completed_at": None,
        "state": None,
        "error": None
    }
    
    background_tasks.add_task(process_ingestion_job, job_id, payload.text, payload.source_name)
    
    return IngestResponse(
        status="queued",
        job_id=job_id,
        message="Document ingestion queued successfully."
    )

@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse, tags=["Ingestion"], summary="Get Ingestion Job Status")
@limiter.limit("30/minute")
def get_job_status_endpoint(request: Request, job_id: str = Path(..., examples=["job_123456"], description="The unique job identifier")):
    """
    Retrieves the current status and results of a background ingestion job.
    Reports whether the job is queued, processing, completed, or failed.
    Once completed, returns the updated GraphUpdateState metrics.
    """
    logger.info(f"API /v1/jobs/{job_id} called.")
    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        
    job_data = jobs_store[job_id]
    return JobStatusResponse(**job_data)

@app.get("/v1/graph/entity/{name}", response_model=EntityInspectResponse, tags=["Knowledge Graph"], summary="Inspect Graph Node & Relationships")
@limiter.limit("30/minute")
def inspect_entity_endpoint(request: Request, name: str = Path(..., examples=["WhySchool"], description="Canonical entity name to inspect")):
    """
    Directly inspects a knowledge graph node in Neo4j. Returns its core properties, aliases, 
    provenance chunk IDs, and all incoming/outgoing relationship edges with their frequency weights.
    """
    logger.info(f"API /v1/graph/entity/{name} called.")
    
    if db.is_dry_run:
        logger.info("[DRY RUN] Returning mock entity inspection response.")
        return EntityInspectResponse(
            name=name,
            type="ORG" if "school" in name.lower() else "CONCEPT",
            description=f"Mock knowledge graph node representing {name} (DRY RUN)",
            aliases=[f"{name} Official", f"{name} Inc"],
            source_chunk_ids=["chunk_1", "chunk_2"],
            outgoing_relationships=[EntityRelationship(predicate="FOUNDED_IN", target="2024", weight=2.0)],
            incoming_relationships=[EntityRelationship(predicate="FOUNDED", source="Shadwal Singh", weight=1.5)]
        )

    query = """
    MATCH (e:Entity) WHERE toLower(e.name) CONTAINS toLower($name) OR toLower($name) CONTAINS toLower(e.name)
    OPTIONAL MATCH (e)-[r_out]->(o:Entity)
    OPTIONAL MATCH (s:Entity)-[r_in]->(e)
    RETURN e.name AS name, e.type AS type, e.description AS description, 
           e.aliases AS aliases, e.source_chunk_ids AS chunks,
           collect(DISTINCT {predicate: type(r_out), target: o.name, weight: coalesce(r_out.weight, 1.0)}) AS outgoing_relationships,
           collect(DISTINCT {source: s.name, predicate: type(r_in), weight: coalesce(r_in.weight, 1.0)}) AS incoming_relationships
    """
    
    try:
        results = db.query(query, {"name": name})
        if not results or not results[0]["name"]:
            raise HTTPException(status_code=404, detail=f"Entity '{name}' not found in knowledge graph.")
            
        r = results[0]
        out_rels = [EntityRelationship(**rel) for rel in r["outgoing_relationships"] if rel.get("predicate")]
        in_rels = [EntityRelationship(**rel) for rel in r["incoming_relationships"] if rel.get("predicate")]
        
        return EntityInspectResponse(
            name=r["name"],
            type=r["type"] or "CONCEPT",
            description=r["description"] or "No description available.",
            aliases=r["aliases"] or [],
            source_chunk_ids=r["chunks"] or [],
            outgoing_relationships=out_rels,
            incoming_relationships=in_rels
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API /v1/graph/entity/{name} failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

@app.get("/v1/graph/path", response_model=ShortestPathResponse, tags=["Knowledge Graph"], summary="Shortest Path Traversal")
@limiter.limit("30/minute")
def shortest_path_endpoint(
    request: Request,
    from_entity: str = Query(..., alias="from", examples=["Shadwal Singh"], description="Start entity name"),
    to_entity: str = Query(..., alias="to", examples=["AI Education"], description="Target entity name")
):
    """
    Executes a shortest path graph traversal between two entities in Neo4j (up to 5 hops). 
    Returns the exact sequence of connecting nodes and relationship verbs. This capability is unique 
    to GraphRAG and has no equivalent in flat vector databases.
    """
    logger.info(f"API /v1/graph/path called from '{from_entity}' to '{to_entity}'.")
    
    if db.is_dry_run:
        logger.info("[DRY RUN] Returning mock shortest path response.")
        return ShortestPathResponse(
            from_entity=from_entity,
            to_entity=to_entity,
            path_found=True,
            path_nodes=[from_entity, "WhySchool", to_entity],
            path_relationships=["FOUNDED", "FOCUSES_ON"]
        )

    query = """
    MATCH (s:Entity {name: $from_name}), (t:Entity {name: $to_name})
    MATCH p = shortestPath((s)-[*..5]-(t))
    RETURN [n IN nodes(p) | n.name] AS path_nodes,
           [r IN relationships(p) | type(r)] AS path_relationships
    """
    
    try:
        results = db.query(query, {"from_name": from_entity, "to_name": to_entity})
        if not results:
            return ShortestPathResponse(
                from_entity=from_entity,
                to_entity=to_entity,
                path_found=False,
                path_nodes=[],
                path_relationships=[]
            )
            
        r = results[0]
        return ShortestPathResponse(
            from_entity=from_entity,
            to_entity=to_entity,
            path_found=True,
            path_nodes=r["path_nodes"],
            path_relationships=r["path_relationships"]
        )
    except Exception as e:
        logger.error(f"API /v1/graph/path failed: {e}")
        raise HTTPException(status_code=500, detail=f"Shortest path traversal failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

