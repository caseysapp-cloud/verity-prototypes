#!/usr/bin/env python3
"""
Verity Sniffer - LLM Hallucination Torture Test
Tests whether LLMs can reliably fact-check claims.
"""

import json
import os
import time
import asyncio
import httpx
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from dotenv import load_dotenv

# Load environment - try project root first, then current directory
env_path = Path(__file__).parent.parent / ".env"
if not env_path.exists():
    env_path = Path(".env")
load_dotenv(env_path)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found. Copy .env.example to .env and add your key.")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Models to test via OpenRouter
MODELS = {
    "gpt-4o": "openai/gpt-4o",
    "claude-sonnet": "anthropic/claude-sonnet-4",
    "gemini-flash": "google/gemini-2.0-flash-001",
}

# Test prompts (different approaches)
PROMPTS = {
    "direct": """You are a fact-checker. Evaluate whether this claim is TRUE or FALSE.

Claim: "{claim}"

Respond with EXACTLY this JSON format:
{{
  "verdict": "TRUE" or "FALSE",
  "confidence": 0-100,
  "explanation": "Brief explanation",
  "sources": ["Source 1", "Source 2"]
}}

JSON response:""",

    "chain_of_thought": """You are a fact-checker. Think step by step to evaluate this claim.

Claim: "{claim}"

Step 1: What is the claim asserting?
Step 2: What evidence exists for/against this?
Step 3: What is the consensus view?
Step 4: Final verdict

Respond with EXACTLY this JSON format at the end:
{{
  "verdict": "TRUE" or "FALSE",
  "confidence": 0-100,
  "explanation": "Brief explanation",
  "sources": ["Source 1", "Source 2"]
}}

Analysis and JSON response:""",

    "source_required": """You are a fact-checker. ONLY mark a claim as TRUE if you can cite a specific, verifiable source.

Claim: "{claim}"

Rules:
- If you cannot cite a real, verifiable source, mark as UNCERTAIN
- Do not make up sources
- Be specific with source names

Respond with EXACTLY this JSON format:
{{
  "verdict": "TRUE", "FALSE", or "UNCERTAIN",
  "confidence": 0-100,
  "explanation": "Brief explanation",
  "sources": ["Specific source with details"]
}}

JSON response:""",

    "confidence_calibrated": """You are a calibrated fact-checker. Rate your confidence 0-100.
- Only give a TRUE/FALSE verdict if confidence > 80
- Otherwise say UNCERTAIN

Claim: "{claim}"

Respond with EXACTLY this JSON format:
{{
  "verdict": "TRUE", "FALSE", or "UNCERTAIN",
  "confidence": 0-100,
  "explanation": "Brief explanation",
  "sources": ["Source if applicable"]
}}

JSON response:"""
}


@dataclass
class CheckResult:
    claim_id: int
    claim_text: str
    ground_truth: bool
    model: str
    prompt_type: str
    verdict: Optional[str] = None
    confidence: Optional[int] = None
    explanation: Optional[str] = None
    sources: list = field(default_factory=list)
    latency_ms: float = 0
    error: Optional[str] = None
    raw_response: Optional[str] = None


@dataclass
class TestReport:
    timestamp: str
    total_claims: int
    models_tested: list
    prompt_types: list
    results: list = field(default_factory=list)
    
    # Computed stats per model
    accuracy_by_model: dict = field(default_factory=dict)
    false_positive_rate: dict = field(default_factory=dict)
    false_negative_rate: dict = field(default_factory=dict)
    hallucinated_sources: dict = field(default_factory=dict)
    avg_latency_ms: dict = field(default_factory=dict)


def parse_llm_response(response_text: str) -> dict:
    """Extract JSON from LLM response."""
    try:
        # Try to find JSON in response
        text = response_text.strip()
        
        # Look for JSON block
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
            json_str = text[start:end]
            return json.loads(json_str)
    except Exception:
        pass
    
    return {}


async def call_llm(client: httpx.AsyncClient, model_key: str, model_id: str, prompt: str) -> tuple[str, float]:
    """Call LLM via OpenRouter."""
    start_time = time.time()
    
    try:
        response = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://verity-sniffer.test",
                "X-Title": "Verity Sniffer Torture Test"
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.1  # Low temp for consistency
            },
            timeout=60.0
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        if response.status_code != 200:
            return f"ERROR: {response.status_code} - {response.text}", latency_ms
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content, latency_ms
        
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return f"ERROR: {str(e)}", latency_ms


