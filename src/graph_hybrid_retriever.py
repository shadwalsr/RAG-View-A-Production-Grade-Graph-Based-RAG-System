import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from src.graph_retriever import graph_retriever
from src.hybrid_store import hybrid_store
from src.query_linker import query_linker

logger = logging.getLogger(__name__)

class GraphHybridRetriever:
    """
    Executes three parallel retrieval paths (Graph Traversal, Vector Search, BM25 Keyword Search),
    merges all candidate chunk IDs, deduplicates, and applies Reciprocal Rank Fusion (RRF)
    to produce a single, unified, high-quality context ranking.
    """
    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k

    def _get_graph_candidates(self, query: str) -> Dict[str, Any]:
        """Path A: Extracts query entities and performs graph traversal."""
        logger.info("[Path A] Executing Graph Traversal...")
        try:
            query_entities = query_linker.extract_entities(query)
            if not query_entities:
                return {"chunk_ids": [], "relationships": []}
            
            graph_data = graph_retriever.traverse(query_entities)
            # Convert set of neighbor chunks to a list.
            return {
                "chunk_ids": list(graph_data["neighbor_chunks"]),
                "relationships": graph_data["relationships"]
            }
        except Exception as e:
            logger.error(f"[Path A] Graph Traversal failed: {e}")
            return {"chunk_ids": [], "relationships": []}

    def _get_vector_candidates(self, query: str, top_k: int) -> List[str]:
        """Path B: Semantic vector search on ChromaDB."""
        logger.info("[Path B] Executing Vector Search...")
        try:
            v_results = hybrid_store.vector_search(query, top_k=top_k)
            return [res["id"] for res in v_results]
        except Exception as e:
            logger.error(f"[Path B] Vector Search failed: {e}")
            return []

    def _get_bm25_candidates(self, query: str, top_k: int) -> List[str]:
        """Path C: Lexical keyword search on BM25."""
        logger.info("[Path C] Executing BM25 Keyword Search...")
        try:
            k_results = hybrid_store.keyword_search(query, top_k=top_k)
            return [res["id"] for res in k_results]
        except Exception as e:
            logger.error(f"[Path C] BM25 Search failed: {e}")
            return []

    def compute_rrf(self, ranked_lists: List[List[str]]) -> List[str]:
        """
        Applies Reciprocal Rank Fusion (RRF) across multiple ranked lists of chunk IDs.
        Formula: RRF_Score(d) = sum(1 / (k + rank(d)))
        """
        rrf_scores: Dict[str, float] = {}

        for r_list in ranked_lists:
            for rank_idx, chunk_id in enumerate(r_list):
                # rank is 1-based.
                rank = rank_idx + 1
                score = 1.0 / (self.rrf_k + rank)
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score

        # Sort chunk IDs descending by RRF score.
        sorted_chunks = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
        return [chunk_id for chunk_id, score in sorted_chunks]

    def retrieve(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Master method to run parallel retrieval, fuse via RRF, and assemble context.
        """
        logger.info(f"GraphHybridRetriever starting parallel fusion for query: '{query}'")

        # Run 3 paths in parallel.
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_graph = executor.submit(self._get_graph_candidates, query)
            future_vector = executor.submit(self._get_vector_candidates, query, top_k * 2)
            future_bm25 = executor.submit(self._get_bm25_candidates, query, top_k * 2)

            try:
                graph_data = future_graph.result(timeout=10)
            except Exception as e:
                logger.error(f"[Path A] Timeout/Error in Graph Traversal: {e}")
                graph_data = {"chunk_ids": [], "relationships": []}

            try:
                vector_ids = future_vector.result(timeout=10)
            except Exception as e:
                logger.error(f"[Path B] Timeout/Error in Vector Search (ChromaDB ONNX download): {e}")
                vector_ids = []

            try:
                bm25_ids = future_bm25.result(timeout=10)
            except Exception as e:
                logger.error(f"[Path C] Timeout/Error in BM25 Search: {e}")
                bm25_ids = []

        # Combine ranked lists.
        ranked_lists = [graph_data["chunk_ids"], vector_ids, bm25_ids]
        
        # Apply RRF.
        fused_chunk_ids = self.compute_rrf(ranked_lists)
        final_top_chunks = fused_chunk_ids[:top_k]
        
        logger.info(f"RRF Fusion complete. Merged {len(fused_chunk_ids)} unique chunks down to top {len(final_top_chunks)}.")

        # Fetch actual text content for the top RRF chunks.
        chunk_texts = []
        for cid in final_top_chunks:
            text = hybrid_store.get_chunk_by_id(cid)
            if text:
                chunk_texts.append(text)

        return {
            "texts": chunk_texts,
            "relationships": graph_data["relationships"]
        }

# Global instance.
graph_hybrid_retriever = GraphHybridRetriever()

