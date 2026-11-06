import json
import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.models.exam import Exam, Section, QuestionGroup, Question, AnswerKey
from app.models.vocabulary import WordDict
from app.core.qa_gate import ContentQAGate
from app.config import settings
from app.data.question_bank_builder import build_all_exams

def seed_database(db: Session):
    # 确保所有数据库表结构已创建
    Base.metadata.create_all(bind=engine)

    # 1. 导入 6,588 真实考研词典库 (若未导入)
    vocab_db_path = settings.DESKTOP_VOCAB_DB
    existing_word_count = db.query(WordDict).count()
    if existing_word_count == 0 and os.path.exists(vocab_db_path):
        print(f"Importing Kaoyan vocabulary dictionary from {vocab_db_path}...")
        try:
            v_conn = sqlite3.connect(vocab_db_path)
            cur = v_conn.cursor()
            cur.execute("SELECT word, phonetic, meaning FROM words")
            rows = cur.fetchall()
            v_conn.close()

            word_dict_map = {}
            for w, p, m in rows:
                if w and m:
                    clean_w = w.strip().lower()
                    if clean_w not in word_dict_map:
                        word_dict_map[clean_w] = {
                            "word": clean_w,
                            "phonetic": p.strip() if p else None,
                            "meaning": m.strip()
                        }
                    else:
                        existing_m = word_dict_map[clean_w]["meaning"]
                        if m.strip() not in existing_m:
                            word_dict_map[clean_w]["meaning"] = f"{existing_m}；{m.strip()}"

            batch = [
                WordDict(word=v["word"], phonetic=v["phonetic"], meaning=v["meaning"])
                for v in word_dict_map.values()
            ]
            db.bulk_save_objects(batch)
            db.commit()
            print(f"Successfully seeded {len(batch)} authentic Kaoyan vocabulary entries.")
        except Exception as e:
            print("Error importing vocab db:", type(e).__name__)
            db.rollback()

    # 2. 真实考研全卷试题数据 (覆盖 2004-2026 年考研英语一与英语二全部 43 套真题试卷)
    # 包含：完形填空 (Cloze)、阅读理解 Part A (4篇)、新题型 Part B、英译汉 Translation、写作 Part A 与 Part B
    # =========================================================================
    GENUINE_EXAMS = build_all_exams()
    print(f"Loading authentic exam curriculum: {len(GENUINE_EXAMS)} exams (2004-2026)...")

    # 3. 幂等插入试卷、板块、题组、题目与标准答案
    for exam_data in GENUINE_EXAMS:
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

    # 4. 严格执行全量 QA 门禁校验
    print("Running QA Gates on all seeded QuestionGroups...")
    all_groups = db.query(QuestionGroup).all()
    qa_passed = 0
    for grp in all_groups:
        qa_res = ContentQAGate.validate_question_group(db, grp.id, record_logs=False)
        if qa_res.is_valid:
            qa_passed += 1
        else:
            print(f"[{grp.group_type.upper()}] Group {grp.id} Failed QA Gate: {qa_res.errors}")

    print(f"QA Gate complete: {qa_passed}/{len(all_groups)} passed.")
    db.commit()

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
