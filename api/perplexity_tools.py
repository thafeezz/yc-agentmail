"""
Perplexity API tools for travel suggestions and web search.

This module provides tools for:
- Travel destination searches
- Location-based travel recommendations
- Multi-query travel research
- Real-time travel information retrieval
"""

from langchain.tools import tool
from typing import Any, Optional, List
from pydantic import BaseModel, Field


class TravelSearchInput(BaseModel):
    """Input schema for travel search tool."""
    query: str = Field(description="The travel-related query to search for")
    max_results: int = Field(default=5, description="Maximum number of results to return (1-20)")
    country: Optional[str] = Field(default=None, description="ISO 3166-1 alpha-2 country code (e.g., 'US', 'GB', 'FR')")


class MultiTravelSearchInput(BaseModel):
    """Input schema for multi-query travel search tool."""
    queries: List[str] = Field(description="List of related travel queries to search")
    max_results: int = Field(default=10, description="Maximum total results to return")
    country: Optional[str] = Field(default=None, description="ISO 3166-1 alpha-2 country code")


class PerplexitySearchTool:
    """Wrapper class for Perplexity API search operations."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Perplexity search tool.
        
        Args:
            api_key: Perplexity API key. If None, will use PERPLEXITY_API_KEY env var.
        """
        try:
            from perplexity import Perplexity
        except ImportError:
            raise ImportError(
                "perplexity package not installed. Install it with: pip install perplexity"
            )
        
        self.client = Perplexity(api_key=api_key) if api_key else Perplexity()
    
    def search(
        self,
        query: str | List[str],
        max_results: int = 5,
        country: Optional[str] = None,
        return_images: bool = True,
        return_snippets: bool = True
    ) -> str:
        """
        Perform a search using Perplexity API.
        
        Args:
            query: Single query string or list of queries
            max_results: Maximum number of results to return
            country: ISO country code for location-based search
            return_images: Whether to include images in results
            return_snippets: Whether to include text snippets
            
        Returns:
            Formatted search results as a string
        """
        try:
            search_params = {
                "query": query,
                "max_results": max_results,
                "return_images": return_images,
                "return_snippets": return_snippets
            }
            
            if country:
                search_params["country"] = country.upper()
            
            search = self.client.search.create(**search_params)
            
            # Format results
            results_text = []
            if isinstance(query, list):
                results_text.append(f"Search Results for queries: {', '.join(query)}\n")
            else:
                results_text.append(f"Search Results for: {query}\n")
            
            results_text.append(f"Found {len(search.results)} results\n")
            results_text.append("=" * 80 + "\n")
            
            for i, result in enumerate(search.results, 1):
                results_text.append(f"\n{i}. {result.title}")
                results_text.append(f"   URL: {result.url}")
                
                if hasattr(result, 'date') and result.date:
                    results_text.append(f"   Date: {result.date}")
                
                if hasattr(result, 'snippet') and result.snippet:
                    results_text.append(f"   Snippet: {result.snippet}")
                
                if return_images and hasattr(result, 'images') and result.images:
                    results_text.append(f"   Images: {len(result.images)} found")
                
                results_text.append("")  # Empty line between results
            
            return "\n".join(results_text)
            
        except Exception as e:
            return f"Error performing search: {str(e)}"


# Initialize the search tool (will be None if API key not available)
try:
    from .cfg import settings
    perplexity_tool = PerplexitySearchTool(
        api_key=getattr(settings, 'perplexity_api_key', None)
    ) if hasattr(settings, 'perplexity_api_key') and settings.perplexity_api_key else None
except (ImportError, Exception):
    perplexity_tool = None


