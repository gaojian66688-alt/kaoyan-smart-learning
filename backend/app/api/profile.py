from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import LearningProfile
from app.models.vocabulary import UserVocabulary
from app.models.mistake import Mistake
from app.models.exam import QuestionGroup
from app.schemas.profile import LearningProfileSchema, TodayPlanSchema

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("", response_model=LearningProfileSchema)
def get_user_profile(user_id: str = "default_user", db: Session = Depends(get_db)):
    profile = db.query(LearningProfile).filter(LearningProfile.user_id == user_id).first()
    if not profile:
        profile = LearningProfile(
            id=f"profile-{user_id}",
            user_id=user_id,
            total_time_seconds=0,
            total_questions_attempted=0,
            total_questions_correct=0,
            overall_accuracy=0.0,
            total_vocabulary_marked=0,
            total_reviews_completed=0,
            consecutive_study_days=1,
            last_active_date=datetime.utcnow().strftime("%Y-%m-%d")
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile

@router.get("/today-plan", response_model=TodayPlanSchema)
def get_today_learning_plan(user_id: str = "default_user", db: Session = Depends(get_db)):
    """
    PRD 10.3: 今日计划推荐引擎
    优先级：今日到期复习 -> 尚未巩固错题 -> 推荐专项训练阅读篇章
    """
    now = datetime.utcnow()
    due_reviews_count = db.query(UserVocabulary).filter(
        UserVocabulary.user_id == user_id,
        UserVocabulary.due_date <= now
    ).count()

    unconsolidated_mistakes_count = db.query(Mistake).filter(
        Mistake.user_id == user_id,
        Mistake.is_mastered == False
    ).count()

    # 推荐篇章：查找第一个未完成的真题阅读
    sample_group = db.query(QuestionGroup).filter(QuestionGroup.qa_status == "verified").first()
    rec_id = sample_group.id if sample_group else None
    rec_title = f"{sample_group.exam_id} {sample_group.title}" if sample_group else "2024 考研英语（一）Text 1"

    profile = db.query(LearningProfile).filter(LearningProfile.user_id == user_id).first()
    days = profile.consecutive_study_days if profile else 1

    return TodayPlanSchema(
        due_reviews_count=due_reviews_count,
        unconsolidated_mistakes_count=unconsolidated_mistakes_count,
        recommended_reading_group_id=rec_id,
        recommended_reading_title=rec_title,
        consecutive_days=days
    )
