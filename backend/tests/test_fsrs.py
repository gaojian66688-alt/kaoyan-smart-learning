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

if __name__ == "__main__":
    unittest.main()
