"""
arXiv paper search module with robust error handling, rate limiting, and date filtering.

This module provides a production-ready client for the arXiv API, designed to fetch
research papers efficiently while respecting API limits and providing structured
data for downstream processing.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import arxiv
import structlog

from config import settings

logger = structlog.get_logger()


@dataclass(frozen=True)
class ArxivPaper:
    """Standardized paper representation for our system."""
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    pdf_url: str
    published: datetime
    categories: List[str]


class ArxivClient:
    """
    A robust client for searching arXiv with built-in rate limiting and filtering.

    This client wraps the `arxiv` library to provide a higher-level interface
    tailored for autonomous research agents. It handles configuration, logging,
    and common filtering patterns like date ranges.

    Attributes:
        max_results (int): Maximum number of papers to fetch per query.
        delay_seconds (float): Delay between API requests to respect rate limits.
        hours_back (int): Time window in hours to look back for papers.
    """

    def __init__(self, max_results: int | None = None, delay_seconds: float | None = None, hours_back: int | None = None):
        # Use settings as defaults, allow override
        self.max_results = max_results or settings.arxiv_max_results
        self.delay_seconds = delay_seconds or settings.arxiv_delay_seconds
        self.hours_back = hours_back or settings.arxiv_hours_back

        # arxiv library client
        self._client = arxiv.Client(
            page_size=self.max_results,
            delay_seconds=self.delay_seconds,  # Built-in rate limiting
            num_retries=3  # Auto-retry on transient failures
        )

        logger.info(
            "ArxivClient initialized",
            max_results=self.max_results,
            delay_seconds=self.delay_seconds,
            hours_back=self.hours_back
        )

    def search_papers(self, topics: List[str]) -> List[ArxivPaper]:
        """
        Search multiple topics, return papers from last N hours.

        Args:
            topics: A list of search query strings (e.g., ["LLM agents", "reasoning"]).

        Returns:
            A list of unique `ArxivPaper` objects published within the last `hours_back`,
            sorted by publication date (newest first).
        """
        # Calculate the cutoff time for filtering papers.
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.hours_back)
        
        all_papers: dict[str, ArxivPaper] = {}  # Dictionary to handle deduplication by ID

        for topic in topics:
            logger.info("Searching arXiv", topic=topic)

            search = arxiv.Search(
                query=topic,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )

            topic_count = 0
            # Iterate through the results generator
            for result in self._client.results(search):
                # Stop if paper is too old (sorted by date, so all later will be older)
                if result.published < cutoff_time:
                    logger.debug("Reached cutoff time", topic=topic, published=result.published)
                    break

                # Extract arxiv_id from URL
                arxiv_id = result.entry_id.split("/")[-1].replace("abs/", "").split("v")[0]

                # Skip if we've already processed this paper from another topic search
                if arxiv_id in all_papers:
                    continue

                # Convert the raw result into our standardized ArxivPaper data class
                paper = ArxivPaper(
                    arxiv_id=arxiv_id,
                    title=result.title,
                    authors=[str(a) for a in result.authors],
                    abstract=result.summary.replace("\n", " "),
                    pdf_url=result.pdf_url,
                    published=result.published,
                    categories=result.categories
                )

                all_papers[arxiv_id] = paper
                topic_count += 1

            logger.info(
                "Topic search complete",
                topic=topic,
                found=topic_count,
                total_unique_so_far=len(all_papers)
            )

        # Convert dictionary values to a list and sort by published date (newest first)
        papers = sorted(all_papers.values(), key=lambda p: p.published, reverse=True)

        logger.info(
            "Search complete",
            topics_count=len(topics),
            total_papers_returned=len(papers),
            hours_back=self.hours_back
        )

        return papers

    def search_single_topic(self, query: str) -> List[ArxivPaper]:
        """
        Convenience method to search for a single topic.

        Args:
            query: The search query string.

        Returns:
            A list of `ArxivPaper` objects matching the query and time constraints.
        """
        return self.search_papers([query])