async def test_claim(
    client: httpx.AsyncClient,
    claim: dict,
    model_key: str,
    model_id: str,
    prompt_type: str
) -> CheckResult:
    """Test a single claim against a model."""
    prompt_template = PROMPTS[prompt_type]
    prompt = prompt_template.format(claim=claim["text"])
    
    response, latency_ms = await call_llm(client, model_key, model_id, prompt)
    
    result = CheckResult(
        claim_id=claim["id"],
        claim_text=claim["text"],
        ground_truth=claim["label"],
        model=model_key,
        prompt_type=prompt_type,
        latency_ms=latency_ms,
        raw_response=response[:500]  # Truncate for storage
    )
    
    if response.startswith("ERROR:"):
        result.error = response
        return result
    
    parsed = parse_llm_response(response)
    
    if parsed:
        verdict_str = parsed.get("verdict", "").upper()
        if "TRUE" in verdict_str:
            result.verdict = "TRUE"
        elif "FALSE" in verdict_str:
            result.verdict = "FALSE"
        else:
            result.verdict = "UNCERTAIN"
        
        result.confidence = parsed.get("confidence", 0)
        result.explanation = parsed.get("explanation", "")
        result.sources = parsed.get("sources", [])
    else:
        result.error = "Failed to parse JSON response"
    
    return result


def is_correct(result: CheckResult) -> bool:
    """Check if the LLM verdict matches ground truth."""
    if result.verdict is None or result.verdict == "UNCERTAIN":
        return False
    
    llm_says_true = result.verdict == "TRUE"
    return llm_says_true == result.ground_truth


def is_false_positive(result: CheckResult) -> bool:
    """LLM said FALSE when claim is actually TRUE."""
    if result.verdict is None:
        return False
    return result.ground_truth == True and result.verdict == "FALSE"


def is_false_negative(result: CheckResult) -> bool:
    """LLM said TRUE when claim is actually FALSE."""
    if result.verdict is None:
        return False
    return result.ground_truth == False and result.verdict == "TRUE"


def detect_hallucinated_sources(sources: list) -> list:
    """
    Detect likely hallucinated sources.
    Heuristics: generic names, non-existent URLs, vague references
    """
    hallucination_patterns = [
        "study shows", "research indicates", "experts say",
        "according to research", "scientific studies",
        "various sources", "multiple studies", "it is known",
        "common knowledge", "widely accepted"
    ]
    
    hallucinated = []
    for source in sources:
        source_lower = source.lower()
        # Check for vague patterns
        if any(pattern in source_lower for pattern in hallucination_patterns):
            hallucinated.append(source)
        # Check for suspiciously generic URLs
        elif "example.com" in source_lower or "source.com" in source_lower:
            hallucinated.append(source)
    
    return hallucinated


def compute_stats(results: list[CheckResult]) -> dict:
    """Compute statistics from results."""
    stats = {}
    
    # Group by model
    by_model = {}
    for r in results:
        if r.model not in by_model:
            by_model[r.model] = []
        by_model[r.model].append(r)
    
    for model, model_results in by_model.items():
        valid_results = [r for r in model_results if r.verdict is not None and r.error is None]
        
        if not valid_results:
            continue
        
        correct = sum(1 for r in valid_results if is_correct(r))
        fp = sum(1 for r in valid_results if is_false_positive(r))
        fn = sum(1 for r in valid_results if is_false_negative(r))
        
        # Count true claims and false claims
        true_claims = [r for r in valid_results if r.ground_truth == True]
        false_claims = [r for r in valid_results if r.ground_truth == False]
        
        # Hallucinated sources
        all_sources = []
        for r in valid_results:
            all_sources.extend(r.sources)
        hallucinated = detect_hallucinated_sources(all_sources)
        
        stats[model] = {
            "total_tested": len(valid_results),
            "correct": correct,
            "accuracy": round(correct / len(valid_results) * 100, 1) if valid_results else 0,
            "false_positives": fp,
            "false_positive_rate": round(fp / len(true_claims) * 100, 1) if true_claims else 0,
            "false_negatives": fn,
            "false_negative_rate": round(fn / len(false_claims) * 100, 1) if false_claims else 0,
            "hallucinated_source_count": len(hallucinated),
            "hallucination_rate": round(len(hallucinated) / len(all_sources) * 100, 1) if all_sources else 0,
            "avg_latency_ms": round(sum(r.latency_ms for r in valid_results) / len(valid_results), 0),
            "errors": sum(1 for r in model_results if r.error)
        }
    
    return stats


