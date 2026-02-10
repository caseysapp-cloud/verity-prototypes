#!/usr/bin/env python3
"""
Verity Sniffer - Source Aggregator
Aggregates existing fact-checks from multiple sources.

This demonstrates what ACTUALLY works: leveraging existing human fact-checks
rather than generating new ones with AI.
"""

import os
import sys
import json
import asyncio
import httpx
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Load environment - try project root first, then current directory
env_path = Path(__file__).parent.parent / ".env"
if not env_path.exists():
    env_path = Path(".env")
load_dotenv(env_path)

# Google Fact Check API (free, rate-limited) - optional
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_FACT_CHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


@dataclass
class FactCheckResult:
    source: str
    claim_reviewed: str
    rating: str
    url: str
    publisher: str
    review_date: Optional[str] = None
    language: Optional[str] = None


@dataclass
class AggregatedResult:
    query: str
    timestamp: str
    total_results: int
    sources_checked: list[str]
    fact_checks: list[FactCheckResult]
    consensus: Optional[str] = None
    
    
class FactCheckAggregator:
    """Aggregates fact-checks from multiple sources."""
    
    def __init__(self):
        self.sources_checked = []
        
    async def search_google_fact_check(self, query: str) -> list[FactCheckResult]:
        """Search Google Fact Check API."""
        if not GOOGLE_API_KEY:
            print("⚠️  GOOGLE_API_KEY not set - skipping Google Fact Check API")
            return []
        
        self.sources_checked.append("Google Fact Check API")
        results = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    GOOGLE_FACT_CHECK_URL,
                    params={
                        "key": GOOGLE_API_KEY,
                        "query": query,
                        "languageCode": "en"
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    print(f"⚠️  Google API error: {response.status_code}")
                    return []
                
                data = response.json()
                claims = data.get("claims", [])
                
                for claim in claims:
                    claim_text = claim.get("text", "")
                    
                    for review in claim.get("claimReview", []):
                        results.append(FactCheckResult(
                            source="Google Fact Check API",
                            claim_reviewed=claim_text,
                            rating=review.get("textualRating", "Unknown"),
                            url=review.get("url", ""),
                            publisher=review.get("publisher", {}).get("name", "Unknown"),
                            review_date=review.get("reviewDate"),
                            language=review.get("languageCode", "en")
                        ))
                
        except Exception as e:
            print(f"⚠️  Google API error: {e}")
        
        return results
    
    async def search_snopes(self, query: str) -> list[FactCheckResult]:
        """Search Snopes via web scraping (no official API)."""
        self.sources_checked.append("Snopes")
        results = []
        
        try:
            search_url = f"https://www.snopes.com/?s={quote_plus(query)}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    search_url,
                    headers={"User-Agent": "Verity Sniffer Research Bot"},
                    timeout=30.0,
                    follow_redirects=True
                )
                
                if response.status_code != 200:
                    return []
                
                # Basic parsing - look for article cards
                # Note: This is fragile and may break. Production would need proper scraping.
                html = response.text
                
                # Find article links with ratings
                import re
                
                # Look for fact-check result pages
                article_pattern = r'<a[^>]+href="(https://www\.snopes\.com/fact-check/[^"]+)"[^>]*>([^<]+)</a>'
                matches = re.findall(article_pattern, html)
                
                for url, title in matches[:5]:  # Limit to 5 results
                    # Try to determine rating from the page (simplified)
                    results.append(FactCheckResult(
                        source="Snopes",
                        claim_reviewed=title.strip(),
                        rating="See article",  # Would need to scrape individual page for rating
                        url=url,
                        publisher="Snopes"
                    ))
                    
        except Exception as e:
            print(f"⚠️  Snopes search error: {e}")
        
        return results
    
    async def search_politifact(self, query: str) -> list[FactCheckResult]:
        """Search PolitiFact via web scraping."""
        self.sources_checked.append("PolitiFact")
        results = []
        
        try:
            search_url = f"https://www.politifact.com/search/?q={quote_plus(query)}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    search_url,
                    headers={"User-Agent": "Verity Sniffer Research Bot"},
                    timeout=30.0,
                    follow_redirects=True
                )
                
                if response.status_code != 200:
                    return []
                
                html = response.text
                import re
                
                # Look for fact-check links
                article_pattern = r'<a[^>]+href="(/factchecks/[^"]+)"[^>]*class="[^"]*"[^>]*>([^<]+)</a>'
                matches = re.findall(article_pattern, html)
                
                for path, title in matches[:5]:
                    results.append(FactCheckResult(
                        source="PolitiFact",
                        claim_reviewed=title.strip(),
                        rating="See article",
                        url=f"https://www.politifact.com{path}",
                        publisher="PolitiFact"
                    ))
                    
        except Exception as e:
            print(f"⚠️  PolitiFact search error: {e}")
        
        return results
    
    async def search_reuters_fact_check(self, query: str) -> list[FactCheckResult]:
        """Search Reuters Fact Check."""
        self.sources_checked.append("Reuters Fact Check")
        results = []
        
        try:
            # Reuters doesn't have a public search API, using their RSS approach
            search_url = f"https://www.reuters.com/site-search/?query={quote_plus(query)}&section=fact-check"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    search_url,
                    headers={"User-Agent": "Verity Sniffer Research Bot"},
                    timeout=30.0,
                    follow_redirects=True
                )
                
                # Reuters search results would need JavaScript rendering
                # This is a placeholder showing the approach
                
        except Exception as e:
            print(f"⚠️  Reuters search error: {e}")
        
        return results
    
    def determine_consensus(self, fact_checks: list[FactCheckResult]) -> Optional[str]:
        """Determine consensus from multiple fact-checks."""
        if not fact_checks:
            return None
        
        ratings = [fc.rating.lower() for fc in fact_checks]
        
        # Count false-ish ratings
        false_keywords = ["false", "pants on fire", "lie", "misleading", "wrong", "incorrect", "debunked"]
        true_keywords = ["true", "correct", "accurate", "verified", "confirmed"]
        
        false_count = sum(1 for r in ratings if any(k in r for k in false_keywords))
        true_count = sum(1 for r in ratings if any(k in r for k in true_keywords))
        
        total = len(ratings)
        
        if false_count > total * 0.6:
            return "LIKELY FALSE - Multiple fact-checkers rated this claim false"
        elif true_count > total * 0.6:
            return "LIKELY TRUE - Multiple fact-checkers rated this claim true"
        elif total > 0:
            return "MIXED - Fact-checkers have varying opinions"
        else:
            return "NO DATA - No existing fact-checks found"
    
    async def search(self, query: str) -> AggregatedResult:
        """Search all sources for fact-checks."""
        self.sources_checked = []
        
        print(f"\n🔍 Searching for fact-checks: \"{query}\"")
        print("-" * 50)
        
        # Run all searches concurrently
        tasks = [
            self.search_google_fact_check(query),
            self.search_snopes(query),
            self.search_politifact(query),
            self.search_reuters_fact_check(query)
        ]
        
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        all_results = []
        for result in results_lists:
            if isinstance(result, list):
                all_results.extend(result)
        
        # Determine consensus
        consensus = self.determine_consensus(all_results)
        
        return AggregatedResult(
            query=query,
            timestamp=datetime.now().isoformat(),
            total_results=len(all_results),
            sources_checked=self.sources_checked,
            fact_checks=all_results,
            consensus=consensus
        )


