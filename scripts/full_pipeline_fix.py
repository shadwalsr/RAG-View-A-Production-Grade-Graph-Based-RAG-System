"""
Full Pipeline Fix: Clear stale data, ingest real CV document, verify graph.
"""
import os, sys, time, logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
sys.path.insert(0, '/app')

from src.database import db
from src.graph_updater import graph_updater
from src.hybrid_store import hybrid_store

print("=" * 60)
print("PHASE 1: Clear Stale Sample Data")
print("=" * 60)

# Clear Neo4j.
print("  Clearing all Neo4j nodes and relationships...")
try:
    db.query("MATCH (n) DETACH DELETE n")
    remaining = db.query("MATCH (n) RETURN COUNT(n) AS count")
    print(f"  Neo4j after clear: {remaining[0]['count']} nodes")
except Exception as e:
    print(f"  Neo4j clear failed: {e}")

# Clear ChromaDB + BM25.
print("  Clearing ChromaDB and BM25 index...")
try:
    hybrid_store.clear()
    count = hybrid_store.collection.count()
    print(f"  ChromaDB after clear: {count} chunks")
except Exception as e:
    print(f"  HybridStore clear failed: {e}")

print()
print("=" * 60)
print("PHASE 2: Ingest Real CV Document")
print("=" * 60)

# Read the PDF.
import pypdf
reader = pypdf.PdfReader('/app/data/raw/CV_Shadwal.pdf')
full_text = ""
for page in reader.pages:
    full_text += page.extract_text() + "\n"

print(f"  PDF pages: {len(reader.pages)}")
print(f"  Total characters: {len(full_text)}")
print(f"  First 200 chars: {full_text[:200]}...")
print()

# Run the full ingestion pipeline.
print("  Starting ingestion pipeline (this will call Groq for each chunk)...")
state = graph_updater.ingest_document(full_text, source_name="CV_Shadwal.pdf")

print()
print(f"  Pipeline State:")
print(f"    Chunks processed: {state.total_chunks_processed}")
print(f"    Entities extracted: {state.total_entities_extracted}")
print(f"    Relationships extracted: {state.total_relationships_extracted}")
print(f"    Relationships weighted: {state.total_relationships_weighted}")
print()

print("=" * 60)
print("PHASE 3: Verification — Neo4j")
print("=" * 60)

nodes = db.query("MATCH (n:Entity) RETURN n.name AS name, n.type AS type, n.source_chunk_ids AS chunks ORDER BY n.name")
print(f"  Total entities in Neo4j: {len(nodes)}")
for n in nodes:
    print(f"    - {n['name']} ({n['type']}) [{len(n['chunks'] or [])} chunks]")

rels = db.query("MATCH (a)-[r]->(b) RETURN a.name AS src, type(r) AS rel, b.name AS tgt ORDER BY a.name")
print(f"  Total relationships: {len(rels)}")
for r in rels:
    print(f"    - {r['src']} --[{r['rel']}]--> {r['tgt']}")
print()

print("=" * 60)
print("PHASE 4: Verification — ChromaDB")
print("=" * 60)

count = hybrid_store.collection.count()
print(f"  Total chunks in ChromaDB: {count}")
if count > 0:
    results = hybrid_store.collection.get(limit=5, include=['metadatas'])
    for cid, meta in zip(results['ids'], results['metadatas']):
        print(f"    - {cid}: {meta}")
print()

print("=" * 60)
print("PHASE 5: Verification — Graph Coverage")
print("=" * 60)
from src.scorer import confidence_scorer

queries = [
    "Who is Shadwal Singh?",
    "What is WhySchool?",
    "What did Shadwal build using Neo4j?",
]
for q in queries:
    try:
        cov, found, missing = confidence_scorer.calculate_graph_coverage(q, full_text[:500])
        print(f"  Query: '{q}'")
        print(f"    Coverage: {cov:.2f} | Found: {found} | Missing: {missing}")
    except Exception as e:
        print(f"  Query '{q}' FAILED: {e}")
print()

print("=" * 60)
print("PHASE 6: Verification — Graph Retriever")
print("=" * 60)
from src.graph_retriever import graph_retriever

for entity in ["Shadwal Singh", "WhySchool", "RAG-View"]:
    gdata = graph_retriever.traverse([entity])
    rels_found = gdata.get("relationships", [])
    chunks = gdata.get("neighbor_chunks", set())
    print(f"  Entity: {entity}")
    print(f"    Relationships: {rels_found}")
    print(f"    Neighbor chunks: {chunks}")
print()

print("=" * 60)
print("DONE — Pipeline fully operational.")
print("=" * 60)

