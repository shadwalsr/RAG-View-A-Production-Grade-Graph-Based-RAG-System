import os
import sys
import logging

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Enable DRY RUN.
os.environ["DRY_RUN"] = "true"

from src.database import db
from src.retriever import retriever

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_context_assembler_logic():
    logger.info("--- Testing ContextAssembler & Relationship Injection ---")
    db.is_dry_run = True
    
    query = "What did Shadwal build at WhySchool?"
    logger.info(f"\nExecuting master retrieval for query: '{query}'")
    
    context = retriever.retrieve(query)
    
    logger.info("\n=== ASSEMBLED PROMPT BLOCK ===")
    print(context)
    logger.info("==============================\n")
    
    assert "INSTRUCTIONS FOR AI" in context
    assert "STRUCTURED KNOWLEDGE GRAPH FACTS" in context
    assert "DOCUMENT EXCERPTS" in context
    assert "USER QUERY: What did Shadwal build at WhySchool?" in context
    logger.info("ContextAssembler test completed successfully.")

if __name__ == "__main__":
    test_context_assembler_logic()

