import os
from serpapi import GoogleSearch
from newspaper import Article, ArticleException
import logging
from typing import Optional

# Set up a logger for this module
logger = logging.getLogger(__name__)


def research_company(company_name: str) -> str:
    """
    Researches a company by searching for it on Google, reading the top result,
    and returning a summary.

    Args:
        company_name (str): The name of the company to research.

    Returns:
        str: A summary of the company information or an error message.
    """
    logger.info(f"Starting research for company: {company_name}")

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        logger.error("SERPAPI_API_KEY is not set in the environment.")
        return "Configuration error: SERPAPI_API_KEY is not set. Please configure it in your environment."

    # 1. Search for the company on Google using SerpApi
    try:
        search_params = {
            "q": f"{company_name} company profile",
            "engine": "google",
            "api_key": api_key,
        }
        search = GoogleSearch(search_params)
        results = search.get_dict()

        organic_results = results.get("organic_results") or []
        if not organic_results:
            logger.warning(f"No organic results found for {company_name}")
            return f"Sorry, I could not find any search results for {company_name}."

        # Get the URL of the top search result
        top_result_url: Optional[str] = organic_results[0].get("link")
        if not top_result_url:
            logger.warning("Top organic result did not contain a link.")
            return "Sorry, I found a search result but it did not contain a usable link."

        logger.info(f"Found top result URL: {top_result_url}")

    except Exception as e:
        logger.error(f"SerpApi search failed: {e}")
        return f"Sorry, the company search failed. {e}"

    # 2. Scrape and parse the article from the URL
    try:
        article = Article(top_result_url)
        article.download()
        article.parse()

        # Check if text was successfully extracted
        if not article.text:
            logger.warning(f"Could not extract text from URL: {top_result_url}")
            return "Sorry, I found a relevant page but could not extract its content."

        return article.text

    except ArticleException as e:
        logger.error(f"Newspaper article download/parse failed: {e}")
        return f"Sorry, I could not read the content from the found page. {e}"
    except Exception as e:
        logger.error(f"An unexpected error occurred during article processing: {e}", exc_info=True)
        return "An unexpected error occurred while processing the company information."