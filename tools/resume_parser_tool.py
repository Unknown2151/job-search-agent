import io
import PyPDF2
import docx
import logging
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)

def parse_resume(file_bytes: bytes, file_name: str, timeout: int = 30) -> dict | str:
    """
    Parses an uploaded resume file (PDF or DOCX) to extract key information.

    Args:
        file_bytes (bytes): The content of the uploaded file in bytes.
        file_name (str): The name of the uploaded file.
        timeout (int): Timeout for LLM call in seconds.

    Returns:
        dict | str: A dictionary with extracted skills and roles, or an error string.
    """
    logger.info(f"Parsing resume file: {file_name}")

    try:
        # --- 1. Extract Raw Text from File ---
        if file_name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            raw_text = "".join(page.extract_text() for page in pdf_reader.pages)
        elif file_name.endswith('.docx'):
            doc = docx.Document(io.BytesIO(file_bytes))
            raw_text = "\n".join([para.text for para in doc.paragraphs])
        else:
            return "Error: Unsupported file type. Please upload a .pdf or .docx file."

        if not raw_text.strip():
            return "Error: Could not extract any text from the resume."

        # --- 2. Use LLM to Parse the Raw Text into JSON ---
        try:
            # Try multiple models with fallback
            # Updated to use models actually available for your API key
            models_to_try = [
                "gemini-2.5-flash",      # Latest fast model
                "gemini-2.0-flash",      # Stable and fast
                "gemini-flash-latest",   # Alias for latest flash
            ]

            llm = None
            for model_name in models_to_try:
                try:
                    logger.info(f"Trying model: {model_name}")
                    candidate_llm = ChatGoogleGenerativeAI(
                        model=model_name,
                        temperature=0.0,
                        timeout=timeout,
                        max_retries=1
                    )

                    # Test the model with a simple invocation
                    test_response = candidate_llm.invoke("Test")

                    llm = candidate_llm
                    logger.info(f"Model {model_name} works! Using it.")
                    break
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {str(e)[:80]}")
                    continue

            if llm is None:
                logger.error("Could not initialize any LLM model - all models failed")
                return "Error: No available AI models. Check your GOOGLE_API_KEY and ensure it has model access. Try checking https://ai.google.dev/ for available models."

        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return f"Error: Could not initialize AI model. ({str(e)[:100]})"

        parser = JsonOutputParser()

        prompt = PromptTemplate(
            template="""
                You are an expert HR assistant. Analyze the following resume text and extract the candidate's key skills and a concise, probable job title or role they would be suitable for.
                Return the result in a clean JSON format.

                Example Output:
                {{
                    "job_role": "Senior Software Engineer",
                    "skills": ["Python", "Django", "AWS", "Docker", "React"]
                }}

                Resume Text:
                {resume_text}

                JSON Output:
                """,
            input_variables=["resume_text"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        truncated_text = raw_text[:3000]  # Truncate to 3000 characters

        try:
            chain = prompt | llm | parser
            parsed_result = chain.invoke({"resume_text": truncated_text})
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            return f"Error: AI parsing failed. The LLM service may be slow or unavailable. ({str(e)[:100]})"

        parsed_result["raw_resume_text"] = truncated_text

        logger.info(f"Successfully parsed resume. Found role: {parsed_result.get('job_role')}")
        return parsed_result

    except Exception as e:
        logger.error(f"Failed to parse resume: {e}", exc_info=True)
        return f"An error occurred while parsing the resume: {e}"