def generate_report(results: list[CheckResult], claims: list) -> str:
    """Generate markdown report."""
    stats = compute_stats(results)
    
    report = f"""# Verity Sniffer - LLM Fact-Check Torture Test Results

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Claims Tested:** {len(claims)}
**Models Tested:** {', '.join(MODELS.keys())}

---

## Executive Summary

"""
    
    # Determine overall verdict
    all_accuracies = [s["accuracy"] for s in stats.values()]
    avg_accuracy = sum(all_accuracies) / len(all_accuracies) if all_accuracies else 0
    
    all_fp_rates = [s["false_positive_rate"] for s in stats.values()]
    avg_fp_rate = sum(all_fp_rates) / len(all_fp_rates) if all_fp_rates else 0
    
    all_hall_rates = [s["hallucination_rate"] for s in stats.values()]
    avg_hall_rate = sum(all_hall_rates) / len(all_hall_rates) if all_hall_rates else 0
    
    if avg_accuracy < 85:
        report += f"""### ❌ PRODUCT THESIS INVALID

Average accuracy across models: **{avg_accuracy:.1f}%** (threshold: 85%)

LLMs cannot reliably fact-check content. The core product assumption is false.

"""
    else:
        report += f"""### ✅ Accuracy Threshold Met

Average accuracy across models: **{avg_accuracy:.1f}%** (threshold: 85%)

"""
    
    if avg_fp_rate > 15:
        report += f"""### ⚠️ HIGH FALSE POSITIVE RATE

Average false positive rate: **{avg_fp_rate:.1f}%** (threshold: 15%)

Users will lose trust quickly when true statements are marked false.

"""
    
    if avg_hall_rate > 10:
        report += f"""### ⚠️ HALLUCINATED SOURCES DETECTED

Average hallucination rate: **{avg_hall_rate:.1f}%** (threshold: 10%)

A "trust layer" that invents sources is ironic and dangerous.

"""
    
    report += """---

## Model Comparison

| Model | Accuracy | False Positive Rate | False Negative Rate | Hallucination Rate | Avg Latency |
|-------|----------|--------------------|--------------------|-------------------|-------------|
"""
    
    for model, s in stats.items():
        report += f"| {model} | {s['accuracy']}% | {s['false_positive_rate']}% | {s['false_negative_rate']}% | {s['hallucination_rate']}% | {s['avg_latency_ms']}ms |\n"
    
    report += """
---

## Worst Failures (Embarrassing Examples)

"""
    
    # Find worst failures
    failures = []
    for r in results:
        if r.error:
            continue
        if is_false_positive(r):
            failures.append((r, "FALSE_POSITIVE", "Marked TRUE claim as FALSE"))
        elif is_false_negative(r):
            failures.append((r, "FALSE_NEGATIVE", "Marked FALSE claim as TRUE"))
    
    # Show worst 10
    for r, fail_type, desc in failures[:10]:
        report += f"""### {fail_type}: {r.model}

**Claim:** "{r.claim_text}"

**Ground Truth:** {"TRUE" if r.ground_truth else "FALSE"}  
**LLM Verdict:** {r.verdict} (Confidence: {r.confidence}%)  
**Error Type:** {desc}

**Explanation:** {r.explanation or "None provided"}

---

"""
    
    report += """## Detailed Statistics by Model

"""
    
    for model, s in stats.items():
        report += f"""### {model}

- **Total Tested:** {s['total_tested']}
- **Correct:** {s['correct']} ({s['accuracy']}%)
- **False Positives:** {s['false_positives']} ({s['false_positive_rate']}% of true claims)
- **False Negatives:** {s['false_negatives']} ({s['false_negative_rate']}% of false claims)
- **Hallucinated Sources:** {s['hallucinated_source_count']} ({s['hallucination_rate']}% of cited sources)
- **Average Latency:** {s['avg_latency_ms']}ms
- **Errors:** {s['errors']}

"""
    
    report += """---

## Methodology

1. **100 curated claims** (50 true, 50 false) across categories:
   - Science, Health, Politics, History, Current Events
   - Mix of easy, medium, and hard difficulty
   - Includes edge cases (technically true but misleading, outdated facts)

2. **Testing approach:**
   - "direct" prompt: Simple true/false request
   - Temperature: 0.1 (for consistency)
   - Each model tested via OpenRouter

3. **Metrics:**
   - **Accuracy:** Correct verdicts / total tested
   - **False Positive Rate:** True claims marked false / total true claims
   - **False Negative Rate:** False claims marked true / total false claims
   - **Hallucination Rate:** Vague/fabricated sources / total sources cited

---

## Implications for Verity Sniffer

"""
    
    if avg_accuracy < 85 or avg_fp_rate > 15 or avg_hall_rate > 10:
        report += """### The Data Shows Fundamental Problems

1. **LLMs are not reliable fact-checkers.** Even on curated, clear-cut claims, accuracy is insufficient.

2. **False positives destroy user trust.** When the tool marks true statements as false, users stop believing it.

3. **Hallucinated sources undermine the "trust layer" premise.** A tool that invents citations is worse than useless.

### Recommendations

- **Do not proceed** with LLM-based fact-checking as the core product
- **Consider pivoting** to source aggregation (existing fact-checks) or enterprise guardrails (B2B market)
- **If proceeding anyway:** Include prominent disclaimers and never claim to be a "trust layer"

"""
    else:
        report += """### Cautiously Optimistic

The models met basic accuracy thresholds on this test set. However:

1. **This is a curated set.** Real-world claims are messier.
2. **Edge cases remain problematic.** Nuanced claims still trip up the models.
3. **Sources need verification.** Cannot trust LLM citations without checking.

### Recommendations

- Proceed with extensive disclaimers
- Always surface "confidence" to users
- Consider hybrid approach: LLM + source aggregation
- Build in human feedback loop

"""
    
    report += f"""---

*Report generated by Verity Sniffer Torture Test v1.0*
*{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    return report


async def main():
    """Run the torture test."""
    print("=" * 60)
    print("VERITY SNIFFER - LLM HALLUCINATION TORTURE TEST")
    print("=" * 60)
    print()
    
    # Load claims
    claims_path = Path(__file__).parent / "claims.json"
    with open(claims_path) as f:
        data = json.load(f)
    claims = data["claims"]
    
    print(f"Loaded {len(claims)} claims")
    print(f"Models: {', '.join(MODELS.keys())}")
    print()
    
    results = []
    
    async with httpx.AsyncClient() as client:
        # Test each model with direct prompt (primary test)
        for model_key, model_id in MODELS.items():
            print(f"\nTesting {model_key}...")
            
            for i, claim in enumerate(claims):
                result = await test_claim(
                    client, claim, model_key, model_id, "direct"
                )
                results.append(result)
                
                # Progress
                status = "✓" if is_correct(result) else "✗"
                if result.error:
                    status = "E"
                print(f"  [{i+1:3d}/100] {status} {claim['text'][:50]}...")
                
                # Rate limiting - be nice to the API
                await asyncio.sleep(0.5)
    
    # Generate report
    print("\n" + "=" * 60)
    print("GENERATING REPORT...")
    print("=" * 60)
    
    report = generate_report(results, claims)
    
    # Save report
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    report_path = results_dir / "report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")
    
    # Save raw results as JSON
    results_json_path = results_dir / "raw_results.json"
    with open(results_json_path, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"Raw results saved to: {results_json_path}")
    
    # Print summary
    stats = compute_stats(results)
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for model, s in stats.items():
        print(f"\n{model}:")
        print(f"  Accuracy: {s['accuracy']}%")
        print(f"  False Positive Rate: {s['false_positive_rate']}%")
        print(f"  False Negative Rate: {s['false_negative_rate']}%")


if __name__ == "__main__":
    asyncio.run(main())
