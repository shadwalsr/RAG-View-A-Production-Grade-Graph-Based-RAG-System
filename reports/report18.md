# Engineering Report 18: Resolving GraphRAG Ingestion Bottlenecks, Token Limits, and Local LLM Migration

**Author:** Senior Python/Neo4j Debugging Assistant  
**Subject:** Diagnostic analysis, root cause identification, and resolution of LLM extraction errors, chunking malformations, API rate limits, and local LLM migration for the RAG-View GraphRAG pipeline.

---

## 1. Executive Summary

During the optimization of the RAG-View Graph Explorer pipeline, the system encountered a series of cascading failures during document ingestion. Initially manifested as JSON validation errors (`json_validate_failed`) on the Groq API, deep diagnostic tracing revealed a combination of LLM token truncation, malformed chunk boundaries, stubborn markdown wrapping by Llama 3 models, and eventual free-tier API rate limit exhaustion across both Groq and Google Gemini. 

This report documents the exact sequence of errors encountered, the architectural root causes identified, and the engineering resolutions implemented. The pipeline has been successfully refactored to utilize a semantic word-boundary chunking algorithm and transitioned to a 100% local, rate-limit-free execution model powered by Ollama.

---

## 2. Chronological Error Analysis & Resolutions

### Phase 1: The `"max completion tokens reached"` Bottleneck

#### **The Symptom**
During the ingestion of uploaded documents, the pipeline failed on Chunk 2 with the following Groq API error:
```json
{
  "error": {
    "message": "Failed to generate JSON. Please adjust your prompt. See 'failed_generation' for more details.",
    "type": "invalid_request_error",
    "code": "json_validate_failed",
    "failed_generation": "max completion tokens reached before generating a valid document"
  }
}
```

#### **Root Cause Analysis**
When the Graph Explorer extraction scope was expanded to include `LOCATION` and `EVENT` entities (in addition to `PERSON`, `ORG`, `PROJECT`, `SKILL`, and `CONCEPT`), the LLM began generating significantly larger and denser JSON knowledge graphs for each text chunk. 
1. **Uncapped API Payloads:** The Groq API call in `src/extractor.py` did not explicitly define a `max_tokens` limit, defaulting to Groq's standard completion ceiling (1,024 tokens).
2. **Oversized Chunks:** The original `chunk_size` in `src/processing.py` was set to `4000` characters (~1,000 tokens). A dense 1,000-token chunk containing 7 categories of entities and their pairwise relationships easily required 2,500+ tokens to represent in verbose JSON format. The generation was cut off mid-stream, resulting in invalid JSON.

#### **Engineering Resolution**
1. **Explicit Token Buffer:** Updated `src/extractor.py` to explicitly set `"max_tokens": 16384` for Groq and OpenAI payloads, providing an immense runway for closing large JSON objects.
2. **Chunk Size Halving:** Modified `src/processing.py` to reduce `chunk_size` from `4000` to `2000` characters (with `200` character overlap). Smaller chunks ensure more focused, higher-precision entity extraction and prevent massive, unwieldy JSON outputs.

---

### Phase 2: The `"json_validate_failed"` Chunking & Markdown Error

#### **The Symptom**
Following the token increase, the pipeline progressed further but failed on subsequent chunks (e.g., Chunk 4, Chunk 23) with a pure JSON validation failure:
```json
{
  "error": {
    "message": "Failed to generate JSON. Please adjust your prompt. See 'failed_generation' for more details.",
    "type": "invalid_request_error",
    "code": "json_validate_failed"
  }
}
```

#### **Root Cause Analysis**
Diagnostic tracing revealed two distinct issues corrupting the LLM output:
1. **Word-Slicing Chunk Boundaries:** The original `TextProcessor` in `src/processing.py` utilized naive character slicing (`text[start:end]`). This frequently sliced words and sentences exactly in half (e.g., `"Artificial Intelligence"` split into `"Artificial Int"` and `"lligence"`). When the LLM encountered broken, incomplete sentences at chunk boundaries, it became confused and generated conversational apologies (e.g., *"I cannot extract entities from an incomplete sentence"*) instead of JSON.
2. **Stubborn Markdown Wrapping:** Llama 3 models on Groq frequently wrap JSON outputs in Markdown code blocks (````json ... ````). Groq's strict API JSON parser rejects Markdown formatting outright, throwing `json_validate_failed`.

