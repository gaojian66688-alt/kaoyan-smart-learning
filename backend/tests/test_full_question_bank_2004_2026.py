import unittest
import json
from app.database import SessionLocal
from app.models.exam import Exam, Section, QuestionGroup, Question, AnswerKey
from app.core.qa_gate import ContentQAGate

class TestFullQuestionBank2004To2026(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_all_43_exams_registered(self):
        """验证 2004-2026 全部 43 套考研英语一与英语二真题试卷全量注册"""
        en1_years = set(range(2004, 2027))
        en2_years = set(range(2007, 2027))

        db_en1 = {ex.year for ex in self.db.query(Exam).filter(Exam.exam_type == "english_1").all()}
        db_en2 = {ex.year for ex in self.db.query(Exam).filter(Exam.exam_type == "english_2").all()}

        self.assertEqual(en1_years - db_en1, set(), f"Missing English 1 years: {en1_years - db_en1}")
        self.assertEqual(en2_years - db_en2, set(), f"Missing English 2 years: {en2_years - db_en2}")
        self.assertEqual(len(db_en1), 23, "English 1 must have 23 years (2004-2026)")
        self.assertEqual(len(db_en2), 20, "English 2 must have 20 years (2007-2026)")

    def test_exam_structural_integrity(self):
        """验证每套试卷均包含完形、阅读A、新题型、翻译、小作文与大作文全部板块"""
        expected_sections = {"cloze", "reading_a", "reading_b", "translation", "writing_a", "writing_b"}
        all_exams = self.db.query(Exam).all()
        self.assertGreaterEqual(len(all_exams), 43)

        for ex in all_exams:
            sec_codes = {s.section_code for s in ex.sections}
            self.assertEqual(
                sec_codes, expected_sections,
                f"Exam {ex.id} ({ex.title}) missing sections: {expected_sections - sec_codes}"
            )

    def test_answers_and_explanations_transparent(self):
        """
        PRD G01 & P0 真实性验证：
        - 验证已上线真题 100% 具备权威标准答案、定位证据句、详细解析与真实核验人
        - 验证严禁使用虚构假审核 'Official Verification Panel'
        - 验证其余未完成逐题核验的试卷严格标记为 offline，绝不灌装虚假题目
        """
        published_exams = self.db.query(Exam).filter(Exam.status == "published").all()
        self.assertEqual(len(published_exams), 1, "Only verified 2024 English I is published")
        self.assertEqual(published_exams[0].id, "2024-english-1")

        offline_exams = self.db.query(Exam).filter(Exam.status == "offline").all()
        self.assertEqual(len(offline_exams), 42, "Expected 42 curriculum exams safely marked offline pending authentic data")

        # 验证所有入库试题均为经核验真题
        questions = self.db.query(Question).all()
        self.assertEqual(len(questions), 52, "Expected exactly 52 authentic questions in 2024 English I")

        for q in questions:
            keys = self.db.query(AnswerKey).filter(AnswerKey.question_id == q.id).all()
            self.assertEqual(len(keys), 1, f"Question {q.id} (#{q.question_num}) lacks 1:1 AnswerKey")
            ak = keys[0]
            self.assertTrue(len(ak.correct_answer.strip()) > 0)
            self.assertTrue(len(ak.explanation.strip()) >= 20, f"Question {q.id} explanation too short")
            self.assertNotEqual(ak.verifier, "Official Verification Panel", f"Question {q.id} contains banned fake verifier")
            if q.category != "subjective":
                opts = q.get_options()
                self.assertIn(len(opts), [4, 5, 7], f"Question {q.id} invalid options count: {len(opts)}")

    def test_content_qa_gate_all_groups_pass(self):
        """PRD 6.2: 验证全库已上线题组 100% 具备有效签名并通过门禁校验"""
        groups = self.db.query(QuestionGroup).all()
        self.assertEqual(len(groups), 9, "Expected exactly 9 verified question groups in published 2024 English I")
        
        for grp in groups:
            self.assertEqual(grp.qa_status, "verified", f"Group {grp.id} status is not verified")
            self.assertTrue(grp.qa_checksum and len(grp.qa_checksum) == 64, f"Group {grp.id} missing SHA-256 checksum")
            res = ContentQAGate.validate_question_group(self.db, grp.id, record_logs=False)
            self.assertTrue(res.is_valid, f"Group {grp.id} failed QA Gate validation: {res.errors}")

if __name__ == "__main__":
    unittest.main()
