import os
import json
import logging
import asyncio
from notion_client import AsyncClient

logger = logging.getLogger(__name__)


async def save_single_job(notion: AsyncClient, database_id: str, job: dict) -> tuple[bool, str]:
    """Helper function to save a single job asynchronously."""
    try:
        title = job.get('title', 'N/A')
        company = job.get('company', 'N/A')
        url = job.get('url', '#')

        await notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Name": {"title": [{"text": {"content": f"{title} at {company}"}}]},
                "URL": {"url": url},
                "Status": {"select": {"name": "Saved"}}
            }
        )
        return True, f"{title} at {company}"
    except Exception as e:
        logger.warning(f"Failed to save job: {e}")
        return False, f"{job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}"


async def _save_jobs_async(jobs_json: str) -> str:
    """Core async logic to save jobs in parallel."""
    logger.info("Received request to save jobs to Notion.")

    notion_token = os.getenv("NOTION_API_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not notion_token or not database_id:
        return "ValueError: NOTION_API_TOKEN and NOTION_DATABASE_ID must be set in the .env file."

    database_id = database_id.replace("-", "")

    try:
        jobs_to_save = json.loads(jobs_json)
        if not isinstance(jobs_to_save, list) or not jobs_to_save:
            return "No jobs were selected to be saved."
    except json.JSONDecodeError:
        return "Error: Invalid JSON provided."

    notion = AsyncClient(auth=notion_token)

    tasks = [save_single_job(notion, database_id, job) for job in jobs_to_save]
    results = await asyncio.gather(*tasks)

    saved_count = sum(1 for success, _ in results if success)
    failed_jobs = [name for success, name in results if not success]

    if failed_jobs:
        return f"Saved {saved_count} of {len(jobs_to_save)} job(s). Failed: {', '.join(failed_jobs)}"

    return f"Successfully saved {saved_count} job(s) to your Notion database."


def save_jobs_to_notion(jobs_json: str) -> str:
    """
    Synchronous wrapper for the async Notion saving tool.
    Allows LangChain and Streamlit to easily call this tool without event loop conflicts.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return executor.submit(asyncio.run, _save_jobs_async(jobs_json)).result()
    else:
        return asyncio.run(_save_jobs_async(jobs_json))