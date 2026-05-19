import logging
import random
from typing import Any, Dict, List

# pyright: ignore [missing-import].
from chromadb.utils import embedding_functions
# pyright: ignore [missing-import].
from dotenv import load_dotenv

# pyright: ignore [missing-import].
from src.database import db

# Load environment variables.
load_dotenv()

logger = logging.getLogger(__name__)


class EntityEmbedder:
    """
    Service to generate and store semantic embeddings for Neo4j Entity nodes.
    Uses local all-MiniLM-L6-v2 to create vectors representing the entity meaning.
    """

    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.ef = None

    def _fetch_unembedded_entities(self) -> List[Dict[str, Any]]:
        """Finds all Entity nodes in Neo4j that do not have an embedding yet."""
        query = """
        MATCH (e:Entity)
        WHERE e.embedding IS NULL
        RETURN e.id AS id, e.name AS name, e.description AS description
        """
        results = db.query(query)
        # Results are a list of neo4j.
        # Convert to standard dict.
        return [
            {"id": r["id"], "name": r["name"], "description": r["description"]}
            for r in results
        ]

    def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings using local model for a batch of strings."""
        if db.is_dry_run:
            logger.info(f"[DRY RUN] Simulating {len(texts)} embeddings...")
            # Return random 384-dim vectors for dry run.
            return [[random.random() for _ in range(384)] for _ in texts]

        try:
            if self.ef is None:
                logger.info("Initializing DefaultEmbeddingFunction (may download ONNX model)...")
                self.ef = embedding_functions.DefaultEmbeddingFunction()
            return self.ef(texts)
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise

    def _upsert_embeddings_batch(self, updates: List[Dict[str, Any]]):
        """Updates Neo4j Entity nodes with their new embeddings using UNWIND."""
        if db.is_dry_run:
            logger.info(f"[DRY RUN] Would update {len(updates)} entities in DB.")
            return

        query = """
        UNWIND $updates AS row
        MATCH (e:Entity {id: row.id})
        SET e.embedding = row.embedding
        """
        db.query(query, parameters={"updates": updates})

    def run(self):
        """
        Main execution loop. Fetches all unembedded entities, batches them,
        generates local HuggingFace embeddings, and writes them back to Neo4j.
        """
        logger.info("Starting Entity Embedding Generation Process...")

        entities = self._fetch_unembedded_entities()
        if not entities:
            logger.info("No unembedded entities found. Graph is up to date.")
            return

        logger.info(f"Found {len(entities)} entities needing embeddings.")

        # Process in batches.
        for i in range(0, len(entities), self.batch_size):
            batch = entities[i : i + self.batch_size]
            logger.info(
                f"Processing batch {i//self.batch_size + 1} (size {len(batch)})..."
            )

            # Prepare text: "name: description".
            texts_to_embed = []
            for e in batch:
                desc = e["description"] if e["description"] else ""
                text = f"{e['name']}: {desc}"
                texts_to_embed.append(text)

            # Generate embeddings.
            try:
                embeddings = self._generate_embeddings_batch(texts_to_embed)
            except Exception as e:
                logger.error(f"Aborting embedding run due to local generation failure: {e}")
                return

            # Prepare updates for Cypher UNWIND.
            updates = []
            for j, e in enumerate(batch):
                updates.append({"id": e["id"], "embedding": embeddings[j]})

            # Upsert back to Graph.
            self._upsert_embeddings_batch(updates)



        logger.info("Entity Embedding Generation Complete.")


# Global instance.
embedder = EntityEmbedder()

