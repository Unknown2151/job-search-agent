"""
Unit tests for job_agent with AsyncIO and concurrent execution tests.
Tests parallel job search across LinkedIn, Naukri, and Indeed.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from agents.job_agent import parallel_job_search, _parallel_job_search


class TestParallelJobSearch:
    """Test suite for parallel job search functionality."""

    @patch('agents.job_agent.search_indeed_jobs')
    @patch('agents.job_agent.search_linkedin_jobs')
    @patch('agents.job_agent.search_naukri_jobs')
    def test_parallel_search_all_succeed(self, mock_naukri, mock_linkedin, mock_indeed):
        """Test successful parallel search from all three platforms."""
        mock_linkedin.return_value = [
            {"title": "Engineer", "company": "TechCorp", "url": "url1"}
        ]
        mock_naukri.return_value = [
            {"title": "Developer", "company": "DevCorp", "url": "url2"}
        ]
        mock_indeed.return_value = [
            {"title": "Analyst", "company": "DataCorp", "url": "url3"}
        ]

        result = parallel_job_search("Python Engineer, Chennai")

        assert result["linkedin"] is not None
        assert result["naukri"] is not None
        assert result["indeed"] is not None
        assert isinstance(result["linkedin"], list)
        assert isinstance(result["naukri"], list)
        assert isinstance(result["indeed"], list)

    @patch('agents.job_agent.search_indeed_jobs')
    @patch('agents.job_agent.search_linkedin_jobs')
    @patch('agents.job_agent.search_naukri_jobs')
    def test_parallel_search_partial_failure(self, mock_naukri, mock_linkedin, mock_indeed):
        """Test handling when one platform fails."""
        mock_linkedin.side_effect = Exception("Network error")
        mock_naukri.return_value = [
            {"title": "Developer", "company": "DevCorp", "url": "url"}
        ]
        mock_indeed.return_value = [
            {"title": "Analyst", "company": "DataCorp", "url": "url3"}
        ]

        result = parallel_job_search("Python Engineer, Chennai")

        assert isinstance(result["naukri"], list)
        assert isinstance(result["indeed"], list)
        # Failed platform should have error message or exception
        assert isinstance(result["linkedin"], Exception) or isinstance(result["linkedin"], str)

    @patch('agents.job_agent.search_indeed_jobs')
    @patch('agents.job_agent.search_linkedin_jobs')
    @patch('agents.job_agent.search_naukri_jobs')
    def test_parallel_search_all_fail(self, mock_naukri, mock_linkedin, mock_indeed):
        """Test error handling when all platforms fail."""
        mock_linkedin.side_effect = Exception("LinkedIn error")
        mock_naukri.side_effect = Exception("Naukri error")
        mock_indeed.side_effect = Exception("Indeed error")

        result = parallel_job_search("Python Engineer, Chennai")

        assert "error" in str(result["linkedin"]).lower() or isinstance(result["linkedin"], Exception)
        assert "error" in str(result["naukri"]).lower() or isinstance(result["naukri"], Exception)
        assert "error" in str(result["indeed"]).lower() or isinstance(result["indeed"], Exception)

    def test_parallel_search_no_event_loop(self):
        """Test parallel search works without existing event loop."""
        with patch('agents.job_agent.search_linkedin_jobs') as mock_linkedin, \
             patch('agents.job_agent.search_naukri_jobs') as mock_naukri, \
             patch('agents.job_agent.search_indeed_jobs') as mock_indeed:

            mock_linkedin.return_value = []
            mock_naukri.return_value = []
            mock_indeed.return_value = []

            try:
                result = parallel_job_search("Python Engineer, Chennai")
                assert result is not None
            except RuntimeError as e:
                if "There is no current event loop" in str(e):
                    pytest.fail("Should handle missing event loop gracefully")

    def test_parallel_search_with_empty_results(self):
        """Test handling of empty results from all platforms."""
        with patch('agents.job_agent.search_linkedin_jobs') as mock_linkedin, \
             patch('agents.job_agent.search_naukri_jobs') as mock_naukri, \
             patch('agents.job_agent.search_indeed_jobs') as mock_indeed:

            mock_linkedin.return_value = []
            mock_naukri.return_value = "No Jobs found for this query."
            mock_indeed.return_value = []

            result = parallel_job_search("NonexistentRole, NonexistentLocation")

            assert result["linkedin"] == [] or isinstance(result["linkedin"], str)
            assert isinstance(result["naukri"], str) or result["naukri"] == []
            assert result["indeed"] == [] or isinstance(result["indeed"], str)


class TestAsyncJobSearch:
    """Test suite for async job search functionality."""

    @pytest.mark.asyncio
    async def test_parallel_job_search_async(self):
        """Test the async _parallel_job_search function."""
        with patch('agents.job_agent.search_linkedin_jobs') as mock_linkedin, \
             patch('agents.job_agent.search_naukri_jobs') as mock_naukri, \
             patch('agents.job_agent.search_indeed_jobs') as mock_indeed:

            mock_linkedin.return_value = [{"title": "Engineer", "company": "Tech", "url": "url"}]
            mock_naukri.return_value = [{"title": "Dev", "company": "Dev", "url": "url"}]
            mock_indeed.return_value = [{"title": "Analyst", "company": "Data", "url": "url"}]

            result = await _parallel_job_search("Python Engineer, Chennai")

            assert "linkedin" in result
            assert "naukri" in result
            assert "indeed" in result

    @pytest.mark.asyncio
    async def test_async_search_timeout_handling(self):
        """Test timeout handling in async context."""
        async def slow_operation():
            await asyncio.sleep(10)
            return []

        with patch('agents.job_agent.search_linkedin_jobs', side_effect=slow_operation), \
             patch('agents.job_agent.search_naukri_jobs') as mock_naukri, \
             patch('agents.job_agent.search_indeed_jobs') as mock_indeed:

            mock_naukri.return_value = []
            mock_indeed.return_value = []

            try:
                result = await asyncio.wait_for(
                    _parallel_job_search("role, location"),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
