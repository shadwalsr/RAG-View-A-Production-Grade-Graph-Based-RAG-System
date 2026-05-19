"""
extractor.py — The Brain of RAG-View

This is the most critical module in the entire system.
It takes raw text and uses Gemini Flash to extract structured
entities and relationships, returning strict Pydantic-validated JSON.

The quality ceiling of the whole knowledge graph depends on this module.
"""

import json
import logging
import os
import time
from enum import Enum
from typing import Optional

# pyrefly: ignore [missing-import].
from dotenv import load_dotenv

# pyrefly: ignore [missing-import].
from google import genai

# pyrefly: ignore [missing-import].
from google.genai import types

# pyrefly: ignore [missing-import].
from pydantic import BaseModel, Field, field_validator

# pyrefly: ignore [missing-import].
from src.database import db

# Load environment variables (e.
load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------.
# Pydantic Models — strict contracts for what the LLM must return.
# ---------------------------------------------------------------------------.

class EntityType(str, Enum):
    """The categories we care about extracting from documents."""
    PERSON = "PERSON"
    ORG = "ORG"
    PROJECT = "PROJECT"
    SKILL = "SKILL"
    CONCEPT = "CONCEPT"
    LOCATION = "LOCATION"
    EVENT = "EVENT"


class Entity(BaseModel):
    """A single extracted entity from a text chunk."""
    name: str = Field(..., description="Canonical name of the entity")
    type: EntityType = Field(..., description="Category of the entity")
    short_description: str = Field(
        ...,
        max_length=200,
        description="One-line description of the entity in context",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How confident the LLM is about this extraction (0-1)",
    )

    @field_validator("name")
    @classmethod
    def name_must_be_clean(cls, v: str) -> str:
        """Strip whitespace and normalize casing for graph deduplication."""
        return v.strip().title()


class Relationship(BaseModel):
    """A directed relationship between two entities."""
    subject: str = Field(..., description="Source entity name")
    predicate: str = Field(
        ...,
        description="The relationship verb, e.g. FOUNDED, WORKS_AT, USES",
    )
    object: str = Field(..., description="Target entity name")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How confident the LLM is about this relationship (0-1)",
    )

    @field_validator("subject", "object")
    @classmethod
    def names_must_be_clean(cls, v: str) -> str:
        return v.strip().title()

    @field_validator("predicate")
    @classmethod
    def predicate_must_be_uppercase(cls, v: str) -> str:
        """Relationship types are always UPPER_SNAKE_CASE in Neo4j."""
        return v.strip().upper().replace(" ", "_")


class ExtractionResult(BaseModel):
    """The complete extraction output — what the LLM gives us per chunk."""
    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    source_chunk_id: Optional[str] = Field(
        default=None,
        description="ID of the text chunk this extraction came from",
    )


# ---------------------------------------------------------------------------.
# The Extraction Prompt — this is where the magic happens.
# ---------------------------------------------------------------------------.

EXTRACTION_PROMPT = """You are an expert knowledge graph engineer. Your task is to extract structured entities and relationships from the following text.

**RULES:**
1. Extract ONLY entities that fall into these categories: PERSON, ORG, PROJECT, SKILL, CONCEPT, LOCATION, EVENT
2. Each entity must have a canonical name, type, a short one-line description (max 200 chars), and a confidence score (0.0-1.0)
3. Each relationship must have a subject (entity name), predicate (verb in UPPER_SNAKE_CASE like FOUNDED, WORKS_AT, USES, BUILT_WITH, TEACHES), object (entity name), and confidence score (0.0-1.0)
4. Every entity mentioned in the relationships list MUST be declared in the entities list with its type and description. Be thorough.
5. Maximize Recall and Detail: Extract as many entities and relationships as possible from the text. Do not summarize or omit technical details, skills, tools used, affiliations, or specific project linkages.
6. Be precise — only extract what is explicitly stated or very strongly implied. Do NOT hallucinate.
7. If there is nothing to extract, return empty lists.

**OUTPUT FORMAT — return ONLY valid JSON, no markdown, no explanation:**
{{
  "entities": [
    {{
      "name": "Entity Name",
      "type": "PERSON|ORG|PROJECT|SKILL|CONCEPT|LOCATION|EVENT",
      "short_description": "Brief description in context",
      "confidence_score": 0.95
    }}
  ],
  "relationships": [
    {{
      "subject": "Entity A",
      "predicate": "RELATIONSHIP_VERB",
      "object": "Entity B",
      "confidence_score": 0.9
    }}
  ]
}}

**TEXT TO ANALYZE:**
{text}
"""


