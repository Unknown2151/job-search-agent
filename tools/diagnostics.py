"""
Diagnostic utilities to check API configuration and system health.
"""
import os
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def check_api_keys() -> Tuple[Dict[str, bool], List[str]]:
    """
    Check which API keys are configured.

    Returns:
        Tuple[Dict[str, bool], List[str]]: (configured_apis, missing_apis)
    """
    required_apis = {
        "GOOGLE_API_KEY": "Google Generative AI (Resume parsing, Agent AI)",
        "OPENAI_API_KEY": "OpenAI (Fallback AI model)",
        "SERPAPI_API_KEY": "SerpAPI (Company research)"
    }

    optional_apis = {
        "NOTION_API_TOKEN": "Notion (Database integration)",
        "ASSEMBLYAI_API_KEY": "AssemblyAI (Voice transcription)"
    }

    configured = {}
    missing_required = []
    missing_optional = []

    for api_key, description in required_apis.items():
        is_set = bool(os.getenv(api_key))
        configured[api_key] = is_set
        if not is_set:
            missing_required.append(f"❌ {api_key}: {description}")
        else:
            logger.info(f"✓ {api_key} configured")

    for api_key, description in optional_apis.items():
        is_set = bool(os.getenv(api_key))
        configured[api_key] = is_set
        if not is_set:
            missing_optional.append(f"⚠️  {api_key}: {description}")
        else:
            logger.info(f"✓ {api_key} configured")

    missing = missing_required + missing_optional
    return configured, missing


def get_diagnostic_message() -> str:
    """Get a user-friendly diagnostic message about missing APIs."""
    configured, missing = check_api_keys()

    if not missing:
        return "All required APIs are configured!"

    message = "**Missing API Configurations**\n\n"
    message += "The following API keys are not configured:\n\n"

    for item in missing:
        message += f"{item}\n"

    message += "\n**How to fix:**\n"
    message += "1. Create a `.env` file in the project root\n"
    message += "2. Copy contents from `.env.example`\n"
    message += "3. Fill in your API keys\n"
    message += "4. Restart the app\n\n"
    message += "**Get your keys:**\n"
    message += "- Google API: https://ai.google.dev/\n"
    message += "- OpenAI API: https://platform.openai.com/\n"
    message += "- SerpAPI: https://serpapi.com/\n"
    message += "- Notion: https://www.notion.so/my-integrations\n"
    message += "- AssemblyAI: https://www.assemblyai.com/\n"

    return message


def check_dependencies() -> Tuple[bool, List[str]]:
    """
    Check if critical dependencies are installed.

    Returns:
        Tuple[bool, List[str]]: (all_ok, missing_packages)
    """
    required_packages = [
        "streamlit",
        "langchain",
        "langchain_google_genai",
        "langgraph",
        "selenium",
        "aiohttp",
        "beautifulsoup4",
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    return len(missing) == 0, missing
