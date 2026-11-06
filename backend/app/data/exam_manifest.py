# =========================================================================
# 考研英语 (一) 与 考研英语 (二) 全真历年题库大纲清单 (2004 - 2026)
# 严格按照全国硕士研究生招生考试大纲标准分值与结构配置
# =========================================================================

EN1_YEARS = list(range(2004, 2027)) # 2004 ~ 2026 (23 年)
EN2_YEARS = list(range(2007, 2027)) # 2007 ~ 2026 (20 年)

def get_all_exam_metadata() -> list[dict]:
    exams = []

    # 1. 英语（一）2004-2026 全真历年试卷元数据
    for y in sorted(EN1_YEARS, reverse=True):
        if y < 2010:
            title = f"{y}年全国硕士研究生入学统一考试 英语试题"
        elif y == 2026:
            title = "2026年全国硕士研究生招生考试 英语（一）备考强化试题"
        else:
            title = f"{y}年全国硕士研究生招生考试 英语（一）全真试题"
        
        exams.append({
            "id": f"{y}-english-1",
            "exam_type": "english_1",
            "year": y,
            "title": title,
            "duration_minutes": 180,
            "total_score": 100.0,
            "status": "published",
            "sections": [
                {
                    "section_code": "cloze",
                    "title": "Section I Use of English",
                    "order_index": 1,
                    "total_score": 10.0,
                    "instructions": "Directions: Read the following text. Choose the best word(s) for each numbered blank and mark A, B, C or D on the ANSWER SHEET. (10 points)"
                },
                {
                    "section_code": "reading_a",
                    "title": "Section II Reading Comprehension Part A",
                    "order_index": 2,
                    "total_score": 40.0,
                    "instructions": "Directions: Read the following four texts. Answer the questions below each text by choosing A, B, C or D. Mark your answers on the ANSWER SHEET. (40 points)"
                },
                {
                    "section_code": "reading_b",
                    "title": "Section II Reading Comprehension Part B",
                    "order_index": 3,
                    "total_score": 10.0,
                    "instructions": "Directions: In the following text, some sentences/paragraphs have been removed or need ordering/headings. Choose the most suitable paragraph/heading for each blank. (10 points)"
                },
                {
                    "section_code": "translation",
                    "title": "Section II Reading Comprehension Part C (Translation)",
                    "order_index": 4,
                    "total_score": 10.0,
                    "instructions": "Directions: Read the following text carefully and then translate the underlined segments into Chinese. Your translation should be written neatly on the ANSWER SHEET. (10 points)"
                },
                {
                    "section_code": "writing_a",
                    "title": "Section III Writing Part A",
                    "order_index": 5,
                    "total_score": 10.0,
                    "instructions": "Directions: Write a letter/notice of about 100 words based on the given situation. Do not sign your own name. (10 points)"
                },
                {
                    "section_code": "writing_b",
                    "title": "Section III Writing Part B",
                    "order_index": 6,
                    "total_score": 20.0,
                    "instructions": "Directions: Write an essay of 160-200 words based on the following drawing/chart. Interpret the meaning and express your opinion. (20 points)"
                }
            ]
        })

    # 2. 英语（二）2007-2026 全真历年试卷元数据
    for y in sorted(EN2_YEARS, reverse=True):
        if y < 2010:
            title = f"{y}年全国硕士研究生招生考试 英语（二）导学基石题"
        elif y == 2010:
            title = "2010年全国硕士研究生招生考试 英语（二）首届全真试题"
        elif y == 2026:
            title = "2026年全国硕士研究生招生考试 英语（二）备考强化试题"
        else:
            title = f"{y}年全国硕士研究生招生考试 英语（二）全真试题"

        exams.append({
            "id": f"{y}-english-2",
            "exam_type": "english_2",
            "year": y,
            "title": title,
            "duration_minutes": 180,
            "total_score": 100.0,
            "status": "published",
            "sections": [
                {
                    "section_code": "cloze",
                    "title": "Section I Use of English",
                    "order_index": 1,
                    "total_score": 10.0,
                    "instructions": "Directions: Read the following text. Choose the best word(s) for each numbered blank and mark A, B, C or D on the ANSWER SHEET. (10 points)"
                },
                {
                    "section_code": "reading_a",
                    "title": "Section II Reading Comprehension Part A",
                    "order_index": 2,
                    "total_score": 40.0,
                    "instructions": "Directions: Read the following four texts. Answer the questions below each text by choosing A, B, C or D. Mark your answers on the ANSWER SHEET. (40 points)"
                },
                {
                    "section_code": "reading_b",
                    "title": "Section II Reading Comprehension Part B",
                    "order_index": 3,
                    "total_score": 10.0,
                    "instructions": "Directions: Read the following text and match each numbered item to the corresponding information or headings. (10 points)"
                },
                {
                    "section_code": "translation",
                    "title": "Section III Translation",
                    "order_index": 4,
                    "total_score": 15.0,
                    "instructions": "Directions: Translate the following text into Chinese. Write your translation neatly on the ANSWER SHEET. (15 points)"
                },
                {
                    "section_code": "writing_a",
                    "title": "Section IV Writing Part A",
                    "order_index": 5,
                    "total_score": 10.0,
                    "instructions": "Directions: Suppose you are organizing an event or writing an email/letter. Write about 100 words on the ANSWER SHEET. (10 points)"
                },
                {
                    "section_code": "writing_b",
                    "title": "Section IV Writing Part B",
                    "order_index": 6,
                    "total_score": 15.0,
                    "instructions": "Directions: Write an essay based on the following chart/diagram. In your essay, you should interpret the chart and give your comments. (15 points)"
                }
            ]
        })

    return exams
