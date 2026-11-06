import io
import csv
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db, utc_now
from app.models.vocabulary import WordDict, UserVocabulary, VocabularyOccurrence, ReviewLog
from app.models.user import LearningProfile
from app.schemas.vocabulary import (
    WordLookupResponse, MarkWordRequest, UserVocabularySchema,
    VocabularyOccurrenceSchema, ReviewFeedbackRequest, ReviewFeedbackResponse
)
from app.core.fsrs_scheduler import default_fsrs
from app.core.phrase_dict import lookup_phrase_meaning, detect_phrases_in_sentence

router = APIRouter(prefix="/vocabulary", tags=["Vocabulary"])

@router.get("/lookup", response_model=WordLookupResponse)
def lookup_word(
    word: str = Query(..., description="English word or phrase to lookup"),
    sentence: str = Query(None, description="Context sentence for smart phrase detection"),
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    clean_w = " ".join(word.strip().lower().split())
    entry = db.query(WordDict).filter(WordDict.word == clean_w).first()
    
    # 检查用户是否已添加过此词或短语
    saved = db.query(UserVocabulary).filter(
        UserVocabulary.user_id == user_id,
        UserVocabulary.word == clean_w
    ).first()

    # 扫描语境中的考研高频核心短语
    detected = detect_phrases_in_sentence(sentence, target_word=clean_w) if sentence else []

    if entry:
        return WordLookupResponse(
            word=entry.word,
            phonetic=entry.phonetic,
            meaning=entry.meaning,
            is_saved=bool(saved),
            detected_phrases=detected
        )

    # 考研核心短语与固定搭配检测
    phrase_meaning = lookup_phrase_meaning(clean_w)
    if phrase_meaning:
        return WordLookupResponse(
            word=clean_w,
            phonetic="[短语搭配]",
            meaning=phrase_meaning,
            is_saved=bool(saved),
            detected_phrases=detected
        )

    # 短语：逐词智能拆解语义合成 (例如 curious treasure -> curious + treasure)
    is_phrase = " " in clean_w or "-" in clean_w
    if is_phrase:
        sub_words = [w for w in clean_w.replace("-", " ").split() if w]
        sub_meanings = []
        for sw in sub_words:
            w_item = db.query(WordDict).filter(WordDict.word == sw).first()
            if w_item and w_item.meaning:
                first_m = w_item.meaning.split(";")[0].split("；")[0].split("\n")[0].strip()
                sub_meanings.append(f"{sw} ({first_m})")
        if sub_meanings:
            synthesized = " [词意构成] " + " + ".join(sub_meanings)
            return WordLookupResponse(
                word=clean_w,
                phonetic="[核心短语]",
                meaning=f"真题重点搭配：{synthesized}",
                is_saved=bool(saved),
                detected_phrases=detected
            )

    return WordLookupResponse(
        word=clean_w,
        phonetic="[核心短语]" if is_phrase else None,
        meaning="考研真题重点短语搭配 (支持自定释义与真题原句复习)" if is_phrase else "真题核心词汇 (可通过上下文推测语义)",
        is_saved=bool(saved),
        detected_phrases=detected
    )

@router.post("/mark", response_model=UserVocabularySchema)
def mark_new_word(data: MarkWordRequest, db: Session = Depends(get_db)):
    """
    PRD 9.2 & 9.4 (AT-06 & AT-07):
    阅读与选项中点击单词或划词短语立即保存，不依赖试卷提交。
    保存真题例句、来源出处。同一单词/短语多次出现自动归并，累加语境，不造成词条泛滥。
    """
    clean_w = " ".join(data.word.strip().lower().split())
    if not clean_w:
        raise HTTPException(status_code=400, detail="Word or phrase cannot be empty")

    dict_entry = db.query(WordDict).filter(WordDict.word == clean_w).first()
    phrase_meaning = lookup_phrase_meaning(clean_w) if not dict_entry else None
    
    phonetic = dict_entry.phonetic if dict_entry else ("[短语搭配]" if (" " in clean_w or phrase_meaning) else None)
    default_def = data.definition or (dict_entry.meaning if dict_entry else (phrase_meaning or ("真题短语" if " " in clean_w else "真题生词")))

    existing_vocab = db.query(UserVocabulary).filter(
        UserVocabulary.user_id == data.user_id,
        UserVocabulary.word == clean_w
    ).first()

    now = utc_now()

    if existing_vocab:
        # AT-07: 累加语境，词条去重归并
        existing_vocab.occurrence_count += 1
        occ = VocabularyOccurrence(
            id=str(uuid.uuid4()),
            user_vocab_id=existing_vocab.id,
            context_sentence=data.context_sentence,
            source_info=data.source_info,
            group_id=data.group_id,
            marked_at=now
        )
        db.add(occ)
        target_vocab = existing_vocab
    else:
        # AT-06: 创建生词/短语卡片并初始化 FSRS 状态
        vocab_id = str(uuid.uuid4())
        new_vocab = UserVocabulary(
            id=vocab_id,
            user_id=data.user_id,
            word=clean_w,
            phonetic=phonetic,
            definition=default_def,
            occurrence_count=1,
            stability=0.0,
            difficulty=0.0,
            reps=0,
            lapses=0,
            state=0,  # New
            due_date=now,  # 立即进入待复习队列
            created_at=now
        )
        db.add(new_vocab)

        occ = VocabularyOccurrence(
            id=str(uuid.uuid4()),
            user_vocab_id=vocab_id,
            context_sentence=data.context_sentence,
            source_info=data.source_info,
            group_id=data.group_id,
            marked_at=now
        )
        db.add(occ)
        target_vocab = new_vocab

        # 档案计数加 1
        profile = db.query(LearningProfile).filter(LearningProfile.user_id == data.user_id).first()
        today_str = utc_now().strftime("%Y-%m-%d")
        if profile:
            profile.total_vocabulary_marked += 1
        else:
            profile = LearningProfile(
                id=str(uuid.uuid4()),
                user_id=data.user_id,
                total_time_seconds=0,
                total_questions_attempted=0,
                total_questions_correct=0,
                overall_accuracy=0.0,
                total_vocabulary_marked=1,
                total_reviews_completed=0,
                consecutive_study_days=1,
                last_active_date=today_str
            )
            db.add(profile)

    db.commit()
    db.refresh(target_vocab)

    # 组装返回
    occs = [
        VocabularyOccurrenceSchema(
            context_sentence=o.context_sentence,
            source_info=o.source_info,
            group_id=o.group_id,
            marked_at=o.marked_at
        )
        for o in target_vocab.occurrences
    ]

    return UserVocabularySchema(
        id=target_vocab.id,
        word=target_vocab.word,
        phonetic=target_vocab.phonetic,
        definition=target_vocab.definition,
        occurrence_count=target_vocab.occurrence_count,
        stability=target_vocab.stability,
        difficulty=target_vocab.difficulty,
        reps=target_vocab.reps,
        lapses=target_vocab.lapses,
        state=target_vocab.state,
        due_date=target_vocab.due_date,
        last_review=target_vocab.last_review,
        occurrences=occs
    )

@router.delete("/unmark")
def unmark_word(
    word: str = Query(..., description="Word or phrase to unmark"),
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    取消生词或短语的标记，移除其 FSRS 记录并撤销马克笔高亮
    """
    clean_w = " ".join(word.strip().lower().split())
    vocab = db.query(UserVocabulary).filter(
        UserVocabulary.user_id == user_id,
        UserVocabulary.word == clean_w
    ).first()
    if not vocab:
        return {"status": "not_found", "word": clean_w}

    db.delete(vocab)
    profile = db.query(LearningProfile).filter(LearningProfile.user_id == user_id).first()
    if profile and profile.total_vocabulary_marked > 0:
        profile.total_vocabulary_marked -= 1
    db.commit()
    return {"status": "unmarked", "word": clean_w}

@router.get("/list", response_model=list[UserVocabularySchema])
def list_user_vocabulary(user_id: str = "default_user", db: Session = Depends(get_db)):
    vocabs = db.query(UserVocabulary).filter(UserVocabulary.user_id == user_id).order_by(UserVocabulary.created_at.desc()).all()
    results = []
    for v in vocabs:
        occs = [
            VocabularyOccurrenceSchema(
                context_sentence=o.context_sentence,
                source_info=o.source_info,
                group_id=o.group_id,
                marked_at=o.marked_at
            )
            for o in v.occurrences
        ]
        results.append(UserVocabularySchema(
            id=v.id,
            word=v.word,
            phonetic=v.phonetic,
            definition=v.definition,
            occurrence_count=v.occurrence_count,
            stability=v.stability,
            difficulty=v.difficulty,
            reps=v.reps,
            lapses=v.lapses,
            state=v.state,
            due_date=v.due_date,
            last_review=v.last_review,
            occurrences=occs
        ))
    return results

@router.get("/review-queue", response_model=list[UserVocabularySchema])
def get_review_queue(user_id: str = "default_user", db: Session = Depends(get_db)):
    """
    获取今日到期需复习的 FSRS 卡片队列
    """
    now = utc_now()
    vocabs = db.query(UserVocabulary).filter(
        UserVocabulary.user_id == user_id,
        UserVocabulary.due_date <= now
    ).order_by(UserVocabulary.due_date.asc()).limit(50).all()

    # 如果到期的少于 10 个，补充新词
    if len(vocabs) < 10:
        new_vocabs = db.query(UserVocabulary).filter(
            UserVocabulary.user_id == user_id,
            UserVocabulary.reps == 0,
            UserVocabulary.id.notin_([v.id for v in vocabs])
        ).limit(10 - len(vocabs)).all()
        vocabs.extend(new_vocabs)

    results = []
    for v in vocabs:
        occs = [
            VocabularyOccurrenceSchema(
                context_sentence=o.context_sentence,
                source_info=o.source_info,
                group_id=o.group_id,
                marked_at=o.marked_at
            )
            for o in v.occurrences
        ]
        results.append(UserVocabularySchema(
            id=v.id,
            word=v.word,
            phonetic=v.phonetic,
            definition=v.definition,
            occurrence_count=v.occurrence_count,
            stability=v.stability,
            difficulty=v.difficulty,
            reps=v.reps,
            lapses=v.lapses,
            state=v.state,
            due_date=v.due_date,
            last_review=v.last_review,
            occurrences=occs
        ))
    return results

@router.post("/feedback", response_model=ReviewFeedbackResponse)
def review_feedback(data: ReviewFeedbackRequest, db: Session = Depends(get_db)):
    """
    PRD 9.3 & AT-08:
    基于 FSRS 四档反馈 (1=忘记, 2=困难, 3=记得, 4=轻松) 计算下一次复习时间。
    生成不可篡改的 ReviewLog 记录。
    """
    vocab = db.query(UserVocabulary).filter(UserVocabulary.id == data.vocab_id).first()
    if not vocab:
        raise HTTPException(status_code=404, detail="Vocabulary item not found")

    if data.rating not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Rating must be 1, 2, 3, or 4")

    now = utc_now()
    res = default_fsrs.review(
        rating=data.rating,
        last_stability=vocab.stability or 0.0,
        last_difficulty=vocab.difficulty or 0.0,
        last_review_date=vocab.last_review,
        now=now
    )

    # 记录复习日志
    log_entry = ReviewLog(
        id=str(uuid.uuid4()),
        user_vocab_id=vocab.id,
        rating=data.rating,
        stability_before=vocab.stability or 0.0,
        stability_after=res["stability"],
        difficulty_before=vocab.difficulty or 0.0,
        difficulty_after=res["difficulty"],
        interval_days=res["interval_days"],
        reviewed_at=now
    )
    db.add(log_entry)

    # 更新词卡状态
    vocab.stability = res["stability"]
    vocab.difficulty = res["difficulty"]
    vocab.state = res["state"]
    vocab.due_date = res["due_date"]
    vocab.last_review = now
    vocab.reps += 1
    if data.rating == 1:
        vocab.lapses += 1

    # 更新个人学习档案 Profile
    profile = db.query(LearningProfile).filter(LearningProfile.user_id == data.user_id).first()
    if profile:
        profile.total_reviews_completed += 1

    db.commit()

    return ReviewFeedbackResponse(
        vocab_id=vocab.id,
        rating=data.rating,
        new_stability=res["stability"],
        new_difficulty=res["difficulty"],
        interval_days=res["interval_days"],
        next_due_date=res["due_date"],
        new_state=res["state"]
    )

@router.get("/export")
def export_vocabulary(
    user_id: str = "default_user",
    format: str = Query("json", description="Export format: json, csv, or anki"),
    db: Session = Depends(get_db)
):
    """
    PRD 12.3: 生词本数据便携导出
    支持 JSON、UTF-8 CSV 以及 Anki 制表符分隔文本 (TSV)
    """
    vocabs = db.query(UserVocabulary).filter(UserVocabulary.user_id == user_id).all()
    
    records = []
    for v in vocabs:
        first_occ = v.occurrences[0] if v.occurrences else None
        records.append({
            "word": v.word,
            "phonetic": v.phonetic or "",
            "definition": v.definition,
            "occurrence_count": v.occurrence_count,
            "stability": round(v.stability or 0.0, 2),
            "difficulty": round(v.difficulty or 0.0, 2),
            "reps": v.reps,
            "lapses": v.lapses,
            "context_sentence": first_occ.context_sentence if first_occ else "",
            "source_info": first_occ.source_info if first_occ else ""
        })

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "word", "phonetic", "definition", "occurrence_count", "stability",
            "difficulty", "reps", "lapses", "context_sentence", "source_info"
        ])
        writer.writeheader()
        writer.writerows(records)
        content = "\ufeff" + output.getvalue()  # Add UTF-8 BOM for Excel compatibility
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=kaoyan_vocabulary.csv"}
        )

    elif format == "anki":
        # Anki TSV: Word \t Phonetic \t Definition \t Context Sentence \t Source
        lines = []
        for r in records:
            ph = f"[{r['phonetic']}]" if r['phonetic'] else ""
            sent = r['context_sentence'].replace("\t", " ").replace("\n", " ")
            src = r['source_info'].replace("\t", " ")
            lines.append(f"{r['word']}\t{ph}\t{r['definition']}\t{sent}\t{src}")
        content = "\n".join(lines)
        return Response(
            content=content,
            media_type="text/tab-separated-values; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=kaoyan_anki_deck.txt"}
        )

    else:
        # Default JSON
        content = json.dumps(records, ensure_ascii=False, indent=2)
        return Response(
            content=content,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=kaoyan_vocabulary.json"}
        )
