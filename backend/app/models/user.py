import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    preferred_exam = Column(String(32), default="english_1")
    created_at = Column(DateTime, default=datetime.utcnow)


class LearningProfile(Base):
    """
    PRD 10.2 & G08: 共享学习档案
    记录刷题、生词、复习、错题的全局事实指标
    """
    __tablename__ = "learning_profiles"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    total_time_seconds = Column(Integer, default=0)
    total_questions_attempted = Column(Integer, default=0)
    total_questions_correct = Column(Integer, default=0)
    overall_accuracy = Column(Float, default=0.0)
    total_vocabulary_marked = Column(Integer, default=0)
    total_reviews_completed = Column(Integer, default=0)
    consecutive_study_days = Column(Integer, default=1)
    last_active_date = Column(String(32), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIReportRecord(Base):
    """
    PRD 8.3 & 12.2: AI 分层报告及可解释证据
    """
    __tablename__ = "ai_reports"

    id = Column(String(64), primary_key=True)
    submission_id = Column(String(64), nullable=False, index=True)
    scope = Column(String(32), nullable=False)  # group / section / exam
    summary = Column(Text, nullable=False)
    evidence_json = Column(Text, nullable=False)  # JSON-encoded evidence items
    recommendations_json = Column(Text, nullable=True)
    model_version = Column(String(64), default="rule_evidence_engine_v1")
    created_at = Column(DateTime, default=datetime.utcnow)

    def get_evidence(self):
        try:
            return json.loads(self.evidence_json)
        except Exception:
            return []

    def get_recommendations(self):
        try:
            return json.loads(self.recommendations_json) if self.recommendations_json else []
        except Exception:
            return []
