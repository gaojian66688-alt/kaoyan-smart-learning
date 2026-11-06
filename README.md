# 考研英语智能学习系统 (Kaoyan English Smart Learning System)

面向中国考研英语（一）、英语（二）备考学生的高性能、模块化全栈智能学习系统。
本系统严格依据《产品需求文档 v1.0》实施，打通**真实试题作答、分层批改、证据化 AI 诊断、FSRS 科学记忆与共享学习档案**全闭环。

---

## 一、系统核心设计原则与架构

1. **真实性与不可篡改 (G01 & G03)**：
   - 题库严格采用真实历年统考真题与官方标准答案版本；
   - 客观题由统一确定性评分内核判定，AI 绝对不参与客观题判分，保证评分可追溯、可审计。
2. **最小完整单元与结构保护 (G02 & PRD 5.2)**：
   - 阅读理解 Part A 严格保持“完整篇章 + 原卷 5 道题目 + 4 个选项 + 原顺序”，绝不跨文拼题或破坏语境。
3. **分层批改一致性 (PRD 8.1 & AT-01)**：
   - 无论是单篇（Unit）、板块（Section）还是整卷（Exam）批改，同一题目基于同一答案版本判定结果 100% 一致。
4. **科学间隔重复 (FSRS v4.5 & PRD 09)**：
   - 采用标准 Free Spaced Repetition Scheduler 算法调度词汇记忆；
   - 阅读中点击单词即时查询义项与音标，一键加入生词本，自动归档真题原句、段落及年份出处；
   - 严格区分“阅读曝光”与“主动回忆”，以 4 档反馈驱动记忆稳定性与难度迭代。
5. **证据化 AI 分析 (PRD 8.3)**：
   - 严格区分“事实（Fact，如用户选择、标准答案、标记生词）”与“推测（Hypothesis，如长难句语法障碍、偷换概念陷阱）”；
   - 每一条推论均有题目、定位句或真实答题行为支撑。

---

## 二、系统技术栈与工程结构

```
kaoyan_smart_learning/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 主入口与静态前端挂载
│   │   ├── config.py                  # 系统配置、FSRS 参数与密钥管理
│   │   ├── database.py                # 统一数据库引擎与 Session 管理
│   │   ├── models/                    # 统一 SQLAlchemy 2.0 数据模型
│   │   │   ├── exam.py                # 试卷、板块、题组 (最小单元)、题目、标准答案、QA日志
│   │   │   ├── practice.py            # 作答会话、草稿快照、提交记录、不可变评分结果
│   │   │   ├── vocabulary.py          # 词库、用户生词本 (FSRS参数)、真题出处、复习日志
│   │   │   ├── mistake.py             # 错题本、错因分类标签、攻克状态
│   │   │   └── user.py                # 用户、共享学习档案、AI 诊断报告记录
│   │   ├── schemas/                   # Pydantic v2 请求与响应数据契约
│   │   ├── core/                      # 核心业务逻辑内核
│   │   │   ├── grading_engine.py      # 客观题统一评分内核 (AT-01)
│   │   │   ├── fsrs_scheduler.py      # FSRS v4.5 记忆调度算法 (AT-08)
│   │   │   ├── qa_gate.py             # 题库发布前质量校验门禁 (AT-09)
│   │   │   └── ai_analyzer.py         # 证据化 AI 学习诊断引擎
│   │   ├── api/                       # RESTful API 路由模块
│   │   │   ├── exams.py               # 题库筛选与获取
│   │   │   ├── practice.py            # 作答会话、草稿自动保存、主动分层提交
│   │   │   ├── vocabulary.py          # 点词查义、加入生词本、FSRS复习队列与反馈
│   │   │   ├── analysis.py            # AI 报告生成与查询
│   │   │   ├── mistakes.py            # 错题本管理与真实错因标记
│   │   │   └── profile.py             # 个人学习档案与今日计划推荐
│   │   └── data/
│   │       └── seed_genuine_exams.py  # 2024/2023 考研真题与 6,588 考研词典导入脚本
│   ├── tests/                         # 自动化测试套件 (11项端到端及验收用例)
│   │   ├── test_fsrs.py               # AT-08: FSRS 状态与四档评分调度测试
│   │   ├── test_qa_gate.py            # AT-09: 资源发布门禁完整性与连续性校验
│   │   ├── test_grading_engine.py     # AT-01: 单篇、板块、整卷一致性评分测试
│   │   ├── test_practice_loop.py      # 完整阅读训练闭环端到端测试
│   │   └── test_api.py                # API 接口集成与模考拦截测试 (AT-05)
│   └── run_server.py                  # 服务端启动脚本
├── frontend/                          # 移动端优先的响应式 Single Page Application
│   ├── index.html                     # 语义化页面结构
│   ├── css/
│   │   └── style.css                  # 现代化设计、左右读答分栏、卡片3D翻转与弹窗
│   └── js/
│       └── app.js                     # 响应式前端控制器 (作答、查词、FSRS、错题、档案)
└── README.md
```

