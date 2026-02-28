import logging
import sqlite3
from typing import TypedDict, List, Dict, Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from agents.job_agent import create_job_agent

logger = logging.getLogger(__name__)

load_dotenv()


class ConversationState(TypedDict):
    """
    State schema for the LangGraph-based persistent conversation.

    This graph treats the existing LangChain AgentExecutor as a black box and
    focuses on persisting high-level question/answer pairs to SQLite so that
    they can be recovered across sessions.
    """

    input: str
    resume_context: str
    response: str


# Lazy-initialized shared agent instance (created on first use, not at import time).
_agent_executor = None


def _get_agent_executor():
    """Get or create the shared agent executor (lazy initialization)."""
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = create_job_agent()
    return _agent_executor


def _run_agent(state: ConversationState) -> ConversationState:
    """
    Node that calls the existing agent and records its final response.

    This wraps the agent so that LangGraph can checkpoint the input and output.
    """
    user_input = state.get("input", "")
    resume_context = state.get("resume_context", "")

    logger.info("LangGraph node invoking agent for persistent run.")

    # Combine input with resume context for better agent performance
    full_input = user_input
    if resume_context:
        full_input = f"(Resume Context: {resume_context})\n\n{user_input}"

    # Invoke the agent with the new message format
    try:
        result = _get_agent_executor().invoke(
            {"messages": [HumanMessage(content=full_input)]}
        )
        
        # Extract response from the new format
        output_text = ""
        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    content = last_message.content
                    # Handle list format (Gemini)
                    if isinstance(content, list):
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict) and 'text' in block:
                                text_parts.append(block['text'])
                            elif isinstance(block, str):
                                text_parts.append(block)
                        output_text = '\n'.join(text_parts)
                    else:
                        output_text = str(content)
        
        if not output_text:
            output_text = "Agent completed but returned no response."
            
    except Exception as exc:
        logger.error("Agent invocation failed: %s", exc, exc_info=True)
        output_text = "Sorry, an internal error occurred while processing your request."

    return {
        "input": user_input,
        "resume_context": resume_context,
        "response": output_text,
    }


def _build_persistent_graph(db_path: str = "job_agent_langgraph.db"):
    """
    Build and compile the LangGraph StateGraph with a SQLite checkpointer.
    
    Note: check_same_thread=False is safe here because we control all SQLite access
    and this is a local app (not a production multi-threaded server).
    """
    builder = StateGraph(ConversationState)
    builder.add_node("agent", _run_agent)
    builder.set_entry_point("agent")

    # Create checkpointer with check_same_thread=False to handle Streamlit's threading
    # This is safe for local apps where we control all database access
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn=conn)
    graph = builder.compile(checkpointer=checkpointer)
    return graph


def get_persistent_graph():
    """
    Returns a compiled LangGraph graph with SQLite-backed persistence.

    The caller is responsible for passing a stable `thread_id` via the
    LangGraph `config={"configurable": {"thread_id": ...}}` mechanism so that
    conversations can be resumed across sessions.
    """
    return _build_persistent_graph()

