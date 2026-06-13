import logging
import re
from datetime import datetime
from typing import Final

from newspaper import Article, ArticleException
from langchain_core.prompts import PromptTemplate
from llm_factory import get_google_llm

logger = logging.getLogger(__name__)

MAX_ANALYSIS_CHARS: Final[int] = 8000


def _truncate_text_for_analysis(text: str, max_chars: int = MAX_ANALYSIS_CHARS) -> str:
    """
    Truncate long input text to the most relevant sections for analysis.

    Heuristic:
    - If the text is already short enough, return it unchanged.
    - Otherwise, try to keep sections that mention common headings such as
      'summary', 'experience', 'work experience', and 'skills'.
    - If no headings are found, fall back to a simple leading substring.
    """
    if len(text) <= max_chars:
        return text

    lowered = text.lower()
    snippets: list[str] = []
    headings = ["summary", "experience", "work experience", "skills", "core skills"]

    for heading in headings:
        idx = lowered.find(heading)
        if idx != -1:
            start = max(0, idx - max_chars // 4)
            end = min(len(text), idx + max_chars // 2)
            snippets.append(text[start:end])

    try:
        year_pattern = re.compile(r"(?:19|20)\d{2}")
        all_years = [int(y) for y in year_pattern.findall(text)]
        if all_years:
            current_year = datetime.now().year
            latest_year = max(all_years)
            cutoff_year = max(latest_year - 5, current_year - 10)

            lines = text.splitlines()
            recent_lines: list[str] = []
            for line in lines:
                years_in_line = [int(y) for y in year_pattern.findall(line)]
                if any(y >= cutoff_year for y in years_in_line):
                    recent_lines.append(line)

            if recent_lines:
                recent_block = "\n".join(recent_lines)
                snippets.append(recent_block)
    except Exception:
        pass

    if snippets:
        combined = "\n\n".join(snippets)
        return combined[:max_chars]

    return text[:max_chars]


def analyze_skill_gap(resume_text: str, job_url: str) -> str:
    """
    Analyzes the gap between skills in a resume and a job description from a URL.

    Args:
        resume_text (str): The full text of the user's resume.
        job_url (str): The URL of the job posting to analyze.

    Returns:
        str: A markdown-formatted analysis of the skill gap.
    """
    logger.info(f"Starting skill gap analysis for job URL: {job_url}")

    if not resume_text or not job_url:
        return "Error: Both a resume and a job URL are required for analysis."

    try:
        article = Article(job_url)
        article.download()
        article.parse()
        job_description_text = article.text
        if not job_description_text:
            logger.warning("No text could be extracted from the job description URL.")
            return "Error: Could not extract the job description from the provided URL."
    except ArticleException as e:
        logger.error(f"Failed to scrape job URL {job_url}: {e}")
        return "Error: Failed to read the job description from the URL. It may be protected or unavailable."
    except Exception as e:
        logger.error(f"An unexpected error occurred during scraping: {e}", exc_info=True)
        return "An unexpected error occurred while fetching the job description."

    resume_snippet = _truncate_text_for_analysis(resume_text)
    job_description_snippet = _truncate_text_for_analysis(job_description_text)

    try:
        try:
            llm = get_google_llm(temperature=0.1)
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return "Error: Could not initialize AI model for skill analysis. Check your GOOGLE_API_KEY."

        analysis_prompt = PromptTemplate.from_template(
            """
            You are an expert career coach providing a skill gap analysis. Your tone should be encouraging but realistic.
            Compare the provided RESUME against the JOB DESCRIPTION and generate a markdown-formatted report with the following sections:

            ### Skills Match
            A bulleted list of key skills and qualifications from the job description that the candidate possesses.

            ### Skills to Develop
            A bulleted list of key skills from the job description that are NOT obviously present in the resume. For each missing skill, provide a brief, one-sentence suggestion on how to learn it (e.g., "Consider an online course on Coursera," or "Build a personal project using this technology.").

            ### SUMMARY
            A brief, 2-3 sentence summary of the candidate's overall fit for the role.

            ---

            RESUME:
            {resume_text}

            ---

            JOB DESCRIPTION:
            {job_description}
            """
        )

        chain = analysis_prompt | llm
        analysis_result = chain.invoke({
            "resume_text": resume_snippet,
            "job_description": job_description_snippet,
        })

        return analysis_result.content

    except Exception as e:
        logger.error(f"LLM analysis for skill gap failed: {e}", exc_info=True)
        return "An error occurred while analyzing the skill gap."