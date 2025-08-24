import requests
from bs4 import BeautifulSoup
import logging

# Set up a logger for this module
logger = logging.getLogger(__name__)


def search_linkedin_jobs(query: str) -> list[dict] | str:
    """
    Searches for job listings on LinkedIn based on a query string.

    Args:
        query (str): A comma-separated string containing the role and location.
                     Example: "Software Engineer, Bengaluru"

    Returns:
        list[dict] | str: A list of job dictionaries or an error message string.
    """
    logger.info(f"Received LinkedIn search query: '{query}'")
    try:
        role, location = [item.strip() for item in query.split(',')]
    except ValueError:
        error_message = "Input error: Please provide the input as 'role, location'."
        logger.error(error_message)
        return error_message

    logger.info(f"Starting LinkedIn job search for '{role}' in '{location}'...")
    url = f"https://www.linkedin.com/jobs/search?keywords={role.replace(' ', '%20')}&location={location.replace(' ', '%20')}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        job_cards = soup.find_all('div', class_='base-card')

        if not job_cards:
            logger.warning("No job cards found on LinkedIn. The page structure may have changed.")
            return "No Jobs found for this query."

        jobs = []
        for card in job_cards:
            title_element = card.find('h3', class_='base-search-card__title')
            company_element = card.find('h4', class_='base-search-card__subtitle')
            url_element = card.find('a', class_='base-card__full-link')

            if all([title_element, company_element, url_element]):
                jobs.append({
                    "platform": "LinkedIn",
                    "title": title_element.text.strip(),
                    "company": company_element.text.strip(),
                    "url": url_element['href']
                })

        logger.info(f"Found {len(jobs)} jobs on LinkedIn.")
        return jobs if jobs else "No Jobs found for this query."

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during LinkedIn search: {e}")
        return f"Error: Could not connect to LinkedIn. {e}"
    except Exception as e:
        logger.error(f"An unexpected error occurred during LinkedIn parsing: {e}", exc_info=True)
        return f"An unexpected error occurred: {e}"