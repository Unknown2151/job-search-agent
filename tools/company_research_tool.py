import os
import requests
from serpapi import GoogleSearch
from newspaper import Article, ArticleException
import logging

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

    # 1. Search for the company on Google using SerpApi
    try:
        search_params = {
            "q": f"{company_name} company profile",
            "engine": "google",
            "api_key": os.getenv("SERPAPI_API_KEY")
        }
        search = GoogleSearch(search_params)
        results = search.get_dict()

        if "organic_results" not in results or not results["organic_results"]:
            logger.warning(f"No organic results found for {company_name}")
            return f"Sorry, I could not find any search results for {company_name}."

        # Get the URL of the top search result
        top_result_url = results["organic_results"][0]['link']
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
        return f"An unexpected error occurred while processing the company information."