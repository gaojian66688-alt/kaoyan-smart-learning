from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Attempt(Base):
    """
    作答会话状态机：
    未开始 -> 作答中 (auto-saving) -> 已提交/评分 (locked snapshot) -> 已分析
    """
    __tablename__ = "attempts"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), default="default_user", index=True)
    mode = Column(String(32), nullable=False)  # special_training / practice_full / strict_mock
    target_type = Column(String(32), nullable=False)  # group / section / exam
    target_id = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="in_progress")  # in_progress / submitted / graded / analyzed
    time_spent_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    responses = relationship("Response", back_populates="attempt", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="attempt", cascade="all, delete-orphan")


class Response(Base):
    """
    用户答题暂存与快照记录。
    作答中支持实时自动保存；一旦随单元/板块/整卷提交，锁定为 is_final_snapshot=True，不可篡改。
    """
    __tablename__ = "responses"

    id = Column(String(64), primary_key=True)
    attempt_id = Column(String(64), ForeignKey("attempts.id"), nullable=False, index=True)
    question_id = Column(String(64), nullable=False, index=True)
    user_answer = Column(String(16), nullable=True)  # "A" / "B" / "C" / "D"
    is_final_snapshot = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attempt = relationship("Attempt", back_populates="responses")


class Submission(Base):
    """
    提交记录：记录提交范围 (单篇/板块/整卷)、得分汇总与不可变快照。
    """
    __tablename__ = "submissions"

    id = Column(String(64), primary_key=True)
    attempt_id = Column(String(64), ForeignKey("attempts.id"), nullable=False, index=True)
    scope = Column(String(32), nullable=False)  # group / section / exam
    scope_id = Column(String(64), nullable=False, index=True)
    total_score = Column(Float, default=0.0)
    max_score = Column(Float, default=0.0)
    accuracy = Column(Float, default=0.0)
    question_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    answer_key_version = Column(String(32), default="1.0")
    submitted_at = Column(DateTime, default=datetime.utcnow)

    attempt = relationship("Attempt", back_populates="submissions")
    grade_results = relationship("GradeResult", back_populates="submission", cascade="all, delete-orphan")


class GradeResult(Base):
    """
    PRD 8.1: 客观题唯一评分内核判分结果，强不可变性。
    同一题目在单篇、板块、整卷批改时得出完全一致的客观判分事实。
    """
    __tablename__ = "grade_results"

    id = Column(String(64), primary_key=True)
    submission_id = Column(String(64), ForeignKey("submissions.id"), nullable=False, index=True)
    question_id = Column(String(64), nullable=False, index=True)
    question_num = Column(Integer, nullable=False)
    user_answer = Column(String(16), nullable=True)
    correct_answer = Column(String(16), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    score = Column(Float, default=0.0)
    max_score = Column(Float, default=2.0)
    evidence_sentence = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    category = Column(String(64), default="detail")

    submission = relationship("Submission", back_populates="grade_results")
