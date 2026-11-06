from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
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
    user_answer = Column(Text, nullable=True)  # 客观题为 "A"/"B"/"C"/"D", 主观题为文本
    is_final_snapshot = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    attempt = relationship("Attempt", back_populates="responses")


class Submission(Base):
    """
    提交记录：记录提交范围 (单篇/板块/整卷)、得分汇总与不可变快照。
    PRD 8.4: 明确区分客观确定分与主观 AI 估分。
    """
    __tablename__ = "submissions"

    id = Column(String(64), primary_key=True)
    attempt_id = Column(String(64), ForeignKey("attempts.id"), nullable=False, index=True)
    scope = Column(String(32), nullable=False)  # group / section / exam
    scope_id = Column(String(64), nullable=False, index=True)
    total_score = Column(Float, default=0.0)
    max_score = Column(Float, default=0.0)
    objective_score = Column(Float, default=0.0)
    subjective_score = Column(Float, default=0.0)
    accuracy = Column(Float, default=0.0)
    question_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    answer_key_version = Column(String(32), default="1.0")
    submitted_at = Column(DateTime, default=utc_now)

    attempt = relationship("Attempt", back_populates="submissions")
    grade_results = relationship("GradeResult", back_populates="submission", cascade="all, delete-orphan")


class GradeResult(Base):
    """
    PRD 8.1 & 8.4: 逐题判分记录
    客观题由确定性内核判分；主观题配备 AI 规则估分区间与分档依据。
    """
    __tablename__ = "grade_results"

    id = Column(String(64), primary_key=True)
    submission_id = Column(String(64), ForeignKey("submissions.id"), nullable=False, index=True)
    question_id = Column(String(64), nullable=False, index=True)
    question_num = Column(Integer, nullable=False)
    user_answer = Column(Text, nullable=True)
    correct_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    is_estimated = Column(Boolean, default=False)  # PRD 8.4: 主观题明确标示估分性质
    score_band = Column(String(64), nullable=True)  # 主观题评分档次 (如 "一档(17-20分)")
    score = Column(Float, default=0.0)
    max_score = Column(Float, default=2.0)
    evidence_sentence = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    category = Column(String(64), default="detail")

    submission = relationship("Submission", back_populates="grade_results")
