import json

with open("scratch_answers/extracted_objective_keys.json", "r", encoding="utf-8") as f:
    keys = json.load(f)

print("Sample en2_2024 answers:", keys.get("en2_2024", {}).get("answers"))
print("Sample en1_2024 answers:", keys.get("en1_2024", {}).get("answers"))
print("Sample en2_2015 answers:", keys.get("en2_2015", {}).get("answers"))
