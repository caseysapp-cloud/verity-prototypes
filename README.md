# Verity Sniffer — De-Risking Prototypes

**For:** Steve Beck (friend of Casey)  
**Purpose:** Let you SEE the problems (or prove us wrong) rather than just hear about them

## The Context

You're raising $2M for a browser extension that uses LLMs to fact-check content. These prototypes test whether that core thesis holds up.

## The Hypothesis Being Tested

> Can LLMs reliably serve as a "trust layer" for web content?

These four prototypes answer that question empirically.

---

## Quick Start (5 Minutes)

```bash
# Clone the repo
git clone https://github.com/caseysapp-cloud/verity-prototypes.git
cd verity-prototypes

# Copy env and add your OpenRouter API key
cp .env.example .env
# Edit .env and add your key from https://openrouter.ai/keys

# Install dependencies
pip install -r requirements.txt

# Run the torture test (most important)
cd 1-torture-test
python test_runner.py

# See the results
cat results/report.md
```

---

## The Four Prototypes

### 1. Hallucination Torture Test ⭐ START HERE
**Folder:** `1-torture-test/`

Tests whether LLMs can reliably fact-check 100 curated claims.

**What it proves:** If accuracy < 85% or false positive rate > 15%, the product thesis is invalid.

```bash
cd 1-torture-test
python test_runner.py
```

### 2. Chrome Extension MVP
**Folder:** `2-chrome-extension/`

A working browser extension so you can EXPERIENCE the product for a day.

**What it proves:** Does the UX feel valuable? What failure modes exist in the wild?

```bash
# Start backend
cd 2-chrome-extension/api
uvicorn main:app --reload

# Load extension in Chrome:
# 1. Go to chrome://extensions
# 2. Enable "Developer mode"
# 3. Click "Load unpacked"
# 4. Select the 2-chrome-extension folder
```

### 3. Source Aggregator
**Folder:** `3-source-aggregator/`

Aggregates EXISTING fact-checks from Snopes, PolitiFact, etc.

**What it proves:** If existing fact-checkers have already covered a claim, what value does AI add?

```bash
cd 3-source-aggregator
python aggregator.py "The 2020 election was stolen"
```

### 4. Enterprise Guardrails
**Folder:** `4-enterprise-guardrails/`

LLM wrapper with trust scoring for compliance teams.

**What it proves:** Is B2B (auditability for enterprises) a better market than B2C (truth for consumers)?

```bash
# CLI demo
cd 4-enterprise-guardrails
python guardrails.py

# Web dashboard
cd dashboard
python app.py
# Open http://localhost:5000
```

---

## What to Evaluate

### After Running the Torture Test

| Question | Target | If Missed |
|----------|--------|-----------|
| Overall accuracy | > 85% | Product is DOA |
| False positive rate | < 15% | Users will revolt |
| Hallucinated sources | < 10% | "Trust layer" is ironic |

### After Using the Extension

- [ ] Did it give confident wrong answers?
- [ ] Did you trust it more than your own judgment?
- [ ] Would you pay $15/month for this?
- [ ] Did the "sources" check out when verified?

### After Seeing the Aggregator

- [ ] For claims you tested, did existing fact-checkers already cover them?
- [ ] What's the marginal value of AI over aggregation?

### After the Enterprise Demo

- [ ] Would a compliance officer pay for this audit trail?
- [ ] Is "guardrails for agents" a better market than "truth for consumers"?

---

## The Hard Questions

### 1. Can LLMs fact-check reliably?
The torture test answers this empirically. If accuracy is below 85%, the core product doesn't work.

### 2. Is the problem already solved?
Google's Fact Check API aggregates existing fact-checks for free. The aggregator shows what this looks like.

### 3. Will consumers pay?
History says no. NewsGuard (similar concept) has struggled with consumer adoption and is now facing FTC scrutiny.

### 4. Is there a better market?
Enterprise compliance is a real budget line. The guardrails demo shows a potential pivot.

---

## Technical Requirements

```bash
# Python 3.9+
pip install httpx python-dotenv fastapi uvicorn pillow pydantic

# Environment (already configured)
# Uses ~/.openclaw/workspace/.env.shared for API keys
# OpenRouter provides access to GPT-4o, Claude, Gemini
```

---

## Files Structure

```
verity-prototypes/
├── README.md                 # This file
├── SPEC.md                   # Technical specification
├── 1-torture-test/           # LLM accuracy testing
│   ├── claims.json           # 100 curated claims
│   ├── test_runner.py        # Test harness
│   ├── results/              # Generated reports
│   └── README.md
├── 2-chrome-extension/       # Browser extension
│   ├── manifest.json
│   ├── popup/
│   ├── content/
│   ├── background/
│   ├── api/                  # FastAPI backend
│   └── README.md
├── 3-source-aggregator/      # Fact-check aggregation
│   ├── aggregator.py
│   └── README.md
└── 4-enterprise-guardrails/  # B2B pivot demo
    ├── guardrails.py
    ├── dashboard/
    └── README.md
```

---

## Expected Outcome

After 2 hours with these tools, you should be able to answer:

1. ✅ or ❌ **Can LLMs fact-check reliably?** (Torture test)
2. ✅ or ❌ **Does the UX feel valuable?** (Extension)
3. ✅ or ❌ **Is the problem already solved?** (Aggregator)
4. ✅ or ❌ **Is B2B a better market?** (Enterprise demo)

The goal isn't to kill your idea — it's to de-risk it before you commit $2M.

---

## Support

These prototypes were built by Casey's AI assistant. If you have questions or want modifications, reach out to Casey.

*Built with care. Test with skepticism.*
