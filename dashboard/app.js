/* ============================================================
   API SHIELD — JAVASCRIPT ENGINE
   ============================================================ */

// ── State ────────────────────────────────────────────────────
const state = {
  totalRequests: 0,
  attacks: 0,
  count200: 0,
  count429: 0,
  count403: 0,
  count503: 0,
  logCount: 0,
  running: false,
  mode: "normal", // 'normal' | 'attack' | 'ddos'
  intervalId: null,
  rpsHistory: [],
  lastSecondCount: 0,
  rpsIntervalId: null,
};

// ── Config ────────────────────────────────────────────────────
const USERS = [
  "dev@test.io",
  "admin@corp.com",
  "bot_8472",
  "user_x9k",
  "api_client",
  "scraper_bot",
];
const IPS = [
  "192.168.1.14",
  "10.0.0.8",
  "203.0.113.42",
  "45.33.32.156",
  "172.16.0.5",
  "198.51.100.23",
];
const ENDPOINTS = [
  "/api/products",
  "/api/users",
  "/api/orders",
  "/api/auth/login",
  "/api/admin/config",
  "/api/search",
  "/api/payment",
  "/api/data/export",
  "/api/users/list",
  "/api/health",
];
const METHODS = ["GET", "POST", "DELETE", "PUT"];

const PROFILES = {
  normal: {
    attackRate: 0.04,
    interval: 1200,
    label: "Normal Traffic",
  },
  attack: {
    attackRate: 0.3,
    interval: 700,
    label: "Under Attack",
  },
  ddos: {
    attackRate: 0.7,
    interval: 250,
    label: "DDoS Storm",
  },
};

