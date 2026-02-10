# Verity Sniffer - Source Aggregator

**Purpose:** Demonstrate what ACTUALLY works — aggregating existing fact-checks from professional fact-checkers rather than generating new analysis with AI.

## The Point This Makes

If existing fact-checkers have already rated a claim, **what value does AI add?**

This prototype shows the "already solved" problem. Google's Fact Check API (free!) aggregates fact-checks from:
- Snopes
- PolitiFact
- AFP Fact Check
- Reuters
- AP Fact Check
- Full Fact
- And 100+ other sources

## Usage

```bash
cd 3-source-aggregator
python aggregator.py "The 2020 election was stolen"
```

### Example Output

```
🔍 Searching for fact-checks: "The 2020 election was stolen"
--------------------------------------------------

============================================================
FACT-CHECK AGGREGATION RESULTS
============================================================

Query: "The 2020 election was stolen"
Sources checked: Google Fact Check API, Snopes, PolitiFact, Reuters
Total fact-checks found: 12

────────────────────────────────────────────────────────────
CONSENSUS: LIKELY FALSE - Multiple fact-checkers rated this claim false
────────────────────────────────────────────────────────────

Individual Fact-Checks:

  1. [PolitiFact] Pants on Fire
     Claim: Claim that 2020 election was stolen...
     URL: https://www.politifact.com/factchecks/...
     Date: 2020-12-01

  2. [AP Fact Check] False
     Claim: There was widespread fraud in the 2020 election...
     URL: https://apnews.com/article/...
     
  ... (more results)

============================================================
NOTE: This aggregator shows EXISTING fact-checks only.
It does not generate new analysis - that's the point.
============================================================
```

## Sources Integrated

### Currently Implemented
1. **Google Fact Check API** (requires API key, free tier)
2. **Snopes** (web scraping, fragile)
3. **PolitiFact** (web scraping, fragile)
4. **Reuters Fact Check** (placeholder)

### Could Add
- AFP Fact Check
- AP Fact Check
- Full Fact (UK)
- ClaimBuster API
- Lead Stories
- USA Today Fact Check

## Key Insights for Steve

### 1. The Coverage Problem
For any **viral misinformation**, fact-checkers have probably already covered it. The AI adds nothing.

### 2. The Novelty Problem
For **new or niche claims**, fact-checkers haven't covered it yet. The AI hallucinates.

### 3. The Trust Problem
Users who distrust mainstream fact-checkers will also distrust an AI trained on those same fact-checkers.

### 4. The Economic Problem
Google's Fact Check API is **free**. Why would users pay for AI analysis?

## The Question This Raises

> If Google already provides free fact-check aggregation, and professional fact-checkers have already covered most viral claims, what is Verity Sniffer's unique value proposition?

### Possible Answers:
1. **UX** - Better presentation of existing fact-checks (but that's a feature, not a company)
2. **Speed** - Faster than waiting for fact-checkers (but AI accuracy is worse)
3. **Novel claims** - Claims not yet fact-checked (but AI hallucinates on these)
4. **Enterprise** - Different market entirely (see Prototype 4)

## Requirements

```bash
pip install httpx python-dotenv
```

## Environment

Optionally set in `~/.openclaw/workspace/.env.shared`:
```
GOOGLE_API_KEY=your_key_here  # For Google Fact Check API
```

The tool works without API keys but returns fewer results.

## Files

```
3-source-aggregator/
├── aggregator.py      # Main aggregator script
├── sources/           # Individual source adapters (future)
├── results/           # Saved search results
└── README.md
```
