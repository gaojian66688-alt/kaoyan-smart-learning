import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
import uuid
import json
from app.database import SessionLocal, Base, engine
from app.models.exam import Exam, Section, QuestionGroup, Question, AnswerKey, ContentQALog
from app.core.qa_gate import ContentQAGate

class TestContentQAGate(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_qa_gate_valid_group(self):
        """AT-09 Part 1: 已核验的合法题组应顺利通过门禁并产生校验指纹"""
        res = ContentQAGate.validate_question_group(self.db, "2024-english-1-reading-text-1")
        self.assertTrue(res.is_valid, f"Validation failed: {res.errors}")
        self.assertGreater(len(res.checksum), 10)
        self.assertEqual(len(res.errors), 0)

    def test_qa_gate_rejects_missing_questions(self):
        """AT-09 Part 2: 阅读理解 A 节不足 5 题应坚决拦截发布"""
        test_grp_id = f"test-invalid-grp-{uuid.uuid4()}"
        grp = QuestionGroup(
            id=test_grp_id,
            section_id="2024-english-1-sec-reading-a",
            exam_id="2024-english-1",
            group_type="reading_a",
            title="Broken Text",
            passage_text="This is a test passage that is long enough to meet length requirement. " * 5,
            order_index=99,
            qa_status="pending"
        )
        self.db.add(grp)
        # 仅插入 2 道题，少于要求的 5 道题
        for num in [21, 22]:
            q = Question(
                id=f"{test_grp_id}-q{num}",
                group_id=test_grp_id,
                question_num=num,
                prompt="Sample prompt?",
                options_json=json.dumps([{"key": "A", "text": "1"}, {"key": "B", "text": "2"}, {"key": "C", "text": "3"}, {"key": "D", "text": "4"}]),
                score=2.0,
                order_index=num
            )
            self.db.add(q)
            ak = AnswerKey(
                id=f"ak-{q.id}",
                question_id=q.id,
                correct_answer="A",
                evidence_sentence="evidence",
                explanation="expl",
                status="verified"
            )
            self.db.add(ak)
        self.db.commit()

        res = ContentQAGate.validate_question_group(self.db, test_grp_id)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("must strictly contain 5 questions" in e for e in res.errors))

        # 检查日志留痕
        log = self.db.query(ContentQALog).filter(ContentQALog.target_id == test_grp_id).first()
        self.assertIsNotNone(log)
        self.assertFalse(log.passed)

        # 清理测试数据
        self.db.query(AnswerKey).filter(AnswerKey.question_id.like(f"{test_grp_id}%")).delete()
        self.db.query(Question).filter(Question.group_id == test_grp_id).delete()
        self.db.query(QuestionGroup).filter(QuestionGroup.id == test_grp_id).delete()
        self.db.query(ContentQALog).filter(ContentQALog.target_id == test_grp_id).delete()
        self.db.commit()

if __name__ == "__main__":
    unittest.main()
