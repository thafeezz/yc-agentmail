# Perplexity Travel Search Tools - Setup Complete ✅

The Perplexity travel search tools have been successfully integrated into your YC AgentMail project!

## 📁 Files Created/Modified

### New Files
1. **`api/perplexity_tools.py`** - Main tool implementation
   - 3 LangChain tools for travel search
   - `PerplexitySearchTool` wrapper class
   - Error handling and result formatting

2. **`api/test_perplexity_tools.py`** - Comprehensive test suite
   - Unit tests with mocks
   - Integration tests (requires API key)
   - Usage examples

3. **`api/example_perplexity_usage.py`** - Interactive examples
   - 8 real-world usage scenarios
   - Interactive menu for testing

4. **`api/PERPLEXITY_TOOLS_README.md`** - Comprehensive documentation
   - Tool descriptions and parameters
   - Code examples
   - Best practices

5. **`api/PERPLEXITY_INTEGRATION_GUIDE.md`** - Integration guide
   - How to integrate with existing agents
   - Workflow examples
   - API endpoint examples

### Modified Files
1. **`api/cfg.py`** - Added `perplexity_api_key` setting
2. **`api/clients.py`** - Initialize Perplexity client
3. **`api/tools.py`** - Export Perplexity tools with `get_all_tools()`
4. **`pyproject.toml`** - Added `perplexity>=0.1.0` dependency
5. **`env.example`** - Added Perplexity API key template

## 🛠️ Available Tools

### 1. `search_travel_destinations`
General travel information and destination search.

```python
from api.perplexity_tools import search_travel_destinations

result = search_travel_destinations.invoke({
    "query": "best beaches in Thailand",
    "max_results": 5,
    "country": "TH"  # Optional
})
```

### 2. `search_multiple_travel_topics`
Multi-query search for comprehensive trip planning.

```python
from api.perplexity_tools import search_multiple_travel_topics

result = search_multiple_travel_topics.invoke({
    "queries": [
        "hotels in Barcelona",
        "restaurants in Barcelona",
        "things to do in Barcelona"
    ],
    "max_results": 15
})
```

### 3. `search_local_travel_info`
Location-specific travel information by country.

```python
from api.perplexity_tools import search_local_travel_info

result = search_local_travel_info.invoke({
    "query": "hidden gem restaurants",
    "country_code": "JP",
    "max_results": 5
})
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
uv pip install perplexity
```

### 2. Set API Key
Add to your `.env` file:
```bash
PERPLEXITY_API_KEY=your_api_key_here
```

Get your API key from: https://www.perplexity.ai/settings/api

### 3. Use in Your Agent
```python
from api.tools import get_all_tools

# Get all tools including Perplexity tools
all_tools = get_all_tools()

# Use with your LangChain agent
# agent_executor = AgentExecutor(agent=agent, tools=all_tools)
```

## 📖 Documentation

- **Main README**: `api/PERPLEXITY_TOOLS_README.md`
  - Detailed tool documentation
  - Parameter descriptions
  - Code examples
  - Country codes reference

- **Integration Guide**: `api/PERPLEXITY_INTEGRATION_GUIDE.md`
  - How to integrate with existing agents
  - Workflow examples
  - Error handling patterns
  - Caching strategies

## 🧪 Testing

### Run Unit Tests
```bash
pytest api/test_perplexity_tools.py -v
```

### Run Integration Tests (requires API key)
```bash
pytest api/test_perplexity_tools.py --run-integration -v
```

### Try Interactive Examples
```bash
python api/example_perplexity_usage.py
```

## 🎯 Use Cases

1. **Travel Planning**
   - Destination research
   - Hotel and restaurant recommendations
   - Itinerary creation

2. **Local Discovery**
   - Hidden gems and local favorites
   - Cultural attractions
   - Regional events

3. **Safety & Logistics**
   - Travel restrictions
   - Safety guidelines
   - Transportation options

4. **Budget Travel**
   - Cost-effective destinations
   - Budget accommodations
   - Free activities

