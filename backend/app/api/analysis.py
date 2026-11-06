from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import AIReportRecord
from app.schemas.analysis import AIReportSchema
from app.core.ai_analyzer import EvidenceBasedAIAnalyzer

router = APIRouter(prefix="/analysis", tags=["Analysis"])

@router.post("/generate/{submission_id}", response_model=AIReportSchema)
def generate_ai_report(submission_id: str, user_id: str = "default_user", db: Session = Depends(get_db)):
    """
    PRD 8.2 & 8.3:
    为指定提交生成证据化 AI 学习诊断报告。
    严格区分事实 (选择/答案/标记生词) 与推测 (错因/陷阱假说)。
    """
    try:
        report = EvidenceBasedAIAnalyzer.analyze_submission(db, submission_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AIReportSchema(
        id=report.id,
        submission_id=report.submission_id,
        scope=report.scope,
        summary=report.summary,
        evidence_items=report.get_evidence(),
        recommendations=report.get_recommendations(),
        model_version=report.model_version,
        created_at=report.created_at
    )

@router.get("/submission/{submission_id}", response_model=AIReportSchema)
def get_ai_report_by_submission(submission_id: str, db: Session = Depends(get_db)):
    report = db.query(AIReportRecord).filter(AIReportRecord.submission_id == submission_id).first()
    if not report:
        # 尝试即时生成
        try:
            report = EvidenceBasedAIAnalyzer.analyze_submission(db, submission_id)
        except Exception:
            raise HTTPException(status_code=404, detail="AI report not found for this submission")

    return AIReportSchema(
        id=report.id,
        submission_id=report.submission_id,
        scope=report.scope,
        summary=report.summary,
        evidence_items=report.get_evidence(),
        recommendations=report.get_recommendations(),
        model_version=report.model_version,
        created_at=report.created_at
    )