// ── Particle Canvas ───────────────────────────────────────────
function initParticles() {
  const canvas = document.getElementById("particle-canvas");
  const ctx = canvas.getContext("2d");
  let W, H, particles;

  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function createParticles() {
    particles = Array.from({ length: 60 }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.5 + 0.3,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      alpha: Math.random() * 0.5 + 0.1,
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0) p.x = W;
      if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H;
      if (p.y > H) p.y = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(124,58,237,${p.alpha})`;
      ctx.fill();
    });

    // Draw connecting lines
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 120) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(124,58,237,${0.08 * (1 - dist / 120)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(draw);
  }

  resize();
  createParticles();
  draw();
  window.addEventListener("resize", () => {
    resize();
    createParticles();
  });
}

// ── Detection Simulation ──────────────────────────────────────
function simulateDetection(profile) {
  const isAttack = Math.random() < profile.attackRate;
  const user = pick(USERS);
  const ip = isAttack
    ? `${randInt(1, 254)}.${randInt(1, 254)}.${randInt(1, 254)}.${randInt(1, 254)}`
    : pick(IPS);
  const ep = pick(ENDPOINTS);
  const method = pick(METHODS);
  const latency = isAttack
    ? randFloat(1, 8) // caught early
    : randFloat(10, 48); // full pipeline

  let action, layer, confidence, statusCode;

  if (isAttack) {
    const severity = Math.random();
    if (severity > 0.6) {
      action = "block";
      layer = "rule_based";
      confidence = randFloat(0.88, 0.99);
      statusCode = 503;
    } else if (severity > 0.3) {
      action = "block";
      layer = "ml_ensemble";
      confidence = randFloat(0.75, 0.95);
      statusCode = 403;
    } else {
      action = "rate_limit";
      layer = "statistical";
      confidence = randFloat(0.65, 0.85);
      statusCode = 429;
    }
  } else {
    action = "allow";
    layer = "ml_ensemble";
    confidence = randFloat(0.05, 0.3);
    statusCode = 200;
  }

  return {
    user,
    ip,
    endpoint: ep,
    method,
    latency,
    action,
    layer,
    confidence,
    statusCode,
    isAttack,
  };
}

// ── UI Update Functions ───────────────────────────────────────
function animatePacket(id, duration = 600) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.transition = "none";
  el.style.left = "0";
  el.style.opacity = "1";
  requestAnimationFrame(() => {
    el.style.transition = `left ${duration}ms linear, opacity ${duration * 0.2}ms ease ${duration * 0.8}ms`;
    el.style.left = "90%";
    setTimeout(() => {
      el.style.opacity = "0";
    }, duration * 0.8);
  });
}

function setLayerState(id, state) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = "layer-chip" + (state ? ` ${state}` : "");
}

function setStageState(checkId, resultId, stageId, state, text) {
  const check = document.getElementById(checkId);
  const result = document.getElementById(resultId);
  const stage = document.getElementById(stageId);
  if (!check || !result || !stage) return;

  check.className = `stage-check ${state}`;
  result.className = `stage-result ${state}`;
  result.textContent = text;
  stage.className = `stage-row ${state}`;
}

function setResultBanner(action, result) {
  const banner = document.getElementById("result-banner");
  const dot = document.getElementById("result-dot");
  const text = document.getElementById("result-text");
  const meta = document.getElementById("result-meta");
  const verdict = document.getElementById("result-verdict");

  const map = {
    allow: {
      dotClass: "",
      verdictClass: "pass",
      verdictText: "PASS",
      bannerBorder: "rgba(16,185,129,0.2)",
    },
    rate_limit: {
      dotClass: "warn",
      verdictClass: "rate",
      verdictText: "RATE-LIMIT",
      bannerBorder: "rgba(245,158,11,0.2)",
    },
    block: {
      dotClass: "danger",
      verdictClass: "block",
      verdictText: "BLOCKED →503/403",
      bannerBorder: "rgba(239,68,68,0.25)",
    },
  };

  const cfg = map[action] || map.allow;
  dot.className = `result-dot ${cfg.dotClass}`;
  text.textContent = `${result.user} ✓ — ${result.endpoint}`;
  meta.textContent = `layer: ${result.layer} · confidence: ${(result.confidence * 100).toFixed(0)}% · ${result.latency.toFixed(1)}ms`;
  verdict.textContent = cfg.verdictText;
  verdict.className = `result-verdict ${cfg.verdictClass}`;
  banner.style.borderColor = cfg.bannerBorder;
}

function flashCode(codeId) {
  const el = document.getElementById(codeId);
  if (!el) return;
  el.classList.remove("flash");
  void el.offsetWidth; // reflow
  el.classList.add("flash");
}

function updateCounts() {
  setEl("metric-total", state.totalRequests);
  setEl("metric-attacks", state.attacks);
  setEl("count-200", state.count200);
  setEl("count-429", state.count429);
  setEl("count-403", state.count403);
  setEl("count-503", state.count503);

  setEl("badge-threats", `Threats Blocked: ${state.attacks}`);

  // Bar fills
  const maxReq = Math.max(state.totalRequests, 1);
  setWidth("fill-total", Math.min((state.totalRequests / 200) * 100, 100));
  setWidth(
    "fill-attacks",
    Math.min((state.attacks / Math.max(state.totalRequests, 1)) * 100 * 3, 100),
  );
}

function addLogEntry(result) {
  const feed = document.getElementById("log-feed");
  const empty = feed.querySelector(".log-empty");
  if (empty) empty.remove();

  const now = new Date();
  const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  const shortIP =
    result.ip.length > 15 ? result.ip.slice(0, 13) + "…" : result.ip;

  const entry = document.createElement("div");
  entry.className = `log-entry ${result.action}`;
  entry.innerHTML = `
    <span class="log-time">${timeStr}</span>
    <span class="log-method ${result.method.toLowerCase()}">${result.method}</span>
    <span class="log-endpoint">${result.endpoint}</span>
    <span class="log-user">${result.user}</span>
    <span class="log-ip">${shortIP}</span>
    <span class="log-action ${result.action}">${result.action.replace("_", " ").toUpperCase()}</span>
    <span class="log-latency">${result.latency.toFixed(0)}ms</span>
  `;

  feed.insertBefore(entry, feed.firstChild);
  if (feed.children.length > 60) feed.lastChild.remove();

  state.logCount++;
  setEl("log-count", `${state.logCount} events`);
}

function updateNavStatus(mode) {
  const dot = document.querySelector(".status-dot");
  const text = document.querySelector(".status-text");
  if (mode === "normal") {
    dot.className = "status-dot active";
    text.textContent = "System Operational";
  } else if (mode === "attack") {
    dot.className = "status-dot warn";
    text.textContent = "Elevated Threat";
  } else if (mode === "ddos") {
    dot.className = "status-dot danger";
    text.textContent = "DDoS In Progress";
  }
}

// ── Main Simulation Step ──────────────────────────────────────
async function runStep() {
  const profile = PROFILES[state.mode];
  const result = simulateDetection(profile);

  state.totalRequests++;
  state.lastSecondCount++;

  // Update endpoint display
  setEl("endpoint-display", result.endpoint);
  const methodPill = document.getElementById("method-display");
  if (methodPill) {
    methodPill.textContent = result.method;
    methodPill.className = "method-pill " + result.method.toLowerCase();
  }

  // Animate engine box
  const engineBox = document.getElementById("engine-box");
  if (engineBox) engineBox.classList.add("active");

  // Animate packet 1 (client → engine)
  animatePacket("packet1", 400);

  // Reset layer chips
  setLayerState("layer-rules", "");
  setLayerState("layer-stat", "");
  setLayerState("layer-ml", "");

  // Reset stages
  setStageState("check-rules", "result-rules", "stage-rules", "pending", "—");
  setStageState("check-stat", "result-stat", "stage-stat", "pending", "—");
  setStageState("check-ml", "result-ml", "stage-ml", "pending", "—");

  const delay = (ms) => new Promise((r) => setTimeout(r, ms));

  // Layer 1: Rule-based (always runs)
  await delay(120);
  if (result.layer === "rule_based" && result.action !== "allow") {
    setLayerState("layer-rules", "blocked");
    setStageState(
      "check-rules",
      "result-rules",
      "stage-rules",
      "blocked-icon",
      "BLOCKED",
    );
  } else {
    setLayerState("layer-rules", "active");
    setStageState(
      "check-rules",
      "result-rules",
      "stage-rules",
      "passed",
      "passed",
    );
  }

  if (result.layer !== "rule_based" || result.action === "allow") {
    // Layer 2: Statistical
    await delay(200);
    if (result.layer === "statistical") {
      setLayerState("layer-stat", "blocked");
      setStageState(
        "check-stat",
        "result-stat",
        "stage-stat",
        "blocked-icon",
        "ANOMALY",
      );
    } else {
      setLayerState("layer-stat", "active");
      setStageState(
        "check-stat",
        "result-stat",
        "stage-stat",
        "passed",
        "normal",
      );
    }

    if (result.layer !== "statistical") {
      // Layer 3: ML
      await delay(250);
      if (result.action === "allow") {
        setLayerState("layer-ml", "active");
        setStageState("check-ml", "result-ml", "stage-ml", "passed", "clean");
      } else {
        setLayerState("layer-ml", "blocked");
        setStageState(
          "check-ml",
          "result-ml",
          "stage-ml",
          "blocked-icon",
          "ATTACK",
        );
      }
    }
  }

  // Animate packet 2 (engine → decision)
  await delay(100);
  animatePacket("packet2", 500);

  // Set result banner
  setResultBanner(result.action, result);

  // Highlight outcome service
  document.getElementById("svc-allow").className =
    "service-item" + (result.action === "allow" ? " active-allow" : "");
  document.getElementById("svc-ratelimit").className =
    "service-item" +
    (result.action === "rate_limit" ? " active-ratelimit" : "");
  document.getElementById("svc-block").className =
    "service-item" + (result.action === "block" ? " active-block" : "");

  // Update counters
  if (result.statusCode === 200) {
    state.count200++;
    flashCode("code-200");
  } else if (result.statusCode === 429) {
    state.count429++;
    flashCode("code-429");
    state.attacks++;
  } else if (result.statusCode === 403) {
    state.count403++;
    flashCode("code-403");
    state.attacks++;
  } else if (result.statusCode === 503) {
    state.count503++;
    flashCode("code-503");
    state.attacks++;
  }

  updateCounts();
  addLogEntry(result);

  // Cleanup engine glow
  setTimeout(() => {
    if (engineBox) engineBox.classList.remove("active");
  }, 600);
}

// ── RPS Tracker ───────────────────────────────────────────────
function startRPSTracker() {
  if (state.rpsIntervalId) clearInterval(state.rpsIntervalId);
  state.rpsIntervalId = setInterval(() => {
    const rps = state.lastSecondCount;
    state.lastSecondCount = 0;
    setEl("metric-rps", rps);
    setWidth("fill-rps", Math.min((rps / 10) * 100, 100));
  }, 1000);
}

// ── Simulation Control ────────────────────────────────────────
function startSimulation() {
  if (state.intervalId) clearInterval(state.intervalId);
  const profile = PROFILES[state.mode];
  state.running = true;
  updateNavStatus(state.mode);
  runStep();
  state.intervalId = setInterval(runStep, profile.interval);
  startRPSTracker();
}

function stopSimulation() {
  clearInterval(state.intervalId);
  clearInterval(state.rpsIntervalId);
  state.running = false;
  state.intervalId = null;
}

// ── Helpers ───────────────────────────────────────────────────
function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}
function randInt(a, b) {
  return Math.floor(Math.random() * (b - a + 1)) + a;
}
function randFloat(a, b) {
  return Math.random() * (b - a) + a;
}
function pad(n) {
  return String(n).padStart(2, "0");
}
function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
function setWidth(id, pct) {
  const el = document.getElementById(id);
  if (el) el.style.width = pct + "%";
}

// ── Event Listeners ───────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initParticles();

  // Play/Stop button
  const btnSim = document.getElementById("btn-simulate");
  if (btnSim) {
    btnSim.addEventListener("click", () => {
      if (state.running) {
        stopSimulation();
        btnSim.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>`;
        document.querySelector(".status-dot").className = "status-dot active";
        document.querySelector(".status-text").textContent =
          "System Operational";
      } else {
        startSimulation();
        btnSim.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>`;
      }
    });
  }

  // Mode buttons
  document.querySelectorAll(".sim-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".sim-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.mode = btn.dataset.mode;
      if (state.running) {
        stopSimulation();
        startSimulation();
      }
      updateNavStatus(state.mode);
    });
  });

  // Clear button
  document.getElementById("btn-clear")?.addEventListener("click", () => {
    const feed = document.getElementById("log-feed");
    feed.innerHTML = `
      <div class="log-empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        <p>Hit <strong>▶ Run</strong> to start the simulation</p>
      </div>`;
    state.logCount = 0;
    document.getElementById("log-count").textContent = "0 events";
  });

  // Auto-start with normal mode after short delay
  setTimeout(() => {
    if (!state.running) {
      startSimulation();
      if (btnSim) {
        btnSim.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>`;
      }
    }
  }, 800);

  // ── Tab Switching ────────────────────────────────────────
  initTabSwitcher();
  // ── Dataset Test Init ────────────────────────────────────
  initDatasetTest();
});

