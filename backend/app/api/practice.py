import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.practice import Attempt, Response, Submission, GradeResult
from app.schemas.practice import (
    AttemptCreate, AttemptResponse, BatchResponseSave,
    SubmitRequest, SubmissionResponse, GradeResultSchema
)
from app.core.grading_engine import GradingEngine

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

router = APIRouter(prefix="/practice", tags=["Practice"])

@router.post("/attempt", response_model=AttemptResponse)
def create_or_resume_attempt(data: AttemptCreate, db: Session = Depends(get_db)):
    """
    创建或恢复作答会话。
    如果存在同用户、同目标且仍在作答中 (in_progress) 的会话，自动恢复，避免丢失未提交内容 (PRD 7.3)。
    """
    # P0 真实性检查：未经过真实来源核验的题目和下线试卷不得进入正式练习
    if data.target_type == "group":
        from app.models.exam import QuestionGroup
        grp = db.query(QuestionGroup).filter(QuestionGroup.id == data.target_id).first()
        if not grp or grp.qa_status != "verified":
            raise HTTPException(
                status_code=403,
                detail="该单元未经过真实来源核验 (Pending)，严禁开始作答！"
            )
    elif data.target_type == "exam":
        from app.models.exam import Exam
        ex = db.query(Exam).filter(Exam.id == data.target_id).first()
        if not ex or ex.status != "published":
            raise HTTPException(
                status_code=403,
                detail="该试卷无法证明真实性或未完成全量核验，已暂时下线，禁止进入练习！"
            )

    existing = db.query(Attempt).filter(
        Attempt.user_id == data.user_id,
        Attempt.target_id == data.target_id,
        Attempt.mode == data.mode,
        Attempt.status == "in_progress"
    ).order_by(Attempt.created_at.desc()).first()

    if existing:
        saved = db.query(Response).filter(Response.attempt_id == existing.id).all()
        saved_dict = {r.question_id: r.user_answer for r in saved if r.user_answer}
        return AttemptResponse(
            id=existing.id,
            mode=existing.mode,
            target_type=existing.target_type,
            target_id=existing.target_id,
            status=existing.status,
            time_spent_seconds=existing.time_spent_seconds or 0,
            created_at=existing.created_at,
            saved_responses=saved_dict
        )

    attempt_id = str(uuid.uuid4())
    attempt = Attempt(
        id=attempt_id,
        user_id=data.user_id,
        mode=data.mode,
        target_type=data.target_type,
        target_id=data.target_id,
        status="in_progress",
        time_spent_seconds=0
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return AttemptResponse(
        id=attempt.id,
        mode=attempt.mode,
        target_type=attempt.target_type,
        target_id=attempt.target_id,
        status=attempt.status,
        time_spent_seconds=0,
        created_at=attempt.created_at,
        saved_responses={}
    )

@router.post("/save")
def auto_save_responses(data: BatchResponseSave, db: Session = Depends(get_db)):
    """
    PRD 7.3: 作答中实时自动保存
    不泄露答案，不执行判分，保证异常退出后可平滑恢复。
    """
    attempt = db.query(Attempt).filter(Attempt.id == data.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail="Cannot edit answers for an already submitted attempt")

    if data.time_spent_seconds is not None:
        attempt.time_spent_seconds = data.time_spent_seconds

    for item in data.responses:
        resp = db.query(Response).filter(
            Response.attempt_id == data.attempt_id,
            Response.question_id == item.question_id
        ).first()

        clean_ans = item.user_answer.strip() if item.user_answer else None

        if resp:
            if resp.is_final_snapshot:
                # 已随单篇/板块批改锁定的答案快照不可篡改 (PRD P1 规则 1)
                continue
            resp.user_answer = clean_ans
            resp.updated_at = utc_now()
        else:
            new_resp = Response(
                id=str(uuid.uuid4()),
                attempt_id=data.attempt_id,
                question_id=item.question_id,
                user_answer=clean_ans,
                is_final_snapshot=False
            )
            db.add(new_resp)

    db.commit()
    return {"status": "saved", "count": len(data.responses)}

@router.post("/submit", response_model=SubmissionResponse)
def submit_attempt(data: SubmitRequest, db: Session = Depends(get_db)):
    """
    PRD G04 & 7.2: 用户主动触发批改
    支持单篇 (group)、板块 (section) 和整卷 (exam) 批改。
    严格模考模式下拦截单篇批改 (AT-05)。
    """
    attempt = db.query(Attempt).filter(Attempt.id == data.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # AT-05 校验：严格模考只能交整卷
    if attempt.mode == "strict_mock" and data.scope != "exam":
        raise HTTPException(
            status_code=403,
            detail="严格模考模式下屏蔽单篇及板块批改，仅允许整卷交卷！"
        )

    try:
        submission = GradingEngine.grade_attempt(
            db=db,
            attempt_id=data.attempt_id,
            scope=data.scope,
            scope_id=data.scope_id,
            answer_key_version="1.0",
            user_id=data.user_id or "default_user"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    grade_results = db.query(GradeResult).filter(GradeResult.submission_id == submission.id).all()
    res_list = [
        GradeResultSchema(
            question_id=gr.question_id,
            question_num=gr.question_num,
            user_answer=gr.user_answer,
            correct_answer=gr.correct_answer,
            is_correct=gr.is_correct,
            is_estimated=bool(gr.is_estimated),
            score_band=gr.score_band,
            score=gr.score,
            max_score=gr.max_score,
            evidence_sentence=gr.evidence_sentence,
            explanation=gr.explanation,
            category=gr.category
        )
        for gr in grade_results
    ]

    return SubmissionResponse(
        id=submission.id,
        attempt_id=submission.attempt_id,
        scope=submission.scope,
        scope_id=submission.scope_id,
        total_score=submission.total_score,
        max_score=submission.max_score,
        objective_score=submission.objective_score or 0.0,
        subjective_score=submission.subjective_score or 0.0,
        accuracy=submission.accuracy,
        question_count=submission.question_count,
        correct_count=submission.correct_count,
        submitted_at=submission.submitted_at,
        results=res_list
    )

@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
def get_submission(submission_id: str, db: Session = Depends(get_db)):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    grade_results = db.query(GradeResult).filter(GradeResult.submission_id == submission_id).all()
    res_list = [
        GradeResultSchema(
            question_id=gr.question_id,
            question_num=gr.question_num,
            user_answer=gr.user_answer,
            correct_answer=gr.correct_answer,
            is_correct=gr.is_correct,
            is_estimated=bool(gr.is_estimated),
            score_band=gr.score_band,
            score=gr.score,
            max_score=gr.max_score,
            evidence_sentence=gr.evidence_sentence,
            explanation=gr.explanation,
            category=gr.category
        )
        for gr in grade_results
    ]

    return SubmissionResponse(
        id=sub.id,
        attempt_id=sub.attempt_id,
        scope=sub.scope,
        scope_id=sub.scope_id,
        total_score=sub.total_score,
        max_score=sub.max_score,
        objective_score=sub.objective_score or 0.0,
        subjective_score=sub.subjective_score or 0.0,
        accuracy=sub.accuracy,
        question_count=sub.question_count,
        correct_count=sub.correct_count,
        submitted_at=sub.submitted_at,
        results=res_list
    )