@tool
def search_travel_destinations(
    query: str,
    max_results: int = 5,
    country: Optional[str] = None
) -> str:
    """Search for travel destinations, recommendations, and travel information using Perplexity AI.
    
    This tool provides real-time, up-to-date travel information including:
    - Destination recommendations
    - Travel tips and guides
    - Local attractions and activities
    - Restaurant and hotel suggestions
    - Travel safety and restrictions
    - Cultural information and events
    
    Args:
        query: The travel-related question or search query (e.g., "best beaches in Thailand",
               "family-friendly hotels in Paris", "local restaurants in Tokyo")
        max_results: Number of results to return (default: 5, max: 20)
        country: Optional ISO country code for location-specific results (e.g., "US", "GB", "FR", "JP")
    
    Returns:
        Formatted search results with titles, URLs, snippets, and images.
    
    Examples:
        - search_travel_destinations("best time to visit Japan", max_results=5)
        - search_travel_destinations("luxury resorts in Maldives", max_results=3)
        - search_travel_destinations("local restaurants", country="IT", max_results=5)
    """
    if perplexity_tool is None:
        return (
            "Perplexity search tool not available. "
            "Please ensure PERPLEXITY_API_KEY is set in your environment and "
            "the perplexity package is installed."
        )
    
    return perplexity_tool.search(
        query=query,
        max_results=min(max_results, 20),  # Cap at 20
        country=country,
        return_images=True,
        return_snippets=True
    )


@tool
def search_multiple_travel_topics(
    queries: List[str],
    max_results: int = 10,
    country: Optional[str] = None
) -> str:
    """Search multiple related travel topics in a single request for comprehensive travel planning.
    
    This tool is ideal for gathering comprehensive information across multiple aspects of travel,
    such as accommodations, dining, activities, and transportation all at once.
    
    Args:
        queries: List of related travel queries (e.g., ["hotels in Paris", "restaurants in Paris", 
                 "things to do in Paris"])
        max_results: Maximum total results across all queries (default: 10)
        country: Optional ISO country code for location-specific results
    
    Returns:
        Combined and ranked search results from all queries.
    
    Examples:
        - search_multiple_travel_topics(
            ["hotels in Barcelona", "beaches near Barcelona", "Barcelona nightlife"],
            max_results=10
          )
        - search_multiple_travel_topics(
            ["best ski resorts", "ski equipment rental", "ski lessons for beginners"],
            country="CH",
            max_results=15
          )
    """
    if perplexity_tool is None:
        return (
            "Perplexity search tool not available. "
            "Please ensure PERPLEXITY_API_KEY is set in your environment and "
            "the perplexity package is installed."
        )
    
    if not queries or len(queries) == 0:
        return "Error: At least one query must be provided"
    
    if len(queries) > 5:
        return "Error: Maximum of 5 queries allowed per search"
    
    return perplexity_tool.search(
        query=queries,
        max_results=max_results,
        country=country,
        return_images=True,
        return_snippets=True
    )


@tool
def search_local_travel_info(
    query: str,
    country_code: str,
    max_results: int = 5
) -> str:
    """Search for location-specific travel information within a particular country.
    
    This tool is optimized for finding local, region-specific travel information by
    filtering results to a specific country.
    
    Args:
        query: The travel query (e.g., "best coffee shops", "historical sites", "hiking trails")
        country_code: ISO 3166-1 alpha-2 country code (e.g., "US", "GB", "FR", "DE", "JP", "AU")
        max_results: Number of results to return (default: 5)
    
    Returns:
        Location-specific search results.
    
    Common country codes:
        - US: United States
        - GB: United Kingdom
        - CA: Canada
        - FR: France
        - DE: Germany
        - IT: Italy
        - ES: Spain
        - JP: Japan
        - AU: Australia
        - NZ: New Zealand
    
    Examples:
        - search_local_travel_info("top museums", "FR", max_results=5)
        - search_local_travel_info("local food markets", "JP", max_results=3)
        - search_local_travel_info("budget hotels", "DE", max_results=10)
    """
    if perplexity_tool is None:
        return (
            "Perplexity search tool not available. "
            "Please ensure PERPLEXITY_API_KEY is set in your environment and "
            "the perplexity package is installed."
        )
    
    if not country_code or len(country_code) != 2:
        return "Error: Country code must be a valid 2-letter ISO 3166-1 alpha-2 code"
    
    return perplexity_tool.search(
        query=query,
        max_results=max_results,
        country=country_code,
        return_images=True,
        return_snippets=True
    )


# Export all tools
__all__ = [
    'search_travel_destinations',
    'search_multiple_travel_topics',
    'search_local_travel_info',
    'PerplexitySearchTool',
]

