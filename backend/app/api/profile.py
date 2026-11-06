from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db, utc_now
from app.models.user import LearningProfile
from app.models.vocabulary import UserVocabulary, ReviewLog
from app.models.mistake import Mistake
from app.models.exam import QuestionGroup, Question
from app.models.practice import Attempt, GradeResult, Submission
from app.schemas.profile import (
    LearningProfileSchema, TodayPlanSchema, ProfileTrendsSchema,
    CategoryStatItem, DailyTrendItem, VocabDistributionSchema
)

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
            last_active_date=utc_now().strftime("%Y-%m-%d")
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
    now = utc_now()
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

@router.get("/trends", response_model=ProfileTrendsSchema)
def get_profile_trends(user_id: str = "default_user", db: Session = Depends(get_db)):
    """
    PRD 10.2 & 11: 历史学习趋势、题型正确率分布与 FSRS 记忆掌握度
    """
    profile = db.query(LearningProfile).filter(LearningProfile.user_id == user_id).first()
    overall_acc = profile.overall_accuracy if profile else 0.0

    # 1. 题型正确率统计
    category_labels = {
        "detail": "细节事实题",
        "inference": "推理判断题",
        "main_idea": "主旨大意题",
        "vocabulary": "词义语义题",
        "subjective": "主观翻译写作"
    }
    
    # 查询所有已批改的 GradeResult
    grades = (
        db.query(GradeResult)
        .join(Submission, GradeResult.submission_id == Submission.id)
        .join(Attempt, Submission.attempt_id == Attempt.id)
        .filter(Attempt.user_id == user_id)
        .all()
    )

    cat_counts = {k: {"total": 0, "correct": 0} for k in category_labels}
    for g in grades:
        c_key = g.category if g.category in cat_counts else "detail"
        cat_counts[c_key]["total"] += 1
        if g.is_correct or (g.score and g.score >= 1.0):
            cat_counts[c_key]["correct"] += 1

    category_stat_items = []
    weak_points = []
    strengths = []
    for c_key, c_name in category_labels.items():
        tot = cat_counts[c_key]["total"]
        cor = cat_counts[c_key]["correct"]
        acc = round((cor / tot) * 100.0, 1) if tot > 0 else 0.0
        category_stat_items.append(CategoryStatItem(
            category=c_key,
            category_name=c_name,
            total=tot,
            correct=cor,
            accuracy=acc
        ))
        if tot >= 3:
            if acc < 60.0:
                weak_points.append(f"{c_name}正确率偏低（{acc}%，{cor}/{tot}题），建议加强该题型的解题策略与定位训练。")
            elif acc >= 80.0:
                strengths.append(f"{c_name}掌握扎实（正确率 {acc}%，{cor}/{tot}题），状态良好。")

    if not weak_points:
        weak_points.append("暂未发现显著薄弱题型，继续完成更多篇章以获得更精准的薄弱点画像。")
    if not strengths:
        strengths.append("保持日常连续作答，随着题量积累将自动沉淀各项高分优势。")

    # 2. 每日作答趋势 (近 7 次/天)
    submissions = (
        db.query(Submission)
        .join(Attempt, Submission.attempt_id == Attempt.id)
        .filter(Attempt.user_id == user_id)
        .order_by(Submission.submitted_at.desc())
        .limit(10)
        .all()
    )
    daily_map = {}
    for sub in reversed(submissions):
        d_str = sub.submitted_at.strftime("%m-%d")
        if d_str not in daily_map:
            daily_map[d_str] = {"attempted": 0, "correct": 0}
        daily_map[d_str]["attempted"] += 1
        if sub.accuracy >= 60.0:
            daily_map[d_str]["correct"] += 1

    daily_trend_items = [
        DailyTrendItem(
            date=d,
            attempted=val["attempted"],
            correct=val["correct"],
            accuracy=round((val["correct"] / val["attempted"]) * 100.0, 1) if val["attempted"] > 0 else 0.0
        )
        for d, val in daily_map.items()
    ]
    if not daily_trend_items:
        today_s = utc_now().strftime("%m-%d")
        daily_trend_items.append(DailyTrendItem(date=today_s, attempted=0, correct=0, accuracy=0.0))

    # 3. 词汇掌握状态分布
    all_user_vocabs = db.query(UserVocabulary).filter(UserVocabulary.user_id == user_id).all()
    v_total = len(all_user_vocabs)
    v_new = 0
    v_learn = 0
    v_rev = 0
    v_relearn = 0
    v_mastered = 0

    for v in all_user_vocabs:
        if (v.reps or 0) >= 3 and (v.stability or 0.0) >= 5.0:
            v_mastered += 1
        elif v.state == 0:
            v_new += 1
        elif v.state == 1:
            v_learn += 1
        elif v.state == 2:
            v_rev += 1
        elif v.state == 3:
            v_relearn += 1
        else:
            v_learn += 1

    vocab_dist = VocabDistributionSchema(
        new_words=v_new,
        learning=v_learn,
        review=v_rev,
        relearning=v_relearn,
        mastered=v_mastered,
        total=v_total
    )

    # 4. FSRS 复习留存率 (rating >= 3)
    user_vocab_ids = [v.id for v in all_user_vocabs]
    if user_vocab_ids:
        all_logs = db.query(ReviewLog).filter(ReviewLog.user_vocab_id.in_(user_vocab_ids)).all()
        if all_logs:
            retained = sum(1 for log in all_logs if log.rating >= 3)
            retention_rate = round((retained / len(all_logs)) * 100.0, 1)
        else:
            retention_rate = 100.0
    else:
        retention_rate = 100.0

    return ProfileTrendsSchema(
        user_id=user_id,
        overall_accuracy=overall_acc,
        retention_rate=retention_rate,
        category_accuracy=category_stat_items,
        daily_trends=daily_trend_items,
        vocab_distribution=vocab_dist,
        weak_points=weak_points,
        strengths=strengths
    )
