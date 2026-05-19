import logging
from typing import List

logger = logging.getLogger(__name__)

class ContextAssembler:
    """
    Assembles retrieved document excerpts and knowledge graph relationships into an explicit,
    highly structured prompt context block designed to optimize LLM multi-hop reasoning.
    """
    def assemble(self, texts: List[str], relationships: List[str], query: str = None) -> str:
        logger.info("ContextAssembler structuring relationship-aware prompt block...")
        
        # Deduplicate and clean.
        clean_texts = list(dict.fromkeys([t.strip() for t in texts if t and t.strip()]))
        clean_rels = list(dict.fromkeys([r.strip() for r in relationships if r and r.strip()]))
        
        prompt = ""
        if query:
            prompt += f"USER QUERY: {query}\n\n"
            
        prompt += "=== INSTRUCTIONS FOR AI ===\n"
        prompt += "You are an advanced GraphRAG reasoning agent. To answer the user's query, synthesize information from both the structured Knowledge Graph facts and the unstructured document excerpts below. Pay special attention to multi-hop relationships connecting entities across different sources.\n\n"
        
        prompt += "=== STRUCTURED KNOWLEDGE GRAPH FACTS & KNOWLEDGE GRAPH RELATIONSHIPS ===\n"
        if clean_rels:
            for rel in clean_rels:
                prompt += f"- {rel}\n"
        else:
            prompt += "No direct graph relationships found.\n"
            
        prompt += "\n=== DOCUMENT EXCERPTS (RETRIEVED TEXT CHUNKS) ===\n"
        if clean_texts:
            for i, text in enumerate(clean_texts):
                prompt += f"[Source {i+1}]\n{text}\n\n"
        else:
            prompt += "No document excerpts found.\n"
            
        return prompt.strip()

# Global instance.
context_assembler = ContextAssembler()

