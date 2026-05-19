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

def test_retrieval_router():
    logger.info("--- Phase 2 DEMO: Retrieval Router & QA ---")
    
    # Setup mocks.
    db.is_dry_run = True
    
    # 1.
    def mock_vector_search(query, top_k):
        return [{"id": "chunk_1", "text": "WhySchool is an innovative startup focused on education.", "metadata": {"entity_ids": ["WhySchool", "Education"]}}]
        
    def mock_keyword_search(query, top_k):
        return [{"id": "chunk_2", "text": "The founder of WhySchool loves Graph Databases.", "metadata": {"entity_ids": ["WhySchool", "Graph Databases"]}}]
        
    hybrid_store.vector_search = mock_vector_search
    hybrid_store.keyword_search = mock_keyword_search
    
    # 2.
    original_query = db.query
    def mock_db_query(query, parameters=None):
        if "MATCH (e:Entity)-[r]->(t:Entity)" in query and "LIMIT 50" in query:
            # Linked entity lookup.
            return [{"source": "WhySchool", "rel": "FOUNDED_IN", "target": "2024"}, 
                    {"source": "WhySchool", "rel": "FOCUSES_ON", "target": "Education"}]
        elif "MATCH (e:Entity)" in query and "vector.similarity.cosine" in query:
            # Semantic search lookup.
            return [{"source": "WhySchool Academy", "rel": "IS_A", "target": "Startup", "score": 0.95}]
        return []
        
    db.query = mock_db_query
    
    # 3.
    query = "What does WhySchool focus on and when was it founded?"
    logger.info(f"\nUser Query: {query}\n")
    
    fused_context = retriever.retrieve(query)
    
    logger.info("=== RETRIEVED FUSED CONTEXT ===")
    print(fused_context)
    logger.info("===============================\n")
    
    # 4.
    # We will mock the client in QA generator to bypass 429.
    qa_generator.client = None 
    answer = qa_generator.generate_answer(query, fused_context)
    
    logger.info("=== GENERATED ANSWER ===")
    print(answer)
    logger.info("========================\n")
    
    # Restore db.
    db.query = original_query

if __name__ == "__main__":
    test_retrieval_router()

