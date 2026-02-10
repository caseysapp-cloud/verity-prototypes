#!/usr/bin/env python3
"""
Verity Sniffer API Backend
FastAPI server for fact-checking, AI detection, and bias analysis.
"""

import os
import json
import httpx
from pathlib import Path
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment - try project root first, then current directory
env_path = Path(__file__).parent.parent.parent / ".env"
if not env_path.exists():
    env_path = Path(".env")
load_dotenv(env_path)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found. Copy .env.example to .env and add your key.")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model mapping
MODELS = {
    "gpt-4o": "openai/gpt-4o",
    "claude-sonnet": "anthropic/claude-sonnet-4",
    "gemini-flash": "google/gemini-2.0-flash-001",
}

app = FastAPI(
    title="Verity Sniffer API",
    description="AI-powered fact-checking, AI detection, and bias analysis",
    version="0.1.0"
)

# CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str
    url: Optional[str] = None
    context: Optional[str] = None
    model: Optional[str] = "gpt-4o"


class Source(BaseModel):
    title: str
    url: Optional[str] = None
    relevance: Optional[float] = None


class FactCheckResult(BaseModel):
    verdict: str  # TRUE, FALSE, PARTIALLY_TRUE, UNCERTAIN
    confidence: int  # 0-100
    explanation: str
    sources: list[Source] = []


class BiasResult(BaseModel):
    detected: bool
    direction: Optional[str] = None  # left-leaning, right-leaning, neutral, mixed
    indicators: list[str] = []


class AnalyzeResponse(BaseModel):
    ai_likelihood: float  # 0-1
    ai_signals: list[str] = []
    fact_check: FactCheckResult
    bias: BiasResult
    warnings: list[str] = []
    model_used: str
    latency_ms: float


# Analysis prompts
FACT_CHECK_PROMPT = """You are a professional fact-checker. Analyze this text for factual accuracy.

TEXT TO CHECK:
"{text}"

{context_section}

Analyze the claims in this text. For each significant claim:
1. Is it factually accurate?
2. What evidence supports or contradicts it?
3. Are there important nuances or context missing?

Respond with EXACTLY this JSON format:
{{
  "verdict": "TRUE" | "FALSE" | "PARTIALLY_TRUE" | "UNCERTAIN",
  "confidence": 0-100,
  "explanation": "Detailed explanation of your analysis",
  "sources": [
    {{"title": "Source name/description", "url": "URL if available", "relevance": 0.0-1.0}}
  ]
}}

IMPORTANT:
- Only cite sources you're confident exist
- If uncertain, say so clearly
- Consider the most significant claims
- PARTIALLY_TRUE means the claim has both accurate and inaccurate elements

JSON response:"""

AI_DETECTION_PROMPT = """Analyze this text for signs of AI-generated content.

TEXT:
"{text}"

Look for:
1. Repetitive sentence structures
2. Lack of specific personal details
3. Generic, "perfect" grammar
4. Hedging language patterns
5. Unusual word choices typical of LLMs
6. Overly balanced viewpoints
7. Missing colloquialisms or idioms

Respond with EXACTLY this JSON format:
{{
  "ai_likelihood": 0.0-1.0,
  "signals": ["Signal 1", "Signal 2"],
  "explanation": "Brief explanation"
}}

JSON response:"""

BIAS_DETECTION_PROMPT = """Analyze this text for political or ideological bias.

TEXT:
"{text}"

SOURCE URL: {url}

Look for:
1. Loaded language (emotionally charged words)
2. One-sided presentation
3. Cherry-picked facts
4. Missing context that would change interpretation
5. Appeals to emotion over logic
6. Stereotyping or generalizations

Respond with EXACTLY this JSON format:
{{
  "detected": true|false,
  "direction": "left-leaning" | "right-leaning" | "neutral" | "mixed",
  "indicators": ["Indicator 1", "Indicator 2"],
  "explanation": "Brief explanation"
}}

JSON response:"""


async def call_llm(prompt: str, model_id: str) -> tuple[str, float]:
    """Call LLM via OpenRouter."""
    import time
    start = time.time()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://verity-sniffer.local",
                "X-Title": "Verity Sniffer API"
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1500,
                "temperature": 0.1
            },
            timeout=60.0
        )
        
        latency = (time.time() - start) * 1000
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"LLM API error: {response.status_code}"
            )
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content, latency


def parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response."""
    try:
        # Handle code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return {}


@app.get("/")
async def root():
    """Health check."""
    return {
        "service": "Verity Sniffer API",
        "version": "0.1.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Analyze text for fact-checking, AI detection, and bias.
    
    This is the main endpoint used by the Chrome extension.
    """
    model_key = request.model or "gpt-4o"
    model_id = MODELS.get(model_key, MODELS["gpt-4o"])
    
    warnings = []
    total_latency = 0
    
    # Context section for prompt
    context_section = ""
    if request.context:
        context_section = f"\nCONTEXT FROM PAGE:\n{request.context[:500]}\n"
    if request.url:
        context_section += f"\nSOURCE URL: {request.url}\n"
    
    # 1. Fact Check
    fact_prompt = FACT_CHECK_PROMPT.format(
        text=request.text,
        context_section=context_section
    )
    fact_response, fact_latency = await call_llm(fact_prompt, model_id)
    total_latency += fact_latency
    
    fact_data = parse_json_response(fact_response)
    
    fact_check = FactCheckResult(
        verdict=fact_data.get("verdict", "UNCERTAIN"),
        confidence=fact_data.get("confidence", 50),
        explanation=fact_data.get("explanation", "Could not analyze"),
        sources=[
            Source(
                title=s.get("title", s) if isinstance(s, dict) else str(s),
                url=s.get("url") if isinstance(s, dict) else None,
                relevance=s.get("relevance") if isinstance(s, dict) else None
            )
            for s in fact_data.get("sources", [])
        ]
    )
    
    # Add warnings for low confidence
    if fact_check.confidence < 70:
        warnings.append("Low confidence - verify independently")
    
    # Check for potentially hallucinated sources
    vague_patterns = ["study shows", "research indicates", "experts say", "according to"]
    for source in fact_check.sources:
        if any(p in source.title.lower() for p in vague_patterns):
            warnings.append("Source citation may be vague or unverifiable")
            break
    
    # 2. AI Detection
    ai_prompt = AI_DETECTION_PROMPT.format(text=request.text)
    ai_response, ai_latency = await call_llm(ai_prompt, model_id)
    total_latency += ai_latency
    
    ai_data = parse_json_response(ai_response)
    ai_likelihood = ai_data.get("ai_likelihood", 0.0)
    ai_signals = ai_data.get("signals", [])
    
    if ai_likelihood > 0.7:
        warnings.append("High likelihood of AI-generated content")
    
    # 3. Bias Detection
    bias_prompt = BIAS_DETECTION_PROMPT.format(
        text=request.text,
        url=request.url or "Unknown"
    )
    bias_response, bias_latency = await call_llm(bias_prompt, model_id)
    total_latency += bias_latency
    
    bias_data = parse_json_response(bias_response)
    bias = BiasResult(
        detected=bias_data.get("detected", False),
        direction=bias_data.get("direction"),
        indicators=bias_data.get("indicators", [])
    )
    
    if bias.detected:
        warnings.append(f"Potential {bias.direction or 'ideological'} bias detected")
    
    # Always add the main disclaimer
    warnings.insert(0, "AI analysis may contain errors - verify important claims")
    
    return AnalyzeResponse(
        ai_likelihood=ai_likelihood,
        ai_signals=ai_signals,
        fact_check=fact_check,
        bias=bias,
        warnings=warnings,
        model_used=model_key,
        latency_ms=round(total_latency, 0)
    )


@app.post("/quick-check")
async def quick_check(request: AnalyzeRequest):
    """
    Quick fact-check only (faster, cheaper).
    Skips AI detection and bias analysis.
    """
    model_key = request.model or "gpt-4o"
    model_id = MODELS.get(model_key, MODELS["gpt-4o"])
    
    context_section = ""
    if request.url:
        context_section = f"\nSOURCE URL: {request.url}\n"
    
    fact_prompt = FACT_CHECK_PROMPT.format(
        text=request.text,
        context_section=context_section
    )
    
    fact_response, latency = await call_llm(fact_prompt, model_id)
    fact_data = parse_json_response(fact_response)
    
    return {
        "verdict": fact_data.get("verdict", "UNCERTAIN"),
        "confidence": fact_data.get("confidence", 50),
        "explanation": fact_data.get("explanation", "Could not analyze"),
        "model_used": model_key,
        "latency_ms": round(latency, 0),
        "warning": "AI analysis may contain errors"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
