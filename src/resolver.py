import logging
import os
import json
from google import genai
from collections import defaultdict
from typing import Any, Dict, List, Set

from src.database import db

logger = logging.getLogger(__name__)


class EntityResolver:
    """
    Identifies and merges duplicate or highly similar entities in the Neo4j Graph.
    Uses cosine similarity on the Gemini embeddings.
    """

    def __init__(self, similarity_threshold: float = 0.92):
        self.similarity_threshold = similarity_threshold
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")) if os.getenv("GEMINI_API_KEY") else None


    def _verify_with_llm(self, ent1: Dict[str, Any], ent2: Dict[str, Any]) -> bool:
        """
        Uses an LLM judge to verify if two similar entities are indeed the same real-world entity.
        """
        if not self.client:
            logger.warning("LLM client not initialized (GEMINI_API_KEY may be missing). Falling back to True.")
            return True

        prompt = f"""You are a precise Entity Resolution system. Decide whether the following two entities represent the EXACT SAME real-world entity.

Entity 1:
- Name: {ent1.get('name')}
- Type: {ent1.get('type')}
- Description: {ent1.get('description')}

Entity 2:
- Name: {ent2.get('name')}
- Type: {ent2.get('type')}
- Description: {ent2.get('description')}

Provide your response in a professional JSON format exactly like this:
{{
  "same_entity": true or false,
  "reason": "Explain your decision clearly and concisely based on entity types, names, and descriptions."
}}
"""
        try:
            from google.genai import types
            
            def _call():
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=1024,
                        response_mime_type="application/json"
                    )
                )
                return response.text

            from src.extractor import _retry_with_backoff
            raw_response = _retry_with_backoff(_call)
            
            # Clean response just in case
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                first_newline = cleaned.index("\n")
                cleaned = cleaned[first_newline + 1 :]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            same_entity = data.get("same_entity", True)
            reason = data.get("reason", "")
            logger.info(f"LLM Judge result for '{ent1.get('name')}' vs '{ent2.get('name')}': {same_entity} (Reason: {reason})")
            return bool(same_entity)
        except Exception as e:
            logger.error(f"LLM Judge verification failed: {e}. Falling back to True.")
            return True

    def _find_similar_pairs(self) -> List[Dict[str, Any]]:
        """
        Finds pairs of entities with cosine similarity above the threshold.
        """
        if db.is_dry_run:
            logger.info("[DRY RUN] Simulating similarity search...")
            return []

        # Using built-in vector similarity function (Neo4j 5+).
        # We compare e1 and e2 where id(e1) < id(e2) to avoid duplicate pairs and self-mat.
        query = """
        MATCH (e1:Entity), (e2:Entity)
        WHERE id(e1) < id(e2) AND e1.embedding IS NOT NULL AND e2.embedding IS NOT NULL
        WITH e1, e2, vector.similarity.cosine(e1.embedding, e2.embedding) AS score
        WHERE score >= $threshold
        RETURN e1.id AS id1, e1.name AS name1, e1.type AS type1, e1.description AS description1,
               e2.id AS id2, e2.name AS name2, e2.type AS type2, e2.description AS description2,
               score
        """
        try:
            results = db.query(query, {"threshold": self.similarity_threshold})
            pairs = []
            for r in results:
                ent1 = {"id": r["id1"], "name": r["name1"], "type": r["type1"], "description": r["description1"]}
                ent2 = {"id": r["id2"], "name": r["name2"], "type": r["type2"], "description": r["description2"]}
                if self._verify_with_llm(ent1, ent2):
                    pairs.append({"id1": r["id1"], "id2": r["id2"], "score": r["score"]})
            return pairs
        except Exception as e:
            logger.error(f"Failed to find similar pairs: {e}")
            return []


    def _build_clusters(self, pairs: List[Dict[str, Any]]) -> List[Set[str]]:
        """
        Groups connected pairs into clusters (Connected Components).
        """
        adj = defaultdict(set)
        for p in pairs:
            adj[p["id1"]].add(p["id2"])
            adj[p["id2"]].add(p["id1"])

        visited = set()
        clusters = []

        for node in list(adj.keys()):
            if node not in visited:
                # BFS/DFS to find component.
                comp = set()
                stack = [node]
                while stack:
                    curr = stack.pop()
                    if curr not in visited:
                        visited.add(curr)
                        comp.add(curr)
                        stack.extend(adj[curr] - visited)
                clusters.append(comp)

        return clusters

    def _merge_cluster(self, cluster: Set[str]):
        """
        Merges a cluster of entity IDs into a single canonical node in Neo4j.
        """
        if db.is_dry_run:
            logger.info(
                f"[DRY RUN] Would merge cluster of {len(cluster)} entities: {cluster}"
            )
            return

        cluster_list = list(cluster)

        # We use a complex Cypher transaction to safely merge nodes.
        # 1.
        # 2.
        # 3.
        # 4.
        # 5.

        # Because rewiring generic relationships safely in pure Cypher without knowing the.
        # types dynamically is extremely complex (Neo4j does not support dynamic relations.
        # the standard practice is to use apoc.

        apoc_query = """
        MATCH (e:Entity)
        WHERE e.id IN $cluster_ids
        WITH e
        ORDER BY size(e.source_chunk_ids) DESC, e.id ASC
        WITH collect(e) AS nodes
        CALL apoc.refactor.mergeNodes(nodes, {
            properties: {
                name: 'discard', // keep canonical name
                id: 'discard',
                type: 'discard',
                description: 'discard',
                embedding: 'discard',
                source_chunk_ids: 'combine',
                aliases: 'combine'
            },
            mergeRels: true
        }) YIELD node
        
        // Deduplicate the combined source_chunk_ids arrays and initialize aliases if neede.
        WITH node
        UNWIND node.source_chunk_ids AS chunk_id
        WITH node, collect(DISTINCT chunk_id) AS deduped_chunks
        SET node.source_chunk_ids = deduped_chunks
        // We will add logic in Python to handle the aliases since apoc.
        RETURN node.id AS merged_id
        """

        # A safer python-driven approach that doesn't strictly require APOC:.
        # We can do this in steps from Python:.
        # 1.
        # 2.
        # 3.
        # 4.

        # Since RAG systems often require APOC, we will attempt the APOC query first.
        # If it fails, we fall back to a simpler pure cypher just for the properties,.
        # assuming basic relationships can be rebuilt or are redundant.

        try:
            db.query(apoc_query, {"cluster_ids": cluster_list})
            logger.info(
                f"Merged cluster of {len(cluster)} entities into canonical root."
            )
        except Exception as e:
            logger.warning(
                f"APOC merge failed (APOC might not be installed). Using Python-driven fallback. {e}"
            )
            self._fallback_merge(cluster_list)

    def _fallback_merge(self, cluster_ids: List[str]):
        """Fallback merge logic if APOC is not installed."""
        # 1.
        q_canonical = """
        MATCH (e:Entity)
        WHERE e.id IN $cluster_ids
        RETURN e.id AS id, e.name AS name, e.source_chunk_ids AS chunks
        ORDER BY size(e.source_chunk_ids) DESC
        """
        res = db.query(q_canonical, {"cluster_ids": cluster_ids})
        if not res:
            return

        canonical_id = res[0]["id"]
        duplicates = [r for r in res if r["id"] != canonical_id]
        dup_ids = [d["id"] for d in duplicates]

        if not dup_ids:
            return

        # 2.
        new_aliases = [d["name"] for d in duplicates]
        all_chunks = set(res[0]["chunks"] or [])
        for d in duplicates:
            all_chunks.update(d["chunks"] or [])

        # 3.
        q_update = """
        MATCH (e:Entity {id: $canonical_id})
        SET e.aliases = coalesce(e.aliases, []) + $new_aliases
        SET e.source_chunk_ids = $all_chunks
        """
        db.query(
            q_update,
            {
                "canonical_id": canonical_id,
                "new_aliases": new_aliases,
                "all_chunks": list(all_chunks),
            },
        )

        # 4.
        # For a generic RAG, we might have multiple types.
        q_rels = "MATCH (d:Entity)-[r]->(t) WHERE d.id IN $dup_ids RETURN d.id as dup, type(r) as r_type, t.id as target"
        rels = db.query(q_rels, {"dup_ids": dup_ids})
        for rel in rels:
            q_rewire = f"""
            MATCH (c:Entity {{id: $canonical_id}}), (t {{id: $target_id}})
            MERGE (c)-[:{rel['r_type']}]->(t)
            """
            db.query(
                q_rewire, {"canonical_id": canonical_id, "target_id": rel["target"]}
            )

        q_rels_in = "MATCH (s)-[r]->(d:Entity) WHERE d.id IN $dup_ids RETURN s.id as source, type(r) as r_type, d.id as dup"
        rels_in = db.query(q_rels_in, {"dup_ids": dup_ids})
        for rel in rels_in:
            q_rewire = f"""
            MATCH (s {{id: $source_id}}), (c:Entity {{id: $canonical_id}})
            MERGE (s)-[:{rel['r_type']}]->(c)
            """
            db.query(
                q_rewire, {"source_id": rel["source"], "canonical_id": canonical_id}
            )

        # 5.
        q_delete = "MATCH (d:Entity) WHERE d.id IN $dup_ids DETACH DELETE d"
        db.query(q_delete, {"dup_ids": dup_ids})

        logger.info(
            f"Merged {len(dup_ids)} duplicates into canonical entity '{canonical_id}' via fallback."
        )

    def run(self):
        """
        Executes the entity resolution pipeline.
        """
        logger.info("Starting Entity Resolution Pass...")
        pairs = self._find_similar_pairs()

        if not pairs:
            logger.info("No highly similar entity pairs found.")
            return

        logger.info(
            f"Found {len(pairs)} pairs of highly similar entities (cosine > {self.similarity_threshold})."
        )

        clusters = self._build_clusters(pairs)
        logger.info(f"Grouped into {len(clusters)} clusters for merging.")

        for idx, cluster in enumerate(clusters):
            self._merge_cluster(cluster)

        logger.info("Entity Resolution Pass Complete.")


# Global instance.
resolver = EntityResolver()

