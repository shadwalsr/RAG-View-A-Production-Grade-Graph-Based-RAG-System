import json
import logging
import os
from typing import List

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.database import db

load_dotenv(override=True)
logger = logging.getLogger(__name__)

QUERY_EXTRACTION_PROMPT = """
You are an expert NLP entity extraction system.
Extract all proper nouns, named entities, organizations, people, and specific concepts from the following user query.
Return the result strictly as a valid JSON array of strings. Do not include any markdown formatting, explanation, or code blocks. Just the JSON array.
If no entities are found, return an empty array: []

USER QUERY: {query}
"""

class QueryEntityLinker:
    """
    Extracts entities directly from the user's incoming query.
    These entities act as guaranteed entry points into the Knowledge Graph.
    """
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = "gemini-2.0-flash"

    def extract_entities(self, query: str) -> List[str]:
        """
        Parses a natural language query and returns a list of mentioned entities.
        """
        if not query or not query.strip():
            return []

        if db.is_dry_run or os.getenv("DRY_RUN") == "true":
            logger.info("[DRY RUN] Mocking query entity extraction...")
            mocks = []
            lower_query = query.lower()
            if "whyschool" in lower_query:
                mocks.append("WhySchool")
            if "shadwal" in lower_query:
                mocks.append("Shadwal")
            return mocks

        prompt = QUERY_EXTRACTION_PROMPT.format(query=query)
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        import requests

        def parse_json_entities(raw_text: str) -> List[str]:
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            try:
                data = json.loads(cleaned.strip())
                if isinstance(data, list):
                    return data
            except Exception as e:
                logger.error(f"Failed to parse JSON entities: {e}")
            return []

        if provider == "groq":
            logger.info("Using Groq API for query entity extraction...")
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return []
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "messages": [
                    {"role": "system", "content": "You are an expert NLP entity extraction system. You must output valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            # Wrap prompt to ensure JSON object with 'entities' key for Groq json_object mode.
            groq_prompt = prompt + "\nReturn a JSON object with a single key 'entities' containing the array of strings."
            payload["messages"][1]["content"] = groq_prompt
            
            import time
            for attempt in range(4):
                try:
                    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        data = json.loads(content.strip())
                        return data.get("entities", [])
                    elif res.status_code == 429:
                        if attempt == 3:
                            return []
                        wait_sec = 2 ** attempt
                        logger.warning(f"Groq API 429 Rate Limit in query_linker. Retrying in {wait_sec}s...")
                        time.sleep(wait_sec)
                    else:
                        logger.error(f"Groq query linker error: {res.text}")
                        if attempt == 3:
                            return []
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Groq query linker exception on attempt {attempt}: {e}")
                    if attempt == 3:
                        return []
                    time.sleep(1)
            return []

        elif provider == "openai":
            logger.info("Using OpenAI API for query entity extraction...")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return []
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": "You are an expert NLP entity extraction system. You must output valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            openai_prompt = prompt + "\nReturn a JSON object with a single key 'entities' containing the array of strings."
            payload["messages"][1]["content"] = openai_prompt
            try:
                res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if res.status_code == 200:
                    content = res.json()["choices"][0]["message"]["content"]
                    data = json.loads(content.strip())
                    return data.get("entities", [])
                else:
                    logger.error(f"OpenAI query linker error: {res.text}")
                    return []
            except Exception as e:
                logger.error(f"OpenAI query linker exception: {e}")
                return []

        elif provider == "ollama":
            logger.info("Using Ollama for query entity extraction...")
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
                    return parse_json_entities(res.json()["response"])
                else:
                    logger.error(f"Ollama query linker error: {res.text}")
                    return []
            except Exception as e:
                logger.error(f"Ollama query linker exception: {e}")
                return []

        else:
            if not self.client:
                return []
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                    ),
                )
                return parse_json_entities(response.text)
            except Exception as e:
                logger.error(f"Query entity extraction failed via Gemini: {e}")
                return []

# Global instance.
query_linker = QueryEntityLinker()

