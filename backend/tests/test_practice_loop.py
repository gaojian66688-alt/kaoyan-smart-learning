import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.practice import Attempt, Response, Submission, GradeResult
from app.models.vocabulary import UserVocabulary, VocabularyOccurrence, ReviewLog
from app.models.mistake import Mistake
from app.models.user import LearningProfile, AIReportRecord

class TestFullReadingTrainingLoop(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_user = f"loop_user_{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        db = SessionLocal()
        try:
            # 清理测试用户的数据
            db.query(GradeResult).filter(GradeResult.submission_id.in_(
                db.query(Submission.id).filter(Submission.attempt_id.in_(
                    db.query(Attempt.id).filter(Attempt.user_id == self.test_user)
                ))
            )).delete(synchronize_session=False)
            db.query(AIReportRecord).filter(AIReportRecord.submission_id.in_(
                db.query(Submission.id).filter(Submission.attempt_id.in_(
                    db.query(Attempt.id).filter(Attempt.user_id == self.test_user)
                ))
            )).delete(synchronize_session=False)
            db.query(Submission).filter(Submission.attempt_id.in_(
                db.query(Attempt.id).filter(Attempt.user_id == self.test_user)
            )).delete(synchronize_session=False)
            db.query(Response).filter(Response.attempt_id.in_(
                db.query(Attempt.id).filter(Attempt.user_id == self.test_user)
            )).delete(synchronize_session=False)
            db.query(Attempt).filter(Attempt.user_id == self.test_user).delete(synchronize_session=False)
            db.query(ReviewLog).filter(ReviewLog.user_vocab_id.in_(
                db.query(UserVocabulary.id).filter(UserVocabulary.user_id == self.test_user)
            )).delete(synchronize_session=False)
            db.query(VocabularyOccurrence).filter(VocabularyOccurrence.user_vocab_id.in_(
                db.query(UserVocabulary.id).filter(UserVocabulary.user_id == self.test_user)
            )).delete(synchronize_session=False)
            db.query(UserVocabulary).filter(UserVocabulary.user_id == self.test_user).delete(synchronize_session=False)
            db.query(Mistake).filter(Mistake.user_id == self.test_user).delete(synchronize_session=False)
            db.query(LearningProfile).filter(LearningProfile.user_id == self.test_user).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    def test_complete_reading_training_closed_loop(self):
        """
        完整阅读训练闭环验收测试：
        导入真题 → 阅读作答 → 标记生词 → 主动提交 → 标准答案评分 → AI 分析 → 生词进入 FSRS → 保存学习档案
        """
        # Step 1: 获取真题阅读单元 (2024 英语一 Text 1)
        res_group = self.client.get("/api/exams/group/2024-english-1-reading-text-1")
        self.assertEqual(res_group.status_code, 200)
        group_data = res_group.json()
        self.assertIn("Text 1", group_data["title"])
        self.assertEqual(len(group_data["questions"]), 5)
        self.assertEqual(group_data["qa_status"], "verified")
        self.assertTrue(len(group_data["passage_text"]) > 100)

        # Step 2: 开启作答会话 (专项训练模式)
        res_att = self.client.post("/api/practice/attempt", json={
            "mode": "special_training",
            "target_type": "group",
            "target_id": "2024-english-1-reading-text-1",
            "user_id": self.test_user
        })
        self.assertEqual(res_att.status_code, 200)
        attempt_id = res_att.json()["id"]

        # Step 3: 阅读中点击查词并标记生词 (AT-06)
        # 查词
        res_lookup = self.client.get("/api/vocabulary/lookup", params={
            "word": "insidious",
            "user_id": self.test_user
        })
        self.assertEqual(res_lookup.status_code, 200)
        self.assertEqual(res_lookup.json()["word"], "insidious")
        self.assertFalse(res_lookup.json()["is_saved"])

        # 标记生词并附带真题原句和出处
        res_mark = self.client.post("/api/vocabulary/mark", json={
            "word": "insidious",
            "context_sentence": "Yet beneath the veneer of quantitative neutrality lies an insidious tension.",
            "source_info": "2024 考研英语（一）Text 1 第2段",
            "group_id": "2024-english-1-reading-text-1",
            "user_id": self.test_user
        })
        self.assertEqual(res_mark.status_code, 200)
        vocab_data = res_mark.json()
        vocab_id = vocab_data["id"]
        self.assertEqual(vocab_data["occurrence_count"], 1)
        self.assertEqual(len(vocab_data["occurrences"]), 1)

        # AT-07: 再次遇到同一词并标记，验证去重累加语境
        res_mark2 = self.client.post("/api/vocabulary/mark", json={
            "word": "insidious",
            "context_sentence": "Another insidious trap in algorithmic evaluation.",
            "source_info": "2024 考研英语（一）模拟补充例句",
            "group_id": "2024-english-1-reading-text-1",
            "user_id": self.test_user
        })
        self.assertEqual(res_mark2.status_code, 200)
        self.assertEqual(res_mark2.json()["id"], vocab_id) # 同一词卡 ID
        self.assertEqual(res_mark2.json()["occurrence_count"], 2)
        self.assertEqual(len(res_mark2.json()["occurrences"]), 2)

        # Step 4: 答题自动保存草稿 (AT-04)
        # 故意将 Q23 答错以测试错题流转与 AI 错因归因
        draft_responses = [
            {"question_id": "2024-english-1-text1-q21", "user_answer": "D"}, # 对
            {"question_id": "2024-english-1-text1-q22", "user_answer": "D"}, # 对
            {"question_id": "2024-english-1-text1-q23", "user_answer": "B"}, # 错 (标准为 A)
            {"question_id": "2024-english-1-text1-q24", "user_answer": "B"}, # 对
            {"question_id": "2024-english-1-text1-q25", "user_answer": "C"}  # 对
        ]
        res_save = self.client.post("/api/practice/save", json={
            "attempt_id": attempt_id,
            "responses": draft_responses,
            "time_spent_seconds": 480
        })
        self.assertEqual(res_save.status_code, 200)
        self.assertEqual(res_save.json()["count"], 5)

        # 检查未提交前不泄漏对错
        res_resume = self.client.post("/api/practice/attempt", json={
            "mode": "special_training",
            "target_type": "group",
            "target_id": "2024-english-1-reading-text-1",
            "user_id": self.test_user
        })
        self.assertEqual(res_resume.json()["status"], "in_progress")
        self.assertEqual(res_resume.json()["saved_responses"]["2024-english-1-text1-q21"], "D")

        # Step 5: 主动提交批改 (G04 & G03)
        res_submit = self.client.post("/api/practice/submit", json={
            "attempt_id": attempt_id,
            "scope": "group",
            "scope_id": "2024-english-1-reading-text-1",
            "user_id": self.test_user
        })
        self.assertEqual(res_submit.status_code, 200)
        sub_data = res_submit.json()
        submission_id = sub_data["id"]

        # 断言评分内核结果：4对1错，得8.0分，正确率80%
        self.assertEqual(sub_data["total_score"], 8.0)
        self.assertEqual(sub_data["max_score"], 10.0)
        self.assertEqual(sub_data["correct_count"], 4)
        self.assertEqual(sub_data["question_count"], 5)
        self.assertEqual(sub_data["accuracy"], 80.0)

        # 验证错题本收录
        res_mistakes = self.client.get("/api/mistakes", params={"user_id": self.test_user})
        self.assertEqual(res_mistakes.status_code, 200)
        m_list = res_mistakes.json()
        self.assertEqual(len(m_list), 1)
        self.assertEqual(m_list[0]["question_id"], "2024-english-1-text1-q23")
        self.assertEqual(m_list[0]["last_user_answer"], "B")
        self.assertEqual(m_list[0]["correct_answer"], "A")

        # 用户在错题本标记真实错因 (PRD 10.1)
        res_tag = self.client.post(f"/api/mistakes/{m_list[0]['id']}/tag", json={"tag": "过度推论，未扣住文章互信受损"})
        self.assertEqual(res_tag.status_code, 200)
        self.assertEqual(res_tag.json()["user_reason_tag"], "过度推论，未扣住文章互信受损")

        # Step 6: 证据化 AI 学习诊断报告 (PRD 8.2 & 8.3)
        res_ai = self.client.post(f"/api/analysis/generate/{submission_id}", params={"user_id": self.test_user})
        self.assertEqual(res_ai.status_code, 200)
        ai_data = res_ai.json()
        self.assertIn("单篇练习诊断报告", ai_data["summary"])
        self.assertEqual(len(ai_data["evidence_items"]), 5)
        
        # 验证区分了 Fact 和 Hypothesis
        wrong_diag = next(item for item in ai_data["evidence_items"] if item["status"] == "wrong")
        self.assertEqual(wrong_diag["question_num"], 23)
        self.assertIn("选 [B]，标准答案为 [A]", wrong_diag["fact"])
        self.assertGreater(len(wrong_diag["hypothesis"]), 0)
        self.assertGreater(len(wrong_diag["evidence_quote"]), 0)

        # Step 7: 生词进入 FSRS 背词系统并完成初次复习 (PRD 9.3 & AT-08)
        res_queue = self.client.get("/api/vocabulary/review-queue", params={"user_id": self.test_user})
        self.assertEqual(res_queue.status_code, 200)
        queue_items = res_queue.json()
        self.assertTrue(any(item["id"] == vocab_id for item in queue_items))

        # 用户选择 "记得 (Good, rating=3)"
        res_feedback = self.client.post("/api/vocabulary/feedback", json={
            "vocab_id": vocab_id,
            "rating": 3,
            "user_id": self.test_user
        })
        self.assertEqual(res_feedback.status_code, 200)
        fb_data = res_feedback.json()
        self.assertGreater(fb_data["new_stability"], 0.0)
        self.assertGreaterEqual(fb_data["interval_days"], 1.0)
        self.assertEqual(fb_data["new_state"], 2) # Review 状态

        # Step 8: 保存并验证全局学习档案 Profile (PRD 10.2 & 10.3)
        res_profile = self.client.get("/api/profile", params={"user_id": self.test_user})
        self.assertEqual(res_profile.status_code, 200)
        p_data = res_profile.json()
        self.assertEqual(p_data["total_questions_attempted"], 5)
        self.assertEqual(p_data["total_questions_correct"], 4)
        self.assertEqual(p_data["overall_accuracy"], 80.0)
        self.assertEqual(p_data["total_vocabulary_marked"], 1)
        self.assertEqual(p_data["total_reviews_completed"], 1)

        # 验证今日计划建议 (PRD 10.3)
        res_plan = self.client.get("/api/profile/today-plan", params={"user_id": self.test_user})
        self.assertEqual(res_plan.status_code, 200)
        plan_data = res_plan.json()
        self.assertEqual(plan_data["unconsolidated_mistakes_count"], 1)
        self.assertIsNotNone(plan_data["recommended_reading_group_id"])

if __name__ == "__main__":
    unittest.main()
