import streamlit as st
import logging
import json
import re
import time
import os
import uuid
import assemblyai as aai
import pandas as pd
from langchain_core.messages import HumanMessage
# from streamlit_audiorecorder import audiorecorder
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

    This wraps the same underlying AgentExecutor but adds a SQLite-backed
    checkpoint layer for long-term storage of question/answer pairs.
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
                    # Pass the file content and file name separately to match the parser signature
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
    """Displays checkboxes and a save button for a list of jobs."""
    job_list = message["job_data"]
    with st.form(key=f"form_{message['timestamp']}"):
        selected_jobs = []
        for i, job in enumerate(job_list):
            if st.checkbox(f"{job.get('title', 'N/A')} at {job.get('company', 'N/A')}",
                           key=f"job_{message['timestamp']}_{i}"):
                selected_jobs.append(job)

        submitted = st.form_submit_button("Save Selected Jobs to Notion")
        if submitted:
            if selected_jobs:
                with st.spinner("Saving to Notion..."):
                    from tools.application_tracker_tool import save_jobs_to_notion
                    jobs_json_str = json.dumps(selected_jobs)
                    result = save_jobs_to_notion(jobs_json_str)
                    st.success(result)
            else:
                st.warning("Please select at least one job to save.")

    # --- Skill Gap Analysis ---
    st.markdown("---")
    st.markdown("##### 🚀 AI Career Coach")

    # Create a select box for the user to choose a job to analyze
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

                # Display the result in an expander
                with st.expander(f"Skill Gap Analysis for: **{selected_job_title}**", expanded=True):
                    st.markdown(analysis_result)

    # --- Data Export ---
    st.markdown("---")
    st.markdown("##### 📥 Export Job Listings")

    # Convert job list to DataFrame for easy export
    df = pd.DataFrame(job_list)

    # Prepare data for download buttons
    csv_data = df.to_csv(index=False).encode('utf-8')
    json_data = df.to_json(orient='records', indent=2).encode('utf-8')

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download as CSV",
            data=csv_data,
            file_name=f"job_listings_{message['timestamp']}.csv",
            mime="text/csv",
        )
    with col2:
        st.download_button(
            label="Download as JSON",
            data=json_data,
            file_name=f"job_listings_{message['timestamp']}.json",
            mime="application/json",
        )


def process_user_prompt(prompt):
    """Processes the user's input, runs the agent, and handles the response."""
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Update analytics
    SEARCH_ANALYTICS_DATA["total_searches"] += 1

    with st.chat_message("assistant"):
        final_response_text = ""
        with st.spinner("🤖 The agent is thinking..."):
            try:
                input_data = {"input": prompt, "resume_context": ""}
                if "resume_data" in st.session_state and isinstance(st.session_state.resume_data, dict):
                    resume_data = st.session_state.resume_data
                    resume_context = (
                        f"User's resume context: Role='{resume_data.get('job_role', '')}', Skills='{', '.join(resume_data.get('skills', []))}'.")
                    input_data["resume_context"] = resume_context

                # Decide which backend to use
                backend = st.session_state.get("agent_backend", "Standard (in-memory)")

                if backend == "Persistent (LangGraph)":
                    # For the persistent backend, we call the LangGraph graph in non-streaming
                    # mode to ensure the interaction is checkpointed to SQLite, and then
                    # display the final response.
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
                    st.markdown(final_response_text)
                else:
                    # Default: use the standard agent (invoke mode for cleaner response handling)
                    result = st.session_state.agent_executor.invoke(
                        {"messages": [HumanMessage(content=prompt)]}
                    )
                    
                    # Extract the final response from the agent result
                    final_response_text = ""
                    
                    if isinstance(result, dict) and "messages" in result:
                        # Get the last message from the result
                        messages = result["messages"]
                        if messages:
                            last_message = messages[-1]
                            
                            # Handle different content formats
                            if hasattr(last_message, 'content'):
                                content = last_message.content
                                # If content is a list (Gemini format), extract text from each block
                                if isinstance(content, list):
                                    text_parts = []
                                    for block in content:
                                        if isinstance(block, dict) and 'text' in block:
                                            text_parts.append(block['text'])
                                        elif isinstance(block, str):
                                            text_parts.append(block)
                                    final_response_text = '\n'.join(text_parts)
                                else:
                                    # Simple string content
                                    final_response_text = str(content)
                            elif isinstance(last_message, dict) and "content" in last_message:
                                content = last_message["content"]
                                if isinstance(content, list):
                                    text_parts = []
                                    for block in content:
                                        if isinstance(block, dict) and 'text' in block:
                                            text_parts.append(block['text'])
                                        elif isinstance(block, str):
                                            text_parts.append(block)
                                    final_response_text = '\n'.join(text_parts)
                                else:
                                    final_response_text = str(content)
                    
                    # Display the response
                    if final_response_text:
                        st.markdown(final_response_text)
                    else:
                        st.warning("Agent completed but returned no response. Please try again.")

            except Exception as e:
                final_response_text = "Sorry, I ran into a critical error. Please check the logs."
                st.error(final_response_text)
                logging.error("Error during agent execution", exc_info=True)

    summary, job_data = extract_and_format_response(final_response_text)
    assistant_message = {"role": "assistant", "content": summary}
    if job_data:
        assistant_message['job_data'] = job_data
        assistant_message['timestamp'] = int(time.time())
        SEARCH_ANALYTICS_DATA["successful_searches"] += 1
    else:
        SEARCH_ANALYTICS_DATA["failed_searches"] += 1

    st.session_state.messages.append(assistant_message)
    st.rerun()


