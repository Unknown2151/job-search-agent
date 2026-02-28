"""
Pytest configuration and fixtures.
"""
import pytest
import asyncio
import sys


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env_setup(monkeypatch):
    """Setup mock environment variables."""
    monkeypatch.setenv("NOTION_API_TOKEN", "test_token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "test-db-id")
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("SERPAPI_API_KEY", "test_key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key")


@pytest.fixture
def sample_jobs():
    """Sample job data for testing."""
    return [
        {
            "title": "Python Engineer",
            "company": "TechCorp",
            "url": "https://example.com/jobs/1",
            "location": "Chennai"
        },
        {
            "title": "Data Scientist",
            "company": "DataCo",
            "url": "https://example.com/jobs/2",
            "location": "Bangalore"
        }
    ]


@pytest.fixture
def sample_resume():
    """Sample resume text for testing."""
    return """
    SENIOR SOFTWARE ENGINEER

    SUMMARY
    Experienced software engineer with 8+ years in backend development.

    EXPERIENCE
    2024-Present: TechCorp - Senior Engineer
    2021-2024: DataCorp - Software Engineer
    2019-2021: StartupXYZ - Junior Developer

    SKILLS
    Python, Java, Go, AWS, Docker, Kubernetes, PostgreSQL, Redis
    """
