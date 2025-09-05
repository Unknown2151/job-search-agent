import logging
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.memory import ConversationBufferWindowMemory

# Import your tools
from tools.linkedin_search_tool import search_linkedin_jobs
from tools.naukri_search_tool import search_naukri_jobs
from tools.company_research_tool import research_company
from tools.application_tracker_tool import save_jobs_to_notion

SEARCH_ANALYTICS_DATA = {
    "total_searches": 0,
    "platform_usage": {"linkedin": 0, "naukri": 0},
    "successful_searches": 0,
    "failed_searches": 0,
}

logger = logging.getLogger(__name__)

def get_search_analytics(query: str) -> dict:
    """Returns the current search analytics data."""
    logger.info("Fetching search analytics.")
    # In a real system, this would be calculated from a persistent log or database
    # For this project, we'll use a simple in-memory dictionary
    return SEARCH_ANALYTICS_DATA

def create_job_agent() -> AgentExecutor:
    """Creates and returns the job search agent."""
    load_dotenv()
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0, convert_system_message_to_human=True)

    tools = [
        Tool(
            name="linkedin_job_search",
            func=search_linkedin_jobs,
            description="Use this to search for jobs on LinkedIn..."
        ),
        Tool(
            name="naukri_job_search",
            func=search_naukri_jobs,
            description="Use this to search for jobs on Naukri.com..."
        ),
        Tool(
            name="company_researcher",
            func=research_company,
            description="Use this tool to research a specific company..."
        ),
        Tool(
            name="application_tracker",
            func=save_jobs_to_notion,
            description="Use this tool to save jobs to a Notion database..."
        ),
        Tool(
            name="get_search_analytics",
            func=get_search_analytics,
            description="Use this to get analytics about the job search history and performance."
        )
    ]
    prompt = PromptTemplate.from_template(
        """
        You are a helpful and proactive job search assistant.
        {resume_context}
        You have access to the following tools:
        {tools}

        Use the following format:
        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question

        Begin!

        ### IMPORTANT INSTRUCTIONS ###
        1. Always be polite and helpful.
        2. Aim to return around 10 job listings unless the user specifies a different number.
        1. If a search tool returns a list of jobs, first provide a brief summary.
        2. After the summary, present the jobs as a clear, markdown-formatted list. Each item must have the title, company, and a clickable URL. For example: - **Software Engineer** at Tech Corp - [Apply Here](https://example.com/job1)
        3. If a tool returns "No jobs found for this query.", suggest a helpful alternative search.

        Previous conversation history:
        {chat_history}

        New question: {input}
        {agent_scratchpad}
        """
    )

    memory = ConversationBufferWindowMemory(
        k=4, memory_key='chat_history', input_key='input', output_key='output', return_messages=True
    )

    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, memory=memory, verbose=True, handle_parsing_errors=True
    )

    return agent_executor