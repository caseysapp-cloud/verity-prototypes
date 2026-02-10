# Verity Sniffer - Chrome Extension MVP

**Purpose:** Experience the product concept firsthand. Use it for a day. See failure modes in the wild.

## Features

- **Right-click to check** any selected text
- **Inline results** displayed on the page
- **Three-part analysis:**
  1. Fact Check (True/False/Partially True/Uncertain)
  2. AI Detection (likelihood of AI-generated content)
  3. Bias Detection (political/ideological lean)
- **Confidence scores** for transparency
- **Warning labels** for low confidence or potential issues
- **Feedback buttons** to report accuracy

## Installation

### 1. Start the Backend API

```bash
cd api
pip install -r requirements.txt
python main.py
# Or: uvicorn main:app --reload --port 8000
```

The API runs at http://localhost:8000

### 2. Load the Extension

1. Open Chrome
2. Go to `chrome://extensions`
3. Enable **"Developer mode"** (toggle in top right)
4. Click **"Load unpacked"**
5. Select this folder (`2-chrome-extension`)

### 3. Test It

1. Go to any news article or website
2. Select some text (10-2000 characters)
3. Right-click → **"Check with Verity 🔍"**
4. See the analysis appear inline

Or: Select text and click the floating **"🔍 Check"** button

## Configuration

Click the extension icon to open the popup and configure:

- **API URL:** Default is `http://localhost:8000`
- **Model:** Choose between GPT-4o, Claude Sonnet, or Gemini Flash

## What to Look For

### While Using the Extension

1. **Confident wrong answers:** Does it ever give high-confidence verdicts that are clearly wrong?
2. **Source quality:** When it cites sources, do they check out?
3. **Useful or annoying?** Does the UX help or hinder your reading?
4. **False alarms:** Does it flag true statements as false?

### Key Questions for Steve

- [ ] Would you pay $15/month for this?
- [ ] Did you trust it more than your own judgment?
- [ ] How often was the "Uncertain" verdict actually useful?
- [ ] Did the AI detection and bias analysis add value?

## API Endpoints

### POST /analyze
Full analysis with fact-checking, AI detection, and bias detection.

```json
{
  "text": "Text to analyze",
  "url": "Source page URL",
  "context": "Surrounding text",
  "model": "gpt-4o"
}
```

Response:
```json
{
  "ai_likelihood": 0.73,
  "ai_signals": ["repetitive structure", "lack of specific details"],
  "fact_check": {
    "verdict": "PARTIALLY_TRUE",
    "confidence": 65,
    "explanation": "...",
    "sources": [{"title": "...", "url": "...", "relevance": 0.8}]
  },
  "bias": {
    "detected": true,
    "direction": "left-leaning",
    "indicators": ["loaded language"]
  },
  "warnings": ["AI analysis may contain errors", "Low confidence"],
  "model_used": "gpt-4o",
  "latency_ms": 2340
}
```

### POST /quick-check
Fast fact-check only (skips AI/bias detection).

## Files

```
2-chrome-extension/
├── manifest.json      # Extension config
├── popup/             # Extension popup UI
├── content/           # In-page scripts and styles
├── background/        # Service worker
├── api/               # FastAPI backend
│   ├── main.py
│   └── requirements.txt
├── icons/             # Extension icons
└── README.md
```

## Limitations

1. **AI is not a fact-checker.** This tool demonstrates the inherent limitations.
2. **Sources may be hallucinated.** Always verify cited sources manually.
3. **Bias detection is subjective.** The AI's view of "bias" reflects its training.
4. **Speed vs. accuracy trade-off.** Faster models may be less accurate.

## Testing Scenarios

Try checking:

1. **A clearly false claim** - Does it catch it?
2. **A clearly true statement** - Does it mark it correctly?
3. **A nuanced claim** - Does it understand context?
4. **AI-generated text** - Does AI detection work?
5. **An opinion piece** - Does bias detection trigger?

The goal is to understand where this approach breaks down.
