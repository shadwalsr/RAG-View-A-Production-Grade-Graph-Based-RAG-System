import logging
import time
from typing import Optional

from pydantic import BaseModel, Field

from src.community_store import community_store
from src.database import db
from src.embedder import embedder
from src.extractor import EntityExtractor
from src.graph_store import graph_store
from src.hybrid_store import hybrid_store
from src.processing import text_processor
from src.resolver import resolver

logger = logging.getLogger(__name__)

class GraphUpdateState(BaseModel):
    """
    State management model tracking incremental graph updates and ingestion metrics.
    """
    last_ingested_source: Optional[str] = Field(default=None, description="Name of the last ingested document source")
    last_updated_at: Optional[float] = Field(default=None, description="Timestamp of the last successful graph update")
    total_documents_ingested: int = Field(default=0, description="Total number of documents ingested into the graph")
    total_chunks_processed: int = Field(default=0, description="Total number of text chunks processed")
    total_entities_extracted: int = Field(default=0, description="Total number of entities extracted across all updates")
    total_relationships_extracted: int = Field(default=0, description="Total number of relationships extracted across all updates")
    total_relationships_weighted: int = Field(default=0, description="Total number of relationships updated with frequency weights")

class GraphUpdater:
    """
    Incremental Graph Update Pipeline (Phase 4 Deliverable).
    Orchestrates document ingestion, entity extraction, duplicate resolution, 
    and frequency-based relationship weight updates. Maintains graph state management.
    """
    def __init__(self):
        self.extractor = EntityExtractor()
        self.state = GraphUpdateState()

    def update_relationship_weights(self) -> int:
        """
        Updates relationship weights based on frequency of appearance across documents/chunks.
        If a relationship appears in 5 documents it gets higher weight (2.0) than one appearing in 1 (1.0).
        """
        logger.info("GraphUpdater starting frequency-based relationship weight updates...")
        
        if db.is_dry_run:
            logger.info("[DRY RUN] Simulating frequency-based relationship weight update.")
            self.state.total_relationships_weighted += 10
            return 10

        query = """
        MATCH ()-[r]->()
        WHERE r.source_chunk_ids IS NOT NULL
        WITH r, size(r.source_chunk_ids) AS freq
        SET r.weight = CASE 
            WHEN freq >= 5 THEN 2.0
            WHEN freq >= 3 THEN 1.5
            ELSE 1.0
        END, r.frequency = freq
        RETURN count(r) AS updated_count
        """
        
        try:
            results = db.query(query)
            updated_count = results[0]["updated_count"] if results else 0
            logger.info(f"Successfully updated weights for {updated_count} relationships.")
            self.state.total_relationships_weighted = updated_count
            return updated_count
        except Exception as e:
            logger.error(f"Failed to update relationship weights: {e}")
            return 0

    def ingest_document(self, raw_text: str, source_name: str = "manual_upload") -> GraphUpdateState:
        """
        Orchestrates the full incremental ingestion and graph update pipeline for a new document.
        Extracts entities, resolves duplicates, updates weights, and refreshes macro-communities.
        """
        logger.info(f"GraphUpdater starting incremental ingestion for source: '{source_name}'")
        
        # 1.
        chunks = text_processor.chunk_text(raw_text, {"source": source_name})
        self.state.total_chunks_processed += len(chunks)
        self.state.total_documents_ingested += 1
        self.state.last_ingested_source = source_name

        # 2.
        for i, chunk in enumerate(chunks):
            logger.info(f"GraphUpdater processing chunk {i+1}/{len(chunks)} (ID: {chunk['id']})...")
            
            entity_names = []
            try:
                extraction = self.extractor.extract(chunk['text'], chunk_id=chunk['id'])
                self.state.total_entities_extracted += len(extraction.entities)
                self.state.total_relationships_extracted += len(extraction.relationships)
                
                # Ingest into Neo4j.
                graph_store.ingest_extraction(extraction)
                entity_names = [e.name for e in extraction.entities]
            except Exception as e:
                logger.warning(f"GraphUpdater entity extraction skipped/failed for chunk {chunk['id']} (likely 429 quota limit): {e}. Proceeding with Hybrid Vector Ingestion.")

            # ALWAYS Ingest into Hybrid Store (ChromaDB + BM25) regardless of LLM quota!.
            try:
                hybrid_store.add_chunk(
                    chunk_id=chunk['id'],
                    text=chunk['text'],
                    entity_ids=entity_names,
                    metadata=chunk['metadata']
                )
            except Exception as e:
                logger.error(f"GraphUpdater hybrid storage failed for chunk {chunk['id']}: {e}")

            # Respect API quotas on free tier.
            if i < len(chunks) - 1 and not db.is_dry_run:
                logger.info("GraphUpdater applying rate-limit delay (5s)...")
                time.sleep(5)

        # 3.
        logger.info("GraphUpdater triggering Graph Entity Embedding pass...")
        try:
            embedder.run()
        except Exception as e:
            logger.error(f"GraphUpdater Entity Embedding pass failed: {e}")

        # 4.
        logger.info("GraphUpdater triggering Entity Resolution pass...")
        try:
            resolver.run()
        except Exception as e:
            logger.error(f"GraphUpdater Entity Resolution pass failed: {e}")

        # 5.
        self.update_relationship_weights()

        # 6.
        logger.info("GraphUpdater triggering Community Detection pass...")
        try:
            community_store.build_communities()
        except Exception as e:
            logger.error(f"GraphUpdater Community Detection pass failed: {e}")

        self.state.last_updated_at = time.time()
        logger.info(f"GraphUpdater incremental ingestion complete for '{source_name}'.")
        return self.state

    def get_state(self) -> GraphUpdateState:
        """Returns the current state management metrics."""
        return self.state

# Global instance.
graph_updater = GraphUpdater()
updater = graph_updater  # Alias

