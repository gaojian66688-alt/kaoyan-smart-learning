import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.practice import Attempt, Response, Submission, GradeResult
from app.models.exam import Question, AnswerKey
from app.models.mistake import Mistake
from app.models.user import LearningProfile

class GradingEngine:
    """
    PRD 8.1 & G03: 客观题唯一评分内核
    输入固定为：题目 ID + 用户提交快照 + 答案版本 + 题目分值。
    保证同一题目无论在单篇、板块还是整卷批改，基于同一答案版本所得分数严格一致 (AT-01)。
    AI 绝不改动客观题判分。
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

        # 3. 获取各题目已核验的标准答案
        keys = db.query(AnswerKey).filter(
            AnswerKey.question_id.in_(question_ids),
            AnswerKey.version == answer_key_version,
            AnswerKey.status == "verified"
        ).all()
        key_map = {k.question_id: k for k in keys}

        # 4. 执行逐题判定内核
        submission_id = str(uuid.uuid4())
        total_score = 0.0
        max_score = 0.0
        correct_count = 0
        grade_results = []
        now = datetime.utcnow()

        for q in target_questions:
            u_ans = user_answer_map.get(q.id)
            ak = key_map.get(q.id)
            if not ak:
                raise RuntimeError(f"Verified AnswerKey missing for question {q.id} (version {answer_key_version}).")

            std_ans = ak.correct_answer.strip().upper()
            user_clean_ans = (u_ans or "").strip().upper()

            is_correct = bool(user_clean_ans and user_clean_ans == std_ans)
            q_score = float(q.score) if is_correct else 0.0

            total_score += q_score
            max_score += float(q.score)
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
                score=q_score,
                max_score=float(q.score),
                evidence_sentence=ak.evidence_sentence,
                explanation=ak.explanation,
                category=q.category
            )
            grade_results.append(gr)

            # 5. 错题本自动流转 (PRD 10.1)
            if not is_correct:
                cls._record_mistake(db, user_id, q, submission_id, user_clean_ans, std_ans, now)
            else:
                # 若之前有错题，标记为已攻克
                existing_m = db.query(Mistake).filter(
                    Mistake.user_id == user_id,
                    Mistake.question_id == q.id
                ).first()
                if existing_m:
                    existing_m.is_mastered = True

        accuracy = round((correct_count / len(target_questions)) * 100.0, 2) if target_questions else 0.0

        # 6. 保存不可变的 Submission 快照
        submission = Submission(
            id=submission_id,
            attempt_id=attempt_id,
            scope=scope,
            scope_id=scope_id,
            total_score=round(total_score, 2),
            max_score=round(max_score, 2),
            accuracy=accuracy,
            question_count=len(target_questions),
            correct_count=correct_count,
            answer_key_version=answer_key_version,
            submitted_at=now
        )
        db.add(submission)
        for gr in grade_results:
            db.add(gr)

        # 7. 更新作答会话状态
        attempt.status = "graded"
        attempt.submitted_at = now

        # 8. 更新全局学习档案 Profile (PRD 10.2)
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
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

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
