import os
import sys
import logging

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Enable DRY RUN.
os.environ["DRY_RUN"] = "true"

from src.database import db
from src.graph_retriever import graph_retriever
from src.hybrid_store import hybrid_store

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_graph_retriever_logic():
    logger.info("--- Testing Graph Retriever (1-Hop & 2-Hop) ---")
    db.is_dry_run = True
    
    # 1.
    res = graph_retriever.traverse(["WhySchool"], depth=1)
    logger.info(f"Dry Run Result: {res}")
    
    # 2.
    db.is_dry_run = False
    original_query = db.query
    
    def mock_db_query(query, parameters=None):
        if "MATCH (start:Entity)-[r1]-(mid:Entity)" in query:
            # 2-hop query simulation.
            return [
                {
                    "source": "WhySchool", "rel1": "FOUNDED_BY", "mid": "Shadwal",
                    "rel2": "LIVES_IN", "end": "San Francisco",
                    "mid_chunks": ["chunk_shadwal_bio"], "end_chunks": ["chunk_sf_info"]
                }
            ]
        elif "MATCH (start:Entity)-[r]-(end:Entity)" in query:
            # 1-hop query simulation.
            return [
                {
                    "source": "WhySchool", "rel": "FOUNDED_BY", "target": "Shadwal",
                    "end_chunks": ["chunk_shadwal_bio"]
                }
            ]
        return []
        
    db.query = mock_db_query
    
    # Add mock chunks to HybridStore corpus so get_chunk_by_id works.
    hybrid_store.corpus = [
        {"id": "chunk_shadwal_bio", "text": "Shadwal is a passionate software architect.", "metadata": {}},
        {"id": "chunk_sf_info", "text": "San Francisco is a major tech hub.", "metadata": {}}
    ]
    
    logger.info("\nExecuting 1-Hop Traversal...")
    hop1 = graph_retriever.traverse(["WhySchool"], depth=1)
    logger.info(f"1-Hop Relationships: {hop1['relationships']}")
    logger.info(f"1-Hop Neighbor Chunks: {hop1['neighbor_chunks']}")
    
    logger.info("\nExecuting 2-Hop Traversal...")
    hop2 = graph_retriever.traverse(["WhySchool"], depth=2)
    logger.info(f"2-Hop Relationships: {hop2['relationships']}")
    logger.info(f"2-Hop Neighbor Chunks: {hop2['neighbor_chunks']}\n")
    
    # Restore DB.
    db.query = original_query
    db.is_dry_run = True
    logger.info("Graph Retriever test completed successfully.")

if __name__ == "__main__":
    test_graph_retriever_logic()

