import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
import uuid
from app.database import SessionLocal, Base, engine
from app.models.practice import Attempt, Response, Submission, GradeResult
from app.models.mistake import Mistake
from app.models.user import LearningProfile
from app.core.grading_engine import GradingEngine

class TestGradingEngineAT01(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        # 清理测试用户数据
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
        self.db.query(Mistake).filter(Mistake.user_id == self.user_id).delete(synchronize_session=False)
        self.db.query(LearningProfile).filter(LearningProfile.user_id == self.user_id).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_at01_consistent_scoring_across_scopes(self):
        """
        AT-01: 同一阅读先单篇再板块后整卷提交
        断言：原题得分不变；不重复记分；汇总正确。
        2024 英语一 Text 1 官方答案：
        21: B, 22: A, 23: C, 24: B, 25: B
        假设用户作答：
        21: B (正确, 2.0分)
        22: A (正确, 2.0分)
        23: A (错误, 0.0分)
        24: B (正确, 2.0分)
        25: B (正确, 2.0分)
        预期该篇得分：8.0 / 10.0 分，正确率 80.0%
        """
        # 1. 创建作答会话
        attempt_id = str(uuid.uuid4())
        att = Attempt(
            id=attempt_id,
            user_id=self.user_id,
            mode="practice_full",
            target_type="exam",
            target_id="2024-english-1",
            status="in_progress",
            time_spent_seconds=600
        )
        self.db.add(att)

        user_answers = {
            "2024-english-1-text1-q21": "D",
            "2024-english-1-text1-q22": "D",
            "2024-english-1-text1-q23": "B", # 错选 B (标准是 A)
            "2024-english-1-text1-q24": "B",
            "2024-english-1-text1-q25": "C"
        }

        for q_id, ans in user_answers.items():
            r = Response(
                id=str(uuid.uuid4()),
                attempt_id=attempt_id,
                question_id=q_id,
                user_answer=ans,
                is_final_snapshot=False
            )
            self.db.add(r)
        self.db.commit()

        # Step 1: 单篇提交 (scope = "group")
        sub_group = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=attempt_id,
            scope="group",
            scope_id="2024-english-1-reading-text-1",
            user_id=self.user_id
        )

        self.assertEqual(sub_group.total_score, 8.0)
        self.assertEqual(sub_group.max_score, 10.0)
        self.assertEqual(sub_group.correct_count, 4)
        self.assertEqual(sub_group.question_count, 5)
        self.assertEqual(sub_group.accuracy, 80.0)

        # 检查逐题明细
        grs_group = {gr.question_id: gr for gr in sub_group.grade_results}
        self.assertTrue(grs_group["2024-english-1-text1-q21"].is_correct)
        self.assertEqual(grs_group["2024-english-1-text1-q21"].score, 2.0)
        self.assertFalse(grs_group["2024-english-1-text1-q23"].is_correct)
        self.assertEqual(grs_group["2024-english-1-text1-q23"].score, 0.0)

        # 检查错题本是否自动收录了 Q23
        mistake = self.db.query(Mistake).filter(
            Mistake.user_id == self.user_id,
            Mistake.question_id == "2024-english-1-text1-q23"
        ).first()
        self.assertIsNotNone(mistake)
        self.assertEqual(mistake.last_user_answer, "B")
        self.assertEqual(mistake.correct_answer, "A")
        self.assertFalse(mistake.is_mastered)

        # Step 2: 板块提交 (scope = "section")
        sub_section = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=attempt_id,
            scope="section",
            scope_id="2024-english-1-sec-reading-a",
            user_id=self.user_id
        )

        # 核心断言：原题得分严格不变！
        grs_section = {gr.question_id: gr for gr in sub_section.grade_results}
        for q_id in user_answers:
            self.assertEqual(
                grs_group[q_id].score,
                grs_section[q_id].score,
                f"Question {q_id} score differed between group and section submission!"
            )
            self.assertEqual(
                grs_group[q_id].is_correct,
                grs_section[q_id].is_correct
            )

        # Step 3: 整卷提交 (scope = "exam")
        sub_exam = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=attempt_id,
            scope="exam",
            scope_id="2024-english-1",
            user_id=self.user_id
        )

        # 核心断言：整卷提交后，原题得分依然完全一致！
        grs_exam = {gr.question_id: gr for gr in sub_exam.grade_results}
        for q_id in user_answers:
            self.assertEqual(
                grs_group[q_id].score,
                grs_exam[q_id].score,
                f"Question {q_id} score differed between group and exam submission!"
            )

if __name__ == "__main__":
    unittest.main()