#### **Engineering Resolution**
1. **Word-Boundary Chunking Algorithm:** Completely rewrote `TextProcessor.chunk_text()` in `src/processing.py` to tokenize text by words (`text.split()`) and calculate chunk boundaries strictly at whitespace intervals. This guarantees that every chunk ends on a clean word boundary, preserving semantic context.
2. **Strict Anti-Markdown Prompting:** Updated the system prompt in `src/extractor.py` to aggressively forbid Markdown: `"You must output ONLY raw, valid JSON. Do NOT use markdown formatting. Do NOT wrap the output in ```json blocks."`

---

### Phase 3: Free-Tier API Quota Exhaustion (`429 Rate Limit`)

#### **The Symptom**
With JSON validation fully stabilized, the pipeline encountered hard rate limits on Chunk 23:
```json
{
  "error": {
    "message": "Rate limit reached for model llama-3.3-70b-versatile in organization... Limit 100000, Used 99387, Requested 16795. Please try again in 3h53m.",
    "type": "tokens",
    "code": "rate_limit_exceeded"
  }
}
```
A subsequent fallback switch to Google Gemini resulted in the Streamlit UI hanging indefinitely on Chunk 1.

#### **Root Cause Analysis**
1. **Groq Daily Token Limits:** Groq calculates rate limits based on *requested* tokens (`prompt_tokens + max_tokens`). Because `max_tokens` was set to `16384`, each chunk requested ~17,000 tokens upfront. Processing 40 chunks instantly exhausted Groq's 100,000 daily free-tier token limit.
2. **Gemini Daily Quota & Backoff Hang:** Switching to Gemini revealed that the Gemini API key had also exhausted its Free Tier daily quota (1,500 requests/day). When `src/extractor.py` encountered a `429 RESOURCE_EXHAUSTED` error from Gemini, the built-in `_retry_with_backoff` logic correctly trapped the error and initiated exponential backoff sleeps (30s, 40s, 50s, 60s, 70s). This cumulative 4.5-minute sleep cycle caused the UI progress bar to appear frozen on Chunk 1.

#### **Engineering Resolution (Migration to Local Ollama)**
To permanently eliminate third-party API quotas, rate limits, and billing bottlenecks, the entire GraphRAG extraction engine was migrated to a 100% local execution model:
1. **Ollama Integration Audit:** Audited `src/extractor.py`, `src/qa.py`, `src/query_linker.py`, `src/scorer.py`, and `src/verifier.py` to verify robust Ollama JSON generation support.
2. **Community Store Enhancement:** Added native Ollama support to `src/community_store.py`, ensuring macro-community summaries can be generated locally alongside entity extraction.
3. **Environment Reconfiguration:** Updated `.env` to set `LLM_PROVIDER=ollama` and `OLLAMA_MODEL=llama3`.
4. **Automated Background Model Pull:** Identified that the Llama 3 weights were missing locally and executed `ollama pull llama3` directly via the Windows host executable path (`C:\Users\shadw\AppData\Local\Programs\Ollama\ollama.exe`). The 4.7 GB model successfully downloaded and verified.

---

## 3. Current System State & Verification

*   **LLM Engine:** Local Ollama (`http://host.docker.internal:11434`) running `llama3:8b`.
*   **Chunking:** `chunk_size=2000`, `chunk_overlap=200`, strictly enforcing word boundaries.
*   **Extraction Scope:** Rich 7-category extraction (`PERSON`, `ORG`, `PROJECT`, `SKILL`, `CONCEPT`, `LOCATION`, `EVENT`).
*   **Status:** All containers recreated and healthy. The Ollama model pull is 100% complete (`success`). The ingestion pipeline is fully unblocked and ready for local execution.

---

## 4. Recommendations for Future Scaling

1.  **Batch Ingestion Queue:** If processing massive document libraries (>500 pages), integrate Celery or RQ with the existing Redis broker to offload Ollama extraction into background worker queues.
2.  **GPU Acceleration:** Ensure Ollama has access to dedicated GPU VRAM (NVIDIA CUDA) on the Windows host to maximize local token generation speed (achieving 50+ tokens/sec).
3.  **Dynamic Chunk Sizing:** Consider implementing dynamic chunk sizing based on document density (e.g., larger chunks for narrative text, smaller chunks for dense tables/resumes).
