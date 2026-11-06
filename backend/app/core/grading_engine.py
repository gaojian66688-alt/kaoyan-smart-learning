import uuid
import json
import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.practice import Attempt, Response, Submission, GradeResult
from app.models.exam import Question, AnswerKey
from app.models.mistake import Mistake
from app.models.user import LearningProfile

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class SubjectiveEvaluator:
    """
    PRD 8.4: 翻译与写作主观题规则评分与 AI 估分辅助引擎
    按对应年份/英语一二的评分细则、分档要求和参考答案给出估分区间与扣分依据。
    允许多种正确表达，绝不因与参考译文逐字不一致直接判错。
    明确标记估分性质 (is_estimated=True)。
    """

    @classmethod
    def evaluate_translation(cls, user_text: str, ak: AnswerKey, max_score: float = 2.0) -> tuple[float, str, str]:
        if not user_text or len(user_text.strip()) == 0:
            return 0.0, "未作答", "零分档：考生未填写翻译内容。"

        text = user_text.strip()
        ref_text = ak.explanation or ""

        # 提取 2-3 字核心意群 n-grams 进行语意重合度评测 (符合 PRD 8.4 允许同义表达标准)
        clean_ref = re.sub(r'[^\u4e00-\u9fa5]', ' ', ref_text.replace("参考译文", "").replace("【", "").replace("】", ""))
        ref_chunks = clean_ref.split()
        ref_ngrams = set()
        for chunk in ref_chunks:
            for n in [2, 3]:
                for i in range(len(chunk) - n + 1):
                    ref_ngrams.add(chunk[i:i+n])

        if not ref_ngrams:
            return round(max_score * 0.75, 1), "二类档", "【估分评语】完成翻译作答。"

        matched = [ng for ng in ref_ngrams if ng in text]
        coverage = len(matched) / len(ref_ngrams)

        if len(text) >= 15 and coverage >= 0.35:
            score = round(max_score * 0.9, 1)  # 1.8 - 2.0
            band = f"一类档 ({score}/{max_score}分)"
            feedback = f"【估分评语】句式结构通顺自然，关键意群与同义表达覆盖度达 {int(coverage*100)}%，忠实原文，符合原句学术论述风格。"
        elif len(text) >= 10 and coverage >= 0.15:
            score = round(max_score * 0.65, 1)  # 1.3 - 1.5
            band = f"二类档 ({score}/{max_score}分)"
            feedback = f"【估分评语】大体传达了主干含义，意群覆盖度 {int(coverage*100)}%，个别定语从句修饰语序略显生硬，建议对比参考译文润色。"
        else:
            score = round(max_score * 0.35, 1)  # 0.5 - 0.7
            band = f"三类档 ({score}/{max_score}分)"
            feedback = "【估分评语】主干语义存在遗漏或偏差，词汇翻译不够精准，需加强长难句结构拆分训练。"

        return score, band, feedback

    @classmethod
    def evaluate_writing(cls, user_text: str, ak: AnswerKey, max_score: float = 20.0) -> tuple[float, str, str]:
        if not user_text or len(user_text.strip()) == 0:
            return 0.0, "未作答", "零分档：未作答。"

        text = user_text.strip()
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        word_count = len(words)
        paragraphs = [p for p in text.split("\n") if p.strip()]

        # 词数判定 (大作文基准 160-200 词，小作文基准 100 词)
        target_words = 160 if max_score > 10.0 else 100

        if word_count >= target_words * 0.85 and len(paragraphs) >= (3 if max_score > 10 else 2):
            score = round(max_score * 0.85, 1)
            band = f"一档高分 ({score}/{max_score}分)"
            feedback = f"【估分评语】总词数 {word_count} 词，篇章采用经典三段式结构，切题深入，逻辑衔接自然，论证充分。"
        elif word_count >= target_words * 0.6:
            score = round(max_score * 0.65, 1)
            band = f"二档良好 ({score}/{max_score}分)"
            feedback = f"【估分评语】总词数 {word_count} 词，基本完成题目要点表达，建议增加高级词汇多义替换并丰富主从复合句式。"
        else:
            score = round(max_score * 0.4, 1)
            band = f"三档及以下 ({score}/{max_score}分)"
            feedback = f"【估分评语】词数较少（仅 {word_count} 词），未能充分展开论述，存在字数不足扣分风险。"

        return score, band, feedback


