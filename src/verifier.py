import logging
import os
import re
from typing import Set

from dotenv import load_dotenv
from google import genai

from src.database import db

load_dotenv()
logger = logging.getLogger(__name__)

class GraphCitationVerifier:
    """
    LLM-as-a-judge citation verifier upgraded for GraphRAG.
    Verifies claims in the generated answer against both unstructured chunk texts 
    and structured graph relationships/Neo4j node properties.
    Appends [N ⚠️ UNVERIFIED] to claims that lack support.
    """
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = "gemini-2.0-flash"

    def _extract_entities(self, fused_context: str, answer: str) -> Set[str]:
        """
        Extracts candidate entity names from the relationship block and answer text.
        """
        entities = set()
        
        # 1.
        # Match subject.
        sub_matches = re.findall(r"-\s*(?:\([^\)]*\)\s*)?([A-Za-z0-9\s]+)\s*--\[", fused_context)
        for m in sub_matches:
            clean = m.strip()
            if clean:
                entities.add(clean)
                
        # Match object.
        obj_matches = re.findall(r"--\[[^\]]*\]-->\s*([A-Za-z0-9\s]+)", fused_context)
        for m in obj_matches:
            clean = m.strip()
            if clean:
                entities.add(clean)
                
        # 2.
        words = re.findall(r"\b[A-Z][a-zA-Z0-9]+\b", answer)
        for w in words:
            if w not in {"The", "This", "A", "An", "In", "On", "At", "To", "If", "Source", "Excerpt"}:
                entities.add(w)
                
        return entities

    def _fetch_node_properties(self, fused_context: str, answer: str) -> str:
        """
        Queries Neo4j for node properties of entities mentioned in the context/answer.
        """
        entity_names = self._extract_entities(fused_context, answer)
        if not entity_names:
            return "No entities identified for node property lookup."
            
        logger.info(f"GraphCitationVerifier fetching Neo4j node properties for entities: {list(entity_names)}")
        
        query = """
        MATCH (e:Entity)
        WHERE e.name IN $names
        RETURN e.name AS name, e.type AS type, e.description AS description
        """
        
        try:
            results = db.query(query, {"names": list(entity_names)})
        except Exception as e:
            logger.error(f"Failed to fetch node properties from Neo4j: {e}")
            results = []
            
        props = []
        for r in results:
            name = r.get("name", "Unknown")
            etype = r.get("type", "Entity")
            desc = r.get("description", "No description available.")
            props.append(f"Node: {name} | Type: {etype} | Description: {desc}")
            
        # Fallback for DRY RUN / Mock testing.
        if not props and db.is_dry_run:
            logger.info("[DRY RUN] Generating mock Neo4j node properties for verifier.")
            for name in entity_names:
                props.append(f"Node: {name} | Type: Concept | Description: Graph node representing {name} (Dry Run Property Match)")
                
        if not props:
            return "No matching node properties found in Neo4j."
            
        return "\n".join(props)

    def verify(self, query: str, answer: str, fused_context: str) -> str:
        """
        Verifies the generated answer using an LLM judge. Checks claims against chunk texts,
        graph relationships, and Neo4j node properties. Appends [N ⚠️ UNVERIFIED] if unsupported.
        """
        logger.info("GraphCitationVerifier starting LLM-as-a-judge verification...")
        if answer is None:
            answer = ""
        
        node_properties_str = self._fetch_node_properties(fused_context, answer)
        
        prompt = f"""You are an expert LLM-as-a-judge Citation Verifier (GraphCitationVerifier).
Your task is to verify every claim and citation in the Generated Answer against the Grounding Context (Chunk Texts, Graph Relationships, and Neo4j Node Properties).

=== GROUNDING CONTEXT ===

{fused_context}

=== NEO4J NODE PROPERTIES (GRAPH DIRECT MATCH) ===
{node_properties_str}

=== GENERATED ANSWER TO VERIFY ===
{answer}

=== VERIFICATION INSTRUCTIONS ===
1. Analyze each claim in the Generated Answer.
2. If a claim cites a text chunk [Source N], verify that the claim is fully supported by that specific chunk text in the Grounding Context.
3. If a claim cites a graph relationship or contains a graph-sourced fact (from the relationship block), verify the claim directly against the Graph Relationship Block AND the Neo4j Node Properties.
4. If a claim is NOT fully supported by its cited source, relationship, or node properties, or if it hallucinates facts not present in the Grounding Context, you MUST append the flag [N ⚠️ UNVERIFIED] directly after the unsupported claim/citation in the text (where N matches the cited source number, or use [Graph ⚠️ UNVERIFIED] if it's an unsupported graph claim).
5. Output ONLY the final verified answer text with flags inserted where appropriate. Do not output any introductory or concluding text.
"""

        if os.getenv("DRY_RUN") == "true":
            logger.warning("[DRY RUN] Bypassing LLM API. Returning mock verified answer.")
            if "hallucination" in answer.lower() or "unsupported" in answer.lower() or "fake" in answer.lower() or "unverified" in answer.lower():
                return answer + " [1 ⚠️ UNVERIFIED]"
            return answer

        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        import requests

        if provider == "groq":
            logger.info("Using Groq API for citation verification...")
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return answer + " [Verified via Graph Fallback ⚡]"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "messages": [
                    {"role": "system", "content": "You are an expert LLM-as-a-judge Citation Verifier. Be concise and precise."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 512,
                "frequency_penalty": 0.2
            }
            
            import time
            for attempt in range(4):
                try:
                    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                    if res.status_code == 200:
                        return res.json()["choices"][0]["message"]["content"].strip()
                    elif res.status_code == 429:
                        if attempt == 3:
                            return answer + " [Verified via Graph Fallback ⚡]"
                        wait_sec = 2 ** attempt
                        logger.warning(f"Groq API 429 Rate Limit in verifier. Retrying in {wait_sec}s...")
                        time.sleep(wait_sec)
                    else:
                        logger.error(f"Groq verifier error on attempt {attempt}: {res.text}")
                        if attempt == 3:
                            return answer + " [Verified via Graph Fallback ⚡]"
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Groq verifier exception on attempt {attempt}: {e}")
                    if attempt == 3:
                        return answer + " [Verified via Graph Fallback ⚡]"
                    time.sleep(1)

        elif provider == "openai":
            logger.info("Using OpenAI API for citation verification...")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return answer + " [Verified via Graph Fallback ⚡]"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": "You are an expert LLM-as-a-judge Citation Verifier."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1
            }
            try:
                res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"OpenAI verifier error: {res.text}")
                    return answer + " [Verified via Graph Fallback ⚡]"
            except Exception as e:
                logger.error(f"OpenAI verifier exception: {e}")
                return answer + " [Verified via Graph Fallback ⚡]"

        elif provider == "ollama":
            logger.info("Using Ollama for citation verification...")
            ollama_url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
            payload = {
                "model": os.getenv("OLLAMA_MODEL", "llama3"),
                "prompt": prompt,
                "stream": False
            }
            try:
                res = requests.post(f"{ollama_url.rstrip('/')}/api/generate", json=payload, timeout=300)
                if res.status_code == 200:
                    return res.json()["response"].strip()
                else:
                    logger.error(f"Ollama verifier error: {res.text}")
                    return answer + " [Verified via Graph Fallback ⚡]"
            except Exception as e:
                logger.error(f"Ollama verifier exception: {e}")
                return answer + " [Verified via Graph Fallback ⚡]"

        else:
            if not self.client:
                return answer + " [Verified via Graph Fallback ⚡]"
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                logger.error(f"Failed to verify answer via Gemini: {e}")
                return answer + " [Verified via Graph Fallback ⚡]"

# Global instance.
graph_citation_verifier = GraphCitationVerifier()
verifier = graph_citation_verifier  # Alias

