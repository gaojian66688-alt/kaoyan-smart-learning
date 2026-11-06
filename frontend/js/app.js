// 考研英语智能学习系统前端应用控制器 v1.1
class KaoyanApp {
  constructor() {
    this.userId = "default_user";
    this.currentExamId = "2024-english-1";
    this.currentGroupId = "2024-en1-text-1";
    this.currentMode = "special_training"; // special_training / practice_full / strict_mock
    this.currentCategoryFilter = "all";
    this.currentAttemptId = null;
    this.currentGroupData = null;
    this.allExamData = null;
    this.userAnswers = {}; // { question_id: "A" 或文本 }
    this.currentActiveWord = null;
    this.currentActiveSentence = "";

    // Timer & Auto-save
    this.timerInterval = null;
    this.timerSeconds = 0; // count-up in training, count-down from 10800 in strict_mock
    this.saveTimeout = null;

    // FSRS Review State
    this.reviewQueue = [];
    this.currentReviewIndex = 0;
    this.isCardFlipped = false;

    // 批改结果字典 (question_id -> GradeResultSchema)，用于逐题渲染解析与展开控制
    this.gradedResultsMap = new Map();
  }

  async init() {
    this.setupEventListeners();
    await this.loadExams();
    await this.updateDashboard();
  }

  setupEventListeners() {
    const examSelect = document.getElementById("examSelect");
    if (examSelect) {
      examSelect.addEventListener("change", async (e) => {
        this.currentExamId = e.target.value;
        this.gradedResultsMap.clear();
        await this.loadExamOutline(this.currentExamId);
      });
    }

    // 点击页面任意外部关闭生词弹窗
    document.addEventListener("click", (e) => {
      const popover = document.getElementById("wordPopover");
      if (popover && !popover.classList.contains("hidden")) {
        if (!popover.contains(e.target) && !e.target.classList.contains("word-token")) {
          this.closeWordPopover();
        }
      }
    });
  }

  switchView(viewId) {
    document.querySelectorAll(".view-panel").forEach(el => el.classList.remove("active"));
    const target = document.getElementById(viewId);
    if (target) target.classList.add("active");

    document.querySelectorAll(".nav-item").forEach(el => {
      if (el.getAttribute("data-view") === viewId) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    });

    if (viewId === "viewHome") {
      this.updateDashboard();
    } else if (viewId === "viewReview") {
      this.loadReviewQueue();
      this.loadAllVocabulary();
    } else if (viewId === "viewMistakes") {
      this.loadMistakes();
    } else if (viewId === "viewProfile") {
      this.loadProfile();
    }
  }

  navTo(viewName, params = {}) {
    if (params.mode) {
      this.switchPracticeMode(params.mode);
    }
    const viewMap = {
      "home": "viewHome",
      "practice": "viewPractice",
      "review": "viewReview",
      "mistakes": "viewMistakes",
      "profile": "viewProfile"
    };
    this.switchView(viewMap[viewName] || "viewHome");
  }

  // ==================================================
  // 模式与板块切换控制 (PRD 5.1 & 7.2)
  // ==================================================

  switchPracticeMode(mode) {
    this.currentMode = mode;
    this.gradedResultsMap.clear();
    document.querySelectorAll(".pill-btn").forEach(btn => {
      if (btn.getAttribute("data-mode") === mode) btn.classList.add("active");
      else btn.classList.remove("active");
    });

    const submitGroupBtn = document.getElementById("btnSubmitGroup");
    const submitExamBtn = document.getElementById("btnSubmitExam");
    const catFilterRow = document.getElementById("categoryFilterRow");
    const tipEl = document.getElementById("passageTip");

    if (mode === "strict_mock") {
      // 严格模考模式：倒计时 180 分钟，屏蔽单篇交卷，屏蔽模考查词辅助
      submitGroupBtn.style.display = "none";
      submitExamBtn.style.display = "inline-block";
      catFilterRow.style.display = "none";
      tipEl.innerText = "⚠️ 严格模拟考试：全真限时180分钟，交卷后统一批改；点击生词仅打标收录，屏蔽即时释义以防辅助。";
      this.startStrictMockTimer();
    } else if (mode === "practice_full") {
      // 日常整卷：保留全题型，单篇与整卷交卷均可用
      submitGroupBtn.style.display = "inline-block";
      submitExamBtn.style.display = "inline-block";
      catFilterRow.style.display = "none";
      tipEl.innerText = "💡 日常整卷模式：支持多板块自由切换作答，支持单篇即时批改或整卷统一交卷。";
      this.startCountupTimer();
    } else {
      // 专项训练：支持题型细分，单篇批改
      submitGroupBtn.style.display = "inline-block";
      submitExamBtn.style.display = "none";
      catFilterRow.style.display = "flex";
      tipEl.innerText = "💡 专项训练模式：点击任意英文单词可即时查词并加入生词本，支持按题型高亮训练。";
      this.startCountupTimer();
    }

    // 重新初始化会话
    this.initPracticeAttempt(this.currentGroupId);
  }

  startCountupTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    document.getElementById("timerLabel").innerText = "作答耗时:";
    this.timerSeconds = 0;
    this.timerInterval = setInterval(() => {
      this.timerSeconds++;
      const mins = String(Math.floor(this.timerSeconds / 60)).padStart(2, "0");
      const secs = String(this.timerSeconds % 60).padStart(2, "0");
      document.getElementById("timerDisplay").innerText = `${mins}:${secs}`;
    }, 1000);
  }

  startStrictMockTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    document.getElementById("timerLabel").innerText = "考试倒计时:";
    this.timerSeconds = 180 * 60; // 180 分钟
    this.timerInterval = setInterval(() => {
      if (this.timerSeconds <= 0) {
        clearInterval(this.timerInterval);
        alert("模考时间到！系统正在自动提交试卷并进行全卷批改...");
        this.confirmSubmit("exam");
        return;
      }
      this.timerSeconds--;
      const hours = String(Math.floor(this.timerSeconds / 3600)).padStart(2, "0");
      const mins = String(Math.floor((this.timerSeconds % 3600) / 60)).padStart(2, "0");
      const secs = String(this.timerSeconds % 60).padStart(2, "0");
      document.getElementById("timerDisplay").innerText = `${hours}:${mins}:${secs}`;
    }, 1000);
  }

  filterCategory(cat) {
    this.currentCategoryFilter = cat;
    document.querySelectorAll(".cat-pill").forEach(el => {
      if (el.getAttribute("data-cat") === cat) el.classList.add("active");
      else el.classList.remove("active");
    });

    // PRD 5.3 & AT-03: 题型筛选不破坏原题上下文，仅高亮目标题目
    if (!this.currentGroupData) return;
    this.renderQuestions(this.currentGroupData.questions);
  }

  // ==================================================
  // 试卷与题组加载
  // ==================================================

  async loadExams() {
    try {
      const res = await fetch("/api/exams");
      if (res.ok) {
        const exams = await res.json();
        const sel = document.getElementById("examSelect");
        if (sel && exams.length > 0) {
          const en1 = exams.filter(e => e.exam_type === "english_1").sort((a, b) => b.year - a.year);
          const en2 = exams.filter(e => e.exam_type === "english_2").sort((a, b) => b.year - a.year);
          let html = "";
          if (en1.length > 0) {
            html += `<optgroup label="📘 考研英语（一）历年真题 (2004–2026)">`;
            html += en1.map(ex => `<option value="${ex.id}">${ex.title}</option>`).join("");
            html += `</optgroup>`;
          }
          if (en2.length > 0) {
            html += `<optgroup label="📙 考研英语（二）历年真题 (2007–2026)">`;
            html += en2.map(ex => `<option value="${ex.id}">${ex.title}</option>`).join("");
            html += `</optgroup>`;
          }
          sel.innerHTML = html;
          // 保持之前选中的考试或默认首张试卷
          if (exams.some(e => e.id === this.currentExamId)) {
            sel.value = this.currentExamId;
          } else {
            this.currentExamId = exams[0].id;
            sel.value = this.currentExamId;
          }
          await this.loadExamOutline(this.currentExamId);
        }
      }
    } catch (e) {
      console.error("Failed to load exams:", e);
    }
  }

  async loadExamOutline(examId) {
    try {
      const res = await fetch("/api/exams");
      if (!res.ok) return;
      const exams = await res.json();
      const currentExam = exams.find(e => e.id === examId) || exams[0];
      this.allExamData = currentExam;

      // 渲染板块与题组导航按钮
      const navContainer = document.getElementById("sectionNavigator");
      let navHtml = "";
      let firstGroupId = null;

      currentExam.sections.forEach(sec => {
        sec.question_groups.forEach(grp => {
          if (!firstGroupId) firstGroupId = grp.id;
          const isAct = (grp.id === this.currentGroupId);
          navHtml += `
            <button class="sec-btn ${isAct ? 'active' : ''}" data-gid="${grp.id}" onclick="app.selectQuestionGroup('${grp.id}')">
              ${sec.title.includes('Reading') ? grp.title : sec.title.split(' ')[1] || grp.title}
            </button>
          `;
        });
      });

      navContainer.innerHTML = navHtml;
      if (firstGroupId && !document.querySelector(`.sec-btn[data-gid="${this.currentGroupId}"]`)) {
        this.currentGroupId = firstGroupId;
      }
      await this.loadGroupData(this.currentGroupId);
    } catch (e) {
      console.error("Load outline error:", e);
    }
  }

  async selectQuestionGroup(groupId) {
    this.currentGroupId = groupId;
    document.querySelectorAll(".sec-btn").forEach(btn => {
      if (btn.getAttribute("data-gid") === groupId) btn.classList.add("active");
      else btn.classList.remove("active");
    });
    await this.loadGroupData(groupId);
  }

  async loadGroupData(groupId) {
    try {
      const res = await fetch(`/api/exams/group/${groupId}`);
      if (!res.ok) return;
      const data = await res.json();
      this.currentGroupData = data;

      document.getElementById("passageSource").innerText = data.source_info || "考研英语官方真题";
      document.getElementById("questionsPanelTitle").innerText = `${data.title} 题目 (共 ${data.questions.length} 题)`;

      // 创建或恢复作答会话
      await this.initPracticeAttempt(groupId);

      this.renderPassage(data.passage_text);
      this.renderQuestions(data.questions);
    } catch (e) {
      console.error("Failed to load group:", e);
    }
  }

  tokenizeWords(text) {
    if (!text) return "";
    return text.replace(/\b([a-zA-Z]{2,})\b/g, (match) => {
      return `<span class="word-token" data-word="${match.toLowerCase()}" onclick="app.onWordClick(event, '${match}')">${match}</span>`;
    });
  }

  renderPassage(text) {
    const container = document.getElementById("passageContent");
    if (!container) return;

    const paragraphs = text.split("\n\n");
    let html = "";

    paragraphs.forEach((para, pIdx) => {
      const trimmed = para.trim();
      if (!trimmed) return;

      const wordsWithTokens = this.tokenizeWords(trimmed);

      html += `<div class="passage-paragraph" data-pid="${pIdx}">
        <span class="para-marker">P${pIdx + 1}</span>${wordsWithTokens}
      </div>`;
    });

    container.innerHTML = html;
  }

  renderQuestions(questions) {
    const container = document.getElementById("questionsList");
    if (!container) return;

    let html = "";
    questions.forEach(q => {
      const isTargetCategory = (this.currentCategoryFilter === "all" || q.category === this.currentCategoryFilter);
      const categoryClass = isTargetCategory ? (this.currentCategoryFilter !== "all" ? "highlighted-target" : "") : "dimmed-non-target";

      const isSubjective = (q.category === "subjective" || !q.options || q.options.length === 0);

      let bodyHtml = "";
      if (isSubjective) {
        // 主观题渲染输入框
        const savedText = this.userAnswers[q.id] || "";
        const wordCount = savedText.trim() ? savedText.trim().split(/\s+/).length : 0;
        bodyHtml = `
          <div class="subjective-textarea-box">
            <textarea class="subjective-textarea" placeholder="在此输入作答内容..."
                      oninput="app.onSubjectiveInput('${q.id}', event)">${savedText}</textarea>
            <span class="word-counter" id="counter-${q.id}">已输入 ${savedText.length} 字 (约 ${wordCount} 词)</span>
          </div>
        `;
      } else {
        // 客观题渲染单选选项（选项中的英文单词与正文一样，可点击即时查词并加入生词本）
        bodyHtml = `<div class="options-container">` +
          q.options.map(opt => `
            <div class="option-item ${this.userAnswers[q.id] === opt.key ? 'selected' : ''}"
                 data-qid="${q.id}" data-key="${opt.key}"
                 onclick="app.selectOption('${q.id}', '${opt.key}')">
              <span class="option-key">${opt.key}.</span>
              <span class="option-text">${this.tokenizeWords(opt.text)}</span>
            </div>
          `).join("") +
        `</div>`;
      }

      html += `
        <div class="question-card ${categoryClass}" id="q-card-${q.id}">
          <div class="question-stem">
            <span class="q-num">#${q.question_num}</span>
            <span>${this.tokenizeWords(q.prompt)}</span>
            <span class="q-badge">${q.category || 'detail'}</span>
          </div>
          ${bodyHtml}
        </div>
      `;
    });

    container.innerHTML = html;
    this.applyGradingToCards();
  }

  onSubjectiveInput(questionId, event) {
    const val = event.target.value;
    this.userAnswers[questionId] = val;
    const counter = document.getElementById(`counter-${questionId}`);
    if (counter) {
      const wordCount = val.trim() ? val.trim().split(/\s+/).length : 0;
      counter.innerText = `已输入 ${val.length} 字 (约 ${wordCount} 词)`;
    }
    this.triggerAutoSave();
  }

  async initPracticeAttempt(groupId) {
    try {
      const res = await fetch("/api/practice/attempt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: this.currentMode,
          target_type: (this.currentMode === "special_training" ? "group" : "exam"),
          target_id: (this.currentMode === "special_training" ? groupId : this.currentExamId),
          user_id: this.userId
        })
      });

      if (res.ok) {
        const att = await res.json();
        this.currentAttemptId = att.id;
        this.userAnswers = { ...(att.saved_responses || {}), ...this.userAnswers };

        // 恢复选中状态
        for (const [qid, ans] of Object.entries(this.userAnswers)) {
          this.applyOptionVisual(qid, ans);
        }
      }
    } catch (e) {
      console.error("Init attempt error:", e);
    }
  }

  selectOption(questionId, key) {
    if (this.gradedResultsMap && this.gradedResultsMap.has(questionId)) {
      return; // 批改后答案锁定
    }
    this.userAnswers[questionId] = key;
    this.applyOptionVisual(questionId, key);
    this.triggerAutoSave();
  }

  applyOptionVisual(questionId, key) {
    const card = document.getElementById(`q-card-${questionId}`);
    if (!card) return;
    card.querySelectorAll(".option-item").forEach(opt => {
      if (opt.getAttribute("data-key") === key) {
        opt.classList.add("selected");
      } else {
        opt.classList.remove("selected");
      }
    });
  }

  triggerAutoSave() {
    const tag = document.getElementById("autoSaveIndicator");
    if (tag) {
      tag.className = "autosave-tag saving";
      tag.querySelector(".text").innerText = "保存中...";
    }

    if (this.saveTimeout) clearTimeout(this.saveTimeout);
    this.saveTimeout = setTimeout(async () => {
      await this.saveResponses();
    }, 500);
  }

  async saveResponses() {
    if (!this.currentAttemptId) return;
    const respList = Object.entries(this.userAnswers).map(([qid, ans]) => ({
      question_id: qid,
      user_answer: ans
    }));

    try {
      const res = await fetch("/api/practice/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          attempt_id: this.currentAttemptId,
          responses: respList,
          time_spent_seconds: this.timerSeconds
        })
      });

      const tag = document.getElementById("autoSaveIndicator");
      if (res.ok && tag) {
        tag.className = "autosave-tag saved";
        tag.querySelector(".text").innerText = "已自动保存";
      }
    } catch (e) {
      console.error("Auto save failed:", e);
    }
  }

  // ==================================================
  // 点词查义与加入生词本 (PRD 9.1: 模考隐藏释义)
  // ==================================================

  async onWordClick(event, word) {
    event.stopPropagation();
    this.currentActiveWord = word.toLowerCase();

    const targetSpan = event.target;
    const parentPara = targetSpan.closest(".passage-paragraph");
    const parentOption = targetSpan.closest(".option-item");
    const parentStem = targetSpan.closest(".question-stem");

    let contextSentence = "";
    if (parentPara) {
      const fullParaText = parentPara.innerText || "";
      const sentences = fullParaText.split(/(?<=[.!?])\s+/);
      const matched = sentences.find(s => s.toLowerCase().includes(this.currentActiveWord));
      contextSentence = (matched || fullParaText.slice(0, 150)).trim();
    } else if (parentOption) {
      const optText = parentOption.querySelector(".option-text")?.innerText || parentOption.innerText || "";
      const qNum = parentOption.closest(".question-card")?.querySelector(".q-num")?.innerText || "";
      const key = parentOption.querySelector(".option-key")?.innerText || "";
      contextSentence = `[${qNum} 选项 ${key}] ${optText.trim()}`;
    } else if (parentStem) {
      contextSentence = `[题干] ${parentStem.innerText.trim()}`;
    } else {
      contextSentence = targetSpan.innerText || "";
    }
    this.currentActiveSentence = contextSentence;

    // PRD 9.1: 严格模考模式下允许标记生词，但默认隐藏释义，以防考试作弊辅助
    const isMock = (this.currentMode === "strict_mock");

    const popover = document.getElementById("wordPopover");
    document.getElementById("popoverWord").innerText = this.currentActiveWord;
    document.getElementById("popoverPhonetic").innerText = isMock ? "/模考状态/" : "/查询中.../";
    document.getElementById("popoverMeaning").innerText = isMock ? "【模考锁定】严格模考进行中，释义与翻译已隐藏。点击下方可标记加入生词本，交卷后进入复习。" : "释义加载中...";
    document.getElementById("popoverSentence").innerText = this.currentActiveSentence;

    const rect = targetSpan.getBoundingClientRect();
    popover.style.top = `${Math.min(window.innerHeight - 200, rect.bottom + window.scrollY + 6)}px`;
    popover.style.left = `${Math.max(10, Math.min(window.innerWidth - 300, rect.left + window.scrollX - 20))}px`;
    popover.classList.remove("hidden");

    if (!isMock) {
      try {
        const res = await fetch(`/api/vocabulary/lookup?word=${encodeURIComponent(this.currentActiveWord)}&user_id=${this.userId}`);
        if (res.ok) {
          const data = await res.json();
          document.getElementById("popoverPhonetic").innerText = data.phonetic ? `/${data.phonetic}/` : "";
          document.getElementById("popoverMeaning").innerText = data.meaning;

          const saveBtn = document.getElementById("btnSaveWord");
          if (data.is_saved) {
            saveBtn.innerText = "✓ 已在生词本";
            saveBtn.disabled = true;
          } else {
            saveBtn.innerText = "+ 加入生词本 (纳入 FSRS)";
            saveBtn.disabled = false;
          }
        }
      } catch (e) {
        console.error("Word lookup error:", e);
      }
    } else {
      const saveBtn = document.getElementById("btnSaveWord");
      saveBtn.innerText = "📌 标记生词 (考后复习)";
      saveBtn.disabled = false;
    }
  }

  closeWordPopover() {
    const popover = document.getElementById("wordPopover");
    if (popover) popover.classList.add("hidden");
  }

  async saveCurrentWord() {
    if (!this.currentActiveWord) return;
    const meaning = document.getElementById("popoverMeaning").innerText;
    let source = `${this.currentGroupData?.exam_id || '考研真题'} ${this.currentGroupData?.title || ''}`;
    if (this.currentActiveSentence.startsWith("[")) {
      const tagEnd = this.currentActiveSentence.indexOf("]");
      if (tagEnd > 0) {
        source += ` (${this.currentActiveSentence.slice(1, tagEnd)})`;
      }
    }

    try {
      const res = await fetch("/api/vocabulary/mark", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          word: this.currentActiveWord,
          context_sentence: this.currentActiveSentence,
          source_info: source,
          group_id: this.currentGroupId,
          definition: meaning,
          user_id: this.userId
        })
      });

      if (res.ok) {
        const saveBtn = document.getElementById("btnSaveWord");
        saveBtn.innerText = "✓ 已成功收录至 FSRS";
        saveBtn.disabled = true;

        document.querySelectorAll(`.word-token[data-word="${this.currentActiveWord}"]`).forEach(el => {
          el.classList.add("saved-word");
        });

        setTimeout(() => this.closeWordPopover(), 1000);
      }
    } catch (e) {
      console.error("Mark word error:", e);
    }
  }

  // ==================================================
  // 主动提交批改与分层评分 (PRD 8.1 & 8.4)
  // ==================================================

  async confirmSubmit(scope = "group") {
    const targetId = (scope === "exam" ? this.currentExamId : this.currentGroupId);
    const scopeName = (scope === "exam" ? "整卷" : "当前单元");

    const proceed = confirm(`本次提交将锁定 ${scopeName} 作答并由统一内核评分。确认提交吗？`);
    if (!proceed) return;

    // 提交前强制刷盘已选答案，防止防抖延迟导致最后一道作答未落库
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
      this.saveTimeout = null;
    }
    await this.saveResponses();

    try {
      const res = await fetch("/api/practice/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          attempt_id: this.currentAttemptId,
          scope: scope,
          scope_id: targetId,
          user_id: this.userId
        })
      });

      if (res.ok) {
        const subData = await res.json();
        this.showGradeResults(subData);
      } else {
        const err = await res.json();
        alert(err.detail || "提交批改失败");
      }
    } catch (e) {
      console.error("Submit error:", e);
    }
  }

  async showGradeResults(subData) {
    if (!this.gradedResultsMap) {
      this.gradedResultsMap = new Map();
    }
    if (subData.results && Array.isArray(subData.results)) {
      subData.results.forEach(r => {
        this.gradedResultsMap.set(r.question_id, r);
      });
    }

    // 立即向题目卡片渲染批改反馈与解析（错题自动展开，正确题提供展开按钮）
    this.applyGradingToCards();

    document.getElementById("modalScore").innerText = `${subData.total_score} / ${subData.max_score} 分`;
    document.getElementById("modalObjScore").innerText = `${subData.objective_score || 0.0} 分`;
    document.getElementById("modalSubjScore").innerText = `${subData.subjective_score || 0.0} 分 (估)`;
    document.getElementById("modalScope").innerText = subData.scope === "group" ? "单篇批改" : (subData.scope === "section" ? "板块批改" : "整卷批改");

    const grid = document.getElementById("modalQuestionsFeedback");
    grid.innerHTML = subData.results.map(r => `
      <div class="result-tag-box ${r.is_correct ? 'correct' : 'wrong'}" onclick="app.jumpToQuestion('${r.question_id}')" title="点击定位至该题及详细解析">
        <span class="q-title">#${r.question_num} ${r.is_correct ? '✓ 达标' : '✗ 失分'}</span>
        <span class="ans-info">${r.is_estimated ? (r.score_band || '已估分') : `得分: ${r.score}/${r.max_score}分`}</span>
        <span style="font-size:11px;color:#64748b;display:block;margin-top:4px;">${r.is_correct ? '查看解析 🔍' : '查看错因 🔍'}</span>
      </div>
    `).join("");

    document.getElementById("gradeModal").classList.remove("hidden");

    try {
      const aiRes = await fetch(`/api/analysis/generate/${subData.id}?user_id=${this.userId}`, { method: "POST" });
      if (aiRes.ok) {
        const aiData = await aiRes.json();
        document.getElementById("modalAiSummary").innerText = aiData.summary;

        const evContainer = document.getElementById("modalAiEvidences");
        evContainer.innerHTML = aiData.evidence_items.map(item => `
          <div class="evidence-card-item">
            <div class="ev-fact">${item.fact}</div>
            ${item.evidence_quote ? `<span class="ev-quote">📌 定位依据：${item.evidence_quote}</span>` : ''}
            <div class="ev-hypothesis">💡 诊断推断：${item.hypothesis}</div>
          </div>
        `).join("");

        const recContainer = document.getElementById("modalAiRecs");
        recContainer.innerHTML = `<h5 style="margin-bottom:6px;font-size:13px;">🎯 精读提升建议：</h5>` +
          aiData.recommendations.map(rc => `<p style="font-size:12px;color:#334155;margin-bottom:4px;">• ${rc}</p>`).join("");
      }
    } catch (e) {
      console.error("AI report error:", e);
    }
  }

  // PRD 8.1 & 8.4: 题目批改后状态与解析渲染
  // 核心规则：错误的要有解析（默认展开），正确的可以让用户自己点开查看（默认折叠提供按钮）
  // 答案、解析与题目一一对应，题目完全干净，无水印或无关串入
  applyGradingToCards() {
    if (!this.gradedResultsMap || this.gradedResultsMap.size === 0) return;

    for (const [qid, r] of this.gradedResultsMap.entries()) {
      const card = document.getElementById(`q-card-${qid}`);
      if (!card) continue;

      // 移除原有的批改反馈容器以防重复
      const oldBox = card.querySelector(".q-graded-box");
      if (oldBox) oldBox.remove();

      // 更新选项样式及指示标注
      const options = card.querySelectorAll(".option-item");
      options.forEach(opt => {
        opt.classList.remove("selected", "correct-opt", "wrong-opt", "target-opt");
        const existingBadge = opt.querySelector(".opt-tag-badge");
        if (existingBadge) existingBadge.remove();

        const optKey = opt.getAttribute("data-key");
        if (r.is_correct) {
          if (optKey === r.user_answer) {
            opt.classList.add("correct-opt");
            const badge = document.createElement("span");
            badge.className = "opt-tag-badge badge-success";
            badge.innerText = "✓ 您的正确作答";
            opt.appendChild(badge);
          }
        } else {
          if (optKey === r.user_answer) {
            opt.classList.add("wrong-opt");
            const badge = document.createElement("span");
            badge.className = "opt-tag-badge badge-danger";
            badge.innerText = "✗ 您的选择";
            opt.appendChild(badge);
          }
          if (optKey === r.correct_answer) {
            opt.classList.add("target-opt");
            const badge = document.createElement("span");
            badge.className = "opt-tag-badge badge-target";
            badge.innerText = "★ 标准答案";
            opt.appendChild(badge);
          }
        }
      });

      // 主观题文本域只读
      const textarea = card.querySelector(".subjective-textarea");
      if (textarea) {
        textarea.readOnly = true;
        textarea.style.backgroundColor = "#f8fafc";
      }

      // 构建逐题解析容器 (错误自动展开，正确默认折叠并提供展开按钮)
      const isSubjective = Boolean(r.is_estimated);
      let headerHtml = "";
      let contentHtml = "";

      if (isSubjective) {
        headerHtml = `
          <div class="q-grade-header subjective">
            <div class="header-left">
              <span class="status-badge badge-subjective">📝 AI 辅助估分</span>
              <span class="ans-summary">等第：<strong>${r.score_band || '已评分'}</strong> | 估分：<strong>${r.score} / ${r.max_score}</strong> 分 (估)</span>
            </div>
            <button class="btn-toggle-exp btn-toggle-subjective" onclick="app.toggleQuestionExp('${qid}')" id="btn-toggle-${qid}">${r.is_correct ? '查看解析与范文 ▼' : '收起解析与范文 ▲'}</button>
          </div>
        `;
        contentHtml = `
          <div class="q-exp-content ${r.is_correct ? 'collapsed' : 'expanded'}" id="exp-card-${qid}">
            <div class="exp-section">
              <div class="exp-section-title">🎯 评分诊断与反馈</div>
              <div class="exp-section-body">${(r.explanation || '').replace(/\n/g, '<br/>')}</div>
            </div>
            ${r.correct_answer ? `
              <div class="exp-section">
                <div class="exp-section-title">📑 官方标准译文 / 经典参考范文</div>
                <div class="exp-section-body model-writing-box">${r.correct_answer.replace(/\n/g, '<br/>')}</div>
              </div>
            ` : ''}
          </div>
        `;
      } else if (!r.is_correct) {
        // 错误题目：自动展开解析
        headerHtml = `
          <div class="q-grade-header wrong">
            <div class="header-left">
              <span class="status-badge badge-wrong">❌ 回答错误</span>
              <span class="ans-summary">您的作答：<strong>${r.user_answer || '未作答'}</strong> | 标准答案：<strong class="text-success">${r.correct_answer}</strong> | 得分：<strong>0 / ${r.max_score}</strong> 分</span>
            </div>
            <button class="btn-toggle-exp btn-toggle-wrong" onclick="app.toggleQuestionExp('${qid}')" id="btn-toggle-${qid}">收起解析 ▲</button>
          </div>
        `;
        contentHtml = `
          <div class="q-exp-content expanded" id="exp-card-${qid}">
            ${r.evidence_sentence ? `
              <div class="exp-section">
                <div class="exp-section-title">📌 真题定位依据</div>
                <div class="exp-section-body evidence-quote">${this.tokenizeWords(r.evidence_sentence)}</div>
              </div>
            ` : ''}
            <div class="exp-section">
              <div class="exp-section-title">💡 权威解析</div>
              <div class="exp-section-body">${(r.explanation || '暂无详细解析').replace(/\n/g, '<br/>')}</div>
            </div>
          </div>
        `;
      } else {
        // 正确题目：默认折叠，提供按钮由用户点开查看
        headerHtml = `
          <div class="q-grade-header correct">
            <div class="header-left">
              <span class="status-badge badge-correct">✅ 回答正确</span>
              <span class="ans-summary">您的作答：<strong>${r.user_answer}</strong> | 标准答案：<strong class="text-success">${r.correct_answer}</strong> | 得分：<strong>${r.score} / ${r.max_score}</strong> 分</span>
            </div>
            <button class="btn-toggle-exp btn-toggle-correct" onclick="app.toggleQuestionExp('${qid}')" id="btn-toggle-${qid}">查看解析 ▼</button>
          </div>
        `;
        contentHtml = `
          <div class="q-exp-content collapsed" id="exp-card-${qid}">
            ${r.evidence_sentence ? `
              <div class="exp-section">
                <div class="exp-section-title">📌 真题定位依据</div>
                <div class="exp-section-body evidence-quote">${this.tokenizeWords(r.evidence_sentence)}</div>
              </div>
            ` : ''}
            <div class="exp-section">
              <div class="exp-section-title">💡 权威解析</div>
              <div class="exp-section-body">${(r.explanation || '暂无详细解析').replace(/\n/g, '<br/>')}</div>
            </div>
          </div>
        `;
      }

      const gradedBox = document.createElement("div");
      gradedBox.className = "q-graded-box";
      gradedBox.innerHTML = headerHtml + contentHtml;
      card.appendChild(gradedBox);
    }
  }

  toggleQuestionExp(questionId) {
    const card = document.getElementById(`exp-card-${questionId}`);
    const btn = document.getElementById(`btn-toggle-${questionId}`);
    if (!card || !btn) return;

    const isCollapsed = card.classList.contains("collapsed");
    if (isCollapsed) {
      card.classList.remove("collapsed");
      card.classList.add("expanded");
      if (btn.classList.contains("btn-toggle-correct")) {
        btn.innerText = "收起解析 ▲";
      } else if (btn.classList.contains("btn-toggle-subjective")) {
        btn.innerText = "收起解析与范文 ▲";
      } else {
        btn.innerText = "收起解析 ▲";
      }
    } else {
      card.classList.remove("expanded");
      card.classList.add("collapsed");
      if (btn.classList.contains("btn-toggle-correct")) {
        btn.innerText = "查看解析 ▼";
      } else if (btn.classList.contains("btn-toggle-subjective")) {
        btn.innerText = "查看解析与范文 ▼";
      } else {
        btn.innerText = "查看解析 ▼";
      }
    }
  }

  async jumpToQuestion(questionId) {
    this.closeGradeModal();
    let targetCard = document.getElementById(`q-card-${questionId}`);
    if (!targetCard && this.allExamData) {
      const currentExam = this.allExamData.find(e => e.id === this.currentExamId);
      if (currentExam && currentExam.sections) {
        for (const sec of currentExam.sections) {
          for (const grp of sec.question_groups) {
            if (grp.id.includes(questionId) || (grp.questions && grp.questions.some(q => q.id === questionId))) {
              await this.selectQuestionGroup(grp.id);
              targetCard = document.getElementById(`q-card-${questionId}`);
              break;
            }
          }
          if (targetCard) break;
        }
      }
    }
    if (targetCard) {
      targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
      targetCard.classList.add("q-card-pulse");
      setTimeout(() => targetCard.classList.remove("q-card-pulse"), 2000);
    }
  }

  closeGradeModal() {
    document.getElementById("gradeModal").classList.add("hidden");
  }

  // ==================================================
  // FSRS 记忆卡片与双向回跳 (PRD 9.2 & 二.3)
  // ==================================================

  async loadReviewQueue() {
    try {
      const res = await fetch(`/api/vocabulary/review-queue?user_id=${this.userId}`);
      if (res.ok) {
        this.reviewQueue = await res.json();
        this.currentReviewIndex = 0;
        this.renderCurrentReviewCard();
      }
    } catch (e) {
      console.error("Load review queue error:", e);
    }
  }

  renderCurrentReviewCard() {
    const cardEl = document.getElementById("flashcard");
    const countEl = document.getElementById("reviewQueueCount");
    const btnGroup = document.getElementById("fsrsBtnGroup");

    this.isCardFlipped = false;
    cardEl.classList.remove("flipped");

    if (!this.reviewQueue || this.reviewQueue.length === 0 || this.currentReviewIndex >= this.reviewQueue.length) {
      countEl.innerText = "今日复习已全部完成！🎉";
      document.getElementById("cardWord").innerText = "恭喜！";
      document.getElementById("cardPhonetic").innerText = "今日任务达成";
      document.querySelector(".card-hint").innerText = "当前没有到期需要复习的真题生词";
      btnGroup.style.display = "none";
      return;
    }

    btnGroup.style.display = "grid";
    const item = this.reviewQueue[this.currentReviewIndex];
    countEl.innerText = `待复习：第 ${this.currentReviewIndex + 1} / ${this.reviewQueue.length} 词`;

    document.getElementById("cardWord").innerText = item.word;
    document.getElementById("cardPhonetic").innerText = item.phonetic ? `/${item.phonetic}/` : "";
    document.getElementById("cardDefinition").innerText = item.definition;

    const occ = item.occurrences && item.occurrences.length > 0 ? item.occurrences[0] : null;
    document.getElementById("cardSentence").innerText = occ ? occ.context_sentence : "暂无例句";
    document.getElementById("cardSource").innerText = occ ? occ.source_info : "真题来源";

    document.getElementById("cardFsrsInfo").innerText = 
      `累计复习: ${item.reps} 次 | 记忆稳定性 S: ${item.stability.toFixed(2)} | 难度 D: ${item.difficulty.toFixed(2)}`;
  }

  flipCard() {
    const cardEl = document.getElementById("flashcard");
    this.isCardFlipped = !this.isCardFlipped;
    if (this.isCardFlipped) {
      cardEl.classList.add("flipped");
    } else {
      cardEl.classList.remove("flipped");
    }
  }

  // PRD 二.3: 背词时支持回跳原阅读文章查看语境
  async jumpToOriginalReading() {
    if (!this.reviewQueue || this.currentReviewIndex >= this.reviewQueue.length) return;
    const item = this.reviewQueue[this.currentReviewIndex];
    const occ = item.occurrences && item.occurrences.length > 0 ? item.occurrences[0] : null;

    if (!occ || !occ.group_id) {
      alert("未找到该词对应的原阅读文章 ID");
      return;
    }

    // 切换至练习视图
    this.switchView("viewPractice");
    await this.selectQuestionGroup(occ.group_id);

    // 平滑滚动并高亮该单词
    setTimeout(() => {
      const wordToken = document.querySelector(`.word-token[data-word="${item.word}"]`);
      if (wordToken) {
        wordToken.scrollIntoView({ behavior: "smooth", block: "center" });
        wordToken.classList.add("target-highlight");
      }
    }, 400);
  }

  async submitFsrsRating(rating) {
    if (!this.reviewQueue || this.currentReviewIndex >= this.reviewQueue.length) return;
    const item = this.reviewQueue[this.currentReviewIndex];

    try {
      const res = await fetch("/api/vocabulary/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vocab_id: item.id,
          rating: rating,
          user_id: this.userId
        })
      });

      if (res.ok) {
        this.currentReviewIndex++;
        this.renderCurrentReviewCard();
      }
    } catch (e) {
      console.error("FSRS feedback error:", e);
    }
  }

  async loadAllVocabulary() {
    try {
      const res = await fetch(`/api/vocabulary/list?user_id=${this.userId}`);
      if (res.ok) {
        const list = await res.json();
        document.getElementById("totalVocabCount").innerText = list.length;
        const table = document.getElementById("vocabTable");
        table.innerHTML = list.map(v => `
          <div class="vocab-row">
            <span class="w-col">${v.word}</span>
            <span class="m-col">${v.definition}</span>
            <span class="s-col">真题曝光 ${v.occurrence_count} 次 · 间隔 ${(v.stability || 1).toFixed(1)} 天</span>
          </div>
        `).join("");
      }
    } catch (e) {
      console.error("Load all vocab error:", e);
    }
  }

  // ==================================================
  // 错题本复盘与长难句结构拆解 (PRD 10.1 & 二.4)
  // ==================================================

  async loadMistakes() {
    try {
      const res = await fetch(`/api/mistakes?user_id=${this.userId}`);
      if (res.ok) {
        const mistakes = await res.json();
        const container = document.getElementById("mistakesListContainer");
        if (mistakes.length === 0) {
          container.innerHTML = `<div style="text-align:center;padding:40px;color:#64748b;">太棒了！错题本为空，继续保持！</div>`;
          return;
        }

        container.innerHTML = mistakes.map(m => `
          <div class="mistake-card" id="mistake-card-${m.id}">
            <div class="mistake-header-row">
              <span class="mode-badge">题号 #${m.question_num} (${m.group_title})</span>
              <span style="font-size:12px;color:#dc2626;font-weight:600;">失分累计: ${m.wrong_count} 次</span>
            </div>
            <div class="mistake-passage-preview">
              <strong>所属原文背景：</strong>${m.passage_text.slice(0, 240)}...
            </div>
            <div class="mistake-prompt">${m.prompt}</div>
            <div class="mistake-answers-bar">
              <span>你的错误选择: <strong>${m.last_user_answer || '未作答'}</strong></span>
              <span style="color:#16a34a;">官方标准答案: <strong>${m.correct_answer}</strong></span>
            </div>
            ${m.syntax_analysis ? `<div class="syntax-box">📐 <strong>长难句语法结构剖析：</strong>${m.syntax_analysis}</div>` : ''}
            ${m.detected_vocabulary_gaps && m.detected_vocabulary_gaps.length > 0 ? `
              <div class="vocab-gaps-box">⚠️ <strong>检出相关词汇盲区：</strong>${m.detected_vocabulary_gaps.join(", ")}（建议在 FSRS 中优先复习）</div>
            ` : ''}
            <div class="mistake-explanation-box">
              <strong>权威解析与定位句：</strong>${m.explanation}
            </div>
            <div class="mistake-tags-row">
              <span style="font-size:12px;font-weight:600;">标定真实错因：</span>
              ${['词汇障碍', '长难句语法偏差', '偷换概念陷阱', '反向推导', '粗心漏看'].map(tag => `
                <span class="reason-tag ${m.user_reason_tag === tag ? 'active' : ''}"
                      onclick="app.tagMistake('${m.id}', '${tag}')">${tag}</span>
              `).join("")}
            </div>
          </div>
        `).join("");
      }
    } catch (e) {
      console.error("Load mistakes error:", e);
    }
  }

  async tagMistake(mistakeId, tag) {
    try {
      const res = await fetch(`/api/mistakes/${mistakeId}/tag`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tag: tag })
      });
      if (res.ok) {
        const card = document.getElementById(`mistake-card-${mistakeId}`);
        if (card) {
          card.querySelectorAll(".reason-tag").forEach(el => {
            if (el.innerText === tag) el.classList.add("active");
            else el.classList.remove("active");
          });
        }
      }
    } catch (e) {
      console.error("Tag mistake error:", e);
    }
  }

  // ==================================================
  // 个人学习档案与今日计划 (PRD 10.2 & 10.3)
  // ==================================================

  async updateDashboard() {
    try {
      const res = await fetch(`/api/profile?user_id=${this.userId}`);
      if (res.ok) {
        const p = await res.json();
        document.getElementById("homeTotalDone").innerText = p.total_questions_attempted;
        document.getElementById("homeAccuracy").innerText = `${p.overall_accuracy}%`;
        document.getElementById("homeStreak").innerText = p.consecutive_study_days;
      }

      const planRes = await fetch(`/api/profile/today-plan?user_id=${this.userId}`);
      if (planRes.ok) {
        const plan = await planRes.json();
        document.getElementById("homeDueReviews").innerText = plan.due_reviews_count;
      }
    } catch (e) {
      console.error("Update dashboard error:", e);
    }
  }

  exportVocab(format) {
    window.open(`/api/vocabulary/export?user_id=${this.userId}&format=${format}`, "_blank");
  }

  exportMistakes(format) {
    window.open(`/api/mistakes/export?user_id=${this.userId}&format=${format}`, "_blank");
  }

  async loadProfile() {
    try {
      const res = await fetch(`/api/profile?user_id=${this.userId}`);
      if (res.ok) {
        const p = await res.json();
        document.getElementById("profTotalQuestions").innerText = p.total_questions_attempted;
        document.getElementById("profAccuracy").innerText = `${p.overall_accuracy}%`;
        document.getElementById("profTotalWords").innerText = p.total_vocabulary_marked;
        document.getElementById("profTotalReviews").innerText = p.total_reviews_completed;
      }

      // 加载趋势与细分画像数据
      const trendsRes = await fetch(`/api/profile/trends?user_id=${this.userId}`);
      if (trendsRes.ok) {
        const trends = await trendsRes.json();
        
        // 渲染题型正确率进度条
        const catContainer = document.getElementById("categoryBarsContainer");
        if (catContainer && trends.category_accuracy) {
          catContainer.innerHTML = trends.category_accuracy.map(c => `
            <div class="category-bar-row">
              <div class="category-bar-info">
                <span><strong>${c.category_name}</strong> (${c.correct}/${c.total}题)</span>
                <span class="${c.accuracy >= 80 ? 'text-success' : (c.accuracy < 60 && c.total > 0 ? 'text-warning' : '')}">${c.accuracy}%</span>
              </div>
              <div class="category-bar-bg">
                <div class="category-bar-fill" style="width: ${c.total > 0 ? c.accuracy : 0}%; background: ${c.accuracy >= 80 ? 'var(--success)' : (c.accuracy < 60 ? 'var(--warning)' : 'var(--primary)')}"></div>
              </div>
            </div>
          `).join("");
        }

        // 渲染 FSRS 状态周期网格与留存率
        const retEl = document.getElementById("fsrsRetentionRate");
        if (retEl) retEl.innerText = `${trends.retention_rate}%`;

        const cycleGrid = document.getElementById("vocabCycleGrid");
        if (cycleGrid && trends.vocab_distribution) {
          const vd = trends.vocab_distribution;
          cycleGrid.innerHTML = `
            <div class="cycle-box">
              <div class="cycle-val">${vd.new_words}</div>
              <div class="cycle-lbl">新收录</div>
            </div>
            <div class="cycle-box">
              <div class="cycle-val text-primary">${vd.learning}</div>
              <div class="cycle-lbl">初期巩固</div>
            </div>
            <div class="cycle-box">
              <div class="cycle-val text-warning">${vd.review}</div>
              <div class="cycle-lbl">复习周期中</div>
            </div>
            <div class="cycle-box">
              <div class="cycle-val text-success">${vd.mastered}</div>
              <div class="cycle-lbl">已深度掌握</div>
            </div>
            <div class="cycle-box">
              <div class="cycle-val text-danger">${vd.relearning}</div>
              <div class="cycle-lbl">遗忘重学</div>
            </div>
            <div class="cycle-box">
              <div class="cycle-val">${vd.total}</div>
              <div class="cycle-lbl">生词总量</div>
            </div>
          `;
        }

        // 渲染 AI 诊断列表
        const diagList = document.getElementById("diagnosticList");
        if (diagList) {
          const diagItems = [];
          if (trends.weak_points && trends.weak_points.length) {
            trends.weak_points.forEach(wp => diagItems.push(`<li>⚠️ ${wp}</li>`));
          }
          if (trends.strengths && trends.strengths.length) {
            trends.strengths.forEach(st => diagItems.push(`<li>✅ ${st}</li>`));
          }
          diagList.innerHTML = diagItems.join("");
        }
      }

      const planRes = await fetch(`/api/profile/today-plan?user_id=${this.userId}`);
      if (planRes.ok) {
        const plan = await planRes.json();
        const list = document.getElementById("planStepsList");
        list.innerHTML = `
          <li class="plan-step-item">
            <span>🧠 阶段一：完成今日到期 FSRS 单词复习</span>
            <span class="mode-badge">${plan.due_reviews_count} 词待复习</span>
          </li>
          <li class="plan-step-item">
            <span>📕 阶段二：复盘历史错题与长难句结构</span>
            <span class="mode-badge">${plan.unconsolidated_mistakes_count} 道错题未攻克</span>
          </li>
          <li class="plan-step-item">
            <span>🎯 阶段三：今日推荐真题专项精读训练</span>
            <button class="btn btn-sm btn-primary" onclick="app.navTo('practice')">开始练习</button>
          </li>
        `;
      }
    } catch (e) {
      console.error("Load profile error:", e);
    }
  }
}

// 实例化应用
const app = new KaoyanApp();
window.app = app;
window.addEventListener("DOMContentLoaded", () => app.init());
