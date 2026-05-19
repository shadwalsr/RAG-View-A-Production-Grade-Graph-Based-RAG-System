import logging
import os
from typing import List

from dotenv import load_dotenv
from google import genai

from src.database import db

load_dotenv()
logger = logging.getLogger(__name__)

COMMUNITY_SUMMARY_PROMPT = """
You are an expert AI summarization engine for a GraphRAG knowledge base.
Below is a list of entities that belong to the same tightly-connected community, along with raw text excerpts where they appear.
Synthesize this information into a comprehensive, high-level summary (3-5 sentences) describing the overarching theme, shared activities, or relationships within this community.

ENTITIES: {entities}

RAW EXCERPTS:
{excerpts}

SUMMARY:
"""

class CommunityStore:
    """
    Manages the creation, summarization, and retrieval of macro-level entity communities.
    Powers global query answering by providing high-level summaries instead of granular node traversals.
    """
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = "gemini-2.0-flash"

    def build_communities(self):
        """
        Executes Louvain community detection (or Cypher fallback), generates AI summaries,
        and persists Community nodes in Neo4j.
        """
        logger.info("Starting Community Detection pass...")

        if db.is_dry_run:
            logger.info("[DRY RUN] Mocking Community Detection & Summarization...")
            # Create a mock community node.
            mock_query = """
            MERGE (c:Community {id: 'comm_0'})
            SET c.summary = 'WhySchool is an educational startup founded by Shadwal focused on graph technology.',
                c.entities = ['WhySchool', 'Shadwal', 'Education']
            """
            db.query(mock_query)
            return

        # Step 1: Assign communityId to entities.
        has_gds = self._try_gds_louvain()
        if not has_gds:
            logger.warning("Neo4j GDS plugin not detected. Falling back to Cypher-based community clustering...")
            self._cypher_fallback_clustering()

        # Step 2: Aggregate entities by communityId and generate summaries.
        self._generate_and_store_summaries()

    def _try_gds_louvain(self) -> bool:
        """Attempts to run Neo4j GDS Louvain algorithm."""
        try:
            # Check if GDS is available.
            res = db.query("CALL gds.list() YIELD name WHERE name = 'gds.louvain.write' RETURN name")
            if not res:
                return False

            # Project graph.
            db.query("CALL gds.graph.drop('comm_graph', false)")
            project_query = """
            CALL gds.graph.project(
                'comm_graph',
                'Entity',
                {RELATED: {type: '*', orientation: 'UNDIRECTED'}}
            )
            """
            db.query(project_query)

            # Run Louvain.
            louvain_query = """
            CALL gds.louvain.write('comm_graph', {writeProperty: 'communityId'})
            YIELD communityCount, modularity
            """
            metrics = db.query(louvain_query)
            logger.info(f"GDS Louvain complete. Communities: {metrics[0]['communityCount']}, Modularity: {metrics[0]['modularity']:.3f}")
            db.query("CALL gds.graph.drop('comm_graph', false)")
            return True
        except Exception as e:
            logger.debug(f"GDS Louvain failed or unavailable: {e}")
            return False

    def _cypher_fallback_clustering(self):
        """
        Simple label-propagation/connected-components fallback using pure Cypher.
        Assigns communityId based on isolated subgraphs or shared neighbors.
        """
        query = """
        MATCH (e:Entity)
        WHERE e.communityId IS NULL
        WITH e
        // Assign a temporary community ID based on internal Neo4j element ID.
        SET e.communityId = 'comm_' + toString(id(e))
        """
        db.query(query)

        # Merge connected entities into the same community ID (1 pass propagation).
        prop_query = """
        MATCH (e1:Entity)-[]-(e2:Entity)
        WHERE e1.communityId <> e2.communityId
        WITH e1, e2
        ORDER BY id(e1) ASC
        SET e2.communityId = e1.communityId
        """
        db.query(prop_query)
        logger.info("Cypher fallback clustering complete.")

    def _generate_and_store_summaries(self):
        """Generates AI summaries for each community and stores them as Community nodes."""
        query = """
        MATCH (e:Entity)
        WHERE e.communityId IS NOT NULL
        WITH e.communityId AS comm_id, collect(e.name) AS entities, collect(e.source_chunk_ids) AS chunk_id_lists
        WHERE size(entities) >= 2
        RETURN comm_id, entities, chunk_id_lists
        ORDER BY size(entities) DESC
        LIMIT 10
        """
        communities = db.query(query)
        logger.info(f"Processing {len(communities)} macro communities for summarization...")

        import time

        from src.hybrid_store import hybrid_store

        for i, comm in enumerate(communities):
            comm_id = comm["comm_id"]
            entities = comm["entities"]
            chunk_id_lists = comm["chunk_id_lists"]

            # Flatten chunk IDs and get unique set.
            unique_chunk_ids = set()
            for cid_list in chunk_id_lists:
                if cid_list:
                    unique_chunk_ids.update(cid_list)

            # Pull raw text excerpts.
            excerpts = []
            for cid in list(unique_chunk_ids)[:5]:  # Cap at top 5 chunks to avoid token limits
                text = hybrid_store.get_chunk_by_id(cid)
                if text:
                    excerpts.append(text)

            excerpts_str = "\n---\n".join(excerpts)
            prompt = COMMUNITY_SUMMARY_PROMPT.format(entities=", ".join(entities), excerpts=excerpts_str)

            summary = f"Community {comm_id} comprising {', '.join(entities[:3])} and others."
            provider = os.getenv("LLM_PROVIDER", "gemini").lower()
            import requests

            if provider == "groq":
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                        "messages": [
                            {"role": "system", "content": "You are an expert AI summarization engine for a GraphRAG knowledge base."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 512,
                        "frequency_penalty": 0.2
                    }
                    try:
                        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                        if res.status_code == 200:
                            summary = res.json()["choices"][0]["message"]["content"].strip()
                        else:
                            logger.error(f"Groq API error in community summary: {res.text}")
                    except Exception as e:
                        logger.error(f"Groq exception in community summary: {e}")
            elif provider == "ollama":
                ollama_url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
                payload = {
                    "model": os.getenv("OLLAMA_MODEL", "llama3"),
                    "prompt": prompt,
                    "stream": False
                }
                try:
                    res = requests.post(f"{ollama_url.rstrip('/')}/api/generate", json=payload, timeout=300)
                    if res.status_code == 200:
                        summary = res.json()["response"].strip()
                    else:
                        logger.error(f"Ollama API error in community summary: {res.text}")
                except Exception as e:
                    logger.error(f"Ollama exception in community summary: {e}")
            elif self.client:
                try:
                    res = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt
                    )
                    summary = res.text.strip()
                except Exception as e:
                    logger.error(f"Failed to generate summary for community {comm_id}: {e}")

            # Store in Neo4j.
            store_query = """
            MERGE (c:Community {id: $comm_id})
            SET c.summary = $summary,
                c.entities = $entities
            """
            db.query(store_query, {"comm_id": str(comm_id), "summary": summary, "entities": entities})

            # Proactive rate limiting for Free Tier.
            if i < len(communities) - 1 and self.client:
                time.sleep(5)

        logger.info("Community summaries successfully generated and stored.")

    def get_community_summaries(self) -> List[str]:
        """Retrieves all macro community summaries from Neo4j."""
        logger.info("Fetching macro community summaries for global query...")
        if db.is_dry_run:
            return ["(Mock Community Summary) WhySchool is an educational startup founded by Shadwal focused on graph technology."]

        query = "MATCH (c:Community) RETURN c.summary AS summary LIMIT 10"
        try:
            results = db.query(query)
            return [r["summary"] for r in results]
        except Exception as e:
            logger.error(f"Failed to fetch community summaries: {e}")
            return []

# Global instance.
community_store = CommunityStore()

