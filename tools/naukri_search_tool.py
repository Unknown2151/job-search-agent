from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import logging
import os
from tools.retry_utils import retry_sync, RetryConfig

# Set up a logger for this module
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
DEFAULT_WAIT_TIME_SECONDS: int = 10
MAX_RESULTS: int = 10

# List of fallback selectors to make the scraper resilient to minor DOM changes.
# Each entry is a (tag_name, class_name) pair that should contain job cards.
JOB_CONTAINER_SELECTORS: list[tuple[str, str]] = [
    ("div", "srp-jobtuple-wrapper"),  # primary container
    ("article", "jobTuple"),          # older/fallback container
]

# Retry configuration for Naukri searches
NAUKRI_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    initial_delay=3.0,
    max_delay=15.0,
    exponential_base=2.0
)


def _create_webdriver() -> webdriver.Chrome:
    """
    Creates and returns a configured Chrome WebDriver instance.

    Prefers a system-installed ChromeDriver (e.g., baked into the Docker image) if
    the CHROMEDRIVER_PATH environment variable is set; otherwise falls back to
    webdriver_manager to download a compatible driver at runtime.
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    if chromedriver_path and os.path.exists(chromedriver_path):
        logger.info(f"Using ChromeDriver from CHROMEDRIVER_PATH: {chromedriver_path}")
        service = Service(chromedriver_path)
    else:
        logger.info("Using webdriver_manager to install ChromeDriver at runtime.")
        service = Service(ChromeDriverManager().install())

    return webdriver.Chrome(service=service, options=options)


@retry_sync(NAUKRI_RETRY_CONFIG, exceptions=(Exception,))
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

    driver = None
    try:
        driver = _create_webdriver()
        driver.get(url)
        try:
            WebDriverWait(driver, DEFAULT_WAIT_TIME_SECONDS).until(
                EC.presence_of_element_located((By.CLASS_NAME, "srp-jobtuple-wrapper"))
            )
            logger.info("Page loaded and job elements found.")
        except Exception as wait_error:
            # If the explicit wait fails (e.g., blocked, structure change), we still
            # attempt to parse the current page source instead of crashing.
            logger.warning(
                "Explicit wait for Naukri job elements timed out or failed; "
                "attempting to parse whatever content is available. Error: %s",
                wait_error,
            )

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        job_elements: list = []
        for tag_name, class_name in JOB_CONTAINER_SELECTORS:
            job_elements = soup.find_all(tag_name, class_=class_name)
            if job_elements:
                logger.info(
                    "Found %d job elements on Naukri.com using selector (%s, %s).",
                    len(job_elements),
                    tag_name,
                    class_name,
                )
                break

        if not job_elements:
            logger.warning(
                "No job elements found on Naukri.com using any known selectors. "
                "The page structure may have changed."
            )
            return "No Jobs found for this query."

        jobs: list[dict] = []
        for job_element in job_elements:
            if len(jobs) >= MAX_RESULTS:
                break
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