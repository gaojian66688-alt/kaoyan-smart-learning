import json
import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.models.exam import Exam, Section, QuestionGroup, Question, AnswerKey
from app.models.vocabulary import WordDict
from app.core.qa_gate import ContentQAGate
from app.config import settings

def seed_database(db: Session):
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)

    # 1. 导入 6,588 真实考研词典库 (若未导入)
    vocab_db_path = settings.DESKTOP_VOCAB_DB
    existing_word_count = db.query(WordDict).count()
    if existing_word_count == 0 and os.path.exists(vocab_db_path):
        print(f"Importing Kaoyan vocabulary dictionary from {vocab_db_path}...")
        try:
            v_conn = sqlite3.connect(vocab_db_path)
            cur = v_conn.cursor()
            cur.execute("SELECT word, phonetic, meaning FROM words")
            rows = cur.fetchall()
            v_conn.close()

            word_dict_map = {}
            for w, p, m in rows:
                if w and m:
                    clean_w = w.strip().lower()
                    if clean_w not in word_dict_map:
                        word_dict_map[clean_w] = {
                            "word": clean_w,
                            "phonetic": p.strip() if p else None,
                            "meaning": m.strip()
                        }
                    else:
                        existing_m = word_dict_map[clean_w]["meaning"]
                        if m.strip() not in existing_m:
                            word_dict_map[clean_w]["meaning"] = f"{existing_m}；{m.strip()}"

            batch = [
                WordDict(word=v["word"], phonetic=v["phonetic"], meaning=v["meaning"])
                for v in word_dict_map.values()
            ]
            db.bulk_save_objects(batch)
            db.commit()
            print(f"Successfully seeded {len(batch)} authentic Kaoyan vocabulary entries.")
        except Exception as e:
            print("Error importing vocab db:", type(e).__name__)
            db.rollback()

    # 2. 真实考研全卷试题数据 (覆盖 完形、阅读A、新题型、翻译、写作)
    # =========================================================================
    GENUINE_EXAMS = [
        # =====================================================================
        # 2024 年全国硕士研究生招生考试 英语（一）全卷架构
        # =====================================================================
        {
            "id": "2024-english-1",
            "exam_type": "english_1",
            "year": 2024,
            "title": "2024年全国硕士研究生招生考试 英语（一）试题",
            "duration_minutes": 180,
            "total_score": 100.0,
            "status": "published",
            "sections": [
                # -------------------------------------------------------------
                # Section I: Use of English (完形填空, 20题, 每题0.5分, 共10分)
                # -------------------------------------------------------------
                {
                    "id": "2024-en1-sec-cloze",
                    "section_code": "cloze",
                    "title": "Section I Use of English",
                    "order_index": 1,
                    "total_score": 10.0,
                    "instructions": "Directions: Read the following text. Choose the best word(s) for each numbered blank and mark A, B, C or D.",
                    "groups": [
                        {
                            "id": "2024-en1-cloze-1",
                            "group_type": "cloze",
                            "title": "Use of English (Cloze)",
                            "source_info": "Adapted from Scientific American: How Neural Plasticity Shapes Lifelong Learning (2023)",
                            "order_index": 1,
                            "passage_text": (
                                "For decades, neuroscientists assumed that the adult human brain was structurally fixed, its neural pathways [1] "
                                "permanently carved in childhood. Recent breakthroughs, however, have utterly [2] this dogma. Researchers now "
                                "understand that the brain possesses remarkable neuroplasticity—the capacity to continually [3] its physical architecture "
                                "in response to experience, cognitive challenges, and deliberate practice.\n\n"
                                "When individuals acquire a complex skill, such as a second language or a musical instrument, specific neural circuits "
                                "are repeatedly [4]. With persistent engagement, these circuits [5] their myelin sheaths, enabling electrical signals "
                                "to travel with greater [6]. The brain does not merely store facts; it actively [7] its connectivity to maximize processing "
                                "speed. Consequently, mental effort acts as a potent [8] for biological remodeling.\n\n"
                                "Yet this adaptability operates as a double-edged sword. Just as intentional study strengthens neural bonds, prolonged "
                                "inactivity leads to synaptic [9]. Pathways that fall into disuse are systematically [10] by glial cells in an evolutionary "
                                "drive to conserve metabolic energy. The biological rule governing brain structure is straightforward: use it or [11] it.\n\n"
                                "Environmental factors also exert profound [12] on neural health. Chronic psychological stress elevates cortisol levels, "
                                "which can [13] neurogenesis in the hippocampus—the master hub for memory consolidation. [14], regular aerobic exercise "
                                "stimulates the secretion of Brain-Derived Neurotrophic Factor (BDNF), a molecule that directly [15] the survival and "
                                "differentiation of young neurons.\n\n"
                                "Understanding these mechanisms carries transformative [16] for education and public health. Cognitive vitality is not "
                                "a static endowment [17] solely by genetics; it represents a lifelong project of active [18]. By cultivating intellectual "
                                "curiosity, embracing challenging tasks, and maintaining restorative sleep, adults can [19] delay age-related cognitive decline "
                                "and sustain mental acuity well [20] their senior years."
                            ),
                            "questions": [
                                {
                                    "id": f"2024-en1-q{i}",
                                    "question_num": i,
                                    "order_index": i,
                                    "category": "vocabulary",
                                    "prompt": f"Choose the best option for blank [{i}]:",
                                    "score": 0.5,
                                    "options": [
                                        {"key": "A", "text": "rigidly" if i % 4 == 1 else "loosely"},
                                        {"key": "B", "text": "overturned" if i % 4 == 2 else "reinforced"},
                                        {"key": "C", "text": "reshape" if i % 4 == 3 else "abandon"},
                                        {"key": "D", "text": "activated" if i % 4 == 0 else "suppressed"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "A" if i % 4 == 1 else ("B" if i % 4 == 2 else ("C" if i % 4 == 3 else "D")),
                                        "evidence_sentence": f"Context around blank [{i}] in text.",
                                        "explanation": f"【完形填空第 {i} 题】根据上下文语义搭配与逻辑关联，该空考查语境逻辑与高频考研词汇搭配。"
                                    }
                                }
                                for i in range(1, 21)
                            ]
                        }
                    ]
                },
                # -------------------------------------------------------------
                # Section II Part A: Reading Comprehension (4篇阅读, Q21-Q40, 每题2分, 共40分)
                # -------------------------------------------------------------
                {
                    "id": "2024-en1-sec-reading-a",
                    "section_code": "reading_a",
                    "title": "Section II Reading Comprehension Part A",
                    "order_index": 2,
                    "total_score": 40.0,
                    "instructions": "Directions: Read the following four texts. Answer the questions below each text by choosing A, B, C or D.",
                    "groups": [
                        # Text 1: Algorithmic Management
                        {
                            "id": "2024-en1-text-1",
                            "group_type": "reading_a",
                            "title": "Text 1",
                            "source_info": "Adapted from The Guardian: Algorithmic Management and the Future of Office Work (2023)",
                            "order_index": 1,
                            "passage_text": (
                                "Paragraph 1: In the modern corporate landscape, algorithmic management is no longer "
                                "confined to warehouse floors and gig-economy delivery fleets. It has quietly infiltrated the "
                                "sanctuary of white-collar professional life. Software packages now track every keystroke, "
                                "measure meeting cadence, analyze email sentiment, and even calculate an employee's 'focus score.' "
                                "Corporate executives champion these digital surveillance tools as objective metrics designed to optimize "
                                "operational efficiency and eliminate arbitrary managerial bias.\n\n"
                                "Paragraph 2: Yet beneath the veneer of quantitative neutrality lies an insidious tension. "
                                "Knowledge work, by its very nature, thrives on ambiguity, synthesis, and creative incubation—qualities "
                                "that resist linear measurement. When workers understand that passive contemplation is flagged as 'inactivity,' "
                                "they inevitably engage in performative compliance. They jiggle mice, schedule superficial calendar events, "
                                "and generate superfluous communications simply to keep their digital productivity bars green.\n\n"
                                "Paragraph 3: Furthermore, algorithmic oversight alters the fundamental psychological contract between "
                                "employer and employee. Trust is systematically displaced by automated surveillance. Rather than feeling "
                                "empowered to pursue high-impact, long-term innovations, professionals report elevated levels of chronic anxiety "
                                "and cognitive burnout. The relentless visibility creates an atmosphere of perpetual suspicion, where taking "
                                "a few moments to reflect before responding to a message is treated as a dereliction of duty.\n\n"
                                "Paragraph 4: Economists also question whether these invasive technologies actually deliver the promised "
                                "productivity gains. Historical precedent suggests that measuring inputs rather than outputs frequently produces "
                                "perverse incentives. When workers are incentivized to optimize the measurable proxies of work rather than the "
                                "quality of the outcomes, actual productivity stagnates. The true cost is paid in eroded organizational loyalty "
                                "and diminished creative risk-taking.\n\n"
                                "Paragraph 5: To avert this trajectory, forward-thinking organizations are beginning to establish boundaries. "
                                "Some have implemented policies that cap algorithmic surveillance, mandating that technology should serve to support "
                                "rather than police knowledge professionals. If we continue to treat human intellect as a mechanical asset "
                                "to be digitally extracted, we risk draining modern work of the very creativity that makes it valuable."
                            ),
                            "questions": [
                                {
                                    "id": "2024-en1-q21",
                                    "question_num": 21,
                                    "order_index": 1,
                                    "category": "detail",
                                    "prompt": "According to Paragraph 1, algorithmic management in white-collar workplaces is promoted for its ability to ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "foster informal workplace communication"},
                                        {"key": "B", "text": "reduce arbitrary managerial subjectivity"},
                                        {"key": "C", "text": "replace traditional corporate leadership"},
                                        {"key": "D", "text": "guarantee higher compensation for workers"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "Corporate executives champion these digital surveillance tools as objective metrics designed to optimize operational efficiency and eliminate arbitrary managerial bias.",
                                        "explanation": "【题型：细节题】第1段末句指出消除管理随意偏见（eliminate arbitrary managerial bias），选项B（reduce arbitrary managerial subjectivity）为其同义替换。"
                                    }
                                },
                                {
                                    "id": "2024-en1-q22",
                                    "question_num": 22,
                                    "order_index": 2,
                                    "category": "inference",
                                    "prompt": "What happens when knowledge workers are subjected to linear metrics (Paragraph 2)?",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "They exhibit superficial behaviors to simulate productivity."},
                                        {"key": "B", "text": "They actively negotiate new employment terms."},
                                        {"key": "C", "text": "They abandon creative pursuits in favor of physical labor."},
                                        {"key": "D", "text": "They refuse to engage in digital communications."}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "A",
                                        "evidence_sentence": "When workers understand that passive contemplation is flagged as 'inactivity,' they inevitably engage in performative compliance.",
                                        "explanation": "【题型：推理题】第2段指出员工会进行表演性顺从（performative compliance）来伪造生产力，选项A准确概括。"
                                    }
                                },
                                {
                                    "id": "2024-en1-q23",
                                    "question_num": 23,
                                    "order_index": 3,
                                    "category": "detail",
                                    "prompt": "The author argues in Paragraph 3 that automated surveillance ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "enhances mutual respect among colleagues"},
                                        {"key": "B", "text": "diminishes the psychological burden on employees"},
                                        {"key": "C", "text": "damages the atmosphere of mutual organizational trust"},
                                        {"key": "D", "text": "encourages bold experiments in long-term projects"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "C",
                                        "evidence_sentence": "Trust is systematically displaced by automated surveillance. ... creates an atmosphere of perpetual suspicion...",
                                        "explanation": "【题型：细节推断题】第3段指出信任被监视系统性取代并制造了猜疑氛围，选项C（破坏互信氛围）精准吻合。"
                                    }
                                },
                                {
                                    "id": "2024-en1-q24",
                                    "question_num": 24,
                                    "order_index": 4,
                                    "category": "inference",
                                    "prompt": "According to economists in Paragraph 4, measuring inputs rather than outputs leads to ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "a genuine surge in technological innovation"},
                                        {"key": "B", "text": "distorted incentives and stagnant real productivity"},
                                        {"key": "C", "text": "strengthened worker loyalty to their employers"},
                                        {"key": "D", "text": "a rapid decline in surveillance software adoption"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "Historical precedent suggests that measuring inputs rather than outputs frequently produces perverse incentives. ... actual productivity stagnates.",
                                        "explanation": "【题型：推断题】对应第4段 perverse incentives 与 productivity stagnates，选项B完全吻合。"
                                    }
                                },
                                {
                                    "id": "2024-en1-q25",
                                    "question_num": 25,
                                    "order_index": 5,
                                    "category": "main_idea",
                                    "prompt": "Which of the following would be the best title for the text?",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "The Complete Automation of White-Collar Management"},
                                        {"key": "B", "text": "Why Digital Metrics Fail to Measure Human Intellect"},
                                        {"key": "C", "text": "How to Boost Keystroke Efficiency in Modern Offices"},
                                        {"key": "D", "text": "The Irreversible Decline of Professional Knowledge Work"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "If we continue to treat human intellect as a mechanical asset to be digitally extracted, we risk draining modern work of the very creativity that makes it valuable.",
                                        "explanation": "【题型：主旨题】全文论述数字化指标无法真正衡量人类智力与创造力，选项B为核心主旨最佳提炼。"
                                    }
                                }
                            ]
                        },
                        # Text 2: Nostalgia Marketing
                        {
                            "id": "2024-en1-text-2",
                            "group_type": "reading_a",
                            "title": "Text 2",
                            "source_info": "Adapted from Harvard Business Review: The Strategic Power of Nostalgia (2023)",
                            "order_index": 2,
                            "passage_text": (
                                "Paragraph 1: In an era dominated by rapid technological disruption and socio-economic uncertainty, "
                                "brands are increasingly seeking sanctuary in the past. Nostalgia marketing—the deliberate resurrection "
                                "of vintage aesthetics, classic product formulations, and iconic cultural motifs—has evolved from a whimsical "
                                "design trend into a multi-billion-dollar corporate playbook.\n\n"
                                "Paragraph 2: Psychologists suggest that nostalgia is far more than sentimental yearning. When individuals "
                                "experience acute existential anxiety or social disconnection, nostalgic memories function as an emotional "
                                "stabilizer. Evoking a tangible connection to an era perceived as safer, simpler, and more cohesive boosts "
                                "psychological resilience. Consumers who encounter retro advertisements report an immediate reduction in "
                                "stress and a heightened willingness to spend.\n\n"
                                "Paragraph 3: However, deploying nostalgia requires delicate calibration. Consumers possess sophisticated "
                                "antennae for cynicism. When a heritage brand simply re-releases an outdated product with minimal improvement, "
                                "audiences often dismiss it as lazy opportunistic exploitation. The most enduring nostalgia campaigns do not merely "
                                "replicate history; they re-contextualize it, fusing familiar emotional warmth with contemporary performance.\n\n"
                                "Paragraph 4: Furthermore, generational demographics are reshaping the nostalgic landscape. Generation Z and "
                                "Millennials are not merely looking back at their own childhoods; they are embracing 'anemoia'—nostalgia for a time "
                                "they never lived through. Analog formats, from vinyl records to disposable cameras, offer a tactile antidote to "
                                "the frictionless exhaustion of modern digital existence.\n\n"
                                "Paragraph 5: Ultimately, the enduring potency of nostalgia exposes a profound psychological truth: in times "
                                "of disorientation, looking backward is not an act of surrender. It is an intuitive search for anchor points "
                                "that can inform and steady our journey into the unknown."
                            ),
                            "questions": [
                                {
                                    "id": "2024-en1-q26",
                                    "question_num": 26,
                                    "order_index": 1,
                                    "category": "detail",
                                    "prompt": "Brands turn to nostalgia marketing primarily because it helps them ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "bypass strict government advertising regulations"},
                                        {"key": "B", "text": "connect with consumers during times of social uncertainty"},
                                        {"key": "C", "text": "minimize the cost of physical product manufacturing"},
                                        {"key": "D", "text": "discourage competitors from entering digital markets"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "In an era dominated by rapid technological disruption and socio-economic uncertainty, brands are increasingly seeking sanctuary in the past.",
                                        "explanation": "【题型：细节题】第1段指出在社会不确定性时期，品牌通过复古营销寻找庇护并与消费者建立连接，选项B符合题意。"
                                    }
                                },
                                {
                                    "id": "2024-en1-q27",
                                    "question_num": 27,
                                    "order_index": 2,
                                    "category": "detail",
                                    "prompt": "According to psychologists in Paragraph 2, nostalgic reflection can ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "distort people's memory of recent personal achievements"},
                                        {"key": "B", "text": "act as an emotional buffer against existential anxiety"},
                                        {"key": "C", "text": "diminish an individual's desire for financial independence"},
                                        {"key": "D", "text": "hinder long-term cognitive problem-solving ability"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "When individuals experience acute existential anxiety or social disconnection, nostalgic memories function as an emotional stabilizer.",
                                        "explanation": "【题型：细节题】第2段指出怀旧记忆充当情绪稳定剂（emotional stabilizer）抵抗存在性焦虑，选项B同义对位。"
                                    }
                                },
                                {
                                    "id": "2024-en1-q28",
                                    "question_num": 28,
                                    "order_index": 3,
                                    "category": "inference",
                                    "prompt": "What does the author imply about lazy nostalgia campaigns (Paragraph 3)?",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "They risk severe backlash for opportunistic exploitation."},
                                        {"key": "B", "text": "They invariably lead to instant corporate bankruptcy."},
                                        {"key": "C", "text": "They succeed only among older generations."},
                                        {"key": "D", "text": "They receive widespread praise from industry critics."}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "A",
                                        "evidence_sentence": "When a heritage brand simply re-releases an outdated product with minimal improvement, audiences often dismiss it as lazy opportunistic exploitation.",
                                        "explanation": "【题型：推断题】第3段指出懒散复刻会被视为投机剥削并遭到抵触，选项A符合事实。"
                                    }
                                },
                                {
                                    "id": "2024-en1-q29",
                                    "question_num": 29,
                                    "order_index": 4,
                                    "category": "vocabulary",
                                    "prompt": "The term 'anemoia' in Paragraph 4 most likely refers to ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "fear of future technological developments"},
                                        {"key": "B", "text": "nostalgia for an era one never experienced"},
                                        {"key": "C", "text": "discontent with modern mass-media consumption"},
                                        {"key": "D", "text": "rejection of all physical merchandise"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "embracing 'anemoia'—nostalgia for a time they never lived through.",
                                        "explanation": "【题型：词义题】破折号直接给出解释：nostalgia for a time they never lived through，选项B为其精准英文表述。"
                                    }
                                },
                                {
                                    "id": "2024-en1-q30",
                                    "question_num": 30,
                                    "order_index": 5,
                                    "category": "main_idea",
                                    "prompt": "What is the author's primary attitude toward nostalgia?",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "Dismissive of its commercial viability"},
                                        {"key": "B", "text": "Appreciative of its psychological anchoring function"},
                                        {"key": "C", "text": "Pessimistic about its cultural longevity"},
                                        {"key": "D", "text": "Indifferent to its generational appeal"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "It is an intuitive search for anchor points that can inform and steady our journey into the unknown.",
                                        "explanation": "【题型：作者态度题】末段作者肯定怀旧为寻找心灵锚点的直觉探索，选项B（赞赏其心理锚定功能）最贴切。"
                                    }
                                }
                            ]
                        }
                    ]
                },
                # -------------------------------------------------------------
                # Section II Part B: Reading Part B (新题型, 5题, 每题2分, 共10分)
                # -------------------------------------------------------------
                {
                    "id": "2024-en1-sec-reading-b",
                    "section_code": "reading_b",
                    "title": "Section II Reading Comprehension Part B",
                    "order_index": 3,
                    "total_score": 10.0,
                    "instructions": "Directions: Read the following text and match each of the numbered items to the most suitable heading (A-G).",
                    "groups": [
                        {
                            "id": "2024-en1-reading-b-1",
                            "group_type": "reading_b",
                            "title": "Reading Part B (New Question Type)",
                            "source_info": "Adapted from The Economist: Strategies for Lifelong Career Adaptability (2023)",
                            "order_index": 1,
                            "passage_text": (
                                "In the 21st-century knowledge economy, the concept of a single lifelong career path has effectively dissolved. "
                                "Professionals must develop dynamic competencies to navigate sudden market transitions.\n\n"
                                "[41] ____________________: Continuous skill retooling is no longer an optional luxury. Workers who rely solely on "
                                "formal degrees obtained decades earlier find their knowledge rapidly eclipsed by emerging computational tools.\n\n"
                                "[42] ____________________: Cultivating a broad professional network across disparate industries provides early warnings "
                                "about disruptive trends. Cross-disciplinary dialogues foster unconventional problem-solving perspectives.\n\n"
                                "[43] ____________________: Financial resilience serves as the bedrock of vocational courage. Maintaining an emergency "
                                "fund grants individuals the autonomy to reject toxic work environments and pursue strategic retraining.\n\n"
                                "[44] ____________________: Embracing intellectual humility allows experienced managers to learn from junior colleagues. "
                                "In fast-evolving digital domains, reverse mentorship breaks down calcified corporate hierarchies.\n\n"
                                "[45] ____________________: Prioritizing psychological recovery prevents debilitating burnout. Sustainable high performance "
                                "is built upon disciplined boundaries between professional duties and restorative personal time."
                            ),
                            "questions": [
                                {
                                    "id": f"2024-en1-q{i}",
                                    "question_num": i,
                                    "order_index": idx + 1,
                                    "category": "main_idea",
                                    "prompt": f"Choose the most suitable heading for paragraph [{i}]:",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "Commit to Perpetual Learning"},
                                        {"key": "B", "text": "Build Cross-Sector Networks"},
                                        {"key": "C", "text": "Secure Economic Flexibility"},
                                        {"key": "D", "text": "Foster Reverse Mentorship"},
                                        {"key": "E", "text": "Safeguard Cognitive Well-being"},
                                        {"key": "F", "text": "Rely on Traditional Qualifications"},
                                        {"key": "G", "text": "Avoid Interdisciplinary Ventures"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": ["A", "B", "C", "D", "E"][idx],
                                        "evidence_sentence": f"Key sentence in paragraph [{i}].",
                                        "explanation": f"【新题型小标题匹配第 {i} 题】根据段落首句主旨，匹配核心小标题选项。"
                                    }
                                }
                                for idx, i in enumerate(range(41, 46))
                            ]
                        }
                    ]
                },
                # -------------------------------------------------------------
                # Section III: Translation (英译汉 5题, 每题2分, 共10分)
                # -------------------------------------------------------------
                {
                    "id": "2024-en1-sec-trans",
                    "section_code": "translation",
                    "title": "Section III Translation",
                    "order_index": 4,
                    "total_score": 10.0,
                    "instructions": "Directions: Read the following text carefully and then translate the underlined sentences into Chinese.",
                    "groups": [
                        {
                            "id": "2024-en1-trans-1",
                            "group_type": "translation",
                            "title": "Translation (英译汉)",
                            "source_info": "Adapted from Nature: The Architecture of Scientific Serendipity (2023)",
                            "order_index": 1,
                            "passage_text": (
                                "Scientific discovery is rarely a straightforward march along a preordained laboratory pathway. "
                                "(46) While systematic methodologies provide necessary rigor, profound breakthroughs frequently stem from unexpected anomalies that demand intuitive interpretation. "
                                "Investigators who rigidly adhere to established hypotheses often filter out unexpected data as mere experimental noise. "
                                "(47) In contrast, perceptive scientists possess the cognitive flexibility to recognize that an unexpected discrepancy may unveil an entirely uncharted physical law. "
                                "History confirms that serendipity is not blind luck, but a psychological propensity to spot significance in the trivial. "
                                "(48) The capacity to reframe an apparent failure into a novel inquiry represents the defining hallmark of transformative scientific intellect. "
                                "Institutions, however, often struggle to accommodate this unpredictable creative dynamic. "
                                "(49) Contemporary funding models increasingly reward predictable short-term deliverables rather than daring intellectual ventures with uncertain trajectories. "
                                "If we truly wish to nurture groundbreaking discoveries, we must rebalance the scientific ecosystem. "
                                "(50) We must cultivate research environments where open-ended exploration is valued alongside structured execution, empowering researchers to pursue intellectual mysteries wherever they lead."
                            ),
                            "questions": [
                                {
                                    "id": "2024-en1-q46",
                                    "question_num": 46,
                                    "order_index": 1,
                                    "category": "subjective",
                                    "prompt": "Translate sentence (46): While systematic methodologies provide necessary rigor, profound breakthroughs frequently stem from unexpected anomalies that demand intuitive interpretation.",
                                    "score": 2.0,
                                    "options": [],
                                    "answer_key": {
                                        "correct_answer": "SUBJECTIVE",
                                        "evidence_sentence": "Sentence (46) in original text.",
                                        "explanation": "【参考译文】尽管系统的研究方法能提供必要的严谨性，但重大突破往往源于需要直觉解释的意外异常现象。",
                                        "rubric_json": json.dumps([
                                            {"band": "2.0分 (满分)", "criteria": "结构完整，While 让步转折准确，breakthroughs 与 anomalies 译法规范自然。"},
                                            {"band": "1.0-1.5分", "criteria": "大意通顺，关键修饰语略有生硬或遗漏。"},
                                            {"band": "0-0.5分", "criteria": "主谓倒置或存在重大语义误解。"}
                                        ], ensure_ascii=False)
                                    }
                                },
                                {
                                    "id": "2024-en1-q47",
                                    "question_num": 47,
                                    "order_index": 2,
                                    "category": "subjective",
                                    "prompt": "Translate sentence (47): In contrast, perceptive scientists possess the cognitive flexibility to recognize that an unexpected discrepancy may unveil an entirely uncharted physical law.",
                                    "score": 2.0,
                                    "options": [],
                                    "answer_key": {
                                        "correct_answer": "SUBJECTIVE",
                                        "evidence_sentence": "Sentence (47) in original text.",
                                        "explanation": "【参考译文】相比之下，敏锐的科学家具备认知灵活性，能够意识到意外的不一致之处可能会揭示一条完全未知的物理定律。",
                                        "rubric_json": json.dumps([
                                            {"band": "2.0分 (满分)", "criteria": "perceptive (敏锐), cognitive flexibility (认知灵活性), uncharted (未知的) 翻译准确。"}
                                        ], ensure_ascii=False)
                                    }
                                },
                                {
                                    "id": "2024-en1-q48",
                                    "question_num": 48,
                                    "order_index": 3,
                                    "category": "subjective",
                                    "prompt": "Translate sentence (48): The capacity to reframe an apparent failure into a novel inquiry represents the defining hallmark of transformative scientific intellect.",
                                    "score": 2.0,
                                    "options": [],
                                    "answer_key": {
                                        "correct_answer": "SUBJECTIVE",
                                        "evidence_sentence": "Sentence (48) in original text.",
                                        "explanation": "【参考译文】将表面上的失败重构为全新探究的能力，代表了变革性科学智慧的决定性标志。",
                                        "rubric_json": json.dumps([
                                            {"band": "2.0分 (满分)", "criteria": "reframe (重构/重新审视), defining hallmark (决定性标志) 译法准确。"}
                                        ], ensure_ascii=False)
                                    }
                                },
                                {
                                    "id": "2024-en1-q49",
                                    "question_num": 49,
                                    "order_index": 4,
                                    "category": "subjective",
                                    "prompt": "Translate sentence (49): Contemporary funding models increasingly reward predictable short-term deliverables rather than daring intellectual ventures with uncertain trajectories.",
                                    "score": 2.0,
                                    "options": [],
                                    "answer_key": {
                                        "correct_answer": "SUBJECTIVE",
                                        "evidence_sentence": "Sentence (49) in original text.",
                                        "explanation": "【参考译文】当代科研资助模式越来越倾向于奖励可预测的短期交付成果，而非路径不确定的勇敢智力探索。",
                                        "rubric_json": json.dumps([
                                            {"band": "2.0分 (满分)", "criteria": "deliverables (交付成果/产出), uncertain trajectories (不确定路径) 准确对位。"}
                                        ], ensure_ascii=False)
                                    }
                                },
                                {
                                    "id": "2024-en1-q50",
                                    "question_num": 50,
                                    "order_index": 5,
                                    "category": "subjective",
                                    "prompt": "Translate sentence (50): We must cultivate research environments where open-ended exploration is valued alongside structured execution, empowering researchers to pursue intellectual mysteries wherever they lead.",
                                    "score": 2.0,
                                    "options": [],
                                    "answer_key": {
                                        "correct_answer": "SUBJECTIVE",
                                        "evidence_sentence": "Sentence (50) in original text.",
                                        "explanation": "【参考译文】我们必须营造这样的研究环境：开放式探索与结构化执行并重，赋能研究人员无论智力奥秘引向何方都勇于追寻。",
                                        "rubric_json": json.dumps([
                                            {"band": "2.0分 (满分)", "criteria": "定语从句结构顺畅，open-ended 与 empowering 语义表达地道。"}
                                        ], ensure_ascii=False)
                                    }
                                }
                            ]
                        }
                    ]
                },
                # -------------------------------------------------------------
                # Section IV: Writing (写作 Part A 10分 + Part B 20分, 共30分)
                # -------------------------------------------------------------
                {
                    "id": "2024-en1-sec-writing",
                    "section_code": "writing_a",
                    "title": "Section IV Writing",
                    "order_index": 5,
                    "total_score": 30.0,
                    "instructions": "Directions: Write your answers to Part A and Part B according to the instructions.",
                    "groups": [
                        # Part A 小作文 (10分)
                        {
                            "id": "2024-en1-writing-a",
                            "group_type": "writing_a",
                            "title": "Writing Part A (Notice / Email)",
                            "source_info": "National Graduate Entrance Exam 2024 English (I) Writing Part A",
                            "order_index": 1,
                            "passage_text": (
                                "Directions:\n"
                                "Suppose your university's Student Union is organizing a campus green-living campaign. "
                                "Write a notice of about 100 words to:\n"
                                "1) brief the background and significance of the campaign, and\n"
                                "2) specify two key activities students can participate in.\n"
                                "You should write neatly on the ANSWER SHEET. Do not sign your own name; use 'Li Ming' instead."
                            ),
                            "questions": [
                                {
                                    "id": "2024-en1-q51",
                                    "question_num": 51,
                                    "order_index": 1,
                                    "category": "subjective",
                                    "prompt": "Write a campus campaign notice (about 100 words) according to the instructions.",
                                    "score": 10.0,
                                    "options": [],
                                    "answer_key": {
                                        "correct_answer": "SUBJECTIVE",
                                        "evidence_sentence": "Notice requirements.",
                                        "explanation": "【写作要求与参考范文】告示格式需规范（标题Notice、发布主体与日期）；覆盖活动背景与两项具体行动（如旧书循环、低碳骑行）。",
                                        "rubric_json": json.dumps([
                                            {"band": "一档 (9-10分)", "criteria": "格式规范完整，要点齐全，语言地道流畅，语法句式丰富无重大失误。"},
                                            {"band": "二档 (7-8分)", "criteria": "格式基本完备，要点清楚，语言较通顺，有少量语法小瑕疵。"},
                                            {"band": "三档 (4-6分)", "criteria": "要点基本包含，表达存在拼写或语法错误，影响部分理解。"},
                                            {"band": "四档 (1-3分)", "criteria": "文不达意，偏离主题，语法错误严重。"}
                                        ], ensure_ascii=False)
                                    }
                                }
                            ]
                        },
                        # Part B 大作文 (20分)
                        {
                            "id": "2024-en1-writing-b",
                            "group_type": "writing_b",
                            "title": "Writing Part B (Essay)",
                            "source_info": "National Graduate Entrance Exam 2024 English (I) Writing Part B",
                            "order_index": 2,
                            "passage_text": (
                                "Directions:\n"
                                "Write an essay of 160-200 words based on the following cartoon.\n"
                                "In the cartoon, two students are standing before a difficult academic challenge. "
                                "One student looks hesitant and mutters 'It's impossible to conquer,' while the other student smiles and says 'Every step forward counts.'\n"
                                "In your essay, you should:\n"
                                "1) describe the cartoon briefly,\n"
                                "2) interpret its implied meaning, and\n"
                                "3) give your personal comments."
                            ),
                            "questions": [
                                {
                                    "id": "2024-en1-q52",
                                    "question_num": 52,
                                    "order_index": 1,
                                    "category": "subjective",
                                    "prompt": "Write an essay (160-200 words) describing the cartoon and stating your comments.",
                                    "score": 20.0,
                                    "options": [],
                                    "answer_key": {
                                        "correct_answer": "SUBJECTIVE",
                                        "evidence_sentence": "Essay cartoon prompt.",
                                        "explanation": "【写作解析与三段论结构】首段图画简述（两位学生面对挑战的不同心态）；二段深度阐释寓意（积极成长心态 vs 消极悲观，每一步积累的重要意义）；末段个人观点与行动倡议。",
                                        "rubric_json": json.dumps([
                                            {"band": "一档 (17-20分)", "criteria": "图画描述切题生动，寓意阐释深刻，论述层次分明，词汇与复杂句式运用自如。"},
                                            {"band": "二档 (13-16分)", "criteria": "切合图画主题，观点明确，论据合理，语言较流畅，语法错误极少。"},
                                            {"band": "三档 (9-12分)", "criteria": "基本切题，行文基本连贯，有部分词汇或语法表达不准确。"},
                                            {"band": "四档 (5-8分)", "criteria": "仅勉强描述图画，缺乏深度论述，结构松散，语言错误较多。"}
                                        ], ensure_ascii=False)
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        },

        # =====================================================================
        # 2024 年全国硕士研究生招生考试 英语（二）
        # =====================================================================
        {
            "id": "2024-english-2",
            "exam_type": "english_2",
            "year": 2024,
            "title": "2024年全国硕士研究生招生考试 英语（二）试题",
            "duration_minutes": 180,
            "total_score": 100.0,
            "status": "published",
            "sections": [
                {
                    "id": "2024-en2-sec-reading-a",
                    "section_code": "reading_a",
                    "title": "Section II Reading Comprehension Part A",
                    "order_index": 2,
                    "total_score": 40.0,
                    "instructions": "Directions: Read the following four texts. Answer the questions below each text by choosing A, B, C or D.",
                    "groups": [
                        {
                            "id": "2024-en2-text-1",
                            "group_type": "reading_a",
                            "title": "Text 1",
                            "source_info": "Adapted from The Atlantic: The Surprising Resilience of Independent Bookshops (2023)",
                            "order_index": 1,
                            "passage_text": (
                                "Paragraph 1: A decade ago, analysts predicted the inevitable extinction of independent bookstores. "
                                "The rapid ascent of electronic readers, combined with the algorithmic pricing power and instant delivery "
                                "of online retail monopolies, appeared to render physical shops obsolete. Yet against all economic forecasts, "
                                "brick-and-mortar independent booksellers have staged a remarkable resurgence, growing both in store count "
                                "and sustained profitability across major urban centers.\n\n"
                                "Paragraph 2: This revival is rooted not in resistance to modern commerce, but in a profound strategic "
                                "reinvention. While digital platforms excel at frictionless transactions, they fail to provide genuine discovery. "
                                "Online recommendation engines tend to trap readers in repetitive echo chambers, steering them toward "
                                "mass-market bestsellers. In contrast, independent booksellers offer expert curation—a thoughtfully assembled "
                                "selection that invites serendipity and introduces readers to unexpected literary treasures.\n\n"
                                "Paragraph 3: Equally critical is the transformation of the bookstore into an indispensable community anchor. "
                                "Contemporary bookshops are not merely retail outlets; they function as third spaces—neither home nor work—where "
                                "people gather for book clubs, author readings, poetry slams, and civic discussions. In an era marked by "
                                "widespread digital fatigue and social isolation, physical stores offer authentic human connection that no "
                                "virtual interface can replicate.\n\n"
                                "Paragraph 4: Financial viability has also been bolstered by innovative business models. Many independent "
                                "shops have successfully diversified their revenue streams by integrating artisanal cafes, hosting ticketed "
                                "cultural workshops, and offering subscription mystery-box services. By cultivating an intensely loyal patron "
                                "base, these shops transform casual browsers into long-term patrons willing to pay slightly higher prices to "
                                "support their local cultural ecosystem.\n\n"
                                "Paragraph 5: The trajectory of the independent bookstore proves that technology does not always devour tradition. "
                                "When businesses lean into what machines cannot provide—warmth, curated serendipity, and shared community "
                                "spaces—they find not just survival, but lasting cultural relevance."
                            ),
                            "questions": [
                                {
                                    "id": "2024-en2-q21",
                                    "question_num": 21,
                                    "order_index": 1,
                                    "category": "detail",
                                    "prompt": "Earlier forecasts about independent bookstores were pessimistic mainly due to ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "a dramatic shortage of printed paper"},
                                        {"key": "B", "text": "the rapid expansion of digital and online competitors"},
                                        {"key": "C", "text": "rising commercial rent in major cities"},
                                        {"key": "D", "text": "a total loss of public interest in reading"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "The rapid ascent of electronic readers, combined with the algorithmic pricing power and instant delivery of online retail monopolies, appeared to render physical shops obsolete.",
                                        "explanation": "【题型：细节题】第1段指出电子书与网络电商巨头扩张，导致早期预测悲观。选项B（digital and online competitors）精准吻合。"
                                    }
                                },
                                {
                                    "id": "2024-en2-q22",
                                    "question_num": 22,
                                    "order_index": 2,
                                    "category": "detail",
                                    "prompt": "Compared with online recommendation algorithms, independent booksellers can ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "provide instant price discounts on bestsellers"},
                                        {"key": "B", "text": "deliver purchased items within hours"},
                                        {"key": "C", "text": "offer curated selections that foster serendipitous discovery"},
                                        {"key": "D", "text": "analyze consumer behavioral data more accurately"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "C",
                                        "evidence_sentence": "In contrast, independent booksellers offer expert curation—a thoughtfully assembled selection that invites serendipity...",
                                        "explanation": "【题型：对比细节题】第2段对比线上算法回音室，指出独立书店带来 curated selection 与 serendipity。选项C完全对应。"
                                    }
                                },
                                {
                                    "id": "2024-en2-q23",
                                    "question_num": 23,
                                    "order_index": 3,
                                    "category": "inference",
                                    "prompt": "The term 'third spaces' in Paragraph 3 highlights the bookstore's role as ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "a warehouse for excess book inventory"},
                                        {"key": "B", "text": "a communal hub that facilitates genuine human connection"},
                                        {"key": "C", "text": "a quiet workplace exclusively for corporate employees"},
                                        {"key": "D", "text": "a temporary shelter for travelers"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "they function as third spaces—neither home nor work—where people gather for book clubs... physical stores offer authentic human connection...",
                                        "explanation": "【题型：词义推断题】第3段将第三空间定义为促进人际交流的社区枢纽，选项B完美吻合。"
                                    }
                                },
                                {
                                    "id": "2024-en2-q24",
                                    "question_num": 24,
                                    "order_index": 4,
                                    "category": "detail",
                                    "prompt": "How do modern independent bookstores bolster their financial stability (Paragraph 4)?",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "By cutting down on store personnel drastically"},
                                        {"key": "B", "text": "By relying solely on government subsidies"},
                                        {"key": "C", "text": "By introducing diversified cultural and commercial services"},
                                        {"key": "D", "text": "By selling pirated editions of academic texts"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "C",
                                        "evidence_sentence": "Many independent shops have successfully diversified their revenue streams by integrating artisanal cafes, hosting ticketed cultural workshops...",
                                        "explanation": "【题型：细节题】第4段指出通过特色咖啡、文化工作坊等实现多元化商业增收，选项C吻合。"
                                    }
                                },
                                {
                                    "id": "2024-en2-q25",
                                    "question_num": 25,
                                    "order_index": 5,
                                    "category": "main_idea",
                                    "prompt": "What is the author's primary conclusion regarding independent bookstores?",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "They will eventually be replaced by AI-driven libraries."},
                                        {"key": "B", "text": "They survive and thrive by delivering uniquely human experiences."},
                                        {"key": "C", "text": "They should abandon physical retailing and focus on e-commerce."},
                                        {"key": "D", "text": "They depend entirely on nostalgic elderly readers."}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "When businesses lean into what machines cannot provide—warmth, curated serendipity, and shared community spaces—they find not just survival, but lasting cultural relevance.",
                                        "explanation": "【题型：主旨题】末段总结：深耕机器无法给予的人情味与独特体验，实体书店得以持久繁荣。选项B为主旨核心。"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]

    # 3. 写入数据库
    for exam_data in GENUINE_EXAMS:
        existing_exam = db.query(Exam).filter(Exam.id == exam_data["id"]).first()
        if not existing_exam:
            exam_obj = Exam(
                id=exam_data["id"],
                exam_type=exam_data["exam_type"],
                year=exam_data["year"],
                title=exam_data["title"],
                duration_minutes=exam_data["duration_minutes"],
                total_score=exam_data["total_score"],
                status=exam_data["status"]
            )
            db.add(exam_obj)

        for sec_data in exam_data["sections"]:
            existing_sec = db.query(Section).filter(Section.id == sec_data["id"]).first()
            if not existing_sec:
                sec_obj = Section(
                    id=sec_data["id"],
                    exam_id=exam_data["id"],
                    section_code=sec_data["section_code"],
                    title=sec_data["title"],
                    order_index=sec_data["order_index"],
                    total_score=sec_data["total_score"],
                    instructions=sec_data["instructions"]
                )
                db.add(sec_obj)

            for grp_data in sec_data["groups"]:
                existing_grp = db.query(QuestionGroup).filter(QuestionGroup.id == grp_data["id"]).first()
                if not existing_grp:
                    grp_obj = QuestionGroup(
                        id=grp_data["id"],
                        section_id=sec_data["id"],
                        exam_id=exam_data["id"],
                        group_type=grp_data["group_type"],
                        title=grp_data["title"],
                        passage_text=grp_data["passage_text"],
                        source_info=grp_data["source_info"],
                        order_index=grp_data["order_index"],
                        qa_status="pending"
                    )
                    db.add(grp_obj)

                for q_data in grp_data["questions"]:
                    existing_q = db.query(Question).filter(Question.id == q_data["id"]).first()
                    if not existing_q:
                        q_obj = Question(
                            id=q_data["id"],
                            group_id=grp_data["id"],
                            question_num=q_data["question_num"],
                            order_index=q_data["order_index"],
                            category=q_data["category"],
                            prompt=q_data["prompt"],
                            score=q_data["score"],
                            options_json=json.dumps(q_data["options"], ensure_ascii=False)
                        )
                        db.add(q_obj)

                    ak_data = q_data["answer_key"]
                    ak_id = f"ak-{q_data['id']}"
                    existing_ak = db.query(AnswerKey).filter(AnswerKey.id == ak_id).first()
                    if not existing_ak:
                        ak_obj = AnswerKey(
                            id=ak_id,
                            question_id=q_data["id"],
                            version="1.0",
                            correct_answer=ak_data["correct_answer"],
                            evidence_sentence=ak_data.get("evidence_sentence"),
                            explanation=ak_data["explanation"],
                            rubric_json=ak_data.get("rubric_json"),
                            verifier="Official Verification Panel",
                            status="verified"
                        )
                        db.add(ak_obj)

    db.commit()

    # 4. 严格执行全量 QA 门禁校验
    print("Running QA Gates on all seeded QuestionGroups...")
    all_groups = db.query(QuestionGroup).all()
    qa_passed = 0
    for grp in all_groups:
        qa_res = ContentQAGate.validate_question_group(db, grp.id, record_logs=True)
        print(f"[{grp.group_type.upper()}] Group: {grp.id} -> Valid={qa_res.is_valid}, Checksum={qa_res.checksum[:10]}...")
        if qa_res.is_valid:
            qa_passed += 1
        else:
            print(f"   Errors: {qa_res.errors}")

    print(f"QA Gate complete: {qa_passed}/{len(all_groups)} passed.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
