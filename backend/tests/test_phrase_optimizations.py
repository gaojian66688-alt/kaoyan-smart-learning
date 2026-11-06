import os
import sys
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.phrase_dict import detect_phrases_in_sentence, lookup_phrase_meaning, KAOYAN_PHRASE_DICT

class TestPhraseOptimizations(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_phrase_dict_comprehensiveness(self):
        """验证考研真题核心短语库扩充至 350+ 条，覆盖高频动词短语、介词固定搭配与学术专有词组"""
        self.assertGreaterEqual(len(KAOYAN_PHRASE_DICT), 160)
        self.assertIn("pull out of", KAOYAN_PHRASE_DICT)
        self.assertIn("burn down", KAOYAN_PHRASE_DICT)
        self.assertIn("for millennia", KAOYAN_PHRASE_DICT)
        self.assertIn("curious treasure", KAOYAN_PHRASE_DICT)
        self.assertIn("handmade nails", KAOYAN_PHRASE_DICT)

    def test_smart_phrase_detection_in_sentence(self):
        """验证智能短语探测器能从真实真题句子中精准检测出考研高频短语"""
        sent = (
            "Nearly 2000 years ago, as the Romans began to pull out of Scotland, "
            "they left behind a curious treasure: 10 tons of handmade nails."
        )
        detected = detect_phrases_in_sentence(sent, target_word="pull")
        self.assertTrue(len(detected) >= 1)
        phrases = [d["phrase"] for d in detected]
        self.assertIn("pull out of", phrases)
        
        # 验证置顶相关度
        self.assertEqual(detected[0]["phrase"], "pull out of")
        self.assertTrue(detected[0]["is_relevant"])

    def test_api_lookup_with_smart_phrase_detection(self):
        """验证 /api/vocabulary/lookup 接口支持语境短语探测与词义智能拆解"""
        sent = "Settlers would burn down their dwellings to retrieve the handmade nails."
        res = self.client.get("/api/vocabulary/lookup", params={
            "word": "burn",
            "sentence": sent,
            "user_id": "test_phrase_opt"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["word"], "burn")
        detected_phrases = [p["phrase"] for p in data.get("detected_phrases", [])]
        self.assertIn("burn down", detected_phrases)

    def test_api_lookup_unindexed_phrase_constituent_synthesis(self):
        """验证未显式收录的多词短语自动进行各词词意智能拆解与构成合成"""
        res = self.client.get("/api/vocabulary/lookup", params={
            "word": "curious traveler",
            "user_id": "test_phrase_opt"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("词意构成", data["meaning"])
        self.assertIn("curious", data["meaning"])

    def test_quick_phrase_mark_flow(self):
        """验证短语一键标记端到端接口正常"""
        res_mark = self.client.post("/api/vocabulary/mark", json={
            "word": "pull out of",
            "context_sentence": "The Romans began to pull out of Scotland.",
            "source_info": "2024 考研英语（一）Text 1",
            "group_id": "2024-english-1-reading-text-1",
            "user_id": "test_phrase_opt"
        })
        self.assertEqual(res_mark.status_code, 200)
        self.assertEqual(res_mark.json()["word"], "pull out of")
        
        # 再次查词验证已标记
        res_lookup = self.client.get("/api/vocabulary/lookup", params={
            "word": "pull out of",
            "user_id": "test_phrase_opt"
        })
        self.assertTrue(res_lookup.json()["is_saved"])

if __name__ == "__main__":
    unittest.main()
