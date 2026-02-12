"""
Main entry point for the arXiv digest agent.
This will be called by cron jobs or imported by other modules.
"""

import asyncio
from src.fetcher import ArxivClient


async def fetch_papers_for_topics(topics: list[str]) -> list:
    """
    Fetch papers for given topics.
    This is the main interface - cron jobs call this.
    """
    client = ArxivClient()
    papers = client.search_papers(topics)
    return papers


if __name__ == "__main__":
    # Simple test run
    topics = ["machine learning", "quantum computing"]
    papers = asyncio.run(fetch_papers_for_topics(topics))
    print(f"Found {len(papers)} papers")
    for p in papers[:3]:
        print(f"  - {p.title[:60]}...")