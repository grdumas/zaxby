"""Shared pytest fixtures for test suite."""
import pytest
from src.cache_service import get_cache_service


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test to ensure isolation."""
    cache_service = get_cache_service()
    cache_service.clear()
    cache_service.reset_metrics()
    yield
    cache_service.clear()
    cache_service.reset_metrics()
