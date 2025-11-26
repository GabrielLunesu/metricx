"""
QA Evaluation Test Fixtures
============================

Shared fixtures for QA evaluation tests.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing without API calls."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"metric": "roas", "time_range": {"last_n_days": 7}}'
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_dsl_response() -> Dict[str, Any]:
    """Sample DSL response for testing."""
    return {
        "metric": "roas",
        "time_range": {"last_n_days": 7},
        "compare_to_previous": False,
        "group_by": "none",
        "breakdown": None,
        "top_n": 5,
        "filters": {},
    }


@pytest.fixture
def sample_metric_result() -> Dict[str, Any]:
    """Sample metric result for testing."""
    return {
        "summary": 2.45,
        "previous": 2.06,
        "delta_pct": 0.189,
        "timeseries": [
            {"date": "2025-01-01", "value": 2.30},
            {"date": "2025-01-02", "value": 2.45},
            {"date": "2025-01-03", "value": 2.60},
        ],
        "breakdown": [
            {"label": "Campaign A", "value": 3.20},
            {"label": "Campaign B", "value": 2.80},
            {"label": "Campaign C", "value": 1.90},
        ],
        "workspace_avg": 2.50,
    }


@pytest.fixture
def sample_comparison_result() -> Dict[str, Any]:
    """Sample comparison result with previous period data."""
    return {
        "summary": 1000.0,
        "previous": 850.0,
        "delta_pct": 0.176,
        "timeseries": [
            {"date": "2025-01-01", "value": 300},
            {"date": "2025-01-02", "value": 350},
            {"date": "2025-01-03", "value": 350},
        ],
        "timeseries_previous": [
            {"date": "2024-12-25", "value": 280},
            {"date": "2024-12-26", "value": 290},
            {"date": "2024-12-27", "value": 280},
        ],
    }


@pytest.fixture
def sample_breakdown_result() -> Dict[str, Any]:
    """Sample result with breakdown data."""
    return {
        "summary": 15000.0,
        "breakdown": [
            {"label": "Holiday Sale Campaign", "value": 5000.0},
            {"label": "Summer Promo", "value": 4500.0},
            {"label": "App Install Campaign", "value": 3000.0},
            {"label": "Brand Awareness", "value": 2500.0},
        ],
    }


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    return MagicMock()


@pytest.fixture
def test_workspace_id() -> str:
    """Test workspace ID."""
    return "test-workspace-123"


@pytest.fixture
def test_user_id() -> str:
    """Test user ID."""
    return "test-user-456"


# =============================================================================
# DeepEval Fixtures (optional)
# =============================================================================

@pytest.fixture
def deepeval_available() -> bool:
    """Check if DeepEval is available."""
    try:
        import deepeval
        return True
    except ImportError:
        return False


@pytest.fixture
def skip_without_deepeval(deepeval_available):
    """Skip test if DeepEval is not available."""
    if not deepeval_available:
        pytest.skip("DeepEval not installed")
