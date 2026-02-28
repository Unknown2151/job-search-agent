import logging
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent

load_dotenv()

# Import your tools
from tools.linkedin_search_tool import search_linkedin_jobs
from tools.naukri_search_tool import search_naukri_jobs
from tools.company_research_tool import research_company
from tools.application_tracker_tool import save_jobs_to_notion

SEARCH_ANALYTICS_DATA: Dict[str, Any] = {
    "total_searches": 0,
    "platform_usage": {"linkedin": 0, "naukri": 0},
    "successful_searches": 0,
    "failed_searches": 0,
}

logger = logging.getLogger(__name__)


def get_search_analytics(query: str) -> Dict[str, Any]:
    """Returns the current search analytics data."""
    logger.info("Fetching search analytics.")
    return SEARCH_ANALYTICS_DATA


def _run_linkedin_search_sync(query: str):
    """Synchronous wrapper for the async LinkedIn search function."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return executor.submit(asyncio.run, search_linkedin_jobs(query)).result()
    else:
        return asyncio.run(search_linkedin_jobs(query))


async def _parallel_job_search(query: str) -> Dict[str, Any]:
    """
    Runs LinkedIn (async HTTP) and Naukri (Selenium) job searches in parallel.

    This function is used behind a synchronous LangChain tool wrapper so that the
    agent can take advantage of concurrency without requiring an async agent
    pipeline end-to-end.
    """
    # Run LinkedIn search as an async task and Naukri search in a worker thread.
    linkedin_task = asyncio.create_task(search_linkedin_jobs(query))
    naukri_task = asyncio.to_thread(search_naukri_jobs, query)

    linkedin_result, naukri_result = await asyncio.gather(
        linkedin_task, naukri_task, return_exceptions=True
    )

    results: Dict[str, Any] = {"linkedin": linkedin_result, "naukri": naukri_result}

    # Increment simple analytics counters defensively
    for platform, result in results.items():
        if isinstance(result, list) and result:
            SEARCH_ANALYTICS_DATA["platform_usage"][platform] += 1

    return results


def parallel_job_search(query: str) -> Dict[str, Any]:
    """
    Synchronous wrapper around `_parallel_job_search` for use as a LangChain tool.

    This allows the agent to trigger concurrent LinkedIn + Naukri searches while
    exposing a simple blocking function signature.
    """
    try:
        # LangChain tools are typically executed in a synchronous context, so we can
        # safely drive the async coroutine with asyncio.run here.
        # Handle the case where an event loop is already running
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # If a loop is already running, use it directly
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(asyncio.run, _parallel_job_search(query)).result()
        else:
            # No loop running, we can use asyncio.run directly
            return asyncio.run(_parallel_job_search(query))
    except Exception as e:
        logger.error(f"Parallel job search failed: {e}", exc_info=True)
        return {
            "linkedin": f"Error during LinkedIn search: {e}",
            "naukri": f"Error during Naukri search: {e}",
        }

def create_job_agent() -> Any:
    """Creates and returns the job search agent as a runnable.

    The returned object implements `.invoke` and `.stream` and is built using
    `create_react_agent` from `langgraph.prebuilt` with the provided tools and
    system prompt.
    """
    load_dotenv()

    # Try multiple model options with fallback
    # Updated to use models actually available for your API key
    models_to_try = [
        "gemini-2.5-flash",      # Latest fast model
        "gemini-2.0-flash",      # Stable and fast
        "gemini-flash-latest",   # Alias for latest flash
        "gemini-pro-latest",     # Pro model alias
    ]

    llm = None
    last_error = None

    for model_name in models_to_try:
        try:
            logger.info(f"Attempting to initialize {model_name}...")
            candidate_llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.0,
                convert_system_message_to_human=True,
                timeout=30,
                max_retries=2
            )

            # Test the model with a simple invocation
            logger.info(f"Testing {model_name} with a simple invocation...")
            test_response = candidate_llm.invoke("Say 'OK'")

            llm = candidate_llm
            logger.info(f"Successfully initialized and tested {model_name}. Using it.")
            break
        except Exception as e:
            last_error = e
            logger.warning(f"Failed to initialize {model_name}: {str(e)[:100]}")
            continue

    if llm is None:
        logger.error(f"Could not initialize any model. Last error: {last_error}")
        raise ValueError(
            f"Failed to initialize Google AI. All models unavailable: {models_to_try}. "
            f"Last error: {last_error}. "
            f"Check your GOOGLE_API_KEY at https://ai.google.dev/"
        )

    tools = [
        Tool(
            name="linkedin_job_search",
            func=_run_linkedin_search_sync,
            coroutine=search_linkedin_jobs,
            description=(
                "Search for jobs on LinkedIn. "
                "Input must be a comma-separated string in the form 'role, location', "
                "for example: 'Software Engineer, Chennai'. "
                "Returns either a list of job dictionaries with title, company, url, and location, "
                "or an error message string if no jobs are found or the site blocks the request."
            ),
        ),
        Tool(
            name="naukri_job_search",
            func=search_naukri_jobs,
            description=(
                "Search for jobs on Naukri.com using Selenium. "
                "Input must be a comma-separated string in the form 'role, location', "
                "for example: 'Data Scientist, Bengaluru'. "
                "Returns either a list of job dictionaries with title, company, and url, "
                "or an error message string if no jobs are found or the site blocks/changes its structure."
            ),
        ),
        Tool(
            name="company_researcher",
            func=research_company,
            description=(
                "Research a specific company by name. "
                "Input must be the plain company name, for example: 'OpenAI' or 'Google India'. "
                "Returns a text summary of the most relevant page about the company, "
                "or an error message if search results or page content cannot be retrieved."
            ),
        ),
        Tool(
            name="application_tracker",
            func=save_jobs_to_notion,
            description=(
                "Save selected jobs to a Notion database. "
                "Input must be a JSON string representing a list of job objects, "
                "where each object has at least 'title', 'company', and 'url' fields. "
                "Returns a confirmation or error message."
            ),
        ),
        Tool(
            name="get_search_analytics",
            func=get_search_analytics,
            description=(
                "Get current in-memory search analytics. "
                "Input should be any non-empty string (ignored). "
                "Returns a dictionary with total searches, platform usage, and success/failure counts."
            ),
        ),
        Tool(
            name="parallel_job_search",
            func=parallel_job_search,
            description=(
                "Run LinkedIn and Naukri job searches in parallel for faster results. "
                "Input must be a comma-separated string in the form 'role, location', "
                "for example: 'Backend Engineer, Remote'. "
                "Returns a dictionary with two keys: 'linkedin' and 'naukri', "
                "each containing either a list of job dictionaries or an error message string."
            ),
        ),
    ]

    # Create system prompt for the agent
    system_prompt = (
        "You are a helpful job search assistant. You help users find job opportunities "
        "on various platforms, research companies, and track job applications. "
        "Use the available tools to search for jobs, research companies, and save applications. "
        "Always be helpful and provide clear, actionable information. "
        "When searching for jobs, try to understand the user's requirements and use appropriate search tools."
    )

    # Create agent using langgraph's create_react_agent
    # This returns a compiled graph that can be invoked directly with {"messages": [...]}
    agent = create_react_agent(llm, tools, prompt=system_prompt)
    
    return agent