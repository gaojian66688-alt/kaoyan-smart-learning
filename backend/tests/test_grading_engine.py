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
            "2024-english-1-text1-q25": "A"  # 选 A (正确)
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

    def test_single_passage_submit_allows_continued_answering(self):
        """验收规则 4: 单篇提交后仍可以继续作答，整卷练习不进入终结状态"""
        attempt_id = str(uuid.uuid4())
        att = Attempt(
            id=attempt_id,
            user_id=self.user_id,
            mode="practice_full",
            target_type="exam",
            target_id="2024-english-1",
            status="in_progress",
            time_spent_seconds=120
        )
        self.db.add(att)
        # 录入 Text 1 的答案并提交单篇
        r1 = Response(
            id=str(uuid.uuid4()),
            attempt_id=attempt_id,
            question_id="2024-english-1-text1-q21",
            user_answer="D",
            is_final_snapshot=False
        )
        self.db.add(r1)
        self.db.commit()

        sub = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=attempt_id,
            scope="group",
            scope_id="2024-english-1-reading-text-1",
            user_id=self.user_id
        )
        self.assertIsNotNone(sub)

        # 核心断言：Attempt 状态依然保持为 in_progress，未被强制终结！
        self.db.refresh(att)
        self.assertEqual(att.status, "in_progress")

        # 用户继续作答 Text 2 (未被提交过的题目)
        r2 = Response(
            id=str(uuid.uuid4()),
            attempt_id=attempt_id,
            question_id="2024-english-1-text2-q26",
            user_answer="A",
            is_final_snapshot=False
        )
        self.db.add(r2)
        self.db.commit()

        # 能够成功保存并查询到最新未锁定的答案
        saved_r2 = self.db.query(Response).filter(
            Response.attempt_id == attempt_id,
            Response.question_id == "2024-english-1-text2-q26"
        ).first()
        self.assertIsNotNone(saved_r2)
        self.assertEqual(saved_r2.user_answer, "A")
        self.assertFalse(saved_r2.is_final_snapshot)

    def test_already_submitted_questions_not_double_counted(self):
        """验收规则 6: 已提交题目不重复计分，学习档案与错题计数精准不累加"""
        attempt_id = str(uuid.uuid4())
        att = Attempt(
            id=attempt_id,
            user_id=self.user_id,
            mode="practice_full",
            target_type="exam",
            target_id="2024-english-1",
            status="in_progress"
        )
        self.db.add(att)
        # 作答 Text 1 全部 5 题
        for num in range(21, 26):
            r = Response(
                id=str(uuid.uuid4()),
                attempt_id=attempt_id,
                question_id=f"2024-english-1-text1-q{num}",
                user_answer="D" if num == 21 else "A",
                is_final_snapshot=False
            )
            self.db.add(r)
        self.db.commit()

        # 首次提交 Text 1
        sub1 = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=attempt_id,
            scope="group",
            scope_id="2024-english-1-reading-text-1",
            user_id=self.user_id
        )
        profile1 = self.db.query(LearningProfile).filter(LearningProfile.user_id == self.user_id).first()
        initial_attempted = profile1.total_questions_attempted
        self.assertEqual(initial_attempted, 5)

        # 随后提交包含 Text 1 的整个 Section II 阅读板块
        sub2 = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=attempt_id,
            scope="section",
            scope_id="2024-english-1-sec-reading-a",
            user_id=self.user_id
        )
        profile2 = self.db.query(LearningProfile).filter(LearningProfile.user_id == self.user_id).first()
        
        # 核心断言：板块共有 20 题，此前已计入 5 题，本次仅新增 15 题，总数严格为 20 题，绝无重复计分
        self.assertEqual(profile2.total_questions_attempted, 20)

    def test_idempotent_duplicate_submission(self):
        """验收规则 7: 重复提交同一快照不重复生成成绩（幂等性）"""
        attempt_id = str(uuid.uuid4())
        att = Attempt(
            id=attempt_id,
            user_id=self.user_id,
            mode="special_training",
            target_type="group",
            target_id="2024-english-1-reading-text-1",
            status="in_progress"
        )
        self.db.add(att)
        r = Response(
            id=str(uuid.uuid4()),
            attempt_id=attempt_id,
            question_id="2024-english-1-text1-q21",
            user_answer="D",
            is_final_snapshot=False
        )
        self.db.add(r)
        self.db.commit()

        sub1 = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=attempt_id,
            scope="group",
            scope_id="2024-english-1-reading-text-1",
            user_id=self.user_id
        )

        sub2 = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=attempt_id,
            scope="group",
            scope_id="2024-english-1-reading-text-1",
            user_id=self.user_id
        )

        # 核心断言：两次调用返回相同 Submission ID，数据库中仅有一条提交记录
        self.assertEqual(sub1.id, sub2.id)
        subs_count = self.db.query(Submission).filter(
            Submission.attempt_id == attempt_id,
            Submission.scope == "group"
        ).count()
        self.assertEqual(subs_count, 1)

if __name__ == "__main__":
    unittest.main()
