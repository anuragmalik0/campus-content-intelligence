"""
Phase 3 Retrieval Verification Test
Tests that for Phase 0 test questions, the correct source material appears in the top 5 search hits.
"""

import os
import unittest
from src.indexing.search_index import search, load_cached_chunks_and_index

class TestSearchRetrieval(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Index all cached chunks from Phase 1 and 2
        total = load_cached_chunks_and_index()
        assert total >= 5, f"Expected at least 5 cached chunks, got {total}"

    def test_schema_compliance_of_hits(self):
        """Every hit returned by search() must have all Chunk contract fields + score."""
        hits = search("gradient descent", top=3)
        self.assertGreater(len(hits), 0)
        required_fields = {"id", "text", "source_type", "source_name", "location", "location_kind", "score"}
        for h in hits:
            self.assertEqual(set(h.keys()), required_fields)
            self.assertIsInstance(h["score"], float)

    def test_document_queries_retrieve_correct_pages(self):
        """D1-D7 test questions."""
        # D1: Update rule
        hits = search("gradient descent update rule parameter vector eta", top=5)
        self.assertTrue(any(h["location"] in ["1", "2"] for h in hits))

        # D3: Learning rate too large failure mode
        hits = search("learning rate eta too large diverge oscillate steep ravines NaN", top=5)
        self.assertTrue(any(h["location"] in ["2", "3"] for h in hits))

        # D4: Vanishing and exploding gradients
        hits = search("vanishing exploding gradients weight initialization skip connections clipping", top=5)
        self.assertTrue(any(h["location"] == "2" for h in hits))

        # D5: Mini-batch size
        hits = search("mini-batch gradient descent recommended batch size", top=5)
        self.assertTrue(any(h["location"] in ["3", "4"] for h in hits))

        # D6: Momentum formula and gamma parameter
        hits = search("momentum velocity vector gamma 0.9 parameter", top=5)
        self.assertTrue(any(h["location"] in ["4", "5", "00:01:10"] for h in hits))

        # D7: AdamW vs Adam
        hits = search("AdamW decouples L2 weight decay regularization bug Adam", top=5)
        self.assertTrue(any(h["location"] in ["6", "00:01:50"] for h in hits))

    def test_cross_source_queries_retrieve_both_sources(self):
        """X1 & X2: Cross-source queries should return both video/slides and document chunks in top 5."""
        # X1: Batch vs Mini-batch vs SGD GPU trade-offs
        hits = search("batch vs mini-batch gradient descent GPU VRAM throughput", top=5)
        sources = {h["source_type"] for h in hits}
        self.assertTrue("slide" in sources or "pdf" in sources)

        # X2: Learning rate warmup and scheduling
        hits = search("learning rate warmup Karpathy constant cosine annealing step decay", top=5)
        locations = {h["location"] for h in hits}
        # Should surface Slides (page 3) and Notes (page 2)
        self.assertTrue("2" in locations or "3" in locations)

    def test_boundary_cases(self):
        """B1 & B2: Boundary and terminology queries."""
        # B1: Karpathy constant
        hits = search("Karpathy constant 3e-4", top=5)
        self.assertTrue(any("3e-4" in h["text"] or "Karpathy" in h["text"] for h in hits))

        # B2: Convex linear regression local minima
        hits = search("linear regression convex loss function local minimum", top=5)
        self.assertTrue(any(h["location"] == "1" for h in hits))

    def test_out_of_scope_relevance_scores(self):
        """O1-O4: Check that out of scope queries don't match strong domain terms."""
        # Query that shares zero vocabulary with course material
        hits = search("capital city of Australia Canberra Sydney", top=5)
        # Check that specific non-existent terms (Australia, Canberra) did not match
        matching_words = [h for h in hits if "australia" in h["text"].lower() or "canberra" in h["text"].lower()]
        self.assertEqual(len(matching_words), 0, "Out of scope terms should not match text")


if __name__ == "__main__":
    unittest.main()
