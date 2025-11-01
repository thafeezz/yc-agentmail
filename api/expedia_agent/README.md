# Expedia Agent Module

Comprehensive browser automation and booking tools for Expedia travel services.

## Structure

```
expedia_agent/
├── __init__.py                      # Package exports
├── README.md                        # This file
├── agent_browser.py                 # Main ExpediaAgent class
├── expedia_prebuilt_actions.py      # High-level prebuilt actions
├── expedia_flight_tools.py          # Flight-specific tools
├── expedia_hotel_prebuilt_actions.py # Hotel-specific tools
└── test_prebuilt_actions.py         # Test suite
```

## Quick Start

```python
from expedia_agent import ExpediaAgent

# Initialize agent
agent = ExpediaAgent(llm_model="claude-sonnet-4")

# Or with observability
from expedia_agent import initialize_observability
initialize_observability()
agent = ExpediaAgent()

# Book flights and hotels
result = agent.book_parallel(
    email="user@example.com",
    password="password",
    origin="LAX",
    destination="JFK",
    departure_date="2025-12-15",
    return_date="2025-12-20",
    hotel_location="Manhattan, New York",
    check_in="2025-12-15",
    check_out="2025-12-20",
    first_name="John",
    last_name="Doe",
    phone="4155551234",
    card_number="4111111111111111",
    cardholder_name="John Doe",
    expiration_month="12",
    expiration_year="2027",
    cvv="123",
    billing_address={
        "street": "123 Main St",
        "city": "San Francisco",
        "state": "CA",
        "zip": "94102",
        "country": "USA"
    }
)
```

## Components

### ExpediaAgent (`agent_browser.py`)
Main browser automation agent for:
- Account management (login, signup, email verification)
- Flight search, selection, and booking
- Hotel search, selection, and booking
- Traveler information filling
- Payment processing
- Parallel/sequential booking modes
- Observability integration (Laminar)

### Prebuilt Actions (`expedia_prebuilt_actions.py`)
High-level browser-use compatible actions:
- Sign in / Sign up
- Flight search and selection
- Hotel search and selection
- Traveler information filling
- Payment form filling
- Complete booking flows

### Flight Tools (`expedia_flight_tools.py`)
Flight-specific selectors and operations:
- Flight search navigation
- Price sorting
- Fare card selection
- Outbound/return flight handling
- Basic/main/first fare selection

### Hotel Actions (`expedia_hotel_prebuilt_actions.py`)
Hotel-specific operations:
- Hotel search with URL parameters
- Hotel details opening
- Room selection and reservation
- Guest information filling
- Hotel payment processing
- Protection decline handling

## Usage Modes

### 1. Combined Booking (Parallel)
```python
result = agent.book_parallel(...)
# Faster: flights and hotels booked simultaneously
```

### 2. Sequential Package Booking
```python
result = agent.book_flight_and_hotel_package(...)
# Single flow: flight selection → hotel selection → payment
```

### 3. Flight-Only Booking
```python
agent.search_flights(...)
agent.select_and_book_flight(...)
agent.fill_traveler_info(...)
agent.fill_payment_info(...)
```

### 4. Hotel-Only Booking
```python
agent.search_hotels(...)
agent.select_and_book_hotel(...)
agent.fill_traveler_info(...)
agent.fill_payment_info(...)
```

### 5. AI-Assisted with Tools
```python
result = await agent.book_with_ai_agent(...)
# AI agent intelligently uses custom Playwright tools
```

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...        # Claude LLM
OPENAI_API_KEY=sk-...                # Or OpenAI GPT
BROWSER_USE_API_KEY=bu_...           # Browser Use cloud API

# Optional
LMNR_PROJECT_API_KEY=...             # Laminar observability
GROQ_API_KEY=...                     # Groq models support
```

## Key Features

- ✅ Hybrid mode: Playwright speed + AI intelligence
- ✅ Parallel booking for faster execution
- ✅ Multiple LLM support (Claude, GPT, Groq)
- ✅ Cloud browser support via Browser Use
- ✅ Observability integration (Laminar)
- ✅ Flexible date format parsing
- ✅ Advanced flight/hotel filtering
- ✅ Complete error handling

## Testing

```bash
# Run prebuilt actions tests
python3 test_prebuilt_actions.py

# Test with mock agent (no real bookings)
python3 expedia_agent/test_prebuilt_actions.py
```

## Performance

- **AI-Only Mode**: ~5-10 minutes per booking
- **Hybrid Mode** (Playwright + AI): ~1-2 minutes per booking
- **Parallel Booking**: Flight + Hotel simultaneously for ~3-5 minutes total

## Integration

This module is used by:
- `agent_service.py`: FastAPI endpoints for plan-driven booking
- `test_api_plan_booking.py`: Integration test suite
- Group Chat API: Expedia booking from approved travel plans

## Documentation

For complete documentation, see:
- `../API_SETUP.md` - API usage guide
- `../IMPLEMENTATION_SUMMARY.md` - Technical details
- `../EXAMPLE_WORKFLOW.md` - Step-by-step examples

---

**Version:** 1.0.0  
**Status:** Production Ready ✅
