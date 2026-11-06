import json
import re

with open("scratch_answers/parsed_raw_answers.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Keys:", list(data.keys()))

# Let's inspect a few
for k in ["en1_2007", "en1_2015", "en1_2024", "en2_2010", "en2_2020", "en2_2024"]:
    if k in data:
        print(f"\n================= {k} =================")
        print(data[k]["full_text"][:400])
