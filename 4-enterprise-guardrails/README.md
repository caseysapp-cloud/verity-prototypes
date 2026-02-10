# Verity Sniffer - Enterprise Guardrails Demo

**Purpose:** Demonstrate the B2B pivot where the real market is. Compliance officers have budget. Consumers don't.

## The Insight

**Consumer market problems:**
- No willingness to pay for "truth verification"
- LLMs can't reliably fact-check anyway
- Political minefield (see: NewsGuard controversies)

**Enterprise market opportunity:**
- Compliance officers need audit trails
- Legal teams need defensible AI usage
- Financial services need trust scores
- Healthcare needs citation verification

**The reframe:** Instead of "truth for consumers," offer "auditability for enterprises."

## What This Demonstrates

A wrapper for any LLM that provides:

### Trust Scoring (0-100)
Every response gets a trust score based on:
- Hedging language ("I think", "probably", "might")
- Citation presence and quality
- Confidence without substantiation
- Temporal confusion indicators
- Contradictions with prior responses

### Flag Categories
1. **Hedging** — Uncertain language detected
2. **Phantom Citation** — Vague sources that may be hallucinated
3. **Confidence Mismatch** — High certainty without citations
4. **Temporal** — References to time that may indicate stale knowledge
5. **Contradiction** — Inconsistent with earlier responses

### Compliance Features
- Session audit trail
- Exportable compliance reports
- Low-trust response flagging
- Real-time dashboard

## Usage

### CLI Demo

```bash
cd 4-enterprise-guardrails
python guardrails.py
```

Interactive chat with trust scoring on every response.

### Web Dashboard

```bash
cd 4-enterprise-guardrails/dashboard
pip install fastapi uvicorn
python app.py
# Or: uvicorn app:app --reload --port 5000
```

Open http://localhost:5000

## What Compliance Officers Care About

### NOT what Verity originally pitched:
- ❌ "Is this statement true or false?"
- ❌ "Detect AI-generated content"
- ❌ "Expose bias in media"

### WHAT they actually need:
- ✅ "Can we prove we monitored AI outputs?"
- ✅ "Did the AI express unwarranted confidence?"
- ✅ "Are there fabricated citations we need to flag?"
- ✅ "What's our audit trail if something goes wrong?"

## Example Session

```
You: What are the side effects of aspirin?

─────────────────────────────────────────────
Trust Score: 72/100
⚠️ Warnings: Potential hallucinated citations detected
Flags: 2
  - [MEDIUM] phantom_citation: Vague citations that may be hallucinated
  - [LOW] hedging: Some hedging language (3 instances)
─────────────────────────────────────────────