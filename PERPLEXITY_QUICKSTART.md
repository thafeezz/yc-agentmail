# Perplexity Tools - Quick Start Guide

Get started with Perplexity travel search tools in 3 minutes!

## 1️⃣ Setup (30 seconds)

### Get API Key
1. Go to https://www.perplexity.ai/settings/api
2. Sign up or log in
3. Create a new API key

### Add to Environment
```bash
# Add to your .env file
PERPLEXITY_API_KEY=pplx-your-key-here
```

### Install Package
```bash
uv pip install perplexity
```

## 2️⃣ Basic Usage (1 minute)

### Simple Travel Search
```python
from api.perplexity_tools import search_travel_destinations

result = search_travel_destinations.invoke({
    "query": "best beaches in Thailand",
    "max_results": 5
})

print(result)
```

### Multi-Topic Search
```python
from api.perplexity_tools import search_multiple_travel_topics

result = search_multiple_travel_topics.invoke({
    "queries": [
        "hotels in Paris",
        "restaurants in Paris",
        "things to do in Paris"
    ],
    "max_results": 10
})

print(result)
```

### Location-Specific Search
```python
from api.perplexity_tools import search_local_travel_info

result = search_local_travel_info.invoke({
    "query": "local food markets",
    "country_code": "JP",  # Japan
    "max_results": 5
})

print(result)
```

## 3️⃣ Use with Your Agent (1 minute)

### Option A: Get All Tools
```python
from api.tools import get_all_tools

# Automatically includes Perplexity tools if API key is set
all_tools = get_all_tools()

# Use with your agent
from langchain.agents import AgentExecutor
agent_executor = AgentExecutor(agent=your_agent, tools=all_tools)
```

### Option B: Import Specific Tools
```python
from api.perplexity_tools import (
    search_travel_destinations,
    search_multiple_travel_topics,
    search_local_travel_info
)

tools = [search_travel_destinations, search_multiple_travel_topics]
# Use these tools with your agent
```

## 4️⃣ Test It (30 seconds)

### Run Tests
```bash
# Unit tests (no API key needed)
pytest api/test_perplexity_tools.py -v

# Integration tests (needs API key)
pytest api/test_perplexity_tools.py --run-integration -v
```

### Try Examples
```bash
python api/example_perplexity_usage.py
```

## 📝 Common Country Codes

Quick reference for location-based searches:

```python
US = United States     FR = France          JP = Japan
GB = United Kingdom    DE = Germany         AU = Australia
CA = Canada           IT = Italy           TH = Thailand
ES = Spain            CH = Switzerland     MX = Mexico
```

## 🎯 Example Use Cases

### Trip Planning
```python
search_travel_destinations.invoke({
    "query": "7-day Italy itinerary for families",
    "max_results": 5
})
```

### Budget Travel
```python
search_travel_destinations.invoke({
    "query": "cheapest European cities to visit 2024",
    "max_results": 10
})
```

### Safety Check
```python
search_travel_destinations.invoke({
    "query": "current travel restrictions Thailand safety guidelines",
    "max_results": 5
})
```

### Local Discoveries
```python
search_local_travel_info.invoke({
    "query": "hidden gem restaurants off the beaten path",
    "country_code": "IT",
    "max_results": 5
})
```

## 💡 Pro Tips

1. **Be specific** - "family-friendly hotels in Tokyo with pools" beats "Tokyo hotels"
2. **Use country codes** - Get more relevant local results
3. **Batch queries** - Use `search_multiple_travel_topics` for related searches
4. **Cache results** - Save on API calls for popular destinations
5. **Limit results** - Start with 5, increase if needed

## 🚨 Troubleshooting

**"Tool not available"**
→ Check `.env` has `PERPLEXITY_API_KEY=your_key`

**"Import error"**
→ Run `uv pip install perplexity`

**Empty results**
→ Make query more specific or add country filter

**Rate limit**
→ Add delay between calls or implement caching

## 📚 Full Documentation

- **Detailed Guide**: `api/PERPLEXITY_TOOLS_README.md`
- **Integration Help**: `api/PERPLEXITY_INTEGRATION_GUIDE.md`
- **Complete Setup**: `PERPLEXITY_SETUP_COMPLETE.md`

## ✅ You're Ready!

That's it! You now have powerful travel search capabilities integrated into your agent.

**Next steps:**
1. Set your API key ✅
2. Try the examples ✅
3. Integrate into your agent ✅
4. Build something awesome! 🚀

---

**Questions?** Check the full documentation in `api/PERPLEXITY_TOOLS_README.md`

