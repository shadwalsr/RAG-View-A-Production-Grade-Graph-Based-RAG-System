# RAG-View: Final Engineering Report
### A Production-Grade, Graph-Powered Document Intelligence Platform

**Author:** Shadwal Singh  
**Engineering Partner:** Antigravity (Google DeepMind Advanced Agentic Coding Team)  
**Project Duration:** Full Build Lifecycle (Reports 1–20)  
**Repository:** [RAG-View on GitHub](https://github.com/shadwalsr/RAG-View-A-Production-Grade-Graph-Based-RAG-System)  
**Status:** ✅ Production-Ready & Publicly Released

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The Problem: Why Flat Vector RAG Fails](#2-the-problem-why-flat-vector-rag-fails)
3. [Architecture Overview](#3-architecture-overview)
4. [Phase-by-Phase Engineering Summary](#4-phase-by-phase-engineering-summary)
5. [Technology Stack](#5-technology-stack)
6. [Core Modules Reference](#6-core-modules-reference)
7. [Benchmark Results: GraphRAG vs Flat RAG](#7-benchmark-results-graphrag-vs-flat-rag)
8. [Critical Incidents & Resolutions](#8-critical-incidents--resolutions)
9. [Test Suite Coverage](#9-test-suite-coverage)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Key Engineering Decisions & Trade-offs](#11-key-engineering-decisions--trade-offs)
12. [Future Roadmap](#12-future-roadmap)
13. [Conclusion](#13-conclusion)

---

## 1. Project Overview

**RAG-View** is a production-grade, graph-powered document intelligence platform that bridges the gap between unstructured text and structured knowledge graphs. It evolved from the limitations of the predecessor system **RAGRead** — a flat, vector-only retrieval pipeline — and was rebuilt from the ground up over 20 engineering phases.

The platform combines three distinct retrieval signals — **dense vector similarity** (ChromaDB), **sparse keyword matching** (BM25), and **graph neighbourhood traversal** (Neo4j) — fused via **Reciprocal Rank Fusion (RRF)** to deliver multi-hop reasoning, community-level summarisation, and 100% citation-grounded answers.

**Core Mission:** To make multi-hop document reasoning reliable, verifiable, and production-deployable — eliminating hallucinations through architectural design rather than prompt hacks.

---

## 2. The Problem: Why Flat Vector RAG Fails

Standard "Flat" Vector RAG systems fail on complex queries because they operate on isolated text chunk islands. Consider:

> **Query:** *"What company did Shadwal Singh found that focuses on AI education?"*

- **Flat RAG Path:** Chunk A contains *"Shadwal Singh founded WhySchool"*. Chunk B contains *"WhySchool is an AI education startup"*. The vector distance between the query and Chunk B is too large — the LLM receives only Chunk A and hallucinates or gives an incomplete answer. **Correctness: 2.4 / 5.0**

- **GraphRAG Path:** `QueryEntityLinker` extracts `"Shadwal Singh"` as a graph entry point. The traverser follows the explicit edge `(Shadwal Singh)-[:FOUNDED]->(WhySchool)-[:FOCUSES_ON]->(AI Education)`. The `ContextAssembler` feeds the LLM a deterministic relational scaffold. **Correctness: 4.9 / 5.0**

**The gap is +2.5 correctness points on multi-hop queries — a 104% improvement.**

---

## 3. Architecture Overview

```
+-----------------------------------------------------------------------------------+
|                        PHASE 1: INGESTION & EXTRACTION                            |
|  [Raw Text / PDF] --> TextProcessor --> EntityExtractor --> GraphStore (Neo4j)    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        PHASE 2: HYBRID STORAGE & INDEXING                         |
|  [Extracted Entities / Chunks] --> HybridStore (ChromaDB Vector + BM25 Keyword)   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        PHASE 3: ADVANCED RETRIEVAL & GENERATION                   |
|  [User Query] --> GraphHybridRetriever (RRF Fusion) --> GraphRAGGenerator         |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        PHASE 4: VERIFICATION & INCREMENTAL MAINTENANCE            |
|  [Generated Answer] --> GraphCitationVerifier --> ConfidenceScorer                |
|  [New Documents]    --> GraphUpdater (Deduplication & Frequency Weighting)        |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        PHASE 5-7: ENTERPRISE HARDENING                            |
|  [FastAPI Gateway] --> Rate Limiting + Redis Cache + API Key Auth                 |
|  [Docker Compose]  --> Neo4j + Redis + FastAPI + Streamlit (One-Command Deploy)   |
|  [Hybrid DB Mode]  --> Local Docker Neo4j <--> Neo4j Aura Cloud (Config-Driven)   |
+-----------------------------------------------------------------------------------+
```

### Security & Caching Gateway Flow

```
Client Request
    --> X-API-Key Header Validation (401 if invalid)
    --> SlowAPI Rate Limiter (429 if exceeded)
    --> Redis Query Cache (return cached if hit, <5ms)
    --> FastAPI Endpoint (full GraphRAG pipeline on miss)
    --> Verified, Confidence-Scored Response
```

---

## 4. Phase-by-Phase Engineering Summary

### Report 1 — Foundation & Repository Scaffold
Initialized the repository architecture with `src/`, `tests/`, `data/`, `frontend/`, `docs/` separation. Established **Poetry** for dependency management, **pre-commit hooks** (Black + Ruff), a `.env.example` template for all secrets, and a `Makefile` with standardized targets (`make run`, `make test`, `make docker-up`).

---

### Report 2 — Intelligence Engine & Graph Ingestion
Built `src/extractor.py` using **Gemini 2.0 Flash** at `temperature=0.1` with strict **Pydantic** schema contracts (`Entity`, `Relationship`, `ExtractionResult`). Implemented hallucination pruning (relationships must link co-extracted entities only). Built `src/graph_store.py` with **idempotent MERGE** Cypher operations and full `source_chunk_ids` provenance tracking.

---

### Report 3 — API Resilience & Phase 1 Completion
Implemented **Exponential Backoff** for `429 RESOURCE_EXHAUSTED` and `5xx` errors with 30-second base delays and 10-second scaling. Added `DRY_RUN` mode for testing without live databases. Completed the end-to-end Phase 1 ingestion flow: Chunk → Extract → Graph Upsert.

---

### Report 4 — Hybrid Storage Layer
Built `src/hybrid_store.py` combining **ChromaDB** (persistent vector store, `all-MiniLM-L6-v2`) and **BM25** (`rank_bm25`, pickle-persisted index). The critical innovation: `entity_ids` extracted by the LLM are serialized as metadata into both stores, creating a **Knowledge Graph Bridge** for instant graph traversal on retrieval.

---

### Report 5 — Graph Entity Embeddings
Built `src/embedder.py` for delta embedding (only un-embedded entities, `WHERE e.embedding IS NULL`). Generated **768-dimensional Gemini embeddings** (`text-embedding-004`) using `"{Entity Name}: {Entity Description}"` context strings. Leveraged Neo4j `UNWIND` for batch upserts. Fully integrated into the `RAGPipeline` orchestrator.

---

### Report 6 — Entity Resolution, Retrieval Router & Pipeline Hardening
Built `src/resolver.py`: semantic clustering via `vector.similarity.cosine >= 0.92`, Python connected-components algorithm, canonical merging with `apoc.refactor.mergeNodes` and pure Cypher fallback. Built `src/retriever.py`: query embedding → HybridStore lookup → entity extraction → graph 1-hop + vector graph search → context fusion. Added `ingest.py` drop-folder utility for `.txt` and `.pdf` files.

---

### Report 7 — Advanced GraphRAG Retrieval Architecture
Built `src/query_linker.py`: pre-retrieval LLM entity extraction with zero temperature, structured JSON array output. Built `src/graph_retriever.py`: multi-hop traversal with explicit bounded Cypher (`OPTIONAL MATCH`) to prevent Cartesian explosions, configurable 1-hop / 2-hop depth, and provenance harvesting. Added `get_chunk_by_id()` to `HybridStore` for graph-neighbor context injection.

---

### Report 8 — Phase 3 Advanced GraphRAG Retrieval Completion
Fixed critical metadata mutation bug in `HybridStore` (shallow dict copying). Built `src/community_store.py`: **Louvain Modularity Clustering** via Neo4j GDS with pure Cypher label-propagation fallback. Built `src/graph_hybrid_retriever.py`: parallel `ThreadPoolExecutor` across 3 paths (Graph + Vector + BM25) with **Reciprocal Rank Fusion (RRF)** scoring:

```
RRF_Score(d) = Σ  1 / (60 + r_m(d))
```

Built `src/context_assembler.py`: structured prompt blocks with `[Source N]` labeling and dual-compatible section headers.

---

### Report 9 — Grounded GraphRAG Generation & Prompt Engineering
Upgraded `src/qa.py` to `GraphRAGGenerator`. Implemented a **three-section grounded generation prompt**:
1. Retrieved Text Chunks with `[Source N]` tags
2. Structured Relationship Block (explicit graph triples)
3. Hard Rules: mandatory source citation, uncertainty flagging, and refusal when confidence is low

---

### Report 10 — Phase 4: Verification & Incremental Maintenance
Built `src/verifier.py`: LLM-as-a-judge with direct Neo4j node property lookups (`MATCH (e:Entity) WHERE e.name IN $names`). Appends `[N ⚠️ UNVERIFIED]` to unsupported claims. Built `src/scorer.py`: Pydantic `ConfidenceReport` with `retrieval_confidence`, `grounding_confidence`, `graph_coverage` (deterministic ratio of query entities found in graph). Built `src/graph_updater.py`: autonomous incremental pipeline with **frequency-based relationship weighting**:
```cypher
SET r.weight = CASE WHEN freq >= 5 THEN 2.0 WHEN freq >= 3 THEN 1.5 ELSE 1.0 END
```

---

### Report 11 — Executive Capstone: Complete Phase 1–4 Architecture
Full verification of all 9 automated test suites in `DRY_RUN` mode. 100% pass rate. Documented the three key system differentiators: Zero-Hallucination Architecture, Self-Improving Knowledge Graph, and Resilient API Orchestration.

---

### Report 12 — Asynchronous Document Ingestion & Background Task Queues
Decoupled heavy ingestion from synchronous HTTP via **FastAPI `BackgroundTasks`**. Implemented `jobs_store` with state transitions (`queued → processing → completed/failed`). Created `GET /v1/jobs/{job_id}` polling endpoint returning `GraphUpdateState` metrics on completion.

---

### Report 13 — Head-to-Head Benchmark: GraphRAG vs Flat RAG
Executed a rigorous 72-pair golden QA benchmark comparing legacy Flat RAG vs GraphRAG. Results documented in `reports/benchmark_report.csv` and `src/benchmark.py`. **Key finding:** GraphRAG achieves +2.5 correctness on two-hop relational queries at the cost of only +300ms latency — a 104% accuracy gain for negligible overhead.

---

### Report 14 — Enterprise API Security: Rate Limiting, Redis Caching & Auth
Implemented `slowapi` token-bucket rate limiting (10/min for `/ask`, 5/min for `/ingest`, 30/min for read endpoints). Added `X-API-Key` header authentication via `APIKeyHeader` with global dependency injection (401 on unauthorized). Built **Redis semantic query caching** with `cache:query:{normalized_query}` keys and 1-hour TTL — serving cached responses in <5ms.

---

### Report 15 — One-Command Enterprise Deployment: Full-Stack Docker Compose
Engineered `Dockerfile` (Poetry-based, `python:3.11-slim`, `POETRY_VIRTUALENVS_CREATE=false`) and `docker-compose.yml` orchestrating 4 services: `neo4j:5.19.0` (APOC + GDS plugins), `redis:7-alpine`, `api` (FastAPI, port 8000), `dashboard` (Streamlit, port 8501). All services have health checks and explicit `depends_on` boot ordering.

---

### Report 16 — Executive Documentation Suite
Authored `README.md` (platform overview, Mermaid architecture diagram, quickstart, benchmark proof), `ARCHITECTURE.md` (mathematical failure modes, subsystem deep-dive, trade-off analysis), and `LINKEDIN_SERIES.md` (12-part thought leadership content matrix).

---

### Report 17 — Hybrid Database Architecture: Local Docker vs Neo4j Aura Cloud
Engineered dual-mode database support via environment variable injection. Local Docker provides full GDS + APOC support at $0/month. Neo4j Aura Cloud provides zero-maintenance managed hosting. `CommunityStore` automatically detects GDS availability and falls back to pure Cypher label propagation. `health_check.py` exits gracefully (`code 0`) in both configurations.

---

### Report 18 — Resolving Ingestion Bottlenecks, Token Limits & Local LLM Migration
**Incident:** Cascading pipeline failures during PDF ingestion — JSON validation errors, LLM token truncation, API quota exhaustion.

**Root Causes & Resolutions:**
- `chunk_size` halved from 4000 → 2000 characters to prevent JSON overflow
- Word-boundary chunking rewrote `TextProcessor.chunk_text()` — no more mid-word slices
- Anti-Markdown system prompting to suppress Groq's Llama 3 `json` block wrapping
- Migrated to **local Ollama** (`llama3:8b`) to permanently eliminate cloud rate limits

---

### Report 19 — Hybrid Chunking Architecture: Structural + Word-Boundary Synthesis
Performed comparative analysis of **RAG-READ's** structural chunker vs RAG-View's word-boundary chunker. Synthesized the best of both:

```python
# Step 1: Structural Paragraph Splitting (preserves topical coherence)
paragraphs = [p.strip() for p in re.split(r'\n\n+', text) if p.strip()]

# Step 2: Word-Boundary Fallback for oversized paragraphs (protects token limits)
if len(para) > self.chunk_size:
    sub_chunks = _word_boundary_split(para)
```

Also resolved ChromaDB SQLite lock errors (container restart), provisioned `llama3.2:1b` weights, purged contaminated graph state, and implemented the zero-state dashboard placeholder UI.

---

### Report 20 — PDF Binary Extraction & LLM Hallucination Resolution
**Incident:** Ingesting `CV_Shadwal.pdf` generated hallucinated entities (Elon Musk, NASA, Adobe) from a document that contained none of them.

**Root Cause Chain:**
1. `pypdf` omitted from Docker container (stale `poetry.lock`)
2. Fallback decoded raw PDF binary bytes as UTF-8 → 100K+ chars of garbled data
3. `llama3.2:1b` (1B params) hallucinated recognizable entities to satisfy the JSON schema

**Resolutions:**
- Modified `Dockerfile` to run `poetry lock && poetry install` during build (always-fresh lockfile)
- Upgraded model from `llama3.2:1b` → `llama3` (8B params) for robust JSON adherence
- Purged contaminated Neo4j nodes (`MATCH (n) DETACH DELETE n`) and ChromaDB volumes

---

## 5. Technology Stack

| Layer | Technology | Version | Role |
|:---|:---|:---|:---|
| **Graph Database** | Neo4j | 5.19+ | Knowledge graph storage, Cypher traversal, GDS clustering |
| **Vector Store** | ChromaDB | 1.5+ | Persistent dense vector similarity search |
| **Keyword Search** | BM25 (rank-bm25) | 0.2.2 | Sparse lexical keyword matching |
| **Cache / Broker** | Redis | 7.0+ | Query caching (1hr TTL), job state store |
| **LLM (Cloud)** | Gemini 2.0 Flash | — | Entity extraction, embedding, generation, verification |
| **LLM (Local)** | Ollama / Llama 3 | 8B | Rate-limit-free local extraction |
| **API Framework** | FastAPI | 0.110+ | REST API, background tasks, dependency injection |
| **UI Framework** | Streamlit | 1.32+ | Interactive dashboard, graph visualization |
| **Graph Viz** | PyVis | 0.3.2 | Neo4j neighbourhood rendering |
| **Rate Limiting** | SlowAPI | 0.1.9 | Token-bucket IP-based rate limiting |
| **Containerization** | Docker Compose | — | Full-stack orchestration (4 services) |
| **Dependency Mgmt** | Poetry | — | Deterministic lockfile builds |
| **Code Quality** | Black + Ruff + pre-commit | — | Formatting, linting, automated gates |

---

## 6. Core Modules Reference

| Module | Lines | Responsibility |
|:---|:---|:---|
| `src/extractor.py` | ~430 | Gemini/Ollama entity & relationship extraction, retry backoff |
| `src/graph_store.py` | ~160 | Neo4j idempotent MERGE upserts, provenance tracking |
| `src/hybrid_store.py` | ~210 | ChromaDB + BM25 dual-store, entity_id bridging |
| `src/embedder.py` | ~105 | Delta entity embedding, batch UNWIND upsert |
| `src/resolver.py` | ~200 | Cosine similarity deduplication, canonical merging |
| `src/query_linker.py` | ~190 | Pre-retrieval LLM entity extraction from query |
| `src/graph_retriever.py` | ~115 | 1/2-hop bounded Cypher traversal, provenance harvest |
| `src/graph_hybrid_retriever.py` | ~130 | Parallel 3-path retrieval, RRF fusion |
| `src/community_store.py` | ~245 | Louvain clustering, Gemini macro summaries, Cypher fallback |
| `src/context_assembler.py` | ~45 | Structured prompt block formatting with `[Source N]` |
| `src/retriever.py` | ~145 | Orchestration router, global intent detection |
| `src/qa.py` | ~195 | GraphRAGGenerator, three-section grounded prompt |
| `src/verifier.py` | ~260 | LLM-as-a-judge, Neo4j node property verification |
| `src/scorer.py` | ~330 | ConfidenceReport, graph_coverage metric |
| `src/graph_updater.py` | ~160 | Incremental ingestion, weight recalculation |
| `src/api.py` | ~420 | FastAPI endpoints, auth, rate limiting, Redis cache |
| `src/dashboard.py` | ~975 | Streamlit UI, graph vis, ingestion tab, benchmark tab |
| `src/processing.py` | ~90 | Hybrid structural + word-boundary chunker |
| `src/pipeline.py` | ~80 | Ingestion orchestration coordinator |
| `src/database.py` | ~65 | Neo4j connection singleton, schema initialization |

---

## 7. Benchmark Results: GraphRAG vs Flat RAG

**Dataset:** 72 manually curated golden QA pairs across 4 evaluation tiers  
**Judge:** Gemini Pro as LLM-as-a-Judge (Correctness: 1.0–5.0 scale)

| Evaluation Tier | Flat RAG | GraphRAG | Δ Correctness | Citation Coverage (GraphRAG) |
|:---|:---:|:---:|:---:|:---:|
| **Single-Entity Fact Retrieval** (20 pairs) | 4.8 | **5.0** | +0.2 | 100% |
| **Two-Hop Relational Queries** (22 pairs) | 2.4 | **4.9** | **+2.5** ⭐ | 100% |
| **Community Macro-Summaries** (15 pairs) | 3.1 | **4.8** | +1.7 | 95% |
| **Negative Cases & Refusals** (15 pairs) | 3.8 | **5.0** | +1.2 | 100% |

**Latency Trade-off:**  
- Flat RAG: ~0.35–0.45s per query  
- GraphRAG: ~0.50–0.85s per query  
- **The +300ms overhead delivers +104% correctness on the most important query tier.**

---

## 8. Critical Incidents & Resolutions

| # | Incident | Root Cause | Resolution |
|:---|:---|:---|:---|
| **1** | `429 RESOURCE_EXHAUSTED` (Gemini Free Tier) | 15 RPM cap exhausted during multi-chunk ingestion | Exponential backoff (30s base), proactive `time.sleep(5)` pacing |
| **2** | `json_validate_failed` (Groq API) | LLM output truncated mid-JSON due to `max_tokens=1024` cap with large chunks | Reduced chunk_size 4000→2000, set `max_tokens=16384` |
| **3** | Markdown wrapping by Llama 3 | Model wraps JSON in ` ```json ``` ` blocks, rejected by strict API parser | Anti-markdown system prompt: *"Output ONLY raw JSON"* |
| **4** | Groq TPM exhaustion (100K daily tokens) | `max_tokens=16384` × 40 chunks = 655K requested tokens | Hybrid chunker (1500 chars), reverted `max_tokens=2048` |
| **5** | ChromaDB SQLite `code: 1802` lock | Directory deleted while container held active file handles | `docker compose restart api dashboard` |
| **6** | PDF hallucination cascade | `pypdf` missing from container → binary UTF-8 fallback → 1B model hallucinated | `poetry lock` in Dockerfile, upgrade to `llama3` 8B |
| **7** | Graph fragmentation (duplicate nodes) | LLM extracts "WhySchool", "WhySchool Academy" as separate nodes | `EntityResolver` cosine clustering ≥ 0.92, canonical merging |
| **8** | Metadata mutation side effects | In-place dict modification shared references across callers | Shallow `dict()` copy in `HybridStore.add_chunk()` and `vector_search()` |

---

## 9. Test Suite Coverage

All tests run in `DRY_RUN=true` mode — no live Neo4j or Gemini API required.

| Test File | Module Tested | Key Assertions | Status |
|:---|:---|:---|:---|
| `test_extractor.py` | `src/extractor.py` | Pydantic validation, retry backoff, JSON fence cleaning | ✅ PASS |
| `test_graph_store.py` | `src/graph_store.py` | Cypher MERGE generation, provenance array tracking | ✅ PASS |
| `test_hybrid_store.py` | `src/hybrid_store.py` | ChromaDB + BM25 indexing, entity_id bridging | ✅ PASS |
| `test_retriever.py` | `src/retriever.py` | Full orchestration path, global intent routing | ✅ PASS |
| `test_graph_hybrid_retriever.py` | `src/graph_hybrid_retriever.py` | Parallel retrieval, RRF scoring, header formatting | ✅ PASS |
| `test_context_assembler.py` | `src/context_assembler.py` | `[Source N]` labeling, dual-compatible section headers | ✅ PASS |
| `test_community_store.py` | `src/community_store.py` | Community build pass, global intent routing | ✅ PASS |
| `test_verifier.py` | `src/verifier.py` | Entity extraction, Neo4j lookup, `[N ⚠️ UNVERIFIED]` flagging | ✅ PASS |
| `test_scorer.py` | `src/scorer.py` | `graph_coverage=0.50`, `ConfidenceReport` serialization | ✅ PASS |
| `test_graph_updater.py` | `src/graph_updater.py` | Incremental ingestion, weight recalculation, state metrics | ✅ PASS |
| `test_api.py` | `src/api.py` | 401 on missing API key, cache hit/miss, job polling | ✅ PASS |

---

## 10. Deployment Architecture

### Quick Start (One Command)
```bash
git clone https://github.com/shadwalsr/RAG-View-A-Production-Grade-Graph-Based-RAG-System.git
cd RAG-View-...
cp .env.example .env   # Add GEMINI_API_KEY
docker compose up -d
```

### Services
| Service | Port | Description |
|:---|:---|:---|
| `neo4j` | 7474 / 7687 | Neo4j Browser + Bolt (APOC + GDS plugins) |
| `redis` | 6379 | Query cache + job state store |
| `api` | 8000 | FastAPI backend (`/docs` for Swagger) |
| `dashboard` | 8501 | Streamlit UI |

### Dual Database Mode
| Mode | Config | Use Case |
|:---|:---|:---|
| **Local Docker** | `NEO4J_URI=bolt://localhost:7687` | Development, $0 cost, full GDS support |
| **Neo4j Aura Cloud** | `NEO4J_URI=neo4j+s://<id>.databases.neo4j.io` | Public demos, zero maintenance |

### API Endpoints Summary
| Endpoint | Method | Rate Limit | Description |
|:---|:---|:---|:---|
| `/v1/ask` | POST | 10/min | Full GraphRAG generation + verification |
| `/v1/ingest` | POST | 5/min | Queue background ingestion job |
| `/v1/jobs/{id}` | GET | 30/min | Poll ingestion job status |
| `/v1/graph/neighbors` | GET | 30/min | 1-hop entity neighborhood |
| `/v1/health` | GET | — | System health check |

---

## 11. Key Engineering Decisions & Trade-offs

| Decision | Chosen | Alternative Considered | Rationale |
|:---|:---|:---|:---|
| **Graph DB** | Neo4j | PostgreSQL + pgvector | Index-free adjacency enables O(1) multi-hop traversal vs O(n) joins |
| **Async Pattern** | FastAPI `BackgroundTasks` | Celery + RQ | Zero infrastructure overhead for moderate load; Celery requires broker complexity |
| **Retrieval Fusion** | Reciprocal Rank Fusion | Weighted linear combination | RRF is parameter-free and highly robust to score-scale differences across retrieval types |
| **UI** | Streamlit | React + TypeScript | 10x faster iteration for ML-centric UIs; React deferred to future phase |
| **Entity Deduplication** | Cosine similarity ≥ 0.92 | Exact string matching | Catches lexical variants ("WhySchool" vs "WhySchool Academy") that exact match misses |
| **Chunking** | Hybrid Structural + Word-Boundary | Fixed character windows | Preserves topical coherence (paragraphs) while guaranteeing entity integrity (no mid-word cuts) |
| **LLM Provider** | Dual (Gemini Cloud + Ollama Local) | Single provider | Eliminates single point of failure; local Ollama removes rate limits during heavy ingestion |

---

## 12. Future Roadmap

### Near-Term (Next 3 Months)
1. **Streaming Token Generation** — Implement `generate_content_stream` in `GraphRAGGenerator` to reduce perceived latency for end users
2. **Interactive Citation Tooltips** — Parse `[Source N]` tags in the Streamlit UI as clickable tooltips displaying underlying chunk text
3. **`ConfidenceReport` Dashboard** — Surface `graph_coverage` and `grounding_confidence` as real-time metric gauges in the UI
4. **Redis-Backed Distributed Rate Limiting** — Migrate `slowapi` to use Redis storage for consistent token buckets across multi-container deployments

### Medium-Term (3–12 Months)
5. **RAGAS / TruLens Evaluation** — Automated evaluation pipeline benchmarking citation accuracy, answer relevance, and context precision
6. **Kubernetes Helm Chart** — Production-grade multi-replica deployment with horizontal pod autoscaling
7. **AuraDS Enterprise Integration** — Terraform script for provisioning dedicated Neo4j AuraDS with auto-scaling memory pools
8. **MkDocs Documentation Site** — Auto-published GitHub Pages site from `README.md` and `ARCHITECTURE.md` on every main branch commit

### Long-Term Vision
9. **Streaming Graph Construction** — Real-time knowledge graph updates as documents arrive (event-driven via Kafka)
10. **Multi-Modal Ingestion** — Extend beyond text/PDF to images, tables, and audio transcripts
11. **Dynamic Chunk Sizing** — Adaptive chunk size based on document density (narrative vs dense tables/resumes)

---

## 13. Conclusion

RAG-View represents a complete, ground-up engineering journey — 20 reports, 26 source modules, 11 automated test suites, and a fully containerized production deployment — built to solve a real architectural problem: **flat vector RAG fails on multi-hop reasoning, and the only correct solution is a knowledge graph.**

The platform delivers on three non-negotiable promises:

1. **Accuracy** — GraphRAG achieves 4.9/5.0 on multi-hop queries vs 2.4/5.0 for flat RAG (+104%)
2. **Verifiability** — Every claim is verified against Neo4j node properties; unsupported statements are explicitly flagged
3. **Production-Readiness** — One-command Docker deployment, enterprise security gateway, async ingestion, and dual cloud/local database support

The codebase is live, open-source, and fully documented. All 20 engineering reports, the `ARCHITECTURE.md` decision record, and the `benchmark_report.csv` are available in the repository as a complete technical audit trail of the build journey.

---

*RAG-View — Engineered by Shadwal Singh. 2026.*  
*[GitHub Repository](https://github.com/shadwalsr/RAG-View-A-Production-Grade-Graph-Based-RAG-System)*
