# Group Chat Agent Tools

## Overview

Group chat agents now have access to two powerful tools that enhance their ability to create personalized travel plans:

1. **HyperSpell Memory Search** - User-specific memory retrieval
2. **Perplexity Travel Search** - Real-time travel information lookup

These tools enable agents to:
- Recall specific user preferences and past experiences
- Research current travel options and destinations
- Make data-driven decisions during group deliberations
- Provide accurate, up-to-date travel recommendations

## Tools

### 1. HyperSpell Memory Search

**Tool Name:** `search_{user_name}_memories`

Each agent gets a personalized version of this tool scoped to their user's memories.

**Purpose:**
- Search through the user's onboarding conversation history
- Retrieve stored preferences, constraints, and experiences
- Recall specific details that might not be in the UserProfile model

**Usage Example:**
```python
# Agent for "Alice" automatically gets:
search_alice_memories(query="dietary restrictions")
# Returns: "Alice mentioned she's vegetarian and allergic to shellfish"

search_alice_memories(query="previous hotel experiences")  
# Returns: "Alice enjoyed boutique hotels in Paris, didn't like large chain hotels"
```

**When Agents Use It:**
- To recall specific user constraints not in structured preferences
- When discussing options that might relate to past experiences
- To validate if a suggestion aligns with user's history

### 2. Perplexity Travel Search

**Tool Name:** `search_travel_info`

A shared tool available to all agents for researching travel information.

**Purpose:**
- Look up current travel information
- Research destinations, hotels, activities
- Validate travel suggestions with real-world data
- Get up-to-date travel tips and recommendations

**Usage Example:**
```python
search_travel_info(
    query="best family-friendly hotels in Tokyo",
    max_results=5
)
# Returns: Search results with hotel names, URLs, ratings, and descriptions

search_travel_info(
    query="visa requirements for US citizens visiting Japan"
)
# Returns: Current visa information and travel requirements
```

**When Agents Use It:**
- To research destination options during initial proposals
- To validate hotel or flight suggestions
- To answer specific questions about travel logistics
- To compare options when finding compromises

## Integration

### Automatic Tool Assignment

Tools are automatically assigned when the `GroupChatOrchestrator` is initialized:

```python
from api.group_chat.orchestrator import GroupChatOrchestrator
from api.group_chat.models import UserProfile

users = [
    UserProfile(user_id="user_001", user_name="Alice", ...),
    UserProfile(user_id="user_002", user_name="Bob", ...)
]

orchestrator = GroupChatOrchestrator(users=users)
# Output:
# 🔧 Created 2 tools for Alice
# 🔧 Created 2 tools for Bob
```

Each agent receives:
- Their personalized HyperSpell memory search tool
- The shared Perplexity travel search tool

### Tool Execution Flow

When an agent decides to use a tool:

1. **Agent generates response** with tool call
2. **Orchestrator intercepts** tool calls
3. **Tools are executed** with provided arguments
4. **Results are collected** and formatted
5. **Agent regenerates message** incorporating tool results
6. **Final message** is added to group chat

```
Agent: "Let me check Alice's dietary restrictions..."
  🔧 Calling: search_alice_memories
  Result: "Alice is vegetarian with shellfish allergy"
Agent: "Based on Alice's dietary needs (vegetarian), I suggest..."
```

## Configuration

### Required Environment Variables

```bash
# For HyperSpell memory search
HYPERSPELL_API_KEY=your-hyperspell-key-here

# For Perplexity travel search
PERPLEXITY_API_KEY=your-perplexity-key-here
```

Both keys are optional - tools will only be available if configured.

### Checking Tool Availability

```python
from api.tools import get_group_chat_tools

tools = get_group_chat_tools("user_001", "Alice")
print(f"Alice has {len(tools)} tools available")

# Expected output (with both APIs configured):
# 🔧 Created 2 tools for Alice
```

## Examples

### Example 1: Agent Using Memory Search

**Scenario:** Agent needs to recall Alice's hotel preferences

```
System: "Provide feedback on the current hotel suggestion"

Agent thinks: "I should check Alice's hotel preferences"
🔧 Calling search_alice_memories: "hotel preferences and experiences"

Tool Result:
"Alice prefers boutique hotels with local character. She mentioned 
disliking large chain hotels during her Paris trip. Prefers walkable
neighborhoods over resort areas."

Agent message: "While this resort looks nice, Alice prefers boutique 
hotels in walkable neighborhoods. Could we consider options in the 
historic district instead?"
```

### Example 2: Agent Using Travel Search

**Scenario:** Agent wants to research destination options

```
System: "Create initial travel plan proposal"

Agent thinks: "Let me research family-friendly activities in Orlando"
🔧 Calling search_travel_info: "family-friendly activities Orlando Florida"

Tool Result:
"1. Universal Orlando Resort - Theme parks with rides for all ages...
 2. Disney World - Magic Kingdom ideal for young children...
 3. Kennedy Space Center - Educational and engaging for teens..."

Agent message: "I propose Orlando for our family trip. It offers diverse
activities from theme parks to educational experiences at Kennedy Space
Center, fitting our budget range of $2000-3000 per person."
```

### Example 3: Multi-Tool Usage

```
Agent 1: "Let me verify Alice's budget and research options"
🔧 Calling search_alice_memories: "budget constraints previous trips"
🔧 Calling search_travel_info: "affordable hotels Tokyo under $150"

Tool Results:
Memory: "Alice's comfortable budget is $2000 per person for a week"
Search: "Found 5 hotels: 1. Hotel Gracery Shinjuku ($120/night)..."

Agent message: "Based on Alice's $2000 budget and research, I found 
Hotel Gracery in Shinjuku at $120/night, leaving room for activities."
```

