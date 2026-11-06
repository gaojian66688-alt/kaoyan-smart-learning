import re

with open("backend/app/data/seed_genuine_exams.py", "r", encoding="utf-8") as f:
    text = f.read()

matches = re.findall(r'"id":\s*"(20\d\d-[^"]+)",\s*"exam_type":\s*"([^"]+)",\s*"year":\s*(\d+)', text)
for m in matches:
    print(m)
