#!/usr/bin/env python3
"""
Verity Enterprise Guardrails - Dashboard
Simple web UI for demonstrating the B2B compliance use case.
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from guardrails import GuardedLLM, TrustAnalysis

# Load environment - try project root first, then current directory
env_path = Path(__file__).parent.parent.parent / ".env"
if not env_path.exists():
    env_path = Path(".env")
load_dotenv(env_path)

app = FastAPI(title="Verity Enterprise Guardrails Dashboard")

# Store active sessions
sessions = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    model: Optional[str] = "openai/gpt-4o"


class ChatResponse(BaseModel):
    response: str
    trust_score: int
    flags: list
    warnings: list
    latency_ms: float


# HTML Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verity Enterprise Guardrails</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            min-height: 100vh;
        }
        header {
            grid-column: 1 / -1;
            background: #1a73e8;
            color: white;
            padding: 20px;
            border-radius: 12px;
        }
        header h1 { margin-bottom: 5px; }
        header p { opacity: 0.9; }
        .chat-section {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
        }
        .chat-header {
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
            font-weight: 600;
        }
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            max-height: 500px;
        }
        .message {
            margin-bottom: 15px;
            max-width: 80%;
        }
        .message.user {
            margin-left: auto;
            text-align: right;
        }
        .message-content {
            display: inline-block;
            padding: 12px 16px;
            border-radius: 16px;
            background: #e3f2fd;
        }
        .message.user .message-content {
            background: #1a73e8;
            color: white;
        }
        .message.assistant .message-content {
            background: #f5f5f5;
        }
        .trust-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 5px;
        }
        .trust-high { background: #c8e6c9; color: #2e7d32; }
        .trust-medium { background: #fff3e0; color: #e65100; }
        .trust-low { background: #ffcdd2; color: #c62828; }
        .chat-input {
            padding: 15px 20px;
            border-top: 1px solid #eee;
            display: flex;
            gap: 10px;
        }
        .chat-input input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #ddd;
            border-radius: 25px;
            font-size: 14px;
        }
        .chat-input input:focus { outline: none; border-color: #1a73e8; }
        .chat-input button {
            padding: 12px 24px;
            background: #1a73e8;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
        }
        .chat-input button:hover { background: #1557b0; }
        .chat-input button:disabled { background: #ccc; cursor: not-allowed; }
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .panel {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .panel h2 {
            font-size: 16px;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #f5f5f5;
        }
        .stat:last-child { border-bottom: none; }
        .stat-value { font-weight: 600; }
        .stat-value.good { color: #2e7d32; }
        .stat-value.warn { color: #e65100; }
        .stat-value.bad { color: #c62828; }
        .flags-list {
            max-height: 200px;
            overflow-y: auto;
        }
        .flag-item {
            padding: 8px 10px;
            margin-bottom: 8px;
            border-radius: 6px;
            font-size: 13px;
        }
        .flag-item.high { background: #ffebee; border-left: 3px solid #c62828; }
        .flag-item.medium { background: #fff3e0; border-left: 3px solid #e65100; }
        .flag-item.low { background: #e3f2fd; border-left: 3px solid #1a73e8; }
        .flag-category { font-weight: 600; text-transform: uppercase; font-size: 11px; }
        .export-btn {
            width: 100%;
            padding: 12px;
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
        }
        .export-btn:hover { background: #eee; }
        .warning-banner {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
            text-align: center;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛡️ Verity Enterprise Guardrails</h1>
            <p>LLM Response Trust Scoring for Compliance Teams</p>
        </header>
        
        <div class="chat-section">
            <div class="chat-header">💬 AI Assistant (Guarded)</div>
            <div class="chat-messages" id="chatMessages">
                <div class="warning-banner">
                    ⚠️ This AI assistant is monitored. All responses are analyzed for trust signals and logged for compliance.
                </div>
            </div>
            <div class="chat-input">
                <input type="text" id="messageInput" placeholder="Type a message..." onkeypress="if(event.key==='Enter')sendMessage()">
                <button onclick="sendMessage()" id="sendBtn">Send</button>
            </div>
        </div>
        
        <div class="sidebar">
            <div class="panel">
                <h2>📊 Session Stats</h2>
                <div class="stat">
                    <span>Total Turns</span>
                    <span class="stat-value" id="totalTurns">0</span>
                </div>
                <div class="stat">
                    <span>Avg Trust Score</span>
                    <span class="stat-value" id="avgScore">-</span>
                </div>
                <div class="stat">
                    <span>Low Trust Responses</span>
                    <span class="stat-value" id="lowTrust">0</span>
                </div>
                <div class="stat">
                    <span>Total Flags</span>
                    <span class="stat-value" id="totalFlags">0</span>
                </div>
            </div>
            
            <div class="panel">
                <h2>🚩 Recent Flags</h2>
                <div class="flags-list" id="flagsList">
                    <p style="color: #999; font-size: 13px;">No flags yet</p>
                </div>
            </div>
            
            <div class="panel">
                <h2>📋 Compliance Export</h2>
                <p style="font-size: 13px; color: #666; margin-bottom: 15px;">
                    Export session data for audit trail and compliance documentation.
                </p>
                <button class="export-btn" onclick="exportSession()">📥 Export Session Report</button>
            </div>
        </div>
    </div>
    
    <script>
        const sessionId = 'session_' + Date.now();
        let stats = { turns: 0, scores: [], flags: [] };
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;
            
            // Add user message
            addMessage(message, 'user');
            input.value = '';
            
            // Disable button
            const btn = document.getElementById('sendBtn');
            btn.disabled = true;
            btn.textContent = '...';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sessionId,
                        message: message
                    })
                });
                
                const data = await response.json();
                
                // Add assistant message with trust score
                addMessage(data.response, 'assistant', data.trust_score, data.flags);
                
                // Update stats
                stats.turns++;
                stats.scores.push(data.trust_score);
                stats.flags.push(...data.flags);
                updateStats();
                
            } catch (err) {
                addMessage('Error: ' + err.message, 'assistant', 0, []);
            }
            
            btn.disabled = false;
            btn.textContent = 'Send';
        }
        
        function addMessage(text, role, trustScore = null, flags = []) {
            const container = document.getElementById('chatMessages');
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message ' + role;
            
            let html = '<div class="message-content">' + escapeHtml(text) + '</div>';
            
            if (trustScore !== null && role === 'assistant') {
                const scoreClass = trustScore >= 70 ? 'high' : trustScore >= 50 ? 'medium' : 'low';
                html += '<div class="trust-badge trust-' + scoreClass + '">Trust: ' + trustScore + '/100</div>';
            }
            
            msgDiv.innerHTML = html;
            container.appendChild(msgDiv);
            container.scrollTop = container.scrollHeight;
        }
        
        function updateStats() {
            document.getElementById('totalTurns').textContent = stats.turns;
            
            const avg = stats.scores.length > 0 
                ? Math.round(stats.scores.reduce((a,b) => a+b, 0) / stats.scores.length)
                : 0;
            const avgEl = document.getElementById('avgScore');
            avgEl.textContent = avg + '/100';
            avgEl.className = 'stat-value ' + (avg >= 70 ? 'good' : avg >= 50 ? 'warn' : 'bad');
            
            const lowCount = stats.scores.filter(s => s < 50).length;
            const lowEl = document.getElementById('lowTrust');
            lowEl.textContent = lowCount;
            lowEl.className = 'stat-value ' + (lowCount === 0 ? 'good' : 'bad');
            
            document.getElementById('totalFlags').textContent = stats.flags.length;
            
            // Update flags list
            const flagsList = document.getElementById('flagsList');
            if (stats.flags.length > 0) {
                const recent = stats.flags.slice(-5).reverse();
                flagsList.innerHTML = recent.map(f => 
                    '<div class="flag-item ' + f.severity + '">' +
                    '<div class="flag-category">' + f.category + '</div>' +
                    '<div>' + f.description + '</div>' +
                    '</div>'
                ).join('');
            }
        }
        
        function exportSession() {
            const report = {
                session_id: sessionId,
                exported_at: new Date().toISOString(),
                stats: {
                    total_turns: stats.turns,
                    average_trust_score: stats.scores.length > 0 
                        ? Math.round(stats.scores.reduce((a,b) => a+b, 0) / stats.scores.length)
                        : 0,
                    low_trust_count: stats.scores.filter(s => s < 50).length,
                    total_flags: stats.flags.length
                },
                flags: stats.flags
            };
            
            const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'guardrails_report_' + sessionId + '.json';
            a.click();
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard."""
    return DASHBOARD_HTML


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with trust analysis."""
    
    # Get or create session
    if request.session_id not in sessions:
        sessions[request.session_id] = GuardedLLM(model=request.model)
    
    llm = sessions[request.session_id]
    
    try:
        result = await llm.chat(request.message)
        
        return ChatResponse(
            response=result.response,
            trust_score=result.trust_analysis.score,
            flags=[{
                "category": f.category,
                "severity": f.severity,
                "description": f.description
            } for f in result.trust_analysis.flags],
            warnings=result.warnings,
            latency_ms=result.latency_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}/summary")
async def session_summary(session_id: str):
    """Get session summary for compliance."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions[session_id].get_session_summary()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
