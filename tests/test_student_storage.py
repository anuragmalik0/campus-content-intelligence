import sys
import uuid
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.ui.server import app
from src.services.student_service import (
    get_or_create_student,
    get_student_profile,
    record_quiz_progress,
    record_question_asked,
    list_all_students
)

client = TestClient(app)


class TestStudentStorage(unittest.TestCase):

    def setUp(self):
        self.run_id = uuid.uuid4().hex[:6]
        self.test_student_id = f"test_student_{self.run_id}"
        self.test_student_name = "Alex Test"
        self.test_department = "Computer Science & Engineering"

    def test_01_service_lifecycle(self):
        # 1. Create student
        student = get_or_create_student(
            student_id=self.test_student_id,
            name=self.test_student_name,
            department=self.test_department
        )
        self.assertEqual(student["student_id"], self.test_student_id)
        self.assertEqual(student["name"], self.test_student_name)
        self.assertEqual(student["stats"]["quizzes_taken"], 0)

        # 2. Record quiz
        updated = record_quiz_progress(
            student_id=self.test_student_id,
            quiz_record={
                "quiz_id": "q-101",
                "document_name": "Gradient_Descent_Notes.pdf",
                "topic": "Optimization Dynamics",
                "difficulty": "medium",
                "score": 4,
                "total": 5
            }
        )
        self.assertEqual(updated["stats"]["quizzes_taken"], 1)
        self.assertEqual(updated["stats"]["quizzes_passed"], 1)
        self.assertEqual(updated["stats"]["average_score_pct"], 80.0)
        self.assertEqual(len(updated["quiz_history"]), 1)

        # 3. Record query
        updated_query = record_question_asked(
            student_id=self.test_student_id,
            question="What is the learning rate?"
        )
        self.assertEqual(updated_query["stats"]["questions_asked"], 1)
        self.assertEqual(len(updated_query["recent_queries"]), 1)

        # 4. Fetch profile
        fetched = get_student_profile(self.test_student_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["student_id"], self.test_student_id)

    def test_02_api_login_and_profile(self):
        # Login API
        res = client.post(
            "/api/student/login",
            json={
                "student_id": self.test_student_id,
                "name": "Sarah Lin",
                "department": "Biotechnology & Bioinformatics",
                "email": f"{self.test_student_id}@campus.edu"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["student_id"], self.test_student_id)
        self.assertEqual(data["department"], "Biotechnology & Bioinformatics")

        # Get Profile API
        res_prof = client.get(f"/api/student/profile/{self.test_student_id}")
        self.assertEqual(res_prof.status_code, 200)
        prof_data = res_prof.json()
        self.assertEqual(prof_data["name"], "Sarah Lin")

    def test_03_api_record_quiz_and_query(self):
        # Ensure student exists
        client.post(
            "/api/student/login",
            json={
                "student_id": self.test_student_id,
                "name": "Sarah Lin",
                "department": "Biotechnology & Bioinformatics"
            }
        )

        # Record quiz via API
        res_quiz = client.post(
            "/api/student/record-quiz",
            json={
                "student_id": self.test_student_id,
                "quiz_id": "quiz-bio-1",
                "document_name": "Bio_Genomics_Lec3.pdf",
                "topic": "CRISPR Genome Editing",
                "difficulty": "hard",
                "score": 5,
                "total": 5
            }
        )
        self.assertEqual(res_quiz.status_code, 200)
        quiz_data = res_quiz.json()
        self.assertTrue(quiz_data["success"])
        self.assertEqual(quiz_data["profile"]["stats"]["average_score_pct"], 100.0)

        # Record question via API
        res_query = client.post(
            "/api/student/record-query",
            json={
                "student_id": self.test_student_id,
                "question": "How does Cas9 bind to target DNA?"
            }
        )
        self.assertEqual(res_query.status_code, 200)
        self.assertTrue(res_query.json()["success"])

        # Check list endpoint
        res_list = client.get("/api/student/list")
        self.assertEqual(res_list.status_code, 200)
        list_data = res_list.json()
        student_ids = [s["student_id"] for s in list_data["students"]]
        self.assertIn(self.test_student_id, student_ids)


if __name__ == "__main__":
    unittest.main()
