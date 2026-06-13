"""
JSearch API client for reliable job search.

Uses the JSearch API on RapidAPI to aggregate job listings from Indeed, LinkedIn,
Glassdoor, ZipRecruiter, and other platforms via a single REST endpoint.

Free tier: 200 requests/month, no credit card required.
API docs: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
"""
import os
import requests
import logging
from typing import List, Dict, Union

logger = logging.getLogger(__name__)

JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_MAX_RESULTS = 10


def _get_headers() -> dict:
    """Build the RapidAPI request headers."""
    api_key = os.getenv("RAPIDAPI_KEY", "")
    if not api_key:
        raise ValueError(
            "RAPIDAPI_KEY is not set. Get a free key at "
            "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"
        )
    return {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "jsearch.p.rapidapi.com",
    }


def search_jobs_api(
    query: str,
    location: str = "",
    num_pages: int = 1,
    country: str = "in",
    platform_label: str = "JSearch",
) -> Union[List[Dict], str]:
    """Search for jobs using the JSearch API.

    Args:
        query: Job role / keywords, e.g. "Python Developer".
        location: City or region, e.g. "Chennai".
        num_pages: Number of result pages (each page ≈ 10 jobs).
        country: ISO-3166 country code for filtering (default: "in" for India).
        platform_label: Label to tag results with, e.g. "Naukri.com" or "Indeed".

    Returns:
        A list of job dicts or an error message string.
    """
    search_query = f"{query} in {location}" if location else query
    logger.info(f"JSearch API call: query='{search_query}', country='{country}'")

    try:
        headers = _get_headers()
    except ValueError as e:
        logger.error(str(e))
        return str(e)

    params = {
        "query": search_query,
        "page": "1",
        "num_pages": str(num_pages),
        "country": country,
        "date_posted": "month",  # last 30 days
    }

    try:
        response = requests.get(
            JSEARCH_API_URL, headers=headers, params=params, timeout=15
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", "unknown")
        logger.error(f"JSearch API HTTP error {status}: {e}")
        if status == 403:
            return "Error: API key is invalid or quota exceeded. Check your RAPIDAPI_KEY."
        if status == 429:
            return "Error: API rate limit reached. Try again later."
        return f"Error: JSearch API returned HTTP {status}."
    except requests.exceptions.RequestException as e:
        logger.error(f"JSearch API request failed: {e}")
        return f"Error: Could not connect to JSearch API. {e}"

    raw_jobs = data.get("data", [])
    if not raw_jobs:
        logger.warning("JSearch API returned no results.")
        return "No Jobs found for this query."

    jobs: List[Dict] = []
    for item in raw_jobs[:JSEARCH_MAX_RESULTS]:
        jobs.append({
            "platform": platform_label,
            "title": item.get("job_title", "N/A"),
            "company": item.get("employer_name", "N/A"),
            "url": item.get("job_apply_link") or item.get("job_google_link", ""),
            "location": item.get("job_city", "") or item.get("job_country", ""),
            "job_type": item.get("job_employment_type", "N/A"),
            "description": item.get("job_description", ""),
        })

    logger.info(f"JSearch API returned {len(jobs)} jobs (tagged as {platform_label}).")
    return jobs
