import os
import sys
import logging
from fastapi.testclient import TestClient

# Ensure src is in path.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Enable DRY RUN.
os.environ["DRY_RUN"] = "true"

from src.database import db
from src.api import app

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

client = TestClient(app)
unauth_client = TestClient(app)

auth_headers = {"X-API-Key": os.getenv("API_KEY", "rag_view_secret_key_2026")}

def test_api_endpoints():
    logger.info("--- Testing FastAPI Endpoints in DRY_RUN Mode ---")
    db.is_dry_run = True
    
    # 0.
    logger.info("\nTesting Unauthorized access without X-API-Key...")
    res = unauth_client.post("/v1/ask", json={"query": "What company did Shadwal Singh found?"})
    assert res.status_code == 401
    logger.info("Successfully verified 401 Unauthorized response.")
    
    # 1.
    logger.info("\nTesting POST /v1/ask...")
    res = client.post("/v1/ask", json={"query": "What company did Shadwal Singh found?"}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    logger.info(f"Response: {data}")
    assert "answer" in data
    assert "confidence_report" in data
    
    # 1b.
    logger.info("\nTesting POST /v1/ask Cache Hit...")
    res_cached = client.post("/v1/ask", json={"query": "What company did Shadwal Singh found?"}, headers=auth_headers)
    assert res_cached.status_code == 200
    assert res_cached.json() == data
    logger.info("Successfully verified query caching hit.")

    # 1c.
    logger.info("\nTesting POST /v1/ask/stream...")
    res_stream = client.post("/v1/ask/stream", json={"query": "What company did Shadwal Singh found?"}, headers=auth_headers)
    assert res_stream.status_code == 200
    
    import json
    tokens = []
    metadata = None
    for line in res_stream.iter_lines():
        if line:
            decoded = line.decode("utf-8").strip()
            if decoded.startswith("data: "):
                chunk = json.loads(decoded[6:].strip())
                if chunk["type"] == "token":
                    tokens.append(chunk["content"])
                elif chunk["type"] == "metadata":
                    metadata = chunk
                    
    assert len(tokens) > 0
    assert metadata is not None
    assert "verified_answer" in metadata
    assert "confidence_score" in metadata
    assert "grounding_confidence" in metadata
    assert "graph_coverage" in metadata
    assert "relationships" in metadata
    logger.info(f"Successfully streamed {len(tokens)} tokens and retrieved final metadata: {metadata}")
    
    # 2.
    logger.info("\nTesting POST /v1/ingest...")
    res = client.post("/v1/ingest", json={"text": "WhySchool is an AI startup.", "source_name": "test_src"}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    logger.info(f"Response: {data}")
    assert data["status"] == "queued"
    assert "job_id" in data
    job_id = data["job_id"]
    
    # 2b.
    logger.info(f"\nTesting GET /v1/jobs/{job_id}...")
    res = client.get(f"/v1/jobs/{job_id}", headers=auth_headers)
    assert res.status_code == 200
    job_data = res.json()
    logger.info(f"Job Status Response: {job_data}")
    assert job_data["job_id"] == job_id
    assert job_data["status"] in ["queued", "processing", "completed", "failed"]
    
    # 3.
    logger.info("\nTesting GET /v1/graph/entity/WhySchool...")
    res = client.get("/v1/graph/entity/WhySchool", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    logger.info(f"Response: {data}")
    assert data["name"] == "WhySchool"
    assert "outgoing_relationships" in data
    
    # 4.
    logger.info("\nTesting GET /v1/graph/path?from=Shadwal&to=WhySchool...")
    res = client.get("/v1/graph/path?from=Shadwal&to=WhySchool", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    logger.info(f"Response: {data}")
    assert data["path_found"] is True
    assert "path_nodes" in data
    
    logger.info("\nAll FastAPI endpoints tested successfully!")

if __name__ == "__main__":
    test_api_endpoints()

