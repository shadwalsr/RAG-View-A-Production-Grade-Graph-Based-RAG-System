# Report 4: Hybrid Storage Layer Implementation


---

## 1. Executive Summary

We have successfully expanded the RAG-View architecture by introducing a **Hybrid Storage Layer** (`HybridStore`). This component integrates persistent vector search capabilities (ChromaDB) alongside lexical keyword search (BM25). Most importantly, this layer bridges the gap between unstructured text chunks and the structured Neo4j Knowledge Graph by embedding extracted `entity_ids` directly into the metadata of the stored vectors.

---

## 2. Architectural Additions

### ChromaDB (Vector Store)
- **Implementation**: Utilized `chromadb.PersistentClient` saving data to `./data/chroma`.
- **Functionality**: Provides out-of-the-box text embedding generation (via `all-MiniLM-L6-v2`) and dense vector similarity search, enabling the system to retrieve context based on semantic meaning rather than exact phrasing.

### BM25 (Keyword Store)
- **Implementation**: Utilized `rank_bm25` for lexical matching. Since BM25 operates entirely in-memory, we implemented an automated persistence mechanism using Python's `pickle` library, saving the index state to `./data/bm25_index.pkl`.
- **Functionality**: Ensures that highly specific domain terms or exact name matches are not missed by the dense vector search, a common failure mode in standard RAG systems.

---

## 3. The Knowledge Graph Bridge

The critical innovation in this phase is the architectural link established between the flat text stores and the graph database.

1.  **Extraction Pipeline**: During ingestion (`RAGPipeline`), raw text is passed to the Gemini LLM to extract entities and relationships.
2.  **Metadata Tagging**: The canonical names (IDs) of these extracted entities are collected into an `entity_ids` list.
3.  **Storage**: This list is serialized into JSON and stored as metadata alongside the text chunk in both ChromaDB and the BM25 corpus.

**Result**: When a user queries the system, we can now retrieve relevant text chunks (via vector/keyword search), instantly read the attached `entity_ids`, and immediately perform targeted graph traversals in Neo4j without needing to re-process the text.

---

## 4. Verification

-   **Integration Tests**: Created `tests/test_hybrid_store.py` to simulate chunk ingestion and hybrid retrieval.
-   **Validation**: The test successfully confirmed that chunks are correctly indexed by both engines, and that the `entity_ids` metadata is perfectly preserved and deserialized upon retrieval.
-   **Data Privacy**: Removed hardcoded personal identifiers from demo scripts to maintain clean, professional repository standards.

---

## Next Steps

With the foundation of Phase 2 laid, the next objective is to build the **Retrieval Router**. This router will orchestrate incoming user queries, distribute them to the HybridStore and Neo4j, and fuse the results (Vector + Lexical + Graph Context) into a single, highly enriched context window for the final LLM response generation.
