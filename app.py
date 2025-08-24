import streamlit as st
import logging
from agents.job_agent import create_job_agent

# --- LOGGING CONFIGURATION ---
# This should be the first line of your app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Job Search Agent",
    page_icon="🤖",
    layout="centered"
)

# --- APP TITLE ---
st.title("AI Job Search & Research Agent")
st.caption("Your intelligent assistant for navigating the job market.")

# --- AGENT INITIALIZATION ---
if 'agent_executor' not in st.session_state:
    with st.spinner("Initializing agent..."):
        st.session_state.agent_executor = create_job_agent()

# --- CHAT HISTORY ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you with your job search today?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- USER INPUT ---
if prompt := st.chat_input("Ask me to find jobs, internships, or research a company..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = ""
        response_placeholder = st.empty()

        with st.spinner("🤖 The agent is thinking..."):
            try:
                stream = st.session_state.agent_executor.stream(
                    {"input": prompt}
                )
                for chunk in stream:
                    if 'output' in chunk:
                        response = chunk['output']

            except Exception as e:
                response = "Sorry, I ran into a critical error. Please check the logs."
                st.error(response)
                logging.error("Error during agent execution", exc_info=True)

        response_placeholder.markdown(response, unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": response})