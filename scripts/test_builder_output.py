import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.data.question_bank_builder import build_all_exams

exams = build_all_exams()
print(f"Total exams built: {len(exams)}")
total_groups = 0
total_questions = 0

for ex in exams:
    for sec in ex["sections"]:
        for grp in sec["groups"]:
            total_groups += 1
            total_questions += len(grp["questions"])

print(f"Total question groups: {total_groups}")
print(f"Total questions: {total_questions}")

# Print sample from 2007-english-1 and 2010-english-2
for ex in exams:
    if ex["id"] in ["2007-english-1", "2010-english-2", "2024-english-1"]:
        print(f"\nExam: {ex['id']} - {ex['title']}")
        print(f"  Sections: {len(ex['sections'])}")
        for sec in ex["sections"]:
            print(f"    Sec: {sec['title']} ({len(sec['groups'])} groups)")
