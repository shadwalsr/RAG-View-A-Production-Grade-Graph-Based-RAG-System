import logging
from typing import Any, Dict, List

from src.database import db

logger = logging.getLogger(__name__)

class GraphRetriever:
    """
    Handles optimized 1-hop and 2-hop traversals of the Neo4j Knowledge Graph.
    Extracts structured relationships and gathers all source text chunks associated with the subgraph.
    """
    def __init__(self, default_depth: int = 2):
        self.default_depth = default_depth

    def traverse(self, entity_ids: List[str], depth: int = None) -> Dict[str, Any]:
        """
        Traverses the graph starting from the given entity IDs.
        Returns a formatted list of relationship strings and a set of unique source_chunk_ids.
        """
        if not entity_ids:
            return {"relationships": [], "neighbor_chunks": set()}
            
        search_depth = depth if depth is not None else self.default_depth
        logger.info(f"Traversing graph for {len(entity_ids)} entities at depth {search_depth}...")

        if db.is_dry_run:
            logger.info("[DRY RUN] Mocking Graph Traversal...")
            return {
                "relationships": [f"(Mock) {entity_ids[0]} --[RELATED_TO]--> MockNeighbor"],
                "neighbor_chunks": {"mock_chunk_99"}
            }

        if search_depth == 1:
            return self._traverse_1_hop(entity_ids)
        else:
            return self._traverse_2_hop(entity_ids)

    def _traverse_1_hop(self, entity_ids: List[str]) -> Dict[str, Any]:
        """
        Optimized 1-hop traversal.
        """
        query = """
        MATCH (start:Entity)-[r]-(end:Entity)
        WHERE ANY(n IN $entity_ids WHERE toLower(start.name) CONTAINS toLower(n) OR toLower(n) CONTAINS toLower(start.name)) OR (start.aliases IS NOT NULL AND ANY(alias IN start.aliases WHERE ANY(n IN $entity_ids WHERE toLower(alias) CONTAINS toLower(n) OR toLower(n) CONTAINS toLower(alias))))
        RETURN start.name AS source, type(r) AS rel, end.name AS target, end.source_chunk_ids AS end_chunks
        LIMIT 100
        """
        try:
            results = db.query(query, {"entity_ids": entity_ids})
            
            relationships = []
            neighbor_chunks = set()
            
            for r in results:
                relationships.append(f"{r['source']} --[{r['rel']}]--> {r['target']}")
                if r['end_chunks']:
                    neighbor_chunks.update(r['end_chunks'])
                    
            return {
                "relationships": list(set(relationships)),
                "neighbor_chunks": neighbor_chunks
            }
        except Exception as e:
            logger.error(f"1-hop traversal failed: {e}")
            return {"relationships": [], "neighbor_chunks": set()}

    def _traverse_2_hop(self, entity_ids: List[str]) -> Dict[str, Any]:
        """
        Optimized 2-hop traversal using OPTIONAL MATCH to avoid catastrophic Cartesian expansion.
        """
        query = """
        MATCH (start:Entity)-[r1]-(mid:Entity)
        WHERE ANY(n IN $entity_ids WHERE toLower(start.name) CONTAINS toLower(n) OR toLower(n) CONTAINS toLower(start.name)) OR (start.aliases IS NOT NULL AND ANY(alias IN start.aliases WHERE ANY(n IN $entity_ids WHERE toLower(alias) CONTAINS toLower(n) OR toLower(n) CONTAINS toLower(alias))))
        OPTIONAL MATCH (mid)-[r2]-(end:Entity)
        WHERE elementId(start) <> elementId(end)
        RETURN 
            start.name AS source, 
            type(r1) AS rel1, 
            mid.name AS mid, 
            type(r2) AS rel2, 
            end.name AS end,
            mid.source_chunk_ids AS mid_chunks, 
            end.source_chunk_ids AS end_chunks
        LIMIT 200
        """
        try:
            results = db.query(query, {"entity_ids": entity_ids})
            
            relationships = []
            neighbor_chunks = set()
            
            for r in results:
                # 1st hop.
                relationships.append(f"{r['source']} --[{r['rel1']}]--> {r['mid']}")
                if r['mid_chunks']:
                    neighbor_chunks.update(r['mid_chunks'])
                    
                # 2nd hop.
                if r['rel2'] and r['end']:
                    relationships.append(f"{r['mid']} --[{r['rel2']}]--> {r['end']}")
                    if r['end_chunks']:
                        neighbor_chunks.update(r['end_chunks'])
                    
            return {
                "relationships": list(set(relationships)),
                "neighbor_chunks": neighbor_chunks
            }
        except Exception as e:
            logger.error(f"2-hop traversal failed: {e}")
            return {"relationships": [], "neighbor_chunks": set()}

# Global instance.
graph_retriever = GraphRetriever()

