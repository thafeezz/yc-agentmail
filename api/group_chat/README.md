# Group Chat Agent System

A LangGraph-based multi-agent system where user agents collaborate to create travel plans through turn-based group chat.

## Overview

This system orchestrates multiple AI agents, each representing a different user with their own preferences and memories. The agents engage in a structured group chat to negotiate and create a collaborative travel plan that balances everyone's needs.

## Architecture

### Core Components

1. **Pydantic Models** (`models.py`)
   - Type-safe data structures for all entities
   - User profiles, preferences, and memories
   - Travel plans with dates, flights, hotels, and budgets
   - API request/response models

2. **Database Layer** (`database.py`)
   - SQLAlchemy models for persistent storage
   - CRUD operations for users, memories, and sessions
   - SQLite by default (configurable to PostgreSQL/MySQL)

3. **LangGraph Orchestrator** (`orchestrator.py`)
   - StateGraph-based workflow
   - Supervisor pattern for agent coordination
   - Sequential turn-taking in input order
   - Master planner for final synthesis

4. **FastAPI Router** (`api.py`)
   - REST endpoints for session management
   - Start, reject, approve, and status endpoints
   - Integration with main FastAPI app

## Key Features

### Multi-Agent Collaboration
- Each agent advocates for their user's preferences
- Structured turn-taking (sequential order based on input)
- Configurable messages per volley (default: 10)

### Memory Integration
- User memories inform agent behavior
- Types: preferences, interactions, constraints
- Relevance scoring for context retrieval

### Plan Synthesis
- Master LLM synthesizes final plans
- Balances competing preferences
- Documents compromises made

### Rejection & Iteration
- Users can reject plans with feedback
- Feedback added to chat context
- New volley starts with adjusted perspective

## Workflow

```mermaid
graph TD
    A[Start Session] --> B[Initialize Agents]
    B --> C[Run Volley]
    C --> D[Agent 1 Speaks]
    D --> E[Agent 2 Speaks]
    E --> F[Agent N Speaks]
    F --> G{All Messages Sent?}
    G -->|No| D
    G -->|Yes| H[Master Planner]
    H --> I[Generate Final Plan]
    I --> J{Plan Approved?}
    J -->|Yes| K[Complete]
    J -->|No| L[Add Feedback]
    L --> C
```

## Usage

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export ANTHROPIC_API_KEY=your_key_here
# or
export OPENAI_API_KEY=your_key_here
```

### 3. Create Sample Users

```python
from group_chat_agent.database import get_session, create_user, create_memory

session = get_session()

# Create a user
user = create_user(
    session,
    user_id="user_001",
    user_name="Alice",
    email="alice@example.com",
    preferences={
        "budget_range": (1000, 2000),
        "preferred_destinations": ["mountains"],
        "travel_style": "adventure",
        "dietary_restrictions": ["vegetarian"],
        "mobility_requirements": []
    }
)

# Add a memory
create_memory(
    session,
    memory_id="mem_001",
    user_id="user_001",
    content="Prefers morning flights and hiking activities",
    memory_type="preference",
    relevance_score=0.9
)

session.close()
```

### 4. Run via API

Start the FastAPI server:

```bash
python3 agent_service.py
```

Start a group chat:

```bash
curl -X POST "http://localhost:8000/group-chat/start" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": ["user_001", "user_002", "user_003"],
    "messages_per_volley": 10
  }'
```

### 5. Run Programmatically

```python
from group_chat_agent.database import get_session, load_user_profiles
from group_chat_agent.orchestrator import GroupChatOrchestrator

# Load users
session = get_session()
profiles = load_user_profiles(session, ["user_001", "user_002"])
session.close()

# Create orchestrator
orchestrator = GroupChatOrchestrator(
    users=profiles,
    messages_per_volley=10
)

# Run volley
result = orchestrator.run_volley()

# Access plan
if result.get('current_plan'):
    print(result['current_plan'])
```

## API Endpoints

### POST /group-chat/start
Start a new group chat session

**Request:**
```json
{
  "user_ids": ["user_001", "user_002"],
  "messages_per_volley": 10
}
```

**Response:**
```json
{
  "session_id": "session_abc123",
  "status": "completed",
  "current_volley": 1,
  "total_messages": 20,
  "participants": ["user_001", "user_002"],
  "current_plan": { ... }
}
```

### POST /group-chat/{session_id}/reject
Reject the current plan with feedback

**Request:**
```json
{
  "user_id": "user_001",
  "feedback": "Budget is too high"
}
```

### POST /group-chat/{session_id}/approve
Approve the final plan

### GET /group-chat/{session_id}/status
Get session status and current plan

### GET /group-chat/{session_id}/messages
Get all chat messages

## LangGraph Implementation Details

### State Schema

Uses `TypedDict` for optimal performance:

```python
class GroupChatState(TypedDict):
    messages: Annotated[List[Any], "add_messages"]
    current_volley: int
    messages_per_agent: int
    active_agent: Optional[str]
    agent_message_counts: Dict[str, int]
    current_agent_index: int
    total_turns: int
    current_plan: Optional[Dict[str, Any]]
    rejection_feedback: Optional[str]
    is_complete: bool
```

### Graph Structure

```python
builder = StateGraph(GroupChatState)

# Add nodes
builder.add_node("supervisor", supervisor_node)
builder.add_node("agent_user1", agent_1_node)
builder.add_node("agent_user2", agent_2_node)
builder.add_node("master_planner", master_planner_node)

# Define edges
builder.add_edge(START, "supervisor")
builder.add_edge("agent_user1", "supervisor")
builder.add_edge("agent_user2", "supervisor")
builder.add_edge("master_planner", END)
```

### Turn Management

Agents take turns sequentially in the order they were provided:

1. Supervisor tracks current agent index
2. Routes to next agent in sequence
3. Agent sends message and increments counter
4. Returns to supervisor
5. When all agents complete their turns, routes to master planner

## Configuration

### Database

Default: SQLite (`./group_chat_agent.db`)

To use PostgreSQL:
```bash
export DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### LLM Model

Supports Anthropic Claude and OpenAI:

```python
orchestrator = GroupChatOrchestrator(
    users=profiles,
    llm_model="claude-sonnet-4"  # or "gpt-4", "gpt-4-turbo", etc.
)
```

## Example Scenarios

### Scenario 1: Budget vs Luxury
- User A: Budget traveler ($1000-1500)
- User B: Luxury seeker ($4000-6000)
- **Result**: Compromised plan with mid-range options

### Scenario 2: Adventure vs Relaxation
- User A: Hiker, outdoor activities
- User B: Spa, poolside relaxation
- **Result**: Destination with both mountain access and resort amenities

### Scenario 3: Dietary Restrictions
- User A: Vegetarian
- User B: Gluten-free
- User C: No restrictions
- **Result**: Destination with diverse dining options

## Files

```
group_chat_agent/
├── __init__.py           # Package exports
├── models.py             # Pydantic models
├── database.py           # SQLAlchemy & CRUD
├── orchestrator.py       # LangGraph implementation
├── api.py                # FastAPI router
├── example.py            # Usage examples
└── README.md             # This file
```

## Future Enhancements

- [ ] Vector search for memory retrieval
- [ ] Parallel agent communication
- [ ] Real-time websocket updates
- [ ] Integration with Expedia booking agent
- [ ] Multi-language support
- [ ] Sentiment analysis for conflict detection
- [ ] Automated budget optimization

## License

MIT

## Contributing

See main project README for contribution guidelines.

