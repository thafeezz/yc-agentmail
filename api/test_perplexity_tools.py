"""
Test suite for Perplexity travel search tools.

This file demonstrates how to use the Perplexity tools for travel suggestions.
Run with: python -m pytest api/test_perplexity_tools.py -v
"""

import pytest
from unittest.mock import Mock, patch
from api.perplexity_tools import (
    search_travel_destinations,
    search_multiple_travel_topics,
    search_local_travel_info,
    PerplexitySearchTool
)


class MockSearchResult:
    """Mock search result object."""
    def __init__(self, title, url, date=None, snippet=None, images=None):
        self.title = title
        self.url = url
        self.date = date
        self.snippet = snippet
        self.images = images or []


class MockSearchResponse:
    """Mock search response object."""
    def __init__(self, results):
        self.results = results


@pytest.fixture
def mock_perplexity_client():
    """Create a mock Perplexity client."""
    with patch('api.perplexity_tools.perplexity_tool') as mock_tool:
        mock_tool.search = Mock()
        yield mock_tool


def test_perplexity_search_tool_initialization():
    """Test PerplexitySearchTool initialization."""
    with patch('api.perplexity_tools.Perplexity') as mock_perplexity:
        tool = PerplexitySearchTool(api_key="test_key")
        assert tool.client is not None
        mock_perplexity.assert_called_once_with(api_key="test_key")


def test_search_travel_destinations_basic():
    """Test basic travel destination search."""
    with patch('api.perplexity_tools.perplexity_tool') as mock_tool:
        mock_tool.search.return_value = "Mocked search results"
        
        result = search_travel_destinations.invoke({
            "query": "best beaches in Thailand",
            "max_results": 5
        })
        
        mock_tool.search.assert_called_once()
        assert isinstance(result, str)


def test_search_travel_destinations_with_country():
    """Test travel search with country filter."""
    with patch('api.perplexity_tools.perplexity_tool') as mock_tool:
        mock_tool.search.return_value = "Mocked search results"
        
        result = search_travel_destinations.invoke({
            "query": "local restaurants",
            "max_results": 3,
            "country": "IT"
        })
        
        mock_tool.search.assert_called_once_with(
            query="local restaurants",
            max_results=3,
            country="IT",
            return_images=True,
            return_snippets=True
        )


def test_search_multiple_travel_topics():
    """Test multi-query travel search."""
    with patch('api.perplexity_tools.perplexity_tool') as mock_tool:
        mock_tool.search.return_value = "Mocked search results"
        
        queries = [
            "hotels in Barcelona",
            "restaurants in Barcelona",
            "things to do in Barcelona"
        ]
        
        result = search_multiple_travel_topics.invoke({
            "queries": queries,
            "max_results": 10
        })
        
        mock_tool.search.assert_called_once_with(
            query=queries,
            max_results=10,
            country=None,
            return_images=True,
            return_snippets=True
        )


def test_search_multiple_travel_topics_too_many_queries():
    """Test that too many queries are rejected."""
    with patch('api.perplexity_tools.perplexity_tool') as mock_tool:
        queries = [f"query {i}" for i in range(6)]  # 6 queries (max is 5)
        
        result = search_multiple_travel_topics.invoke({
            "queries": queries,
            "max_results": 10
        })
        
        assert "Maximum of 5 queries" in result
        mock_tool.search.assert_not_called()


def test_search_local_travel_info():
    """Test location-specific travel search."""
    with patch('api.perplexity_tools.perplexity_tool') as mock_tool:
        mock_tool.search.return_value = "Mocked search results"
        
        result = search_local_travel_info.invoke({
            "query": "top museums",
            "country_code": "FR",
            "max_results": 5
        })
        
        mock_tool.search.assert_called_once_with(
            query="top museums",
            max_results=5,
            country="FR",
            return_images=True,
            return_snippets=True
        )


def test_search_local_travel_info_invalid_country_code():
    """Test that invalid country codes are rejected."""
    with patch('api.perplexity_tools.perplexity_tool') as mock_tool:
        result = search_local_travel_info.invoke({
            "query": "museums",
            "country_code": "USA",  # Invalid: should be 2 letters
            "max_results": 5
        })
        
        assert "valid 2-letter ISO 3166-1 alpha-2 code" in result
        mock_tool.search.assert_not_called()


