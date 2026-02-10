#!/usr/bin/env python3
"""
Verity Sniffer - Enterprise Guardrails
LLM response wrapper with trust scoring for B2B compliance use cases.

This demonstrates the B2B pivot: compliance officers care about auditability,
not "truth." This is a market that actually exists.
"""

import os
import re
import json
import time
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict
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

# Default model
DEFAULT_MODEL = "openai/gpt-4o"


@dataclass
class TrustFlag:
    category: str  # hedging, phantom_citation, confidence_mismatch, temporal, contradiction
    severity: str  # low, medium, high
    description: str
    excerpt: Optional[str] = None


@dataclass
class TrustAnalysis:
    score: int  # 0-100
    flags: list[TrustFlag] = field(default_factory=list)
    citations_found: int = 0
    citations_verified: int = 0
    hedging_instances: int = 0
    confidence_indicators: list[str] = field(default_factory=list)


@dataclass
class GuardedResponse:
    """Response from the guarded LLM."""
    response: str
    trust_analysis: TrustAnalysis
    model: str
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    warnings: list[str] = field(default_factory=list)


class TrustAnalyzer:
    """Analyzes LLM responses for trust signals."""
    
    # Hedging patterns
    HEDGING_PATTERNS = [
        r"\bI think\b",
        r"\bI believe\b",
        r"\bprobably\b",
        r"\bmight be\b",
        r"\bmay be\b",
        r"\bpossibly\b",
        r"\bI'm not sure\b",
        r"\bI'm uncertain\b",
        r"\bit seems\b",
        r"\bapparently\b",
        r"\bperhaps\b",
        r"\bcould be\b",
        r"\blikely\b",
        r"\bunlikely\b",
        r"\bestimated\b",
        r"\bapproximately\b",
        r"\bsupposedly\b"
    ]
    
    # High-confidence language
    CONFIDENCE_PATTERNS = [
        r"\bdefinitely\b",
        r"\bcertainly\b",
        r"\babsolutely\b",
        r"\bundoubtedly\b",
        r"\bwithout question\b",
        r"\bguaranteed\b",
        r"\balways\b",
        r"\bnever\b",
        r"\bproven\b",
        r"\bestablished fact\b"
    ]
    
    # Citation patterns
    CITATION_PATTERNS = [
        r"https?://\S+",  # URLs
        r"\(\d{4}\)",  # Year citations (2023)
        r"et al\.",  # Academic citations
        r"according to",
        r"as reported by",
        r"published in",
        r"\[\d+\]",  # Numbered citations [1]
    ]
    
    # Vague citation patterns (potential hallucinations)
    VAGUE_CITATION_PATTERNS = [
        r"studies show",
        r"research indicates",
        r"experts say",
        r"according to research",
        r"scientists believe",
        r"a study found",
        r"recent research",
        r"various sources",
        r"multiple studies",
        r"it is known",
        r"common knowledge"
    ]
    
    # Temporal confusion indicators
    TEMPORAL_PATTERNS = [
        r"as of \d{4}",
        r"currently",
        r"at present",
        r"recently",
        r"in the future",
        r"will be",
        r"was going to"
    ]
    
    def analyze(self, text: str, previous_responses: list[str] = None) -> TrustAnalysis:
        """Analyze a response for trust indicators."""
        flags = []
        score = 100  # Start at max, deduct for issues
        
        # 1. Check for hedging
        hedging_count = 0
        for pattern in self.HEDGING_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            hedging_count += len(matches)
        
        if hedging_count > 5:
            score -= 15
            flags.append(TrustFlag(
                category="hedging",
                severity="medium",
                description=f"High hedging language ({hedging_count} instances)",
                excerpt=None
            ))
        elif hedging_count > 2:
            score -= 5
            flags.append(TrustFlag(
                category="hedging",
                severity="low",
                description=f"Some hedging language ({hedging_count} instances)",
                excerpt=None
            ))
        
        # 2. Check for high-confidence claims (potential red flag if unsubstantiated)
        confidence_matches = []
        for pattern in self.CONFIDENCE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            confidence_matches.extend(matches)
        
        # 3. Check for citations
        citations_found = 0
        for pattern in self.CITATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            citations_found += len(matches)
        
        # 4. Check for vague/potentially hallucinated citations
        vague_citations = 0
        for pattern in self.VAGUE_CITATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            vague_citations += len(matches)
        
        if vague_citations > 0:
            score -= vague_citations * 5
            flags.append(TrustFlag(
                category="phantom_citation",
                severity="high" if vague_citations > 2 else "medium",
                description=f"Vague citations that may be hallucinated ({vague_citations} instances)",
                excerpt=None
            ))
        
        # 5. Check for confidence mismatch (high confidence + low citations)
        if len(confidence_matches) > 2 and citations_found == 0:
            score -= 20
            flags.append(TrustFlag(
                category="confidence_mismatch",
                severity="high",
                description="High certainty expressed without citations",
                excerpt=confidence_matches[0] if confidence_matches else None
            ))
        
        # 6. Check for temporal indicators (may indicate knowledge cutoff issues)
        temporal_count = 0
        for pattern in self.TEMPORAL_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            temporal_count += len(matches)
        
        if temporal_count > 3:
            flags.append(TrustFlag(
                category="temporal",
                severity="low",
                description="Multiple temporal references - verify currency of information",
                excerpt=None
            ))
        
        # 7. Check for contradictions with previous responses
        if previous_responses:
            # Simple check: look for direct contradictions
            # A production system would use semantic similarity
            for prev in previous_responses[-3:]:  # Check last 3 responses
                if self._detect_contradiction(text, prev):
                    score -= 25
                    flags.append(TrustFlag(
                        category="contradiction",
                        severity="high",
                        description="Possible contradiction with earlier response",
                        excerpt=None
                    ))
                    break
        
        # Ensure score is in valid range
        score = max(0, min(100, score))
        
        return TrustAnalysis(
            score=score,
            flags=flags,
            citations_found=citations_found,
            citations_verified=0,  # Would need actual URL checking
            hedging_instances=hedging_count,
            confidence_indicators=confidence_matches
        )
    
    def _detect_contradiction(self, current: str, previous: str) -> bool:
        """Simple contradiction detection."""
        # Very basic: look for negation of same phrases
        # Production would use NLI models
        
        # Extract key phrases from current
        current_sentences = current.lower().split('.')
        previous_sentences = previous.lower().split('.')
        
        negation_pairs = [
            ("is not", "is"),
            ("does not", "does"),
            ("cannot", "can"),
            ("never", "always"),
            ("false", "true"),
            ("incorrect", "correct"),
            ("wrong", "right")
        ]
        
        for curr_sent in current_sentences:
            for prev_sent in previous_sentences:
                for neg, pos in negation_pairs:
                    # Check if one sentence has negation where other doesn't
                    if neg in curr_sent and pos in prev_sent:
                        # Check if sentences are about same topic (very rough)
                        curr_words = set(curr_sent.split())
                        prev_words = set(prev_sent.split())
                        overlap = len(curr_words & prev_words)
                        if overlap > 5:  # Significant overlap
                            return True
        
        return False


