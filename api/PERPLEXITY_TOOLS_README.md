# Perplexity Travel Search Tools

This module provides LangChain tools for integrating Perplexity AI's Search API to deliver real-time travel suggestions and information.

## Features

- **Real-time travel information**: Get up-to-date travel recommendations, destination guides, and local insights
- **Location-based search**: Filter results by country using ISO country codes
- **Multi-query support**: Search multiple related topics in a single request
- **Rich results**: Includes titles, URLs, snippets, publication dates, and images
- **Error handling**: Graceful handling of API errors and rate limits

## Installation

1. **Install the Perplexity SDK**:
   ```bash
   uv pip install perplexity
   ```
   Or add it to your `pyproject.toml` (already included).

2. **Set up your API key**:
   Get your API key from [Perplexity API Settings](https://www.perplexity.ai/settings/api) and add it to your `.env` file:
   ```bash
   PERPLEXITY_API_KEY=your_api_key_here
   ```

## Available Tools

### 1. `search_travel_destinations`

Search for general travel information, destinations, and recommendations.

**Parameters:**
- `query` (str): The travel-related question or search query
- `max_results` (int, optional): Number of results to return (default: 5, max: 20)
- `country` (str, optional): ISO 3166-1 alpha-2 country code for location-specific results

**Examples:**
```python
from api.perplexity_tools import search_travel_destinations

# Basic search
result = search_travel_destinations.invoke({
    "query": "best beaches in Thailand",
    "max_results": 5
})

# Search with location filter
result = search_travel_destinations.invoke({
    "query": "luxury resorts",
    "country": "MV",  # Maldives
    "max_results": 3
})

# Travel planning queries
result = search_travel_destinations.invoke({
    "query": "best time to visit Japan for cherry blossoms",
    "max_results": 5
})
```

### 2. `search_multiple_travel_topics`

Search multiple related travel topics in a single request for comprehensive trip planning.

**Parameters:**
- `queries` (List[str]): List of related travel queries (max 5 queries)
- `max_results` (int, optional): Maximum total results across all queries (default: 10)
- `country` (str, optional): ISO country code for location-specific results

**Examples:**
```python
from api.perplexity_tools import search_multiple_travel_topics

# Plan a complete trip
result = search_multiple_travel_topics.invoke({
    "queries": [
        "hotels in Barcelona",
        "restaurants in Barcelona", 
        "things to do in Barcelona",
        "Barcelona public transportation"
    ],
    "max_results": 15
})

# Activity planning
result = search_multiple_travel_topics.invoke({
    "queries": [
        "best ski resorts Alps",
        "ski equipment rental",
        "ski lessons for beginners"
    ],
    "country": "CH",  # Switzerland
    "max_results": 10
})
```

### 3. `search_local_travel_info`

Search for location-specific travel information within a particular country.

**Parameters:**
- `query` (str): The travel query
- `country_code` (str): ISO 3166-1 alpha-2 country code (e.g., "US", "GB", "FR")
- `max_results` (int, optional): Number of results to return (default: 5)

**Examples:**
```python
from api.perplexity_tools import search_local_travel_info

# Find local attractions
result = search_local_travel_info.invoke({
    "query": "hidden gem restaurants",
    "country_code": "JP",  # Japan
    "max_results": 5
})

# Local events
result = search_local_travel_info.invoke({
    "query": "festivals in December",
    "country_code": "DE",  # Germany
    "max_results": 5
})
```

## Common Country Codes

| Code | Country         | Code | Country        |
|------|-----------------|------|----------------|
| US   | United States   | JP   | Japan          |
| GB   | United Kingdom  | AU   | Australia      |
| CA   | Canada          | NZ   | New Zealand    |
| FR   | France          | MX   | Mexico         |
| DE   | Germany         | BR   | Brazil         |
| IT   | Italy           | ES   | Spain          |
| CH   | Switzerland     | NL   | Netherlands    |
| AT   | Austria         | SE   | Sweden         |
| GR   | Greece          | TH   | Thailand       |
| MV   | Maldives        | SG   | Singapore      |

See the full list: [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)

## Using with LangChain Agents

```python
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from api.perplexity_tools import (
    search_travel_destinations,
    search_multiple_travel_topics,
    search_local_travel_info
)

# Create tools list
tools = [
    search_travel_destinations,
    search_multiple_travel_topics,
    search_local_travel_info
]

# Create agent
llm = ChatOpenAI(model="gpt-4", temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful travel planning assistant."),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Use the agent
result = agent_executor.invoke({
    "input": "I want to plan a 5-day trip to Paris. Can you suggest hotels, restaurants, and top attractions?"
})
print(result["output"])
```

## Direct API Usage

For more control, use the `PerplexitySearchTool` class directly:

```python
from api.perplexity_tools import PerplexitySearchTool

# Initialize with API key
tool = PerplexitySearchTool(api_key="your_api_key")

# Or use environment variable
tool = PerplexitySearchTool()

# Perform search
result = tool.search(
    query="best hiking trails",
    max_results=10,
    country="NZ",
    return_images=True,
    return_snippets=True
)

print(result)
```

## Error Handling

The tools handle common errors gracefully:

```python
try:
    result = search_travel_destinations.invoke({
        "query": "hotels in Paris",
        "max_results": 5
    })
except Exception as e:
    print(f"Error: {e}")
```

Common error scenarios:
- **API key not set**: Returns a helpful message about setting `PERPLEXITY_API_KEY`
- **Rate limit exceeded**: Built-in retry logic handles temporary rate limits
- **Invalid parameters**: Clear error messages for validation issues
- **Network errors**: Graceful handling with error messages

## Best Practices

1. **Be specific with queries**: More specific queries return better results
   - Good: "family-friendly hotels in Tokyo with pools"
   - Less good: "hotels Tokyo"

2. **Use country codes for local information**: When searching for local businesses or attractions, use the `country` parameter

3. **Combine queries strategically**: Group related queries in `search_multiple_travel_topics` for efficient API usage

4. **Limit results appropriately**: Request only the number of results you need to minimize costs and response time

5. **Handle empty results**: Always check if results are meaningful before presenting to users

## Testing

Run the test suite:

```bash
# Unit tests (no API key required)
pytest api/test_perplexity_tools.py -v

# Integration tests (requires PERPLEXITY_API_KEY)
pytest api/test_perplexity_tools.py --run-integration -v
```

## Rate Limits

Perplexity API has rate limits. Best practices:
- Cache frequently requested searches
- Batch related queries using `search_multiple_travel_topics`
- Implement exponential backoff for retries
- Monitor your API usage in the Perplexity dashboard

## Example Use Cases

### 1. Complete Trip Planning
```python
# Get comprehensive trip information
result = search_multiple_travel_topics.invoke({
    "queries": [
        "best hotels in Rome near attractions",
        "authentic Italian restaurants Rome",
        "must-see attractions Rome 3 days",
        "Rome metro pass tourist"
    ],
    "max_results": 20
})
```

### 2. Safety and Travel Restrictions
```python
# Check current travel conditions
result = search_travel_destinations.invoke({
    "query": "current travel restrictions and safety guidelines for Thailand 2024",
    "max_results": 5
})
```

### 3. Local Experiences
```python
# Find local hidden gems
result = search_local_travel_info.invoke({
    "query": "local markets and street food recommendations",
    "country_code": "VN",  # Vietnam
    "max_results": 5
})
```

### 4. Budget Travel
```python
# Find budget-friendly options
result = search_travel_destinations.invoke({
    "query": "budget backpacking Southeast Asia cheapest countries 2024",
    "max_results": 10
})
```

## Troubleshooting

**Issue**: "Perplexity search tool not available"
- **Solution**: Ensure `PERPLEXITY_API_KEY` is set in your `.env` file and the `perplexity` package is installed

**Issue**: Empty or irrelevant results
- **Solution**: Make your query more specific and consider adding a country filter

**Issue**: Rate limit errors
- **Solution**: Implement caching and reduce the frequency of requests

**Issue**: Import errors
- **Solution**: Run `uv pip install perplexity` to install the SDK

## Resources

- [Perplexity API Documentation](https://docs.perplexity.ai/)
- [Perplexity SDK Guide](https://docs.perplexity.ai/guides/perplexity-sdk)
- [Search API Reference](https://docs.perplexity.ai/api-reference/search-post)
- [Get API Key](https://www.perplexity.ai/settings/api)

## Support

For issues specific to these tools, check the test file `api/test_perplexity_tools.py` for examples.
For Perplexity API issues, consult the [official documentation](https://docs.perplexity.ai/).

