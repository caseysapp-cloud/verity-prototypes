#!/usr/bin/env python3
"""
Quick test - runs a subset of claims for demo purposes.
Full test takes 15+ minutes; this takes ~2 minutes.
"""

import json
import os
import time
import asyncio
import httpx
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Unbuffered output
import sys
sys.stdout.reconfigure(line_buffering=True)

# Load environment - try project root first, then current directory
env_path = Path(__file__).parent.parent / ".env"
if not env_path.exists():
    env_path = Path(".env")
load_dotenv(env_path)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found. Copy .env.example to .env and add your key.")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = {
    "gpt-4o": "openai/gpt-4o",
    "claude-sonnet": "anthropic/claude-sonnet-4",
    "gemini-flash": "google/gemini-2.0-flash-001",
}

PROMPT = """You are a fact-checker. Is this claim TRUE or FALSE?

Claim: "{claim}"

Respond with ONLY a JSON object:
{{"verdict": "TRUE" or "FALSE", "confidence": 0-100, "explanation": "brief reason"}}
"""


async def call_llm(client, model_id, claim):
    """Call LLM."""
    prompt = PROMPT.format(claim=claim)
    start = time.time()
    
    try:
        response = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.1
            },
            timeout=60.0
        )
        
        latency = (time.time() - start) * 1000
        
        if response.status_code != 200:
            return None, f"Error {response.status_code}", latency
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse JSON
        try:
            import re
            match = re.search(r'\{[^}]+\}', content)
            if match:
                result = json.loads(match.group())
                return result.get("verdict", "").upper(), content, latency
        except:
            pass
        
        return None, content, latency
        
    except Exception as e:
        return None, str(e), (time.time() - start) * 1000


async def main():
    print("=" * 60)
    print("VERITY SNIFFER - QUICK TORTURE TEST")
    print("Testing 20 claims against 3 models")
    print("=" * 60)
    print()
    
    # Load claims - take a representative sample
    with open("claims.json") as f:
        data = json.load(f)
    
    # Select 20 claims: 10 true, 10 false (varied difficulty)
    true_claims = [c for c in data["claims"] if c["label"] == True][:10]
    false_claims = [c for c in data["claims"] if c["label"] == False][:10]
    claims = true_claims + false_claims
    
    print(f"Selected {len(claims)} claims (10 true, 10 false)")
    print()
    
    results = {model: {"correct": 0, "wrong": 0, "errors": 0, "fp": 0, "fn": 0} for model in MODELS}
    
    async with httpx.AsyncClient() as client:
        for model_name, model_id in MODELS.items():
            print(f"\n--- Testing {model_name} ---")
            
            for claim in claims:
                verdict, raw, latency = await call_llm(client, model_id, claim["text"])
                
                # Check correctness
                ground_truth = claim["label"]
                
                if verdict is None:
                    results[model_name]["errors"] += 1
                    status = "E"
                elif verdict == "TRUE" and ground_truth == True:
                    results[model_name]["correct"] += 1
                    status = "✓"
                elif verdict == "FALSE" and ground_truth == False:
                    results[model_name]["correct"] += 1
                    status = "✓"
                elif verdict == "FALSE" and ground_truth == True:
                    results[model_name]["wrong"] += 1
                    results[model_name]["fp"] += 1
                    status = "✗ FP"
                elif verdict == "TRUE" and ground_truth == False:
                    results[model_name]["wrong"] += 1
                    results[model_name]["fn"] += 1
                    status = "✗ FN"
                else:
                    results[model_name]["wrong"] += 1
                    status = "?"
                
                print(f"  {status} [{latency:.0f}ms] {claim['text'][:50]}...")
                
                await asyncio.sleep(0.3)  # Rate limiting
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for model, stats in results.items():
        total = stats["correct"] + stats["wrong"]
        accuracy = (stats["correct"] / total * 100) if total > 0 else 0
        fp_rate = (stats["fp"] / 10 * 100)  # 10 true claims
        fn_rate = (stats["fn"] / 10 * 100)  # 10 false claims
        
        print(f"\n{model}:")
        print(f"  Accuracy: {accuracy:.1f}% ({stats['correct']}/{total})")
        print(f"  False Positive Rate: {fp_rate:.1f}% (true marked false)")
        print(f"  False Negative Rate: {fn_rate:.1f}% (false marked true)")
        print(f"  Errors: {stats['errors']}")
    
    # Quick verdict
    print("\n" + "=" * 60)
    avg_accuracy = sum(
        (r["correct"] / (r["correct"] + r["wrong"]) * 100) if (r["correct"] + r["wrong"]) > 0 else 0
        for r in results.values()
    ) / len(results)
    
    if avg_accuracy < 85:
        print("❌ VERDICT: Average accuracy below 85% - PRODUCT THESIS INVALID")
    else:
        print("✅ VERDICT: Accuracy threshold met on this sample")
    print("=" * 60)
    
    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "claims_tested": len(claims),
        "results": results
    }
    
    Path("results").mkdir(exist_ok=True)
    with open("results/quick_test_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print("\nResults saved to results/quick_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())
