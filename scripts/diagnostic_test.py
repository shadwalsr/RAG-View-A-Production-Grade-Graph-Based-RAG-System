"""Diagnostic: End-to-end extraction + ingestion test."""
import os, json, logging, sys
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

sys.path.insert(0, '/app')

from src.extractor import EntityExtractor
from src.graph_store import graph_store
from src.hybrid_store import hybrid_store
from src.database import db

print("=" * 60)
print("STEP A: LLM Provider Config")
print("=" * 60)
print(f"  LLM_PROVIDER = {os.getenv('LLM_PROVIDER')}")
print(f"  GROQ_API_KEY  = {'SET' if os.getenv('GROQ_API_KEY') else 'MISSING'}")
print(f"  GROQ_MODEL    = {os.getenv('GROQ_MODEL')}")
print()

print("=" * 60)
print("STEP B: Live Extraction Test (Groq)")
print("=" * 60)

test_text = (
    "Shadwal Singh is a software engineer and the founder of WhySchool, "
    "an AI-powered educational platform launched in 2024. He built the "
    "RAG-View system using Neo4j for knowledge graph storage, Gemini Flash "
    "for entity extraction, and ChromaDB for vector embeddings. The system "
    "implements a Hybrid RAG architecture that combines BM25 keyword search "
    "with semantic vector search using Reciprocal Rank Fusion."
)

extractor = EntityExtractor()
result = extractor.extract(test_text, chunk_id='diag_chunk_001')

print(f"  Entities extracted: {len(result.entities)}")
for e in result.entities:
    print(f"    - {e.name} ({e.type.value}): {e.short_description}")
print(f"  Relationships extracted: {len(result.relationships)}")
for r in result.relationships:
    print(f"    - {r.subject} --[{r.predicate}]--> {r.object}")
print(f"  Source chunk ID: {result.source_chunk_id}")
print()

if not result.entities:
    print("FATAL: Extractor returned 0 entities. Pipeline is broken at extraction level.")
    sys.exit(1)

print("=" * 60)
print("STEP C: Graph Store Ingestion")
print("=" * 60)
try:
    graph_store.ingest_extraction(result)
    print("  SUCCESS: Entities and relationships written to Neo4j.")
except Exception as e:
    print(f"  FAILED: {e}")
print()

print("=" * 60)
print("STEP D: Hybrid Store Ingestion")
print("=" * 60)
try:
    entity_names = [e.name for e in result.entities]
    hybrid_store.add_chunk(
        chunk_id='diag_chunk_001',
        text=test_text,
        entity_ids=entity_names,
        metadata={'source': 'diagnostic_test'}
    )
    print(f"  SUCCESS: Chunk stored with entity_ids={entity_names}")
except Exception as e:
    print(f"  FAILED: {e}")
print()

print("=" * 60)
print("STEP E: Neo4j Verification After Ingestion")
print("=" * 60)
nodes = db.query("MATCH (n:Entity) RETURN n.name AS name, n.type AS type, n.source_chunk_ids AS chunks")
print(f"  Total nodes in Neo4j: {len(nodes)}")
for n in nodes:
    print(f"    - {n['name']} ({n['type']}) chunks={n['chunks']}")
rels = db.query("MATCH (a:Entity)-[r]->(b:Entity) RETURN a.name AS src, type(r) AS rel, b.name AS tgt")
print(f"  Total relationships: {len(rels)}")
for r in rels:
    print(f"    - {r['src']} --[{r['rel']}]--> {r['tgt']}")
print()

print("=" * 60)
print("STEP F: ChromaDB Verification After Ingestion")
print("=" * 60)
count = hybrid_store.collection.count()
print(f"  Total chunks in ChromaDB: {count}")
if count > 0:
    results = hybrid_store.collection.get(limit=10, include=['metadatas'])
    for cid, meta in zip(results['ids'], results['metadatas']):
        print(f"    - {cid}: {meta}")
print()

print("=" * 60)
print("STEP G: Graph Coverage Test")
print("=" * 60)
from src.scorer import confidence_scorer
test_query = "What did Shadwal Singh build?"
try:
    cov, found, missing = confidence_scorer.calculate_graph_coverage(test_query, test_text)
    print(f"  Query: '{test_query}'")
    print(f"  Graph Coverage: {cov}")
    print(f"  Found: {found}")
    print(f"  Missing: {missing}")
except Exception as e:
    print(f"  FAILED: {e}")
print()

print("=" * 60)
print("STEP H: Graph Retriever Test")
print("=" * 60)
from src.graph_retriever import graph_retriever
gdata = graph_retriever.traverse(['Shadwal Singh'])
print(f"  Relationships: {gdata.get('relationships', [])}")
print(f"  Neighbor chunks: {gdata.get('neighbor_chunks', set())}")