---

## 三、快速启动与开发指南

### 1. 运行环境
- Python 3.10+ (已在 Python 3.14.5 环境测试通过)
- 依赖：`fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`

### 2. 初始化与启动服务
在项目根目录下执行：
```bash
python backend/run_server.py
```
服务将在 `http://127.0.0.1:8000` 启动，浏览器打开该地址即可直接访问完整的移动端适配 Web 前端。

### 3. 运行自动化测试套件
```bash
python -m unittest discover -s backend/tests
```
11 项核心自动化测试全数执行，涵盖：
- `test_at01_consistent_scoring_across_scopes` (AT-01: 跨层级判分绝对一致)
- `test_complete_reading_training_closed_loop` (阅读训练全闭环验证)
- `test_qa_gate_rejects_missing_questions` (AT-09: 缺题拦截门禁)
- `test_strict_mock_mode_blocks_unit_submission` (AT-05: 严格模考模式屏蔽单篇批改)
- `test_initial_review_ratings` & `test_subsequent_recall_and_forget` (AT-08: FSRS 四档调度算法)
- `test_vocab_lookup_from_database` (6,588 条真实考研词库精确检索)

---

## 四、第一阶段（MVP）闭环功能清单

| 模块 | 关键功能与实现 | 对应 PRD 规则 |
|---|---|---|
| **题库系统** | 导入已核验 2024 / 2023 英语（一）与英语（二）真题阅读篇章与 6,588 真实大纲词汇；发布前 SHA-256 门禁校验 | G01, G02, 6.2, AT-09 |
| **作答系统** | 支持专项训练、日常整卷与严格模考；前端实时自动保存草稿；离开与切换不判分 | G04, 7.1, 7.3, AT-04 |
| **评分系统** | 确定性评分内核，单篇/板块/整卷提交逐题得分恒定一致；严格模考拦截单篇批改 | G03, 8.1, AT-01, AT-05 |
| **生词本** | 阅读文本点击单词弹出释义与音标；一键收录生词，自动抓取真题原句与出处；跨真题自动归并去重 | 9.1, 9.2, 9.4, AT-06, AT-07 |
| **FSRS 背词** | 标准 FSRS v4.5 算法驱动；4 档反馈（忘记、困难、记得、轻松）实时推算下次复习日期与记忆稳定性 | 9.3, AT-08 |
| **错题本** | 批改后错题自动收录；完整保留原题上下文与权威解析；支持用户自标真实错因标签 | 10.1 |
| **学习档案** | 记录累计答题数、客观正确率、生词收录数、复习次数与连续学习天数；生成今日推荐计划 | 10.2, 10.3, G08 |
| **AI 诊断** | 证据化分析报告，区分“客观事实”与“推论假说”，高亮题号、定位依据并输出精读建议 | 8.2, 8.3 |