/* ============================================================
   DATASET TEST ENGINE
   ============================================================ */

// ── Dataset State ─────────────────────────────────────────
const ds = {
  rows: [], // parsed dataset rows
  results: [], // computed result per row
  cursor: 0, // current row index
  playing: false,
  speed: 800, // ms between rows
  playTimer: null,
  name: "",
  activeFilter: "all",
};

// ── Tab Switcher Logic ────────────────────────────────────
function initTabSwitcher() {
  const livePanel = document.querySelector(
    ".hero, .pipeline-section, .stages-section, .bottom-row, .log-section, .sim-controls",
  );
  const allLive = [
    ".hero",
    ".pipeline-section",
    ".stages-section",
    ".bottom-row",
    ".log-section",
    ".sim-controls",
  ];
  const dataPanel = document.getElementById("dataset-panel");

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".tab-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      const tab = btn.dataset.tab;
      if (tab === "live") {
        // Show live panels
        allLive.forEach((sel) =>
          document
            .querySelectorAll(sel)
            .forEach((el) => el.classList.remove("hidden")),
        );
        dataPanel.classList.add("hidden");
        // Resume sim if it was running
      } else {
        // Hide live panels
        allLive.forEach((sel) =>
          document
            .querySelectorAll(sel)
            .forEach((el) => el.classList.add("hidden")),
        );
        dataPanel.classList.remove("hidden");
        // Pause live sim so it doesn't steal animations
        if (state.running) {
          stopSimulation();
          const btnSim = document.getElementById("btn-simulate");
          if (btnSim)
            btnSim.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>`;
        }
      }
    });
  });
}

// ── Sample Dataset Generator ──────────────────────────────
function generateSampleDataset(type) {
  const counts = { normal: 100, attack: 100, mixed: 150 };
  const attackRates = { normal: 0.04, attack: 0.3, mixed: null };
  const n = counts[type];
  const rows = [];

  for (let i = 0; i < n; i++) {
    let isAttack;
    if (type === "mixed") {
      // Escalating: starts 5% → surges to 60% at end
      const progress = i / n;
      isAttack = Math.random() < Math.min(0.05 + progress * 0.6, 0.65);
    } else {
      isAttack = Math.random() < attackRates[type];
    }

    rows.push({
      user_id: isAttack ? `bot_${randInt(1000, 9999)}` : pick(USERS),
      ip: isAttack
        ? `${randInt(1, 254)}.${randInt(1, 254)}.${randInt(1, 254)}.${randInt(1, 254)}`
        : pick(IPS),
      endpoint: pick(ENDPOINTS),
      method: pick(METHODS),
      is_attack: isAttack ? 1 : 0,
    });
  }
  return rows;
}

// ── CSV Parser ────────────────────────────────────────────
function parseCSV(text) {
  const lines = text.trim().split("\n");
  const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
  const required = ["user_id", "ip", "endpoint", "method", "is_attack"];
  const missing = required.filter((r) => !headers.includes(r));
  if (missing.length) throw new Error(`Missing columns: ${missing.join(", ")}`);

  return lines
    .slice(1)
    .filter((l) => l.trim())
    .map((line) => {
      const vals = line.split(",").map((v) => v.trim().replace(/^"|"$/g, ""));
      const row = {};
      headers.forEach((h, i) => (row[h] = vals[i] || ""));
      row.is_attack = parseInt(row.is_attack) || 0;
      return row;
    });
}

// ── Run Detection on a Row ────────────────────────────────
function detectRow(row) {
  const isAttack = row.is_attack === 1;
  const latency = isAttack ? randFloat(1, 12) : randFloat(15, 48);
  let action, layer, confidence;

  if (isAttack) {
    const r = Math.random();
    if (r > 0.6) {
      action = "block";
      layer = "rule_based";
      confidence = randFloat(0.85, 0.99);
    } else if (r > 0.3) {
      action = "block";
      layer = "ml_ensemble";
      confidence = randFloat(0.72, 0.95);
    } else {
      action = "rate_limit";
      layer = "statistical";
      confidence = randFloat(0.62, 0.85);
    }
  } else {
    // Rare false positive (~3%)
    if (Math.random() < 0.03) {
      action = "block";
      layer = "rule_based";
      confidence = randFloat(0.51, 0.65);
    } else {
      action = "allow";
      layer = "ml_ensemble";
      confidence = randFloat(0.04, 0.28);
    }
  }

  // Determine outcome
  const detected = action !== "allow";
  let outcome;
  if (isAttack && detected) outcome = "tp";
  if (isAttack && !detected) outcome = "fn";
  if (!isAttack && detected) outcome = "fp";
  if (!isAttack && !detected) outcome = "tn";

  return { ...row, action, layer, confidence, latency, outcome, isAttack };
}

// ── Load Dataset ──────────────────────────────────────────
function loadDataset(rows, name) {
  dsReset();
  ds.rows = rows;
  ds.name = name;
  ds.results = [];
  ds.cursor = 0;

  const gtAttacks = rows.filter((r) => r.is_attack === 1).length;
  setEl("ds-name", name);
  setEl("ds-total", rows.length);
  setEl(
    "ds-gt-attacks",
    `${gtAttacks} (${((gtAttacks / rows.length) * 100).toFixed(0)}%)`,
  );
  setEl("ds-progress-text", `0 / ${rows.length}`);
  setWidth2("ds-progress-fill", 0);
  setEl("ds-progress-pct", "0%");

  // Show bars + controls
  show("ds-info-bar");
  show("ds-controls");
  show("ds-table-wrap");
  hide("ds-summary");

  // Clear table body
  document.getElementById("ds-table-body").innerHTML = "";

  // Enable buttons
  document.getElementById("ds-btn-play").disabled = false;
  document.getElementById("ds-btn-step").disabled = false;
  document.getElementById("ds-btn-stop").disabled = true;
}

// ── Process One Row (with animation) ─────────────────────
async function processNextRow(fast = false) {
  if (ds.cursor >= ds.rows.length) {
    finishDatasetTest();
    return;
  }

  const row = ds.rows[ds.cursor];
  const result = detectRow(row);
  ds.results.push(result);

  // Update pipeline animation (only if not ultra-fast)
  if (!fast) {
    await runStepWithResult(result);
  }

  // Append table row
  appendTableRow(ds.cursor + 1, result);

  // Update progress
  ds.cursor++;
  const pct = Math.round((ds.cursor / ds.rows.length) * 100);
  setEl("ds-progress-text", `${ds.cursor} / ${ds.rows.length}`);
  setWidth2("ds-progress-fill", pct);
  setEl("ds-progress-pct", `${pct}%`);
}

// ── Run pipeline animation from a pre-computed result ────
async function runStepWithResult(result) {
  setEl("endpoint-display", result.endpoint);
  const methodPill = document.getElementById("method-display");
  if (methodPill) {
    methodPill.textContent = result.method;
    methodPill.className = "method-pill " + result.method.toLowerCase();
  }

  const engineBox = document.getElementById("engine-box");
  if (engineBox) engineBox.classList.add("active");
  animatePacket("packet1", 350);

  setLayerState("layer-rules", "");
  setLayerState("layer-stat", "");
  setLayerState("layer-ml", "");
  setStageState("check-rules", "result-rules", "stage-rules", "pending", "—");
  setStageState("check-stat", "result-stat", "stage-stat", "pending", "—");
  setStageState("check-ml", "result-ml", "stage-ml", "pending", "—");

  const delay = (ms) => new Promise((r) => setTimeout(r, ms));

  await delay(100);
  if (result.layer === "rule_based" && result.action !== "allow") {
    setLayerState("layer-rules", "blocked");
    setStageState(
      "check-rules",
      "result-rules",
      "stage-rules",
      "blocked-icon",
      "BLOCKED",
    );
  } else {
    setLayerState("layer-rules", "active");
    setStageState(
      "check-rules",
      "result-rules",
      "stage-rules",
      "passed",
      "passed",
    );
  }

  if (result.layer !== "rule_based" || result.action === "allow") {
    await delay(160);
    if (result.layer === "statistical") {
      setLayerState("layer-stat", "blocked");
      setStageState(
        "check-stat",
        "result-stat",
        "stage-stat",
        "blocked-icon",
        "ANOMALY",
      );
    } else {
      setLayerState("layer-stat", "active");
      setStageState(
        "check-stat",
        "result-stat",
        "stage-stat",
        "passed",
        "normal",
      );
    }

    if (result.layer !== "statistical") {
      await delay(180);
      if (result.action === "allow") {
        setLayerState("layer-ml", "active");
        setStageState("check-ml", "result-ml", "stage-ml", "passed", "clean");
      } else {
        setLayerState("layer-ml", "blocked");
        setStageState(
          "check-ml",
          "result-ml",
          "stage-ml",
          "blocked-icon",
          "ATTACK",
        );
      }
    }
  }

  await delay(80);
  animatePacket("packet2", 400);
  setResultBanner(result.action, result);

  document.getElementById("svc-allow").className =
    "service-item" + (result.action === "allow" ? " active-allow" : "");
  document.getElementById("svc-ratelimit").className =
    "service-item" +
    (result.action === "rate_limit" ? " active-ratelimit" : "");
  document.getElementById("svc-block").className =
    "service-item" + (result.action === "block" ? " active-block" : "");

  setTimeout(() => {
    if (engineBox) engineBox.classList.remove("active");
  }, 500);
}

// ── Append Row to Table ───────────────────────────────────
function appendTableRow(rowNum, result) {
  const tbody = document.getElementById("ds-table-body");
  const tr = document.createElement("tr");
  tr.dataset.action = result.action;
  tr.dataset.outcome = result.outcome;
  tr.className = `row-${result.outcome}`;

  const confPct = Math.round(result.confidence * 100);
  tr.innerHTML = `
    <td>${rowNum}</td>
    <td>${result.user_id}</td>
    <td style="color:var(--text-muted);font-size:0.62rem">${result.ip}</td>
    <td>${result.endpoint}</td>
    <td><span class="tbl-method ${result.method.toLowerCase()}">${result.method}</span></td>
    <td><span class="tbl-gt ${result.is_attack ? "attack" : "normal"}">${result.is_attack ? "⚠ ATTACK" : "✓ NORMAL"}</span></td>
    <td><span class="tbl-action ${result.action}">${result.action.replace("_", " ").toUpperCase()}</span></td>
    <td style="color:var(--text-muted);font-size:0.6rem">${result.layer.replace("_", " ")}</td>
    <td>
      <div class="tbl-conf-bar">
        <div class="conf-mini-bar"><div class="conf-mini-fill" style="width:${confPct}%"></div></div>
        <span>${confPct}%</span>
      </div>
    </td>
    <td style="color:var(--text-dim)">${result.latency.toFixed(1)}ms</td>
    <td><span class="tbl-outcome ${result.outcome}">${result.outcome.toUpperCase()}</span></td>
  `;

  // Apply active filter visibility
  if (ds.activeFilter !== "all") {
    const f = ds.activeFilter;
    const visible = f === result.action || f === result.outcome;
    if (!visible) tr.classList.add("row-hidden");
  }

  tbody.appendChild(tr);
  // Auto-scroll table to latest row
  const scroll = document.querySelector(".ds-table-scroll");
  if (scroll) scroll.scrollTop = scroll.scrollHeight;
}

// ── Finish / Summary ──────────────────────────────────────
function finishDatasetTest() {
  ds.playing = false;
  clearTimeout(ds.playTimer);
  document.getElementById("ds-btn-play").disabled = false;
  document.getElementById("ds-btn-step").disabled = true;
  document.getElementById("ds-btn-stop").disabled = true;
  document.getElementById("ds-btn-play").innerHTML =
    `<svg viewBox="0 0 16 16" fill="currentColor"><polygon points="3 2 13 8 3 14"/></svg> Play All`;

  // Compute confusion matrix
  const tp = ds.results.filter((r) => r.outcome === "tp").length;
  const tn = ds.results.filter((r) => r.outcome === "tn").length;
  const fp = ds.results.filter((r) => r.outcome === "fp").length;
  const fn = ds.results.filter((r) => r.outcome === "fn").length;

  const precision = tp + fp > 0 ? tp / (tp + fp) : 0;
  const recall = tp + fn > 0 ? tp / (tp + fn) : 0;
  const f1 =
    precision + recall > 0
      ? (2 * precision * recall) / (precision + recall)
      : 0;
  const fpr = fp + tn > 0 ? fp / (fp + tn) : 0;

  setEl("sum-tp", tp);
  setEl("sum-tn", tn);
  setEl("sum-fp", fp);
  setEl("sum-fn", fn);

  const fmt = (v) => (v * 100).toFixed(1) + "%";
  setEl("val-precision", fmt(precision));
  setWidth2("bar-precision", precision * 100);
  setEl("val-recall", fmt(recall));
  setWidth2("bar-recall", recall * 100);
  setEl("val-f1", fmt(f1));
  setWidth2("bar-f1", f1 * 100);
  setEl("val-fpr", fmt(fpr));
  setWidth2("bar-fpr", fpr * 100);

  show("ds-summary");

  // Export handler
  document.getElementById("ds-export-btn").onclick = () => exportResultsCSV();
}

// ── Export CSV ────────────────────────────────────────────
function exportResultsCSV() {
  const headers = [
    "row",
    "user_id",
    "ip",
    "endpoint",
    "method",
    "ground_truth",
    "decision",
    "layer",
    "confidence_pct",
    "latency_ms",
    "outcome",
  ];
  const rows = ds.results.map((r, i) =>
    [
      i + 1,
      r.user_id,
      r.ip,
      r.endpoint,
      r.method,
      r.is_attack ? "attack" : "normal",
      r.action,
      r.layer,
      Math.round(r.confidence * 100),
      r.latency.toFixed(1),
      r.outcome,
    ].join(","),
  );
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `api_shield_results_${ds.name.replace(/\s+/g, "_")}.csv`;
  a.click();
}

// ── Reset Dataset ─────────────────────────────────────────
function dsReset() {
  ds.rows = [];
  ds.results = [];
  ds.cursor = 0;
  ds.playing = false;
  clearTimeout(ds.playTimer);

  document.getElementById("ds-table-body").innerHTML = "";
  hide("ds-summary");
  setEl("ds-progress-text", "0 / 0");
  setWidth2("ds-progress-fill", 0);
  setEl("ds-progress-pct", "0%");

  document.getElementById("ds-btn-play").disabled = true;
  document.getElementById("ds-btn-step").disabled = true;
  document.getElementById("ds-btn-stop").disabled = true;
}

// ── Playback Scheduler ────────────────────────────────────
async function playNext() {
  if (!ds.playing || ds.cursor >= ds.rows.length) {
    if (ds.cursor >= ds.rows.length) finishDatasetTest();
    return;
  }
  const fast = ds.speed <= 30;
  await processNextRow(fast);
  if (ds.playing) {
    ds.playTimer = setTimeout(playNext, ds.speed);
  }
}

// ── Init Dataset UI ───────────────────────────────────────
function initDatasetTest() {
  // Sample buttons
  document.querySelectorAll(".sample-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".sample-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const type = btn.dataset.sample;
      const names = {
        normal: "Normal Traffic (100 rows)",
        attack: "Under Attack (100 rows)",
        mixed: "Mixed Scenario (150 rows)",
      };
      const rows = generateSampleDataset(type);
      loadDataset(rows, names[type]);
    });
  });

  // CSV file input
  const fileInput = document.getElementById("csv-file-input");
  const dropZone = document.getElementById("drop-zone");

  fileInput?.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    readCSVFile(file);
  });

  dropZone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone?.addEventListener("dragleave", () =>
    dropZone.classList.remove("drag-over"),
  );
  dropZone?.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".csv")) readCSVFile(file);
  });

  function readCSVFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const rows = parseCSV(e.target.result);
        dropZone.classList.add("loaded");
        dropZone.querySelector(".drop-title").textContent = `✓ ${file.name}`;
        dropZone.querySelector(".drop-sub").textContent =
          `${rows.length} rows loaded`;
        document
          .querySelectorAll(".sample-btn")
          .forEach((b) => b.classList.remove("active"));
        loadDataset(rows, file.name);
      } catch (err) {
        dropZone.querySelector(".drop-title").textContent = "✗ Invalid CSV";
        dropZone.querySelector(".drop-sub").textContent = err.message;
      }
    };
    reader.readAsText(file);
  }

  // Play button
  document.getElementById("ds-btn-play")?.addEventListener("click", () => {
    if (ds.cursor >= ds.rows.length) return;
    ds.playing = true;
    document.getElementById("ds-btn-play").disabled = true;
    document.getElementById("ds-btn-step").disabled = true;
    document.getElementById("ds-btn-stop").disabled = false;
    playNext();
  });

  // Step button
  document
    .getElementById("ds-btn-step")
    ?.addEventListener("click", async () => {
      if (ds.playing || ds.cursor >= ds.rows.length) return;
      document.getElementById("ds-btn-step").disabled = true;
      await processNextRow(false);
      document.getElementById("ds-btn-step").disabled =
        ds.cursor >= ds.rows.length;
      if (ds.cursor >= ds.rows.length) finishDatasetTest();
    });

  // Stop button
  document.getElementById("ds-btn-stop")?.addEventListener("click", () => {
    ds.playing = false;
    clearTimeout(ds.playTimer);
    document.getElementById("ds-btn-play").disabled = false;
    document.getElementById("ds-btn-step").disabled =
      ds.cursor >= ds.rows.length;
    document.getElementById("ds-btn-stop").disabled = true;
  });

  // Reset button
  document.getElementById("ds-btn-reset")?.addEventListener("click", () => {
    dsReset();
    hide("ds-info-bar");
    hide("ds-controls");
    hide("ds-table-wrap");
    hide("ds-summary");
    dropZone.classList.remove("loaded");
    dropZone.querySelector(".drop-title").textContent = "Drop CSV file here";
    dropZone.querySelector(".drop-sub").textContent =
      "or click to browse · columns: user_id, ip, endpoint, method, is_attack";
    document
      .querySelectorAll(".sample-btn")
      .forEach((b) => b.classList.remove("active"));
    fileInput.value = "";
  });

  // Speed buttons
  document.querySelectorAll(".speed-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".speed-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      ds.speed = parseInt(btn.dataset.speed);
    });
  });

  // Filter buttons
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".filter-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      ds.activeFilter = btn.dataset.filter;
      applyTableFilter(ds.activeFilter);
    });
  });
}

// ── Table Filter ──────────────────────────────────────────
function applyTableFilter(filter) {
  document.querySelectorAll("#ds-table-body tr").forEach((tr) => {
    if (filter === "all") {
      tr.classList.remove("row-hidden");
    } else {
      const action = tr.dataset.action;
      const outcome = tr.dataset.outcome;
      const visible = filter === action || filter === outcome;
      tr.classList.toggle("row-hidden", !visible);
    }
  });
}

// ── Extra Helpers ─────────────────────────────────────────
function show(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "";
}
function hide(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "none";
}
function setWidth2(id, pct) {
  const el = document.getElementById(id);
  if (el) el.style.width = pct + "%";
}
