import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.exam import Exam, Section, QuestionGroup, Question
from app.schemas.exam import ExamSchema, QuestionGroupDetailSchema, QuestionSchema, OptionItem

router = APIRouter(prefix="/exams", tags=["Exams"])

@router.get("", response_model=list[ExamSchema])
def list_exams(db: Session = Depends(get_db)):
    exams = db.query(Exam).order_by(Exam.year.desc()).all()
    results = []
    for ex in exams:
        sec_list = []
        for sec in ex.sections:
            grp_summaries = []
            for grp in sec.question_groups:
                q_count = db.query(Question).filter(Question.group_id == grp.id).count()
                grp_summaries.append({
                    "id": grp.id,
                    "section_id": grp.section_id,
                    "exam_id": grp.exam_id,
                    "group_type": grp.group_type,
                    "title": grp.title,
                    "order_index": grp.order_index,
                    "qa_status": grp.qa_status,
                    "question_count": q_count
                })
            sec_list.append({
                "id": sec.id,
                "exam_id": sec.exam_id,
                "section_code": sec.section_code,
                "title": sec.title,
                "order_index": sec.order_index,
                "total_score": sec.total_score,
                "instructions": sec.instructions,
                "question_groups": grp_summaries
            })
        results.append({
            "id": ex.id,
            "exam_type": ex.exam_type,
            "year": ex.year,
            "title": ex.title,
            "duration_minutes": ex.duration_minutes,
            "total_score": ex.total_score,
            "status": ex.status,
            "sections": sec_list
        })
    return results

@router.get("/group/{group_id}", response_model=QuestionGroupDetailSchema)
def get_question_group(group_id: str, db: Session = Depends(get_db)):
    """
    PRD 5.2: 获取最小完整作答单元
    保证包含完整 Text、题干和全部选项，顺序与原卷完全一致。
    """
    group = db.query(QuestionGroup).filter(QuestionGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Question group not found")

    questions = db.query(Question).filter(Question.group_id == group_id).order_by(Question.order_index).all()
    q_schemas = []
    for q in questions:
        raw_options = q.get_options()
        opt_items = [OptionItem(key=o["key"], text=o["text"]) for o in raw_options]
        q_schemas.append(QuestionSchema(
            id=q.id,
            group_id=q.group_id,
            question_num=q.question_num,
            prompt=q.prompt,
            options=opt_items,
            score=q.score,
            order_index=q.order_index,
            category=q.category or "detail"
        ))

    return QuestionGroupDetailSchema(
        id=group.id,
        section_id=group.section_id,
        exam_id=group.exam_id,
        group_type=group.group_type,
        title=group.title,
        passage_text=group.passage_text,
        source_info=group.source_info,
        order_index=group.order_index,
        qa_status=group.qa_status,
        questions=q_schemas
    )
