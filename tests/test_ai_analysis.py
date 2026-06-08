"""
Tests for AI analysis service (RPOPC-1016).
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ai_analysis import (
    AIAnalysisService,
    AIAnalysisError,
    get_ai_analysis_service,
    analyze_performance_comparison,
)


@pytest.fixture
def mock_anthropic():
    """Mock the anthropic package."""
    # Mock the anthropic module import
    mock_anthropic_module = MagicMock()

    # Mock the Anthropic client
    mock_client = MagicMock()
    mock_anthropic_module.Anthropic.return_value = mock_client

    # Mock a successful response
    mock_message = MagicMock()
    mock_block = MagicMock()
    mock_block.text = "Test analysis response"
    mock_message.content = [mock_block]
    mock_client.messages.create.return_value = mock_message

    # Mock APIError class
    mock_anthropic_module.APIError = Exception

    # Patch the import
    with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
        yield mock_anthropic_module


@pytest.fixture
def sample_data():
    """Sample performance comparison data."""
    return {
        "baseline": {
            "throughput": 1000,
            "latency": 50,
            "cpu_usage": 60
        },
        "comparison": {
            "throughput": 1100,
            "latency": 45,
            "cpu_usage": 58
        },
        "metadata": {
            "test": "benchmark_test",
            "os_version": "RHEL 9.5 → RHEL 9.6",
            "hardware": "AWS m5.xlarge"
        }
    }


def test_service_init_with_api_key(mock_anthropic):
    """Test service initialization with explicit API key."""
    service = AIAnalysisService(api_key="test-key")
    assert service.api_key == "test-key"
    assert service.client is not None


def test_service_init_from_env(mock_anthropic):
    """Test service initialization from environment variable."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
        service = AIAnalysisService()
        assert service.api_key == "env-key"


def test_service_init_no_api_key(mock_anthropic):
    """Test service initialization fails without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(AIAnalysisError, match="ANTHROPIC_API_KEY"):
            AIAnalysisService()


def test_service_init_missing_package():
    """Test service initialization fails if anthropic package not installed."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        # Simulate anthropic not being installed
        with patch.dict('sys.modules', {'anthropic': None}):
            with pytest.raises(AIAnalysisError, match="anthropic package not installed"):
                # This will trigger ImportError when trying to import anthropic
                service = AIAnalysisService()


def test_analyze_comparison_success(mock_anthropic, sample_data):
    """Test successful comparison analysis."""
    service = AIAnalysisService(api_key="test-key")

    result = service.analyze_comparison(
        baseline_data=sample_data["baseline"],
        comparison_data=sample_data["comparison"],
        metadata=sample_data["metadata"],
        persona="executive"
    )

    assert result == "Test analysis response"
    assert mock_anthropic.Anthropic().messages.create.called


def test_analyze_comparison_different_personas(mock_anthropic, sample_data):
    """Test that different personas call the API with different prompts."""
    service = AIAnalysisService(api_key="test-key")

    for persona in ["executive", "tech_lead", "expert"]:
        result = service.analyze_comparison(
            baseline_data=sample_data["baseline"],
            comparison_data=sample_data["comparison"],
            persona=persona
        )
        assert result == "Test analysis response"


def test_analyze_comparison_custom_model(mock_anthropic, sample_data):
    """Test analysis with custom model parameter."""
    service = AIAnalysisService(api_key="test-key")

    service.analyze_comparison(
        baseline_data=sample_data["baseline"],
        comparison_data=sample_data["comparison"],
        model="claude-opus-4"
    )

    call_kwargs = mock_anthropic.Anthropic().messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-opus-4"


def test_analyze_comparison_custom_max_tokens(mock_anthropic, sample_data):
    """Test analysis with custom max_tokens parameter."""
    service = AIAnalysisService(api_key="test-key")

    service.analyze_comparison(
        baseline_data=sample_data["baseline"],
        comparison_data=sample_data["comparison"],
        max_tokens=4096
    )

    call_kwargs = mock_anthropic.Anthropic().messages.create.call_args[1]
    assert call_kwargs["max_tokens"] == 4096


