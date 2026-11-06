import json
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.database import engine, SessionLocal, Base
from app.models.exam import Exam, Section, QuestionGroup, Question, AnswerKey
from app.core.qa_gate import ContentQAGate
from app.data.exam_manifest import get_all_exam_metadata

print("Loaded manifest successfully.")
all_metadata = get_all_exam_metadata()
print(f"Total exams in manifest: {len(all_metadata)}")
