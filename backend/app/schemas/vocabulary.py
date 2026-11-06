from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class WordLookupResponse(BaseModel):
    word: str
    phonetic: Optional[str] = None
    meaning: str
    is_saved: bool = False
    detected_phrases: list[dict] = []

class MarkWordRequest(BaseModel):
    word: str
    context_sentence: str
    source_info: str
    group_id: Optional[str] = None
    definition: Optional[str] = None
    user_id: Optional[str] = "default_user"

class VocabularyOccurrenceSchema(BaseModel):
    context_sentence: str
    source_info: str
    group_id: Optional[str] = None
    marked_at: datetime

class UserVocabularySchema(BaseModel):
    id: str
    word: str
    phonetic: Optional[str] = None
    definition: str
    occurrence_count: int
    stability: float
    difficulty: float
    reps: int
    lapses: int
    state: int
    due_date: datetime
    last_review: Optional[datetime] = None
    occurrences: list[VocabularyOccurrenceSchema] = []

    class Config:
        from_attributes = True

class ReviewFeedbackRequest(BaseModel):
    vocab_id: str
    rating: int  # 1=Again, 2=Hard, 3=Good, 4=Easy
    user_id: Optional[str] = "default_user"

class ReviewFeedbackResponse(BaseModel):
    vocab_id: str
    rating: int
    new_stability: float
    new_difficulty: float
    interval_days: float
    next_due_date: datetime
    new_state: int
