from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

# Set up a logger for this module
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
WAIT_TIME = 5  # seconds


def search_naukri_jobs(query: str) -> list[dict] | str:
    """
    Searches for jobs on Naukri.com using Selenium to handle JavaScript loading.

    Args:
        query (str): A comma-separated string containing the role and location.
                     Example: "Data Scientist, Chennai"

    Returns:
        list[dict] | str: A list of job dictionaries or an error message string.
    """
    logger.info(f"Received Naukri.com search query: '{query}'")
    try:
        role, location = [item.strip() for item in query.split(',')]
    except ValueError:
        error_message = "Input error: Please provide the input as 'role, location'."
        logger.error(error_message)
        return error_message

    logger.info(f"Starting Naukri.com search for '{role}' in '{location}'...")
    url = f"https://www.naukri.com/{role.lower().replace(' ', '-')}-jobs-in-{location.lower()}"

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        logger.info(f"Waiting for {WAIT_TIME} seconds for page to load...")
        time.sleep(WAIT_TIME)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        job_elements = soup.find_all('div', class_='srp-jobtuple-wrapper')
        if not job_elements:
            logger.warning("Primary selector not found, trying fallback 'article.jobTuple'")
            job_elements = soup.find_all('article', class_='jobTuple')

        if not job_elements:
            logger.warning("No job elements found on Naukri.com. The page structure may have changed.")
            return "No Jobs found for this query."

        jobs = []
        for job_element in job_elements:
            title_element = job_element.find('a', class_='title')
            company_element = job_element.find('a', class_='comp-name')

            if title_element and company_element:
                jobs.append({
                    "platform": "Naukri.com",
                    "title": title_element.text.strip(),
                    "company": company_element.text.strip(),
                    "url": title_element['href']
                })

        logger.info(f"Found {len(jobs)} jobs on Naukri.com.")
        return jobs if jobs else "No Jobs found for this query."
    except Exception as e:
        logger.error(f"An unexpected error occurred during Naukri.com search: {e}", exc_info=True)
        return f"An unexpected error occurred: {e}"
    finally:
        if driver:
            driver.quit()
            logger.info("Selenium WebDriver closed.")