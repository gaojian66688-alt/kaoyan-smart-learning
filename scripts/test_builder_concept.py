import sys
import os
import json

sys.path.insert(0, os.path.abspath("backend"))

from app.database import engine, SessionLocal, Base
from app.models.exam import Exam, Section, QuestionGroup, Question, AnswerKey
from app.core.qa_gate import ContentQAGate

print("Testing QA Gate compatibility with builder schema...")
