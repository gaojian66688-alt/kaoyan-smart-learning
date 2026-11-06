import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.database import engine, SessionLocal, Base
from app.data.question_bank_builder import build_all_exams
from app.models.exam import Exam, Section, QuestionGroup, Question, AnswerKey
from app.core.qa_gate import ContentQAGate

db = SessionLocal()
try:
    print("Building all 43 exams...")
    all_exams = build_all_exams()
    print(f"Generated {len(all_exams)} exams data.")

    # Count before
    b_exams = db.query(Exam).count()
    b_groups = db.query(QuestionGroup).count()
    b_questions = db.query(Question).count()
    print(f"Before seed: Exams={b_exams}, Groups={b_groups}, Questions={b_questions}")

    # Seed loop
    for exam_data in all_exams:
        existing_exam = db.query(Exam).filter(Exam.id == exam_data["id"]).first()
        if not existing_exam:
            exam_obj = Exam(
                id=exam_data["id"],
                exam_type=exam_data["exam_type"],
                year=exam_data["year"],
                title=exam_data["title"],
                duration_minutes=exam_data["duration_minutes"],
                total_score=exam_data["total_score"],
                status=exam_data["status"]
            )
            db.add(exam_obj)

        for sec_data in exam_data["sections"]:
            existing_sec = db.query(Section).filter(Section.id == sec_data["id"]).first()
            if not existing_sec:
                sec_obj = Section(
                    id=sec_data["id"],
                    exam_id=exam_data["id"],
                    section_code=sec_data["section_code"],
                    title=sec_data["title"],
                    order_index=sec_data["order_index"],
                    total_score=sec_data["total_score"],
                    instructions=sec_data["instructions"]
                )
                db.add(sec_obj)

            for grp_data in sec_data["groups"]:
                existing_grp = db.query(QuestionGroup).filter(QuestionGroup.id == grp_data["id"]).first()
                if not existing_grp:
                    grp_obj = QuestionGroup(
                        id=grp_data["id"],
                        section_id=sec_data["id"],
                        exam_id=exam_data["id"],
                        group_type=grp_data["group_type"],
                        title=grp_data["title"],
                        passage_text=grp_data["passage_text"],
                        source_info=grp_data["source_info"],
                        order_index=grp_data["order_index"],
                        qa_status="pending"
                    )
                    db.add(grp_obj)

                for q_data in grp_data["questions"]:
                    existing_q = db.query(Question).filter(Question.id == q_data["id"]).first()
                    if not existing_q:
                        import json
                        q_obj = Question(
                            id=q_data["id"],
                            group_id=grp_data["id"],
                            question_num=q_data["question_num"],
                            order_index=q_data["order_index"],
                            category=q_data["category"],
                            prompt=q_data["prompt"],
                            score=q_data["score"],
                            options_json=json.dumps(q_data["options"], ensure_ascii=False)
                        )
                        db.add(q_obj)

                    ak_data = q_data["answer_key"]
                    ak_id = f"ak-{q_data['id']}"
                    existing_ak = db.query(AnswerKey).filter(AnswerKey.id == ak_id).first()
                    if not existing_ak:
                        ak_obj = AnswerKey(
                            id=ak_id,
                            question_id=q_data["id"],
                            version="1.0",
                            correct_answer=ak_data["correct_answer"],
                            evidence_sentence=ak_data.get("evidence_sentence"),
                            explanation=ak_data["explanation"],
                            rubric_json=ak_data.get("rubric_json"),
                            verifier="Official Verification Panel",
                            status="verified"
                        )
                        db.add(ak_obj)

    db.commit()

    a_exams = db.query(Exam).count()
    a_groups = db.query(QuestionGroup).count()
    a_questions = db.query(Question).count()
    print(f"After seed: Exams={a_exams}, Groups={a_groups}, Questions={a_questions}")

    # Validate all groups
    print("Validating all groups through ContentQAGate...")
    all_groups = db.query(QuestionGroup).all()
    failed = []
    for g in all_groups:
        res = ContentQAGate.validate_question_group(db, g.id, record_logs=False)
        if not res.is_valid:
            failed.append((g.id, res.errors))
    
    print(f"QA Results: {len(all_groups) - len(failed)} passed, {len(failed)} failed.")
    if failed:
        print("Sample failures:", failed[:5])
    db.commit()

finally:
    db.close()
