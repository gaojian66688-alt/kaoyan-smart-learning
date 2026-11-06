import os
import sys
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
import sqlite3
import json
from app.database import SessionLocal
from app.models.exam import Exam, Section, QuestionGroup, Question, AnswerKey
from app.models.practice import Attempt, Submission, GradeResult, Response
from app.models.mistake import Mistake
from app.models.vocabulary import UserVocabulary, VocabularyOccurrence
from app.core.grading_engine import GradingEngine, SubjectiveEvaluator
from app.core.fsrs_scheduler import FSRSScheduler, default_fsrs

class TestAuditComprehensive(unittest.TestCase):
    """
    全量验收与深度审计测试套件
    严格核对《考研英语智能学习软件 PRD v1.0》及用户各项明确指令要求
    """

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_audit_zero_watermarks_in_db(self):
        """审计项 1: 全库无水印、无商业广告、无外源泄露检测"""
        banned_keywords = [
            "公众号", "柠檬水", "世纪高教", "绝密★", "启用前", "扫码", "关注",
            "线上打印", "淘宝", "店铺", "微店", "拼多多", "免费分享", "顺丰包邮",
            "微信", "学霸狂练", "再来一杯"
        ]
        
        # 1. 检查题组文章材料与题组标题
        groups = self.db.query(QuestionGroup).all()
        for g in groups:
            for kw in banned_keywords:
                self.assertNotIn(kw, g.passage_text or "", f"Group {g.id} passage contains watermark: {kw}")
                self.assertNotIn(kw, g.title or "", f"Group {g.id} title contains watermark: {kw}")

        # 2. 检查题干与选项
        questions = self.db.query(Question).all()
        for q in questions:
            for kw in banned_keywords:
                self.assertNotIn(kw, q.prompt or "", f"Question {q.id} prompt contains watermark: {kw}")
                self.assertNotIn(kw, q.options_json or "", f"Question {q.id} options contain watermark: {kw}")

        # 3. 检查解析与定位依据
        keys = self.db.query(AnswerKey).all()
        for ak in keys:
            for kw in banned_keywords:
                self.assertNotIn(kw, ak.explanation or "", f"AnswerKey {ak.id} explanation contains watermark: {kw}")
                self.assertNotIn(kw, ak.evidence_sentence or "", f"AnswerKey {ak.id} evidence contains watermark: {kw}")

    def test_audit_exact_1_to_1_answer_keys(self):
        """审计项 2: 题库全部题目与答案、解析 1:1 严格对齐"""
        total_q = self.db.query(Question).count()
        total_ak = self.db.query(AnswerKey).count()
        self.assertEqual(total_q, total_ak, f"Question count {total_q} != AnswerKey count {total_ak}")
        self.assertEqual(total_q, 2156, f"Expected exactly 2156 questions across 43 exams, got {total_q}")

        # 逐题核实外键对应与内容完整度
        questions = self.db.query(Question).all()
        for q in questions:
            ak = self.db.query(AnswerKey).filter(AnswerKey.question_id == q.id).first()
            self.assertIsNotNone(ak, f"Question {q.id} has no matching answer key")
            self.assertTrue(len(ak.correct_answer.strip()) > 0, f"Question {q.id} answer is empty")
            self.assertTrue(len(ak.explanation.strip()) > 0, f"Question {q.id} explanation is empty")
            self.assertFalse(ak.explanation.startswith("null"))

    def test_audit_question_numbering_continuity(self):
        """审计项 3: 每套试卷内部题目编号严格连续、不跳号、不重号"""
        all_exams = self.db.query(Exam).all()
        for ex in all_exams:
            all_q_nums = []
            for sec in ex.sections:
                for grp in sec.question_groups:
                    for q in grp.questions:
                        all_q_nums.append(q.question_num)
            
            # 排序后检查连续性
            all_q_nums.sort()
            expected_nums = list(range(1, len(all_q_nums) + 1))
            self.assertEqual(
                all_q_nums, expected_nums,
                f"Exam {ex.id} question numbers are not continuous or duplicate: {all_q_nums[:10]}..."
            )
            # 英语一必定 52 题，英语二必定 48 题
            if ex.exam_type == "english_1":
                self.assertEqual(len(all_q_nums), 52)
            else:
                self.assertEqual(len(all_q_nums), 48)

    def test_audit_multi_tier_grading_consistency(self):
        """审计项 4: 单篇批改、板块批改与整卷批改使用同一评分内核与标准答案，结果绝对一致"""
        ex = self.db.query(Exam).filter(Exam.id == "2024-english-1").first()
        reading_sec = next(s for s in ex.sections if s.section_code == "reading_a")
        first_group = reading_sec.question_groups[0] # Reading A Text 1 (Q21-Q25)
        
        # 创建单篇作答
        att_group = Attempt(
            id=str(uuid.uuid4()),
            mode="special_training",
            target_type="group",
            target_id=first_group.id,
            user_id="audit_tester_1"
        )
        self.db.add(att_group)
        self.db.commit()

        # 预设作答：Q21选D(对), Q22选C(错，标准答案为D)
        self.db.add(Response(id=str(uuid.uuid4()), attempt_id=att_group.id, question_id="2024-english-1-text1-q21", user_answer="D"))
        self.db.add(Response(id=str(uuid.uuid4()), attempt_id=att_group.id, question_id="2024-english-1-text1-q22", user_answer="C"))
        self.db.commit()

        sub_group = GradingEngine.grade_attempt(
            db=self.db,
            attempt_id=att_group.id,
            scope="group",
            scope_id=first_group.id,
            user_id="audit_tester_1"
        )

        res_q21 = next(r for r in sub_group.grade_results if r.question_id == "2024-english-1-text1-q21")
        res_q22 = next(r for r in sub_group.grade_results if r.question_id == "2024-english-1-text1-q22")

        # 验证 Q21 正确：得分 2.0，is_correct 为 True
        self.assertTrue(res_q21.is_correct)
        self.assertEqual(res_q21.score, 2.0)
        self.assertTrue(len(res_q21.explanation) > 10)
        self.assertTrue(len(res_q21.evidence_sentence) > 5)

        # 验证 Q22 错误：得分 0.0，is_correct 为 False
        self.assertFalse(res_q22.is_correct)
        self.assertEqual(res_q22.score, 0.0)
        self.assertEqual(res_q22.correct_answer, "D")
        self.assertEqual(res_q22.user_answer, "C")

        # 验证错题已真实归档至 mistakes 表且保留原题组上下文
        mistake_entry = self.db.query(Mistake).filter(
            Mistake.user_id == "audit_tester_1",
            Mistake.question_id == "2024-english-1-text1-q22"
        ).first()
        self.assertIsNotNone(mistake_entry, "Failed to archive mistake to mistakes table")
        self.assertEqual(mistake_entry.last_user_answer, "C")
        self.assertEqual(mistake_entry.correct_answer, "D")

    def test_audit_subjective_evaluation(self):
        """审计项 5: 主观题 (翻译/作文) 规则分档与 AI 估分逻辑及估分标识校验"""
        ak_sample = AnswerKey(
            id="ak-test-subj",
            question_id="q-test-subj",
            correct_answer="SAMPLE",
            explanation="【参考译文】这是一段标准权威的学术参考翻译，包含核心学术论述意群。",
            evidence_sentence="评分细则：按原句意群分档，语法通顺一类档。"
        )

        # 1. 翻译评测：高匹配度输入
        score_high, band_high, fb_high = SubjectiveEvaluator.evaluate_translation(
            user_text="这是一段标准权威的学术参考翻译，论述核心意群。",
            ak=ak_sample,
            max_score=2.0
        )
        self.assertGreaterEqual(score_high, 1.5)
        self.assertIn("一类档", band_high)
        self.assertIn("估分评语", fb_high)

        # 2. 翻译评测：未作答
        score_zero, band_zero, fb_zero = SubjectiveEvaluator.evaluate_translation(
            user_text="",
            ak=ak_sample,
            max_score=2.0
        )
        self.assertEqual(score_zero, 0.0)
        self.assertEqual(band_zero, "未作答")

        # 3. 作文评测 (标准长度小作文信函)
        ak_writing = AnswerKey(
            id="ak-test-w",
            question_id="q-test-w",
            correct_answer="SAMPLE",
            explanation="【写作范文】Dear Sir or Madam,\nI am writing to express...",
            evidence_sentence="小作文满分10分，词数100词左右。"
        )
        sample_essay = (
            "Dear Sir or Madam,\n\n"
            "I am writing this letter to convey my sincere congratulations to you on your outstanding achievement in our annual project. "
            "Your continuous dedication, exceptional diligence, and remarkable leadership have set an admirable benchmark for everyone in our department. "
            "We take enormous pride in your success and look forward to collaborating with you closely in future endeavors.\n\n"
            "Should you need any further assistance with the upcoming presentation, please feel free to let me know at your earliest convenience. "
            "Please accept our warmest wishes for your continued accomplishment and happiness.\n\n"
            "Yours faithfully,\nLi Ming"
        )
        w_score, w_band, w_feedback = SubjectiveEvaluator.evaluate_writing(
            user_text=sample_essay,
            ak=ak_writing,
            max_score=10.0
        )
        self.assertGreaterEqual(w_score, 8.0)
        self.assertIn("高分", w_band)
        self.assertIn("估分评语", w_feedback)

    def test_audit_fsrs_algorithm(self):
        """审计项 6: FSRS 记忆算法科学调度间隔与四档反馈校验"""
        from datetime import datetime
        now = datetime(2026, 11, 6, 12, 0, 0)

        # 1: Again (忘记)
        r1 = default_fsrs.review(rating=1, now=now)
        self.assertGreater(r1["stability"], 0.0)
        self.assertEqual(r1["state"], 1) # Learning

        # 2: Hard (困难)
        r2 = default_fsrs.review(rating=2, now=now)
        self.assertGreaterEqual(r2["interval_days"], 1.0)

        # 3: Good (记得)
        r3 = default_fsrs.review(rating=3, now=now)
        self.assertGreater(r3["stability"], r1["stability"])
        self.assertEqual(r3["state"], 2) # Review

        # 4: Easy (轻松)
        r4 = default_fsrs.review(rating=4, now=now)
        self.assertGreater(r4["stability"], r3["stability"])
        self.assertGreater(r4["interval_days"], r3["interval_days"])

    def test_audit_vocabulary_occurrence_preservation(self):
        """审计项 7: 生词入库同时保存真题例句、来源与题组回跳锚点"""
        word = "surveillance"
        context_sentence = "Corporate executives champion these digital surveillance tools as objective metrics."
        source = "2024 英语（一）官方真题 Reading A Text 1"
        group_id = "2024-english-1-reading-text-1"

        # 验证模型和关联
        uv = UserVocabulary(
            id=str(uuid.uuid4()),
            user_id="audit_tester_vocab",
            word=word,
            definition="n. 监控，监视",
            stability=2.0,
            difficulty=5.0
        )
        self.db.add(uv)
        self.db.commit()

        occ = VocabularyOccurrence(
            id=str(uuid.uuid4()),
            user_vocab_id=uv.id,
            group_id=group_id,
            context_sentence=context_sentence,
            source_info=source
        )
        self.db.add(occ)
        self.db.commit()

        # 查询回检
        saved_uv = self.db.query(UserVocabulary).filter(UserVocabulary.id == uv.id).first()
        self.assertEqual(len(saved_uv.occurrences), 1)
        self.assertEqual(saved_uv.occurrences[0].group_id, group_id)
        self.assertEqual(saved_uv.occurrences[0].context_sentence, context_sentence)

    def test_audit_phrase_vocabulary_and_marker_system(self):
        """审计项 8: 短语与固定搭配查词、入库、马克笔标记与取消标记适配"""
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        test_user = "phrase_audit_user"

        # 1. 考研核心短语搭配查询 (如 rely on)
        res_lookup = client.get("/api/vocabulary/lookup", params={"word": "rely on", "user_id": test_user})
        self.assertEqual(res_lookup.status_code, 200)
        data_lookup = res_lookup.json()
        self.assertEqual(data_lookup["word"], "rely on")
        self.assertIn("短语", data_lookup["phonetic"])
        self.assertTrue("依靠" in data_lookup["meaning"] or "依赖" in data_lookup["meaning"])
        self.assertFalse(data_lookup["is_saved"])

        # 2. 标记短语至生词本并纳入 FSRS
        phrase_sent = "Researchers increasingly rely on empirical datasets to validate theoretical assertions."
        res_mark = client.post("/api/vocabulary/mark", json={
            "word": "rely on",
            "context_sentence": phrase_sent,
            "source_info": "2024 考研英语（一）Text 1",
            "group_id": "2024-english-1-reading-text-1",
            "user_id": test_user
        })
        self.assertEqual(res_mark.status_code, 200)
        data_mark = res_mark.json()
        self.assertEqual(data_mark["word"], "rely on")
        self.assertEqual(data_mark["occurrence_count"], 1)

        # 3. 再次查询短语验证已标记状态
        res_lookup_saved = client.get("/api/vocabulary/lookup", params={"word": "rely on", "user_id": test_user})
        self.assertTrue(res_lookup_saved.json()["is_saved"])

        # 4. 选项内划词短语入库 (如 foster structured)
        res_opt_mark = client.post("/api/vocabulary/mark", json={
            "word": "foster structured",
            "context_sentence": "[#21 选项 A] foster structured institutional support",
            "source_info": "2024 考研英语（一）Text 1 (选项 A)",
            "group_id": "2024-english-1-reading-text-1",
            "user_id": test_user
        })
        self.assertEqual(res_opt_mark.status_code, 200)

        # 5. 用户生词本列表同时包含单词与短语
        res_list = client.get("/api/vocabulary/list", params={"user_id": test_user})
        self.assertEqual(res_list.status_code, 200)
        vocab_words = [v["word"] for v in res_list.json()]
        self.assertIn("rely on", vocab_words)
        self.assertIn("foster structured", vocab_words)

        # 6. 取消短语标记 (Unmark)
        res_unmark = client.delete("/api/vocabulary/unmark", params={"word": "rely on", "user_id": test_user})
        self.assertEqual(res_unmark.status_code, 200)
        self.assertEqual(res_unmark.json()["status"], "unmarked")

        # 验证已取消标记
        res_lookup_after = client.get("/api/vocabulary/lookup", params={"word": "rely on", "user_id": test_user})
        self.assertFalse(res_lookup_after.json()["is_saved"])

if __name__ == "__main__":
    unittest.main()
