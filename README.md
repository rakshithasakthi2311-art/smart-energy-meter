# ⚡ Smart Energy Monitoring & Theft Detection System

Real-time energy monitoring dashboard with theft/overload detection.
**Backend**: FastAPI + WebSockets | **Frontend**: React + Recharts (+ legacy HTML fallback)

---

## 📁 Project Structure

```
smart_energy/
├── main.py                    ← FastAPI backend (WebSockets + REST API)
├── requirements.txt           ← Python dependencies
├── README.md
├── frontend/                  ← Plain HTML/CSS/JS fallback (no Node needed)
│   ├── login.html
│   └── dashboard.html
└── react-frontend/            ← React app (PRIMARY)
    ├── package.json
    ├── public/
    │   └── index.html
    └── src/
        ├── index.js
        ├── App.js             ← React Router setup
        ├── index.css          ← Global CSS variables & base styles
        ├── hooks/
        │   ├── useEnergyData.js   ← WebSocket + rolling chart history hook
        │   └── useSoundAlert.js   ← Web Audio API buzzer hook
        ├── pages/
        │   ├── LoginPage.js       ← Login with auth guard
        │   └── DashboardPage.js   ← Main dashboard wiring all components
        └── components/
            ├── MetricCard.js      ← Voltage / Current / Power / Energy / Cost cards
            ├── AlertBar.js        ← Normal / Warning / Critical alert strip
            ├── PowerChart.js      ← Recharts live area chart
            ├── ControlPanel.js    ← Mode buttons + sliders + power toggle
            ├── InsightsPanel.js   ← Peak, avg, abnormal %, theft stats
            ├── BillingPanel.js    ← Rate input + live cost + reset meter
            └── TNEBReport.js      ← Issue report form
```

---

## 🚀 Quick Start

### Step 1 — Start the FastAPI backend

Open a terminal in the `smart_energy/` folder:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

### Step 2A — React Dev Mode (recommended)

Open a **second** terminal inside `smart_energy/react-frontend/`:

```bash
npm install
npm start
```

React dev server starts at **http://localhost:3000**
It proxies `/api` and `/ws` calls to `http://localhost:8000` automatically
(configured via `"proxy"` field in package.json).

---

### Step 2B — React Production Build (served by FastAPI)

```bash
cd react-frontend
npm install
npm run build
```

Now visit **http://localhost:8000** — FastAPI detects the `react-frontend/build/`
folder and serves the React SPA, including client-side routing.

---

### Step 2C — Legacy HTML (no Node.js needed)

Just go to **http://localhost:8000** without building React.
FastAPI falls back to the plain HTML/CSS/JS version in `frontend/`.

---

## 🔑 Login Credentials

| Username | Password  |
|----------|-----------|
| admin    | admin123  |
| tneb     | tneb2024  |

---

## 🎮 Features

| Feature | Details |
|---|---|
| 📡 Real-time WebSocket | Live data pushed every second |
| 🎮 Control Panel | Voltage/current sliders, Normal/Theft/Overload mode buttons |
| ⚠️ Theft Detection | Alert when current > 6A for 3+ seconds |
| 🚨 Overload Alert | Triggers at > 2200W, topbar turns red |
| 🔊 Sound Alert | Web Audio API buzzer on critical events |
| 💳 Live Billing | Configurable ₹/kWh rate, real-time cost |
| 📊 Insights | Peak power, average, abnormal %, theft duration & loss |
| 📞 TNEB Report | Simulated issue submission with ticket number |
| 🔴 Remote Control | Disconnect / Restore power instantly |

---

## 🛠 VS Code Tips

- Install **Python** and **ES7+ React** extensions
- Use `Ctrl+`` ` to open split terminals
- Backend auto-reloads on save with `--reload`
- React hot-reloads automatically on every file save
