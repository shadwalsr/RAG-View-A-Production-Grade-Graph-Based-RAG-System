import sys
sys.path.insert(0, '/app')
from src.database import db
from src.hybrid_store import hybrid_store

nodes = db.query("MATCH (n:Entity) RETURN n.name AS name, n.type AS type ORDER BY n.name")
print("Neo4j: {} entities".format(len(nodes)))
for n in nodes:
    print("  {} ({})".format(n["name"], n["type"]))
rels = db.query("MATCH (a)-[r]->(b) RETURN COUNT(r) AS c")
print("Neo4j: {} relationships".format(rels[0]["c"]))
print()
print("ChromaDB: {} chunks".format(hybrid_store.collection.count()))
print("BM25: {} docs".format(len(hybrid_store.corpus)))
