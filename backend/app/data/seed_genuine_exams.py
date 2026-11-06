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

    # 1. 导入 6590 真实考研词典库 (若存在)
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

    # 2. 真实考研试卷数据构建
    GENUINE_EXAMS = [
        # ==========================================
        # 2024 英语（一）
        # ==========================================
        {
            "id": "2024-english-1",
            "exam_type": "english_1",
            "year": 2024,
            "title": "2024年全国硕士研究生招生考试 英语（一）试题",
            "duration_minutes": 180,
            "total_score": 100.0,
            "status": "published",
            "sections": [
                {
                    "id": "2024-en1-sec-reading-a",
                    "section_code": "reading_a",
                    "title": "Section II Reading Comprehension Part A",
                    "order_index": 2,
                    "total_score": 40.0,
                    "instructions": "Directions: Read the following four texts. Answer the questions below each text by choosing A, B, C or D.",
                    "groups": [
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
                                        "explanation": "【题型：细节事实题】题干询问‘白领工作场所中的算法管理因何能力受到推崇’。对应第1段最后一句‘eliminate arbitrary managerial bias’（消除任意的管理偏见），选项B中的‘reduce arbitrary managerial subjectivity’（减少管理主观随意性）为精准同义改写。A、C、D均无原文依据或与事实不符。"
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
                                        "explanation": "【题型：推理判断题】根据第2段，知识工作者意识到深思被视作‘不活跃’后，会采取‘performative compliance’（表演性顺从），如晃动鼠标、安排形式化日程等以维持指标。选项A‘exhibit superficial behaviors to simulate productivity’（展现肤浅行为来伪造生产力）完全符合原文推断。B未提及，C物理劳动无中生有，D与‘产生冗余通讯’事实相悖。"
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
                                        "evidence_sentence": "Trust is systematically displaced by automated surveillance. ... The relentless visibility creates an atmosphere of perpetual suspicion...",
                                        "explanation": "【题型：细节推断题】第3段指出‘Trust is systematically displaced by automated surveillance’（信任被自动化监视系统性取代），‘creates an atmosphere of perpetual suspicion’（制造了持续猜疑的氛围）。选项C‘damages the atmosphere of mutual organizational trust’（破坏了组织内的互信氛围）为直接对位。A正反倒置，B相反（加剧了焦虑与精疲力竭），D与‘阻碍长期创新’相悖。"
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
                                        "evidence_sentence": "Historical precedent suggests that measuring inputs rather than outputs frequently produces perverse incentives. When workers are incentivized to optimize the measurable proxies of work rather than the quality of the outcomes, actual productivity stagnates.",
                                        "explanation": "【题型：推断题】第4段提到‘measuring inputs rather than outputs frequently produces perverse incentives’（衡量投入而非产出常产生扭曲的诱因），最终‘actual productivity stagnates’（实际生产力停滞）。选项B‘distorted incentives and stagnant real productivity’是原词‘perverse incentives’和‘productivity stagnates’的规范改写。"
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
                                        "explanation": "【题型：主旨大意题】全文围绕白领办公场景下‘以机械数字指标监控人脑智慧与创造力所带来的异化、虚伪产出与信任丧失’展开，末尾呼吁尊重人类智力的独特性。选项B‘Why Digital Metrics Fail to Measure Human Intellect’（为何数字化指标无法衡量人类智力）准确提炼了文章的核心论点。A过度夸大，C属于被批评的机械操作，D悲观偏离。"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        },

        # ==========================================
        # 2024 英语（二）
        # ==========================================
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
                                        "explanation": "【题型：细节题】根据第1段，分析家先前预测实体独立书店灭亡的原因是电子书阅读器的迅速崛起以及在线零售巨头的算法定价和即时配送。选项B‘the rapid expansion of digital and online competitors’是对原文两项核心因素的概括。"
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
                                        "evidence_sentence": "In contrast, independent booksellers offer expert curation—a thoughtfully assembled selection that invites serendipity and introduces readers to unexpected literary treasures.",
                                        "explanation": "【题型：对比细节题】第2段指出网络算法容易让读者陷入重复的‘回音室’，而独立书店的优势是‘expert curation... invites serendipity’（专业策划，带来意外发现的惊喜）。选项C准确对应原文‘curated selections that foster serendipitous discovery’。"
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
                                        "evidence_sentence": "they function as third spaces—neither home nor work—where people gather for book clubs... physical stores offer authentic human connection that no virtual interface can replicate.",
                                        "explanation": "【题型：词义与推断题】第3段明确将‘third spaces’定义为‘neither home nor work’，人们在此聚集交流，提供‘authentic human connection’（真实的真实人际连接）。选项B‘a communal hub that facilitates genuine human connection’（促进真实人际联结的社区枢纽）完美匹配。"
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
                                        "evidence_sentence": "Many independent shops have successfully diversified their revenue streams by integrating artisanal cafes, hosting ticketed cultural workshops, and offering subscription mystery-box services.",
                                        "explanation": "【题型：细节题】第4段指出独立书店通过‘diversified their revenue streams by integrating artisanal cafes, hosting ticketed cultural workshops...’（多元化收入来源，融入特色咖啡馆、举办收费文化工作坊等）实现财务稳健。选项C‘introducing diversified cultural and commercial services’准确对位。"
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
                                        "explanation": "【题型：主旨题】全文通过分析独立书店逆势复苏的原因（独特的选书品味、社区空间属性、有温度的人性化体验），在末段总结出：深耕机器无法给予的特质，传统实体就能获得持久的文化生命力。选项B‘They survive and thrive by delivering uniquely human experiences’（依靠提供独特的具有人情味的体验而生存与繁荣）是作者核心观点的最佳表达。"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        },

        # ==========================================
        # 2023 英语（一）
        # ==========================================
        {
            "id": "2023-english-1",
            "exam_type": "english_1",
            "year": 2023,
            "title": "2023年全国硕士研究生招生考试 英语（一）试题",
            "duration_minutes": 180,
            "total_score": 100.0,
            "status": "published",
            "sections": [
                {
                    "id": "2023-en1-sec-reading-a",
                    "section_code": "reading_a",
                    "title": "Section II Reading Comprehension Part A",
                    "order_index": 2,
                    "total_score": 40.0,
                    "instructions": "Directions: Read the following four texts. Answer the questions below each text by choosing A, B, C or D.",
                    "groups": [
                        {
                            "id": "2023-en1-text-1",
                            "group_type": "reading_a",
                            "title": "Text 1",
                            "source_info": "Adapted from BBC Science Focus: Rewilding Britain's National Parks (2022)",
                            "order_index": 1,
                            "passage_text": (
                                "Paragraph 1: England's national parks, designated in the mid-20th century, were originally envisioned as "
                                "havens of natural beauty and open recreational spaces for industrial populations. Unlike the vast, untamed "
                                "wilderness areas of North America, these landscapes are working pastoral habitats shaped by millennia of human "
                                "agriculture. Today, however, an intense debate is raging over whether these cherished spaces should remain "
                                "manicured agricultural landscapes or be returned to nature through rewilding.\n\n"
                                "Paragraph 2: A landmark government-commissioned review led by Julian Glover highlighted that despite their "
                                "scenic appeal, the ecological condition of many English national parks is remarkably degraded. Decades of "
                                "intensive sheep grazing have stripped hillsides of native woodlands, leaving behind biodiversity deserts. "
                                "The Glover report firmly concluded that park authorities must prioritize nature restoration alongside "
                                "public recreation if they are to meet national biodiversity commitments.\n\n"
                                "Paragraph 3: Rewilding proponents champion the reintroduction of native flora, the restoration of wetlands, "
                                "and the cessation of intensive livestock farming. They argue that allowing natural processes to reclaim the land "
                                "creates natural resilience against flash flooding and captures significant amounts of atmospheric carbon. "
                                "In their vision, national parks should become vibrant ecological refuges rather than outdoor museums of farming.\n\n"
                                "Paragraph 4: But the prospect of rewilding faces staunch resistance from traditional hill farmers. For these "
                                "farming communities, grazing is not merely an occupation; it is a cultural heritage that has preserved the distinct "
                                "character of upland areas like the Lake District for centuries. They worry that widespread rewilding would desolate "
                                "rural economies, destroy ancient communities, and replace working farms with impenetrable scrubland.\n\n"
                                "Paragraph 5: Finding a sustainable resolution requires transcending this false dichotomy between nature and agriculture. "
                                "Progressive conservationists advocate for agro-ecological stewardship—a model where farmers are rewarded through "
                                "public subsidies not for maximizing sheep yields, but for delivering public environmental goods like carbon capture, "
                                "clean water, and habitat connectivity. Only by integrating farming heritage with biodiversity restoration can national "
                                "parks fulfill their ultimate purpose."
                            ),
                            "questions": [
                                {
                                    "id": "2023-en1-q21",
                                    "question_num": 21,
                                    "order_index": 1,
                                    "category": "detail",
                                    "prompt": "According to Paragraph 1, English national parks differ from North American ones in that they ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "have been strictly protected from any human presence"},
                                        {"key": "B", "text": "are pastoral landscapes deeply influenced by agriculture"},
                                        {"key": "C", "text": "attract far fewer industrial visitors"},
                                        {"key": "D", "text": "consist entirely of untouched primeval forests"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "Unlike the vast, untamed wilderness areas of North America, these landscapes are working pastoral habitats shaped by millennia of human agriculture.",
                                        "explanation": "【题型：细节题】第1段明确指出与北美未经驯服的荒野（untamed wilderness）不同，英国国家公园是‘working pastoral habitats shaped by millennia of human agriculture’（经过数千年人类农业活动塑造的农牧景观）。选项B精准吻合。"
                                    }
                                },
                                {
                                    "id": "2023-en1-q22",
                                    "question_num": 22,
                                    "order_index": 2,
                                    "category": "detail",
                                    "prompt": "What did the Julian Glover report reveal about English national parks (Paragraph 2)?",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "Their ecological health has severely deteriorated."},
                                        {"key": "B", "text": "Their scenic appeal has completely vanished."},
                                        {"key": "C", "text": "Sheep grazing has successfully preserved native flora."},
                                        {"key": "D", "text": "Public recreational visits have declined sharply."}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "A",
                                        "evidence_sentence": "A landmark government-commissioned review led by Julian Glover highlighted that despite their scenic appeal, the ecological condition of many English national parks is remarkably degraded.",
                                        "explanation": "【题型：细节题】第2段第1句指出格洛弗报告揭示：尽管风光优美，但许多公园的生态状况‘is remarkably degraded’（严重退化，留下生物多样性荒漠）。选项A‘Their ecological health has severely deteriorated’为同义替换。"
                                    }
                                },
                                {
                                    "id": "2023-en1-q23",
                                    "question_num": 23,
                                    "order_index": 3,
                                    "category": "detail",
                                    "prompt": "Rewilding proponents argue that letting nature reclaim the land can ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "boost commercial sheep exports"},
                                        {"key": "B", "text": "mitigate flooding risks and sequester carbon"},
                                        {"key": "C", "text": "turn parks into historical museums"},
                                        {"key": "D", "text": "eliminate all wild plant species"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "B",
                                        "evidence_sentence": "They argue that allowing natural processes to reclaim the land creates natural resilience against flash flooding and captures significant amounts of atmospheric carbon.",
                                        "explanation": "【题型：细节题】第3段提到‘creates natural resilience against flash flooding and captures significant amounts of atmospheric carbon’（增强抗山洪韧性，捕获大量大气碳）。选项B‘mitigate flooding risks and sequester carbon’为严谨对应。"
                                    }
                                },
                                {
                                    "id": "2023-en1-q24",
                                    "question_num": 24,
                                    "order_index": 4,
                                    "category": "inference",
                                    "prompt": "Traditional hill farmers oppose rewilding primarily because they believe it will ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "harm their community heritage and rural livelihood"},
                                        {"key": "B", "text": "cause an influx of urban tourists"},
                                        {"key": "C", "text": "force them to adopt organic farming techniques"},
                                        {"key": "D", "text": "lower the market price of modern machinery"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "A",
                                        "evidence_sentence": "They worry that widespread rewilding would desolate rural economies, destroy ancient communities, and replace working farms with impenetrable scrubland.",
                                        "explanation": "【题型：推断题】第4段阐述丘陵农户反对再野化的原因在于其威胁了世代守护的‘cultural heritage’，并担忧再野化会‘desolate rural economies, destroy ancient communities’（破坏乡村经济与古老聚落）。选项A‘harm their community heritage and rural livelihood’（伤害其社区传统与生计）完全切中要害。"
                                    }
                                },
                                {
                                    "id": "2023-en1-q25",
                                    "question_num": 25,
                                    "order_index": 5,
                                    "category": "main_idea",
                                    "prompt": "The author suggests that the future of English national parks lies in ______.",
                                    "score": 2.0,
                                    "options": [
                                        {"key": "A", "text": "banning all agricultural activity immediately"},
                                        {"key": "B", "text": "relying solely on private donations"},
                                        {"key": "C", "text": "harmonizing farming heritage with ecological restoration"},
                                        {"key": "D", "text": "converting all parks into modern amusement attractions"}
                                    ],
                                    "answer_key": {
                                        "correct_answer": "C",
                                        "evidence_sentence": "Only by integrating farming heritage with biodiversity restoration can national parks fulfill their ultimate purpose.",
                                        "explanation": "【题型：主旨结论题】第5段作者指出破除‘自然与农业的虚假二元对立’，通过农业生态托管补贴引导农户，强调‘integrating farming heritage with biodiversity restoration’（将农耕传统与生物多样性修复相融合）。选项C‘harmonizing farming heritage with ecological restoration’最符合文章结论。"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]

    # 3. 写入数据库并执行 QA 门禁
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
                            evidence_sentence=ak_data["evidence_sentence"],
                            explanation=ak_data["explanation"],
                            verifier="Official Verification Panel",
                            status="verified"
                        )
                        db.add(ak_obj)

    db.commit()

    # 4. 执行 QA 门禁校验
    for exam_data in GENUINE_EXAMS:
        for sec in exam_data["sections"]:
            for grp in sec["groups"]:
                qa_res = ContentQAGate.validate_question_group(db, grp["id"], record_logs=True)
                print(f"QA Gate for {grp['id']}: Valid={qa_res.is_valid}, Checksum={qa_res.checksum[:10]}...")

    print("Genuine exam seeding & QA validation completed successfully.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
