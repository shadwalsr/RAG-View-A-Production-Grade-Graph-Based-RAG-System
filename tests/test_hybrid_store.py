import logging
import sys
import os

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.hybrid_store import hybrid_store

# Configure logging.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_hybrid_store():
    logger.info("--- Starting HybridStore Tests ---")
    
    # 1.
    chunks = [
        {
            "id": "chunk_v1",
            "text": "The quick brown fox jumps over the lazy dog.",
            "entity_ids": ["Fox", "Dog"],
            "metadata": {"source": "test_script"}
        },
        {
            "id": "chunk_v2",
            "text": "Neo4j is a powerful graph database often used in Hybrid RAG systems.",
            "entity_ids": ["Neo4j", "Hybrid RAG"],
            "metadata": {"source": "test_script"}
        },
        {
            "id": "chunk_v3",
            "text": "ChromaDB provides efficient vector storage and similarity search capabilities.",
            "entity_ids": ["ChromaDB"],
            "metadata": {"source": "test_script"}
        }
    ]
    
    for c in chunks:
        hybrid_store.add_chunk(
            chunk_id=c["id"],
            text=c["text"],
            entity_ids=c["entity_ids"],
            metadata=c["metadata"]
        )
        
    logger.info("Chunks successfully added to HybridStore.")
    
    # 2.
    logger.info("--- Testing Vector Search ---")
    query_vector = "Looking for a graph storage solution"
    v_results = hybrid_store.vector_search(query_vector, top_k=2)
    logger.info(f"Vector search results for '{query_vector}':")
    for r in v_results:
        logger.info(f" - [{r['id']}] (dist: {r['distance']:.3f}): {r['text'][:50]}... | Entities: {r['metadata'].get('entity_ids')}")
        
    # 3.
    logger.info("--- Testing Keyword Search (BM25) ---")
    query_keyword = "Neo4j database"
    k_results = hybrid_store.keyword_search(query_keyword, top_k=2)
    logger.info(f"Keyword search results for '{query_keyword}':")
    for r in k_results:
        logger.info(f" - [{r['id']}] (score: {r['score']:.3f}): {r['text'][:50]}... | Entities: {r['metadata'].get('entity_ids')}")
        
    logger.info("HybridStore tests completed successfully.")

if __name__ == "__main__":
    test_hybrid_store()

