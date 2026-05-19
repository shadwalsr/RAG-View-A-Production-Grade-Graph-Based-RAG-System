import os
import sys
import logging

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Enable DRY RUN to avoid 429 Quota errors for the demo.
os.environ["DRY_RUN"] = "true"

from src.database import db
from src.retriever import retriever
from src.qa import qa_generator
from src.hybrid_store import hybrid_store

# Configure logging.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_query_entity_linker():
    logger.info("--- Phase 3 DEMO: Query Entity Extraction ---")
    
    # Setup mocks.
    db.is_dry_run = True
    
    # Mock Hybrid Store to return NO chunks.
    # This will prove that graph traversal still happens because of Query Entity Linke.
    hybrid_store.vector_search = lambda query, top_k=5: []
    hybrid_store.keyword_search = lambda query, top_k=5: []
    
    # Mock DB Query results.
    original_query = db.query
    def mock_db_query(query, parameters=None):
        if "MATCH (e:Entity)-[r]->(t:Entity)" in query and "LIMIT 50" in query:
            # Linked entity lookup.
            # If the Query Entity Linker correctly extracted "WhySchool", it will be in parame.
            if "WhySchool" in parameters.get("entity_ids", []):
                return [{"source": "WhySchool", "rel": "FOUNDED_IN", "target": "2024"}, 
                        {"source": "WhySchool", "rel": "FOCUSES_ON", "target": "Education"}]
        elif "MATCH (e:Entity)" in query and "vector.similarity.cosine" in query:
            # Semantic search lookup.
            return [{"source": "WhySchool Academy", "rel": "IS_A", "target": "Startup", "score": 0.95}]
        return []
        
    db.query = mock_db_query
    
    query = "What did Shadwal build at WhySchool?"
    logger.info(f"\nUser Query: {query}\n")
    
    # Run the retrieval router.
    fused_context = retriever.retrieve(query)
    
    logger.info("=== RETRIEVED FUSED CONTEXT ===")
    print(fused_context)
    logger.info("===============================\n")
    
    # Restore db.
    db.query = original_query

if __name__ == "__main__":
    test_query_entity_linker()