def test_perplexity_search_tool_format_results():
    """Test result formatting."""
    mock_results = [
        MockSearchResult(
            title="Best Beaches in Thailand",
            url="https://example.com/thailand-beaches",
            date="2024-10-15",
            snippet="Discover the most beautiful beaches...",
            images=["img1.jpg", "img2.jpg"]
        ),
        MockSearchResult(
            title="Top 10 Thai Islands",
            url="https://example.com/thai-islands",
            snippet="Explore paradise islands..."
        )
    ]
    
    with patch('api.perplexity_tools.Perplexity') as mock_perplexity:
        mock_client = Mock()
        mock_client.search.create.return_value = MockSearchResponse(mock_results)
        mock_perplexity.return_value = mock_client
        
        tool = PerplexitySearchTool(api_key="test_key")
        result = tool.search("beaches in Thailand", max_results=5)
        
        assert "Best Beaches in Thailand" in result
        assert "https://example.com/thailand-beaches" in result
        assert "2024-10-15" in result
        assert "Discover the most beautiful beaches" in result
        assert "2 found" in result  # Images count
        assert "Top 10 Thai Islands" in result


def test_tool_unavailable_when_no_api_key():
    """Test graceful handling when Perplexity is not configured."""
    with patch('api.perplexity_tools.perplexity_tool', None):
        result = search_travel_destinations.invoke({
            "query": "test",
            "max_results": 5
        })
        
        assert "Perplexity search tool not available" in result
        assert "PERPLEXITY_API_KEY" in result


def test_max_results_capped():
    """Test that max_results is capped at 20."""
    with patch('api.perplexity_tools.perplexity_tool') as mock_tool:
        mock_tool.search.return_value = "Mocked search results"
        
        result = search_travel_destinations.invoke({
            "query": "hotels",
            "max_results": 100  # Should be capped at 20
        })
        
        # Check that the call was made with max_results=20
        call_args = mock_tool.search.call_args
        assert call_args[1]['max_results'] == 20


# Integration test examples (requires actual API key)
@pytest.mark.integration
@pytest.mark.skipif(
    not pytest.config.getoption("--run-integration", default=False),
    reason="Integration tests require --run-integration flag and valid API key"
)
def test_real_travel_search():
    """
    Real integration test with Perplexity API.
    
    To run: pytest api/test_perplexity_tools.py::test_real_travel_search --run-integration -v
    Requires: PERPLEXITY_API_KEY environment variable
    """
    result = search_travel_destinations.invoke({
        "query": "best time to visit Japan",
        "max_results": 3
    })
    
    assert "Japan" in result or "travel" in result.lower()
    assert "URL:" in result


@pytest.mark.integration
@pytest.mark.skipif(
    not pytest.config.getoption("--run-integration", default=False),
    reason="Integration tests require --run-integration flag and valid API key"
)
def test_real_multi_query_search():
    """
    Real integration test for multi-query search.
    
    To run: pytest api/test_perplexity_tools.py::test_real_multi_query_search --run-integration -v
    Requires: PERPLEXITY_API_KEY environment variable
    """
    result = search_multiple_travel_topics.invoke({
        "queries": [
            "cheap hotels Paris",
            "free things to do Paris"
        ],
        "max_results": 5
    })
    
    assert "Paris" in result or len(result) > 100


# Add pytest hook for integration test flag
def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require API keys"
    )


if __name__ == "__main__":
    # Example usage without pytest
    print("Example usage of Perplexity travel tools:\n")
    
    print("1. Basic travel search:")
    print("   search_travel_destinations('best beaches in Thailand', max_results=5)")
    
    print("\n2. Search with country filter:")
    print("   search_travel_destinations('local restaurants', country='IT', max_results=5)")
    
    print("\n3. Multi-query search:")
    print("   search_multiple_travel_topics([")
    print("       'hotels in Barcelona',")
    print("       'restaurants in Barcelona',")
    print("       'things to do in Barcelona'")
    print("   ], max_results=10)")
    
    print("\n4. Location-specific search:")
    print("   search_local_travel_info('top museums', 'FR', max_results=5)")
    
    print("\n\nNote: Requires PERPLEXITY_API_KEY environment variable to be set.")

