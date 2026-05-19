import os
import sys
import logging

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Enable DRY RUN.
os.environ["DRY_RUN"] = "true"

from src.database import db
from src.community_store import community_store
from src.retriever import retriever

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_community_store_logic():
    logger.info("--- Testing CommunityStore & Global Query Routing ---")
    db.is_dry_run = True
    
    # 1.
    logger.info("\nExecuting Community Detection build pass...")
    community_store.build_communities()
    
    # 2.
    global_query = "Summarize all of Shadwal's experience and overview of his startup."
    logger.info(f"\nUser Query: '{global_query}'")
    
    context = retriever.retrieve(global_query)
    
    logger.info("=== RETRIEVED CONTEXT ===")
    print(context)
    logger.info("=========================\n")
    
    assert "MACRO COMMUNITY SUMMARIES (GLOBAL QUERY)" in context
    assert "WhySchool is an educational startup" in context
    logger.info("CommunityStore test completed successfully.")

if __name__ == "__main__":
    test_community_store_logic()

