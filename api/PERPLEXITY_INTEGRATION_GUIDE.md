# Perplexity Tools Integration Guide

This guide shows how to integrate the Perplexity travel search tools into your existing agent architecture.

## Quick Start

### 1. Setup

First, ensure you have your Perplexity API key:

```bash
# Add to your .env file
PERPLEXITY_API_KEY=your_api_key_here
```

Get your API key from: https://www.perplexity.ai/settings/api

### 2. Install Dependencies

The Perplexity SDK is already included in `pyproject.toml`. If you need to install it separately:

```bash
uv pip install perplexity
```

### 3. Basic Usage in Your Agent

The tools are automatically available when you import from `api.tools`:

```python
from api.tools import get_all_tools

# Get all tools including Perplexity tools
all_tools = get_all_tools()

# Now you can use them in your agent
```

## Integration with Existing Agents

### Option 1: Add to Group Chat Agent

Update your group chat orchestrator to include travel planning capabilities:

```python
from api.group_chat.orchestrator import GroupChatOrchestrator
from api.perplexity_tools import (
    search_travel_destinations,
    search_multiple_travel_topics,
    search_local_travel_info
)

# Add Perplexity tools to your agent's tool list
travel_tools = [
    search_travel_destinations,
    search_multiple_travel_topics,
    search_local_travel_info
]

# Include in orchestrator
orchestrator = GroupChatOrchestrator(
    additional_tools=travel_tools
)
```

### Option 2: Create a Dedicated Travel Agent

Create a specialized travel planning agent:

```python
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from api.perplexity_tools import (
    search_travel_destinations,
    search_multiple_travel_topics,
    search_local_travel_info
)

# Travel agent prompt
travel_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a knowledgeable travel planning assistant. 
    You help users plan trips by:
    - Suggesting destinations based on preferences and budget
    - Finding hotels, restaurants, and attractions
    - Providing local insights and hidden gems
    - Offering real-time travel information and safety guidelines
    - Creating comprehensive itineraries
    
    Always use the Perplexity search tools to get the most up-to-date information."""),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent
llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7)
tools = [
    search_travel_destinations,
    search_multiple_travel_topics,
    search_local_travel_info
]

travel_agent = create_openai_functions_agent(llm, tools, travel_prompt)
travel_executor = AgentExecutor(
    agent=travel_agent,
    tools=tools,
    verbose=True,
    max_iterations=5
)

# Use the agent
response = travel_executor.invoke({
    "input": "I want to plan a 7-day trip to Japan in April. Budget is $3000."
})
print(response["output"])
```

### Option 3: Add to Existing Agent Service

Update `api/agent_service.py` to include travel tools:

```python
# In api/agent_service.py

from .perplexity_tools import (
    search_travel_destinations,
    search_multiple_travel_topics,
    search_local_travel_info
)

class AgentService:
    def __init__(self):
        self.base_tools = [
            # ... existing tools ...
        ]
        
        # Add Perplexity tools
        self.travel_tools = [
            search_travel_destinations,
            search_multiple_travel_topics,
            search_local_travel_info
        ]
        
        self.all_tools = self.base_tools + self.travel_tools
    
    def create_travel_agent(self):
        """Create an agent specialized for travel planning."""
        # Implementation here
        pass
```

## Example Workflows

### Workflow 1: Complete Trip Planning

```python
from api.perplexity_tools import search_multiple_travel_topics

def plan_complete_trip(destination, duration_days, budget):
    """Plan a complete trip with hotels, dining, and activities."""
    
    queries = [
        f"best hotels in {destination} for {budget} budget",
        f"highly rated restaurants in {destination}",
        f"must-see attractions in {destination} {duration_days} days",
        f"local transportation options {destination}",
        f"travel tips and cultural etiquette {destination}"
    ]
    
    result = search_multiple_travel_topics.invoke({
        "queries": queries,
        "max_results": 20
    })
    
    return result

# Usage
trip_plan = plan_complete_trip("Barcelona", 5, "mid-range")
print(trip_plan)
```

### Workflow 2: Location-Specific Recommendations

```python
from api.perplexity_tools import search_local_travel_info

def get_local_recommendations(country_code, interest):
    """Get local recommendations based on user interest."""
    
    interest_queries = {
        "food": "best local restaurants and street food",
        "culture": "museums, galleries, and cultural sites",
        "nature": "hiking trails, parks, and natural attractions",
        "nightlife": "bars, clubs, and entertainment venues",
        "shopping": "local markets and shopping districts"
    }
    
    query = interest_queries.get(interest, "local attractions and activities")
    
    result = search_local_travel_info.invoke({
        "query": query,
        "country_code": country_code,
        "max_results": 10
    })
    
    return result

# Usage
recommendations = get_local_recommendations("JP", "food")
print(recommendations)
```

### Workflow 3: Real-Time Travel Safety Check

```python
from api.perplexity_tools import search_travel_destinations

def check_travel_safety(destination):
    """Check current travel safety and restrictions."""
    
    result = search_travel_destinations.invoke({
        "query": f"current travel restrictions safety guidelines {destination} 2024",
        "max_results": 5
    })
    
    return result

# Usage
safety_info = check_travel_safety("Thailand")
print(safety_info)
```

## Integration with Expedia Agent

Combine Perplexity search with Expedia booking:

