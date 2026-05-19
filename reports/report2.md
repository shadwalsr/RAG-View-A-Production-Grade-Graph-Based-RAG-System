# Report 2: Intelligence Engine and Graph Ingestion

**Author:** Shadwal Singh  

---

## 1. Executive Summary

With the foundation established, we have now implemented the "brain" of **RAG-View**. This phase focused on building a high-fidelity intelligence engine that transforms raw, unstructured text into validated, interconnected graph data. By integrating **Gemini 2.0 Flash** with a strict **Pydantic** validation layer and an idempotent **Neo4j** ingestion pipeline, we have achieved a system that not only extracts information but maintains full provenance for every data point.

---

## 2. The Intelligence Engine (`extractor.py`)

The extraction pipeline is the quality ceiling of the entire system. We opted for **Gemini 2.0 Flash** due to its exceptional balance of speed and reasoning capabilities for structured JSON tasks.

- **Low-Temperature Extraction**: We configured the model with `temperature=0.1` to ensure deterministic, reproducible outputs.
- **Structured Contracts**: We defined strict Pydantic models (`Entity`, `Relationship`, `ExtractionResult`) that serve as a contract between the LLM and the database. This prevents "schema drift" and ensures that every node and edge in our graph follows our domain ontology (PERSON, ORG, SKILL, etc.).
- **Hallucination Mitigation**: The extractor includes post-processing logic to ensure that relationships only connect entities that were actually extracted in the same context, effectively pruning common LLM "hallucinated links."

---

## 3. Resilience and API Stability

Production-grade RAG systems must handle API instability gracefully. We implemented a robust **Exponential Backoff** strategy:
- The system automatically detects **429 (Resource Exhausted)** and **5xx (Server Error)** responses.
- It retries with increasing delays, allowing the system to handle high-concurrency document processing without crashing or losing data.

---

## 4. Graph Ingestion and Full Provenance (`graph_store.py`)

The transition from a flat list of entities to an interconnected graph happens in the ingestion layer. Our implementation focuses on two critical principles:

- **Idempotent MERGE Operations**: We use Cypher `MERGE` clauses to ensure that even if the same entity (e.g., "Neo4j") is mentioned across 100 different document chunks, it exists as a single, canonical node in our graph.
- **Provenenance Tracking (`source_chunk_ids`)**: Unlike traditional RAG systems that lose context after extraction, RAG-View attaches the source chunk ID to every node and relationship. This creates a "traceable graph," where every edge can be clicked to reveal the exact paragraph that justified its existence.

---

## 5. Verification and Scale Testing

We established an automated integration test suite (`tests/test_graph_ingestion.py`) that simulates multi-chunk ingestion. 
- **Tests Performed**: Deduplication checks, provenance array validation, and relationship consistency.
- **Result**: Confirmed that overlapping entities are correctly merged while their source IDs are appended, maintaining a complete "knowledge audit trail."

---

## 6. Conclusion: From Graph to Intelligence

RAG-View is no longer just a database; it is an active knowledge processor. The system can now ingest raw documents and construct a verifiable knowledge graph autonomously.

**Status:** Ingestion Pipeline Operational.  
**Next Objective:** Implementation of **Hybrid Retrieval** (Vector + Graph) and the interactive visual canvas.
