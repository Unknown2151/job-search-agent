import pandas as pd
import plotly.express as px
import streamlit as st
import logging
import json
import re
import time
from agents.job_agent import create_job_agent, SEARCH_ANALYTICS_DATA

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
st.set_page_config(page_title="AI Job Search Agent", page_icon="🤖", layout="centered")


# --- AGENT INITIALIZATION ---
@st.cache_resource
def get_agent_executor():
    """Initializes and returns the agent executor, cached for the session."""
    return create_job_agent()


# --- UI HELPER FUNCTIONS ---
def handle_resume_upload():
    """Handles the resume upload and analysis in the sidebar."""
    with st.sidebar:
        st.header("📄 Your Resume")
        uploaded_file = st.file_uploader("Upload your resume to personalize your search.", type=["pdf", "docx"])

        if uploaded_file:
            if st.session_state.get("resume_filename") != uploaded_file.name:
                with st.spinner("Analyzing your resume..."):
                    file_bytes = uploaded_file.getvalue()
                    st.session_state.resume_filename = uploaded_file.name
                    from tools.resume_parser_tool import parse_resume
                    st.session_state.resume_data = parse_resume(file_bytes, uploaded_file.name)

            if isinstance(st.session_state.get("resume_data"), dict):
                st.success("Resume analyzed!")
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
            if st.checkbox(f"{job.get('title', 'N/A')} at {job.get('company', 'N/A')}", key=f"job_{message['timestamp']}_{i}"):
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


# --- RESPONSE EXTRACTION ---
def extract_and_format_response(response_text: str):
    """
    Extracts job data from the agent's response and creates a clean summary.
    Works with both markdown job lists and JSON.
    """
    job_list = None
    summary = response_text

    # Regex to detect markdown job listings
    pattern = r"-\s*\*\*(.*?)\*\* at (.*?)\s*-\s*\[Apply Here\]\((.*?)\)"
    matches = re.findall(pattern, summary)

    if matches:
        job_list = [{"title": t, "company": c, "url": u} for t, c, u in matches]
        return summary, job_list

    # Fallback: try JSON parsing
    try:
        data = json.loads(summary)
        if isinstance(data, list):
            job_list = data
            summary = "\n".join(
                [f"- **{job['title']}** at {job['company']} - [Apply Here]({job['url']})" for job in data]
            )
    except Exception:
        pass

    return summary, job_list


# --- PROCESS USER PROMPT ---
def process_user_prompt(prompt):
    """Processes the user's input, runs the agent, and handles the response."""

    SEARCH_ANALYTICS_DATA["total_searches"] += 1

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        final_response_text = ""
        with st.spinner("🤖 The agent is thinking..."):
            try:
                # Prepare input for agent
                input_data = {"input": prompt, "resume_context": ""}

                if "resume_data" in st.session_state and isinstance(st.session_state.resume_data, dict):
                    resume_data = st.session_state.resume_data
                    resume_context = (
                        f"The user has uploaded their resume. Use this information to guide your searches. "
                        f"Their probable job role is '{resume_data.get('job_role', '')}' "
                        f"and their skills include '{', '.join(resume_data.get('skills', []))}'."
                    )
                    input_data["resume_context"] = resume_context

                # Stream the agent's response properly
                stream = st.session_state.agent_executor.stream(input_data)

                for chunk in stream:
                    # Handle job listings (structured dicts)
                    if isinstance(chunk, dict) and "jobs" in chunk:
                        for job in chunk["jobs"]:
                            line = f"- **{job['title']}** at {job['company']} - [Apply Here]({job['url']})"
                            final_response_text += line + "\n"
                            st.markdown(line)

                    # Handle final assistant text output
                    elif isinstance(chunk, dict) and "output" in chunk:
                        text = str(chunk["output"])
                        final_response_text += text + "\n"
                        st.markdown(text)

                    # Handle plain string responses (fallback)
                    elif isinstance(chunk, str):
                        final_response_text += chunk + "\n"
                        st.markdown(chunk)

                # Save assistant message
                st.session_state.messages.append({"role": "assistant", "content": final_response_text})

            except Exception as e:
                final_response_text = "Sorry, I ran into a critical error. Please check the logs."
                st.error(final_response_text)
                logging.error("Error during agent execution", exc_info=True)

    # Extract jobs and store in messages
    summary, job_data = extract_and_format_response(final_response_text)
    assistant_message = {"role": "assistant", "content": summary}
    if job_data:
        assistant_message["job_data"] = job_data
        assistant_message["timestamp"] = int(time.time())

    st.session_state.messages.append(assistant_message)
    st.rerun()


def analytics_dashboard():
    st.header("📊 Analytics Dashboard")
    st.markdown("Insights into your job search activity.")

    analytics_data = SEARCH_ANALYTICS_DATA

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Searches", analytics_data["total_searches"])
    col2.metric("Successful Searches", analytics_data["successful_searches"])
    col3.metric("Failed Searches", analytics_data["failed_searches"])

    st.divider()

    platform_data = analytics_data["platform_usage"]
    if sum(platform_data.values()) > 0:
        df = pd.DataFrame(list(platform_data.items()), columns=['Platform', 'Searches'])

        fig = px.pie(df, names='Platform', values='Searches', title='Job Searches by Platform',
                     color_discrete_sequence=px.colors.sequential.RdBu)
        fig.update_layout(legend_title_text='Platforms')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No platform search data yet. Ask the agent to find some jobs!")


# --- MAIN APP LOGIC ---
def main():
    """The main function that runs the Streamlit application."""
    st.title("🤖 AI Job Search & Research Agent")
    st.caption("Your intelligent assistant for navigating the job market.")

    st.session_state.agent_executor = get_agent_executor()
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! How can I help you today? Upload your resume in the sidebar for personalized results!",
            }
        ]

    handle_resume_upload()

    tab1, tab2 = st.tabs(["💬 Chat Agent", "📊 Analytics"])

    with tab1:
        st.header("Chat with your AI Job Agent")
        display_chat_messages()
        if prompt := st.chat_input("Ask me to find jobs..."):
            process_user_prompt(prompt)

    with tab2:
        analytics_dashboard()


if __name__ == "__main__":
    main()
