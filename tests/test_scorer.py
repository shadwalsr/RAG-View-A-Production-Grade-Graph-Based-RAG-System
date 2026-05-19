import os
import sys
import logging

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Enable DRY RUN.
os.environ["DRY_RUN"] = "true"

from src.database import db
from src.scorer import confidence_scorer, ConfidenceReport

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_confidence_scorer_logic():
    logger.info("--- Testing ConfidenceScorer & Graph Coverage Metric ---")
    db.is_dry_run = True
    
    # Bypass 429 Quota errors for the test by mocking client.
    confidence_scorer.client = None
    
    # Mock fused context containing WhySchool and Education.
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

    query = "What did Shadwal build at WhySchool in Education?"
    answer = "Shadwal built WhySchool, an educational startup [Source 1]."
    
    logger.info(f"\nEvaluating Confidence for Query:\n'{query}'")
    
    report = confidence_scorer.score(query, answer, fused_context)
    logger.info(f"\nGenerated Confidence Report:\n{report.model_dump_json(indent=2)}\n")
    
    assert isinstance(report, ConfidenceReport)
    # Query has 3 entities: Shadwal, WhySchool, Education (mocked by query_linker in dry run: WhySchool, Shadwal).
    # Let's check what query_linker.
    # In query_linker.
    # So query_entities = ["WhySchool", "Shadwal"].
    # WhySchool is in fused_context.
    # So coverage = 1/2 = 0.
    assert 0.49 <= report.graph_coverage <= 0.51
    assert report.retrieval_confidence > 0.0
    assert report.grounding_confidence > 0.0
    
    logger.info("ConfidenceScorer test completed successfully.")

if __name__ == "__main__":
    test_confidence_scorer_logic()

