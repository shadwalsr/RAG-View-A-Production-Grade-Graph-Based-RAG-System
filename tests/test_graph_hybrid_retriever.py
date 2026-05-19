import os
import sys
import logging

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Enable DRY RUN.
os.environ["DRY_RUN"] = "true"

from src.database import db
from src.graph_hybrid_retriever import graph_hybrid_retriever
from src.retriever import retriever

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_graph_hybrid_retriever_logic():
    logger.info("--- Testing GraphHybridRetriever & RRF Fusion ---")
    db.is_dry_run = True
    
    # 1.
    query = "What did Shadwal build at WhySchool?"
    logger.info(f"\nExecuting parallel retrieval for query: '{query}'")
    
    res = graph_hybrid_retriever.retrieve(query, top_k=3)
    logger.info(f"Retrieved {len(res['texts'])} fused chunks and {len(res['relationships'])} relationships.")
    
    # 2.
    logger.info("\nExecuting Master RetrievalRouter flow...")
    context = retriever.retrieve(query)
    
    logger.info("\n=== MASTER RETRIEVED CONTEXT ===")
    print(context)
    logger.info("================================\n")
    
    assert "DOCUMENT EXCERPTS" in context
    assert "KNOWLEDGE GRAPH RELATIONSHIPS" in context
    logger.info("GraphHybridRetriever test completed successfully.")

if __name__ == "__main__":
    test_graph_hybrid_retriever_logic()

