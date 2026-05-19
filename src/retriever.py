import logging
import random
from typing import Any, Dict, List

# pyright: ignore [missing-import].
from chromadb.utils import embedding_functions
# pyright: ignore [missing-import].
from dotenv import load_dotenv

# pyright: ignore [missing-import].
from src.database import db
# pyright: ignore [missing-import].
from src.hybrid_store import hybrid_store

load_dotenv()
logger = logging.getLogger(__name__)


class RetrievalRouter:
    """
    Core engine that retrieves and fuses context from both the flat HybridStore
    and the structured Neo4j Knowledge Graph.
    """

    def __init__(self):
        self.ef = None

    def _embed_query(self, query: str) -> List[float]:
        """Generates a local embedding for the user's query to search the Graph."""
        if db.is_dry_run:
            return [random.random() for _ in range(384)]

        try:
            if self.ef is None:
                logger.info("Initializing DefaultEmbeddingFunction in Retriever (may download ONNX model)...")
                self.ef = embedding_functions.DefaultEmbeddingFunction()
            return self.ef([query])[0]
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return []

    def _get_hybrid_context(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """Retrieves raw text chunks and their linked entity IDs."""
        logger.info("Querying HybridStore...")

        # Combine vector and keyword search results.
        v_results = hybrid_store.vector_search(query, top_k=top_k)
        k_results = hybrid_store.keyword_search(query, top_k=top_k)

        # Deduplicate chunks based on ID.
        all_chunks = {res["id"]: res for res in v_results + k_results}

        # We need to extract the entity IDs that these chunks reference.
        linked_entities = set()
        chunk_texts = []

        for chunk in all_chunks.values():
            chunk_texts.append(chunk["text"])
            if "entity_ids" in chunk["metadata"]:
                linked_entities.update(chunk["metadata"]["entity_ids"])

        return {"texts": chunk_texts, "linked_entities": list(linked_entities)}

    def _get_graph_traversal_context(self, entity_ids: List[str]) -> Dict[str, Any]:
        """Traverses the graph using the new GraphRetriever."""
        if not entity_ids:
            return {"relationships": [], "neighbor_chunks": set()}

        # pyright: ignore [missing-import].
        from src.graph_retriever import graph_retriever

        return graph_retriever.traverse(entity_ids)

    def _get_graph_context_by_semantics(
        self, query_vector: List[float], top_k: int = 3
    ) -> List[str]:
        """Performs a vector search directly on the graph to find entities conceptually similar to the query."""
        if query_vector is None or len(query_vector) == 0:
            return []

        logger.info("Performing Semantic Graph Search...")

        query = """
        MATCH (e:Entity)
        WHERE e.embedding IS NOT NULL
        WITH e, vector.similarity.cosine(e.embedding, $query_vector) AS score
        WHERE score > 0.6
        ORDER BY score DESC
        LIMIT $top_k
        
        // Find immediate relationships for these semantic matches.
        OPTIONAL MATCH (e)-[r]->(t:Entity)
        RETURN e.name AS source, type(r) AS rel, t.name AS target, score
        """
        results = db.query(query, {"query_vector": query_vector, "top_k": top_k})

        context_lines = []
        for r in results:
            if r["rel"] and r["target"]:
                context_lines.append(
                    f"(Semantic Match: {r['source']}) {r['source']} --[{r['rel']}]--> {r['target']}"
                )
            else:
                context_lines.append(
                    f"(Semantic Match) {r['source']} (No outbound relationships)"
                )

        return list(set(context_lines))

    def retrieve(self, query: str) -> str:
        """
        Master method to retrieve and fuse all context.
        """
        logger.info(f"Retrieval Router starting for query: '{query}'")

        # 1.
        lower_query = query.lower()
        global_keywords = [
            "summarize",
            "summarise",
            "all experience",
            "overview",
            "journey",
            "entire",
            "macro",
        ]
        is_global = any(kw in lower_query for kw in global_keywords)

        if is_global:
            logger.info(
                "Query classified as GLOBAL INTENT. Bypassing granular entity traversal..."
            )
            # pyright: ignore [missing-import].
            from src.community_store import community_store

            summaries = community_store.get_community_summaries()

            fused_context = "=== MACRO COMMUNITY SUMMARIES (GLOBAL QUERY) ===\n"
            for i, s in enumerate(summaries):
                fused_context += f"Community Summary {i+1}:\n{s}\n\n"
            return fused_context

        # 2.
        # pyright: ignore [missing-import].
        from src.graph_hybrid_retriever import graph_hybrid_retriever

        fusion_data = graph_hybrid_retriever.retrieve(query, top_k=5)
        texts = fusion_data["texts"]
        graph_links = fusion_data["relationships"]

        # 3.
        query_vector = self._embed_query(query)
        graph_semantics = self._get_graph_context_by_semantics(query_vector)

        # 4.
        all_graph_facts = list(set(graph_links + graph_semantics))
        # pyright: ignore [missing-import].
        from src.context_assembler import context_assembler

        return context_assembler.assemble(
            texts=texts, relationships=all_graph_facts, query=query
        )


# Global instance.
retriever = RetrievalRouter()

