"""
Unit tests for application_tracker_tool with edge case handling.
Tests error scenarios, partial failures, and invalid inputs.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from tools.application_tracker_tool import save_jobs_to_notion


class TestSaveJobsToNotion:
    """Test suite for Notion job saving functionality."""

    @patch.dict('os.environ', {'NOTION_API_TOKEN': 'test_token', 'NOTION_DATABASE_ID': 'test-db-id'})
    @patch('tools.application_tracker_tool.Client')
    def test_save_jobs_success(self, mock_client):
        """Test successful job saving to Notion."""
        jobs = [
            {"title": "Python Engineer", "company": "TechCorp", "url": "https://example.com/job1"},
            {"title": "Data Scientist", "company": "DataCo", "url": "https://example.com/job2"},
        ]
        jobs_json = json.dumps(jobs)

        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        result = save_jobs_to_notion(jobs_json)

        assert "Successfully saved 2 job(s)" in result
        assert mock_instance.pages.create.call_count == 2

    @patch.dict('os.environ', {'NOTION_API_TOKEN': '', 'NOTION_DATABASE_ID': ''})
    def test_missing_notion_credentials(self):
        """Test error handling when Notion credentials are missing."""
        jobs = [{"title": "Job", "company": "Company", "url": "url"}]
        jobs_json = json.dumps(jobs)

        result = save_jobs_to_notion(jobs_json)

        assert "must be set in the .env file" in result or "error" in result.lower()

    @patch.dict('os.environ', {'NOTION_API_TOKEN': 'test_token', 'NOTION_DATABASE_ID': 'test-db-id'})
    @patch('tools.application_tracker_tool.Client')
    def test_partial_job_save_failure(self, mock_client):
        """Test partial failure when saving multiple jobs."""
        jobs = [
            {"title": "Job 1", "company": "Company 1", "url": "url1"},
            {"title": "Job 2", "company": "Company 2", "url": "url2"},
            {"title": "Job 3", "company": "Company 3", "url": "url3"},
        ]
        jobs_json = json.dumps(jobs)

        mock_instance = MagicMock()
        # Simulate failure on second job
        mock_instance.pages.create.side_effect = [None, Exception("API Error"), None]
        mock_client.return_value = mock_instance

        result = save_jobs_to_notion(jobs_json)

        assert "Saved 2 of 3 job(s)" in result
        assert "Failed:" in result
        assert "Job 2" in result

    @patch.dict('os.environ', {'NOTION_API_TOKEN': 'test_token', 'NOTION_DATABASE_ID': 'test-db-id'})
    def test_empty_jobs_list(self):
        """Test handling of empty job list."""
        jobs_json = json.dumps([])

        result = save_jobs_to_notion(jobs_json)

        assert "No jobs were selected" in result

    @patch.dict('os.environ', {'NOTION_API_TOKEN': 'test_token', 'NOTION_DATABASE_ID': 'test-db-id'})
    def test_invalid_json(self):
        """Test error handling for invalid JSON input."""
        invalid_json = "{invalid json}"

        result = save_jobs_to_notion(invalid_json)

        assert "error" in result.lower() or "occurred" in result.lower()

    @patch.dict('os.environ', {'NOTION_API_TOKEN': 'test_token', 'NOTION_DATABASE_ID': 'test-db-123-456'})
    @patch('tools.application_tracker_tool.Client')
    def test_database_id_formatting(self, mock_client):
        """Test that database IDs with hyphens are properly formatted."""
        jobs = [{"title": "Job", "company": "Company", "url": "url"}]
        jobs_json = json.dumps(jobs)

        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        save_jobs_to_notion(jobs_json)

        call_args = mock_instance.pages.create.call_args
        assert call_args is not None
        database_id_sent = call_args[1]['parent']['database_id']
        assert "-" not in database_id_sent
        assert database_id_sent == "testdb123456"

    @patch.dict('os.environ', {'NOTION_API_TOKEN': 'test_token', 'NOTION_DATABASE_ID': 'test-db-id'})
    @patch('tools.application_tracker_tool.Client')
    def test_missing_job_fields(self, mock_client):
        """Test handling of jobs with missing optional fields."""
        jobs = [
            {"title": "Job", "company": "Company"},
            {"title": "Job2"},
        ]
        jobs_json = json.dumps(jobs)

        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        result = save_jobs_to_notion(jobs_json)

        assert "Successfully saved" in result or "Saved" in result
        assert mock_instance.pages.create.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
