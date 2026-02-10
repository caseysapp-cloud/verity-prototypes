# Verity Sniffer - LLM Hallucination Torture Test

**Purpose:** Empirically test whether LLMs can reliably fact-check content.

## The Question This Answers

> "Can LLMs accurately distinguish true from false statements?"

If accuracy is below 85%, or false positive rate exceeds 15%, the core Verity Sniffer product thesis is invalid.

## What's Tested

- **100 curated claims** (50 true, 50 false)
- **Categories:** Science, Health, Politics, History, Current Events
- **Edge cases:** Technically true but misleading, outdated facts, common myths

### Models Tested

1. **GPT-4o** (OpenAI's flagship)
2. **Claude Sonnet** (Anthropic's balanced model)
3. **Gemini Flash** (Google's fast model)

## How to Run

### Prerequisites

```bash
pip install httpx python-dotenv
```

### Run the Test

```bash
cd 1-torture-test
python test_runner.py
```

**Takes approximately 10-15 minutes** (100 claims × 3 models with rate limiting)

### View Results

```bash
cat results/report.md
```

## What to Look For

### ❌ Product is DOA if:
- Overall accuracy < 85%
- False positive rate > 15% (marking true statements as false)
- Hallucinated sources > 10%

### ✅ Cautiously proceed if:
- All models exceed 85% accuracy
- False positive rate < 15%
- Sources are verifiable

## Understanding the Output

### Accuracy
How often the LLM correctly identifies true vs false claims.

### False Positive Rate
When a TRUE statement is incorrectly marked FALSE. This is especially bad for a "trust layer" - users will lose confidence when correct information is flagged.

### False Negative Rate
When a FALSE statement is incorrectly marked TRUE. This means misinformation gets through.

### Hallucination Rate
How often the LLM cites vague or fabricated sources. A "trust layer" that invents sources is dangerous.

## Sample Claims

**True (should be marked TRUE):**
- "Water boils at 100 degrees Celsius at sea level."
- "The Berlin Wall fell in 1989."
- "Birds are descendants of dinosaurs."

**False (should be marked FALSE):**
- "Vaccines cause autism."
- "The Great Wall of China is visible from space with the naked eye."
- "Humans only use 10% of their brain."

**Edge Cases (tricky):**
- "The Declaration of Independence was signed on July 4, 1776." (FALSE - most signatures were August 2)
- "The Amazon rainforest produces 20% of the world's oxygen." (FALSE - net contribution is near zero)

## Files

- `claims.json` — The 100 curated claims with ground truth labels
- `test_runner.py` — The test harness
- `results/report.md` — Generated report with statistics
- `results/raw_results.json` — Full results data
