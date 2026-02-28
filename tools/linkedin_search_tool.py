import aiohttp
from bs4 import BeautifulSoup
import logging
import random
from typing import List, Dict, Union
from tools.retry_utils import retry_async, RetryConfig

# Set up a logger for this module
logger = logging.getLogger(__name__)

USER_AGENTS: list[str] = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
]


JOB_CARD_SELECTORS: list[tuple[str, str]] = [
    ("div", "base-card"),                         # current primary card container
    ("li", "jobs-search-results__list-item"),     # list items in some layouts
    ("div", "job-search-card"),                   # generic job card container
]

# Retry configuration for LinkedIn searches
LINKEDIN_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0
)


@retry_async(LINKEDIN_RETRY_CONFIG, exceptions=(aiohttp.ClientError,))
async def search_linkedin_jobs(query: str) -> Union[List[Dict], str]:
    """Asynchronously searches for jobs on LinkedIn.

    The input must be a comma-separated string in the form 'role, location',
    for example: 'Software Engineer, Chennai'.
    """
    try:
        role, location = [item.strip() for item in query.split(',')]
    except ValueError:
        error_message = "Input error: Please provide the input as 'role, location'."
        logger.error(error_message)
        return error_message

    logger.info(f"Starting LinkedIn job search for '{role}' in '{location}'...")
    url = f"https://www.linkedin.com/jobs/search?keywords={role.replace(' ', '%20')}&location={location.replace(' ', '%20')}"

    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=10) as response:
                status = response.status
                if status == 403:
                    logger.warning("LinkedIn returned HTTP 403 (possibly blocked or bot-detected).")
                    return "Error: LinkedIn blocked the request. Please try again later or refine your search."

                response.raise_for_status()
                html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')
        job_cards: List = []
        for tag_name, class_name in JOB_CARD_SELECTORS:
            job_cards = soup.find_all(tag_name, class_=class_name)
            if job_cards:
                logger.info(
                    "Found %d LinkedIn job cards using selector (%s, %s).",
                    len(job_cards),
                    tag_name,
                    class_name,
                )
                break

        if not job_cards:
            logger.warning(
                "No job cards found on LinkedIn using any known selectors. "
                "The page structure may have changed or content is protected."
            )
            return "No Jobs found for this query."

        jobs: List[Dict] = []
        for card in job_cards:
            if len(jobs) >= 10:
                break
            title_element = card.find('h3', class_='base-search-card__title')
            company_element = card.find('h4', class_='base-search-card__subtitle')
            url_element = card.find('a', class_='base-card__full-link')
            location_element = card.find('span', class_='job-search-card__location')

            if all([title_element, company_element, url_element]):
                jobs.append({
                    "platform": "LinkedIn",
                    "title": title_element.text.strip(),
                    "company": company_element.text.strip(),
                    "url": url_element['href'],
                    "location": location_element.text.strip() if location_element else location
                })

        logger.info(f"Found {len(jobs)} jobs on LinkedIn.")
        return jobs if jobs else "No Jobs found for this query."

    except aiohttp.ClientError as e:
        logger.error(f"Network error during LinkedIn search: {e}")
        return f"Error: Could not connect to LinkedIn. {e}"
    except Exception as e:
        logger.error(f"An unexpected error occurred during LinkedIn parsing: {e}", exc_info=True)
        return f"An unexpected error occurred: {e}"