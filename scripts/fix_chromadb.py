"""Phase 2: Re-populate ChromaDB with real CV data (Neo4j already populated)."""
import sys, logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
sys.path.insert(0, '/app')

import pypdf
from src.database import db
from src.hybrid_store import hybrid_store
from src.processing import text_processor

print("=" * 60)
print("VERIFY: Neo4j State After Restart")
print("=" * 60)

nodes = db.query("MATCH (n:Entity) RETURN n.name AS name, n.type AS type ORDER BY n.name")
print(f"  Total entities in Neo4j: {len(nodes)}")
for n in nodes:
    print(f"    - {n['name']} ({n['type']})")

rels = db.query("MATCH (a)-[r]->(b) RETURN a.name AS src, type(r) AS rel, b.name AS tgt ORDER BY a.name")
print(f"  Total relationships: {len(rels)}")
for r in rels:
    print(f"    - {r['src']} --[{r['rel']}]--> {r['tgt']}")
print()

print("=" * 60)
print("FIX: Clear and Re-populate ChromaDB + BM25")
print("=" * 60)

# Fresh clear with the fixed method.
hybrid_store.clear()
print(f"  ChromaDB count after clear: {hybrid_store.collection.count()}")

# Read the CV.
reader = pypdf.PdfReader('/app/data/raw/CV_Shadwal.pdf')
full_text = ""
for page in reader.pages:
    full_text += page.extract_text() + "\n"

# Chunk the text.
chunks = text_processor.chunk_text(full_text, {"source": "CV_Shadwal.pdf"})
print(f"  Created {len(chunks)} chunks from CV")

# Get entity names for each chunk from Neo4j.
for chunk in chunks:
    # Query Neo4j for entities that reference this chunk.
    chunk_entities = db.query(
        "MATCH (e:Entity) WHERE $cid IN e.source_chunk_ids RETURN e.name AS name",
        {"cid": chunk['id']}
    )
    entity_names = [r['name'] for r in chunk_entities]
    
    # If no entities found for this specific chunk, get all entities.
    if not entity_names:
        all_ents = db.query("MATCH (e:Entity) RETURN e.name AS name")
        entity_names = [r['name'] for r in all_ents]
    
    try:
        hybrid_store.add_chunk(
            chunk_id=chunk['id'],
            text=chunk['text'],
            entity_ids=entity_names,
            metadata=chunk['metadata']
        )
        print(f"  Added chunk {chunk['id']} with {len(entity_names)} entities")
    except Exception as e:
        print(f"  FAILED chunk {chunk['id']}: {e}")

print()
print("=" * 60)
print("VERIFY: ChromaDB State")
print("=" * 60)
count = hybrid_store.collection.count()
print(f"  Total chunks in ChromaDB: {count}")
if count > 0:
    results = hybrid_store.collection.get(limit=10, include=['metadatas'])
    for cid, meta in zip(results['ids'], results['metadatas']):
        print(f"    - {cid}: {meta}")

print()
print("=" * 60)
print("VERIFY: Graph Coverage")
print("=" * 60)
from src.scorer import confidence_scorer

for q in ["Who is Shadwal Singh?", "What is LitKit?", "What is WhySchool?"]:
    try:
        cov, found, missing = confidence_scorer.calculate_graph_coverage(q, full_text[:500])
        print(f"  '{q}' -> coverage={cov:.2f}, found={found}")
    except Exception as e:
        print(f"  '{q}' -> ERROR: {e}")

print()
print("=" * 60)
print("VERIFY: Graph Retriever")
print("=" * 60)
from src.graph_retriever import graph_retriever

for ent in ["Shadwal Singh", "LitKit", "WhySchool"]:
    gdata = graph_retriever.traverse([ent])
    rels_found = gdata.get("relationships", [])
    print(f"  '{ent}' -> {rels_found}")

print()
print("DONE.")

