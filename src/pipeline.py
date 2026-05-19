import logging

from src.extractor import EntityExtractor
from src.graph_store import graph_store
from src.hybrid_store import hybrid_store
from src.processing import text_processor

logger = logging.getLogger(__name__)

class RAGPipeline:
    """
    The orchestrator for the Phase 1 and 2 deliverables.
    Connects text processing, LLM extraction, graph ingestion, and hybrid storage.
    """
    
    def __init__(self):
        self.extractor = EntityExtractor()

    def run(self, raw_text: str, source_name: str = "manual_upload"):
        """
        Runs the full pipeline from raw text to knowledge graph and hybrid store.
        """
        logger.info(f"Starting Pipeline for source: {source_name}")
        
        # 1.
        chunks = text_processor.chunk_text(raw_text, {"source": source_name})
        
        # 2.
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)} (ID: {chunk['id']})...")
            
            entity_ids = []
            # Step A & B: Extract structured data via LLM and Upsert into Neo4j.
            try:
                extraction = self.extractor.extract(chunk['text'], chunk_id=chunk['id'])
                graph_store.ingest_extraction(extraction)
                entity_ids = [entity.name for entity in extraction.entities]
            except Exception as e:
                logger.warning(f"Pipeline entity extraction skipped/failed for chunk {chunk['id']} (likely 429 quota limit): {e}. Proceeding with Hybrid Vector Ingestion.")
            
            # Step C: ALWAYS Upsert into Hybrid Store (ChromaDB + BM25).
            try:
                hybrid_store.add_chunk(
                    chunk_id=chunk['id'],
                    text=chunk['text'],
                    entity_ids=entity_ids,
                    metadata=chunk['metadata']
                )
            except Exception as e:
                logger.error(f"Hybrid Storage failed for chunk {chunk['id']}: {e}")
                
            # Proactive rate-limiting for Free Tier (15 Requests per Minute = 1 req / 4s).
            import time
            if i < len(chunks) - 1:
                logger.info("Applying proactive rate-limit delay (5s) to respect API quotas...")
                time.sleep(5)
            
        # 3.
        logger.info("Triggering Graph Entity Embedding pass...")
        try:
            from src.embedder import embedder
            embedder.run()
        except Exception as e:
            logger.error(f"Entity Embedding pass failed: {e}")

        # 4.
        logger.info("Triggering Entity Resolution pass...")
        try:
            from src.resolver import resolver
            resolver.run()
        except Exception as e:
            logger.error(f"Entity Resolution pass failed: {e}")

        # 5.
        logger.info("Triggering Community Detection pass...")
        try:
            from src.community_store import community_store
            community_store.build_communities()
        except Exception as e:
            logger.error(f"Community Detection pass failed: {e}")

        logger.info("Pipeline execution complete.")

# Global instance.
pipeline = RAGPipeline()

