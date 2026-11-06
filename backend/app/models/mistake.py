from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from app.database import Base

class Mistake(Base):
    """
    PRD 10.1: 错题本模型
    根据已提交评分自动收录错题，完整保留原题上下文、作答快照、用户真实错因标记与复练状态。
    """
    __tablename__ = "mistakes"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), default="default_user", index=True)
    question_id = Column(String(64), ForeignKey("questions.id"), nullable=False, index=True)
    group_id = Column(String(64), nullable=False, index=True)
    last_submission_id = Column(String(64), nullable=False)
    last_user_answer = Column(String(16), nullable=True)
    correct_answer = Column(String(16), nullable=False)
    wrong_count = Column(Integer, default=1)
    first_wrong_at = Column(DateTime, default=datetime.utcnow)
    last_wrong_at = Column(DateTime, default=datetime.utcnow)
    user_reason_tag = Column(String(64), nullable=True)  # 用户自认错因标签
    ai_reason_hypothesis = Column(Text, nullable=True)  # AI 假说错因
    is_mastered = Column(Boolean, default=False)
