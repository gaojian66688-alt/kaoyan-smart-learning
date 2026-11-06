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
            source_info="National Examination Center: Sample Verified Source",
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
                evidence_sentence="This is authentic evidence sentence directly found in passage.",
                explanation="Detailed authentic explanation for this question.",
                verifier="Curriculum Reviewer",
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

    def test_qa_gate_rejects_missing_source(self):
        """验收规则 1: 真题来源缺失时必须拦截发布"""
        test_grp_id = f"test-no-source-{uuid.uuid4().hex[:8]}"
        grp = QuestionGroup(
            id=test_grp_id,
            section_id="2024-english-1-sec-reading-a",
            exam_id="2024-english-1",
            group_type="reading_a",
            title="Missing Source Text",
            source_info="", # 缺失真题来源
            passage_text="This is a valid long passage about economic development and technology. " * 5,
            order_index=98,
            qa_status="pending"
        )
        self.db.add(grp)
        for num in range(21, 26):
            q = Question(
                id=f"{test_grp_id}-q{num}",
                group_id=test_grp_id,
                question_num=num,
                prompt=f"Prompt for #{num}?",
                options_json=json.dumps([{"key": "A", "text": f"Opt A {num}"}, {"key": "B", "text": f"Opt B {num}"}, {"key": "C", "text": f"Opt C {num}"}, {"key": "D", "text": f"Opt D {num}"}]),
                score=2.0,
                order_index=num
            )
            self.db.add(q)
            ak = AnswerKey(
                id=f"ak-{q.id}",
                question_id=q.id,
                correct_answer="A",
                evidence_sentence="This is authentic evidence sentence directly found in passage.",
                explanation="Detailed genuine explanation.",
                verifier="Curriculum Reviewer",
                status="verified"
            )
            self.db.add(ak)
        self.db.commit()

        res = ContentQAGate.validate_question_group(self.db, test_grp_id)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("真题来源缺失" in e for e in res.errors))

        # 清理
        self.db.query(AnswerKey).filter(AnswerKey.question_id.like(f"{test_grp_id}%")).delete()
        self.db.query(Question).filter(Question.group_id == test_grp_id).delete()
        self.db.query(QuestionGroup).filter(QuestionGroup.id == test_grp_id).delete()
        self.db.commit()

    def test_qa_gate_rejects_template_synthetic_content(self):
        """验收规则 2: 模板生成内容不能通过真题真实性门禁 (检测占位定位句与虚假审核记录)"""
        test_grp_id = f"test-syn-{uuid.uuid4().hex[:8]}"
        grp = QuestionGroup(
            id=test_grp_id,
            section_id="2024-english-1-sec-reading-a",
            exam_id="2024-english-1",
            group_type="reading_a",
            title="Synthetic Template Text",
            source_info="National Examination Center: Sample Verified Source",
            passage_text="This is a test passage that is sufficiently long for verification purposes. " * 5,
            order_index=97,
            qa_status="pending"
        )
        self.db.add(grp)
        for num in range(21, 26):
            q = Question(
                id=f"{test_grp_id}-q{num}",
                group_id=test_grp_id,
                question_num=num,
                prompt=f"According to paragraph {num-20}, what is noted?",
                options_json=json.dumps([
                    {"key": "A", "text": "foster structured institutional frameworks"},
                    {"key": "B", "text": "overlook critical qualitative nuances"},
                    {"key": "C", "text": "catalyze substantial advancements"},
                    {"key": "D", "text": "reinforce existing systemic imbalances"}
                ]),
                score=2.0,
                order_index=num
            )
            self.db.add(q)
            ak = AnswerKey(
                id=f"ak-{q.id}",
                question_id=q.id,
                correct_answer="A",
                evidence_sentence="Key evidence sentence cited from Paragraph 1 in Text 1.", # 占位定位句
                explanation="【正确项解析】选项 [A] 对原文关键论点进行了严密而准确的同义转述，逻辑严谨，论据充分。",
                verifier="Official Verification Panel", # 虚假硬编码审核记录
                status="verified"
            )
            self.db.add(ak)
        self.db.commit()

        res = ContentQAGate.validate_question_group(self.db, test_grp_id)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Official Verification Panel" in e for e in res.errors))
        self.assertTrue(any("模板占位定位句" in e for e in res.errors))
        self.assertTrue(any("重复选项模板" in e for e in res.errors))

        # 清理
        self.db.query(AnswerKey).filter(AnswerKey.question_id.like(f"{test_grp_id}%")).delete()
        self.db.query(Question).filter(Question.group_id == test_grp_id).delete()
        self.db.query(QuestionGroup).filter(QuestionGroup.id == test_grp_id).delete()
        self.db.commit()

    def test_qa_gate_rejects_duplicate_passages_across_years(self):
        """验收规则 3: 不同年份重复文章必须经过来源核查 (未经核查完全重复坚决拦截)"""
        # 获取现存 2024 英语一 Text 1 正文
        orig_grp = self.db.query(QuestionGroup).filter(QuestionGroup.id == "2024-english-1-reading-text-1").first()
        self.assertIsNotNone(orig_grp)

        test_grp_id = f"test-dup-{uuid.uuid4().hex[:8]}"
        dup_grp = QuestionGroup(
            id=test_grp_id,
            section_id="2023-english-1-sec-reading-a",
            exam_id="2023-english-1", # 跨年份冒充 2023 年试卷
            group_type="reading_a",
            title="Duplicate 2023 Text",
            source_info="National Examination Center: Sample Verified Source",
            passage_text=orig_grp.passage_text, # 完全照抄 2024 年文章
            order_index=1,
            qa_status="pending"
        )
        self.db.add(dup_grp)
        for num in range(21, 26):
            q = Question(
                id=f"{test_grp_id}-q{num}",
                group_id=test_grp_id,
                question_num=num,
                prompt=f"Question #{num}",
                options_json=json.dumps([{"key": "A", "text": f"A{num}"}, {"key": "B", "text": f"B{num}"}, {"key": "C", "text": f"C{num}"}, {"key": "D", "text": f"D{num}"}]),
                score=2.0,
                order_index=num
            )
            self.db.add(q)
            ak = AnswerKey(
                id=f"ak-{q.id}",
                question_id=q.id,
                correct_answer="A",
                evidence_sentence="This is authentic evidence sentence directly found in passage.",
                explanation="Genuine explanation text.",
                verifier="Curriculum Reviewer",
                status="verified"
            )
            self.db.add(ak)
        self.db.commit()

        res = ContentQAGate.validate_question_group(self.db, test_grp_id)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("存在完全重复文章" in e for e in res.errors))

        # 清理
        self.db.query(AnswerKey).filter(AnswerKey.question_id.like(f"{test_grp_id}%")).delete()
        self.db.query(Question).filter(Question.group_id == test_grp_id).delete()
        self.db.query(QuestionGroup).filter(QuestionGroup.id == test_grp_id).delete()
        self.db.commit()

if __name__ == "__main__":
    unittest.main()
