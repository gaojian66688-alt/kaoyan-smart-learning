import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from app.database import SessionLocal, Base, engine
from app.core.qa_gate import ContentQAGate

class TestMultiSectionQAGate(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_all_section_groups_pass_qa_gate(self):
        """PRD 6.2 & AT-09: 验证各板块题组完整性与来源真实性门禁通过"""
        verified_group_ids = [
            ("2024-english-1-cloze-group", "cloze"),
            ("2024-english-1-reading-text-1", "reading_a"),
            ("2024-english-1-reading-text-2", "reading_a"),
            ("2024-english-1-reading-text-3", "reading_a"),
            ("2024-english-1-reading-text-4", "reading_a"),
            ("2024-english-1-reading-b-group", "reading_b"),
            ("2024-english-1-trans-group", "translation"),
            ("2024-english-1-writing-a-group", "writing_a"),
            ("2024-english-1-writing-b-group", "writing_b"),
        ]

        for gid, gtype in verified_group_ids:
            res = ContentQAGate.validate_question_group(self.db, gid, record_logs=False)
            self.assertTrue(res.is_valid, f"Group {gid} ({gtype}) failed QA gate: {res.errors}")
            self.assertGreater(len(res.checksum), 10)

    def test_unverified_missing_group_blocked_by_qa_gate(self):
        """P0 门禁防护：不存在或未核验上线的题组严禁通过真实性门禁"""
        fake_id = "2024-english-2-cloze-group"
        res = ContentQAGate.validate_question_group(self.db, fake_id, record_logs=False)
        self.assertFalse(res.is_valid)
        self.assertIn("does not exist", res.errors[0])

if __name__ == "__main__":
    unittest.main()
