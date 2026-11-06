import json
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.data.exam_manifest import get_all_exam_metadata
from app.data.authentic_data_source import HISTORICAL_OFFICIAL_KEYS

print(f"Total exams to generate: {len(get_all_exam_metadata())}")
print(f"Total answer key maps: {len(HISTORICAL_OFFICIAL_KEYS)}")
