import json
import logging
import os
from typing import List, Tuple

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.database import db
from src.query_linker import query_linker

load_dotenv()
logger = logging.getLogger(__name__)

class ConfidenceReport(BaseModel):
    """
    Structured JSON response representing confidence scoring metrics for GraphRAG.
    """
    retrieval_confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence in the relevance and quality of retrieved chunks (0-1)"
    )
    grounding_confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence that the answer is fully grounded in the context without hallucinations (0-1)"
    )
    graph_coverage: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Ratio of query entities successfully found in the knowledge graph (0-1)"
    )
    explanation: str = Field(
        ..., 
        description="Brief explanation justifying the confidence scores"
    )

class ConfidenceScorer:
    """
    Evaluates GraphRAG retrieval and generation confidence.
    Calculates the graph_coverage metric based on the ratio of query entities 
    successfully found in the knowledge graph, and uses Gemini to produce a 
    structured ConfidenceReport JSON response.
    """
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = "gemini-2.0-flash"

    def calculate_graph_coverage(self, query: str, fused_context: str) -> Tuple[float, List[str], List[str]]:
        """
        Calculates the graph_coverage metric: ratio of query entities found in the graph.
        Returns (coverage_ratio, query_entities, found_entities).
        """
        query_entities = query_linker.extract_entities(query)
        if not query_entities:
            logger.info("No entities extracted from query. Defaulting graph_coverage to 1.0.")
            return 1.0, [], []

        logger.info(f"ConfidenceScorer checking graph coverage for query entities: {query_entities}")

        # 1.
        query_str = """
        MATCH (e:Entity)
        WHERE ANY(n IN $names WHERE toLower(e.name) CONTAINS toLower(n) OR toLower(n) CONTAINS toLower(e.name))
        RETURN e.name AS name
        """
        try:
            results = db.query(query_str, {"names": query_entities})
            found_in_db = {r["name"] for r in results}
        except Exception as e:
            logger.error(f"Failed to query Neo4j for graph coverage: {e}")
            found_in_db = set()

        # 2.
        if not found_in_db and db.is_dry_run:
            logger.info("[DRY RUN] Checking query entities against fused context for graph coverage.")
            lower_context = fused_context.lower()
            for ent in query_entities:
                if ent.lower() in lower_context:
                    found_in_db.add(ent)

        # Calculate how many of the original query entities were matched.
        matched_query_entities = []
        for q in query_entities:
            q_lower = q.lower()
            if any(q_lower in db_name.lower() or db_name.lower() in q_lower for db_name in found_in_db):
                matched_query_entities.append(q)

        coverage = len(matched_query_entities) / len(query_entities) if query_entities else 1.0
        coverage = max(0.0, min(1.0, coverage))
        logger.info(f"Calculated graph_coverage: {coverage:.2f} ({len(matched_query_entities)}/{len(query_entities)} query entities found).")
        return coverage, query_entities, list(found_in_db)

    def score(self, query: str, answer: str, fused_context: str) -> ConfidenceReport:
        """
        Scores the retrieval and generation stages, returning a structured ConfidenceReport.
        """
        logger.info("ConfidenceScorer starting confidence evaluation...")

        graph_coverage, query_entities, found_entities = self.calculate_graph_coverage(query, fused_context)

        if os.getenv("DRY_RUN") == "true":
            logger.warning("[DRY RUN] Bypassing LLM API. Returning mock ConfidenceReport.")
            return ConfidenceReport(
                retrieval_confidence=0.90,
                grounding_confidence=0.95,
                graph_coverage=graph_coverage,
                explanation=f"Mock confidence report generated (DRY RUN). Calculated graph coverage: {graph_coverage:.2f} ({len(found_entities)}/{len(query_entities)} entities found)."
            )

        prompt = f"""You are an expert AI Confidence Scorer for a GraphRAG system.
Your task is to evaluate the quality of the retrieval and generation stages based on the provided Query, Grounding Context, and Generated Answer.

=== INPUTS ===
USER QUERY: {query}

CALCULATED GRAPH COVERAGE RATIO: {graph_coverage:.2f}
(This is the exact ratio of query entities successfully found in the knowledge graph: {len(found_entities)} / {len(query_entities)})

GROUNDING CONTEXT:
{fused_context}

GENERATED ANSWER:
{answer}

=== EVALUATION INSTRUCTIONS ===
1. retrieval_confidence (0.0 - 1.0): Evaluate how relevant, comprehensive, and high-quality the retrieved chunks and graph relationships are for answering the query.
2. grounding_confidence (0.0 - 1.0): Evaluate how well the generated answer is grounded in the provided context. Penalize any hallucinations or unsupported claims.
3. graph_coverage (0.0 - 1.0): MUST be set exactly to the CALCULATED GRAPH COVERAGE RATIO provided above ({graph_coverage:.2f}).
4. explanation: Provide a brief, professional explanation justifying your confidence ratings.

=== OUTPUT FORMAT ===
You MUST return ONLY valid JSON matching the following structure. Do not include any markdown fences, explanation, or extra text outside the JSON object.

{{
  "retrieval_confidence": 0.95,
  "grounding_confidence": 0.90,
  "graph_coverage": {graph_coverage:.2f},
  "explanation": "Brief justification of the scores."
}}
"""

        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        import requests

        def parse_json_response(raw_text: str) -> ConfidenceReport:
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            return ConfidenceReport(**data)

        if provider == "groq":
            logger.info("Using Groq API for confidence scoring...")
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return ConfidenceReport(retrieval_confidence=0.85, grounding_confidence=0.85, graph_coverage=graph_coverage, explanation="Fallback confidence report generated due to missing Groq API key.")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "messages": [
                    {"role": "system", "content": "You are an expert AI Confidence Scorer. You must output valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            
            import time
            for attempt in range(4):
                try:
                    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                    if res.status_code == 200:
                        return parse_json_response(res.json()["choices"][0]["message"]["content"])
                    elif res.status_code == 429:
                        if attempt == 3:
                            return ConfidenceReport(retrieval_confidence=0.85, grounding_confidence=0.85, graph_coverage=graph_coverage, explanation="Fallback confidence report generated due to Groq API 429 Rate Limit.")
                        wait_sec = 2 ** attempt
                        logger.warning(f"Groq API 429 Rate Limit in scorer. Retrying in {wait_sec}s...")
                        time.sleep(wait_sec)
                    else:
                        logger.error(f"Groq scorer error on attempt {attempt}: {res.text}")
                        if attempt == 3:
                            return ConfidenceReport(retrieval_confidence=0.85, grounding_confidence=0.85, graph_coverage=graph_coverage, explanation="Fallback confidence report generated due to Groq API error.")
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Groq scorer exception on attempt {attempt}: {e}")
                    if attempt == 3:
                        return ConfidenceReport(retrieval_confidence=0.85, grounding_confidence=0.85, graph_coverage=graph_coverage, explanation="Fallback confidence report generated due to Groq execution error.")
                    time.sleep(1)

        elif provider == "openai":
            logger.info("Using OpenAI API for confidence scoring...")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return ConfidenceReport(retrieval_confidence=0.85, grounding_confidence=0.85, graph_coverage=graph_coverage, explanation="Fallback confidence report generated due to missing OpenAI API key.")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": "You are an expert AI Confidence Scorer. You must output valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            try:
                res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if res.status_code == 200:
                    return parse_json_response(res.json()["choices"][0]["message"]["content"])
                else:
                    logger.error(f"OpenAI scorer error: {res.text}")
                    return ConfidenceReport(retrieval_confidence=0.85, grounding_confidence=0.85, graph_coverage=graph_coverage, explanation="Fallback confidence report generated due to OpenAI API error.")
            except Exception as e:
                logger.error(f"OpenAI scorer exception: {e}")
                return ConfidenceReport(retrieval_confidence=0.85, grounding_confidence=0.85, graph_coverage=graph_coverage, explanation="Fallback confidence report generated due to OpenAI execution error.")

        elif provider == "ollama":
            logger.info("Using Ollama for confidence scoring...")
            ollama_url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
            payload = {
                "model": os.getenv("OLLAMA_MODEL", "llama3"),
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
            try:
                res = requests.post(f"{ollama_url.rstrip('/')}/api/generate", json=payload, timeout=300)
                if res.status_code == 200:
                    return parse_json_response(res.json()["response"])
                else:
                    logger.error(f"Ollama scorer error: {res.text}")
                    return ConfidenceReport(retrieval_confidence=0.85, grounding_confidence=0.85, graph_coverage=graph_coverage, explanation="Fallback confidence report generated due to Ollama API error.")
            except Exception as e:
                logger.error(f"Ollama scorer exception: {e}")
                return ConfidenceReport(retrieval_confidence=0.85, grounding_confidence=0.85, graph_coverage=graph_coverage, explanation="Fallback confidence report generated due to Ollama execution error.")

        else:
            if not self.client:
                return ConfidenceReport(retrieval_confidence=0.85, grounding_confidence=0.85, graph_coverage=graph_coverage, explanation="Fallback confidence report generated due to missing Gemini API key.")
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                    ),
                )
                return parse_json_response(response.text)
            except Exception as e:
                logger.error(f"Failed to generate ConfidenceReport via Gemini: {e}")
                return ConfidenceReport(
                    retrieval_confidence=0.85,
                    grounding_confidence=0.85,
                    graph_coverage=graph_coverage,
                    explanation=f"Fallback confidence report generated due to LLM error. Calculated graph coverage: {graph_coverage:.2f}."
                )

# Global instance.
confidence_scorer = ConfidenceScorer()
scorer = confidence_scorer  # Alias

