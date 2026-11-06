from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base, utc_now

class WordDict(Base):
    """
    词汇基础字典（内置 6590 考研高频大纲词汇与核心短语）
    """
    __tablename__ = "word_dicts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(128), unique=True, nullable=False, index=True)
    phonetic = Column(String(64), nullable=True)
    meaning = Column(Text, nullable=False)


class UserVocabulary(Base):
    """
    PRD 9.2: 用户生词卡片与 FSRS 记忆状态（支持单词及多词核心短语搭配）
    """
    __tablename__ = "user_vocabularies"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), default="default_user", index=True)
    word = Column(String(128), nullable=False, index=True)
    lemma = Column(String(128), nullable=True)
    phonetic = Column(String(64), nullable=True)
    definition = Column(Text, nullable=False)  # 当前真题语境义项
    occurrence_count = Column(Integer, default=1)  # 跨真题曝光/标记次数
    
    # FSRS v4.5 parameters
    stability = Column(Float, default=0.0)      # 记忆稳定性 S
    difficulty = Column(Float, default=0.0)     # 难度 D (1.0 - 10.0)
    reps = Column(Integer, default=0)           # 历史有效复习次数
    lapses = Column(Integer, default=0)         # 遗忘次数 (rating=Again)
    state = Column(Integer, default=0)          # 0=New, 1=Learning, 2=Review, 3=Relearning
    due_date = Column(DateTime, default=utc_now, index=True)
    last_review = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    occurrences = relationship("VocabularyOccurrence", back_populates="user_vocab", cascade="all, delete-orphan")
    review_logs = relationship("ReviewLog", back_populates="user_vocab", cascade="all, delete-orphan", order_by="ReviewLog.reviewed_at.desc()")


class VocabularyOccurrence(Base):
    """
    PRD 9.4: 真题原句与出处溯源（一个词多次出现，多条语境可查看）
    """
    __tablename__ = "vocabulary_occurrences"

    id = Column(String(64), primary_key=True)
    user_vocab_id = Column(String(64), ForeignKey("user_vocabularies.id"), nullable=False, index=True)
    context_sentence = Column(Text, nullable=False)  # 原文例句
    source_info = Column(String(255), nullable=False)  # e.g., 2024 考研英语（一）Text 1
    group_id = Column(String(64), nullable=True, index=True)
    marked_at = Column(DateTime, default=utc_now)

    user_vocab = relationship("UserVocabulary", back_populates="occurrences")


class ReviewLog(Base):
    """
    PRD 9.3: FSRS 复习历史记录（不可修改的追加审计日志）
    """
    __tablename__ = "review_logs"

    id = Column(String(64), primary_key=True)
    user_vocab_id = Column(String(64), ForeignKey("user_vocabularies.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1=Again, 2=Hard, 3=Good, 4=Easy
    stability_before = Column(Float, default=0.0)
    stability_after = Column(Float, default=0.0)
    difficulty_before = Column(Float, default=0.0)
    difficulty_after = Column(Float, default=0.0)
    interval_days = Column(Float, default=0.0)
    reviewed_at = Column(DateTime, default=utc_now)

    user_vocab = relationship("UserVocabulary", back_populates="review_logs")
