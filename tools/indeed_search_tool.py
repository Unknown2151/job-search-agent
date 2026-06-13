"""
Indeed job search tool — powered by JSearch API.

Previously scraped Indeed's HTML directly, which was blocked by anti-bot
protections and used outdated CSS selectors. Now uses the JSearch API
(RapidAPI) to return reliable results.
"""
import logging
from typing import List, Dict, Union
from tools.jsearch_api_tool import search_jobs_api

logger = logging.getLogger(__name__)


def search_indeed_jobs(role: str, location: str = "", job_type: str = "") -> Union[List[Dict], str]:
    """Search for jobs on Indeed (via JSearch API).

    Args:
        role: The job role to search for.
        location: The location to search in.
        job_type: Optional filter for employment type (e.g., "internship", "full-time").

    Returns:
        A list of job dicts, or an error message string on failure.
    """
    logger.info(f"Searching Indeed for '{role}' in '{location}', job_type filter: '{job_type}'...")

    results = search_jobs_api(
        query=role,
        location=location,
        country="in",
        platform_label="Indeed",
    )
    
    # Filter by job_type if specified
    if isinstance(results, list) and job_type:
        job_type_normalized = job_type.lower().replace("-", "_").replace(" ", "_")
        filtered = [
            job for job in results
            if job_type_normalized in str(job.get("job_type", "")).lower().replace("-", "_").replace(" ", "_")
        ]
        logger.info(f"Filtered {len(results)} results to {len(filtered)} {job_type} positions.")
        return filtered if filtered else f"No {job_type} positions found."
    
    return results