## 🔗 Integration Points

### With Group Chat Agent
```python
from api.group_chat.orchestrator import GroupChatOrchestrator
from api.perplexity_tools import search_travel_destinations

orchestrator = GroupChatOrchestrator(
    additional_tools=[search_travel_destinations]
)
```

### With Expedia Agent
Combine Perplexity research with Expedia booking for end-to-end travel planning.

### As API Endpoint
Create FastAPI endpoints for travel search functionality.

## 📊 Features

✅ **Real-time travel information** - Up-to-date data from the web
✅ **Location-based search** - Filter by country using ISO codes
✅ **Multi-query support** - Search multiple topics at once
✅ **Rich results** - Titles, URLs, snippets, dates, and images
✅ **Error handling** - Graceful handling of API issues
✅ **LangChain compatible** - Works with LangChain agents
✅ **Type safe** - Full type hints and Pydantic models
✅ **Well tested** - Comprehensive test suite
✅ **Documented** - Extensive documentation and examples

## 🔧 Configuration

All configuration is handled through environment variables:

```bash
# Required
PERPLEXITY_API_KEY=your_key_here

# Optional (from existing config)
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
AGENTMAIL_API_KEY=your_agentmail_key
HYPERSPELL_API_KEY=your_hyperspell_key
```

## 📝 Example Queries

Here are some example queries to try:

```python
# Destination planning
"best time to visit Japan for cherry blossoms"
"family-friendly hotels in Paris with pools"
"budget backpacking Southeast Asia 2024"

# Local exploration
"hidden gem restaurants in Tokyo"
"free museums and attractions in London"
"best hiking trails near Vancouver"

# Safety and logistics
"current travel restrictions Thailand 2024"
"safest neighborhoods in Barcelona for tourists"
"public transportation passes for tourists Rome"

# Seasonal travel
"best winter destinations Europe Christmas markets"
"summer beach destinations under $1000"
"autumn foliage viewing spots New England"
```

## 🎓 Learning Resources

1. **Start with examples**: Run `python api/example_perplexity_usage.py`
2. **Read the docs**: Check `api/PERPLEXITY_TOOLS_README.md`
3. **Study tests**: Look at `api/test_perplexity_tools.py` for usage patterns
4. **Integration guide**: Follow `api/PERPLEXITY_INTEGRATION_GUIDE.md`

## ⚡ Performance Tips

1. **Cache results** - Implement caching for frequently searched destinations
2. **Batch queries** - Use `search_multiple_travel_topics` for related searches
3. **Limit results** - Request only what you need (default: 5, max: 20)
4. **Use country filters** - More specific searches return better results faster

## 🐛 Troubleshooting

**Tools not working?**
1. Check `PERPLEXITY_API_KEY` is set in `.env`
2. Run `uv pip install perplexity`
3. Restart your application

**Empty results?**
1. Make queries more specific
2. Try adding a country filter
3. Increase `max_results`

**Rate limit errors?**
1. Implement caching
2. Add delays between requests
3. Reduce request frequency

## 📚 Next Steps

1. ✅ Set your `PERPLEXITY_API_KEY` in `.env`
2. ✅ Install dependencies: `uv pip install perplexity`
3. ✅ Run tests: `pytest api/test_perplexity_tools.py -v`
4. ✅ Try examples: `python api/example_perplexity_usage.py`
5. ✅ Integrate into your agent architecture
6. ✅ Build awesome travel planning features!

## 🙏 Support

- **Perplexity API Docs**: https://docs.perplexity.ai/
- **Get API Key**: https://www.perplexity.ai/settings/api
- **Tool Documentation**: `api/PERPLEXITY_TOOLS_README.md`
- **Integration Help**: `api/PERPLEXITY_INTEGRATION_GUIDE.md`

---

**Status**: ✅ Ready to use
**Version**: 1.0.0
**Last Updated**: November 1, 2025

Happy building! 🚀✈️🌍

