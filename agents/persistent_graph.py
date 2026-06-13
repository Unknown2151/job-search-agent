import logging
import sqlite3
from typing import TypedDict, Annotated, Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages

from agents.job_agent import create_job_agent

logger = logging.getLogger(__name__)
load_dotenv()


class ConversationState(TypedDict):
    """
    State schema for the LangGraph-based persistent conversation.
    By using 'add_messages', SQLite will now maintain a continuous log of
    Tool Calls, JSON data, and Agent responses. No more amnesia!
    """
    input: str
    resume_context: str
    response: str
    messages: Annotated[list[Any], add_messages]


_agent_executor = None


def _get_agent_executor():
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = create_job_agent()
    return _agent_executor


def _run_agent(state: ConversationState) -> dict:
    user_input = state.get("input", "")
    resume_context = state.get("resume_context", "")
    history = state.get("messages", [])

    logger.info("LangGraph node invoking agent for persistent run.")

    full_input = user_input
    if resume_context and len(history) == 0:
        full_input = f"(Resume Context: {resume_context})\n\n{user_input}"

    new_user_msg = HumanMessage(content=full_input)

    messages_to_pass = history + [new_user_msg]

    try:
        result = _get_agent_executor().invoke({"messages": messages_to_pass})

        output_text = "Agent completed but returned no response."
        new_msgs = []

        if isinstance(result, dict) and "messages" in result:
            returned_messages = result["messages"]

            new_msgs = returned_messages[len(history):]

            if new_msgs:
                last_message = new_msgs[-1]
                if hasattr(last_message, 'content'):
                    content = last_message.content
                    if isinstance(content, list):
                        text_parts = [block['text'] for block in content if isinstance(block, dict) and 'text' in block]
                        output_text = '\n'.join(text_parts)
                    else:
                        output_text = str(content)

    except Exception as exc:
        logger.error("Agent invocation failed: %s", exc, exc_info=True)
        output_text = "Sorry, an internal error occurred while processing your request."
        new_msgs = [new_user_msg]  # At least save the user's attempt

    return {
        "input": user_input,
        "resume_context": resume_context,
        "response": output_text,
        "messages": new_msgs
    }


def _build_persistent_graph(db_path: str = "job_agent_langgraph.db"):
    builder = StateGraph(ConversationState)
    builder.add_node("agent", _run_agent)
    builder.set_entry_point("agent")

    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn=conn)
    graph = builder.compile(checkpointer=checkpointer)
    return graph


def get_persistent_graph():
    return _build_persistent_graph()