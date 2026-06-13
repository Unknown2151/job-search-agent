import logging
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


def get_google_llm(temperature: float = 0.0, timeout: int = 30) -> ChatGoogleGenerativeAI:
    """
    Centralized factory to initialize the best available Google LLM.
    Ensures all tools and agents use the exact same model configuration.
    """
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest"
    ]

    for model_name in models_to_try:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                timeout=timeout,
                max_retries=2
            )
            # Silent dry-run to verify access
            llm.invoke("ping")
            logger.info(f"Initialized LLM factory with: {model_name}")
            return llm
        except Exception as e:
            logger.debug(f"Factory fallback - {model_name} failed: {e}")
            continue

    raise RuntimeError("LLM Factory failed: No models available. Check GOOGLE_API_KEY.")