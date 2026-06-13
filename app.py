import streamlit as st
import logging
import json
import time
import os
import uuid
import assemblyai as aai
import pandas as pd
from langchain_core.messages import HumanMessage
from agents.job_agent import create_job_agent, SEARCH_ANALYTICS_DATA
from config import configure_logging
from tools.diagnostics import check_api_keys, get_diagnostic_message

# --- CONFIGURATION ---
configure_logging()
logger = logging.getLogger(__name__)
st.set_page_config(page_title="AI Job Search Agent", page_icon="🤖", layout="wide")


# --- API KEY VALIDATION ---
@st.cache_resource
def validate_api_configuration():
    """Validate and show API configuration."""
    configured, missing = check_api_keys()
    missing_required = [m for m in missing if "❌" in m]

    if missing_required:
        st.error("⚠️ **Missing Required API Keys**")
        st.markdown(get_diagnostic_message())
        st.stop()

    return True


# Check APIs at startup
validate_api_configuration()


# --- AGENT INITIALIZATION ---
@st.cache_resource
def get_agent_executor():
    """Initializes and returns the standard in-memory AgentExecutor."""
    return create_job_agent()


@st.cache_resource
def get_persistent_graph():
    """
    Initializes and returns the LangGraph-based persistent graph.
    """
    from agents.persistent_graph import get_persistent_graph as _build_graph
    return _build_graph()


# --- UI HELPER FUNCTIONS ---
def handle_resume_upload():
    """Handles the resume upload and analysis in the sidebar."""
    with st.sidebar:
        st.header("📄 Your Resume")
        uploaded_file = st.file_uploader("Upload to personalize your search.", type=["pdf", "docx"])

        if uploaded_file:
            if st.session_state.get("resume_filename") != uploaded_file.name:
                with st.spinner("Analyzing your resume..."):
                    file_bytes = uploaded_file.getvalue()
                    st.session_state.resume_filename = uploaded_file.name
                    from tools.resume_parser_tool import parse_resume
                    st.session_state.resume_data = parse_resume(file_bytes, uploaded_file.name)

            if isinstance(st.session_state.get("resume_data"), dict):
                st.success("Resume analyzed!")
                st.session_state.resume_text = st.session_state.resume_data.get("raw_resume_text")
                st.write(f"**Role:** {st.session_state.resume_data.get('job_role', 'N/A')}")
                st.write(f"**Skills:** {', '.join(st.session_state.resume_data.get('skills', []))}")
            else:
                st.error(st.session_state.get("resume_data", "Could not parse resume."))


