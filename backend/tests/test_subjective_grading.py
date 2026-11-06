import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
import uuid
from app.database import SessionLocal, Base, engine
from app.models.practice import Attempt, Response, Submission, GradeResult
from app.models.exam import Question, AnswerKey
from app.core.grading_engine import GradingEngine, SubjectiveEvaluator

class TestSubjectiveGrading(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self.user_id = f"test_subj_user_{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        self.db.query(GradeResult).filter(GradeResult.submission_id.in_(
            self.db.query(Submission.id).filter(Submission.attempt_id.in_(
                self.db.query(Attempt.id).filter(Attempt.user_id == self.user_id)
            ))
        )).delete(synchronize_session=False)
        self.db.query(Submission).filter(Submission.attempt_id.in_(
            self.db.query(Attempt.id).filter(Attempt.user_id == self.user_id)
        )).delete(synchronize_session=False)
        self.db.query(Response).filter(Response.attempt_id.in_(
            self.db.query(Attempt.id).filter(Attempt.user_id == self.user_id)
        )).delete(synchronize_session=False)
        self.db.query(Attempt).filter(Attempt.user_id == self.user_id).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_subjective_translation_grading(self):
        """PRD 8.4: 翻译主观题分档估分与估分性质标记"""
        # 测试 2024 英语一 翻译 Q46
        att_id = str(uuid.uuid4())
        att = Attempt(
            id=att_id,
            user_id=self.user_id,
            mode="special_training",
            target_type="group",
            target_id="2024-english-1-trans-group",
            status="in_progress"
        )
        self.db.add(att)

        # 用户作答 Q46
        r = Response(
            id=str(uuid.uuid4()),
            attempt_id=att_id,
            question_id="2024-english-1-trans-q46",
            user_answer="长久以来，相关专业素养在该领域一直被视为专家独有的，而不是高等教育者知识底蕴中不可或缺的组成部分。",
            is_final_snapshot=False
        )
        self.db.add(r)
        self.db.commit()

        sub = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=att_id,
            scope="group",
            scope_id="2024-english-1-trans-group",
            user_id=self.user_id
        )

        self.assertGreater(sub.subjective_score, 0.0)
        self.assertEqual(sub.objective_score, 0.0)
        
        gr_46 = next(g for g in sub.grade_results if g.question_id == "2024-english-1-trans-q46")
        self.assertTrue(gr_46.is_estimated) # 必须明确标记估分性质
        self.assertIn("一类档", gr_46.score_band)
        self.assertGreaterEqual(gr_46.score, 1.5)

    def test_subjective_writing_grading(self):
        """PRD 8.4: 作文主观题词数与三段论分档估分"""
        att_id = str(uuid.uuid4())
        att = Attempt(
            id=att_id,
            user_id=self.user_id,
            mode="special_training",
            target_type="group",
            target_id="2024-english-1-writing-a-group",
            status="in_progress"
        )
        self.db.add(att)

        sample_notice = (
            "Notice\n\n"
            "To promote environmental sustainability and foster eco-friendly habits, "
            "the Student Union is proud to launch our annual campus green-living campaign. "
            "This initiative aims to cultivate eco-consciousness and reduce resource waste across our student community.\n\n"
            "We warmly invite all students to actively take part in two featured activities. "
            "First, a second-hand book fair will be held this Saturday on the central plaza, "
            "encouraging knowledge reuse and minimizing paper waste. "
            "Second, a low-carbon cycling relay will commence on Sunday morning, "
            "rewarding participants with eco-commemorative badges for every clean kilometer logged.\n\n"
            "Let us join hands to build a greener and more vibrant campus environment!\n\n"
            "The Student Union\n"
            "Li Ming"
        )

        r = Response(
            id=str(uuid.uuid4()),
            attempt_id=att_id,
            question_id="2024-english-1-writing-q51",
            user_answer=sample_notice,
            is_final_snapshot=False
        )
        self.db.add(r)
        self.db.commit()

        sub = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=att_id,
            scope="group",
            scope_id="2024-english-1-writing-a-group",
            user_id=self.user_id
        )

        gr_51 = next(g for g in sub.grade_results if g.question_id == "2024-english-1-writing-q51")
        self.assertTrue(gr_51.is_estimated)
        self.assertIn("一档", gr_51.score_band)
        self.assertGreaterEqual(gr_51.score, 8.0)

    def test_subjective_evaluation_not_only_word_count(self):
        """验收规则 9: 主观题评分不能只依据词数和段落数量，必须综合考量词汇多样性、逻辑连贯性与语义准确度"""
        ak_write = self.db.query(AnswerKey).filter(AnswerKey.question_id == "2024-english-1-writing-q52").first()
        self.assertIsNotNone(ak_write)

        # 测试场景 1：机械重复 180 词（反复复制 'good'，分 3 段）
        repetitive_text = ("good " * 60 + "\n\n") * 3
        score, band, feedback = SubjectiveEvaluator.evaluate_writing(repetitive_text, ak_write, max_score=20.0)
        
        # 核心断言：虽然词数达到 180 词且分为 3 段，但由于词汇多样性接近于 0 且无逻辑词，被判定为机械重复并惩罚至低分档
        self.assertLessEqual(score, 5.0)
        self.assertIn("机械重复", band)
        self.assertIn("词汇丰富度极低", feedback)

        # 测试场景 2：翻译未作答或无有效汉字，不得给出虚假分数
        ak_trans = self.db.query(AnswerKey).filter(AnswerKey.question_id == "2024-english-1-trans-q46").first()
        self.assertIsNotNone(ak_trans)

        empty_score, empty_band, empty_feedback = SubjectiveEvaluator.evaluate_translation("   ", ak_trans, max_score=2.0)
        self.assertEqual(empty_score, 0.0)
        self.assertEqual(empty_band, "未作答")
        self.assertIn("缺乏评分依据", empty_feedback)

        nonsense_score, nonsense_band, _ = SubjectiveEvaluator.evaluate_translation("abc def 123", ak_trans, max_score=2.0)
        self.assertEqual(nonsense_score, 0.0)
        self.assertEqual(nonsense_band, "缺乏评分依据")

if __name__ == "__main__":
    unittest.main()
