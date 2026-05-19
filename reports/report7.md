# Report 7: Advanced GraphRAG Retrieval Architecture


---

## 1. Executive Summary

Following the completion of the foundational ingestion, deduplication, and basic routing engines documented in Report 6, our focus shifted entirely to **Phase 3: Advanced GraphRAG Retrieval**. We successfully implemented the two core pillars that differentiate our system from traditional "Flat RAG" architectures: **Query Entity Extraction** and **Multi-Hop Subgraph Traversal**. These systems work in tandem to guarantee deep, multi-dimensional contextual grounding for the LLM.

---

## 2. Query Entity Extraction (`src/query_linker.py`)

In standard RAG, if a user asks a question whose exact phrasing fails to trigger a vector match in the text store, the system fails. We eliminated this vulnerability by creating the `QueryEntityLinker`.

- **Active Interception**: Before any database lookup occurs, the incoming natural language query is passed to `gemini-2.0-flash` with a strict, zero-temperature system prompt.
- **Structured JSON Output**: The LLM extracts all named entities, proper nouns, and core concepts, returning them strictly as a valid JSON array of strings (e.g., `"What did Shadwal build at WhySchool?"` -> `["Shadwal", "WhySchool"]`).
- **Guaranteed Entry Points**: These extracted entities are injected directly into the `RetrievalRouter`, ensuring that even if the vector text search returns zero chunks, the system still possesses explicit entry points to traverse the Knowledge Graph.
- **Resilience**: Implemented a robust `DRY_RUN` mocking mechanism to ensure development and testing continue flawlessly despite Gemini Free Tier API rate limits (`429 RESOURCE_EXHAUSTED`).

---

## 3. Multi-Hop Subgraph Traversal (`src/graph_retriever.py`)

We replaced our rudimentary 1-hop graph lookup with a dedicated, highly optimized `GraphRetriever` engine capable of deep structural exploration.

- **Optimized Cypher Execution**: Naively executing variable-length path queries (`[*1..2]`) in Neo4j risks massive Cartesian explosions when encountering highly connected "supernodes." We engineered explicit, bounded Cypher queries utilizing `OPTIONAL MATCH` blocks (`start -[r1]- mid OPTIONAL MATCH mid -[r2]- end`) to safely pull 2-hop neighborhoods without compromising database memory or performance.
- **Configurable Depth**: The engine supports dynamic toggling between `depth=1` (for hyper-focused precision) and `depth=2` (for broad conceptual discovery).
- **Provenance Harvesting**: Crucially, as the query traverses the graph, it harvests the `source_chunk_ids` of every neighboring entity discovered along the path.

---

## 4. The Complete Grounding Loop (`src/retriever.py` & `src/hybrid_store.py`)

We updated the `RetrievalRouter` and `HybridStore` to achieve the ultimate RAG grounding loop:

1. **Entity Aggregation**: The router combines entities extracted from the query with those discovered in the metadata of vector-matched text chunks.
2. **Subgraph Retrieval**: It passes this comprehensive list to the `GraphRetriever`, which returns structured relationship strings (`A -> B -> C`) and a massive set of neighboring `source_chunk_ids`.
3. **Neighbor Text Fetching**: We added a `get_chunk_by_id()` method to the `HybridStore`. The router iterates over the neighboring chunk IDs, pulls their original raw text excerpts from disk/ChromaDB, and injects them into the final LLM prompt under a dedicated header: `(Graph Neighbor Context)`.

---

## 5. Verification & Testing

Both major additions were rigorously tested using dedicated simulation scripts:
- **`tests/demo_phase3.py`**: Proved that when text vector search is intentionally forced to return zero chunks, the `QueryEntityLinker` successfully bridges the gap, allowing the system to pull accurate graph relationships (`WhySchool --[FOCUSES_ON]--> Education`).
- **`tests/test_graph_retriever.py`**: Validated 2-hop traversal logic (`WhySchool -> Shadwal -> San Francisco`) and confirmed successful extraction of distant neighbor text chunks (`chunk_shadwal_bio`, `chunk_sf_info`).

---

## Next Steps

With Query Entity Extraction and Multi-Hop Traversal fully operational, the core retrieval engine is complete. Our next objective in Phase 3 is implementing advanced re-ranking and context pruning mechanisms to ensure our expanded context windows remain highly relevant and performant.