def print_results(result: AggregatedResult):
    """Pretty print aggregation results."""
    print(f"\n{'=' * 60}")
    print(f"FACT-CHECK AGGREGATION RESULTS")
    print(f"{'=' * 60}")
    print(f"\nQuery: \"{result.query}\"")
    print(f"Timestamp: {result.timestamp}")
    print(f"Sources checked: {', '.join(result.sources_checked)}")
    print(f"Total fact-checks found: {result.total_results}")
    
    print(f"\n{'─' * 60}")
    print(f"CONSENSUS: {result.consensus}")
    print(f"{'─' * 60}")
    
    if result.fact_checks:
        print(f"\nIndividual Fact-Checks:")
        print()
        
        for i, fc in enumerate(result.fact_checks, 1):
            print(f"  {i}. [{fc.publisher}] {fc.rating}")
            print(f"     Claim: {fc.claim_reviewed[:80]}...")
            print(f"     URL: {fc.url}")
            if fc.review_date:
                print(f"     Date: {fc.review_date}")
            print()
    else:
        print("\n  No existing fact-checks found.")
        print("  This could mean:")
        print("  - The claim hasn't been fact-checked yet")
        print("  - The search terms need adjustment")
        print("  - The claim is too recent")
    
    print(f"\n{'=' * 60}")
    print("NOTE: This aggregator shows EXISTING fact-checks only.")
    print("It does not generate new analysis - that's the point.")
    print(f"{'=' * 60}\n")


async def main():
    """CLI interface."""
    if len(sys.argv) < 2:
        print("Usage: python aggregator.py \"claim to fact-check\"")
        print()
        print("Examples:")
        print("  python aggregator.py \"The 2020 election was stolen\"")
        print("  python aggregator.py \"COVID vaccines cause autism\"")
        print("  python aggregator.py \"5G causes coronavirus\"")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    aggregator = FactCheckAggregator()
    result = await aggregator.search(query)
    
    print_results(result)
    
    # Save results to file
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    filename = f"aggregation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_dir / filename, "w") as f:
        # Convert dataclass instances to dicts
        output = asdict(result)
        output["fact_checks"] = [asdict(fc) for fc in result.fact_checks]
        json.dump(output, f, indent=2)
    
    print(f"Results saved to: {output_dir / filename}")


if __name__ == "__main__":
    asyncio.run(main())
