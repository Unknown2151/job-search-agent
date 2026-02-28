"""
Unit tests for search tools with network error handling.
Tests resilience to network failures and malformed responses.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import aiohttp
import asyncio


class TestLinkedInSearchTool:
    """Test suite for LinkedIn job search."""

    @pytest.mark.asyncio
    async def test_linkedin_success(self):
        """Test successful LinkedIn job search."""
        from tools.linkedin_search_tool import search_linkedin_jobs

        mock_html = """
        <div class="base-card">
            <h3 class="base-search-card__title">Software Engineer</h3>
            <h4 class="base-search-card__subtitle">TechCorp</h4>
            <a class="base-card__full-link" href="https://example.com/job1"></a>
            <span class="job-search-card__location">Chennai</span>
        </div>
        """

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_html)
            mock_response.__aenter__.return_value = mock_response

            mock_get.return_value.__aenter__.return_value = mock_response

            result = await search_linkedin_jobs("Software Engineer, Chennai")

            assert isinstance(result, (list, str))

    @pytest.mark.asyncio
    async def test_linkedin_403_blocked(self):
        """Test LinkedIn 403 blocking detection."""
        from tools.linkedin_search_tool import search_linkedin_jobs

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 403
            mock_response.__aenter__.return_value = mock_response

            mock_get.return_value.__aenter__.return_value = mock_response

            result = await search_linkedin_jobs("Software Engineer, Chennai")

            assert isinstance(result, str)
            assert "blocked" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_linkedin_network_error(self):
        """Test LinkedIn network error handling."""
        from tools.linkedin_search_tool import search_linkedin_jobs

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Network error")

            result = await search_linkedin_jobs("Software Engineer, Chennai")

            assert isinstance(result, str)
            assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_linkedin_invalid_input_format(self):
        """Test LinkedIn with invalid input format."""
        from tools.linkedin_search_tool import search_linkedin_jobs

        result = await search_linkedin_jobs("InvalidFormatWithoutComma")

        assert isinstance(result, str)
        assert "error" in result.lower() or "input" in result.lower()


class TestNaukriSearchTool:
    """Test suite for Naukri job search."""

    @patch('tools.naukri_search_tool._create_webdriver')
    def test_naukri_success(self, mock_driver_factory):
        """Test successful Naukri job search."""
        from tools.naukri_search_tool import search_naukri_jobs

        mock_driver = MagicMock()
        mock_driver.page_source = """
        <div class="srp-jobtuple-wrapper">
            <a class="title" href="https://example.com/job1">Python Developer</a>
            <a class="comp-name">TechCorp</a>
        </div>
        """
        mock_driver_factory.return_value = mock_driver

        result = search_naukri_jobs("Python Developer, Bangalore")

        assert isinstance(result, (list, str))
        mock_driver.quit.assert_called_once()

    @patch('tools.naukri_search_tool._create_webdriver')
    def test_naukri_no_jobs_found(self, mock_driver_factory):
        """Test Naukri with no jobs found."""
        from tools.naukri_search_tool import search_naukri_jobs

        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>No jobs</body></html>"
        mock_driver_factory.return_value = mock_driver

        result = search_naukri_jobs("UnicornRole, UnknownCity")

        assert isinstance(result, str)
        assert "no jobs" in result.lower()
        mock_driver.quit.assert_called_once()

    @patch('tools.naukri_search_tool._create_webdriver')
    def test_naukri_driver_cleanup(self, mock_driver_factory):
        """Test that WebDriver is properly closed even on error."""
        from tools.naukri_search_tool import search_naukri_jobs

        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("Connection error")
        mock_driver_factory.return_value = mock_driver

        result = search_naukri_jobs("Python Developer, Bangalore")

        assert isinstance(result, str)
        mock_driver.quit.assert_called_once()

    def test_naukri_invalid_input_format(self):
        """Test Naukri with invalid input format."""
        from tools.naukri_search_tool import search_naukri_jobs

        result = search_naukri_jobs("InvalidFormatWithoutComma")

        assert isinstance(result, str)
        assert "error" in result.lower() or "input" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
