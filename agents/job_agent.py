import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.memory import ConversationBufferWindowMemory
import logging


from tools.linkedin_search_tool import search_linkedin_jobs
from tools.naukri_search_tool import search_naukri_jobs
from tools.company_research_tool import research_company

# Set up a logger for this module
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
LLM_MODEL = "gemini-1.5-flash"
# LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.0
MEMORY_WINDOW_SIZE = 4


def create_job_agent():
    """
    Creates and returns the job search agent by defining its LLM, tools, and instructions.
    """
    logger.info("Creating job agent...")
    load_dotenv()

    # 1. Initialize the LLM (the "brain")
    # llm = ChatOpenAI(temperature=LLM_TEMPERATURE, model_name=LLM_MODEL)
    llm = ChatGoogleGenerativeAI(temperature=LLM_TEMPERATURE, model=LLM_MODEL, convert_system_message_to_human=True)
    logger.info(f"LLM initialized with model: {LLM_MODEL}")

    # 2. Define the tools the agent can use
    tools = [
        Tool(
            name="linkedin_job_search",
            func=search_linkedin_jobs,
            description="Use this to search for jobs on LinkedIn. The input must be a single string containing the job role and location, separated by a comma. For example: 'Software Engineer, Bengaluru'"
        ),
        Tool(
            name="naukri_job_search",
            func=search_naukri_jobs,
            description="Use this to search for jobs on Naukri.com. The input must be a single string containing the job role and location, separated by a comma. For example: 'Data Scientist, Chennai'"
        ),
        Tool(
            name="company_researcher",
            func=research_company,
            description="Use this tool to research a specific company. The input should be the company's name. This provides a summary of what the company does."
        )
    ]
    logger.info(f"Agent tools defined: {[tool.name for tool in tools]}")

    # 3. Create the prompt template (the agent's "instructions")
    template = """
        You are a helpful and proactive job search assistant. Your goal is to find relevant job opportunities for the user.
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
    2. If a search tool returns a list of jobs, first provide a brief summary.
    3. After the summary, present the jobs as a clear, markdown-formatted list. Each item should have the title, company, and a clickable URL. For example: - **Software Engineer** at Tech Corp - [Apply Here](https://example.com/job1)
    4. If a tool returns "No jobs found for this query.", suggest a helpful alternative search.

    Previous conversation history:
    {chat_history}

    New question: {input}
    {agent_scratchpad}
        """
    prompt = PromptTemplate.from_template(template)

    # Initialize Memory
    memory = ConversationBufferWindowMemory(
        k=MEMORY_WINDOW_SIZE,
        memory_key='chat_history',
        input_key='input',
        output_key='output',
        return_messages=True  # Important for the prompt
    )

    # 4. Create the agent itself
    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    # 5. Create the Agent Executor, which is what actually runs the agent
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True  # Gracefully handle if the LLM messes up formatting
    )

    logger.info("Job agent created successfully.")
    return agent_executor