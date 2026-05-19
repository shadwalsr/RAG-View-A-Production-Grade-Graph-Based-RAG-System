import logging
import sys
import os

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.graph_store import graph_store
from src.extractor import ExtractionResult, Entity, Relationship, EntityType
from src.database import db

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ingestion():
    logger.info("Starting graph ingestion test...")
    orig_dry_run = db.is_dry_run
    db.is_dry_run = False
    
    try:
        # 1.
        try:
            db.query("MATCH (n) DETACH DELETE n")
            logger.info("Cleared database.")
        except Exception as e:
            logger.error(f"Failed to clear database (is Neo4j running?): {e}")
            return

        # 2.
        db.setup_schema()

        # 3.
        sample_extractions = [
            ExtractionResult(
                source_chunk_id="chunk_001",
                entities=[
                    Entity(name="Neo4j", type=EntityType.ORG, short_description="A graph database company", confidence_score=1.0),
                    Entity(name="Cypher", type=EntityType.SKILL, short_description="A graph query language", confidence_score=1.0)
                ],
                relationships=[
                    Relationship(subject="Neo4j", predicate="DEVELOPED", object="Cypher", confidence_score=0.95)
                ]
            ),
            ExtractionResult(
                source_chunk_id="chunk_002",
                entities=[
                    Entity(name="Neo4j", type=EntityType.ORG, short_description="Graph data platform creator", confidence_score=1.0),
                    Entity(name="Python", type=EntityType.SKILL, short_description="A popular programming language", confidence_score=1.0)
                ],
                relationships=[
                    Relationship(subject="Neo4j", predicate="SUPPORTED_BY", object="Python", confidence_score=0.9)
                ]
            ),
            ExtractionResult(
                source_chunk_id="chunk_003",
                entities=[
                    Entity(name="Shadwal Singh", type=EntityType.PERSON, short_description="A software engineer building RAG-View", confidence_score=1.0),
                    Entity(name="RAG-View", type=EntityType.PROJECT, short_description="A graph-powered document intelligence platform", confidence_score=1.0),
                    Entity(name="Neo4j", type=EntityType.ORG, short_description="Graph database", confidence_score=1.0)
                ],
                relationships=[
                    Relationship(subject="Shadwal Singh", predicate="BUILT", object="RAG-View", confidence_score=1.0),
                    Relationship(subject="RAG-View", predicate="USES", object="Neo4j", confidence_score=1.0)
                ]
            )
        ]

        # 4.
        for ext in sample_extractions:
            logger.info(f"Ingesting {ext.source_chunk_id}...")
            graph_store.ingest_extraction(ext)

        # 5.
        logger.info("--- Verification Queries ---")
        
        # Check node count.
        res = db.query("MATCH (n:Entity) RETURN count(n) AS count")
        node_count = res[0]["count"]
        logger.info(f"Total Entity nodes: {node_count} (Expected: 5)")
        
        # Check relationship count.
        res = db.query("MATCH ()-[r]->() RETURN count(r) AS count")
        rel_count = res[0]["count"]
        logger.info(f"Total Relationships: {rel_count} (Expected: 4)")
        
        # Check provenance for 'Neo4j'.
        res = db.query("MATCH (e:Entity {name: 'Neo4j'}) RETURN e.source_chunk_ids AS ids")
        neo4j_provenance = res[0]["ids"]
        logger.info(f"'Neo4j' node provenance: {neo4j_provenance} (Expected: all 3 chunks)")
        
        # Check deduplication.
        res = db.query("MATCH (e:Entity {name: 'Python'}) RETURN count(e) AS count")
        py_count = res[0]["count"]
        logger.info(f"'Python' node count: {py_count} (Expected: 1)")

        logger.info("Test completed successfully!")
    finally:
        db.is_dry_run = orig_dry_run

if __name__ == "__main__":
    test_ingestion()

