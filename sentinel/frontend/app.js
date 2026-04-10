/* ═══════════════════════════════════════════════════════════════════
   SENTINEL — Frontend Application Logic
   AI for Detecting Manipulative Digital Content
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  // ─── Sample Content ──────────────────────────────────────────────

  const SAMPLES = {
    fear: `URGENT: Scientists confirm new pathogen spreading in major cities — government hiding the real death toll. Your family is at risk RIGHT NOW. Share before they take this down. The media won't tell you this but thousands are already dying. Stock up on food and water immediately. Do NOT trust the official numbers.`,

    consensus: `Everyone is switching to [Product X] — 9 out of 10 experts agree it's the only safe choice left. Millions have already made the switch. Are you still using the dangerous old alternative? Join the movement that's sweeping the nation. Don't be left behind while everyone else protects their family.`,

    clean: `The city council voted 7-2 yesterday to approve the new public transit expansion. The project adds 12 new bus routes and extends the metro line by 8km, beginning construction in Q2 next year. Funding comes from federal grants and municipal bonds. Critics raised concerns about construction disruption to local businesses.`,
  };

  // ─── State ───────────────────────────────────────────────────────

  let currentMode = "text"; // "text" | "url"
  let isAnalyzing = false;
  let lastReport = null;

  // ─── DOM References ──────────────────────────────────────────────

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const els = {
    // Nav
    navLinks: $$(".nav-link, .nav-link-inline"),
    sections: $$(".section"),
    navStatus: $("#nav-status"),

    // Input
    modeToggle: $("#mode-toggle"),
    modeBtns: $$(".mode-btn"),
    inputTextMode: $("#input-text-mode"),
    inputUrlMode: $("#input-url-mode"),
    textarea: $("#input-textarea"),
    charCount: $("#char-count"),
    urlInput: $("#input-url"),
    sampleBtns: $$(".sample-btn"),
    analyzeBtn: $("#btn-analyze"),
    analyzeBtnText: $("#analyze-btn-text"),
    analyzeBtnLoader: $("#analyze-btn-loader"),

    // Results
    resultsPanel: $("#results-panel"),
    riskScoreNumber: $("#risk-score-number"),
    riskBadge: $("#risk-badge"),
    riskVerdict: $("#risk-verdict"),
    riskBarFill: $("#risk-bar-fill"),
    metadataCard: $("#metadata-card"),
    metadataStrip: $("#metadata-strip"),
    techniquesGrid: $("#techniques-grid"),
    psychContent: $("#psych-content"),
    actionContent: $("#action-content"),
    summaryContent: $("#summary-content"),

    // History
    historyEmpty: $("#history-empty"),
    historyTable: $("#history-table"),
    historyTbody: $("#history-tbody"),

    // Stats
    statTotal: $("#stat-total"),
    statAvg: $("#stat-avg"),
    statHigh: $("#stat-high"),
    statTechnique: $("#stat-technique"),
  };

  // ─── Error Toast ─────────────────────────────────────────────────

  let toastEl = null;
  let toastTimer = null;

  function createToast() {
    toastEl = document.createElement("div");
    toastEl.className = "error-toast";
    toastEl.id = "error-toast";
    document.body.appendChild(toastEl);
  }

  function showError(message) {
    if (!toastEl) createToast();
    toastEl.textContent = message;
    toastEl.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastEl.classList.remove("visible");
    }, 5000);
  }

  // ─── Navigation ──────────────────────────────────────────────────

  function switchSection(sectionName) {
    els.sections.forEach((s) => {
      s.classList.remove("active");
      s.classList.add("hidden");
    });

    const target = $(`#section-${sectionName}`);
    if (target) {
      target.classList.remove("hidden");
      target.classList.add("active");
    }

    $$(".nav-link").forEach((link) => {
      link.classList.toggle(
        "active",
        link.getAttribute("data-section") === sectionName
      );
    });

    // Refresh history/stats when switching to history
    if (sectionName === "history") {
      loadHistory();
      loadStats();
    }
  }

  function initNav() {
    document.addEventListener("click", (e) => {
      const link = e.target.closest("[data-section]");
      if (link) {
        e.preventDefault();
        switchSection(link.getAttribute("data-section"));
      }
    });

    // Logo click goes to analyze
    $("#nav-logo").addEventListener("click", (e) => {
      e.preventDefault();
      switchSection("analyze");
    });
  }

  // ─── Mode Toggle ────────────────────────────────────────────────

  function initModeToggle() {
    els.modeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.getAttribute("data-mode");
        currentMode = mode;

        els.modeBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        if (mode === "text") {
          els.inputTextMode.classList.remove("hidden");
          els.inputUrlMode.classList.add("hidden");
        } else {
          els.inputTextMode.classList.add("hidden");
          els.inputUrlMode.classList.remove("hidden");
        }
      });
    });
  }

  // ─── Character Count ────────────────────────────────────────────

  function initCharCount() {
    els.textarea.addEventListener("input", () => {
      els.charCount.textContent = els.textarea.value.length.toLocaleString();
    });
  }

  // ─── Sample Buttons ─────────────────────────────────────────────

  function initSamples() {
    els.sampleBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-sample");
        const text = SAMPLES[key];
        if (text) {
          els.textarea.value = text;
          els.charCount.textContent = text.length.toLocaleString();
          els.textarea.focus();
        }
      });
    });
  }

  // ─── Keyboard Shortcut ──────────────────────────────────────────

  function initKeyboard() {
    document.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        if (!isAnalyzing) {
          runAnalysis();
        }
      }
    });
  }

  // ─── Analysis ────────────────────────────────────────────────────

  async function runAnalysis() {
    if (isAnalyzing) return;

    let endpoint, payload;

    if (currentMode === "text") {
      const content = els.textarea.value.trim();
      if (!content) {
        showError("Please paste some content to analyze.");
        els.textarea.focus();
        return;
      }
      if (content.length < 10) {
        showError("Content too short. Please provide at least 10 characters.");
        els.textarea.focus();
        return;
      }
      endpoint = "/api/analyze/text";
      payload = { content };
    } else {
      const url = els.urlInput.value.trim();
      if (!url) {
        showError("Please enter a URL to analyze.");
        els.urlInput.focus();
        return;
      }
      endpoint = "/api/analyze/url";
      payload = { url };
    }

    setLoading(true);

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `Server error (${res.status})`);
      }

      const report = await res.json();
      lastReport = report;
      renderResults(report);
    } catch (err) {
      showError(err.message || "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function setLoading(loading) {
    isAnalyzing = loading;
    els.analyzeBtn.disabled = loading;
    els.analyzeBtnText.classList.toggle("hidden", loading);
    els.analyzeBtnLoader.classList.toggle("hidden", !loading);
  }

  function initAnalyzeBtn() {
    els.analyzeBtn.addEventListener("click", () => {
      if (!isAnalyzing) runAnalysis();
    });
  }

  // ─── Render Results ──────────────────────────────────────────────

  function renderResults(report) {
    // Show panel
    els.resultsPanel.classList.remove("hidden");

    // Scroll to results
    setTimeout(() => {
      els.resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);

    // Risk meter
    renderRiskMeter(report);

    // Metadata (URL only)
    renderMetadata(report);

    // Techniques
    renderTechniques(report);

    // Psych profile
    els.psychContent.textContent =
      report.psychological_target || "No specific psychological targeting identified.";

    // Action
    renderAction(report);

    // Summary
    els.summaryContent.textContent =
      report.summary || "No summary available.";
  }

  function renderRiskMeter(report) {
    const score = report.risk_score || 0;
    const level = (report.risk_level || "LOW").toLowerCase();

    // Animate score number
    animateNumber(els.riskScoreNumber, score);

    // Badge
    els.riskBadge.textContent = report.risk_level || "LOW";
    els.riskBadge.className = "risk-badge " + level;

    // Verdict
    els.riskVerdict.textContent = report.verdict || "";

    // Bar — reset first, then animate
    els.riskBarFill.style.width = "0%";
    els.riskBarFill.className = "risk-bar-fill " + level;

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        els.riskBarFill.style.width = score + "%";
      });
    });
  }

  function animateNumber(el, target) {
    const duration = 800;
    const start = performance.now();
    const from = 0;

    function tick(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(from + (target - from) * eased);
      el.textContent = current;
      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    }

    requestAnimationFrame(tick);
  }

  function renderMetadata(report) {
    if (report.content_type !== "url" || !report.scraped_metadata) {
      els.metadataCard.classList.add("hidden");
      return;
    }

    els.metadataCard.classList.remove("hidden");
    const m = report.scraped_metadata;

    const items = [
      { label: "Domain", value: m.domain },
      { label: "Title", value: m.title },
      { label: "Author", value: m.author },
      { label: "Published", value: m.publish_date },
    ].filter((item) => item.value);

    els.metadataStrip.innerHTML = items
      .map(
        (item) => `
      <div class="meta-item">
        <span class="meta-item-label">${item.label}</span>
        <span class="meta-item-value">${escapeHtml(item.value)}</span>
      </div>`
      )
      .join("");
  }

  function renderTechniques(report) {
    const techniques = report.techniques_detected || [];

    if (report.clean && techniques.length === 0) {
      els.techniquesGrid.innerHTML = `
        <div class="clean-banner">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="10"/>
            <path d="M7 11l3 3 5-5"/>
          </svg>
          No manipulation techniques detected. This content appears clean.
        </div>`;
      return;
    }

    els.techniquesGrid.innerHTML = techniques
      .map(
        (t) => `
      <div class="technique-card">
        <div class="technique-header">
          <span class="technique-name">${escapeHtml(t.name)}</span>
          <span class="severity-badge ${t.severity}">${t.severity}</span>
        </div>
        <p class="technique-explanation">${escapeHtml(t.explanation)}</p>
        <div class="technique-evidence">"${escapeHtml(t.evidence)}"</div>
      </div>`
      )
      .join("");
  }

  function renderAction(report) {
    const action =
      report.recommended_action || "No specific action recommended.";
    els.actionContent.innerHTML = `
      <svg class="action-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8v4M12 16h.01"/>
      </svg>
      <p>${escapeHtml(action)}</p>`;
  }

  // ─── History ─────────────────────────────────────────────────────

  async function loadHistory() {
    try {
      const res = await fetch("/api/history");
      if (!res.ok) return;
      const data = await res.json();
      const items = data.history || [];

      if (items.length === 0) {
        els.historyEmpty.classList.remove("hidden");
        els.historyTable.classList.add("hidden");
        return;
      }

      els.historyEmpty.classList.add("hidden");
      els.historyTable.classList.remove("hidden");

      els.historyTbody.innerHTML = items
        .map(
          (item) => `
        <tr>
          <td>${formatTime(item.timestamp)}</td>
          <td><span class="history-preview">${escapeHtml(item.input_preview)}</span></td>
          <td><span class="type-badge">${item.content_type}</span></td>
          <td class="score-cell">${item.risk_score}</td>
          <td><span class="risk-badge ${(item.risk_level || "low").toLowerCase()}">${item.risk_level}</span></td>
        </tr>`
        )
        .join("");
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  }

  async function loadStats() {
    try {
      const res = await fetch("/api/stats");
      if (!res.ok) return;
      const stats = await res.json();

      els.statTotal.textContent = stats.total_analyzed;
      els.statAvg.textContent = stats.avg_risk_score;
      els.statHigh.textContent = stats.high_risk_count;
      els.statTechnique.textContent = stats.most_common_technique || "N/A";
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
  }

  // ─── Utilities ───────────────────────────────────────────────────

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function formatTime(isoString) {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoString;
    }
  }

  // ─── Health Check ────────────────────────────────────────────────

  async function checkHealth() {
    try {
      const res = await fetch("/health");
      if (res.ok) {
        els.navStatus.title = "SENTINEL is online";
      }
    } catch {
      els.navStatus.title = "SENTINEL may be offline";
    }
  }

  // ─── Init ────────────────────────────────────────────────────────

  function init() {
    initNav();
    initModeToggle();
    initCharCount();
    initSamples();
    initKeyboard();
    initAnalyzeBtn();
    createToast();
    checkHealth();
  }

  // Run when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
