from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel

class EvidenceItemSchema(BaseModel):
    type: str
    question_num: int
    category: Optional[str] = None
    fact: str
    evidence_quote: str
    explanation_excerpt: Optional[str] = None
    hypothesis: str
    confidence: str
    status: str

class AIReportSchema(BaseModel):
    id: str
    submission_id: str
    scope: str
    summary: str
    evidence_items: list[dict[str, Any]]
    recommendations: list[str]
    model_version: str
    created_at: datetime