```python
from api.expedia_agent.expedia_agent_tools import search_flights, search_hotels
from api.perplexity_tools import search_travel_destinations, search_local_travel_info

class TravelPlanningAgent:
    """Combined agent for research and booking."""
    
    def research_and_book(self, destination, dates, budget):
        # Step 1: Research with Perplexity
        research = search_travel_destinations.invoke({
            "query": f"best areas to stay in {destination}",
            "max_results": 5
        })
        
        # Step 2: Get local insights
        local_info = search_local_travel_info.invoke({
            "query": "top rated neighborhoods",
            "country_code": self._get_country_code(destination),
            "max_results": 5
        })
        
        # Step 3: Search and book with Expedia
        hotels = search_hotels(destination, dates)
        
        return {
            "research": research,
            "local_insights": local_info,
            "hotel_options": hotels
        }
```

## API Endpoint Example

Create a FastAPI endpoint for travel suggestions:

```python
# In main.py or a new routes file

from fastapi import APIRouter
from pydantic import BaseModel
from api.perplexity_tools import search_travel_destinations

router = APIRouter()

class TravelQuery(BaseModel):
    query: str
    max_results: int = 5
    country: str | None = None

@router.post("/api/travel/search")
async def search_travel(request: TravelQuery):
    """Search for travel information using Perplexity."""
    
    result = search_travel_destinations.invoke({
        "query": request.query,
        "max_results": request.max_results,
        "country": request.country
    })
    
    return {
        "status": "success",
        "data": result
    }

# Add to your FastAPI app
# app.include_router(router)
```

Test the endpoint:

```bash
curl -X POST http://localhost:8000/api/travel/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "best beaches in Thailand",
    "max_results": 5
  }'
```

## Caching Strategy

Implement caching to reduce API calls and costs:

```python
from functools import lru_cache
import hashlib
import json

@lru_cache(maxsize=100)
def cached_travel_search(query_hash: str):
    """Cache search results to reduce API calls."""
    # This is called by the main function with a hash
    pass

def search_with_cache(query, max_results=5, country=None):
    """Wrapper that caches Perplexity search results."""
    
    # Create cache key
    cache_key = hashlib.md5(
        json.dumps({
            "query": query,
            "max_results": max_results,
            "country": country
        }).encode()
    ).hexdigest()
    
    # Try to get from cache
    cached = cached_travel_search(cache_key)
    if cached:
        return cached
    
    # If not in cache, fetch and cache
    result = search_travel_destinations.invoke({
        "query": query,
        "max_results": max_results,
        "country": country
    })
    
    return result
```

## Error Handling

Implement robust error handling:

```python
from api.perplexity_tools import search_travel_destinations

def safe_travel_search(query, fallback_message="Unable to fetch travel information"):
    """Safely search with error handling."""
    
    try:
        result = search_travel_destinations.invoke({
            "query": query,
            "max_results": 5
        })
        
        # Check if tool is unavailable
        if "not available" in result:
            return {
                "status": "error",
                "message": "Perplexity API not configured",
                "data": None
            }
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": fallback_message,
            "error": str(e),
            "data": None
        }
```

## Monitoring and Analytics

Track usage of Perplexity tools:

```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def track_search(query, tool_name, result_count):
    """Track search usage for analytics."""
    
    logger.info(
        f"Perplexity Search - Tool: {tool_name}, "
        f"Query: {query}, Results: {result_count}, "
        f"Timestamp: {datetime.now().isoformat()}"
    )

# Use in your tools
def monitored_search(query):
    result = search_travel_destinations.invoke({
        "query": query,
        "max_results": 5
    })
    
    # Extract result count from response
    result_count = len(result.split('\n')) if result else 0
    track_search(query, "search_travel_destinations", result_count)
    
    return result
```

## Best Practices

1. **Combine Tools**: Use Perplexity for research, then Expedia tools for booking
2. **Cache Results**: Implement caching for frequently requested destinations
3. **Rate Limiting**: Monitor API usage and implement rate limiting
4. **Error Recovery**: Always provide fallback responses when API is unavailable
5. **User Context**: Use country codes based on user's location when available
6. **Query Optimization**: Make queries specific and relevant
7. **Result Filtering**: Post-process results to extract most relevant information

## Testing

Test your integration:

```bash
# Run unit tests
pytest api/test_perplexity_tools.py -v

# Run integration tests (requires API key)
pytest api/test_perplexity_tools.py --run-integration -v

# Test with examples
python api/example_perplexity_usage.py
```

## Troubleshooting

**Issue**: Tools not available in agent
- **Check**: Ensure `PERPLEXITY_API_KEY` is set in `.env`
- **Check**: Run `uv pip install perplexity`
- **Check**: Import using `from api.tools import get_all_tools`

**Issue**: Empty results
- **Solution**: Make queries more specific
- **Solution**: Try adding country filter
- **Solution**: Check API key validity

**Issue**: Rate limit errors
- **Solution**: Implement caching
- **Solution**: Add delays between requests
- **Solution**: Reduce `max_results` parameter

## Next Steps

1. Test the tools with example queries
2. Integrate into your specific agent architecture
3. Implement caching and error handling
4. Create custom workflows for your use case
5. Monitor usage and optimize based on patterns

For more details, see:
- [Perplexity Tools README](./PERPLEXITY_TOOLS_README.md)
- [Test Examples](./test_perplexity_tools.py)
- [Usage Examples](./example_perplexity_usage.py)

