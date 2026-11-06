import hashlib
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.exam import QuestionGroup, Question, AnswerKey, ContentQALog

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class QAGateResult:
    def __init__(self, is_valid: bool, errors: list[str], warnings: list[str], checksum: str = ""):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings
        self.checksum = checksum

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "checksum": self.checksum,
        }

class ContentQAGate:
    """
    PRD 6.2 & AT-09: 全板块题库与资源发布门禁系统
    覆盖完形填空 (Cloze)、阅读A (Reading A)、新题型 (Reading B)、翻译 (Translation) 和写作 (Writing)。
    任何单元缺失关键信息、缺段、选项不足、答案错配或题号乱序，坚决阻止发布。
    """

    @staticmethod
    def compute_group_checksum(group: QuestionGroup, questions: list[Question], answer_keys: list[AnswerKey]) -> str:
        h = hashlib.sha256()
        h.update(group.passage_text.strip().encode("utf-8"))
        for q in sorted(questions, key=lambda x: x.order_index):
            h.update(str(q.question_num).encode("utf-8"))
            h.update(q.prompt.strip().encode("utf-8"))
            h.update(q.options_json.strip().encode("utf-8"))
        for ak in sorted(answer_keys, key=lambda x: x.question_id):
            h.update(ak.correct_answer.strip().encode("utf-8"))
        return h.hexdigest()

    @classmethod
    def validate_question_group(cls, db: Session, group_id: str, record_logs: bool = True) -> QAGateResult:
        errors = []
        warnings = []

        group = db.query(QuestionGroup).filter(QuestionGroup.id == group_id).first()
        if not group:
            return QAGateResult(False, [f"QuestionGroup with ID {group_id} does not exist."], [])

        # 1. 验证正文完整性与真实来源 (PRD G01)
        if not group.passage_text or len(group.passage_text.strip()) < 50:
            errors.append("Passage/Prompt text is empty or shorter than 50 characters (incomplete).")

        # 检查来源是否缺失或为占位符 (P0 要求)
        if not group.source_info or len(group.source_info.strip()) < 5:
            errors.append("真题来源缺失：QuestionGroup 缺少经过核验的真实来源出处 (source_info)，必须拦截发布。")
        elif any(ph in group.source_info.lower() for ph in ["placeholder", "unknown", "待补充", "暂无"]):
            errors.append("真题来源无效：检测到占位符来源描述。")

        # 检查不同年份重复文章 (P0 要求 3: 不同年份重复文章必须经过来源核查)
        if group.exam_id:
            from app.models.exam import Exam
            curr_exam = db.query(Exam).filter(Exam.id == group.exam_id).first()
            if curr_exam:
                dup_group = (
                    db.query(QuestionGroup)
                    .join(Exam, QuestionGroup.exam_id == Exam.id)
                    .filter(
                        QuestionGroup.id != group.id,
                        QuestionGroup.exam_id != group.exam_id,
                        Exam.year != curr_exam.year,
                        QuestionGroup.passage_text == group.passage_text
                    )
                    .first()
                )
                if dup_group:
                    dup_exam = db.query(Exam).filter(Exam.id == dup_group.exam_id).first()
                    dup_year = dup_exam.year if dup_exam else "其他年份"
                    errors.append(
                        f"真题真实性门禁拦截：检测到不同年份（{curr_exam.year}年 与 {dup_year}年）存在完全重复文章，未经核查严禁发布。"
                    )

        questions = db.query(Question).filter(Question.group_id == group_id).order_by(Question.order_index).all()

        # 2. 按题型定义严格最小完整单元 (PRD 5.2)
        gt = group.group_type
        if gt == "reading_a":
            if len(questions) != 5:
                errors.append(f"Reading comprehension Part A must strictly contain 5 questions. Found {len(questions)}.")
        elif gt == "cloze":
            if len(questions) != 20:
                errors.append(f"Cloze (Use of English) must strictly contain 20 questions. Found {len(questions)}.")
        elif gt == "reading_b":
            if len(questions) != 5:
                errors.append(f"Reading Part B (新题型) must strictly contain 5 questions. Found {len(questions)}.")
        elif gt == "translation":
            if len(questions) not in [1, 5]:
                errors.append(f"Translation must contain 1 (English II) or 5 (English I) questions. Found {len(questions)}.")
        elif gt in ["writing_a", "writing_b"]:
            if len(questions) != 1:
                errors.append(f"Writing task must contain exactly 1 question prompt. Found {len(questions)}.")
        elif len(questions) == 0:
            errors.append("Question group contains no questions.")

        # 3. 验证题目序号连续性 (如 1-20, 21-25, 41-45 等)
        for i in range(len(questions) - 1):
            if questions[i + 1].question_num != questions[i].question_num + 1:
                errors.append(
                    f"Question numbers must be continuous and in order. Gap found between #{questions[i].question_num} and #{questions[i + 1].question_num}."
                )

        # 4. 逐题校验选项、标准答案、真实性与评分细则 (防模板生成)
        all_answer_keys = []
        seen_option_signatures = []

        # 模板生成特征词汇检测黑名单
        SYNTHETIC_EVIDENCE_PATTERNS = [
            "Key evidence sentence cited from Paragraph",
            "Sentence containing blank [",
            "Cohesive context markers and thematic progression",
            "Full authentic English II translation passage",
            "Underlined sentence segment ("
        ]
        SYNTHETIC_EXPLANATION_PATTERNS = [
            "准确契合上下文主题语境，符合学术英语语义规范",
            "对原文关键论点进行了严密而准确的同义转述，逻辑严谨，论据充分",
            "均属典型考研真题命题陷阱"
        ]

        for q in questions:
            is_subjective = gt in ["translation", "writing_a", "writing_b"]

            if not is_subjective:
                options = q.get_options()
                if gt == "reading_b":
                    # 新题型备选项通常为 5-7 项 (A-G 或小标题)
                    if len(options) < 5:
                        errors.append(f"Reading Part B question #{q.question_num} must have at least 5 candidates. Found {len(options)}.")
                else:
                    # 完形和阅读 A 严格 4 选 1
                    if len(options) != 4:
                        errors.append(f"Question #{q.question_num} must have exactly 4 options. Found {len(options)}.")
                    else:
                        opt_keys = {opt.get("key") for opt in options}
                        if opt_keys != {"A", "B", "C", "D"}:
                            errors.append(f"Question #{q.question_num} options must be labeled A, B, C, D. Found {opt_keys}.")

                # 检测选项是否为固定模板跨题重复
                if options:
                    opt_sig = "|".join(opt.get("text", "").strip() for opt in options)
                    seen_option_signatures.append(opt_sig)

            keys = db.query(AnswerKey).filter(
                AnswerKey.question_id == q.id,
                AnswerKey.status == "verified"
            ).all()

            if not keys:
                errors.append(f"Question #{q.question_num} lacks a verified AnswerKey.")
            else:
                ak = keys[0]
                all_answer_keys.append(ak)

                # 禁止硬编码 'Official Verification Panel' 虚假审核记录 (P0 规则 6)
                if ak.verifier == "Official Verification Panel":
                    errors.append(
                        f"真题真实性门禁拦截：Question #{q.question_num} 答案审核人不能使用虚假硬编码 'Official Verification Panel'。"
                    )

                # 占位符定位句检测 (P0 规则 5)
                if ak.evidence_sentence:
                    for syn_p in SYNTHETIC_EVIDENCE_PATTERNS:
                        if syn_p in ak.evidence_sentence:
                            errors.append(
                                f"真题真实性门禁拦截：Question #{q.question_num} 检测到模板占位定位句 ('{syn_p}')，禁止通过门禁。"
                            )
                            break

                # 占位符解析检测 (P0 规则 5)
                if ak.explanation:
                    for syn_exp in SYNTHETIC_EXPLANATION_PATTERNS:
                        if syn_exp in ak.explanation:
                            errors.append(
                                f"真题真实性门禁拦截：Question #{q.question_num} 检测到模板公式化解析，禁止通过真实性门禁。"
                            )
                            break

                if is_subjective:
                    # 主观题检查评分细则 (PRD 8.4)
                    if not ak.explanation or len(ak.explanation.strip()) == 0:
                        errors.append(f"Subjective Question #{q.question_num} reference translation or sample is missing.")
                    if not ak.rubric_json or len(ak.rubric_json.strip()) == 0:
                        warnings.append(f"Subjective Question #{q.question_num} scoring rubric bands are missing.")
                else:
                    if ak.correct_answer not in {"A", "B", "C", "D", "E", "F", "G"}:
                        errors.append(f"Question #{q.question_num} correct answer '{ak.correct_answer}' is invalid.")
                    if not ak.explanation or len(ak.explanation.strip()) == 0:
                        errors.append(f"Question #{q.question_num} explanation is missing.")

        # 检测同题组内是否有 2 道以上题目拥有完全相同的选项文本集合 (固定选项模板检测，排除新题型 7选5)
        if gt != "reading_b" and len(seen_option_signatures) >= 2:
            from collections import Counter
            counts = Counter(seen_option_signatures)
            for sig, cnt in counts.items():
                if cnt >= 2 and len(sig) > 20:
                    errors.append(
                        f"真题真实性门禁拦截：检测到重复选项模板（共有 {cnt} 道题目选项完全相同），禁止伪造真题。"
                    )
                    break

        checksum = cls.compute_group_checksum(group, questions, all_answer_keys) if not errors else ""
        is_valid = len(errors) == 0

        # 更新题组状态与校验指纹
        if is_valid:
            group.qa_status = "verified"
            group.qa_checksum = checksum
        else:
            group.qa_status = "rejected"

        if record_logs:
            log_entry = ContentQALog(
                id=str(uuid.uuid4()),
                target_id=group_id,
                target_type="group",
                rule_name="G01_G02_CONTENT_GATE",
                passed=is_valid,
                details=json.dumps({"errors": errors, "warnings": warnings, "checksum": checksum}, ensure_ascii=False),
                checked_at=utc_now()
            )
            db.add(log_entry)
            db.commit()

        return QAGateResult(is_valid, errors, warnings, checksum)
