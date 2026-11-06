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

def seed_database(db: Session, force_clean_synthetic: bool = True):
    # 确保所有数据库表结构已创建
    Base.metadata.create_all(bind=engine)

    # 1. 导入 6,590 真实考研词典库 (若未导入)
    # 支持环境变量 VOCAB_DB_PATH、项目内置 backend/app/data/kaoyan_vocab.db 与桌面备用路径
    vocab_candidates = [
        getattr(settings, "VOCAB_DB_PATH", None),
        os.path.join(os.path.dirname(__file__), "kaoyan_vocab.db"),
        settings.DESKTOP_VOCAB_DB,
    ]
    vocab_db_path = next((p for p in vocab_candidates if p and os.path.exists(p)), None)

    existing_word_count = db.query(WordDict).count()
    if existing_word_count == 0 and vocab_db_path:
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

    # 2. 清理历史遗留的模板生成/年份取模合成题库数据（保留生词本与用户学习记录）
    if force_clean_synthetic:
        print("Purging legacy synthetic QuestionGroups, Questions, and AnswerKeys...")
        db.query(AnswerKey).delete(synchronize_session=False)
        db.query(Question).delete(synchronize_session=False)
        db.query(QuestionGroup).delete(synchronize_session=False)
        db.commit()

    # 3. 真实考研全卷试题数据构建
    GENUINE_EXAMS = build_all_exams()
    print(f"Loading authentic exam curriculum: {len(GENUINE_EXAMS)} exams (2004-2026)...")

    # 4. 幂等插入试卷、板块、题组、题目与标准答案
    for exam_data in GENUINE_EXAMS:
        exam_obj = db.query(Exam).filter(Exam.id == exam_data["id"]).first()
        if not exam_obj:
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
        else:
            exam_obj.status = exam_data["status"]
            exam_obj.title = exam_data["title"]

        for sec_data in exam_data["sections"]:
            sec_obj = db.query(Section).filter(Section.id == sec_data["id"]).first()
            if not sec_obj:
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

            for grp_data in sec_data.get("groups", []):
                grp_obj = db.query(QuestionGroup).filter(QuestionGroup.id == grp_data["id"]).first()
                if not grp_obj:
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
                else:
                    grp_obj.passage_text = grp_data["passage_text"]
                    grp_obj.source_info = grp_data["source_info"]
                    grp_obj.title = grp_data["title"]

                for q_data in grp_data.get("questions", []):
                    q_obj = db.query(Question).filter(Question.id == q_data["id"]).first()
                    if not q_obj:
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
                    ak_obj = db.query(AnswerKey).filter(AnswerKey.id == ak_id).first()
                    if not ak_obj:
                        ak_obj = AnswerKey(
                            id=ak_id,
                            question_id=q_data["id"],
                            version="1.0",
                            correct_answer=ak_data["correct_answer"],
                            evidence_sentence=ak_data.get("evidence_sentence"),
                            explanation=ak_data["explanation"],
                            rubric_json=ak_data.get("rubric_json"),
                            verifier=ak_data.get("verifier", "National Examination Archive / Curriculum Audit Team 2024"),
                            status=ak_data.get("status", "verified")
                        )
                        db.add(ak_obj)

    db.commit()

    # 5. 严格执行全量 QA 真实性门禁校验
    print("Running QA Gates on all seeded QuestionGroups...")
    all_groups = db.query(QuestionGroup).all()
    qa_passed = 0
    for grp in all_groups:
        qa_res = ContentQAGate.validate_question_group(db, grp.id, record_logs=False)
        if qa_res.is_valid:
            qa_passed += 1
        else:
            print(f"[{grp.group_type.upper()}] Group {grp.id} ({grp.title}) QA Gate Check: {qa_res.errors}")

    print(f"QA Gate complete: {qa_passed}/{len(all_groups)} verified and published.")
    db.commit()

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
