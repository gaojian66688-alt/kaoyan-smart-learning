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
        """PRD 6.2 & AT-09: 验证各板块题组完整性门禁通过"""
        test_group_ids = [
            ("2024-en1-cloze-1", "cloze"),
            ("2024-en1-text-1", "reading_a"),
            ("2024-en1-reading-b-1", "reading_b"),
            ("2024-en1-trans-1", "translation"),
            ("2024-en1-writing-a", "writing_a"),
            ("2024-en1-writing-b", "writing_b"),
        ]

        for gid, gtype in test_group_ids:
            res = ContentQAGate.validate_question_group(self.db, gid, record_logs=False)
            self.assertTrue(res.is_valid, f"Group {gid} ({gtype}) failed QA gate: {res.errors}")
            self.assertGreater(len(res.checksum), 10)

if __name__ == "__main__":
    unittest.main()
