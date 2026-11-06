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
            target_id="2024-en1-trans-1",
            status="in_progress"
        )
        self.db.add(att)

        # 用户作答 Q46
        r = Response(
            id=str(uuid.uuid4()),
            attempt_id=att_id,
            question_id="2024-en1-q46",
            user_answer="虽然系统化的方法提供了必要的严谨性，但重大的科学突破往往源自意外的异常现象，需要直觉的解释。",
            is_final_snapshot=False
        )
        self.db.add(r)
        self.db.commit()

        sub = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=att_id,
            scope="group",
            scope_id="2024-en1-trans-1",
            user_id=self.user_id
        )

        self.assertGreater(sub.subjective_score, 0.0)
        self.assertEqual(sub.objective_score, 0.0)
        
        gr_46 = next(g for g in sub.grade_results if g.question_id == "2024-en1-q46")
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
            target_id="2024-en1-writing-a",
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
            question_id="2024-en1-q51",
            user_answer=sample_notice,
            is_final_snapshot=False
        )
        self.db.add(r)
        self.db.commit()

        sub = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=att_id,
            scope="group",
            scope_id="2024-en1-writing-a",
            user_id=self.user_id
        )

        gr_51 = next(g for g in sub.grade_results if g.question_id == "2024-en1-q51")
        self.assertTrue(gr_51.is_estimated)
        self.assertIn("一档", gr_51.score_band)
        self.assertGreaterEqual(gr_51.score, 8.0)

if __name__ == "__main__":
    unittest.main()
