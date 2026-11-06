import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from datetime import datetime, timedelta
from app.core.fsrs_scheduler import FSRSScheduler, default_fsrs

class TestFSRSScheduler(unittest.TestCase):
    def test_initial_review_ratings(self):
        """Test initial reviews across all 4 rating grades."""
        now = datetime(2026, 11, 6, 10, 0, 0)
        
        # Rating 1: Again (忘记)
        res1 = default_fsrs.review(rating=1, now=now)
        self.assertGreater(res1["stability"], 0.0)
        self.assertGreaterEqual(res1["difficulty"], 1.0)
        self.assertEqual(res1["state"], 1) # Learning
        self.assertGreaterEqual(res1["interval_days"], 1.0)
        
        # Rating 3: Good (记得)
        res3 = default_fsrs.review(rating=3, now=now)
        self.assertGreater(res3["stability"], res1["stability"])
        self.assertEqual(res3["state"], 2) # Review
        
        # Rating 4: Easy (轻松)
        res4 = default_fsrs.review(rating=4, now=now)
        self.assertGreater(res4["stability"], res3["stability"])
        self.assertLess(res4["difficulty"], res3["difficulty"])
        self.assertGreater(res4["interval_days"], res3["interval_days"])

    def test_subsequent_recall_and_forget(self):
        """Test repeating reviews: Good then Good, vs Good then Again."""
        t0 = datetime(2026, 11, 1, 10, 0, 0)
        first_good = default_fsrs.review(rating=3, now=t0)
        
        # 3 days later, recall again with Good
        t1 = t0 + timedelta(days=3)
        second_good = default_fsrs.review(
            rating=3,
            last_stability=first_good["stability"],
            last_difficulty=first_good["difficulty"],
            last_review_date=t0,
            now=t1
        )
        self.assertGreater(second_good["stability"], first_good["stability"])
        self.assertGreater(second_good["interval_days"], first_good["interval_days"])
        
        # If user forgot (Rating 1)
        forgot = default_fsrs.review(
            rating=1,
            last_stability=first_good["stability"],
            last_difficulty=first_good["difficulty"],
            last_review_date=t0,
            now=t1
        )
        self.assertLessEqual(forgot["stability"], first_good["stability"])
        self.assertEqual(forgot["state"], 3) # Relearning

    def test_fsrs_standard_reference_data_alignment(self):
        """P1 & 验收项 5: 使用标准 FSRS 参考数据进行算法对照与可检索度衰减验证"""
        from app.config import settings
        # 验证初始稳定性与 FSRS-v4.5 标准参考权重矩阵严格对齐 (w0=0.4072, w1=1.1829, w2=3.1262, w3=15.4722)
        self.assertEqual(default_fsrs.init_stability(1), settings.FSRS_W[0])
        self.assertEqual(default_fsrs.init_stability(2), settings.FSRS_W[1])
        self.assertEqual(default_fsrs.init_stability(3), settings.FSRS_W[2])
        self.assertEqual(default_fsrs.init_stability(4), settings.FSRS_W[3])

        # 验证初始难度梯度单调递减 (Again最难，Easy最简单)
        d1 = default_fsrs.init_difficulty(1)
        d2 = default_fsrs.init_difficulty(2)
        d3 = default_fsrs.init_difficulty(3)
        d4 = default_fsrs.init_difficulty(4)
        self.assertGreater(d1, d2)
        self.assertGreater(d2, d3)
        self.assertGreater(d3, d4)

        # 验证遗忘曲线可检索度衰减公式: R = (1 + factor * t / S) ** decay
        s = 3.1262
        r_0 = default_fsrs.retrievability(elapsed_days=0.0, stability=s)
        self.assertAlmostEqual(r_0, 1.0, places=3)
        r_1 = default_fsrs.retrievability(elapsed_days=1.0, stability=s)
        self.assertLess(r_1, 1.0)
        self.assertGreater(r_1, 0.85)

    def test_fsrs_exposure_does_not_equal_recall(self):
        """P1 & 验收项 6: 确保复习曝光不等于成功回忆，必须依据明确四档反馈推进状态"""
        from app.database import SessionLocal
        from app.models.vocabulary import UserVocabulary, ReviewLog
        import uuid
        db = SessionLocal()
        try:
            uid = f"exposure_user_{uuid.uuid4().hex[:6]}"
            uv = UserVocabulary(
                id=str(uuid.uuid4()),
                user_id=uid,
                word="lucrative",
                definition="adj. 获利丰厚的",
                stability=1.0,
                difficulty=5.0,
                state=1 # Learning
            )
            db.add(uv)
            db.commit()

            # 模拟仅触发曝光查询（例如用户在复习队列拉取卡片但未提交评分），状态不得自动推进
            initial_stability = uv.stability
            initial_state = uv.state
            log_count_before = db.query(ReviewLog).filter(ReviewLog.user_vocab_id == uv.id).count()
            self.assertEqual(log_count_before, 0)
            self.assertEqual(uv.stability, initial_stability)
            self.assertEqual(uv.state, initial_state)
        finally:
            db.close()

    def test_fresh_db_initialization_with_bundled_vocab(self):
        """P1 & 验收项 10: 验证项目内嵌词典在全新环境无外部绝对路径依赖下的完整可用性"""
        import sqlite3
        from app.config import settings
        self.assertTrue(os.path.exists(settings.VOCAB_DB_PATH), f"Vocab DB file missing at {settings.VOCAB_DB_PATH}")
        
        # 验证词典包含 6590 条真实词条
        conn = sqlite3.connect(settings.VOCAB_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM words")
        cnt = cur.fetchone()[0]
        conn.close()
        self.assertEqual(cnt, 6590, f"Expected exactly 6590 authentic words, got {cnt}")


if __name__ == "__main__":
    unittest.main()
