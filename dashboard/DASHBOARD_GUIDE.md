# API Shield — Dashboard Guide

> A real-time, dark cyberpunk-themed frontend for the **API Abuse Detection System**.  
> Inspired by the API Gateway visualization aesthetic — dark void background, neon accents, animated pipeline.

---

## 📁 File Structure

```
dashboard/
├── index.html          ← Main HTML page (structure & layout)
├── style.css           ← Dark cyberpunk CSS (colors, animations, layout)
├── app.js              ← JavaScript simulation engine (logic + animations)
└── DASHBOARD_GUIDE.md  ← This file
```

---

## 🚀 How to Run

### Option 1 — Python HTTP Server (Recommended)

Open a terminal in the `dashboard/` directory and run:

```bash
# From the project root
cd "api_abuse_detection/dashboard"

# Python 3
python -m http.server 5500
```

Then open your browser and go to:

```
http://localhost:5500
```

The simulation **starts automatically** after ~1 second.

---

### Option 2 — VS Code Live Server

1. Install the **Live Server** extension in VS Code
2. Right-click `index.html` → **"Open with Live Server"**
3. It will open at `http://127.0.0.1:5500`

---

### Option 3 — Open Directly (Limited)

> ⚠️ Some browsers block local file access. Use a server (Option 1 or 2) for best results.

Double-click `index.html` or drag it into any browser window.

---

## 🖥️ What the Dashboard Shows

The dashboard is a **visual, interactive simulation** of the 3-layer detection system. It does **not** require the FastAPI backend (`main.py`) to run — it has its own built-in simulation engine in JavaScript.

