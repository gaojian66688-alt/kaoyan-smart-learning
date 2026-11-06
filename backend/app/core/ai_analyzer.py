import json
import uuid
from app.database import utc_now
from sqlalchemy.orm import Session
from app.models.practice import Submission, GradeResult
from app.models.exam import QuestionGroup, Question
from app.models.vocabulary import UserVocabulary, VocabularyOccurrence
from app.models.user import AIReportRecord

class EvidenceBasedAIAnalyzer:
    """
    PRD 8.2 & 8.3: 证据化 AI 学习分析引擎
    区分“事实（Fact）”与“推测（Hypothesis）”，所有推测均有题号、原文证据句与用户行为支撑。
    AI 仅负责诊断与解释，不篡改客观题成绩。
    """

    @classmethod
    def analyze_submission(cls, db: Session, submission_id: str, user_id: str = "default_user") -> AIReportRecord:
        sub = db.query(Submission).filter(Submission.id == submission_id).first()
        if not sub:
            raise ValueError(f"Submission {submission_id} not found.")

        grade_results = db.query(GradeResult).filter(GradeResult.submission_id == submission_id).all()
        if not grade_results:
            raise ValueError("No grade results for this submission.")

        # 收集用户在此篇/板块标记过的生词 (作为分析证据)
        user_words = (
            db.query(UserVocabulary.word, VocabularyOccurrence.context_sentence)
            .join(VocabularyOccurrence, UserVocabulary.id == VocabularyOccurrence.user_vocab_id)
            .filter(UserVocabulary.user_id == user_id)
            .all()
        )
        marked_word_set = {w[0].lower() for w in user_words}

        evidence_items = []
        recommendations = []

        total_questions = len(grade_results)
        wrong_results = [gr for gr in grade_results if not gr.is_correct]

        # 1. 单题深入证据分析 (Fact vs Hypothesis)
        for gr in grade_results:
            q = db.query(Question).filter(Question.id == gr.question_id).first()
            if not q:
                continue

            if gr.is_correct:
                evidence_items.append({
                    "type": "CORRECT_AFFIRMATION",
                    "question_num": gr.question_num,
                    "fact": f"题号 #{gr.question_num} 作答正确 (选择 {gr.user_answer})",
                    "evidence_quote": gr.evidence_sentence or "",
                    "hypothesis": "精准定位并匹配核心同义替换",
                    "confidence": "high",
                    "status": "correct"
                })
            else:
                # 错题诊断
                prompt = q.prompt
                category = gr.category or "detail"

                # 检查题干或定位句中是否有用户标记过的生词
                detected_marked_words = [
                    w for w in marked_word_set
                    if (gr.evidence_sentence and w in gr.evidence_sentence.lower())
                    or (prompt and w in prompt.lower())
                ]

                # 构建严谨假设
                hypotheses = []
                if detected_marked_words:
                    hypotheses.append(f"发现用户在此题相关句标记了生词 [{', '.join(detected_marked_words)}]，可能存在关键语义理解受阻")

                if category == "inference":
                    hypotheses.append("推断题失分：选项可能存在‘过度推论’或‘正反倒置’陷阱，混淆了作者真实态度与引述观点")
                elif category == "detail":
                    hypotheses.append("细节题失分：可能定位句范围偏差，或被临近同义干扰词误导")
                elif category == "vocabulary":
                    hypotheses.append("词汇题失分：误用了字典常备义，忽视了上下文特定语境含义")
                else:
                    hypotheses.append("主旨/观点题失分：可能以偏概全，将局部段落细节误选为主旨")

                evidence_items.append({
                    "type": "ERROR_DIAGNOSIS",
                    "question_num": gr.question_num,
                    "category": category,
                    "fact": f"题号 #{gr.question_num} 用户选 [{gr.user_answer or '未作答'}]，标准答案为 [{gr.correct_answer}]",
                    "evidence_quote": gr.evidence_sentence or "",
                    "explanation_excerpt": gr.explanation or "",
                    "hypothesis": "；".join(hypotheses),
                    "confidence": "inferred",
                    "status": "wrong"
                })

        # 2. 宏观诊断与个性化建议 (分层)
        if sub.scope == "group":
            summary = (
                f"单篇练习诊断报告：本单元共 {total_questions} 题，答对 {sub.correct_count} 题，"
                f"得分 {sub.total_score}/{sub.max_score} 分 (正确率 {sub.accuracy}%)。"
            )
            if wrong_results:
                recommendations.append("精读建议：点击高亮定位句，对比原文表述与干扰项的转折、限定词差异。")
                recommendations.append("生词巩固：本篇标记的生词已自动纳入 FSRS 队列，请于今日完成首轮卡片复习。")
            else:
                recommendations.append("表现优异：本篇关键定位与逻辑链条均把握准确，建议保持节奏并训练计时速度。")
        elif sub.scope == "section":
            summary = (
                f"Section II 板块诊断报告：板块总得分 {sub.total_score}/{sub.max_score} 分，"
                f"总题数 {total_questions} 题，错误题数 {len(wrong_results)}。"
            )
            recommendations.append("板块复盘：对比不同文章的失分分布，重点防范同类题型 (如推理题) 的连续失分。")
        else:
            summary = (
                f"整卷诊断报告：整卷客观题得分 {sub.total_score}/{sub.max_score} 分，"
                f"整体正确率 {sub.accuracy}%。"
            )
            recommendations.append("整卷策略建议：平衡各题型作答时间分配，先攻稳细节题，最后攻克长难句推理。")

        report_id = str(uuid.uuid4())
        report = AIReportRecord(
            id=report_id,
            submission_id=submission_id,
            scope=sub.scope,
            summary=summary,
            evidence_json=json.dumps(evidence_items, ensure_ascii=False),
            recommendations_json=json.dumps(recommendations, ensure_ascii=False),
            model_version="rule_evidence_engine_v1",
            created_at=utc_now()
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
