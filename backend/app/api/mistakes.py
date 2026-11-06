import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.mistake import Mistake
from app.models.exam import Question, QuestionGroup, AnswerKey

router = APIRouter(prefix="/mistakes", tags=["Mistakes"])

@router.get("")
def list_mistakes(user_id: str = "default_user", db: Session = Depends(get_db)):
    """
    PRD 10.1: 错题本列表
    完整呈现所属原题材料上下文、题干、选项、用户作答、标准答案及错因标记。
    """
    mistakes = db.query(Mistake).filter(Mistake.user_id == user_id).order_by(Mistake.last_wrong_at.desc()).all()
    results = []

    for m in mistakes:
        q = db.query(Question).filter(Question.id == m.question_id).first()
        grp = db.query(QuestionGroup).filter(QuestionGroup.id == m.group_id).first()
        ak = db.query(AnswerKey).filter(AnswerKey.question_id == m.question_id, AnswerKey.status == "verified").first()

        results.append({
            "id": m.id,
            "question_id": m.question_id,
            "group_id": m.group_id,
            "group_title": grp.title if grp else "",
            "passage_text": grp.passage_text if grp else "",
            "question_num": q.question_num if q else 0,
            "prompt": q.prompt if q else "",
            "options": q.get_options() if q else [],
            "last_user_answer": m.last_user_answer,
            "correct_answer": m.correct_answer,
            "explanation": ak.explanation if ak else "",
            "evidence_sentence": ak.evidence_sentence if ak else "",
            "wrong_count": m.wrong_count,
            "user_reason_tag": m.user_reason_tag,
            "is_mastered": m.is_mastered,
            "first_wrong_at": m.first_wrong_at,
            "last_wrong_at": m.last_wrong_at
        })

    return results

@router.post("/{mistake_id}/tag")
def update_mistake_tag(
    mistake_id: str,
    tag: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    PRD 10.1: 用户主动标记真实错因标签
    (如: 词汇盲区 / 长难句语法偏差 / 偷换概念 / 反向推导 / 粗心看错)
    """
    m = db.query(Mistake).filter(Mistake.id == mistake_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mistake item not found")

    m.user_reason_tag = tag.strip()
    db.commit()
    return {"status": "ok", "mistake_id": m.id, "user_reason_tag": m.user_reason_tag}

@router.post("/{mistake_id}/toggle-mastery")
def toggle_mastery(mistake_id: str, db: Session = Depends(get_db)):
    m = db.query(Mistake).filter(Mistake.id == mistake_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mistake item not found")

    m.is_mastered = not m.is_mastered
    db.commit()
    return {"status": "ok", "mistake_id": m.id, "is_mastered": m.is_mastered}
