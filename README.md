# AI Job Search & Research Agent

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.48-red.svg)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Stateful_Agents-orange.svg)](https://langchain.com/)
[![Deployed on Railway](https://img.shields.io/badge/Deployed-Railway-purple.svg)](https://railway.app/)

A full-stack, asynchronous multi-agent system designed to automate the job search pipeline. It features concurrent web scraping, persistent conversational memory, AI-driven skill gap analysis, and real-time CRM syncing.

---

## ️ Architecture & Engineering Highlights

This project was built to demonstrate scalable backend engineering patterns, API orchestration, and stateful LLM interactions.

### Concurrent I/O Processing

- Utilizes `asyncio.gather` and custom worker threads to simultaneously query multiple job boards.
- Implemented asynchronous request jittering to reduce API rate-limit collisions.
- Reduced overall search latency through parallelized network operations.

### Stateful Agentic Memory

- Built on **LangGraph** state machines.
- Uses persistent checkpointing and message reducers.
- Maintains conversational context across multiple interactions and resume uploads.

### Deterministic Data Extraction

- Reads structured JSON tool outputs directly from workflow state.
- Eliminates brittle markdown parsing.
- Ensures reliable UI rendering and data consistency.

### Asynchronous CRM Integration

- Batch exports selected job opportunities to Notion.
- Uses asynchronous HTTP requests for efficient bulk operations.
- Prevents UI blocking during synchronization.

### Dependency Injection

- Centralized LLM initialization through an `llm_factory`.
- Simplifies model swapping and configuration management.
- Easily extensible to additional providers.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---------|------------|
| Frontend | Streamlit |
| Agent Framework | LangChain Core, LangGraph |
| LLM | Google Gemini |
| APIs | RapidAPI (JSearch), Notion API, SerpAPI, AssemblyAI |
| Concurrency | asyncio, aiohttp |
| Testing | Pytest |
| Infrastructure | Docker, Railway |
| Language | Python 3.11+ |

---

## Local Development & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Unknown2151job-search-agent.git
cd job-search-agent
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
make install
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_gemini_key
RAPIDAPI_KEY=your_rapidapi_key
NOTION_API_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id
SERPAPI_API_KEY=your_serpapi_key
```

### 5. Run the Application

```bash
make run
```

---

## Testing & Diagnostics

### Run Fast Test Suite

```bash
make test-fast
```

### Run Coverage Report

```bash
make test-cov
```

### Run Diagnostics

```bash
python diagnose.py
```

---

## Docker Deployment

### Build Docker Image

```bash
make docker-build
```

### Run Docker Container

```bash
make docker-run
```

---

## Key Features

- Multi-agent job search workflows
- Resume-aware recommendations
- Skill-gap analysis
- Persistent conversational memory
- Async job aggregation
- Notion CRM synchronization
- Streamlit dashboard
- Dockerized deployment

---
