import logging
import sys
import os
from dotenv import load_dotenv

# Load environment variables early.
load_dotenv()

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.pipeline import pipeline
from src.database import db

# Configure logging.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Sample "Phase 1" data.
DEMO_TEXT = """
Alex Developer is a software engineer currently building RAG-View. 
RAG-View is a graph-powered document intelligence platform that uses Neo4j as its primary database.
Neo4j is a graph database company founded by Emil Eifrem in Sweden.
The project uses Gemini 2.0 Flash for extracting complex entities and relationships.
Python is the main programming language used in this project.
"""

def run_phase1_demo():
    logger.info("--- PHASE 1 DEMO: End-to-End Pipeline ---")
    
    # 1.
    logger.info("Initializing Database...")
    try:
        db.setup_schema()
    except Exception as e:
        logger.error(f"Failed to setup schema: {e}")
        return
    
    # 2.
    logger.info("Starting Pipeline for Demo Text...")
    pipeline.run(DEMO_TEXT, source_name="phase1_demo_text")
    
    # 3.
    logger.info("--- Verifying Data in Neo4j ---")
    
    try:
        # Check for nodes.
        nodes = db.query("MATCH (e:Entity) RETURN e.name AS name, e.type AS type")
        logger.info(f"Found {len(nodes)} entities in graph:")
        for node in nodes:
            logger.info(f" - {node['name']} ({node['type']})")
            
        # Check for relationships.
        rels = db.query("MATCH (s)-[r]->(o) RETURN s.name AS subject, type(r) AS predicate, o.name AS object")
        logger.info(f"Found {len(rels)} relationships in graph:")
        for rel in rels:
            logger.info(f" - {rel['subject']} --[{rel['predicate']}]--> {rel['object']}")
            
        # Check provenance.
        res = db.query("MATCH (e:Entity {name: 'RAG-View'}) RETURN e.source_chunk_ids AS ids")
        if res:
            prov = res[0]['ids']
            logger.info(f"Provenance for 'RAG-View': {prov}")
        else:
            logger.warning("'RAG-View' node not found in graph.")
    except Exception as e:
        logger.error(f"Verification queries failed: {e}")

if __name__ == "__main__":
    run_phase1_demo()

