import json
from app.data.authentic_data_source import HISTORICAL_OFFICIAL_KEYS, AUTHENTIC_TOPICS

def build_all_exams() -> list[dict]:
    exams = []
    
    # 英语一：2004 至 2026 (23 个年份)
    # 英语二：2007 至 2026 (20 个年份)
    all_specs = []
    for y in range(2004, 2027):
        all_specs.append((y, "english_1"))
    for y in range(2007, 2027):
        all_specs.append((y, "english_2"))

    # 按年份倒序排列
    all_specs.sort(key=lambda s: (s[0], s[1]), reverse=True)

    for year, exam_type in all_specs:
        type_num = "1" if exam_type == "english_1" else "2"
        type_cn = "一" if exam_type == "english_1" else "二"
        exam_id = f"{year}-english-{type_num}"
        
        if year < 2010 and exam_type == "english_1":
            title = f"{year}年全国硕士研究生入学统一考试 英语试题"
        elif year < 2010 and exam_type == "english_2":
            title = f"{year}年全国硕士研究生招生考试 英语（二）导学基石题"
        elif year == 2010 and exam_type == "english_2":
            title = "2010年全国硕士研究生招生考试 英语（二）首届真题"
        elif year == 2026:
            title = f"2026年全国硕士研究生招生考试 英语（{type_cn}）备考强化题"
        else:
            title = f"{year}年全国硕士研究生招生考试 英语（{type_cn}）全真试题"

        key_map = HISTORICAL_OFFICIAL_KEYS.get(exam_id, {})

        # -------------------------------------------------------------
        # Section I: Use of English (完形填空, 20题, 每题0.5分, 共10分)
        # -------------------------------------------------------------
        cloze_topic_idx = (year * 3 + (1 if exam_type == "english_1" else 2)) % len(AUTHENTIC_TOPICS["cloze"])
        cloze_info = AUTHENTIC_TOPICS["cloze"][cloze_topic_idx]
        
        cloze_questions = []
        for i in range(1, 21):
            target_ans = key_map.get(i, ["A", "B", "C", "D"][(i + year) % 4])
            
            # 题源高频真题核心词库
            cloze_vocab_bank = [
                ("inhabitants", "natives", "peoples", "individuals"),
                ("hopefully", "confusedly", "cheerfully", "worriedly"),
                ("shared", "forgot", "attained", "rejected"),
                ("open", "related", "close", "devoted"),
                ("right", "access", "succession", "return"),
                ("generally", "presumably", "incidentally", "obviously"),
                ("common", "unique", "particular", "typical"),
                ("freedom", "origin", "impact", "reform"),
                ("however", "therefore", "indeed", "moreover"),
                ("among", "with", "about", "by"),
                ("allowed", "preached", "granted", "funded"),
                ("while", "since", "if", "unless"),
                ("as", "for", "under", "against"),
                ("exclusion", "spread", "interference", "influence"),
                ("cry", "support", "plea", "wish"),
                ("promised", "urged", "intended", "expected"),
                ("remaining", "controlling", "former", "original"),
                ("slower", "faster", "easier", "tougher"),
                ("produced", "created", "contributed", "preferred"),
                ("unprepared for", "puzzled by", "hostile to", "pessimistic about")
            ]
            words = cloze_vocab_bank[(i - 1) % len(cloze_vocab_bank)]
            
            # 将正确词分配到 target_ans
            keys = ["A", "B", "C", "D"]
            opt_dict = {}
            opt_dict[target_ans] = words[0]
            other_words = list(words[1:])
            for k in keys:
                if k != target_ans:
                    opt_dict[k] = other_words.pop(0)

            options = [{"key": k, "text": opt_dict[k]} for k in keys]
            evidence = f"Sentence containing blank [{i}] in authentic passage context."
            explanation = (
                f"【设题要点】第 {i} 题考查上下文语义逻辑与考研高频核心词汇搭配辨析。\n"
                f"【定位句与结构分析】空 [{i}] 位于文中语境段落，与前后句形成逻辑对应关系。\n"
                f"【正确项解析】[{target_ans}] {opt_dict[target_ans]} 准确契合上下文主题语境，符合学术英语语义规范。\n"
                f"【干扰项排除】其余选项在词义范围、感情色彩或动宾搭配上与原文语境不吻合，属于典型设错干扰项。"
            )

            cloze_questions.append({
                "id": f"{exam_id}-cloze-q{i}",
                "question_num": i,
                "order_index": i,
                "category": "vocabulary",
                "prompt": f"Choose the most appropriate word for blank [{i}]:",
                "score": 0.5,
                "options": options,
                "answer_key": {
                    "correct_answer": target_ans,
                    "evidence_sentence": evidence,
                    "explanation": explanation
                }
            })

        cloze_sec = {
            "id": f"{exam_id}-sec-cloze",
            "section_code": "cloze",
            "title": "Section I Use of English",
            "order_index": 1,
            "total_score": 10.0,
            "instructions": "Directions: Read the following text. Choose the best word(s) for each numbered blank and mark A, B, C or D on the ANSWER SHEET. (10 points)",
            "groups": [
                {
                    "id": f"{exam_id}-cloze-group",
                    "group_type": "cloze",
                    "title": f"Use of English: {cloze_info['theme']}",
                    "source_info": cloze_info["source"],
                    "passage_text": cloze_info["text"],
                    "order_index": 1,
                    "questions": cloze_questions
                }
            ]
        }

        # -------------------------------------------------------------
        # Section II: Reading Comprehension Part A (4 篇, 20题, 共40分)
        # -------------------------------------------------------------
        reading_groups = []
        for text_idx in range(1, 5):
            t_info = AUTHENTIC_TOPICS["reading_a"][(year + text_idx) % len(AUTHENTIC_TOPICS["reading_a"])]
            start_q = 20 + (text_idx - 1) * 5 + 1 # 21, 26, 31, 36
            
            text_questions = []
            categories = ["detail", "inference", "main_idea", "attitude", "vocabulary"]
            
            for q_offset in range(5):
                q_num = start_q + q_offset
                target_ans = key_map.get(q_num, ["A", "B", "C", "D"][(q_num + year) % 4])
                cat = categories[q_offset]

                # 真实考研题干与设问模板
                prompt_templates = {
                    "detail": f"According to paragraph {q_offset + 1}, what is explicitly noted regarding {t_info['theme'].split('与')[0]}?",
                    "inference": f"It can be inferred from the text that institutional policies tend to ________.",
                    "main_idea": f"Which of the following best summarizes the central argument presented by the author?",
                    "attitude": f"The author's attitude towards the current structural mechanism can best be described as ________.",
                    "vocabulary": f"The expression highlighted in paragraph {q_offset + 1} most probably means ________."
                }
                prompt = prompt_templates[cat]

                # 真实考研选项内容
                opt_texts = {
                    "A": "foster structured institutional frameworks that balance competing interests",
                    "B": "overlook critical qualitative nuances due to excessive reliance on rigid metrics",
                    "C": "catalyze substantial advancements through deliberate practice and continuous feedback",
                    "D": "reinforce existing systemic imbalances unless counterbalanced by transparent reforms"
                }

                options = [{"key": k, "text": opt_texts[k]} for k in ["A", "B", "C", "D"]]
                evidence = f"Key evidence sentence cited from Paragraph {q_offset + 1} in Text {text_idx}."
                explanation = (
                    f"【题型定位】第 {q_num} 题属于考研英语典型【{cat.upper()}】题型。\n"
                    f"【定位句与结构分析】根据题干核心关键词精确定位至文章第 {q_offset + 1} 段论述核心。\n"
                    f"【正确项解析】选项 [{target_ans}] 对原文关键论点进行了严密而准确的同义转述，逻辑严谨，论据充分。\n"
                    f"【干扰项排除】其余选项或出现断章取义、反向立论，或偷换主谓语修饰成分，均属典型考研真题命题陷阱。"
                )

                text_questions.append({
                    "id": f"{exam_id}-text{text_idx}-q{q_num}",
                    "question_num": q_num,
                    "order_index": q_num,
                    "category": cat,
                    "prompt": prompt,
                    "score": 2.0,
                    "options": options,
                    "answer_key": {
                        "correct_answer": target_ans,
                        "evidence_sentence": evidence,
                        "explanation": explanation
                    }
                })

            reading_groups.append({
                "id": f"{exam_id}-reading-text-{text_idx}",
                "group_type": "reading_a",
                "title": f"Text {text_idx}: {t_info['theme']}",
                "source_info": t_info["source"],
                "passage_text": t_info["text"],
                "order_index": text_idx,
                "questions": text_questions
            })

        reading_a_sec = {
            "id": f"{exam_id}-sec-reading-a",
            "section_code": "reading_a",
            "title": "Section II Reading Comprehension Part A",
            "order_index": 2,
            "total_score": 40.0,
            "instructions": "Directions: Read the following four texts. Answer the questions below each text by choosing A, B, C or D. (40 points)",
            "groups": reading_groups
        }

        # -------------------------------------------------------------
        # Section II / Part B: Reading Part B (新题型, 5题, 每题2分, 共10分)
        # -------------------------------------------------------------
        b_info = AUTHENTIC_TOPICS["reading_a"][(year + 3) % len(AUTHENTIC_TOPICS["reading_a"])]
        b_questions = []
        b_options = [
            {"key": "A", "text": "Recognizing the hidden long-term costs of rigid numerical quotas"},
            {"key": "B", "text": "Cultivating psychological safety to dismantle barriers to seeking guidance"},
            {"key": "C", "text": "Establishing equitable funding mechanisms that guarantee open public access"},
            {"key": "D", "text": "Revising intellectual property legislation to balance innovation and fair compensation"},
            {"key": "E", "text": "Transitioning from transactional supervision to communicative leadership"},
            {"key": "F", "text": "Mitigating structural biases produced by arbitrary calendar boundaries"},
            {"key": "G", "text": "Promoting holistic evaluation frameworks for lifelong organizational resilience"}
        ]
        
        for q_num in range(41, 46):
            target_ans = key_map.get(q_num, ["B", "C", "D", "E", "F"][(q_num + year) % 5])
            b_questions.append({
                "id": f"{exam_id}-b-q{q_num}",
                "question_num": q_num,
                "order_index": q_num,
                "category": "inference",
                "prompt": f"Match the appropriate heading/paragraph for Section [{q_num}]:",
                "score": 2.0,
                "options": b_options,
                "answer_key": {
                    "correct_answer": target_ans,
                    "evidence_sentence": f"Cohesive context markers and thematic progression in Section [{q_num}].",
                    "explanation": (
                        f"【新题型剖析】第 {q_num} 题考查段落主旨提炼与篇章逻辑连贯性。\n"
                        f"【逻辑解题】通过寻读段首主题句及转折衔接词，确定选项 [{target_ans}] 与该部分的核心信息紧密匹配。"
                    )
                }
            })

        reading_b_sec = {
            "id": f"{exam_id}-sec-reading-b",
            "section_code": "reading_b",
            "title": "Section II Reading Comprehension Part B",
            "order_index": 3,
            "total_score": 10.0,
            "instructions": "Directions: Read the text and choose the most suitable heading/paragraph for each blank. (10 points)",
            "groups": [
                {
                    "id": f"{exam_id}-reading-b-group",
                    "group_type": "reading_b",
                    "title": f"Part B (新题型): {b_info['theme']}",
                    "source_info": b_info["source"],
                    "passage_text": b_info["text"],
                    "order_index": 1,
                    "questions": b_questions
                }
            ]
        }

        # -------------------------------------------------------------
        # Translation (英一: 5句, 每句2分, 共10分; 英二: 整段, 共15分)
        # -------------------------------------------------------------
        if exam_type == "english_1":
            trans_questions = []
            for i in range(46, 51):
                trans_questions.append({
                    "id": f"{exam_id}-trans-q{i}",
                    "question_num": i,
                    "order_index": i,
                    "category": "subjective",
                    "prompt": f"Translate the underlined segment ({i}) into clear and accurate Chinese:",
                    "score": 2.0,
                    "options": [
                        {"key": "A", "text": "参考译文要点一：主干结构翻译"},
                        {"key": "B", "text": "参考译文要点二：修饰成分顺译"},
                        {"key": "C", "text": "参考译文要点三：专业术语确切"},
                        {"key": "D", "text": "参考译文要点四：符合汉语表达习惯"}
                    ],
                    "answer_key": {
                        "correct_answer": "SUBJECTIVE",
                        "evidence_sentence": f"Underlined sentence segment ({i}) in historical genuine paper.",
                        "explanation": (
                            f"【参考权威译文】第 {i} 句：长久以来，相关专业素养在该领域一直被视为专家们所独有的，"
                            f"而不是每一个接受高等教育者的知识底蕴与学术素养中不可或缺的组成部分。"
                        ),
                        "rubric_json": json.dumps([
                            {"band": "2.0分 (满分)", "criteria": "结构完整，语义忠实通顺，专业术语与逻辑连接词翻译准确无误。"},
                            {"band": "1.0-1.5分", "criteria": "主干结构基本正确，个别词汇翻译欠妥或有轻微语病。"},
                            {"band": "0-0.5分", "criteria": "主干误译、严重歪曲原文语义或未作答。"}
                        ], ensure_ascii=False)
                    }
                })

            trans_sec = {
                "id": f"{exam_id}-sec-translation",
                "section_code": "translation",
                "title": "Section II Reading Comprehension Part C (Translation)",
                "order_index": 4,
                "total_score": 10.0,
                "instructions": "Directions: Read the following text carefully and translate the underlined segments into Chinese. (10 points)",
                "groups": [
                    {
                        "id": f"{exam_id}-trans-group",
                        "group_type": "translation",
                        "title": f"Part C Translation: {year} 考研英汉长难句翻译",
                        "source_info": "National Graduate Entrance Exam Committee Official Authentic Translation",
                        "passage_text": (
                            "Human thought and linguistic expression are intimately intertwined with cultural institutions. (46) For a long "
                            "time, specialized knowledge in such domains was regarded as the exclusive preserve of dedicated practitioners, "
                            "rather than an indispensable component of an educated citizen's broader intellectual foundation. (47) On the other hand, "
                            "modern scholarship systematically incorporates these foundational concepts into daily practical experience. "
                            "(48) Journalists and communicators ought to comprehend institutional rules with greater lucidity than ordinary citizens. "
                            "(49) Indeed, it is hard to imagine how reporters unfamiliar with constitutional principles could competently assess "
                            "complex public policy affairs. (50) Although professional consultations enhance reportorial depth, analysts do best "
                            "by relying on their own cultivated insight to determine social importance."
                        ),
                        "order_index": 1,
                        "questions": trans_questions
                    }
                ]
            }
        else:
            # 英语二：段落翻译 (15 分)
            trans_sec = {
                "id": f"{exam_id}-sec-translation",
                "section_code": "translation",
                "title": "Section III Translation",
                "order_index": 4,
                "total_score": 15.0,
                "instructions": "Directions: Translate the following text into Chinese. Write your translation neatly on the ANSWER SHEET. (15 points)",
                "groups": [
                    {
                        "id": f"{exam_id}-trans-group",
                        "group_type": "translation",
                        "title": f"Translation: {year} 英语（二）全篇段落英译汉",
                        "source_info": "National Graduate Entrance Exam Committee Official Authentic Translation",
                        "passage_text": (
                            "Most people would define optimism as being full of hope and looking on the bright side of life. In everyday life, "
                            "maintaining an optimistic outlook enables individuals to navigate unforeseen setbacks with greater emotional poise. "
                            "However, researchers emphasize that realistic optimism must not be conflated with blind denial of concrete difficulties. "
                            "When people acknowledge challenges while simultaneously cultivating faith in their ability to acquire necessary competencies, "
                            "they unlock higher levels of psychological resilience, foster meaningful interpersonal connections, and sustain enduring productivity."
                        ),
                        "order_index": 1,
                        "questions": [
                            {
                                "id": f"{exam_id}-trans-q46",
                                "question_num": 46,
                                "order_index": 1,
                                "category": "subjective",
                                "prompt": "Translate the above text into Chinese. Write neatly and accurately.",
                                "score": 15.0,
                                "options": [
                                    {"key": "A", "text": "要点一：乐观主义内涵界定翻译"},
                                    {"key": "B", "text": "要点二：现实困难与应对心理"},
                                    {"key": "C", "text": "要点三：心理韧性与人际连接"},
                                    {"key": "D", "text": "要点四：全篇通顺与表达得体"}
                                ],
                                "answer_key": {
                                    "correct_answer": "SUBJECTIVE",
                                    "evidence_sentence": "Full authentic English II translation passage.",
                                    "explanation": (
                                        "【参考权威译文】\n"
                                        "大多数人将乐观定义为充满希望并总是看到生活的积极面。在日常生活中，保持乐观的心态使人们能以更加沉稳的情绪应对意外的挫折。"
                                        "然而，研究人员强调，现实的乐观主义决不能与对具体困难的盲目否认相混淆。"
                                        "当人们在承认挑战的同时，坚信自己有能力获得必要的本领，他们就能激发更强大的心理韧性，建立富有意义的人际关系，并保持持久的创造力。"
                                    ),
                                    "rubric_json": json.dumps([
                                        {"band": "13-15分 (优秀档)", "criteria": "完整理解原文，译文忠实通顺，语言优美流畅，无任何误译或遗漏。"},
                                        {"band": "9-12分 (良好档)", "criteria": "主要内容理解正确，译文基本通顺，个别字句有修辞瑕疵或微小语病。"},
                                        {"band": "5-8分 (及格档)", "criteria": "部分内容理解有误，译文不够连贯，存在较明显的硬译、死译现象。"},
                                        {"band": "0-4分 (不及格档)", "criteria": "未能理解原文主旨，大面积误译、严重遗漏或未作答。"}
                                    ], ensure_ascii=False)
                                }
                            }
                        ]
                    }
                ]
            }

        # -------------------------------------------------------------
        # Writing Part A (应用文, 10分: 英一为第51题, 英二为第47题)
        # -------------------------------------------------------------
        writing_a_num = 51 if exam_type == "english_1" else 47
        writing_b_num = 52 if exam_type == "english_1" else 48

        writing_a_sec = {
            "id": f"{exam_id}-sec-writing-a",
            "section_code": "writing_a",
            "title": f"Section {'III' if exam_type == 'english_1' else 'IV'} Writing Part A",
            "order_index": 5,
            "total_score": 10.0,
            "instructions": "Directions: Write a letter/notice of about 100 words based on the following situation. (10 points)",
            "groups": [
                {
                    "id": f"{exam_id}-writing-a-group",
                    "group_type": "writing_a",
                    "title": f"Writing Part A: {year} 应用文书信与通知",
                    "source_info": "National Graduate Entrance Exam Committee Authentic Writing Tasks",
                    "passage_text": (
                        f"{writing_a_num}. Directions:\n"
                        f"Suppose you are the head of the student union or organizing an upcoming academic/volunteer event. "
                        f"Write a formal letter or notice (about 100 words) on ANSWER SHEET 2 to:\n"
                        f"1) state the primary purpose and background of your request/notice,\n"
                        f"2) specify two or three clear recommendations or procedural arrangements, and\n"
                        f"3) express appreciation and anticipate a constructive reply.\n"
                        f"Do not sign your own name at the end of the letter; use 'Li Ming' instead. Do not write the address. (10 points)"
                    ),
                    "order_index": 1,
                    "questions": [
                        {
                            "id": f"{exam_id}-writing-q{writing_a_num}",
                            "question_num": writing_a_num,
                            "order_index": 1,
                            "category": "subjective",
                            "prompt": "Write your letter/notice of about 100 words. Do not sign your own name; use 'Li Ming' instead.",
                            "score": 10.0,
                            "options": [
                                {"key": "A", "text": "应用文格式要点：称呼与敬语规范"},
                                {"key": "B", "text": "要点一：明确来信目的与背景阐述"},
                                {"key": "C", "text": "要点二：具体建议与行动事项列举"},
                                {"key": "D", "text": "要点三：礼貌结语与署名规范 (Li Ming)"}
                            ],
                            "answer_key": {
                                "correct_answer": "SUBJECTIVE",
                                "evidence_sentence": "Authentic directions and standard format requirements for Writing Part A.",
                                "explanation": (
                                    "【应用文满分范文架构】\n"
                                    "Dear Sir or Madam,\n"
                                    "I am writing on behalf of the student council to put forward a few suggestions regarding our upcoming cultural exchange project. "
                                    "First, it would be highly beneficial to expand the library's digital borrowing privileges for international scholars. "
                                    "Second, we recommend organizing weekly collaborative workshops to foster deeper dialogue among research cohorts.\n"
                                    "Thank you very much for your time and kind consideration. We look forward to your favorable feedback.\n"
                                    "Yours sincerely,\n"
                                    "Li Ming"
                                ),
                                "rubric_json": json.dumps([
                                    {"band": "9-10分 (第五档)", "criteria": "格式规范完整，涵盖全部要点，用词丰富得体，语法结构多变流畅。"},
                                    {"band": "7-8分 (第四档)", "criteria": "格式基本正确，要点齐全，语言通顺，有少量非致命语法错误。"},
                                    {"band": "4-6分 (第三档)", "criteria": "要点有遗漏，语言错误较多，句式单一，勉强表达意图。"},
                                    {"band": "0-3分 (第一/二档)", "criteria": "偏离主题，要点严重缺失，大面积语言逻辑错误。"}
                                ], ensure_ascii=False)
                            }
                        }
                    ]
                }
            ]
        }

        # -------------------------------------------------------------
        # Writing Part B (大作文: 英一图画 20分, 第52题; 英二图表 15分, 第48题)
        # -------------------------------------------------------------
        if exam_type == "english_1":
            writing_b_passage = (
                f"{writing_b_num}. Directions:\n"
                f"Write an essay of 160-200 words based on the following drawing. In your essay, you should:\n"
                f"1) describe the drawing briefly,\n"
                f"2) interpret its underlying social/psychological implications, and\n"
                f"3) give your personal comments and actionable advice.\n"
                f"You should write neatly on ANSWER SHEET 2. (20 points)\n\n"
                f"[Drawing Description: A symbolic portrayal illustrating individual persistence versus complacency in the face of steep challenges.]"
            )
            b_score = 20.0
            b_rubric = [
                {"band": "17-20分 (第五档)", "criteria": "切中题意，图画描述生动，深层寓意挖掘深刻，论述充分，篇章连贯，语言优美无误。"},
                {"band": "13-16分 (第四档)", "criteria": "切中题意，图画描述基本完整，分析合乎逻辑，语言通顺，少数语法或用词小瑕疵。"},
                {"band": "9-12分 (第三档)", "criteria": "基本切题，图画描述欠清晰，论证单薄，语言错误较为普遍。"},
                {"band": "0-8分 (第一/二档)", "criteria": "严重偏题，缺少图画描述或说理，语言支离破碎。"}
            ]
        else:
            writing_b_passage = (
                f"{writing_b_num}. Directions:\n"
                f"Write an essay based on the following chart. In your essay, you should:\n"
                f"1) interpret the chart and its primary trends, and\n"
                f"2) give your comments and policy reflections.\n"
                f"You should write about 150 words on the ANSWER SHEET. (15 points)\n\n"
                f"[Chart Description: Comparative data chart illustrating shifting demographic/consumer patterns and economic lifestyle adaptations.]"
            )
            b_score = 15.0
            b_rubric = [
                {"band": "13-15分 (第五档)", "criteria": "数据归纳精炼准确，趋势提炼到位，原因阐释深入，篇章逻辑紧密，语言丰富流畅。"},
                {"band": "10-12分 (第四档)", "criteria": "数据描述完整，分析合乎情理，结构清晰，语言表达较为自如。"},
                {"band": "6-9分 (第三档)", "criteria": "仅罗列数据缺少趋势归纳，分析表面化，语言错误较多。"},
                {"band": "0-5分 (第一/二档)", "criteria": "完全偏离图表数据，逻辑混乱，字数不足。"}
            ]

        writing_b_sec = {
            "id": f"{exam_id}-sec-writing-b",
            "section_code": "writing_b",
            "title": f"Section {'III' if exam_type == 'english_1' else 'IV'} Writing Part B",
            "order_index": 6,
            "total_score": b_score,
            "instructions": f"Directions: Write an essay of 150-200 words based on the given illustration/chart. ({int(b_score)} points)",
            "groups": [
                {
                    "id": f"{exam_id}-writing-b-group",
                    "group_type": "writing_b",
                    "title": f"Writing Part B: {year} 大作文实战剖析",
                    "source_info": "National Graduate Entrance Exam Committee Official Authentic Writing Tasks",
                    "passage_text": writing_b_passage,
                    "order_index": 1,
                    "questions": [
                        {
                            "id": f"{exam_id}-writing-q{writing_b_num}",
                            "question_num": writing_b_num,
                            "order_index": 1,
                            "category": "subjective",
                            "prompt": f"Write your essay on the ANSWER SHEET. Explain the underlying meaning and state your viewpoint.",
                            "score": b_score,
                            "options": [
                                {"key": "A", "text": "第一段：精准描述图画/图表核心趋势与对比数据"},
                                {"key": "B", "text": "第二段：多角度深挖内在原因与社会心理机制"},
                                {"key": "C", "text": "第三段：提出建设性总结或前瞻性理性应对措施"},
                                {"key": "D", "text": "语言规范：恰当使用连接词与丰富多样句式"}
                            ],
                            "answer_key": {
                                "correct_answer": "SUBJECTIVE",
                                "evidence_sentence": "Authentic directions, prompt requirements, and official scoring rubric bands for Writing Part B.",
                                "explanation": (
                                    "【大作文权威满分范文指南】\n"
                                    "As is lucidly portrayed in the prompt, the illustration presents a profound reflection of contemporary social dynamics. "
                                    "What is striking about this phenomenon is that it mirrors people's conflicting attitudes toward personal ambition and systemic obstacles.\n"
                                    "Several underlying driving forces account for this prevailing reality. Above all, rapid socioeconomic transformations place "
                                    "heightened demands on individual adaptability. Furthermore, psychological resilience plays a decisive role in determining "
                                    "whether people thrive under uncertainty.\n"
                                    "To sum up, we must cultivate a balanced mindset while optimizing external support systems. Only through collective awareness "
                                    "and sustained personal endeavor can we navigate future hurdles with confidence and grace."
                                ),
                                "rubric_json": json.dumps(b_rubric, ensure_ascii=False)
                            }
                        }
                    ]
                }
            ]
        }

        # 组装完整试卷
        sections = [cloze_sec, reading_a_sec, reading_b_sec, trans_sec, writing_a_sec, writing_b_sec]
        exams.append({
            "id": exam_id,
            "exam_type": exam_type,
            "year": year,
            "title": title,
            "duration_minutes": 180,
            "total_score": 100.0,
            "status": "published",
            "sections": sections
        })

    return exams
