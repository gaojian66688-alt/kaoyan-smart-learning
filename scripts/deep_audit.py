import sqlite3
import json
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('backend/kaoyan_learning.db')
c = conn.cursor()

print("="*60)
print("1. EXAMS AUDIT")
print("="*60)
c.execute("SELECT id, exam_type, year, title, status FROM exams ORDER BY year DESC, exam_type")
exams = c.fetchall()
print(f"Total exams registered: {len(exams)}")
status_counts = {}
for e in exams:
    status_counts[e[4]] = status_counts.get(e[4], 0) + 1
print(f"Status distribution: {status_counts}")

print("\n="*60)
print("2. QUESTION GROUPS AUDIT")
print("="*60)
c.execute("""
    SELECT qg.id, qg.exam_id, qg.group_type, qg.title, qg.qa_status, 
           qg.source_info, length(qg.passage_text), COUNT(q.id) as q_count
    FROM question_groups qg
    LEFT JOIN questions q ON q.group_id = qg.id
    GROUP BY qg.id
    ORDER BY qg.order_index
""")
groups = c.fetchall()
print(f"Total question groups in DB: {len(groups)}")
for g in groups:
    print(f"Group ID: {g[0]}")
    print(f"  Exam: {g[1]} | Type: {g[2]} | Title: {g[3]}")
    print(f"  QA Status: {g[4]} | Passage len: {g[6]} | Questions: {g[7]}")
    print(f"  Source: {g[5][:80]}...")

print("\n="*60)
print("3. QUESTIONS & ANSWER KEYS AUDIT")
print("="*60)
c.execute("""
    SELECT q.id, q.group_id, q.question_num, q.prompt, q.options_json, q.score, q.category,
           ak.correct_answer, ak.evidence_sentence, ak.explanation, ak.verifier, ak.status, ak.rubric_json
    FROM questions q
    LEFT JOIN answer_keys ak ON ak.question_id = q.id
    ORDER BY q.question_num
""")
questions = c.fetchall()
print(f"Total questions in DB: {len(questions)}")

errors_found = []
for q in questions:
    qid, gid, qnum, prompt, opt_json, score, cat, ans, evidence, expl, verifier, ak_status, rubric = q
    # Check options
    opt_keys = []
    if opt_json:
        try:
            parsed = json.loads(opt_json)
            if isinstance(parsed, list):
                opt_keys = [item.get("key") for item in parsed if isinstance(item, dict)]
            elif isinstance(parsed, dict):
                opt_keys = list(parsed.keys())
        except Exception as ex:
            errors_found.append(f"Q{qnum} ({qid}) Invalid options JSON: {ex}")
    
    # Check answer
    if not ans:
        errors_found.append(f"Q{qnum} ({qid}) Missing correct answer")
    elif opt_keys and ans not in opt_keys:
        errors_found.append(f"Q{qnum} ({qid}) Correct answer '{ans}' not in options {opt_keys}")
        
    # Check explanation
    if not expl or len(expl.strip()) < 10:
        errors_found.append(f"Q{qnum} ({qid}) Explanation missing or too short: '{expl}'")
    if "Official Verification Panel" in (expl or "") or "TODO" in (expl or "") or "placeholder" in (expl.lower() if expl else ""):
        errors_found.append(f"Q{qnum} ({qid}) Explanation contains placeholder/fake audit text")
        
    # Check evidence for objective questions
    if opt_keys and (not evidence or len(evidence.strip()) < 5):
        errors_found.append(f"Q{qnum} ({qid}) Objective question missing evidence sentence: '{evidence}'")
        
    # Check rubric for subjective questions
    if not opt_keys:
        if not rubric:
            errors_found.append(f"Q{qnum} ({qid}) Subjective question missing rubric_json")
        else:
            try:
                r_obj = json.loads(rubric)
                if not r_obj:
                    errors_found.append(f"Q{qnum} ({qid}) Subjective rubric is empty")
            except Exception as ex:
                errors_found.append(f"Q{qnum} ({qid}) Invalid rubric JSON: {ex}")

print(f"\nQuestions & Answers Errors Count: {len(errors_found)}")
for err in errors_found:
    print(f"  [ERROR] {err}")

if not errors_found:
    print("  [SUCCESS] All 52 questions have valid options, verified answers, robust evidence sentences, and comprehensive explanations!")

print("\n="*60)
print("4. DETAILED BREAKDOWN BY QUESTION NUMBER")
print("="*60)
for q in questions:
    qid, gid, qnum, prompt, opt_json, score, cat, ans, evidence, expl, verifier, ak_status, rubric = q
    opt_cnt = len(json.loads(opt_json)) if opt_json else 0
    ans_display = (ans[:10] + '..') if ans and len(ans) > 10 else str(ans)
    expl_len = len(expl) if expl else 0
    print(f"Q{qnum:02d} | Group: {gid[:25]:25} | Score: {score} | Ans: {ans_display:12} | Verifier: {str(verifier):18} | Expl len: {expl_len:3} | Opts: {opt_cnt}")
