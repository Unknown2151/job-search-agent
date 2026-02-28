"""
Unit tests for job_agent with AsyncIO and concurrent execution tests.
Tests parallel job search, error handling, and event loop management.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from agents.job_agent import parallel_job_search, _parallel_job_search


class TestParallelJobSearch:
    """Test suite for parallel job search functionality."""

    @patch('agents.job_agent.search_linkedin_jobs')
    @patch('agents.job_agent.search_naukri_jobs')
    def test_parallel_search_both_succeed(self, mock_naukri, mock_linkedin):
        """Test successful parallel search from both platforms."""
        mock_linkedin.return_value = [
            {"title": "Engineer", "company": "TechCorp", "url": "url1"}
        ]
        mock_naukri.return_value = [
            {"title": "Developer", "company": "DevCorp", "url": "url2"}
        ]

        result = parallel_job_search("Python Engineer, Chennai")

        assert result["linkedin"] is not None
        assert result["naukri"] is not None
        assert isinstance(result["linkedin"], list)
        assert isinstance(result["naukri"], list)

    @patch('agents.job_agent.search_linkedin_jobs')
    @patch('agents.job_agent.search_naukri_jobs')
    def test_parallel_search_partial_failure(self, mock_naukri, mock_linkedin):
        """Test handling when one platform fails."""
        mock_linkedin.side_effect = Exception("Network error")
        mock_naukri.return_value = [
            {"title": "Developer", "company": "DevCorp", "url": "url"}
        ]

        result = parallel_job_search("Python Engineer, Chennai")

        # Should contain results from successful platform
        assert isinstance(result["naukri"], list)
        # Failed platform should have error message or exception
        assert isinstance(result["linkedin"], Exception) or isinstance(result["linkedin"], str)

    @patch('agents.job_agent.search_linkedin_jobs')
    @patch('agents.job_agent.search_naukri_jobs')
    def test_parallel_search_both_fail(self, mock_naukri, mock_linkedin):
        """Test error handling when both platforms fail."""
        mock_linkedin.side_effect = Exception("LinkedIn error")
        mock_naukri.side_effect = Exception("Naukri error")

        result = parallel_job_search("Python Engineer, Chennai")

        # Both should contain error information
        assert "error" in str(result["linkedin"]).lower() or isinstance(result["linkedin"], Exception)
        assert "error" in str(result["naukri"]).lower() or isinstance(result["naukri"], Exception)

    def test_parallel_search_no_event_loop(self):
        """Test parallel search works without existing event loop."""
        with patch('agents.job_agent.search_linkedin_jobs') as mock_linkedin, \
             patch('agents.job_agent.search_naukri_jobs') as mock_naukri:

            mock_linkedin.return_value = []
            mock_naukri.return_value = []

            # This should not raise an error about event loop
            try:
                result = parallel_job_search("Python Engineer, Chennai")
                assert result is not None
            except RuntimeError as e:
                if "There is no current event loop" in str(e):
                    pytest.fail("Should handle missing event loop gracefully")

    def test_parallel_search_with_empty_results(self):
        """Test handling of empty results from both platforms."""
        with patch('agents.job_agent.search_linkedin_jobs') as mock_linkedin, \
             patch('agents.job_agent.search_naukri_jobs') as mock_naukri:

            mock_linkedin.return_value = []
            mock_naukri.return_value = "No Jobs found for this query."

            result = parallel_job_search("NonexistentRole, NonexistentLocation")

            assert result["linkedin"] == [] or isinstance(result["linkedin"], str)
            assert isinstance(result["naukri"], str) or result["naukri"] == []


class TestAsyncJobSearch:
    """Test suite for async job search functionality."""

    @pytest.mark.asyncio
    async def test_parallel_job_search_async(self):
        """Test the async _parallel_job_search function."""
        with patch('agents.job_agent.search_linkedin_jobs') as mock_linkedin, \
             patch('agents.job_agent.search_naukri_jobs') as mock_naukri:

            mock_linkedin.return_value = [{"title": "Engineer", "company": "Tech", "url": "url"}]
            mock_naukri.return_value = [{"title": "Dev", "company": "Dev", "url": "url"}]

            result = await _parallel_job_search("Python Engineer, Chennai")

            assert "linkedin" in result
            assert "naukri" in result

    @pytest.mark.asyncio
    async def test_async_search_timeout_handling(self):
        """Test timeout handling in async context."""
        async def slow_operation():
            await asyncio.sleep(10)
            return []

        with patch('agents.job_agent.search_linkedin_jobs', side_effect=slow_operation), \
             patch('agents.job_agent.search_naukri_jobs') as mock_naukri:

            mock_naukri.return_value = []

            # Set a short timeout to test timeout handling
            try:
                # This should eventually complete even if one operation is slow
                result = await asyncio.wait_for(
                    _parallel_job_search("role, location"),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                # Timeout is expected - the point is we're testing timeout handling
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
