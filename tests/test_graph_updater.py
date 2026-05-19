import os
import sys
import logging

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Enable DRY RUN.
os.environ["DRY_RUN"] = "true"

from src.database import db
from src.graph_updater import graph_updater, GraphUpdateState

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_graph_updater_logic():
    logger.info("--- Testing GraphUpdater & Incremental State Management ---")
    db.is_dry_run = True
    graph_updater.state = GraphUpdateState()
    
    # Bypass 429 Quota errors for the test by mocking extractor client.
    graph_updater.extractor.client = None
    
    raw_text = "WhySchool is an educational startup founded in 2024. It focuses on AI."
    source_name = "whyschool_press_release"
    
    logger.info(f"\nIngesting Document from source: '{source_name}'")
    state = graph_updater.ingest_document(raw_text, source_name)
    
    logger.info(f"\nUpdated Graph State:\n{state.model_dump_json(indent=2)}\n")
    
    assert isinstance(state, GraphUpdateState)
    assert state.last_ingested_source == source_name
    assert state.total_documents_ingested == 1
    assert state.total_chunks_processed > 0
    assert state.total_relationships_weighted > 0
    assert state.last_updated_at is not None
    
    logger.info("GraphUpdater test completed successfully.")

if __name__ == "__main__":
    test_graph_updater_logic()

