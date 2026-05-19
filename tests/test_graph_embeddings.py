import logging
import sys
import os

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.database import db
from src.embedder import embedder

# Configure logging.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_graph_embeddings():
    logger.info("--- Testing Graph Entity Embeddings ---")
    
    # Enable DRY RUN to avoid needing a live DB and API key for basic logic verificati.
    os.environ["DRY_RUN"] = "true"
    db.is_dry_run = True
    
    # 1.
    logger.info("Mocking DB query for unembedded entities...")
    original_query = db.query
    
    def mock_query(query, parameters=None):
        if "WHERE e.embedding IS NULL" in query:
            return [
                {"id": "person_alex", "name": "Alex Developer", "description": "Software engineer building RAG-View."},
                {"id": "org_neo4j", "name": "Neo4j", "description": "Graph database company."},
            ]
        logger.info(f"[MOCK UNWIND] Would update Neo4j with parameters: {parameters}")
        return []
        
    db.query = mock_query
    
    # 2.
    try:
        embedder.run()
        logger.info("Embedder completed successfully.")
    except Exception as e:
        logger.error(f"Embedder failed: {e}")
        
    # Restore original query.
    db.query = original_query
    
if __name__ == "__main__":
    test_graph_embeddings()

