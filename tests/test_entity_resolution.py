import logging
import sys
import os

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.database import db
from src.resolver import resolver

# Configure logging.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_entity_resolution():
    logger.info("--- Testing Entity Resolution ---")
    
    # Enable DRY RUN to test logic safely.
    os.environ["DRY_RUN"] = "true"
    db.is_dry_run = True
    
    original_query = db.query
    
    def mock_query(query, parameters=None):
        if "vector.similarity.cosine" in query:
            # Return some mocked similarity pairs.
            return [
                {"id1": "ent_whyschool", "id2": "ent_whyschool_academy", "score": 0.95},
                {"id1": "ent_whyschool_academy", "id2": "ent_whyschool_startup", "score": 0.93},
            ]
        elif "MATCH (e:Entity)" in query and "ORDER BY size" in query:
            # This is the APOC or fallback canonical selection query.
            # In Dry Run mode, the main merge_cluster prints to logger and returns early.
            pass
        return []
        
    db.query = mock_query
    
    # Run Resolver.
    try:
        resolver.run()
        logger.info("Resolver completed successfully.")
    except Exception as e:
        logger.error(f"Resolver failed: {e}")
        
    # Restore original query.
    db.query = original_query
    
if __name__ == "__main__":
    test_entity_resolution()

