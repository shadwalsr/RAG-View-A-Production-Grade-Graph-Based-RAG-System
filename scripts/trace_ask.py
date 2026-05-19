"""Live end-to-end ask pipeline trace."""
import sys, os, logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
sys.path.insert(0, '/app')

from src.database import db
from src.query_linker import query_linker
from src.graph_retriever import graph_retriever
from src.scorer import confidence_scorer
from src.retriever import retriever

query = "Who founded WhySchool?"

print("=" * 60)
print("STEP 1: Query Entity Extraction (query_linker)")
print("=" * 60)
entities = query_linker.extract_entities(query)
print("  Extracted entities: {}".format(entities))

print()
print("=" * 60)
print("STEP 2: Graph Traversal (graph_retriever)")
print("=" * 60)
gdata = graph_retriever.traverse(entities)
rels = gdata.get("relationships", [])
print("  Relationships found: {}".format(len(rels)))
for r in rels:
    print("    {}".format(r))

print()
print("=" * 60)
print("STEP 3: Graph Coverage (scorer)")
print("=" * 60)
cov, found, missing = confidence_scorer.calculate_graph_coverage(query, "test context")
print("  Coverage: {}".format(cov))
print("  Found: {}".format(found))
print("  Missing: {}".format(missing))

print()
print("=" * 60)
print("STEP 4: Full Retrieval (retriever.retrieve)")
print("=" * 60)
try:
    fused = retriever.retrieve(query)
    print("  Fused context length: {} chars".format(len(fused)))
    print("  First 500 chars:")
    print(fused[:500])
except Exception as e:
    print("  FAILED: {}".format(e))
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("STEP 5: Direct Neo4j Entity Check")
print("=" * 60)
for ent in entities:
    results = db.query(
        "MATCH (e:Entity) WHERE ANY(n IN $names WHERE toLower(e.name) CONTAINS toLower(n) OR toLower(n) CONTAINS toLower(e.name)) RETURN e.name AS name",
        {"names": [ent]}
    )
    print("  '{}' -> matches: {}".format(ent, [r['name'] for r in results]))
