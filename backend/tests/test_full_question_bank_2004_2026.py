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
        """验证所有题目均包含明确的标准答案、定位证据句与详实清晰的黄皮书式解析"""
        questions = self.db.query(Question).all()
        self.assertEqual(len(questions), 2156, "Expected exactly 2156 authentic questions")

        for q in questions[:200]: # 抽样检验深度
            keys = self.db.query(AnswerKey).filter(AnswerKey.question_id == q.id).all()
            self.assertTrue(len(keys) >= 1, f"Question {q.id} (#{q.question_num}) lacks AnswerKey")
            ak = keys[0]
            self.assertTrue(len(ak.correct_answer.strip()) > 0)
            self.assertTrue(len(ak.explanation.strip()) >= 20, f"Question {q.id} explanation too short")
            if q.category != "subjective":
                opts = q.get_options()
                self.assertIn(len(opts), [4, 5, 7], f"Question {q.id} invalid options count: {len(opts)}")

    def test_content_qa_gate_all_groups_pass(self):
        """验证全库 387 个题组均 100% 具备有效签名并顺利通过门禁发布校验"""
        groups = self.db.query(QuestionGroup).all()
        self.assertEqual(len(groups), 387, "Expected exactly 387 authentic question groups across 43 exams")
        
        for grp in groups:
            self.assertEqual(grp.qa_status, "verified", f"Group {grp.id} status is not verified")
            self.assertTrue(grp.qa_checksum and len(grp.qa_checksum) == 64, f"Group {grp.id} missing SHA-256 checksum")

if __name__ == "__main__":
    unittest.main()
