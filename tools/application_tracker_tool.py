import os
import json
import logging
from notion_client import Client

logger = logging.getLogger(__name__)

def save_jobs_to_notion(jobs_json: str) -> str:
    """
    Saves a list of jobs to a Notion database.

    Args:
        jobs_json (str): A JSON string representing a list of job objects.
                         Each object must have 'title', 'company', and 'url'.

    Returns:
        str: A confirmation message or an error string.
    """
    logger.info("Received request to save jobs to Notion.")

    try:
        notion_token = os.getenv("NOTION_API_TOKEN")
        database_id = os.getenv("NOTION_DATABASE_ID")

        if not notion_token or not database_id:
            raise ValueError("NOTION_API_TOKEN and NOTION_DATABASE_ID must be set in the .env file.")

        jobs_to_save = json.loads(jobs_json)
        if not isinstance(jobs_to_save, list) or not jobs_to_save:
            return "No jobs were selected to be saved."

        notion = Client(auth=notion_token)
        saved_count = 0

        for job in jobs_to_save:
            title = job.get('title', 'N/A')
            company = job.get('company', 'N/A')
            url = job.get('url', '#')

            # Create a new page in the Notion database
            notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Name": {"title": [{"text": {"content": f"{title} at {company}"}}]},
                    "URL": {"url": url},
                    "Status": {"select": {"name": "Saved"}}
                }
            )
            saved_count += 1

        success_message = f"Successfully saved {saved_count} job(s) to your Notion database."
        logger.info(success_message)
        return success_message

    except Exception as e:
        logger.error(f"Failed to save jobs to Notion: {e}", exc_info=True)
        return f"An error occurred while saving to Notion: {e}"