def display_chat_messages():
    """Displays the chat history and the job application tracker UI."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)
            if message["role"] == "assistant" and "job_data" in message:
                display_application_tracker(message)


def display_application_tracker(message):
    """Displays a compact UI for tracking, analyzing, and exporting jobs."""
    job_list = message["job_data"]

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        with st.expander("Save Jobs to Notion CRM", expanded=False):
            with st.form(key=f"form_{message['timestamp']}"):
                st.caption("Select jobs to track in your database:")
                selected_jobs = []
                for i, job in enumerate(job_list):
                    # Clean checkbox with bold title
                    if st.checkbox(f"**{job.get('title', 'N/A')}** at {job.get('company', 'N/A')}",
                                   key=f"job_{message['timestamp']}_{i}"):
                        selected_jobs.append(job)

                submitted = st.form_submit_button("Push Selected to Notion", use_container_width=True)
                if submitted:
                    if selected_jobs:
                        with st.spinner("Saving to Notion..."):
                            from tools.application_tracker_tool import save_jobs_to_notion
                            jobs_json_str = json.dumps(selected_jobs)
                            result = save_jobs_to_notion(jobs_json_str)
                            st.success(result)
                    else:
                        st.warning("Please select at least one job to save.")

    with col2:
        with st.expander("Export Results", expanded=False):
            st.caption("Download locally:")
            df = pd.DataFrame(job_list)
            st.download_button("Download CSV", data=df.to_csv(index=False).encode('utf-8'),
                               file_name=f"jobs_{message['timestamp']}.csv", mime="text/csv", use_container_width=True)
            st.download_button("Download JSON", data=df.to_json(orient='records', indent=2).encode('utf-8'),
                               file_name=f"jobs_{message['timestamp']}.json", mime="application/json",
                               use_container_width=True)

    # --- Skill Gap Analysis (Now front and center) ---
    st.markdown("##### AI Career Coach")

    job_options = {f"{job.get('title')} at {job.get('company')}": job.get('url') for job in job_list}
    selected_job_title = st.selectbox("Select a job to analyze your skill match:", options=job_options.keys(),
                                      index=None, placeholder="Choose a job...")

    if st.button("Analyze My Fit", key=f"analyze_{message['timestamp']}"):
        if not selected_job_title:
            st.warning("Please select a job from the list above to analyze.")
        elif "resume_text" not in st.session_state or not st.session_state.resume_text:
            st.warning("Please upload your resume in the sidebar before analyzing your fit.")
        else:
            with st.spinner("The Career Coach is analyzing your profile..."):
                from tools.skill_analyzer_tool import analyze_skill_gap
                job_url = job_options[selected_job_title]
                resume_text = st.session_state.resume_text
                analysis_result = analyze_skill_gap(resume_text, job_url)

                with st.expander(f"Skill Gap Analysis for: **{selected_job_title}**", expanded=True):
                    st.markdown(analysis_result)


def extract_job_data_from_state(result: dict):
    """
    Extracts job data by reading the raw tool outputs directly from LangGraph state,
    eliminating the need for fragile Regex Markdown parsing.
    """
    job_list = []
    messages = result.get("messages", [])

    for msg in messages:
        if msg.type == "tool":
            if msg.name in ["parallel_job_search", "linkedin_job_search", "naukri_job_search", "indeed_job_search"]:
                try:
                    raw_data = json.loads(msg.content)

                    if isinstance(raw_data, dict):
                        for platform, jobs in raw_data.items():
                            if isinstance(jobs, list):
                                job_list.extend(jobs)
                    elif isinstance(raw_data, list):
                        job_list.extend(raw_data)

                except json.JSONDecodeError:
                    continue

    unique_jobs = {job['url']: job for job in job_list if 'url' in job}.values()
    return list(unique_jobs)


def process_user_prompt(prompt):
    """Processes the user's input, runs the agent, and handles the response."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    SEARCH_ANALYTICS_DATA["total_searches"] += 1

    with st.chat_message("assistant"):
        final_response_text = ""
        raw_state = {}

        with st.spinner("The agent is thinking..."):
            try:
                input_data = {"input": prompt, "resume_context": ""}
                if "resume_data" in st.session_state and isinstance(st.session_state.resume_data, dict):
                    resume_data = st.session_state.resume_data
                    resume_context = (
                        f"User's resume context: Role='{resume_data.get('job_role', '')}', Skills='{', '.join(resume_data.get('skills', []))}'.")
                    input_data["resume_context"] = resume_context

                backend = st.session_state.get("agent_backend", "Standard (in-memory)")

                if backend == "Persistent (LangGraph)":
                    if "persistent_graph" not in st.session_state:
                        st.session_state.persistent_graph = get_persistent_graph()

                    if "langgraph_thread_id" not in st.session_state:
                        st.session_state.langgraph_thread_id = str(uuid.uuid4())

                    graph = st.session_state.persistent_graph
                    thread_id = st.session_state.langgraph_thread_id

                    graph_state = {
                        "input": prompt,
                        "resume_context": input_data.get("resume_context", ""),
                        "response": "",
                    }

                    final_state = graph.invoke(
                        graph_state,
                        config={"configurable": {"thread_id": thread_id}},
                    )
                    final_response_text = final_state.get("response", "")
                    raw_state = final_state
                    st.markdown(final_response_text)
                else:
                    result = st.session_state.agent_executor.invoke(
                        {"messages": [HumanMessage(content=f"(Resume Context: {input_data.get('resume_context', '')})\n\n{prompt}")]}
                    )
                    raw_state = result

                    if isinstance(result, dict) and "messages" in result:
                        messages = result["messages"]
                        if messages:
                            last_message = messages[-1]
                            if hasattr(last_message, 'content'):
                                content = last_message.content
                                if isinstance(content, list):
                                    text_parts = [block['text'] for block in content if
                                                  isinstance(block, dict) and 'text' in block]
                                    final_response_text = '\n'.join(text_parts)
                                else:
                                    final_response_text = str(content)
                            elif isinstance(last_message, dict) and "content" in last_message:
                                content = last_message["content"]
                                if isinstance(content, list):
                                    text_parts = [block['text'] for block in content if
                                                  isinstance(block, dict) and 'text' in block]
                                    final_response_text = '\n'.join(text_parts)
                                else:
                                    final_response_text = str(content)

                    if final_response_text:
                        st.markdown(final_response_text)
                    else:
                        st.warning("Agent completed but returned no response. Please try again.")

            except Exception as e:
                final_response_text = "Sorry, I ran into a critical error. Please check the logs."
                st.error(final_response_text)
                logging.error("Error during agent execution", exc_info=True)

    # --- THE CLEAN DATA EXTRACTION ---
    summary = final_response_text
    job_data = extract_job_data_from_state(raw_state)
    pending_job = None

    assistant_message = {"role": "assistant", "content": summary}
    if job_data:
        assistant_message['job_data'] = job_data
        assistant_message['timestamp'] = int(time.time())
        SEARCH_ANALYTICS_DATA["successful_searches"] += 1
    else:
        SEARCH_ANALYTICS_DATA["failed_searches"] += 1

    if pending_job:
        st.session_state.pending_save_job = pending_job

    st.session_state.messages.append(assistant_message)
    st.rerun()


