import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
import logging

from tools.linkedin_search_tool import search_linkedin_jobs
from tools.naukri_search_tool import search_naukri_jobs

# Set up a logger for this module
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.0


def create_job_agent():
    """
    Creates and returns the job search agent by defining its LLM, tools, and instructions.
    """
    logger.info("Creating job agent...")
    load_dotenv()

    # 1. Initialize the LLM (the "brain")
    llm = ChatOpenAI(temperature=LLM_TEMPERATURE, model_name=LLM_MODEL)
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
        )
    ]
    logger.info(f"Agent tools defined: {[tool.name for tool in tools]}")

    # 3. Create the prompt template (the agent's "instructions")
    template = """
    Answer the following questions as best you can. You have access to the following tools:

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

    Question: {input}
    Thought:{agent_scratchpad}
    """
    prompt = PromptTemplate.from_template(template)

    # 4. Create the agent itself
    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    # 5. Create the Agent Executor, which is what actually runs the agent
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True  # Gracefully handle if the LLM messes up formatting
    )

    logger.info("Job agent created successfully.")
    return agent_executor