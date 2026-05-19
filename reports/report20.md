# Report 20: PDF Binary Extraction & LLM Hallucination Resolution

## 1. The Incident
During the ingestion of a standard PDF document (`CV_Shadwal.pdf`), the GraphRAG pipeline generated a massive cluster of completely hallucinated entities and relationships. The generated knowledge graph displayed famous tech industry concepts (e.g., "Elon Musk", "Adobe", "Photoshop", "Satya Nadella", "Google") that did not exist anywhere in the source document.

## 2. Root Cause Analysis
An extensive audit of the Docker containers, vector storage, and extraction logic revealed a fascinating three-part cascading failure:

### A. The Dependency Lock Mismatch
The `pypdf` library was added to `pyproject.toml` to handle PDF text extraction. However, `poetry.lock` was not regenerated after this addition. When Docker built the `rag_view_api` container, `poetry install` strictly adhered to the stale lockfile. As a result, `pypdf` was completely omitted from the production container environment.

### B. The Raw Binary Fallback
When the ingestion script (`src/dashboard.py`) attempted to `import pypdf` inside the container, it triggered a `ModuleNotFoundError`. The script caught this exception and defaulted to its emergency fallback mechanism:
```python
text_content = content_bytes.decode("utf-8", errors="ignore")
```
Because `content_bytes` represented the raw, compressed binary byte stream of a PDF file, force-decoding it into UTF-8 produced over 100,000 characters of absolute garbled binary gibberish (e.g., `3go{&e\ov U wI _JÄƒeØ©%0...`). This gibberish was successfully chunked and stored in ChromaDB.

### C. The LLM Hallucination Engine
The pipeline's `.env` configuration was utilizing `llama3.2:1b`, an ultra-lightweight 1-Billion parameter language model. When this tiny model was fed chunks containing 2,000 characters of alien binary symbols alongside strict, complex instructions to extract "tech entities, skills, and organizations" in a rigid JSON format, its reasoning capabilities collapsed. 

Desperate to satisfy the JSON schema requirements, the model either misinterpreted random binary characters as partial acronyms or completely hallucinated highly probable entities from its pre-training weights (Elon Musk, SpaceX, NASA) to fill in the blanks.

## 3. The Resolution

### A. Infrastructure Fix (Dockerfile)
To ensure the container dependencies always perfectly reflect the `pyproject.toml`, the `Dockerfile` was modified to dynamically generate a fresh lockfile during the build phase:
```dockerfile
# Copy dependency files (ignoring stale lockfile)
COPY pyproject.toml ./

# Generate fresh lockfile and install dependencies
RUN poetry lock && poetry install --no-root --no-interaction --no-ansi
```
The containers were subsequently rebuilt, successfully injecting `pypdf` into the active environment.

### B. Model Upgrade (.env)
To prevent future reasoning failures and ensure strict prompt adherence, the `.env` configuration was upgraded from the 1B model to the flagship 8B model:
```env
OLLAMA_MODEL=llama3
```

### C. Data Sanitization
The contaminated graph environment was securely purged to restore a zero-state:
*   **Neo4j:** Executed `MATCH (n) DETACH DELETE n` to remove all hallucinated nodes and relationships.
*   **ChromaDB:** Wiped the local `data/chroma` volume to eliminate the garbled binary chunks.

## 4. Conclusion
The pipeline is now highly resilient. PDF text is correctly parsed using the native `pypdf` library, and the robust 8B Llama 3 model ensures that entity extraction strictly reflects the provided text without hallucinating structural schemas.
