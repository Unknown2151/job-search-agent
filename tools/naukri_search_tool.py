"""
Naukri.com job search tool — powered by JSearch API.

Previously used Selenium to scrape Naukri.com directly, which was blocked
by anti-bot protections. Now uses the JSearch API (RapidAPI) filtered to
India to return equivalent results reliably.
"""
import logging
from typing import List, Dict, Union
from tools.jsearch_api_tool import search_jobs_api

logger = logging.getLogger(__name__)


def search_naukri_jobs(query: str, job_type: str = "") -> Union[List[Dict], str]:
    """Search for jobs on Naukri.com (via JSearch API, India-filtered).

    Args:
        query: A comma-separated string containing the role and location.
               Example: "Data Scientist, Chennai"
        job_type: Optional filter for employment type (e.g., "internship", "full-time").

    Returns:
        A list of job dicts or an error message string.
    """
    logger.info(f"Received Naukri search query: '{query}', job_type filter: '{job_type}'")
    try:
        role, location = [item.strip() for item in query.split(',')]
    except ValueError:
        error_message = "Input error: Please provide the input as 'role, location'."
        logger.error(error_message)
        return error_message

    results = search_jobs_api(
        query=role,
        location=location,
        country="in",
        platform_label="Naukri.com",
    )
    
    if isinstance(results, list) and job_type:
        job_type_normalized = job_type.lower().replace("-", "_").replace(" ", "_")
        filtered = [
            job for job in results
            if job_type_normalized in str(job.get("job_type", "")).lower().replace("-", "_").replace(" ", "_")
        ]
        logger.info(f"Filtered {len(results)} results to {len(filtered)} {job_type} positions.")
        return filtered if filtered else f"No {job_type} positions found."
    
    return results