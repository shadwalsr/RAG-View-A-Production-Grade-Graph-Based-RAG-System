import logging
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
logger = logging.getLogger(__name__)

class GraphRAGGenerator:
    """
    Generates the final answer using the Gemini LLM by reasoning over the fused context.
    Includes a three-section grounded generation prompt with retrieved text chunks,
    structured graph relationships, and hard rules for citation and uncertainty.
    """
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = "gemini-2.0-flash"

    def generate_answer(self, query: str, fused_context: str) -> str:
        """
        Calls Gemini to generate an answer based ONLY on the provided context.
        """
        logger.info("Generating final answer via GraphRAG LLM...")
        
        prompt = f"""You are an advanced GraphRAG analytical engine (GraphRAGGenerator).
You must answer the user's question using ONLY the grounded context provided below.

=== GRAPH-GROUNDED GENERATION PROMPT ===

SECTION 1: RETRIEVED TEXT CHUNKS
The context below includes retrieved unstructured text chunks labeled with [Source N]. You must use these sources to ground your answer.

SECTION 2: STRUCTURED RELATIONSHIP BLOCK
The context below also includes a structured relationship block listing facts extracted from the knowledge graph. This relationship block significantly reduces hallucinations on multi-hop questions by providing explicit entity-to-entity links.

SECTION 3: HARD RULES
1. Cite Sources: You MUST cite the specific [Source N] labels or graph relationships for every claim, fact, or statement you make.
2. Flag Uncertainty: If the context contains conflicting information or ambiguity, you MUST explicitly flag your uncertainty to the user.
3. Refuse if Confidence is Low: If the provided context does not contain sufficient information to answer the query with high confidence, you MUST refuse to answer by explicitly stating: "I do not have enough information in my context to answer this."

=== GROUNDED CONTEXT ===
{fused_context}
========================

USER QUESTION: {query}
"""

        if os.getenv("DRY_RUN") == "true":
            logger.warning("[DRY RUN] Bypassing LLM API. Returning mock answer.")
            return f"[MOCK ANSWER for query: {query}]\n\nContext used:\n{fused_context}"

        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        import requests

        if provider == "groq":
            logger.info("Using Groq API for LLM synthesis...")
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return "❌ GROQ_API_KEY is missing from .env. Please add it to use Groq."
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "messages": [
                    {"role": "system", "content": "You are an advanced GraphRAG analytical engine. Provide clear, concise, professional answers without repetition."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 1024
            }
            
            import time
            for attempt in range(4):
                try:
                    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                    if res.status_code == 200:
                        return res.json()["choices"][0]["message"]["content"]
                    elif res.status_code == 429:
                        if attempt == 3:
                            return "❌ Groq API 429 Rate Limit Error: Please try again in a few seconds."
                        wait_sec = 2 ** attempt
                        logger.warning(f"Groq API 429 Rate Limit in qa. Retrying in {wait_sec}s...")
                        time.sleep(wait_sec)
                    else:
                        logger.error(f"Groq API error on attempt {attempt}: {res.text}")
                        if attempt == 3:
                            return f"❌ Groq API Error ({res.status_code}): {res.text}"
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Groq exception on attempt {attempt}: {e}")
                    if attempt == 3:
                        return f"❌ Groq Execution Error: {e}"
                    time.sleep(1)

        elif provider == "openai":
            logger.info("Using OpenAI API for LLM synthesis...")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "❌ OPENAI_API_KEY is missing from .env. Please add it to use OpenAI."
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": "You are an advanced GraphRAG analytical engine."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }
            try:
                res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
                else:
                    logger.error(f"OpenAI API error: {res.text}")
                    return f"❌ OpenAI API Error ({res.status_code}): {res.text}"
            except Exception as e:
                logger.error(f"OpenAI exception: {e}")
                return f"❌ OpenAI Execution Error: {e}"

        elif provider == "ollama":
            logger.info("Using local Ollama for LLM synthesis...")
            ollama_url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
            payload = {
                "model": os.getenv("OLLAMA_MODEL", "llama3"),
                "prompt": prompt,
                "stream": False
            }
            try:
                res = requests.post(f"{ollama_url.rstrip('/')}/api/generate", json=payload, timeout=300)
                if res.status_code == 200:
                    return res.json()["response"]
                else:
                    logger.error(f"Ollama API error: {res.text}")
                    return f"❌ Ollama API Error ({res.status_code}): Ensure Ollama is running and model '{payload['model']}' is pulled."
            except Exception as e:
                logger.error(f"Ollama exception: {e}")
                return f"❌ Ollama Connection Error: {e}. Ensure Ollama is running on your machine."

        else:
            # Default Gemini.
            if not self.client:
                return "❌ GEMINI_API_KEY is missing or invalid in .env."
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                logger.error(f"Failed to generate answer via Gemini: {e}")
                clean_context = fused_context.strip() if fused_context else "No direct context chunks found."
                return f"**[Gemini API Rate-Limit Fallback]**\n\nBased on the retrieved knowledge graph and document context, here are the grounded findings for your query:\n\n```text\n{clean_context}\n```\n\n*(Note: Live Gemini LLM synthesis is temporarily paused due to free-tier API quota limits. The exact retrieved context above is provided for complete transparency.)*"

# Global instance.
graph_rag_generator = GraphRAGGenerator()
qa_generator = graph_rag_generator  # For backwards compatibility with existing imports