def extract_and_format_response(response_text: str):
    """Extracts job data from the agent's markdown response and creates a clean summary."""
    summary = response_text
    job_list = None
    pattern = r"-\s*\*\*(.*?)\*\* at (.*?)\s*-\s*\[Apply Here\]\((.*?)\)"
    matches = re.findall(pattern, summary)
    if matches:
        job_list = [{"title": t, "company": c, "url": u} for t, c, u in matches]
    return summary, job_list





@st.cache_data
def transcribe_voice_command(audio_bytes):
    """Transcribes audio bytes to text using AssemblyAI."""
    try:
        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        if not aai.settings.api_key:
            st.error("AssemblyAI API key not set.")
            return None
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_bytes)
        if transcript and hasattr(transcript, 'status') and hasattr(aai, 'TranscriptStatus'):
            return transcript.text if transcript.status == aai.TranscriptStatus.COMPLETED else None
        elif transcript and hasattr(transcript, 'text'):
            return transcript.text
        return None
    except Exception as e:
        st.error(f"Transcription error: {e}")
        return None


# --- MAIN APP LOGIC ---
def main():
    """The main function that runs the Streamlit application."""
    st.title("AI Job Search & Research Agent")
    st.caption("Your intelligent assistant for navigating the job market.")

    # Let the user choose between in-memory and persistent backends.
    with st.sidebar:
        st.subheader("⚙️ Settings")
        backend = st.radio(
            "Agent backend",
            options=["Standard (in-memory)", "Persistent (LangGraph)"],
            key="agent_backend",
        )

    # Initialize backend-specific resources.
    if backend == "Persistent (LangGraph)":
        if "persistent_graph" not in st.session_state:
            st.session_state.persistent_graph = get_persistent_graph()
    else:
        if "agent_executor" not in st.session_state:
            st.session_state.agent_executor = get_agent_executor()
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant",
                                      "content": "Hello! How can I help you today? Upload your resume for personalized results!"}]

    handle_resume_upload()

    display_chat_messages()

    # audio_bytes = audiorecorder("Start recording", "Stop recording")

    prompt = st.chat_input("Ask me to find jobs...")

    # if audio_bytes and not prompt:
    #     with st.spinner("Transcribing your command..."):
    #         prompt = transcribe_voice_command(audio_bytes)

    if prompt:
        process_user_prompt(prompt)


if __name__ == "__main__":
    main()