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
            "scope_id": "2024-en1-text-1",
            "user_id": "mock_tester"
        })
        self.assertEqual(res_sub.status_code, 403)
        self.assertIn("严格模考模式下屏蔽单篇及板块批改", res_sub.json()["detail"])

if __name__ == "__main__":
    unittest.main()
