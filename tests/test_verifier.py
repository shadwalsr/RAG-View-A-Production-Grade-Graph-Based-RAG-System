import os
import sys
import logging

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Enable DRY RUN.
os.environ["DRY_RUN"] = "true"

from src.database import db
from src.verifier import graph_citation_verifier

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_graph_citation_verifier_logic():
    logger.info("--- Testing GraphCitationVerifier & Node Property Lookup ---")
    db.is_dry_run = True
    
    # Mock fused context.
    fused_context = """
=== INSTRUCTIONS FOR AI ===
Synthesize facts.

=== STRUCTURED KNOWLEDGE GRAPH FACTS & KNOWLEDGE GRAPH RELATIONSHIPS ===
- WhySchool --[FOUNDED_IN]--> 2024
- WhySchool --[FOCUSES_ON]--> Education

=== DOCUMENT EXCERPTS (RETRIEVED TEXT CHUNKS) ===
[Source 1]
WhySchool is an innovative startup focused on education.
"""

    query = "When was WhySchool founded and what does it do?"
    
    # Bypass 429 Quota errors for the test by mocking client.
    graph_citation_verifier.client = None
    
    # 1.
    valid_answer = "WhySchool is an educational startup founded in 2024 [Source 1]."
    logger.info(f"\nVerifying Valid Answer:\n'{valid_answer}'")
    
    verified_valid = graph_citation_verifier.verify(query, valid_answer, fused_context)
    logger.info(f"Result:\n'{verified_valid}'\n")
    assert "UNVERIFIED" not in verified_valid
    
    # 2.
    fake_answer = "WhySchool was founded in 1999 by aliens [Source 1]. (hallucination)"
    logger.info(f"Verifying Hallucinated Answer:\n'{fake_answer}'")
    
    verified_fake = graph_citation_verifier.verify(query, fake_answer, fused_context)
    logger.info(f"Result:\n'{verified_fake}'\n")
    assert "UNVERIFIED" in verified_fake
    
    # 3.
    entities = graph_citation_verifier._extract_entities(fused_context, valid_answer)
    logger.info(f"Extracted Entities: {entities}")
    assert "WhySchool" in entities
    assert "2024" in entities
    
    props = graph_citation_verifier._fetch_node_properties(fused_context, valid_answer)
    logger.info(f"Fetched Node Properties:\n{props}\n")
    assert "WhySchool" in props
    
    logger.info("GraphCitationVerifier test completed successfully.")

if __name__ == "__main__":
    test_graph_citation_verifier_logic()

