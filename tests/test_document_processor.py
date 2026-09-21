"""
Tests for Document Processor (Phase 1)
Validates Chunk contract compliance, deterministic IDs, page number preservation,
and JSON cache round-trip.
"""

import os
import json
import unittest
from src.ingestion.document_processor import (
    extract_pdf_content,
    extract_slide_content,
    save_extracted_chunks,
    load_cached_chunks,
    generate_chunk_id,
    split_page_into_paragraphs,
    Chunk
)

class TestDocumentProcessor(unittest.TestCase):

    def setUp(self):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.notes_path = os.path.join(self.project_root, "data", "sample_media", "neural_networks_notes.pdf")
        self.slides_path = os.path.join(self.project_root, "data", "sample_media", "neural_networks_slides.pdf")
        self.test_cache_path = os.path.join(self.project_root, "data", "cache", "test_cache.json")

    def tearDown(self):
        if os.path.exists(self.test_cache_path):
            os.remove(self.test_cache_path)

    def test_chunk_contract_schema(self):
        """Every chunk must have all required fields with correct types."""
        chunks = extract_pdf_content(self.notes_path, source_name="Lecture 3 Notes")
        self.assertGreater(len(chunks), 0, "Should extract at least one chunk")

        required_keys = {"id", "text", "source_type", "source_name", "location", "location_kind"}
        for chunk in chunks:
            self.assertEqual(set(chunk.keys()), required_keys, f"Chunk missing or has extra keys: {chunk}")
            self.assertIsInstance(chunk["id"], str)
            self.assertIsInstance(chunk["text"], str)
            self.assertIsInstance(chunk["source_type"], str)
            self.assertIsInstance(chunk["source_name"], str)
            self.assertIsInstance(chunk["location"], str)
            self.assertIsInstance(chunk["location_kind"], str)

            self.assertEqual(chunk["source_type"], "pdf")
            self.assertEqual(chunk["location_kind"], "page")
            self.assertTrue(chunk["location"].isdigit(), "Location must be a string representation of page number")
            self.assertGreater(len(chunk["text"].strip()), 20, "Chunk text should be meaningful content")

    def test_chunk_ids_are_deterministic_and_unique(self):
        """Chunk IDs must be deterministic (not random UUIDs) and unique across the document."""
        chunks1 = extract_pdf_content(self.notes_path, source_name="Lecture 3 Notes")
        chunks2 = extract_pdf_content(self.notes_path, source_name="Lecture 3 Notes")

        ids1 = [c["id"] for c in chunks1]
        ids2 = [c["id"] for c in chunks2]

        self.assertEqual(ids1, ids2, "IDs must be deterministic across runs")
        self.assertEqual(len(ids1), len(set(ids1)), "All chunk IDs within the document must be unique")

    def test_page_numbers_match_content(self):
        """Spot-check that content extracted matches the known page in the document."""
        chunks = extract_pdf_content(self.notes_path, source_name="Lecture 3 Notes")
        page_chunks = {c["location"]: c["text"] for c in chunks}

        # Page 1 contains 'Fundamentals of Gradient Descent' and 'Convex'
        self.assertIn("1", page_chunks)
        self.assertIn("Gradient Descent", page_chunks["1"])

        # Page 2 contains 'Learning Rate and Convergence Dynamics'
        self.assertIn("2", page_chunks)
        self.assertIn("Learning Rate", page_chunks["2"])

        # Page 3 contains 'Variants of Gradient Descent' (Batch, Mini-Batch, SGD)
        self.assertIn("3", page_chunks)
        self.assertIn("Batch", page_chunks["3"])

        # Page 4 contains 'Adam' and 'Momentum'
        self.assertIn("4", page_chunks)
        self.assertIn("Adam", page_chunks["4"])

    def test_slide_content_extraction(self):
        """Test slide extraction preserves slide numbers and source type."""
        slides = extract_slide_content(self.slides_path, source_name="Lecture 3 Slides")
        self.assertEqual(len(slides), 6, "Should extract 6 slide chunks")

        for slide in slides:
            self.assertEqual(slide["source_type"], "slide")
            self.assertEqual(slide["location_kind"], "page")
            self.assertTrue(1 <= int(slide["location"]) <= 6)

        # Slide 5 should cover Momentum
        slide_5 = [s for s in slides if s["location"] == "5"][0]
        self.assertIn("Momentum", slide_5["text"])

        # Slide 6 should cover AdamW
        slide_6 = [s for s in slides if s["location"] == "6"][0]
        self.assertIn("AdamW", slide_6["text"])

    def test_cache_round_trip(self):
        """Ensure chunks can be saved to disk and reloaded identically."""
        chunks = extract_pdf_content(self.notes_path, source_name="Lecture 3 Notes")
        save_extracted_chunks(chunks, self.test_cache_path)

        reloaded = load_cached_chunks(self.test_cache_path)
        self.assertEqual(chunks, reloaded)

    def test_missing_file_raises_error(self):
        """Confirm clear error handling for non-existent file path."""
        with self.assertRaises(FileNotFoundError):
            extract_pdf_content("data/sample_media/does_not_exist.pdf", "Ghost Notes")


if __name__ == "__main__":
    unittest.main()
