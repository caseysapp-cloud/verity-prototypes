# Verity Sniffer — De-Risking Prototypes

**For:** Steve Beck  
**From:** Casey Sapp  
**Purpose:** Test the technical reality before you take the $2M

---

## What This Is

You're raising $2M for a browser extension that uses LLMs to fact-check content. Before you pitch, you need data. I built four prototypes to stress-test the core "Trust Layer" thesis.

**The Hypothesis:** Can LLMs reliably serve as a "trust layer" for web content?

These tools answer that question empirically.

---

## Prerequisites

Before you start, you'll need:

1. **Python 3.9+** — Check with `python3 --version`
   - Mac: `brew install python3`
   - Windows: Download from [python.org](https://www.python.org/downloads/)

2. **An OpenRouter API Key** (free tier available)
   - Go to [openrouter.ai/keys](https://openrouter.ai/keys)
   - Create an account and generate an API key
   - Free tier gives you limited calls to GPT-4o, Claude, Gemini

3. **Git** — To clone this repo
   - Mac: `xcode-select --install`
   - Windows: Download from [git-scm.com](https://git-scm.com/)

---

## Quick Start (10 Minutes)

```bash
# 1. Clone the repo
git clone https://github.com/caseysapp-cloud/verity-prototypes.git
cd verity-prototypes

# 2. Set up your API key
cp .env.example .env
# Open .env in any text editor and paste your OpenRouter key

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the torture test (START HERE)
cd 1-torture-test
python3 test_runner.py

# 5. See the results
cat results/report.md
```

---

## The Four Prototypes

### 1. Hallucination Torture Test ⭐ START HERE
**Folder:** `1-torture-test/`

A script running 100 curated hard/edge-case claims against GPT-4o, Claude, and Gemini. This measures whether AI can actually fact-check without hallucinating.

**Pass Criteria:**
- Accuracy > 85%
- False positive rate < 15%
- Hallucinated sources < 10%

**If it fails:** The core product promise is broken.

```bash
cd 1-torture-test
python3 test_runner.py

# Quick test (2 min instead of 15):
python3 quick_test.py
```

---

### 2. Chrome Extension MVP
**Folder:** `2-chrome-extension/`

A working Manifest V3 extension with a FastAPI backend. Real-time fact-checking, AI likelihood scoring, and bias detection on any selected text.

**Known Issue:** The MVP makes three sequential LLM calls (Fact → AI Detect → Bias). This takes 3–5 seconds — an eternity in a browsing context.

```bash
# Terminal 1: Start the backend
cd 2-chrome-extension/api
uvicorn main:app --reload --port 8000

# Keep this running, then in Chrome:
# 1. Go to chrome://extensions
# 2. Enable "Developer mode" (top right toggle)
# 3. Click "Load unpacked"
# 4. Select the 2-chrome-extension folder
# 5. Browse any news site, select text, right-click → "Check with Verity"
```

---

### 3. Source Aggregator — "The Pepsi Challenge"
**Folder:** `3-source-aggregator/`

Queries Google Fact Check API, Snopes, and PolitiFact. Tests if "free" tools already solve the problem.

**The Question:** If Google's free API answers 80% of queries correctly, are you building a tech company or a UI wrapper?

```bash
cd 3-source-aggregator
python3 aggregator.py "COVID vaccines cause autism"
python3 aggregator.py "The 2020 election was stolen"
python3 aggregator.py "Climate change is a hoax"
```

---

### 4. Enterprise Guardrails — The Pivot Option
**Folder:** `4-enterprise-guardrails/`

Instead of checking news for consumers, this wraps LLMs for enterprise use. Flags hedging, vague citations, and confidence mismatches.

**Why This Matters:** Consumers rarely pay for "truth" — they pay for confirmation. But enterprises pay for compliance.

```bash
# CLI demo
cd 4-enterprise-guardrails
python3 guardrails.py

# Web dashboard
cd dashboard
uvicorn app:app --reload --port 5000
# Open http://localhost:5000
```

---

## The Validation Phases

### Phase 1: Run the Torture Test (Days 1–5)

Run `test_runner.py` against the 100 claims.

| Result | Accuracy | Action |
|--------|----------|--------|
| ✅ **PASS** | > 85%, < 10% hallucinated sources | Proceed with current pitch |
| ❌ **FAIL** | Anything less | Pivot the tech stack or business model |

---

### Phase 2: The "Pepsi Challenge" (Days 5–10)

Use the Source Aggregator. Answer these questions:

- Does Google's free Fact Check API answer 80%+ of queries?
- Can you prove your "Ensemble" model adds marginal value over free APIs?
- What's the actual gap you're filling?

---

### Phase 3: The Enterprise Pivot (Backup Plan)

If consumer "trust" fails the tests above:

- Take the Guardrails prototype
- Pitch to compliance officers (finance/legal) as an "AI Audit Layer"
- Same tech, but the customer has a budget

---

## Critical Risks Identified

### 1. The Latency Problem
3–5 second analysis time is too slow for real-time browsing. Users won't wait.

### 2. The "Circular Logic" Trap
Using an LLM to check for hallucinations is dangerous. Models often hallucinate the *correction* just as confidently as the original error.

### 3. The "Who Pays?" Issue
NewsGuard (similar concept) has struggled with consumer adoption and is now facing FTC scrutiny. Enterprise compliance is a clearer path to revenue.

---

## Evaluation Checklist

After 2 hours with these tools, answer:

### Torture Test Results
- [ ] Overall accuracy > 85%?
- [ ] False positive rate < 15%?
- [ ] Hallucinated sources < 10%?
- [ ] Any model significantly better than others?

### Chrome Extension Experience
- [ ] Did it give confident wrong answers?
- [ ] Did you trust it more than your own judgment?
- [ ] Would you pay $15/month for this?
- [ ] Did cited "sources" check out when you verified them?
- [ ] Was the 3-5 second latency acceptable?

### Source Aggregator Comparison
- [ ] For claims tested, did existing fact-checkers already cover them?
- [ ] What's the marginal value of AI over free aggregation?

### Enterprise Pivot Viability
- [ ] Would a compliance officer pay for this audit trail?
- [ ] Is "guardrails for agents" a better market than "truth for consumers"?

---

## File Structure

```
verity-prototypes/
├── README.md                 # This file
├── .env.example              # Copy to .env, add your API key
├── requirements.txt          # Python dependencies
├── 1-torture-test/           # LLM accuracy testing
│   ├── claims.json           # 100 curated claims
│   ├── test_runner.py        # Full test (15 min)
│   ├── quick_test.py         # Quick test (2 min)
│   └── results/              # Generated reports
├── 2-chrome-extension/       # Browser extension MVP
│   ├── manifest.json
│   ├── popup/                # Extension UI
│   ├── content/              # Page injection
│   ├── background/           # Service worker
│   └── api/                  # FastAPI backend
├── 3-source-aggregator/      # Fact-check aggregation
│   └── aggregator.py         # CLI tool
└── 4-enterprise-guardrails/  # B2B pivot demo
    ├── guardrails.py         # Core library
    └── dashboard/            # Web UI
```

---

## Troubleshooting

### "OPENROUTER_API_KEY not found"
Make sure you:
1. Copied `.env.example` to `.env`
2. Added your actual API key (not the placeholder)
3. Are running from the project root or correct subfolder

### "ModuleNotFoundError"
Run `pip install -r requirements.txt` from the project root.

### Chrome extension not working
1. Make sure the API server is running (`uvicorn main:app --reload --port 8000`)
2. Check the browser console for errors (F12 → Console)
3. Reload the extension after any code changes

### Rate limits
OpenRouter free tier has limits. If you hit them:
- Wait a few minutes
- Or upgrade to a paid tier at openrouter.ai

---

## Bottom Line

The goal isn't to kill your idea — it's to de-risk it before you commit $2M.

Run the numbers. Let the data speak.

*Built by Casey's AI assistant. Test with skepticism.*