## Agent Behavior

### Tool Usage Guidelines

Agents are instructed to use tools strategically:

**DO use tools when:**
- Specific user details are needed that aren't in the profile
- Travel options need real-world validation
- Current information would improve decision quality
- Resolving disagreements with factual data

**DON'T overuse tools:**
- For information already in the user profile
- For general knowledge that doesn't need validation
- Multiple times for the same information
- When it would slow down conversation flow

### System Prompt Excerpt

```
AVAILABLE TOOLS:
You have access to tools for:
1. Searching {user_name}'s personal travel memories and preferences
2. Searching for up-to-date travel information

Use these tools when:
- You need to recall specific details about {user_name}'s past experiences
- You want to research travel options, destinations, or current information
- You need to validate or enhance suggestions with real-world data

Don't overuse tools - only use when information would genuinely help.
```

## Testing

### Run Test Suite

```bash
python test_group_chat_tools.py
```

**Tests include:**
1. Tool creation for sample users
2. HyperSpell memory search functionality
3. Perplexity travel search functionality
4. Orchestrator integration verification

### Expected Output

```
==================================================
GROUP CHAT TOOLS TEST SUITE
==================================================

Testing Group Chat Tools Creation
--------------------------------------------------
Created 2 tools for Alice:
  ✓ search_alice_memories
  ✓ search_travel_info

Testing HyperSpell Tool
--------------------------------------------------
✅ HyperSpell tool test passed!

Testing Perplexity Tool
--------------------------------------------------
✅ Perplexity tool test passed!

Testing Orchestrator Integration
--------------------------------------------------
✅ Orchestrator created successfully
   Participants: ['Alice', 'Bob']
   Base tools: 4
   Alice's tools: 2
     - search_alice_memories
     - search_travel_info
   Bob's tools: 2
     - search_bob_memories
     - search_travel_info
```

## Technical Details

### Tool Creation

**HyperSpell Tool:**
```python
def create_user_hyperspell_tool(user_id: str, user_name: str):
    """Creates a tool scoped to user's memory collection"""
    @tool
    def search_user_memories(query: str) -> str:
        memories = hyperspell_client.memories.search(
            query=query,
            collection=user_id  # Scoped to user
        )
        # Format and return top 5 results
```

**Perplexity Tool:**
```python
@tool
def search_travel_info(query: str, max_results: int = 5) -> str:
    """Searches travel info via Perplexity API"""
    search_result = perplexity_client.search.create(
        query=query,
        max_results=max_results
    )
    # Format and return search results
```

### Tool Binding

```python
# In orchestrator agent node:
user_tools = self.user_tools.get(user.user_id, [])

if user_tools:
    llm_with_tools = self.llm.bind_tools(user_tools)
else:
    llm_with_tools = self.llm

response = llm_with_tools.invoke([...])
```

### Error Handling

Both tools include comprehensive error handling:

```python
# HyperSpell
if not hyperspell_client:
    return "HyperSpell not available"

try:
    memories = hyperspell_client.memories.search(...)
except Exception as e:
    return f"Error searching memories: {str(e)}"

# Perplexity  
if not perplexity_client:
    return "Perplexity not configured"

try:
    results = perplexity_client.search.create(...)
except Exception as e:
    return f"Error performing search: {str(e)}"
```

## Performance Considerations

### Memory Search
- Searches user-specific collections (faster than global search)
- Returns top 5 results only (reduces token usage)
- Includes relevance scores for quality assessment

### Travel Search
- Default limit of 5 results (configurable up to 10)
- Images disabled to reduce response size
- Snippets enabled for quick scanning

### Tool Call Overhead
- Tool execution adds ~2-5 seconds per call
- Agent regeneration adds ~1-2 seconds
- Total overhead: ~3-7 seconds when tools are used
- Acceptable for deliberation quality improvement

## Monitoring

### Log Output

Tool usage is logged for monitoring:

```
🔧 Alice's agent is using tools...
   - Calling: search_alice_memories
   - Calling: search_travel_info
   
🔧 Bob's agent is using tools...
   - Calling: search_bob_memories
```

### Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Potential improvements:
- Cache frequently searched memories
- Parallel tool execution for speed
- Tool usage analytics and optimization
- Additional search filters (location, date range)
- Integration with more data sources
- Custom tool per user type (business vs. leisure)

## Troubleshooting

### Tools Not Available

**Problem:** Tools show as 0 for users

**Solution:** Check API keys are set:
```bash
echo $HYPERSPELL_API_KEY
echo $PERPLEXITY_API_KEY
```

### Memory Search Returns No Results

**Problem:** `search_user_memories` finds nothing

**Possible causes:**
- User hasn't completed onboarding
- Memories not stored in correct collection
- Query doesn't match stored content

**Solution:** Check memory storage:
```python
memories = hyperspell_client.memories.list(collection=user_id)
```

### Perplexity Rate Limits

**Problem:** "Rate limit exceeded" errors

**Solution:** 
- Add exponential backoff
- Reduce search frequency
- Upgrade Perplexity plan

### Tool Calls Not Executing

**Problem:** Agent mentions tools but doesn't use them

**Possible causes:**
- LLM doesn't support tool calling (use GPT-4 or Claude)
- Tools not properly bound to LLM
- System prompt doesn't encourage tool use

**Solution:** Verify LLM model and tool binding

## Summary

The group chat agents now have powerful tools for:
- 🧠 **Personalized Context** via HyperSpell memory search
- 🌍 **Real-Time Research** via Perplexity travel search

These tools enable agents to:
- Make more informed decisions
- Recall user-specific details accurately
- Validate suggestions with current data
- Provide better travel recommendations

Result: **Higher quality travel plans that better match user needs**

