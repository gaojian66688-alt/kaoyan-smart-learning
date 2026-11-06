import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestExportAndTrends(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.user_id = "export_tester_01"

        # 1. 标记一个单词
        cls.client.post("/api/vocabulary/mark", json={
            "user_id": cls.user_id,
            "word": "resilience",
            "context_sentence": "Cultivating emotional resilience helps professionals recover from setbacks.",
            "source_info": "2024 考研英语（一）Text 1",
            "group_id": "2024-english-1-reading-text-1"
        })

        # 2. 产生一次客观题作答并提交批改，生成错题记录
        res_att = cls.client.post("/api/practice/attempt", json={
            "mode": "special_group",
            "target_type": "group",
            "target_id": "2024-english-1-reading-text-1",
            "user_id": cls.user_id
        })
        cls.att_id = res_att.json()["id"]

        # 提交一份包含答对与答错的响应
        cls.client.post(f"/api/practice/attempt/{cls.att_id}/response", json={
            "question_id": "2024-english-1-text1-q21",
            "user_answer": "D"  # 正确
        })
        cls.client.post(f"/api/practice/attempt/{cls.att_id}/response", json={
            "question_id": "2024-english-1-text1-q22",
            "user_answer": "C"  # 故意答错，正确是 D
        })

        # 提交批改
        cls.client.post("/api/practice/submit", json={
            "attempt_id": cls.att_id,
            "scope": "group",
            "scope_id": "2024-english-1-reading-text-1",
            "user_id": cls.user_id
        })

    def test_vocabulary_export_json(self):
        res = self.client.get(f"/api/vocabulary/export?user_id={self.user_id}&format=json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/json; charset=utf-8")
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        words = [d["word"] for d in data]
        self.assertIn("resilience", words)

    def test_vocabulary_export_csv(self):
        res = self.client.get(f"/api/vocabulary/export?user_id={self.user_id}&format=csv")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers["content-type"])
        self.assertTrue(res.text.startswith("\ufeffword,"))
        self.assertIn("resilience", res.text)

    def test_vocabulary_export_anki(self):
        res = self.client.get(f"/api/vocabulary/export?user_id={self.user_id}&format=anki")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/tab-separated-values", res.headers["content-type"])
        self.assertIn("resilience\t", res.text)
        self.assertIn("2024 考研英语（一）Text 1", res.text)

    def test_mistakes_export_markdown(self):
        res = self.client.get(f"/api/mistakes/export?user_id={self.user_id}&format=markdown")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/markdown", res.headers["content-type"])
        self.assertIn("# 考研英语智能学习平台 —— 个人真题错题档案", res.text)
        self.assertIn("第 22 题", res.text)
        self.assertIn("你的作答", res.text)
        self.assertIn("标准答案", res.text)
        self.assertIn("语法句式拆分", res.text)

    def test_mistakes_export_json(self):
        res = self.client.get(f"/api/mistakes/export?user_id={self.user_id}&format=json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/json; charset=utf-8")
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        q_nums = [d["question_num"] for d in data]
        self.assertIn(22, q_nums)

    def test_profile_trends_api(self):
        res = self.client.get(f"/api/profile/trends?user_id={self.user_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["user_id"], self.user_id)
        self.assertIn("category_accuracy", data)
        self.assertIn("daily_trends", data)
        self.assertIn("vocab_distribution", data)
        self.assertIn("weak_points", data)
        self.assertIn("strengths", data)
        
        # 验证词汇掌握状态
        vd = data["vocab_distribution"]
        self.assertGreaterEqual(vd["total"], 1)

if __name__ == "__main__":
    unittest.main()
