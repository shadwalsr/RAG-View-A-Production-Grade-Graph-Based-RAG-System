import logging
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables (NEO4J_URI, etc.
load_dotenv(override=True)

logger = logging.getLogger(__name__)

class Neo4jConnection:
    def __init__(self):
        self.is_dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        if self.is_dry_run:
            self.driver = None
            logger.info("Database initialized in DRY RUN mode. No connection will be attempted.")
        else:
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USERNAME", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "password")
            self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        if self.driver:
            self.driver.close()

    def query(self, query, parameters=None):
        if self.is_dry_run:
            logger.info(f"[DRY RUN] Executing query:\n{query}\nWith params: {parameters}")
            return []

        assert self.driver is not None, "Driver not initialized!"
        session = None
        response = None
        try:
            session = self.driver.session()
            response = list(session.run(query, parameters))
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise 
        finally:
            if session:
                session.close()
        return response

    def setup_schema(self):
        """
        Initializes the schema for the knowledge graph.
        """
        if self.is_dry_run:
            logger.info("[DRY RUN] Skipping schema setup.")
            return

        drop_indexes = [
            "DROP INDEX entity_embedding IF EXISTS"
        ]
        
        constraints = [
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
        ]
        
        indexes = [
            """
            CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
            FOR (e:Entity) ON (e.embedding)
            OPTIONS {indexConfig: {
              `vector.dimensions`: 384,
              `vector.similarity_function`: 'cosine'
            }}
            """
        ]
        
        with self.driver.session() as session:
            for drop_idx in drop_indexes:
                try:
                    session.run(drop_idx)
                except Exception as e:
                    logger.warning(f"Drop index skipped: {e}")
            for constraint in constraints:
                session.run(constraint)
            for index in indexes:
                session.run(index)
            logger.info("Schema initialized successfully.")

# Global instance.
db = Neo4jConnection()

