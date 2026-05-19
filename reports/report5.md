# Report 5: Graph Entity Embeddings


---

## 1. Executive Summary

We have successfully enhanced the Neo4j Knowledge Graph by introducing semantic embeddings directly into the graph structure. By computing and storing 768-dimensional vector representations for every extracted entity, the RAG-View platform is now capable of performing semantic search queries against the graph itself, bridging the gap between exact-match node properties and nuanced, meaning-based entity retrieval.

---

## 2. The Entity Embedder Architecture

To handle the generation and storage of these embeddings, we built a dedicated service (`src/embedder.py`).

### Workflow Mechanics
1. **Delta Processing**: The `EntityEmbedder` runs a highly efficient Cypher query (`MATCH (e:Entity) WHERE e.embedding IS NULL`) to only select newly created entities. This ensures we don't waste API quota re-embedding older entities.
2. **Semantic Context**: For each entity, a context string is synthesized using the format `"{Entity Name}: {Entity Description}"`. This maximizes the semantic richness fed to the embedding model.
3. **Batch Generation**: The system batches entities (default size: 50) and calls the Gemini API (`text-embedding-004`), retrieving an array of 768-dimensional floats for each entity in the batch.
4. **Optimized Upsertion**: To ensure high throughput when writing back to the database, the embedder utilizes Neo4j's `UNWIND` capability to update the entire batch of entities in a single, fast transaction.

---

## 3. Pipeline Orchestration

The graph embedding process is not meant to be run manually. It has been fully integrated into the core `RAGPipeline` orchestrator (`src/pipeline.py`).

**The Updated Ingestion Flow:**
1. Text is Chunked.
2. Gemini Extracts Entities/Relationships (Upserted to Neo4j).
3. Raw chunks are saved to the HybridStore (Vector/BM25) with linked `entity_ids`.
4. **[NEW]** The Pipeline triggers the `EntityEmbedder` to generate vectors for any *new* entities discovered in step 2.

This guarantees that our graph's vector space is always perfectly synchronized with the underlying data immediately following an ingestion cycle.

---

## 4. Verification & Resilience

- **Dry Run Capabilities**: Built-in support for `$env:DRY_RUN="true"` ensures developers can test the embedding logic and batch query formation without expending Gemini API tokens or requiring an active Neo4j connection.
- **Automated Testing**: Created `tests/test_graph_embeddings.py` to mock database interactions and validate that the logic correctly isolates un-embedded nodes, generates proper batches, and successfully completes the pipeline lifecycle.

---

## Conclusion & Next Steps

With the text chunks now residing in a persistent HybridStore and the Graph Entities enhanced with semantic vectors, the underlying storage infrastructure for Phase 2 is complete. 

We are fully prepared to build the **Retrieval Router**, which will accept a user's natural language question, convert it into an embedding, and traverse these stores to assemble the ultimate, contextually enriched prompt.