def test_analyze_comparison_api_error(mock_anthropic, sample_data):
    """Test handling of API errors."""
    mock_anthropic.Anthropic().messages.create.side_effect = (
        mock_anthropic.APIError("API error")
    )

    service = AIAnalysisService(api_key="test-key")

    with pytest.raises(AIAnalysisError, match="AI service error"):
        service.analyze_comparison(
            baseline_data=sample_data["baseline"],
            comparison_data=sample_data["comparison"]
        )


def test_analyze_comparison_empty_response(mock_anthropic, sample_data):
    """Test handling of empty AI response."""
    mock_message = MagicMock()
    mock_message.content = []
    mock_anthropic.Anthropic().messages.create.return_value = mock_message

    service = AIAnalysisService(api_key="test-key")

    with pytest.raises(AIAnalysisError, match="Empty response"):
        service.analyze_comparison(
            baseline_data=sample_data["baseline"],
            comparison_data=sample_data["comparison"]
        )


def test_is_available(mock_anthropic):
    """Test availability check."""
    service = AIAnalysisService(api_key="test-key")
    assert service.is_available() is True


def test_get_ai_analysis_service_with_key(mock_anthropic):
    """Test getting global service instance with API key."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        # Reset the global service
        import src.ai_analysis
        src.ai_analysis._service = None

        service = get_ai_analysis_service()
        assert service is not None
        assert service.is_available()


def test_get_ai_analysis_service_without_key():
    """Test getting global service instance without API key."""
    with patch.dict(os.environ, {}, clear=True):
        # Reset the global service
        import src.ai_analysis
        src.ai_analysis._service = None

        # Mock anthropic module
        mock_anthropic = MagicMock()
        with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
            service = get_ai_analysis_service()
            assert service is None


def test_analyze_performance_comparison_convenience(mock_anthropic, sample_data):
    """Test convenience function for analysis."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        # Reset the global service
        import src.ai_analysis
        src.ai_analysis._service = None

        result = analyze_performance_comparison(
            baseline_data=sample_data["baseline"],
            comparison_data=sample_data["comparison"],
            metadata=sample_data["metadata"],
            persona="tech_lead"
        )

        assert result == "Test analysis response"


def test_analyze_performance_comparison_no_service():
    """Test convenience function when service is unavailable."""
    with patch.dict(os.environ, {}, clear=True):
        # Reset the global service
        import src.ai_analysis
        src.ai_analysis._service = None

        # Mock anthropic module
        mock_anthropic = MagicMock()
        with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
            result = analyze_performance_comparison(
                baseline_data={"metric": 100},
                comparison_data={"metric": 110}
            )

            assert result is None


def test_analyze_comparison_includes_context_in_prompt(mock_anthropic, sample_data):
    """Test that comparison context is included in the API call."""
    service = AIAnalysisService(api_key="test-key")

    service.analyze_comparison(
        baseline_data=sample_data["baseline"],
        comparison_data=sample_data["comparison"],
        metadata=sample_data["metadata"]
    )

    # Get the user message content
    call_kwargs = mock_anthropic.Anthropic().messages.create.call_args[1]
    user_message = call_kwargs["messages"][0]["content"]

    # Check that key data points are in the prompt
    assert "throughput" in user_message.lower()
    assert "1000" in user_message or "1100" in user_message


def test_analyze_comparison_uses_system_prompt(mock_anthropic, sample_data):
    """Test that system prompt is properly set."""
    service = AIAnalysisService(api_key="test-key")

    service.analyze_comparison(
        baseline_data=sample_data["baseline"],
        comparison_data=sample_data["comparison"],
        persona="executive"
    )

    call_kwargs = mock_anthropic.Anthropic().messages.create.call_args[1]
    system_prompt = call_kwargs["system"]

    # Executive persona should mention executives or concise
    assert "executive" in system_prompt.lower() or "concise" in system_prompt.lower()
