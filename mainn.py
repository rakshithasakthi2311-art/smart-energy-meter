"""
Smart Energy Monitoring and Theft Detection System - Backend
FastAPI + WebSockets for real-time energy data
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio
import json
import random
import time
from typing import Optional

app = FastAPI(title="Smart Energy Monitor")

# Allow all origins for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mock users ─────────────────────────────────────────────────────────────────
USERS = {
    "admin": "admin123",
    "tneb":  "tneb2024",
}

# ── Shared energy state (mutated by WebSocket loop & control API) ──────────────
state = {
    "mode":          "normal",   # normal | theft | overload
    "manual_voltage": None,       # float override or None
    "manual_current": None,       # float override or None
    "power_on":      True,
    "energy_kwh":    0.0,
    "rate_per_unit": 6.0,         # ₹ per kWh
    "theft_seconds": 0,
    "peak_power":    0.0,
    "power_sum":     0.0,
    "sample_count":  0,
    "abnormal_count":0,
}

# ── Auth models ────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class ControlRequest(BaseModel):
    mode:            Optional[str]   = None
    manual_voltage:  Optional[float] = None
    manual_current:  Optional[float] = None
    power_on:        Optional[bool]  = None
    rate_per_unit:   Optional[float] = None
    reset_energy:    Optional[bool]  = None

class TNEBReport(BaseModel):
    name:    str
    issue:   str

# ── Auth endpoint ──────────────────────────────────────────────────────────────
@app.post("/api/login")
async def login(req: LoginRequest):
    if USERS.get(req.username) == req.password:
        return {"success": True, "username": req.username, "token": f"mock-token-{req.username}"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# ── Control endpoint ───────────────────────────────────────────────────────────
@app.post("/api/control")
async def control(req: ControlRequest):
    if req.mode is not None:
        state["mode"] = req.mode
    if req.manual_voltage is not None:
        state["manual_voltage"] = req.manual_voltage
    if req.manual_current is not None:
        state["manual_current"] = req.manual_current
    if req.power_on is not None:
        state["power_on"] = req.power_on
    if req.rate_per_unit is not None:
        state["rate_per_unit"] = req.rate_per_unit
    if req.reset_energy:
        state["energy_kwh"]    = 0.0
        state["theft_seconds"] = 0
        state["peak_power"]    = 0.0
        state["power_sum"]     = 0.0
        state["sample_count"]  = 0
        state["abnormal_count"]= 0
    return {"success": True, "state": state}

# ── TNEB Report ────────────────────────────────────────────────────────────────
@app.post("/api/report")
async def report_to_tneb(req: TNEBReport):
    # Simulated — just echo back
    return {"success": True, "message": f"Report from {req.name} submitted to TNEB. Ticket #TN{int(time.time())%100000}"}

# ── WebSocket ──────────────────────────────────────────────────────────────────
connected_clients: list[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            # ── Generate readings ──────────────────────────────────────────────
            if not state["power_on"]:
                voltage = current = power = 0.0
            else:
                mode = state["mode"]

                # Voltage
                if state["manual_voltage"] is not None:
                    voltage = state["manual_voltage"]
                elif mode == "overload":
                    voltage = random.uniform(235, 245)
                else:
                    voltage = random.uniform(218, 238)

                # Current
                if state["manual_current"] is not None:
                    current = state["manual_current"]
                elif mode == "theft":
                    current = random.uniform(7.5, 9.5)
                elif mode == "overload":
                    current = random.uniform(9.0, 10.5)
                else:
                    current = random.uniform(1.5, 5.5)

                power = round(voltage * current, 2)

            voltage = round(voltage, 2)
            current = round(current, 2)

            # ── Accumulate energy (1-second interval → /3600) ─────────────────
            delta_kwh = (power / 1000) / 3600
            state["energy_kwh"] += delta_kwh
            cost = round(state["energy_kwh"] * state["rate_per_unit"], 4)

            # ── Theft detection ────────────────────────────────────────────────
            THEFT_CURRENT_THRESHOLD = 6.0
            if state["power_on"] and current > THEFT_CURRENT_THRESHOLD:
                state["theft_seconds"] += 1
            else:
                state["theft_seconds"] = 0

            theft_detected  = state["theft_seconds"] >= 3
            theft_extra_kwh = round((current - THEFT_CURRENT_THRESHOLD) * voltage / 1000 / 3600
                                    * state["theft_seconds"], 6) if theft_detected else 0

            # ── Overload detection ─────────────────────────────────────────────
            OVERLOAD_THRESHOLD = 2200  # W
            overload_detected = state["power_on"] and power > OVERLOAD_THRESHOLD

            # ── Insights ───────────────────────────────────────────────────────
            if state["power_on"] and power > 0:
                state["sample_count"] += 1
                state["power_sum"]    += power
                if power > state["peak_power"]:
                    state["peak_power"] = power
                if theft_detected or overload_detected:
                    state["abnormal_count"] += 1

            avg_power    = round(state["power_sum"] / state["sample_count"], 2) if state["sample_count"] else 0
            abnormal_pct = round(state["abnormal_count"] / state["sample_count"] * 100, 1) if state["sample_count"] else 0

            # ── Alert level ────────────────────────────────────────────────────
            if not state["power_on"]:
                alert_level   = "info"
                alert_message = "Power supply is currently DISCONNECTED."
            elif theft_detected:
                alert_level   = "critical"
                alert_message = f"⚠️ Power Theft Detected! Excess current {round(current - THEFT_CURRENT_THRESHOLD, 2)}A for {state['theft_seconds']}s. Extra loss: {theft_extra_kwh} kWh (₹{round(theft_extra_kwh * state['rate_per_unit'],4)})"
            elif overload_detected:
                alert_level   = "critical"
                alert_message = f"🚨 Overload Warning! Power {power}W exceeds {OVERLOAD_THRESHOLD}W limit."
            elif current > 5.0:
                alert_level   = "warning"
                alert_message = f"⚡ High current detected ({current}A). Monitor closely."
            else:
                alert_level   = "normal"
                alert_message = "✅ All systems operating normally."

            # ── Build payload ──────────────────────────────────────────────────
            payload = {
                "timestamp":       round(time.time() * 1000),
                "voltage":         voltage,
                "current":         current,
                "power":           power,
                "energy_kwh":      round(state["energy_kwh"], 6),
                "cost":            cost,
                "rate_per_unit":   state["rate_per_unit"],
                "mode":            state["mode"],
                "power_on":        state["power_on"],
                "theft_detected":  theft_detected,
                "theft_seconds":   state["theft_seconds"],
                "theft_extra_kwh": theft_extra_kwh,
                "overload_detected": overload_detected,
                "alert_level":     alert_level,
                "alert_message":   alert_message,
                "peak_power":      round(state["peak_power"], 2),
                "avg_power":       avg_power,
                "abnormal_pct":    abnormal_pct,
            }

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

# ── Serve frontend ─────────────────────────────────────────────────────────────
import os

BASE_DIR = os.path.dirname(__file__)

# React build takes priority (react-frontend/build), falls back to plain HTML frontend
react_build = os.path.join(BASE_DIR, "react-frontend", "build")
html_frontend = os.path.join(BASE_DIR, "frontend")

if os.path.exists(react_build):
    # ── Serve React SPA ───────────────────────────────────────────────────────
    app.mount("/static", StaticFiles(directory=os.path.join(react_build, "static")), name="static")

    @app.get("/")
    async def serve_react_root():
        return FileResponse(os.path.join(react_build, "index.html"))

    # Catch-all: React Router handles client-side routing
    @app.get("/{full_path:path}")
    async def serve_react_spa(full_path: str):
        # Serve actual files if they exist (e.g. favicon, manifest)
        candidate = os.path.join(react_build, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(react_build, "index.html"))

elif os.path.exists(html_frontend):
    # ── Fallback: plain HTML frontend ─────────────────────────────────────────
    app.mount("/static", StaticFiles(directory=html_frontend), name="static")

    @app.get("/")
    async def serve_login():
        return FileResponse(os.path.join(html_frontend, "login.html"))

    @app.get("/dashboard")
    async def serve_dashboard():
        return FileResponse(os.path.join(html_frontend, "dashboard.html"))
