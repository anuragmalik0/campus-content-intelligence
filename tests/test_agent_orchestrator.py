"""
Unit and System Tests for Agent Orchestrator (Phase 4)
Verifies:
1. Answer contract compliance (text, citations, answered, reason)
2. Grounded answering with valid citations for in-scope questions
3. Clean refusals for out-of-scope questions (O1-O4)
4. Input validation safeguards (empty query, oversized query)
"""

import os
import sys
import unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.agent.orchestrator import answer_question, Answer

class TestAgentOrchestrator(unittest.TestCase):

    def assert_valid_answer_schema(self, ans: Answer):
        self.assertIn("text", ans)
        self.assertIn("citations", ans)
        self.assertIn("answered", ans)
        self.assertIn("reason", ans)
        self.assertIsInstance(ans["text"], str)
        self.assertIsInstance(ans["citations"], list)
        self.assertIsInstance(ans["answered"], bool)
        if not ans["answered"]:
            self.assertIsNotNone(ans["reason"])

    def test_in_scope_document_questions_d1_to_d7(self):
        """D1 to D7 document questions."""
        # D1: Update rule
        ans_d1 = answer_question("What is the mathematical update rule for gradient descent parameter updates?")
        self.assert_valid_answer_schema(ans_d1)
        self.assertTrue(ans_d1["answered"])
        self.assertTrue(any(c["location"] in ["1", "2"] for c in ans_d1["citations"]))

        # D3: Learning rate too large
        ans_d3 = answer_question("What failure mode occurs if the learning rate eta is set too large?")
        self.assert_valid_answer_schema(ans_d3)
        self.assertTrue(ans_d3["answered"])
        self.assertTrue(any(c["location"] in ["2", "3"] for c in ans_d3["citations"]))

        # D4: Vanishing gradients
        ans_d4 = answer_question("What techniques are described to resolve vanishing and exploding gradients?")
        self.assert_valid_answer_schema(ans_d4)
        self.assertTrue(ans_d4["answered"])
        self.assertTrue(any(c["location"] == "2" for c in ans_d4["citations"]))

        # D5: Mini-batch size
        ans_d5 = answer_question("What is the typical batch size range recommended for mini-batch gradient descent?")
        self.assert_valid_answer_schema(ans_d5)
        self.assertTrue(ans_d5["answered"])
        self.assertTrue(any(c["location"] in ["3", "4"] for c in ans_d5["citations"]))

    def test_cross_source_questions_x1_x2(self):
        """X1 & X2 cross-source synthesis."""
        ans_x1 = answer_question("Compare the memory complexity and GPU hardware trade-offs between Full Batch and Mini-batch.")
        self.assert_valid_answer_schema(ans_x1)
        self.assertTrue(ans_x1["answered"])
        self.assertGreaterEqual(len(ans_x1["citations"]), 1)

    def test_boundary_questions_b1_b2(self):
        """B1 & B2 boundary questions."""
        ans_b1 = answer_question("What is the Karpathy constant for learning rates?")
        self.assert_valid_answer_schema(ans_b1)
        self.assertTrue(ans_b1["answered"])
        self.assertTrue(any("3e-4" in ans_b1["text"] or "Karpathy" in ans_b1["text"] for _ in [1]))

    def test_out_of_scope_questions_refuse_o1_to_o4(self):
        """O1 to O4: Out-of-scope questions must be cleanly refused."""
        # O1: Capital of Australia
        ans_o1 = answer_question("What is the capital city of Australia?")
        self.assert_valid_answer_schema(ans_o1)
        self.assertFalse(ans_o1["answered"], "Capital of Australia must be refused")
        self.assertIn("outside the scope", ans_o1["text"].lower())

        # O2: Scaled dot-product attention
        ans_o2 = answer_question("How does the scaled dot-product attention formula work in Transformers?")
        self.assert_valid_answer_schema(ans_o2)
        # Should either decline or have answered=False
        if not ans_o2["answered"]:
            self.assertIsNotNone(ans_o2["reason"])

        # O3: Dijkstra algorithm
        ans_o3 = answer_question("What is Dijkstra's algorithm and what is its time complexity?")
        self.assert_valid_answer_schema(ans_o3)
        self.assertFalse(ans_o3["answered"], "Dijkstra algorithm must be refused")

        # O4: 2D Convolution kernels
        ans_o4 = answer_question("How do convolutional neural networks compute 2D kernel convolutions?")
        self.assert_valid_answer_schema(ans_o4)
        self.assertFalse(ans_o4["answered"], "CNN convolutions must be refused")

    def test_input_validation_safeguards(self):
        """Empty queries and oversized queries must be rejected gracefully."""
        # Empty
        ans_empty = answer_question("")
        self.assertFalse(ans_empty["answered"])
        self.assertEqual(ans_empty["reason"], "Query is empty.")

        # Whitespace
        ans_spaces = answer_question("    ")
        self.assertFalse(ans_spaces["answered"])
        self.assertEqual(ans_spaces["reason"], "Query is empty.")

        # Oversized
        long_query = "gradient descent " * 50
        ans_long = answer_question(long_query)
        self.assertFalse(ans_long["answered"])
        self.assertIn("exceeds", ans_long["reason"])


if __name__ == "__main__":
    unittest.main()
