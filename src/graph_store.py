import logging
from typing import List

from src.database import db
from src.extractor import Entity, ExtractionResult, Relationship

logger = logging.getLogger(__name__)

class GraphStore:
    """
    Handles the ingestion of ExtractionResult objects into Neo4j.
    Uses MERGE to prevent duplicates and ensures full provenance with source_chunk_id.
    """

    def ingest_extraction(self, extraction: ExtractionResult):
        """
        Ingests a single ExtractionResult into Neo4j.
        """
        if not extraction.entities and not extraction.relationships:
            logger.info("Extraction result is empty, skipping ingestion.")
            return

        source_chunk_id = extraction.source_chunk_id or "unknown"

        # 1.
        self._upsert_entities(extraction.entities, source_chunk_id)

        # 2.
        self._create_relationships(extraction.relationships, source_chunk_id)

    def _upsert_entities(self, entities: List[Entity], source_chunk_id: str):
        """
        Upserts entities using MERGE.
        Entities are identified by their canonical name.
        """
        query = """
        UNWIND $entities AS entity
        MERGE (e:Entity {name: entity.name})
        ON CREATE SET 
            e.type = entity.type,
            e.description = entity.short_description,
            e.source_chunk_ids = [ $source_chunk_id ],
            e.created_at = timestamp(),
            e.updated_at = timestamp()
        ON MATCH SET
            e.type = entity.type,
            e.description = entity.short_description,
            e.source_chunk_ids = CASE 
                WHEN $source_chunk_id IN e.source_chunk_ids THEN e.source_chunk_ids 
                ELSE e.source_chunk_ids + $source_chunk_id 
            END,
            e.updated_at = timestamp()
        """
        
        # Prepare parameters for UNWIND.
        entity_params = [
            {
                "name": e.name,
                "type": e.type.value,
                "short_description": e.short_description
            }
            for e in entities
        ]

        try:
            db.query(query, {"entities": entity_params, "source_chunk_id": source_chunk_id})
            logger.info(f"Upserted {len(entities)} entities from chunk '{source_chunk_id}'.")
        except Exception as e:
            logger.error(f"Failed to upsert entities: {e}")
            raise

    def _create_relationships(self, relationships: List[Relationship], source_chunk_id: str):
        """
        Creates relationships between existing entities.
        Since we ensure entities exist first, we use MATCH for both ends.
        """
        # We process relationships one by one because Neo4j relationship types (predicates.
        # cannot be dynamic in a single Cypher query without using APOC or complex string manipulation.
        
        for rel in relationships:
            # We use MERGE for the relationship itself to avoid duplicates between same nodes.
            query = f"""
            MATCH (s:Entity {{name: $subject}})
            MATCH (o:Entity {{name: $object}})
            MERGE (s)-[r:{rel.predicate}]->(o)
            ON CREATE SET 
                r.source_chunk_ids = [ $source_chunk_id ],
                r.confidence_score = $confidence,
                r.created_at = timestamp()
            ON MATCH SET
                r.source_chunk_ids = CASE 
                    WHEN $source_chunk_id IN r.source_chunk_ids THEN r.source_chunk_ids 
                    ELSE r.source_chunk_ids + $source_chunk_id 
                END,
                r.updated_at = timestamp()
            """
            
            params = {
                "subject": rel.subject,
                "object": rel.object,
                "confidence": rel.confidence_score,
                "source_chunk_id": source_chunk_id
            }
            
            try:
                db.query(query, params)
            except Exception as e:
                logger.error(f"Failed to create relationship {rel.subject} -> {rel.predicate} -> {rel.object}: {e}")
                continue

        logger.info(f"Processed {len(relationships)} relationships from chunk '{source_chunk_id}'.")

# Global instance.
graph_store = GraphStore()