# --- MAIN APP LOGIC ---
def main():
    st.title("AI Job Search & Research Agent")
    st.caption("Your intelligent assistant for navigating the job market.")

    with st.sidebar:
        st.subheader("⚙️ Settings")
        backend = st.radio(
            "Agent backend",
            options=["Standard (in-memory)", "Persistent (LangGraph)"],
            key="agent_backend",
        )

    if backend == "Persistent (LangGraph)":
        if "persistent_graph" not in st.session_state:
            st.session_state.persistent_graph = get_persistent_graph()
    else:
        if "agent_executor" not in st.session_state:
            st.session_state.agent_executor = get_agent_executor()

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant",
                                      "content": "Hello! How can I help you today? Upload your resume for personalized results!"}]

    if "pending_save_job" not in st.session_state:
        st.session_state.pending_save_job = None

    handle_resume_upload()
    display_chat_messages()

    prompt = st.chat_input("Ask me to find jobs...")

    if prompt and st.session_state.pending_save_job:
        user_input_lower = prompt.lower().strip()
        affirmative_keywords = ['yes', 'yeah', 'ok', 'okay', 'sure', 'y', 'definitely', 'please']

        if any(user_input_lower.startswith(keyword) for keyword in affirmative_keywords):
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.spinner("Saving to Notion..."):
                    try:
                        from tools.application_tracker_tool import save_jobs_to_notion
                        jobs_json = json.dumps([st.session_state.pending_save_job])
                        result = save_jobs_to_notion(jobs_json)
                        st.success(result)
                        st.markdown(f" {result}")
                        st.session_state.pending_save_job = None
                    except Exception as e:
                        st.error(f"Failed to save to Notion: {e}")
                        st.session_state.pending_save_job = None

            st.rerun()
            return

    if prompt:
        process_user_prompt(prompt)


if __name__ == "__main__":
    main()