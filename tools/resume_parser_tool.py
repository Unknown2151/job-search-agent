import io
import PyPDF2
import docx
import logging
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from llm_factory import get_google_llm

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

        try:
            llm = get_google_llm(temperature=0.0)
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

        truncated_text = raw_text[:3000]

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