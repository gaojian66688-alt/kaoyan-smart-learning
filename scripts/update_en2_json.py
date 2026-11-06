import json
import os
import easyocr

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)

with open("scratch_answers/parsed_raw_answers.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for y in range(2014, 2026):
    k = f"en2_{y}"
    img_path = f"scratch_answers/{k}_answers.png"
    tokens = reader.readtext(img_path, detail=0)
    full_text = "\n".join(tokens)
    data[k] = {
        "tokens": tokens,
        "full_text": full_text
    }
    print(f"Updated {k}: {len(tokens)} tokens")

with open("scratch_answers/parsed_raw_answers.json", "w", encoding="utf-8") as out:
    json.dump(data, out, ensure_ascii=False, indent=2)

print("Updated parsed_raw_answers.json successfully!")
