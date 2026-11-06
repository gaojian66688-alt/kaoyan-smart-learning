// 考研英语智能学习系统前端应用控制器
class KaoyanApp {
  constructor() {
    this.userId = "default_user";
    this.currentExamId = "2024-english-1";
    this.currentGroupId = "2024-en1-text-1";
    this.currentMode = "special_training"; // special_training / practice_full / strict_mock
    this.currentAttemptId = null;
    this.currentGroupData = null;
    this.userAnswers = {}; // { question_id: "A" }
    this.currentActiveWord = null;
    this.currentActiveSentence = "";

    // Timer & Auto-save
    this.timerInterval = null;
    this.timerSeconds = 0;
    this.saveTimeout = null;

    // FSRS Review State
    this.reviewQueue = [];
    this.currentReviewIndex = 0;
    this.isCardFlipped = false;
  }

  async init() {
    this.setupEventListeners();
    await this.loadExams();
    await this.loadGroupData(this.currentGroupId);
    await this.updateDashboard();
  }

  setupEventListeners() {
    const examSelect = document.getElementById("examSelect");
    if (examSelect) {
      examSelect.addEventListener("change", async (e) => {
        this.currentExamId = e.target.value;
        // 自动选择该试卷的第一个阅读篇章
        const targetGroupMap = {
          "2024-english-1": "2024-en1-text-1",
          "2024-english-2": "2024-en2-text-1",
          "2023-english-1": "2023-en1-text-1"
        };
        this.currentGroupId = targetGroupMap[this.currentExamId] || "2024-en1-text-1";
        await this.loadGroupData(this.currentGroupId);
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
      this.currentMode = params.mode;
      const badge = document.getElementById("practiceModeBadge");
      if (badge) {
        badge.innerText = params.mode === "strict_mock" ? "严格整卷模拟" : "专项训练";
      }
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
  // 试卷与阅读作答系统
  // ==================================================

  async loadExams() {
    try {
      const res = await fetch("/api/exams");
      if (res.ok) {
        const exams = await res.json();
        const sel = document.getElementById("examSelect");
        if (sel && exams.length > 0) {
          sel.innerHTML = exams.map(ex => `<option value="${ex.id}">${ex.title}</option>`).join("");
          sel.value = this.currentExamId;
        }
      }
    } catch (e) {
      console.error("Failed to load exams:", e);
    }
  }

  async loadGroupData(groupId) {
    try {
      const res = await fetch(`/api/exams/group/${groupId}`);
      if (!res.ok) return;
      const data = await res.json();
      this.currentGroupData = data;

      document.getElementById("readingTitleBadge").innerText = data.title;
      document.getElementById("passageSource").innerText = data.source_info || "考研英语官方真题";

      this.renderPassage(data.passage_text);
      this.renderQuestions(data.questions);

      // 创建或恢复作答会话
      await this.initPracticeAttempt(groupId);
    } catch (e) {
      console.error("Failed to load group:", e);
    }
  }

  renderPassage(text) {
    const container = document.getElementById("passageContent");
    if (!container) return;

    // 按段落分割
    const paragraphs = text.split("\n\n");
    let html = "";

    paragraphs.forEach((para, pIdx) => {
      const trimmed = para.trim();
      if (!trimmed) return;

      // 段落内单词标记化处理，用于点词查义
      const wordsWithTokens = trimmed.replace(/\b([a-zA-Z]{2,})\b/g, (match) => {
        return `<span class="word-token" data-word="${match.toLowerCase()}" onclick="app.onWordClick(event, '${match}')">${match}</span>`;
      });

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
      const optionsHtml = q.options.map(opt => `
        <div class="option-item ${this.userAnswers[q.id] === opt.key ? 'selected' : ''}"
             data-qid="${q.id}" data-key="${opt.key}"
             onclick="app.selectOption('${q.id}', '${opt.key}')">
          <span class="option-key">${opt.key}.</span>
          <span class="option-text">${opt.text}</span>
        </div>
      `).join("");

      html += `
        <div class="question-card" id="q-card-${q.id}">
          <div class="question-stem">
            <span class="q-num">#${q.question_num}</span>
            <span>${q.prompt}</span>
          </div>
          <div class="options-container">
            ${optionsHtml}
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  async initPracticeAttempt(groupId) {
    try {
      const res = await fetch("/api/practice/attempt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: this.currentMode,
          target_type: "group",
          target_id: groupId,
          user_id: this.userId
        })
      });

      if (res.ok) {
        const att = await res.json();
        this.currentAttemptId = att.id;
        this.userAnswers = att.saved_responses || {};
        this.timerSeconds = att.time_spent_seconds || 0;

        // 恢复选中状态
        for (const [qid, ans] of Object.entries(this.userAnswers)) {
          this.applyOptionVisual(qid, ans);
        }

        this.startTimer();
      }
    } catch (e) {
      console.error("Init attempt error:", e);
    }
  }

  startTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    const display = document.getElementById("timerDisplay");
    this.timerInterval = setInterval(() => {
      this.timerSeconds++;
      const mins = String(Math.floor(this.timerSeconds / 60)).padStart(2, "0");
      const secs = String(this.timerSeconds % 60).padStart(2, "0");
      if (display) display.innerText = `${mins}:${secs}`;
    }, 1000);
  }

  selectOption(questionId, key) {
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
  // 点词查义与加入生词本 (PRD 09)
  // ==================================================

  async onWordClick(event, word) {
    event.stopPropagation();
    this.currentActiveWord = word.toLowerCase();

    // 提取当前点击词所在的句子作为真题原句上下文
    const targetSpan = event.target;
    const parentPara = targetSpan.closest(".passage-paragraph");
    let fullParaText = parentPara ? parentPara.innerText : "";
    
    // 粗略以句号分割取句子
    const sentences = fullParaText.split(/(?<=[.!?])\s+/);
    let matchedSentence = sentences.find(s => s.toLowerCase().includes(this.currentActiveWord)) || fullParaText.slice(0, 100);
    this.currentActiveSentence = matchedSentence.trim();

    const popover = document.getElementById("wordPopover");
    document.getElementById("popoverWord").innerText = this.currentActiveWord;
    document.getElementById("popoverPhonetic").innerText = "/查询中.../";
    document.getElementById("popoverMeaning").innerText = "释义加载中...";
    document.getElementById("popoverSentence").innerText = this.currentActiveSentence;

    // 定位 popover
    const rect = targetSpan.getBoundingClientRect();
    popover.style.top = `${Math.min(window.innerHeight - 200, rect.bottom + window.scrollY + 6)}px`;
    popover.style.left = `${Math.max(10, Math.min(window.innerWidth - 300, rect.left + window.scrollX - 20))}px`;
    popover.classList.remove("hidden");

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
  }

  closeWordPopover() {
    const popover = document.getElementById("wordPopover");
    if (popover) popover.classList.add("hidden");
  }

  async saveCurrentWord() {
    if (!this.currentActiveWord) return;
    const meaning = document.getElementById("popoverMeaning").innerText;
    const source = `${this.currentGroupData?.exam_id || '考研真题'} ${this.currentGroupData?.title || ''}`;

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

        // 高亮文章中所有该词
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
  // 主动提交批改与 AI 证据化诊断 (PRD 08)
  // ==================================================

  async confirmSubmit(scope = "group") {
    // 检查是否有未作答题目
    const totalQuestions = this.currentGroupData?.questions?.length || 5;
    const answeredCount = Object.keys(this.userAnswers).length;
    if (answeredCount < totalQuestions) {
      const proceed = confirm(`当前单元共 ${totalQuestions} 题，您已作答 ${answeredCount} 题。确认提交并锁定答案吗？`);
      if (!proceed) return;
    } else {
      const proceed = confirm("本次提交将锁定当前单元作答并由统一内核评分。确认提交吗？");
      if (!proceed) return;
    }

    try {
      const res = await fetch("/api/practice/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          attempt_id: this.currentAttemptId,
          scope: scope,
          scope_id: this.currentGroupId,
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
    document.getElementById("modalScore").innerText = `${subData.total_score} / ${subData.max_score} 分`;
    document.getElementById("modalAccuracy").innerText = `${subData.accuracy}%`;
    document.getElementById("modalScope").innerText = subData.scope === "group" ? "单篇批改" : "整卷批改";

    // 逐题渲染
    const grid = document.getElementById("modalQuestionsFeedback");
    grid.innerHTML = subData.results.map(r => `
      <div class="result-tag-box ${r.is_correct ? 'correct' : 'wrong'}" onclick="app.highlightEvidence('${r.question_id}')">
        <span class="q-title">#${r.question_num} ${r.is_correct ? '✓ 正确' : '✗ 错误'}</span>
        <span class="ans-info">你的选择: ${r.user_answer || '未答'} | 标准: ${r.correct_answer}</span>
      </div>
    `).join("");

    // 打开模态框
    document.getElementById("gradeModal").classList.remove("hidden");

    // 请求证据化 AI 学习诊断报告
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

  highlightEvidence(questionId) {
    const q = this.currentGroupData?.questions?.find(x => x.id === questionId);
    if (!q) return;
    alert(`定位提示：请查看题 #${q.question_num} 对应的定位句。`);
  }

  closeGradeModal() {
    document.getElementById("gradeModal").classList.add("hidden");
  }

  // ==================================================
  // FSRS 记忆卡片与复习系统 (PRD 09)
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
  // 错题本复盘系统 (PRD 10.1)
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
              <span>你的错误选择: <strong>${m.last_user_answer}</strong></span>
              <span style="color:#16a34a;">官方标准答案: <strong>${m.correct_answer}</strong></span>
            </div>
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
  // 个人学习档案与仪表盘 (PRD 10.2 & 10.3)
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
            <span>📕 阶段二：复盘历史错题与逻辑偏差</span>
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