class GuardedLLM:
    """LLM wrapper with trust scoring for enterprise use."""
    
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.analyzer = TrustAnalyzer()
        self.conversation_history = []
        self.response_history = []
        
    async def chat(self, message: str, system_prompt: str = None) -> GuardedResponse:
        """Send a message and get a trust-analyzed response."""
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        for turn in self.conversation_history:
            messages.append(turn)
        
        # Add new message
        messages.append({"role": "user", "content": message})
        
        # Call LLM
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://verity-guardrails.enterprise",
                    "X-Title": "Verity Enterprise Guardrails"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 2000,
                    "temperature": 0.7
                },
                timeout=60.0
            )
        
        latency_ms = (time.time() - start_time) * 1000
        
        if response.status_code != 200:
            raise Exception(f"LLM API error: {response.status_code} - {response.text}")
        
        data = response.json()
        response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Analyze response for trust signals
        trust_analysis = self.analyzer.analyze(response_text, self.response_history)
        
        # Update history
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": response_text})
        self.response_history.append(response_text)
        
        # Generate warnings
        warnings = []
        if trust_analysis.score < 50:
            warnings.append("LOW TRUST SCORE - Review before using")
        if any(f.category == "phantom_citation" for f in trust_analysis.flags):
            warnings.append("Potential hallucinated citations detected")
        if any(f.category == "contradiction" for f in trust_analysis.flags):
            warnings.append("May contradict earlier statements")
        
        return GuardedResponse(
            response=response_text,
            trust_analysis=trust_analysis,
            model=self.model,
            latency_ms=round(latency_ms, 0),
            warnings=warnings
        )
    
    def get_session_summary(self) -> dict:
        """Get summary of the conversation session for compliance."""
        trust_scores = []
        all_flags = []
        
        for response in self.response_history:
            analysis = self.analyzer.analyze(response)
            trust_scores.append(analysis.score)
            all_flags.extend([asdict(f) for f in analysis.flags])
        
        return {
            "total_turns": len(self.response_history),
            "average_trust_score": round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0,
            "min_trust_score": min(trust_scores) if trust_scores else 0,
            "max_trust_score": max(trust_scores) if trust_scores else 0,
            "total_flags": len(all_flags),
            "flags_by_category": self._count_flags_by_category(all_flags),
            "low_trust_responses": sum(1 for s in trust_scores if s < 50),
            "timestamp": datetime.now().isoformat()
        }
    
    def _count_flags_by_category(self, flags: list) -> dict:
        """Count flags by category."""
        counts = {}
        for flag in flags:
            cat = flag["category"]
            counts[cat] = counts.get(cat, 0) + 1
        return counts
    
    def reset(self):
        """Reset conversation history."""
        self.conversation_history = []
        self.response_history = []


