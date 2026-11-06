from typing import Optional, Any
from pydantic import BaseModel

class OptionItem(BaseModel):
    key: str  # A / B / C / D
    text: str

class QuestionSchema(BaseModel):
    id: str
    group_id: str
    question_num: int
    prompt: str
    options: list[OptionItem]
    score: float
    order_index: int
    category: str

    class Config:
        from_attributes = True

class QuestionGroupDetailSchema(BaseModel):
    id: str
    section_id: str
    exam_id: str
    group_type: str
    title: str
    passage_text: str
    source_info: Optional[str] = None
    order_index: int
    qa_status: str
    questions: list[QuestionSchema]

    class Config:
        from_attributes = True

class QuestionGroupSummarySchema(BaseModel):
    id: str
    section_id: str
    exam_id: str
    group_type: str
    title: str
    order_index: int
    qa_status: str
    question_count: int

class SectionSchema(BaseModel):
    id: str
    exam_id: str
    section_code: str
    title: str
    order_index: int
    total_score: float
    instructions: Optional[str] = None
    question_groups: list[QuestionGroupSummarySchema] = []

    class Config:
        from_attributes = True

class ExamSchema(BaseModel):
    id: str
    exam_type: str
    year: int
    title: str
    duration_minutes: int
    total_score: float
    status: str
    sections: list[SectionSchema] = []

    class Config:
        from_attributes = True

class AnswerKeySchema(BaseModel):
    question_id: str
    version: str
    correct_answer: str
    evidence_sentence: Optional[str] = None
    explanation: str
    verifier: str
