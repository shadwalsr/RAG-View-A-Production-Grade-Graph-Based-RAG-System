"""
Quick smoke test for the entity extractor.
Run: python -m poetry run python tests/test_extractor.py
"""

import sys
import os

# Add src to path so we can import.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

from extractor import EntityExtractor, ExtractionResult


SAMPLE_TEXT = """
Shadwal Singh is a software engineer who founded the RAG-View project.
He built it using Python, Neo4j, and Google Gemini. The system uses
FastAPI for the backend and React for the frontend. RAG-View is designed
to be a graph-powered document intelligence platform that provides
visual exploration of knowledge graphs.
"""


def test_extraction():
    print("=" * 60)
    print("  EXTRACTOR SMOKE TEST")
    print("=" * 60)

    extractor = EntityExtractor()
    result = extractor.extract(SAMPLE_TEXT, chunk_id="test_chunk_001")

    # Validate return type.
    assert isinstance(result, ExtractionResult), "Result must be ExtractionResult"

    print(f"\n📦 Entities extracted: {len(result.entities)}")
    for entity in result.entities:
        print(f"   • [{entity.type.value}] {entity.name} — {entity.short_description} (conf: {entity.confidence_score})")

    print(f"\n🔗 Relationships extracted: {len(result.relationships)}")
    for rel in result.relationships:
        print(f"   • {rel.subject} —[{rel.predicate}]→ {rel.object} (conf: {rel.confidence_score})")

    print(f"\n📊 Stats: {extractor.get_stats()}")

    # Basic assertions.
    assert len(result.entities) > 0, "Should extract at least one entity"
    assert result.source_chunk_id == "test_chunk_001", "Chunk ID should be preserved"

    print("\n✅ All assertions passed!")


if __name__ == "__main__":
    test_extraction()

