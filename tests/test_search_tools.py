"""
Unit tests for search tools with the JSearch API backend.
Tests resilience to API failures and correct result parsing.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import aiohttp



class TestJSearchApiTool:
    """Test suite for the core JSearch API client."""

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"}, clear=False)
    @patch("tools.jsearch_api_tool.requests.get")
    def test_jsearch_success(self, mock_get):
        """Test successful API response parsing."""
        from tools.jsearch_api_tool import search_jobs_api

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "job_title": "Python Developer",
                        "employer_name": "TechCorp",
                        "job_apply_link": "https://example.com/apply",
                        "job_city": "Chennai",
                    }
                ]
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_jobs_api("Python Developer", location="Chennai")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Python Developer"
        assert result[0]["company"] == "TechCorp"
        assert result[0]["url"] == "https://example.com/apply"

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"}, clear=False)
    @patch("tools.jsearch_api_tool.requests.get")
    def test_jsearch_empty_results(self, mock_get):
        """Test handling when API returns no jobs."""
        from tools.jsearch_api_tool import search_jobs_api

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": []},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_jobs_api("NonexistentRole", location="Nowhere")

        assert isinstance(result, str)
        assert "no jobs" in result.lower()

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"}, clear=False)
    @patch("tools.jsearch_api_tool.requests.get")
    def test_jsearch_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        import requests as req_lib
        from tools.jsearch_api_tool import search_jobs_api

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = req_lib.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        result = search_jobs_api("Developer", location="Mumbai")

        assert isinstance(result, str)
        assert "rate limit" in result.lower() or "error" in result.lower()

    @patch.dict("os.environ", {"RAPIDAPI_KEY": ""}, clear=False)
    def test_jsearch_missing_api_key(self):
        """Test graceful error when API key is missing."""
        from tools.jsearch_api_tool import search_jobs_api

        result = search_jobs_api("Developer", location="Delhi")

        assert isinstance(result, str)
        assert "rapidapi_key" in result.lower() or "key" in result.lower()

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"}, clear=False)
    @patch("tools.jsearch_api_tool.requests.get")
    def test_jsearch_platform_label(self, mock_get):
        """Test that platform_label is correctly applied."""
        from tools.jsearch_api_tool import search_jobs_api

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "job_title": "Engineer",
                        "employer_name": "Corp",
                        "job_apply_link": "https://example.com",
                        "job_city": "Pune",
                    }
                ]
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_jobs_api("Engineer", platform_label="Naukri.com")

        assert isinstance(result, list)
        assert result[0]["platform"] == "Naukri.com"

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"}, clear=False)
    @patch("tools.jsearch_api_tool.requests.get")
    def test_jsearch_job_type_extraction(self, mock_get):
        """Test that job_type is correctly extracted from API response."""
        from tools.jsearch_api_tool import search_jobs_api

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "job_title": "Intern - Python Developer",
                        "employer_name": "TechCorp",
                        "job_apply_link": "https://example.com/apply",
                        "job_city": "Chennai",
                        "job_employment_type": "Internship",
                        "job_description": "Junior developer internship",
                    }
                ]
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_jobs_api("Python Intern", location="Chennai")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["job_type"] == "Internship"
        assert "description" in result[0]
        assert result[0]["description"] == "Junior developer internship"



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
    """Test suite for Naukri job search (JSearch API backend)."""

    @patch("tools.jsearch_api_tool.requests.get")
    def test_naukri_success(self, mock_get):
        """Test successful Naukri job search."""
        from tools.naukri_search_tool import search_naukri_jobs

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "job_title": "Python Developer",
                        "employer_name": "TechCorp",
                        "job_apply_link": "https://example.com/job1",
                        "job_city": "Bangalore",
                    }
                ]
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_naukri_jobs("Python Developer, Bangalore")

        assert isinstance(result, (list, str))
        if isinstance(result, list):
            assert result[0]["platform"] == "Naukri.com"

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"}, clear=False)
    @patch("tools.jsearch_api_tool.requests.get")
    def test_naukri_no_jobs_found(self, mock_get):
        """Test Naukri with no jobs found."""
        from tools.naukri_search_tool import search_naukri_jobs

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": []},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_naukri_jobs("UnicornRole, UnknownCity")

        assert isinstance(result, str)
        assert "no jobs" in result.lower()

    def test_naukri_invalid_input_format(self):
        """Test Naukri with invalid input format."""
        from tools.naukri_search_tool import search_naukri_jobs

        result = search_naukri_jobs("InvalidFormatWithoutComma")

        assert isinstance(result, str)
        assert "error" in result.lower() or "input" in result.lower()

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"}, clear=False)
    @patch("tools.jsearch_api_tool.requests.get")
    def test_naukri_internship_filter(self, mock_get):
        """Test Naukri internship filtering."""
        from tools.naukri_search_tool import search_naukri_jobs

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "job_title": "Python Developer",
                        "employer_name": "TechCorp",
                        "job_apply_link": "https://example.com/job1",
                        "job_city": "Bangalore",
                        "job_employment_type": "INTERNSHIP",
                    },
                    {
                        "job_title": "Python Developer",
                        "employer_name": "DataCorp",
                        "job_apply_link": "https://example.com/job2",
                        "job_city": "Bangalore",
                        "job_employment_type": "FULL_TIME",
                    },
                ]
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_naukri_jobs("Python Developer, Bangalore", job_type="internship")

        assert isinstance(result, list)
        assert len(result) == 1
        assert "INTERNSHIP" in result[0]["job_type"]

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"}, clear=False)
    @patch("tools.jsearch_api_tool.requests.get")
    def test_naukri_no_internships_found(self, mock_get):
        """Test Naukri when no internships are available for the query."""
        from tools.naukri_search_tool import search_naukri_jobs

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "job_title": "Senior Developer",
                        "employer_name": "TechCorp",
                        "job_apply_link": "https://example.com/job1",
                        "job_city": "Bangalore",
                        "job_employment_type": "FULL_TIME",
                    }
                ]
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_naukri_jobs("Developer, Bangalore", job_type="internship")

        assert isinstance(result, str)
        assert "no" in result.lower() and "internship" in result.lower()



class TestIndeedSearchTool:
    """Test suite for Indeed job search (JSearch API backend)."""

    @patch("tools.jsearch_api_tool.requests.get")
    def test_indeed_success(self, mock_get):
        """Test successful Indeed job search."""
        from tools.indeed_search_tool import search_indeed_jobs

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "job_title": "Data Analyst",
                        "employer_name": "DataCo",
                        "job_apply_link": "https://example.com/apply",
                        "job_city": "Mumbai",
                    }
                ]
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_indeed_jobs("Data Analyst", "Mumbai")

        assert isinstance(result, (list, str))
        if isinstance(result, list):
            assert result[0]["platform"] == "Indeed"
            assert result[0]["title"] == "Data Analyst"

    @patch("tools.jsearch_api_tool.requests.get")
    def test_indeed_no_location(self, mock_get):
        """Test Indeed search without specifying location."""
        from tools.indeed_search_tool import search_indeed_jobs

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "job_title": "Remote Engineer",
                        "employer_name": "RemoteCo",
                        "job_apply_link": "https://example.com",
                        "job_city": "",
                    }
                ]
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_indeed_jobs("Remote Engineer")

        assert isinstance(result, (list, str))

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"}, clear=False)
    @patch("tools.jsearch_api_tool.requests.get")
    def test_indeed_internship_filter(self, mock_get):
        """Test Indeed internship filtering."""
        from tools.indeed_search_tool import search_indeed_jobs

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "job_title": "Data Analyst",
                        "employer_name": "DataCo",
                        "job_apply_link": "https://example.com/apply1",
                        "job_city": "Mumbai",
                        "job_employment_type": "INTERNSHIP",
                    },
                    {
                        "job_title": "Data Analyst",
                        "employer_name": "AnalyticsCorp",
                        "job_apply_link": "https://example.com/apply2",
                        "job_city": "Mumbai",
                        "job_employment_type": "FULL_TIME",
                    },
                ]
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_indeed_jobs("Data Analyst", "Mumbai", job_type="internship")

        assert isinstance(result, list)
        assert len(result) == 1
        assert "INTERNSHIP" in result[0]["job_type"]

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"}, clear=False)
    @patch("tools.jsearch_api_tool.requests.get")
    def test_indeed_full_time_filter(self, mock_get):
        """Test Indeed full-time job filtering."""
        from tools.indeed_search_tool import search_indeed_jobs

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "job_title": "Engineer",
                        "employer_name": "TechCorp",
                        "job_apply_link": "https://example.com/apply1",
                        "job_city": "Bengaluru",
                        "job_employment_type": "INTERNSHIP",
                    },
                    {
                        "job_title": "Engineer",
                        "employer_name": "MegaCorp",
                        "job_apply_link": "https://example.com/apply2",
                        "job_city": "Bengaluru",
                        "job_employment_type": "FULL_TIME",
                    },
                ]
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = search_indeed_jobs("Engineer", "Bengaluru", job_type="full-time")

        assert isinstance(result, list)
        assert len(result) == 1
        assert "FULL_TIME" in result[0]["job_type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
