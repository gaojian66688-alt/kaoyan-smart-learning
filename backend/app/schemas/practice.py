from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class AttemptCreate(BaseModel):
    mode: str  # special_training / practice_full / strict_mock
    target_type: str  # group / section / exam
    target_id: str
    user_id: Optional[str] = "default_user"

class GradeResultSchema(BaseModel):
    question_id: str
    question_num: int
    user_answer: Optional[str] = None
    correct_answer: str
    is_correct: bool
    is_estimated: bool = False
    score_band: Optional[str] = None
    score: float
    max_score: float
    evidence_sentence: Optional[str] = None
    explanation: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True

class AttemptResponse(BaseModel):
    id: str
    mode: str
    target_type: str
    target_id: str
    status: str
    time_spent_seconds: int
    created_at: datetime
    saved_responses: dict[str, str] = {}
    prior_results: list[GradeResultSchema] = []

class ResponseSaveItem(BaseModel):
    question_id: str
    user_answer: str

class BatchResponseSave(BaseModel):
    attempt_id: str
    responses: list[ResponseSaveItem]
    time_spent_seconds: Optional[int] = None

class SubmitRequest(BaseModel):
    attempt_id: str
    scope: str  # group / section / exam
    scope_id: str
    user_id: Optional[str] = "default_user"

class SubmissionResponse(BaseModel):
    id: str
    attempt_id: str
    scope: str
    scope_id: str
    total_score: float
    max_score: float
    objective_score: float = 0.0
    subjective_score: float = 0.0
    accuracy: float
    question_count: int
    correct_count: int
    submitted_at: datetime
    results: list[GradeResultSchema]

    class Config:
        from_attributes = True