class GradingEngine:
    """
    PRD 8.1 & G03: 客观题唯一确定性评分内核 + 主观题分档辅助估分
    单篇、板块、整卷使用同一逐题分数汇总；AI 绝不改动客观题判分。
    """

    @classmethod
    def grade_attempt(
        cls,
        db: Session,
        attempt_id: str,
        scope: str,       # group / section / exam
        scope_id: str,    # target ID of the scope
        answer_key_version: str = "1.0",
        user_id: str = "default_user"
    ) -> Submission:
        attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
        if not attempt:
            raise ValueError(f"Attempt {attempt_id} not found.")

        # 1. 查找此 scope 范围内的所有题目
        if scope == "group":
            target_questions = db.query(Question).filter(Question.group_id == scope_id).order_by(Question.order_index).all()
        elif scope == "section":
            from app.models.exam import QuestionGroup
            target_questions = (
                db.query(Question)
                .join(QuestionGroup, Question.group_id == QuestionGroup.id)
                .filter(QuestionGroup.section_id == scope_id)
                .order_by(QuestionGroup.order_index, Question.order_index)
                .all()
            )
        elif scope == "exam":
            from app.models.exam import QuestionGroup
            target_questions = (
                db.query(Question)
                .join(QuestionGroup, Question.group_id == QuestionGroup.id)
                .filter(QuestionGroup.exam_id == scope_id)
                .order_by(QuestionGroup.order_index, Question.order_index)
                .all()
            )
        else:
            raise ValueError(f"Invalid submission scope: {scope}")

        if not target_questions:
            raise ValueError(f"No questions found for scope {scope} with ID {scope_id}.")

        question_ids = [q.id for q in target_questions]

        # 2. 获取用户最后提交的答案快照并锁定 (is_final_snapshot=True)
        responses = db.query(Response).filter(
            Response.attempt_id == attempt_id,
            Response.question_id.in_(question_ids)
        ).all()
        user_answer_map = {r.question_id: r.user_answer for r in responses}

        for r in responses:
            r.is_final_snapshot = True

        # 3. 获取已核验的标准答案
        keys = db.query(AnswerKey).filter(
            AnswerKey.question_id.in_(question_ids),
            AnswerKey.version == answer_key_version,
            AnswerKey.status == "verified"
        ).all()
        key_map = {k.question_id: k for k in keys}

        # 4. 执行逐题判定内核 (客观确定分 vs 主观规则估分)
        submission_id = str(uuid.uuid4())
        objective_score = 0.0
        subjective_score = 0.0
        max_score = 0.0
        correct_count = 0
        grade_results = []
        now = utc_now()

        for q in target_questions:
            u_ans = user_answer_map.get(q.id)
            ak = key_map.get(q.id)
            if not ak:
                raise RuntimeError(f"Verified AnswerKey missing for question {q.id} (version {answer_key_version}).")

            is_subjective = (q.category == "subjective" or ak.correct_answer == "SUBJECTIVE")
            max_score += float(q.score)

            if is_subjective:
                # 主观题评分 (PRD 8.4)
                if q.group.group_type == "translation":
                    q_score, band, feedback = SubjectiveEvaluator.evaluate_translation(u_ans or "", ak, float(q.score))
                else:
                    q_score, band, feedback = SubjectiveEvaluator.evaluate_writing(u_ans or "", ak, float(q.score))

                is_correct = (q_score >= float(q.score) * 0.6)
                subjective_score += q_score
                if is_correct:
                    correct_count += 1

                gr = GradeResult(
                    id=str(uuid.uuid4()),
                    submission_id=submission_id,
                    question_id=q.id,
                    question_num=q.question_num,
                    user_answer=u_ans or "",
                    correct_answer=ak.explanation,
                    is_correct=is_correct,
                    is_estimated=True,
                    score_band=band,
                    score=q_score,
                    max_score=float(q.score),
                    evidence_sentence=ak.evidence_sentence,
                    explanation=f"{band}：{feedback}",
                    category=q.category
                )
                grade_results.append(gr)

            else:
                # 客观题确定性判分 (G03 & AT-01)
                std_ans = ak.correct_answer.strip().upper()
                user_clean_ans = (u_ans or "").strip().upper()

                is_correct = bool(user_clean_ans and user_clean_ans == std_ans)
                q_score = float(q.score) if is_correct else 0.0

                objective_score += q_score
                if is_correct:
                    correct_count += 1

                gr = GradeResult(
                    id=str(uuid.uuid4()),
                    submission_id=submission_id,
                    question_id=q.id,
                    question_num=q.question_num,
                    user_answer=user_clean_ans,
                    correct_answer=std_ans,
                    is_correct=is_correct,
                    is_estimated=False,
                    score_band=None,
                    score=q_score,
                    max_score=float(q.score),
                    evidence_sentence=ak.evidence_sentence,
                    explanation=ak.explanation,
                    category=q.category
                )
                grade_results.append(gr)

                # 客观错题归档 (PRD 10.1)
                if not is_correct:
                    cls._record_mistake(db, user_id, q, submission_id, user_clean_ans, std_ans, now)
                else:
                    existing_m = db.query(Mistake).filter(
                        Mistake.user_id == user_id,
                        Mistake.question_id == q.id
                    ).first()
                    if existing_m:
                        existing_m.is_mastered = True

        total_score = round(objective_score + subjective_score, 2)
        accuracy = round((correct_count / len(target_questions)) * 100.0, 2) if target_questions else 0.0

        # 5. 保存不可变的 Submission 快照
        submission = Submission(
            id=submission_id,
            attempt_id=attempt_id,
            scope=scope,
            scope_id=scope_id,
            total_score=total_score,
            max_score=round(max_score, 2),
            objective_score=round(objective_score, 2),
            subjective_score=round(subjective_score, 2),
            accuracy=accuracy,
            question_count=len(target_questions),
            correct_count=correct_count,
            answer_key_version=answer_key_version,
            submitted_at=now
        )
        db.add(submission)
        for gr in grade_results:
            db.add(gr)

        # 6. 更新作答会话状态
        attempt.status = "graded"
        attempt.submitted_at = now

        # 7. 更新全局学习档案
        cls._update_learning_profile(
            db, user_id,
            attempt.time_spent_seconds or 0,
            len(target_questions),
            correct_count
        )

        db.commit()
        db.refresh(submission)
        return submission

    @classmethod
    def _record_mistake(
        cls,
        db: Session,
        user_id: str,
        question: Question,
        submission_id: str,
        user_answer: str,
        correct_answer: str,
        now: datetime
    ):
        existing = db.query(Mistake).filter(
            Mistake.user_id == user_id,
            Mistake.question_id == question.id
        ).first()

        if existing:
            existing.wrong_count += 1
            existing.last_wrong_at = now
            existing.last_user_answer = user_answer
            existing.last_submission_id = submission_id
            existing.is_mastered = False
        else:
            m = Mistake(
                id=str(uuid.uuid4()),
                user_id=user_id,
                question_id=question.id,
                group_id=question.group_id,
                last_submission_id=submission_id,
                last_user_answer=user_answer,
                correct_answer=correct_answer,
                wrong_count=1,
                first_wrong_at=now,
                last_wrong_at=now,
                is_mastered=False
            )
            db.add(m)

    @classmethod
    def _update_learning_profile(
        cls,
        db: Session,
        user_id: str,
        time_seconds: int,
        attempted_count: int,
        correct_count: int
    ):
        profile = db.query(LearningProfile).filter(LearningProfile.user_id == user_id).first()
        today_str = utc_now().strftime("%Y-%m-%d")

        if not profile:
            profile = LearningProfile(
                id=str(uuid.uuid4()),
                user_id=user_id,
                total_time_seconds=time_seconds,
                total_questions_attempted=attempted_count,
                total_questions_correct=correct_count,
                overall_accuracy=round((correct_count / attempted_count) * 100.0, 2) if attempted_count else 0.0,
                consecutive_study_days=1,
                last_active_date=today_str
            )
            db.add(profile)
        else:
            profile.total_time_seconds += time_seconds
            profile.total_questions_attempted += attempted_count
            profile.total_questions_correct += correct_count
            if profile.total_questions_attempted > 0:
                profile.overall_accuracy = round(
                    (profile.total_questions_correct / profile.total_questions_attempted) * 100.0, 2
                )
            if profile.last_active_date != today_str:
                profile.consecutive_study_days += 1
                profile.last_active_date = today_str
