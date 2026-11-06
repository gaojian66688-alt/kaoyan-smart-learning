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

        # 1. 验证正文完整性
        if not group.passage_text or len(group.passage_text.strip()) < 50:
            errors.append("Passage/Prompt text is empty or shorter than 50 characters (incomplete).")

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

        # 4. 逐题校验选项、标准答案与评分细则
        all_answer_keys = []
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

            keys = db.query(AnswerKey).filter(
                AnswerKey.question_id == q.id,
                AnswerKey.status == "verified"
            ).all()

            if not keys:
                errors.append(f"Question #{q.question_num} lacks a verified AnswerKey.")
            else:
                ak = keys[0]
                all_answer_keys.append(ak)

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