# ---------------------------------------------------------------------------.
# Retry Logic — exponential backoff for API resilience.
# ---------------------------------------------------------------------------.

def _retry_with_backoff(func, max_retries: int = 5, base_delay: float = 2.0):
    """
    Wraps an API call with exponential backoff.
    Retries on rate-limit (429) and transient server errors (500/503).
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            error_str = str(e).lower()

            # Check if it's a retryable error.
            is_rate_limit = "429" in error_str or "resource exhausted" in error_str or "rate limit" in error_str or "rate_limit" in error_str
            is_server_error = "500" in error_str or "503" in error_str

            if (is_rate_limit or is_server_error) and attempt < max_retries:
                # For rate limits, we wait significantly longer.
                if is_rate_limit:
                    delay = 30.0 + (attempt * 10.0) # Start at 30s for free tier quota resets
                else:
                    delay = base_delay * (2 ** attempt)
                
                logger.warning(
                    f"API call failed (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Retrying in {delay:.1f}s... Error: {e}"
                )
                time.sleep(delay)
            else:
                logger.error(f"API call failed permanently after {attempt + 1} attempts: {e}")
                raise


# ---------------------------------------------------------------------------.
# The Extractor — the core function.
# ---------------------------------------------------------------------------.

class EntityExtractor:
    """
    Uses Gemini Flash to extract entities and relationships from text.
    This is the quality ceiling of the entire RAG-View system.
    """

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=key) if key else None
        self.model_name = "gemini-2.0-flash"

        # Track stats for reporting.
        self.total_calls = 0
        self.total_entities_extracted = 0
        self.total_relationships_extracted = 0

    def extract(self, text: str, chunk_id: Optional[str] = None) -> ExtractionResult:
        """
        Extract entities and relationships from a single text chunk.

        Args:
            text: The raw text to analyze.
            chunk_id: Optional ID to tag the extraction back to its source.

        Returns:
            ExtractionResult with validated entities and relationships.
        """
        if not text or not text.strip():
            logger.warning("Empty text passed to extractor, skipping.")
            return ExtractionResult(source_chunk_id=chunk_id)

        if db.is_dry_run or os.getenv("DRY_RUN") == "true":
            logger.info("[DRY RUN] Bypassing LLM API for entity extraction.")
            return ExtractionResult(
                entities=[Entity(name="WhySchool", type="ORG", short_description="AI startup", confidence_score=0.95)],
                relationships=[Relationship(subject="WhySchool", predicate="USES", object="AI", confidence_score=0.9)],
                source_chunk_id=chunk_id
            )

        prompt = EXTRACTION_PROMPT.format(text=text)

        def _call_llm():
            provider = os.getenv("LLM_PROVIDER", "gemini").lower()
            if provider == "groq":
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    raise ValueError("GROQ_API_KEY is missing from .env")
                import requests
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    "messages": [
                        {"role": "system", "content": "You are an expert knowledge graph engineer. You must output ONLY raw, valid JSON. Do NOT use markdown formatting. Do NOT wrap the output in ```json blocks."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048,
                    "response_format": {"type": "json_object"}
                }
                
                import time
                for attempt in range(4):
                    try:
                        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                        if res.status_code == 200:
                            return res.json()["choices"][0]["message"]["content"]
                        elif res.status_code == 429:
                            if attempt == 3:
                                raise Exception("Groq API 429 Rate Limit Error after 4 attempts.")
                            wait_sec = 2 ** attempt
                            logger.warning(f"Groq API 429 Rate Limit in extractor. Retrying in {wait_sec}s...")
                            time.sleep(wait_sec)
                        else:
                            if attempt == 3:
                                raise Exception(f"Groq API Error: {res.text}")
                            time.sleep(1)
                    except Exception as e:
                        if attempt == 3:
                            raise e
                        time.sleep(1)

            elif provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY is missing from .env")
                import requests
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [
                        {"role": "system", "content": "You are an expert knowledge graph engineer. You must output ONLY raw, valid JSON. Do NOT use markdown formatting. Do NOT wrap the output in ```json blocks."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048,
                    "response_format": {"type": "json_object"}
                }
                res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
                else:
                    raise Exception(f"OpenAI API Error: {res.text}")

            elif provider == "ollama":
                ollama_url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
                import requests
                payload = {
                    "model": os.getenv("OLLAMA_MODEL", "llama3"),
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
                res = requests.post(f"{ollama_url.rstrip('/')}/api/generate", json=payload, timeout=300)
                if res.status_code == 200:
                    return res.json()["response"]
                else:
                    raise Exception(f"Ollama API Error: {res.text}")

            else:
                # Default Gemini.
                if not self.client:
                    raise ValueError("GEMINI_API_KEY is missing from .env")
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=2048,
                    ),
                )
                return response.text

        # Call with retry logic.
        raw_response = _retry_with_backoff(_call_llm)

        # Parse and validate.
        result = self._parse_response(raw_response, chunk_id)

        # Update stats.
        self.total_calls += 1
        self.total_entities_extracted += len(result.entities)
        self.total_relationships_extracted += len(result.relationships)

        logger.info(
            f"Extracted {len(result.entities)} entities and "
            f"{len(result.relationships)} relationships from chunk '{chunk_id}'"
        )

        return result

    def _parse_response(
        self, raw: str, chunk_id: Optional[str] = None
    ) -> ExtractionResult:
        """
        Parse the raw LLM response into a validated ExtractionResult.
        Handles common LLM quirks like markdown code fences.
        """
        cleaned = raw.strip()

        # Strip markdown code fences if the LLM wraps its JSON.
        if cleaned.startswith("```"):
            # Remove opening fence (```json or ```).
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response was: {raw}")
            return ExtractionResult(source_chunk_id=chunk_id)

        # Validate through Pydantic.
        try:
            result = ExtractionResult(
                entities=data.get("entities", []),
                relationships=data.get("relationships", []),
                source_chunk_id=chunk_id,
            )
        except Exception as e:
            logger.error(f"Pydantic validation failed: {e}")
            logger.debug(f"Parsed data was: {data}")
            return ExtractionResult(source_chunk_id=chunk_id)

        # Post-validation: ensure relationship endpoints exist in entities.
        entity_names = {e.name for e in result.entities}
        valid_relationships = []
        for rel in result.relationships:
            subject_clean = rel.subject.strip().title()
            object_clean = rel.object.strip().title()
            if not subject_clean or not object_clean:
                logger.warning(f"Dropping relationship '{rel.subject} -> {rel.predicate} -> {rel.object}' because of empty entity names.")
                continue

            # Update names to clean versions just in case.
            rel.subject = subject_clean
            rel.object = object_clean

            # If subject not in entity_names, add it as a CONCEPT entity.
            if subject_clean not in entity_names:
                result.entities.append(Entity(
                    name=subject_clean,
                    type=EntityType.CONCEPT,
                    short_description=f"Auto-extracted entity from relationship: {rel.predicate}",
                    confidence_score=rel.confidence_score
                ))
                entity_names.add(subject_clean)
                logger.info(f"Auto-added missing subject entity: {subject_clean}")

            # If object not in entity_names, add it as a CONCEPT entity.
            if object_clean not in entity_names:
                result.entities.append(Entity(
                    name=object_clean,
                    type=EntityType.CONCEPT,
                    short_description=f"Auto-extracted entity from relationship: {rel.predicate}",
                    confidence_score=rel.confidence_score
                ))
                entity_names.add(object_clean)
                logger.info(f"Auto-added missing object entity: {object_clean}")

            valid_relationships.append(rel)
        result.relationships = valid_relationships

        return result

    def get_stats(self) -> dict:
        """Return extraction statistics for reporting."""
        return {
            "total_api_calls": self.total_calls,
            "total_entities_extracted": self.total_entities_extracted,
            "total_relationships_extracted": self.total_relationships_extracted,
        }

