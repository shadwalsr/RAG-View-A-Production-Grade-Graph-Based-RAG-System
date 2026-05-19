import os
import sys
import logging
from dotenv import load_dotenv
from pypdf import PdfReader

# Ensure environment variables are loaded.
load_dotenv()

from src.pipeline import pipeline

# Configure logging.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")

def extract_text(filepath: str) -> str:
    """Extracts text from a given file path based on its extension."""
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == ".txt":
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext == ".pdf":
        text = ""
        try:
            reader = PdfReader(filepath)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Failed to read PDF {filepath}: {e}")
        return text
    return ""

def ingest_documents():
    """Reads all supported files from data/raw/ and runs them through the pipeline."""
    if not os.path.exists(RAW_DATA_DIR):
        os.makedirs(RAW_DATA_DIR)
        logger.info(f"Created directory: {RAW_DATA_DIR}. Please place your .txt or .pdf files here.")
        return

    # Support .
    valid_exts = (".txt", ".pdf")
    files = [f for f in os.listdir(RAW_DATA_DIR) if f.lower().endswith(valid_exts)]
    
    if not files:
        logger.info(f"No valid documents found in {RAW_DATA_DIR}. Please drop a sample document (.txt or .pdf) there.")
        return
        
    for filename in files:
        filepath = os.path.join(RAW_DATA_DIR, filename)
        logger.info(f"Reading document: {filename}")
        
        content = extract_text(filepath)
            
        if not content.strip():
            logger.warning(f"File {filename} is empty or unreadable. Skipping.")
            continue
            
        # Run the full pipeline (Chunking -> Extraction -> HybridStore -> Graph Embeddings.
        logger.info(f"Ingesting {filename} into RAG-View...")
        try:
            pipeline.run(raw_text=content, source_name=filename)
            logger.info(f"Successfully ingested {filename}!\n")
        except Exception as e:
            logger.error(f"Failed to ingest {filename}: {e}\n")

if __name__ == "__main__":
    ingest_documents()


