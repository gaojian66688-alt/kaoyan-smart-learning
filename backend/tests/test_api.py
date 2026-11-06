import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")

    def test_serve_frontend(self):
        # 验证前端首页与静态资源挂载
        res_index = self.client.get("/")
        self.assertEqual(res_index.status_code, 200)
        self.assertIn("考研英语智能学习系统", res_index.text)

        res_css = self.client.get("/static/css/style.css")
        self.assertEqual(res_css.status_code, 200)

        res_js = self.client.get("/static/js/app.js")
        self.assertEqual(res_js.status_code, 200)

    def test_exams_list(self):
        res = self.client.get("/api/exams")
        self.assertEqual(res.status_code, 200)
        exams = res.json()
        self.assertGreaterEqual(len(exams), 3)
        exam_ids = {e["id"] for e in exams}
        self.assertIn("2024-english-1", exam_ids)
        self.assertIn("2024-english-2", exam_ids)
        self.assertIn("2023-english-1", exam_ids)

    def test_vocab_lookup_from_database(self):
        # 从 6588 真实考研词典库中查询单词
        res = self.client.get("/api/vocabulary/lookup?word=nominal")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["word"], "nominal")
        self.assertIn("名义上", data["meaning"])

    def test_strict_mock_mode_blocks_unit_submission(self):
        """AT-05: 严格模考模式屏蔽单篇批改"""
        # 创建模考会话
        res_att = self.client.post("/api/practice/attempt", json={
            "mode": "strict_mock",
            "target_type": "exam",
            "target_id": "2024-english-1",
            "user_id": "mock_tester"
        })
        self.assertEqual(res_att.status_code, 200)
        att_id = res_att.json()["id"]

        # 尝试单篇批改 -> 必须被 403 拦截并提示
        res_sub = self.client.post("/api/practice/submit", json={
            "attempt_id": att_id,
            "scope": "group",
            "scope_id": "2024-english-1-reading-text-1",
            "user_id": "mock_tester"
        })
        self.assertEqual(res_sub.status_code, 403)
        self.assertIn("严格模考模式下屏蔽单篇及板块批改", res_sub.json()["detail"])

    def test_section_submission_flow(self):
        """验收项 8: 板块批改入口与后端处理流程正常可用"""
        user_id = "section_tester_user"
        # 1. 开启综合训练整卷会话
        res_att = self.client.post("/api/practice/attempt", json={
            "mode": "practice_full",
            "target_type": "exam",
            "target_id": "2024-english-1",
            "user_id": user_id
        })
        self.assertEqual(res_att.status_code, 200)
        att_id = res_att.json()["id"]

        # 2. 保存 Reading A Text 1 的答案
        res_save = self.client.post("/api/practice/save", json={
            "attempt_id": att_id,
            "responses": [
                {"question_id": "2024-english-1-text1-q21", "user_answer": "D"},
                {"question_id": "2024-english-1-text1-q22", "user_answer": "D"},
                {"question_id": "2024-english-1-text1-q23", "user_answer": "A"},
                {"question_id": "2024-english-1-text1-q24", "user_answer": "B"},
                {"question_id": "2024-english-1-text1-q25", "user_answer": "A"},
            ]
        })
        self.assertEqual(res_save.status_code, 200)

        # 3. 执行板块批改 (scope='section', scope_id='2024-english-1-sec-reading-a')
        res_sec_sub = self.client.post("/api/practice/submit", json={
            "attempt_id": att_id,
            "scope": "section",
            "scope_id": "2024-english-1-sec-reading-a",
            "user_id": user_id
        })
        self.assertEqual(res_sec_sub.status_code, 200)
        sub_data = res_sec_sub.json()
        self.assertEqual(sub_data["scope"], "section")
        self.assertEqual(sub_data["scope_id"], "2024-english-1-sec-reading-a")
        self.assertEqual(sub_data["question_count"], 20) # Reading A 共 4 篇 20 题
        self.assertEqual(sub_data["correct_count"], 5)  # Text 1 全对 (5题)
        self.assertEqual(sub_data["total_score"], 10.0) # 5 * 2.0 = 10.0 分

        # 4. 验证会话仍然处于 in_progress 状态，考生可继续作答其他板块
        res_resume = self.client.post("/api/practice/attempt", json={
            "mode": "practice_full",
            "target_type": "exam",
            "target_id": "2024-english-1",
            "user_id": user_id
        })
        self.assertEqual(res_resume.status_code, 200)
        self.assertEqual(res_resume.json()["status"], "in_progress")

if __name__ == "__main__":
    unittest.main()