> If you want to connect it to the real backend, see the [Connecting to Real Backend](#connecting-to-real-backend) section below.

---

### 1. 🔷 Hero Section (Top)

| Element                   | Description                                     |
| ------------------------- | ----------------------------------------------- |
| **Title**                 | "API Abuse Detection" with cyan→purple gradient |
| **Subtitle**              | Lists the 3 detection layers and latency target |
| **Precision badge**       | Shows current precision (90%)                   |
| **Latency badge**         | Shows `<50ms` target                            |
| **Threats Blocked badge** | Live count of all blocked/rate-limited requests |

---

### 2. 🔄 Pipeline Visualizer (Middle)

This is the core visual — it mimics the flow of a real API request through the detection engine:

```
[ CLIENT ] ──●──▶ [ DETECTION ENGINE ] ──●──▶ [ allow / rate-limit / block ]
                  ┌──────────────────┐
                  │  Rules │ Stat │ ML│
                  └──────────────────┘
```

| Component                                     | What it shows                                                            |
| --------------------------------------------- | ------------------------------------------------------------------------ |
| **Client node**                               | The source of the incoming API request                                   |
| **Animated packet (purple dot)**              | Travels left→right to show request in-flight                             |
| **Detection Engine box**                      | Glows purple when actively processing                                    |
| **Layer chips** (Rules / Statistical / ML)    | Turn **green** = passed, **red** = blocked at that layer                 |
| **Second packet (green/cyan dot)**            | Shows the outgoing decision after processing                             |
| **Service list** (allow / rate-limit / block) | The active outcome highlights in color                                   |
| **Result banner**                             | Shows: `user ✓ — endpoint`, confidence %, which layer caught it, latency |
| **PASS / RATE-LIMIT / BLOCKED verdict**       | Badge in top-right of banner                                             |

---

### 3. 🧱 Detection Layers Panel

Displays the **3 sequential layers** of the detection pipeline:

| Layer                    | Technique                                              | Typical Latency | What triggers it       |
| ------------------------ | ------------------------------------------------------ | --------------- | ---------------------- |
| **Rule-Based**           | Blacklists, rate limits, bot signatures, IP reputation | `<2ms`          | Always runs first      |
| **Statistical Analysis** | EWMA, Isolation Forest, behavioral anomalies           | `5–10ms`        | Runs if Layer 1 passes |
| **ML Ensemble**          | XGBoost (50%) + LSTM (30%) + Autoencoder (20%)         | `15–25ms`       | Runs if Layer 2 passes |

Each row shows:

- **Check icon** — idle / processing (spinning) / passed (green ✓) / blocked (red ✗)
- **Stage result** — `passed` / `BLOCKED` / `ANOMALY` / `ATTACK` / `clean`
- **Highlight color** — green border = passed, red border = blocked at this layer

---

### 4. 📊 Response Code Counters

Shows cumulative counts for each type of HTTP outcome:

| Code    | Color     | Meaning                                                           |
| ------- | --------- | ----------------------------------------------------------------- |
| **200** | 🟢 Green  | Request **allowed** — legitimate traffic                          |
| **429** | 🟡 Yellow | **Rate limited** — suspicious but not confirmed attack            |
| **403** | 🟠 Orange | **Blocked** — confirmed attack by ML ensemble                     |
| **503** | 🔴 Red    | **Attack / Service Down** — high-confidence block from Rule layer |

Each card **flashes** briefly when a new request gets that status code.

---

### 5. 📈 Live Metrics Panel

| Metric             | Description                                              |
| ------------------ | -------------------------------------------------------- |
| **Total Requests** | Running count of all simulated requests                  |
| **Req / sec**      | Requests processed in the last second (updates every 1s) |
| **Attacks Caught** | Total threats (429 + 403 + 503 combined)                 |
| **Precision**      | Fixed at 90% (matches the model's evaluated performance) |

Each metric has an **animated progress bar** below it.

---

### 6. 📜 Live Request Log

An auto-scrolling feed showing the last 60 requests, with:

```
[TIME]  [METHOD]  [ENDPOINT]          [USER]       [IP]              [ACTION]      [LATENCY]
12:46:07  POST   /api/users          bot_8472   65.176.235.143       BLOCK           8ms
```

- **Color-coded rows**: green tint = allow, yellow tint = rate limit, red tint = block
- **Newest entries appear at the top**
- Click **Clear** to wipe the log

---

## 🎮 Simulation Modes

Three modes are available via the buttons at the **bottom of the screen**:

| Mode               | Attack Rate  | Update Speed  | Status Indicator      |
| ------------------ | ------------ | ------------- | --------------------- |
| **Normal Traffic** | ~4% attacks  | 1 req / 1.2s  | 🟢 System Operational |
| **Under Attack**   | ~30% attacks | 1 req / 0.7s  | 🟡 Elevated Threat    |
| **DDoS Storm**     | ~70% attacks | 1 req / 0.25s | 🔴 DDoS In Progress   |

The **▶ Play button** (top right) starts/stops the simulation. The navbar status dot changes color to match the current threat level.

---

## ⚙️ How It Works Internally

### Simulation Engine (`app.js`)

Each simulated request goes through these steps:

```
1. Pick random: user, IP, endpoint, method
2. Roll probability → decide if it's an attack (based on mode's attackRate)
3. If attack → randomly assign which layer catches it (rule / statistical / ml)
4. Animate: packet1 flies, engine glows, layer chips update sequentially
5. Animate: packet2 flies to decision node
6. Update: banner, status codes, metrics, log
```

**Animation sequence (per request):**

```
t+0ms    → packet1 animates (client → engine)
t+120ms  → Layer 1 (Rules) updates
t+320ms  → Layer 2 (Statistical) updates
t+570ms  → Layer 3 (ML) updates
t+620ms  → packet2 animates (engine → decision)
t+620ms  → Banner, counters, log all update
```

### Particle Background (`app.js → initParticles()`)

- 60 semi-transparent purple dots float across a `<canvas>` element
- Connecting lines are drawn between dots within 120px of each other
- Pure `requestAnimationFrame` loop — no external libraries

---

## 🔌 Connecting to Real Backend

To make the dashboard send **real** requests to `main.py` instead of simulating:

1. Start the FastAPI backend:

   ```bash
   cd api_abuse_detection
   python main.py
   # Runs at http://localhost:8000
   ```

2. In `app.js`, replace the `runStep()` function body with a `fetch` call:

   ```javascript
   async function runStep() {
     const payload = {
       user_id: pick(USERS),
       ip: pick(IPS),
       endpoint: pick(ENDPOINTS),
       method: pick(METHODS),
       status_code: 200,
       user_agent: "Mozilla/5.0",
     };

     const response = await fetch("http://localhost:8000/detect", {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify(payload),
     });
     const result = await response.json();
     // result.action = 'allow' | 'rate_limit' | 'block'
     // result.confidence, result.latency_ms, result.reason ...
   }
   ```

3. ⚠️ You'll need to add CORS headers to `main.py`:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
   ```

---

## 🐛 Troubleshooting

| Problem                    | Fix                                                            |
| -------------------------- | -------------------------------------------------------------- |
| Blank page / nothing loads | Use a local server (Option 1), not `file://`                   |
| Fonts look wrong           | Check internet connection (loads from Google Fonts)            |
| Particles not showing      | Make sure browser supports `<canvas>` (all modern browsers do) |
| Animation is choppy        | Close other browser tabs; reduce DDoS Storm mode usage         |
| Port 5500 already in use   | Change port: `python -m http.server 5600`                      |

---

## 🎨 Design Reference

The UI is inspired by the **API Gateway visualization** style:

| Design Element         | Implementation                                             |
| ---------------------- | ---------------------------------------------------------- |
| Dark void background   | `#080b10` base color                                       |
| Neon cyan/purple title | CSS gradient + `text-fill-color` trick                     |
| Pipeline flow diagram  | Flexbox layout with SVG arrows + CSS-animated dots         |
| Monospace labels       | JetBrains Mono font                                        |
| Glassmorphism cards    | `backdrop-filter: blur()` + semi-transparent borders       |
| Status badges          | Pill-shaped elements with color-matched `box-shadow` glows |
| Particle mesh          | `<canvas>` with `requestAnimationFrame`                    |

---

**Version:** 1.0  
**Last Updated:** 2026-03-08  
**Compatible with:** Chrome, Firefox, Edge, Safari (modern versions)
