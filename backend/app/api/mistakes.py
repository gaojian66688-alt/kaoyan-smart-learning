import json
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db, utc_now
from app.models.mistake import Mistake
from app.models.exam import Question, QuestionGroup, AnswerKey
from app.models.vocabulary import UserVocabulary

router = APIRouter(prefix="/mistakes", tags=["Mistakes"])

def generate_syntax_breakdown(sentence: str) -> str:
    """
    长难句语法结构拆分：自动标注主句、引导词与从句层次
    """
    if not sentence or len(sentence.strip()) < 15:
        return ""
    
    # 查找常见的从句引导词
    markers = ["that", "which", "who", "whom", "where", "when", "while", "although", "because", "since", "if", "unless"]
    found_markers = [m for m in markers if f" {m} " in f" {sentence.lower()} "]
    
    if found_markers:
        return f"【句式结构】复合长难句；包含引导词 [{', '.join(found_markers)}] 构成的从属结构。建议先剥离修饰从句，抓住主干‘主-谓-宾’核心意群。"
    else:
        return "【句式结构】简单句扩展；包含多重介词短语修饰语或非谓语动词结构，定位时注意限定词边界。"

@router.get("")
def list_mistakes(user_id: str = "default_user", db: Session = Depends(get_db)):
    """
    PRD 10.1 & 二.4: 错题本列表
    完整呈现所属原题材料上下文、题干、选项、用户作答、标准答案、长难句结构剖析与词汇盲区诊断。
    """
    mistakes = db.query(Mistake).filter(Mistake.user_id == user_id).order_by(Mistake.last_wrong_at.desc()).all()
    results = []

    # 获取用户所有已标记生词
    user_words = {
        v.word.lower() for v in db.query(UserVocabulary.word).filter(UserVocabulary.user_id == user_id).all()
    }

    for m in mistakes:
        q = db.query(Question).filter(Question.id == m.question_id).first()
        grp = db.query(QuestionGroup).filter(QuestionGroup.id == m.group_id).first()
        ak = db.query(AnswerKey).filter(AnswerKey.question_id == m.question_id, AnswerKey.status == "verified").first()

        evidence = ak.evidence_sentence if ak else ""
        syntax = m.syntax_analysis or generate_syntax_breakdown(evidence)

        # 检查定位句中的词汇盲区
        words_in_ev = [w.strip(".,;:?!\"'()").lower() for w in evidence.split()]
        detected_gaps = [w for w in set(words_in_ev) if w in user_words]

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
            "evidence_sentence": evidence,
            "syntax_analysis": syntax,
            "detected_vocabulary_gaps": detected_gaps,
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

@router.get("/export")
def export_mistakes(
    user_id: str = "default_user",
    format: str = Query("markdown", description="Export format: markdown or json"),
    db: Session = Depends(get_db)
):
    """
    PRD 12.3: 错题本数据导出 (Markdown / JSON)
    保留完整题干、选项、你的作答、官方标准答案、定位句与长难句语法剖析
    """
    mistakes = db.query(Mistake).filter(Mistake.user_id == user_id).order_by(Mistake.last_wrong_at.desc()).all()
    
    items = []
    for m in mistakes:
        q = db.query(Question).filter(Question.id == m.question_id).first()
        grp = db.query(QuestionGroup).filter(QuestionGroup.id == m.group_id).first()
        ak = db.query(AnswerKey).filter(AnswerKey.question_id == m.question_id, AnswerKey.status == "verified").first()
        evidence = ak.evidence_sentence if ak else ""
        syntax = m.syntax_analysis or generate_syntax_breakdown(evidence)

        items.append({
            "question_num": q.question_num if q else 0,
            "group_title": grp.title if grp else "",
            "exam_id": grp.exam_id if grp else "",
            "prompt": q.prompt if q else "",
            "options": q.get_options() if q else [],
            "last_user_answer": m.last_user_answer,
            "correct_answer": m.correct_answer,
            "evidence_sentence": evidence,
            "syntax_analysis": syntax,
            "explanation": ak.explanation if ak else "",
            "wrong_count": m.wrong_count,
            "user_reason_tag": m.user_reason_tag or "未标记",
            "is_mastered": m.is_mastered
        })

    if format == "json":
        content = json.dumps(items, ensure_ascii=False, indent=2)
        return Response(
            content=content,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=kaoyan_mistakes.json"}
        )
    else:
        # Markdown export
        md_lines = [
            "# 考研英语智能学习平台 —— 个人真题错题档案",
            f"\n> 导出用户: `{user_id}` | 错题总数: {len(items)} 道 | 导出时间: {utc_now().strftime('%Y-%m-%d %H:%M')}\n",
            "---\n"
        ]
        for idx, it in enumerate(items, 1):
            opts_str = "\n".join([f"  - `{opt['key']}`: {opt['text']}" for opt in it['options']])
            status_tag = "✅ 已掌握" if it['is_mastered'] else "⚠️ 待巩固"
            md_lines.append(f"## {idx}. [{it['exam_id']} {it['group_title']}] 第 {it['question_num']} 题 ({status_tag})")
            md_lines.append(f"**题干**: {it['prompt']}\n")
            if opts_str:
                md_lines.append(f"**选项**:\n{opts_str}\n")
            md_lines.append(f"- **你的作答**: `{it['last_user_answer']}`")
            md_lines.append(f"- **标准答案**: `{it['correct_answer']}`")
            md_lines.append(f"- **错题频次**: {it['wrong_count']} 次 | **归因分类**: {it['user_reason_tag']}")
            if it['evidence_sentence']:
                md_lines.append(f"\n> **原文定位句**:\n> \"{it['evidence_sentence']}\"")
            if it['syntax_analysis']:
                md_lines.append(f"\n**语法句式拆分**: {it['syntax_analysis']}")
            if it['explanation']:
                md_lines.append(f"\n**题目官方解析**: {it['explanation']}")
            md_lines.append("\n---\n")

        content = "\n".join(md_lines)
        return Response(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=kaoyan_mistakes.md"}
        )
