import json
import re

with open("scratch_answers/parsed_raw_answers.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

extracted_keys = {}

for k, val in raw.items():
    text = val["full_text"]
    # Look for numbered answers like 1. B or 1.B or 1 B or 21. C
    # Patterns: (\d+)\s*[\.、\s]\s*([A-G])
    matches = re.findall(r'(?<!\d)(\d{1,2})\s*[\.、\s\-_]\s*([A-G])(?!\w)', text)
    # Filter and deduplicate by question number
    q_map = {}
    for num_str, ans in matches:
        num = int(num_str)
        if 1 <= num <= 45:
            if num not in q_map:
                q_map[num] = ans
    
    extracted_keys[k] = {
        "count": len(q_map),
        "answers": q_map
    }
    print(f"{k}: found {len(q_map)} objective answers")

with open("scratch_answers/extracted_objective_keys.json", "w", encoding="utf-8") as f:
    json.dump(extracted_keys, f, indent=2)

print("Saved extracted_objective_keys.json")
