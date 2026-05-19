import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class TextProcessor:
    """Handles splitting raw text into chunks for extraction."""
    
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, source_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Hybrid Chunking: Respects structural paragraph breaks first, 
        and falls back to word-boundary sliding windows for massive paragraphs.
        Returns a list of dicts: {"id": str, "text": str, "metadata": dict}
        """
        if not text:
            return []

        import re
        paragraphs = [p.strip() for p in re.split(r'\n\n+', text) if p.strip()]
        chunks = []
        current_chunk_text = ""

        # Approximate overlap in words for the fallback (avg 6 chars per word).
        overlap_words = max(1, self.chunk_overlap // 6)

        def _word_boundary_split(long_text: str) -> List[str]:
            words = long_text.split()
            sub_chunks = []
            curr_sub = []
            curr_len = 0
            i = 0
            while i < len(words):
                word = words[i]
                if curr_len + len(word) + 1 > self.chunk_size and curr_sub:
                    sub_chunks.append(" ".join(curr_sub))
                    # Apply overlap, but never go back further than 1 position behind current.
                    overlap_start = max(0, i - overlap_words)
                    # Safety: ensure we always make forward progress.
                    if overlap_start <= (i - len(curr_sub)):
                        overlap_start = i  # No overlap if it would cause backtracking
                    i = overlap_start
                    curr_sub = []
                    curr_len = 0
                    continue
                curr_sub.append(word)
                curr_len += len(word) + 1
                i += 1
            if curr_sub:
                sub_chunks.append(" ".join(curr_sub))
            return sub_chunks

        for para in paragraphs:
            # If the paragraph itself is too large, process what we have, then split the parag.
            if len(para) > self.chunk_size:
                if current_chunk_text:
                    chunks.append(current_chunk_text.strip())
                    current_chunk_text = ""
                
                # Split this massive paragraph using word boundaries.
                sub_chunks = _word_boundary_split(para)
                chunks.extend(sub_chunks)
                continue

            # If adding this paragraph exceeds the chunk size, save current and start new.
            potential_len = len(current_chunk_text) + len(para) + 2 # +2 for \n\n
            if potential_len > self.chunk_size and current_chunk_text:
                chunks.append(current_chunk_text.strip())
                current_chunk_text = para
            else:
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para
                else:
                    current_chunk_text = para
        
        if current_chunk_text:
            chunks.append(current_chunk_text.strip())

        result = []
        for c in chunks:
            chunk_id = f"chunk_{uuid.uuid4().hex[:8]}"
            result.append({
                "id": chunk_id,
                "text": c,
                "metadata": source_metadata or {}
            })
            
        logger.info(f"Split text into {len(result)} hybrid structural chunks.")
        return result

text_processor = TextProcessor()

