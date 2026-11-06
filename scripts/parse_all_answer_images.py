import os
import re
import json
import easyocr

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)

answer_dir = "scratch_answers"
results = {}

files = sorted([f for f in os.listdir(answer_dir) if f.endswith("_answers.png")])
print(f"Processing {len(files)} answer images...")

for f in files:
    key = f.replace("_answers.png", "")
    img_path = os.path.join(answer_dir, f)
    tokens = reader.readtext(img_path, detail=0)
    full_text = "\n".join(tokens)
    results[key] = {
        "tokens": tokens,
        "full_text": full_text
    }
    print(f"Extracted {key}: {len(tokens)} tokens")

with open(os.path.join(answer_dir, "parsed_raw_answers.json"), "w", encoding="utf-8") as out:
    json.dump(results, out, ensure_ascii=False, indent=2)

print("Finished saving parsed_raw_answers.json!")
