# Report 1: Foundation and Graph Data Model

**Author:** Shadwal Singh  

---

## 1. Executive Summary

As we transition from the flat, vector-based architecture of RAGRead to the graph-powered intelligence of **RAG-View**, our first crucial step is establishing a robust, production-grade foundation. In this phase, we initialized the repository architecture, configured dependency management, and established the development environment required to support our Neo4j and FastAPI stack.

---

## 2. Repository Architecture

We structured the project to separate concerns clearly, ensuring maintainability as the platform scales:

- **`src/`**: The core application logic, housing our FastAPI service, Neo4j integration layer, and retrieval fusion algorithms.
- **`tests/`**: Dedicated environment for unit and integration testing to ensure pipeline reliability.
- **`data/`**: Local storage for document ingestion and preprocessing before pushing to the graph.
- **`frontend/`**: The designated location for our upcoming React + TypeScript interactive visual canvas.
- **`docs/`**: Centralized project documentation.

---

## 3. Dependency Management and Quality Control

To ensure a deterministic and high-quality development lifecycle, we implemented modern Python tooling:

- **Poetry (`pyproject.toml`)**: Chosen over standard `pip` for robust dependency resolution and virtual environment management. We defined all necessary dependencies for the tech stack, including `fastapi`, `neo4j`, `google-generativeai`, and `redis`.
- **Pre-commit Hooks**: We configured `.pre-commit-config.yaml` to run automatically before every commit, ensuring code quality without manual intervention.
  - **Black**: Enforces strict, uncompromising code formatting (`line-length = 88`).
  - **Ruff**: Provides blazing-fast linting to catch errors and maintain clean imports.

---

## 4. Environment and Task Orchestration

We built utilities to streamline the developer experience:

- **Environment Template (`.env.example`)**: We documented every configuration key the system will ever need upfront. This includes the `NEO4J_URI`, `GEMINI_API_KEY`, `REDIS_URL`, and internal `API_KEY`s, providing clear instructions for secure deployment.
- **Task Runner (`Makefile`)**: We created a centralized Makefile with standardized targets (`make run`, `make test`, `make lint`, `make docker-up`, `make setup`). This abstracts away complex commands, allowing developers to spin up the infrastructure or run tests with a single word.

---

## 5. Conclusion: Ready for the Graph

With the repository scaffolded, dependencies locked, and quality gates in place, the environment is fully primed. 

**Status:** Scaffold Complete. The system is ready to define the Neo4j schema and begin building the entity extraction pipeline.
