import logging
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent

from llm_factory import get_google_llm

load_dotenv()

# Import your tools
from tools.linkedin_search_tool import search_linkedin_jobs
from tools.naukri_search_tool import search_naukri_jobs
from tools.indeed_search_tool import search_indeed_jobs
from tools.company_research_tool import research_company
from tools.application_tracker_tool import save_jobs_to_notion

SEARCH_ANALYTICS_DATA: Dict[str, Any] = {
    "total_searches": 0,
    "platform_usage": {"linkedin": 0, "naukri": 0, "indeed": 0},
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


def _run_indeed_search_sync(query: str):
    """Synchronous wrapper that parses 'role, location' and calls search_indeed_jobs."""
    try:
        role, location = [item.strip() for item in query.split(',')]
    except ValueError:
        return "Input error: Please provide the input as 'role, location'."
    return search_indeed_jobs(role, location)


async def _parallel_job_search(query: str) -> Dict[str, Any]:
    """
    Runs LinkedIn, Naukri, and Indeed job searches in parallel.

    LinkedIn runs as an async task; Naukri and Indeed run in worker threads
    since they are synchronous (API calls via requests).
    """
    linkedin_task = asyncio.create_task(search_linkedin_jobs(query))
    naukri_task = asyncio.to_thread(search_naukri_jobs, query)

    try:
        role, location = [item.strip() for item in query.split(',')]
    except ValueError:
        role, location = query, ""

    async def delayed_indeed():
        await asyncio.sleep(0.5)
        return await asyncio.to_thread(search_indeed_jobs, role, location)

    indeed_task = asyncio.create_task(delayed_indeed())

    linkedin_result, naukri_result, indeed_result = await asyncio.gather(
        linkedin_task, naukri_task, indeed_task, return_exceptions=True
    )

    results: Dict[str, Any] = {
        "linkedin": linkedin_result,
        "naukri": naukri_result,
        "indeed": indeed_result,
    }

    for platform, result in results.items():
        if isinstance(result, list) and result:
            SEARCH_ANALYTICS_DATA["platform_usage"][platform] += 1

    return results


def parallel_job_search(query: str) -> Dict[str, Any]:
    """
    Synchronous wrapper around `_parallel_job_search` for use as a LangChain tool.

    This allows the agent to trigger concurrent LinkedIn + Naukri + Indeed searches
    while exposing a simple blocking function signature.
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(asyncio.run, _parallel_job_search(query)).result()
        else:
            return asyncio.run(_parallel_job_search(query))
    except Exception as e:
        logger.error(f"Parallel job search failed: {e}", exc_info=True)
        return {
            "linkedin": f"Error during LinkedIn search: {e}",
            "naukri": f"Error during Naukri search: {e}",
            "indeed": f"Error during Indeed search: {e}",
        }


def create_job_agent() -> Any:
    """Creates and returns the job search agent as a runnable.

    The returned object implements `.invoke` and `.stream` and is built using
    `create_react_agent` from `langgraph.prebuilt` with the provided tools and
    system prompt.
    """
    load_dotenv()

    llm = get_google_llm(temperature=0.0)

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
                "Search for jobs on Naukri.com (India-focused). "
                "Input must be a comma-separated string in the form 'role, location', "
                "for example: 'Data Scientist, Bengaluru'. "
                "Returns either a list of job dictionaries with title, company, url, and location, "
                "or an error message string if no jobs are found."
            ),
        ),
        Tool(
            name="indeed_job_search",
            func=_run_indeed_search_sync,
            description=(
                "Search for jobs on Indeed. "
                "Input must be a comma-separated string in the form 'role, location', "
                "for example: 'Backend Engineer, Mumbai'. "
                "Returns either a list of job dictionaries with title, company, url, and location, "
                "or an error message string if no jobs are found."
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
                "Run LinkedIn, Naukri, and Indeed job searches in parallel for faster results. "
                "Input must be a comma-separated string in the form 'role, location', "
                "for example: 'Backend Engineer, Remote'. "
                "Returns a dictionary with three keys: 'linkedin', 'naukri', and 'indeed', "
                "each containing either a list of job dictionaries or an error message string."
            ),
        ),
    ]

    system_prompt = (
        "You are a helpful job search assistant. You help users find job opportunities "
        "on various platforms, research companies, and track job applications. "
        "\n\nIMPORTANT FORMATTING RULES FOR JOB RESULTS:\n"
        "When presenting job search results, ALWAYS format them as follows:\n"
        "- Use numbered list format: 1. **Title** at Company\n"
        "- On the next line, include: **URL:** https://...\n"
        "- Include location and job type information\n"
        "NEVER omit the URL - it is critical for the UI to show save buttons.\n"
        "Example format:\n"
        "1. **Senior Python Developer** at PayPal\n"
        "   **URL:** https://linkedin.com/jobs/view/123\n"
        "   Location: Bangalore, India\n"
        "\n\nIMPORTANT BEHAVIOR:\n"
        "When the user asks you to save jobs to Notion:\n"
        "1. DO NOT ask the user to re-provide job details you already found.\n"
        "2. DIRECTLY use the application_tracker tool with the job details from your search results.\n"
        "3. For each job you want to save, call the application_tracker with JSON like:\n"
        "   [{\"title\": \"Job Title\", \"company\": \"Company Name\", \"url\": \"https://...\"}]\n"
        "4. Report back to the user that the jobs have been saved.\n"
        "\nAlways extract job information (title, company, URL) from search results you just provided, "
        "and use the application_tracker tool directly to save them. Never ask users to re-enter information you already have."
    )

    agent = create_react_agent(llm, tools, prompt=system_prompt)

    return agent