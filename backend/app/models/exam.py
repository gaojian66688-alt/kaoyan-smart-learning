import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Exam(Base):
    __tablename__ = "exams"

    id = Column(String(64), primary_key=True)
    exam_type = Column(String(32), nullable=False, index=True)  # english_1 / english_2
    year = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    duration_minutes = Column(Integer, default=180)
    total_score = Column(Float, default=100.0)
    status = Column(String(32), default="published")  # draft / verified / published / archived
    created_at = Column(DateTime, default=utc_now)

    sections = relationship("Section", back_populates="exam", cascade="all, delete-orphan", order_by="Section.order_index")
    question_groups = relationship("QuestionGroup", back_populates="exam", order_by="QuestionGroup.order_index")


class Section(Base):
    __tablename__ = "sections"

    id = Column(String(64), primary_key=True)
    exam_id = Column(String(64), ForeignKey("exams.id"), nullable=False, index=True)
    section_code = Column(String(32), nullable=False)  # cloze, reading_a, reading_b, translation, writing_a, writing_b
    title = Column(String(255), nullable=False)
    order_index = Column(Integer, default=1)
    total_score = Column(Float, default=40.0)
    instructions = Column(Text, nullable=True)

    exam = relationship("Exam", back_populates="sections")
    question_groups = relationship("QuestionGroup", back_populates="section", cascade="all, delete-orphan", order_by="QuestionGroup.order_index")


class QuestionGroup(Base):
    """
    PRD 5.2 & G02: 最小完整作答单元
    不可拆散：完形(20题)、阅读A(5题)、新题型(5题)、翻译、写作。
    不得跨文拼题、缺段、乱序。
    """
    __tablename__ = "question_groups"

    id = Column(String(64), primary_key=True)
    section_id = Column(String(64), ForeignKey("sections.id"), nullable=False, index=True)
    exam_id = Column(String(64), ForeignKey("exams.id"), nullable=False, index=True)
    group_type = Column(String(32), nullable=False)  # cloze, reading_a, reading_b, translation, writing_a, writing_b
    title = Column(String(255), nullable=False)  # e.g., Text 1, Cloze, Translation
    passage_text = Column(Text, nullable=False)  # 完整文章正文/写作提示说明
    source_info = Column(String(512), nullable=True)  # 原文出处与版权状态
    order_index = Column(Integer, default=1)
    qa_status = Column(String(32), default="verified")  # verified / pending / rejected
    qa_checksum = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    section = relationship("Section", back_populates="question_groups")
    exam = relationship("Exam", back_populates="question_groups")
    questions = relationship("Question", back_populates="group", cascade="all, delete-orphan", order_by="Question.order_index")


class Question(Base):
    """
    独立题目对象：唯一 ID、严格保持原卷顺序、分值与选项
    """
    __tablename__ = "questions"

    id = Column(String(64), primary_key=True)
    group_id = Column(String(64), ForeignKey("question_groups.id"), nullable=False, index=True)
    question_num = Column(Integer, nullable=False)  # 原卷题号 (如 1-20, 21-40, 41-45, 46-50, 51, 52)
    prompt = Column(Text, nullable=False)  # 题干 / 题目要求
    options_json = Column(Text, nullable=False)  # JSON: [{"key": "A", "text": "..."}]
    score = Column(Float, default=2.0)  # 题目分值
    order_index = Column(Integer, default=1)
    category = Column(String(64), default="detail")  # detail / inference / main_idea / attitude / vocabulary / grammar / subjective

    group = relationship("QuestionGroup", back_populates="questions")
    answer_keys = relationship("AnswerKey", back_populates="question", cascade="all, delete-orphan")

    def get_options(self):
        try:
            return json.loads(self.options_json)
        except Exception:
            return []


class AnswerKey(Base):
    """
    PRD G03 & 6.1: 唯一标准答案与权威解析
    版本化管理，客观题严格核验；主观题配备评分细则与分档标准
    """
    __tablename__ = "answer_keys"

    id = Column(String(64), primary_key=True)
    question_id = Column(String(64), ForeignKey("questions.id"), nullable=False, index=True)
    version = Column(String(32), default="1.0")
    correct_answer = Column(String(16), nullable=False)  # "A" / "B" / "C" / "D" 或 "SUBJECTIVE"
    evidence_sentence = Column(Text, nullable=True)  # 原文证据句 / 定位依据
    explanation = Column(Text, nullable=False)  # 详细解析与选项剖析
    rubric_json = Column(Text, nullable=True)  # PRD 8.4: 主观题分档细则与评分点 [{"band": "一类(17-20分)", "criteria": "..."}]
    verifier = Column(String(128), default="Expert QA Panel")
    status = Column(String(32), default="verified")  # verified / superseded
    verified_at = Column(DateTime, default=utc_now)

    question = relationship("Question", back_populates="answer_keys")

    def get_rubric(self):
        try:
            return json.loads(self.rubric_json) if self.rubric_json else []
        except Exception:
            return []


class ContentQALog(Base):
    """
    PRD 6.2 & AT-09: 资源发布前 QA 门禁校验日志
    """
    __tablename__ = "content_qa_logs"

    id = Column(String(64), primary_key=True)
    target_id = Column(String(64), nullable=False, index=True)
    target_type = Column(String(32), nullable=False)  # group / exam / asset
    rule_name = Column(String(64), nullable=False)
    passed = Column(Boolean, nullable=False)
    details = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=utc_now)
