import json
import logging
import os
import pickle
from typing import Any, Dict, List, Optional

import chromadb
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

class HybridStore:
    """
    Manages Vector (ChromaDB) and Lexical (BM25) storage for text chunks.
    Bridges the flat text chunks with the Neo4j Graph via the 'entity_ids' metadata field.
    """
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 1.
        self.chroma_path = os.path.join(self.data_dir, "chroma")
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        # Using default embedding function (all-MiniLM-L6-v2).
        self.collection = self.chroma_client.get_or_create_collection(name="rag_chunks")
        
        # 2.
        self.bm25_path = os.path.join(self.data_dir, "bm25_index.pkl")
        self.corpus: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None
        self._load_bm25()

    def _load_bm25(self):
        """Loads the BM25 index and corpus from disk if it exists."""
        if os.path.exists(self.bm25_path):
            try:
                with open(self.bm25_path, "rb") as f:
                    data = pickle.load(f)
                    self.corpus = data.get("corpus", [])
                    self.bm25 = data.get("bm25", None)
                logger.info(f"Loaded BM25 index with {len(self.corpus)} chunks.")
            except Exception as e:
                logger.error(f"Failed to load BM25 index: {e}")
                self.corpus = []
                self.bm25 = None
        else:
            logger.info("No existing BM25 index found. Starting fresh.")

    def _save_bm25(self):
        """Saves the BM25 index and corpus to disk."""
        try:
            with open(self.bm25_path, "wb") as f:
                pickle.dump({"corpus": self.corpus, "bm25": self.bm25}, f)
        except Exception as e:
            logger.error(f"Failed to save BM25 index: {e}")

    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace/lowercase tokenization for BM25."""
        return text.lower().split()

    def add_chunk(self, chunk_id: str, text: str, entity_ids: List[str], metadata: Dict[str, Any] = None):
        """
        Adds a single text chunk to both ChromaDB and BM25.
        
        Args:
            chunk_id: Unique identifier for the chunk.
            text: The raw text of the chunk.
            entity_ids: List of Neo4j canonical entity names associated with this chunk.
            metadata: Any additional metadata (e.g., source).
        """
        meta = dict(metadata) if metadata else {}
        
        # ChromaDB metadata values must be str, int, float, or bool.
        # Serialize the list of entity_ids to a JSON string so it can be stored.
        meta["entity_ids"] = json.dumps(entity_ids)
        
        # Add to ChromaDB.
        try:
            self.collection.upsert(
                documents=[text],
                metadatas=[meta],
                ids=[chunk_id]
            )
        except Exception as e:
            logger.error(f"Failed to add chunk to ChromaDB: {e}")
            raise

        # Add to BM25 Corpus.
        # Check if updating an existing chunk in BM25 (rare but possible in upserts).
        existing_idx = next((i for i, c in enumerate(self.corpus) if c["id"] == chunk_id), None)
        
        chunk_data = {
            "id": chunk_id,
            "text": text,
            "metadata": meta
        }
        
        if existing_idx is not None:
            self.corpus[existing_idx] = chunk_data
        else:
            self.corpus.append(chunk_data)
            
        # Rebuild BM25 index (BM25Okapi does not support incremental updates).
        tokenized_corpus = [self._tokenize(doc["text"]) for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        # Persist BM25.
        self._save_bm25()
        logger.info(f"Added chunk '{chunk_id}' to HybridStore with {len(entity_ids)} linked entities.")

    def vector_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Performs semantic vector search using ChromaDB."""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        formatted_results = []
        if results and results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                meta = dict(results["metadatas"][0][i]) if results["metadatas"] and results["metadatas"][0][i] else {}
                # Deserialize entity_ids.
                if "entity_ids" in meta and isinstance(meta["entity_ids"], str):
                    try:
                        meta["entity_ids"] = json.loads(meta["entity_ids"])
                    except json.JSONDecodeError:
                        meta["entity_ids"] = []
                
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": meta,
                    "distance": results["distances"][0][i] if results.get("distances") else 0.0
                })
        return formatted_results

    def keyword_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Performs exact keyword matching using BM25."""
        if not self.bm25 or not self.corpus:
            return []
            
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top_k indices sorted by score descending.
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        formatted_results = []
        for idx in top_indices:
            if scores[idx] > 0: # Only return if there is some match
                chunk = self.corpus[idx]
                meta = dict(chunk["metadata"])
                
                # Deserialize entity_ids.
                if "entity_ids" in meta and isinstance(meta["entity_ids"], str):
                    try:
                        meta["entity_ids"] = json.loads(meta["entity_ids"])
                    except json.JSONDecodeError:
                        meta["entity_ids"] = []
                
                formatted_results.append({
                    "id": chunk["id"],
                    "text": chunk["text"],
                    "metadata": meta,
                    "score": scores[idx]
                })
                
        return formatted_results

    def get_chunk_by_id(self, chunk_id: str) -> Optional[str]:
        """Fetches the raw text of a chunk by its ID across multi-process container boundaries."""
        # 1.
        for chunk in self.corpus:
            if chunk["id"] == chunk_id:
                return chunk["text"]
        
        # 2.
        self._load_bm25()
        for chunk in self.corpus:
            if chunk["id"] == chunk_id:
                return chunk["text"]
                
        # 3.
        try:
            res = self.collection.get(ids=[chunk_id])
            if res and res.get("documents") and len(res["documents"]) > 0:
                return res["documents"][0]
        except Exception as e:
            logger.error(f"Failed to fetch chunk {chunk_id} from ChromaDB: {e}")
            
        return None

    def clear(self):
        """Completely purges all data from ChromaDB and BM25 stores."""
        logger.info("Purging all data from HybridStore...")
        try:
            self.chroma_client.delete_collection("rag_chunks")
        except Exception as e:
            logger.warning(f"ChromaDB delete_collection error (may not exist): {e}")
        
        # Reinitialize client to avoid stale collection handle.
        try:
            self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
            self.collection = self.chroma_client.get_or_create_collection(name="rag_chunks")
            logger.info("ChromaDB collection reinitialized successfully.")
        except Exception as e:
            logger.error(f"Failed to reinitialize ChromaDB collection: {e}")
            
        self.corpus = []
        self.bm25 = None
        if os.path.exists(self.bm25_path):
            try:
                os.remove(self.bm25_path)
            except Exception as e:
                logger.error(f"Failed to delete BM25 index file: {e}")

# Global instance.
hybrid_store = HybridStore()

