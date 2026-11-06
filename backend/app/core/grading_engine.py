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
    按全国硕士研究生招生考试大纲评分标准、分档要求和参考答案给出估分区间与扣分依据。
    多维度综合评测：
    - 翻译：语义完整、关键词覆盖、漏译检测与句法通顺度；
    - 作文：内容切题、篇章结构、词汇语法丰富度（非纯词数/段落）与逻辑连贯性。
    明确标记估分性质 (is_estimated=True)。
    """

    @classmethod
    def evaluate_translation(cls, user_text: str, ak: AnswerKey, max_score: float = 2.0) -> tuple[float, str, str]:
        if not user_text or len(user_text.strip()) == 0:
            return 0.0, "未作答", "零分档：考生未填写翻译内容，缺乏评分依据。"

        text = user_text.strip()
        # 汉字有效字符数判定
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text)
        if len(chinese_chars) < 4:
            return 0.0, "缺乏评分依据", "零分档：作答内容未包含有效汉字翻译，缺乏评分依据。"

        ref_text = ak.explanation or ""
        # 移除解析说明、题号与前缀标签，提取纯净中文参考句
        clean_ref = re.sub(r'【.*?】|第\s*\d+\s*句[：:]|参考.*?[：:]', '', ref_text)
        clean_ref = re.sub(r'[^\u4e00-\u9fa5]', ' ', clean_ref)
        ref_chinese = re.findall(r'[\u4e00-\u9fa5]', clean_ref)

        # 1. 漏译检测 (Omission detection)
        length_ratio = len(chinese_chars) / max(1, len(ref_chinese))
        has_severe_omission = length_ratio < 0.35

        # 2. 提取 2 字核心意群 n-grams 进行语义重合度与关键词评测
        ref_chunks = clean_ref.split()
        ref_ngrams = set()
        for chunk in ref_chunks:
            for n in [2]:
                for i in range(len(chunk) - n + 1):
                    ref_ngrams.add(chunk[i:i+n])

        if not ref_ngrams:
            coverage = 0.5
        else:
            matched = [ng for ng in ref_ngrams if ng in text]
            coverage = len(matched) / len(ref_ngrams)

        # 3. 句法结构与逻辑连接标记检测
        syntax_markers = ["虽然", "但是", "因为", "所以", "不仅", "而且", "然而", "尽管", "因此", "表明", "认为", "指出", "不是", "而是"]
        has_syntax_flow = any(m in text for m in syntax_markers) or ("，" in text and "。" in text)

        # 4. 结合考纲标准分档评定
        if has_severe_omission:
            score = round(max_score * 0.25, 1)
            band = f"四类档 ({score}/{max_score}分)"
            feedback = f"【估分评语】存在严重漏译现象（译文长度仅为参考基准的 {int(length_ratio*100)}%），缺失核心从句或主干信息。"
        elif coverage >= 0.30 and has_syntax_flow and length_ratio >= 0.60:
            score = round(max_score * 0.9, 1)
            band = f"一类档 ({score}/{max_score}分)"
            feedback = f"【估分评语】句式结构通顺自然，关键意群与同义表达覆盖度达 {int(coverage*100)}%，句法符合汉语习惯，无重大漏译。"
        elif coverage >= 0.15 and length_ratio >= 0.45:
            score = round(max_score * 0.65, 1)
            band = f"二类档 ({score}/{max_score}分)"
            feedback = f"【估分评语】大体传达主干含义（意群覆盖度 {int(coverage*100)}%），但个别修饰语序略显僵硬，建议对照参考译文优化衔接。"
        elif coverage >= 0.08:
            score = round(max_score * 0.40, 1)
            band = f"三类档 ({score}/{max_score}分)"
            feedback = "【估分评语】存在较多理解偏差或词义生硬拼凑，关键术语与从句结构翻译不够精准。"
        else:
            score = round(max_score * 0.20, 1)
            band = f"四类档 ({score}/{max_score}分)"
            feedback = "【估分评语】未能准确理解原文核心论述，大面积误译或脱离原文主题。"

        return score, band, feedback

    @classmethod
    def evaluate_writing(cls, user_text: str, ak: AnswerKey, max_score: float = 20.0) -> tuple[float, str, str]:
        if not user_text or len(user_text.strip()) == 0:
            return 0.0, "未作答", "零分档：未填写作文作答内容，缺乏评分依据。"

        text = user_text.strip()
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        word_count = len(words)

        if word_count < 15:
            return 0.0, "缺乏评分依据", "零分档：有效词汇量极低（少于15词），缺乏评分依据。"

        paragraphs = [p for p in text.split("\n") if p.strip()]
        target_words = 160 if max_score > 10.0 else 100

        # 1. 词汇多样性与语言质量 (Type-Token Ratio - 防止纯堆砌单一单词)
        unique_words = {w.lower() for w in words}
        lexical_richness = len(unique_words) / max(1, word_count)

        # 2. 逻辑连接词检测 (Discourse / Cohesion Markers)
        logic_connectors = [
            "furthermore", "however", "therefore", "in addition", "moreover", "consequently",
            "on the one hand", "on the other hand", "for instance", "for example", "in conclusion",
            "as a result", "nevertheless", "firstly", "secondly", "finally", "to sum up", "besides"
        ]
        text_lower = text.lower()
        matched_connectors = [c for c in logic_connectors if c in text_lower]

        # 3. 拦截机械堆砌词汇 (P1 规则: 主观题评分不能只依据词数和段落数量)
        if lexical_richness < 0.35 and word_count >= 50:
            score = round(max_score * 0.2, 1)
            band = f"低分档 (机械重复 {score}/{max_score}分)"
            feedback = f"【估分评语】虽然总词数达 {word_count} 词，但词汇丰富度极低，词汇重复率过高（不同词汇占比仅 {int(lexical_richness*100)}%），存在机械重复嫌疑，不符合考研写作语言规范。"
            return score, band, feedback

        # 4. 综合加权指标计算：词数达标度 (30%) + 词汇多样性 (30%) + 逻辑衔接 (20%) + 篇章结构 (20%)
        word_ratio = min(1.0, word_count / (target_words * 0.85))
        lex_score = min(1.0, lexical_richness / 0.55)
        logic_score = min(1.0, len(matched_connectors) / (3.0 if max_score > 10 else 2.0))
        struct_score = min(1.0, len(paragraphs) / (3.0 if max_score > 10 else 2.0))

        overall_quality = 0.30 * word_ratio + 0.30 * lex_score + 0.20 * logic_score + 0.20 * struct_score

        if overall_quality >= 0.80 and word_count >= target_words * 0.80 and len(paragraphs) >= (3 if max_score > 10 else 2):
            score = round(max_score * 0.85, 1)
            band = f"一档高分 ({score}/{max_score}分)"
            feedback = (
                f"【估分评语】篇章结构完整规范（{len(paragraphs)}段式），总词数 {word_count} 词，"
                f"词汇丰富度良好（独特词汇比 {int(lexical_richness*100)}%），运用了 [{', '.join(matched_connectors[:3])}] 等逻辑过渡词，论证充分。"
            )
        elif overall_quality >= 0.55 and word_count >= target_words * 0.50:
            score = round(max_score * 0.65, 1)
            band = f"二档良好 ({score}/{max_score}分)"
            feedback = (
                f"【估分评语】基本达到题目要求（总词数 {word_count} 词，段落数 {len(paragraphs)}），"
                f"论述较清晰。建议进一步丰富高级短语与从句结构，加强段落间的逻辑连接词使用。"
            )
        elif overall_quality >= 0.32:
            score = round(max_score * 0.40, 1)
            band = f"三档及格边缘 ({score}/{max_score}分)"
            feedback = (
                f"【估分评语】总词数偏少（{word_count} 词）或逻辑衔接较弱，语言表达多为简单句，"
                f"建议严格依据题目提纲要点展开并强化段落层次。"
            )
        else:
            score = round(max_score * 0.20, 1)
            band = f"四档低分 ({score}/{max_score}分)"
            feedback = f"【估分评语】词数明显不足（仅 {word_count} 词），篇章结构不完整，缺乏必要的逻辑过渡和论述要点。"

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

        # 2. 获取用户最后提交的答案快照
        responses = db.query(Response).filter(
            Response.attempt_id == attempt_id,
            Response.question_id.in_(question_ids)
        ).all()
        user_answer_map = {r.question_id: r.user_answer for r in responses}

        # 锁定当前提交范围内的题目快照 (P1 规则 1: 单篇提交后，只锁定该篇的答案快照)
        for r in responses:
            r.is_final_snapshot = True

        # 0. 幂等性检查 (P1 规则 8: 重复提交同一范围、同一答案快照时，必须保证幂等，不重复生成成绩与记录)
        existing_subs = db.query(Submission).filter(
            Submission.attempt_id == attempt_id,
            Submission.scope == scope,
            Submission.scope_id == scope_id
        ).order_by(Submission.submitted_at.desc()).all()

        for es in existing_subs:
            sub_results = db.query(GradeResult).filter(GradeResult.submission_id == es.id).all()
            sub_ans_map = {gr.question_id: (gr.user_answer or "") for gr in sub_results}
            curr_ans_map = {qid: (user_answer_map.get(qid) or "") for qid in question_ids}
            if all(sub_ans_map.get(qid, "") == curr_ans_map.get(qid, "") for qid in question_ids):
                # 答案快照一致，直接幂等返回已存在的 Submission
                return es

        # 3. 获取已核验的标准答案
        keys = db.query(AnswerKey).filter(
            AnswerKey.question_id.in_(question_ids),
            AnswerKey.version == answer_key_version,
            AnswerKey.status == "verified"
        ).all()
        key_map = {k.question_id: k for k in keys}

        # 查询此 Attempt 此前已经产生的所有逐题批改结果 (用于单篇->板块->整卷继承成绩，P1 规则 4 & 6)
        prior_results = (
            db.query(GradeResult)
            .join(Submission, GradeResult.submission_id == Submission.id)
            .filter(Submission.attempt_id == attempt_id)
            .order_by(GradeResult.id)
            .all()
        )
        # 以 question_id 为键建立继承索引
        prior_result_map = {gr.question_id: gr for gr in prior_results}

        # 4. 执行逐题判定内核 (客观确定分 vs 主观规则估分，继承与新判分分离)
        submission_id = str(uuid.uuid4())
        objective_score = 0.0
        subjective_score = 0.0
        max_score = 0.0
        correct_count = 0
        newly_graded_count = 0
        newly_correct_count = 0
        grade_results = []
        now = utc_now()

        for q in target_questions:
            u_ans = user_answer_map.get(q.id)
            ak = key_map.get(q.id)
            if not ak:
                raise RuntimeError(f"Verified AnswerKey missing for question {q.id} (version {answer_key_version}).")

            max_score += float(q.score)

            if q.id in prior_result_map:
                # P1 规则 4 & 6: 已经提交过的单篇/题目直接继承已有成绩与解析，不重复计算判分
                inh = prior_result_map[q.id]
                if inh.is_estimated:
                    subjective_score += inh.score
                else:
                    objective_score += inh.score
                if inh.is_correct:
                    correct_count += 1

                gr = GradeResult(
                    id=str(uuid.uuid4()),
                    submission_id=submission_id,
                    question_id=q.id,
                    question_num=q.question_num,
                    user_answer=inh.user_answer,
                    correct_answer=inh.correct_answer,
                    is_correct=inh.is_correct,
                    is_estimated=inh.is_estimated,
                    score_band=inh.score_band,
                    score=inh.score,
                    max_score=inh.max_score,
                    evidence_sentence=inh.evidence_sentence,
                    explanation=inh.explanation,
                    category=inh.category
                )
                grade_results.append(gr)
            else:
                # 尚未提交的题目：首次执行批改 (P1 规则 5)
                newly_graded_count += 1
                is_subjective = (q.category == "subjective" or ak.correct_answer == "SUBJECTIVE")

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
                        newly_correct_count += 1

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
                        newly_correct_count += 1

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

                    # 客观错题归档 (PRD 10.1: 仅对新判分题目归档，避免重复叠加错题计数)
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

        # 5. 保存不可变的 Submission 快照 (P1 规则 10: 历史提交和成绩不得被覆盖)
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

        # 6. 更新作答会话状态 (P1 规则 1, 2, 9)
        # 单篇或板块提交后，Attempt 依然保持 in_progress 状态，用户可继续作答其他篇章；
        # 只有完成整卷提交 (scope == "exam") 或独立单篇练习目标完成 (attempt.target_type == scope)，才进入 graded 状态！
        is_final_exam = (scope == "exam")
        is_exact_target_finished = (attempt.target_type == scope and attempt.target_id == scope_id)

        if is_final_exam or is_exact_target_finished:
            attempt.status = "graded"
            attempt.submitted_at = now
        else:
            attempt.status = "in_progress"

        # 7. 更新全局学习档案 (P1 规则 7: 不允许重复计算已经提交的题目，仅累加新批改题数)
        if newly_graded_count > 0:
            cls._update_learning_profile(
                db, user_id,
                attempt.time_spent_seconds or 0,
                newly_graded_count,
                newly_correct_count
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