# Simple demo CLI
async def demo():
    """Interactive demo of the guardrails system."""
    print("=" * 60)
    print("VERITY ENTERPRISE GUARDRAILS - Interactive Demo")
    print("=" * 60)
    print()
    print("This wraps any LLM with trust scoring for compliance use cases.")
    print("Type 'quit' to exit, 'summary' for session summary.")
    print()
    
    llm = GuardedLLM()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
            
        if not user_input:
            continue
        
        if user_input.lower() == 'quit':
            break
        
        if user_input.lower() == 'summary':
            summary = llm.get_session_summary()
            print("\n" + "=" * 40)
            print("SESSION SUMMARY")
            print("=" * 40)
            print(json.dumps(summary, indent=2))
            continue
        
        try:
            result = await llm.chat(user_input)
            
            print(f"\n{'─' * 60}")
            print(f"Trust Score: {result.trust_analysis.score}/100")
            
            if result.warnings:
                print(f"⚠️  Warnings: {', '.join(result.warnings)}")
            
            if result.trust_analysis.flags:
                print(f"Flags: {len(result.trust_analysis.flags)}")
                for flag in result.trust_analysis.flags:
                    print(f"  - [{flag.severity.upper()}] {flag.category}: {flag.description}")
            
            print(f"{'─' * 60}")
            print(f"\nAssistant: {result.response}")
            print(f"\n[Latency: {result.latency_ms}ms | Model: {result.model}]")
            
        except Exception as e:
            print(f"Error: {e}")
    
    # Print final summary
    print("\n" + "=" * 60)
    print("FINAL SESSION SUMMARY")
    print("=" * 60)
    summary = llm.get_session_summary()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
