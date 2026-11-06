from typing import Optional
from pydantic import BaseModel

class LearningProfileSchema(BaseModel):
    user_id: str
    total_time_seconds: int
    total_questions_attempted: int
    total_questions_correct: int
    overall_accuracy: float
    total_vocabulary_marked: int
    total_reviews_completed: int
    consecutive_study_days: int

    class Config:
        from_attributes = True

class TodayPlanSchema(BaseModel):
    due_reviews_count: int
    unconsolidated_mistakes_count: int
    recommended_reading_group_id: Optional[str] = None
    recommended_reading_title: Optional[str] = None
    consecutive_days: int

class CategoryStatItem(BaseModel):
    category: str
    category_name: str
    total: int
    correct: int
    accuracy: float

class DailyTrendItem(BaseModel):
    date: str
    attempted: int
    correct: int
    accuracy: float

class VocabDistributionSchema(BaseModel):
    new_words: int
    learning: int
    review: int
    relearning: int
    mastered: int
    total: int

class ProfileTrendsSchema(BaseModel):
    user_id: str
    overall_accuracy: float
    retention_rate: float
    category_accuracy: list[CategoryStatItem]
    daily_trends: list[DailyTrendItem]
    vocab_distribution: VocabDistributionSchema
    weak_points: list[str]
    strengths: list[str]
