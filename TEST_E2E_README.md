# E2E Test: Group Chat to Expedia Booking

## Overview

This comprehensive end-to-end test validates the complete workflow from group chat deliberation through travel plan approval to final booking execution.

## Test Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    E2E Test Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Setup Phase                                                 │
│     ├── Create test users (Alice & Bob)                        │
│     ├── Complete onboarding data (credentials, payment, etc.)  │
│     └── Initialize database                                     │
│                                                                 │
│  2. Group Chat Phase                                            │
│     ├── POST /api/group-chat/start                            │
│     ├── Real LLM calls (OpenAI/Anthropic)                     │
│     ├── Agents deliberate (10 messages each)                   │
│     ├── Master planner synthesizes TravelPlan                  │
│     └── Plan sent via email (mocked)                           │
│                                                                 │
│  3. Approval Simulation                                         │
│     ├── Simulate webhook payloads                              │
│     ├── Update approval_state in database                      │
│     └── Track all_approved / any_rejected                      │
│                                                                 │
│  4. Booking Phase                                               │
│     ├── trigger_parallel_bookings()                            │
│     ├── Real ExpediaAgent with Browser Use Cloud               │
│     ├── Parallel execution (asyncio.gather)                    │
│     └── Booking confirmations sent (mocked)                    │
│                                                                 │
│  5. Verification                                                │
│     ├── Validate TravelPlan structure                          │
│     ├── Check approval states                                  │
│     ├── Verify booking results                                 │
│     └── Confirm emails sent                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Required Environment Variables

Create a `.env` file with the following keys:

```bash
# Required for real ExpediaAgent
BROWSER_USE_API_KEY=your_browser_use_api_key_here

# Required for group chat LLMs (choose one or both)
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional (will be mocked if not provided)
AGENTMAIL_API_KEY=your_agentmail_api_key_here
HYPERSPELL_API_KEY=your_hyperspell_api_key_here
```

### Python Dependencies

All dependencies should be installed via:
```bash
pip3 install -r requirements.txt
# OR
pip3 install -e .
```

## Running the Tests

### Run All E2E Tests

```bash
cd /Users/charleswright/yc-agentmail
python3 -m pytest test_e2e_group_chat_booking.py -v -s
```

### Run Specific Test

```bash
# Test 1: Full flow with approval
python3 -m pytest test_e2e_group_chat_booking.py::TestE2EGroupChatBooking::test_full_flow_with_approval -v -s

# Test 2: Rejection and new volley
python3 -m pytest test_e2e_group_chat_booking.py::TestE2EGroupChatBooking::test_rejection_and_new_volley -v -s

# Test 3: Parallel booking execution
python3 -m pytest test_e2e_group_chat_booking.py::TestE2EGroupChatBooking::test_parallel_booking_execution -v -s
```

### Run with Custom Timeout

These tests take a while due to real browser automation:

```bash
python3 -m pytest test_e2e_group_chat_booking.py -v -s --timeout=600
```

## Test Scenarios

### Test 1: Full Flow with Approval

**Duration:** ~5-8 minutes  
**What it tests:**
- Group chat initialization
- LLM-based agent deliberations
- TravelPlan generation and validation
- All users approve the plan
- Parallel booking execution with real browsers
- Booking confirmation delivery

**Expected outcome:** Complete booking flow succeeds for both users.

### Test 2: Rejection and New Volley

**Duration:** ~8-12 minutes  
**What it tests:**
- Initial plan generation
- One user rejects with feedback
- New deliberation round with feedback
- Updated plan generation
- Approval on second round

**Expected outcome:** System handles rejection gracefully and produces updated plan.

### Test 3: Parallel Booking Execution

**Duration:** ~2-5 minutes  
**What it tests:**
- Direct booking trigger with pre-approved plan
- Parallel execution timing
- Booking results for multiple users
- Confirmation email delivery

**Expected outcome:** Both bookings execute in parallel (not sequentially).

## What's Mocked vs Real

### Mocked Components
- **Email sending** (`send_plan_email`, `send_booking_confirmation`)
  - Returns fake message IDs
  - No actual network calls to AgentMail API
- **Webhook events**
  - Simulated by directly calling database functions
  - No actual HTTP webhook calls

### Real Components
- **GroupChatOrchestrator**
  - Real LLM calls to OpenAI or Anthropic
  - Actual agent deliberations
  - Real plan synthesis
- **ExpediaAgent**
  - Real browser automation via Browser Use Cloud
  - Actual Expedia website interactions
  - Real flight/hotel searches (no actual booking/payment)
- **Database**
  - Real SQLite database operations
  - Actual CRUD operations

## Test Data

### Test Users

**Alice Johnson** (`e2e_alice`)
- Email: `alice_test@example.com`
- Travel style: Adventure seeker
- Budget: Medium ($2000-3000)
- Preferences: United/Alaska airlines, Marriott/Hilton hotels

**Bob Smith** (`e2e_bob`)
- Email: `bob_test@example.com`
- Travel style: Relaxation
- Budget: Medium ($2000-3000)
- Preferences: Delta/Southwest airlines, Hyatt/Westin hotels, Vegetarian

### Test Credentials

⚠️ **Important:** Test credentials are fake and for testing only:
- Credit cards: Test numbers (4111111111111111, etc.)
- Expedia accounts: Test emails
- No real bookings or charges will occur

## Troubleshooting

### Test Fails: "Module not found"

```bash
# Install all dependencies
pip3 install -e .
```

### Test Fails: "No API key provided"

```bash
# Check .env file exists and has required keys
cat .env | grep -E "BROWSER_USE_API_KEY|OPENAI_API_KEY"
```

### Test Times Out

```bash
# Increase timeout (default is 5 minutes)
python3 -m pytest test_e2e_group_chat_booking.py -v -s --timeout=900
```

### Browser Use Cloud Issues

If Browser Use Cloud fails:
- Check `BROWSER_USE_API_KEY` is valid
- Verify network connectivity
- Check Browser Use Cloud dashboard for quota/limits

### LLM Calls Fail

If LLM calls fail:
- Verify `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set
- Check API key has sufficient credits
- Review rate limits on your account

## Test Output Example

```
================================ test session starts ================================
test_e2e_group_chat_booking.py::TestE2EGroupChatBooking::test_full_flow_with_approval

================================================================================
TEST: Full Flow with Approval
================================================================================

🧹 Cleaning up existing test data...
   ✅ Cleaned up existing test data

👥 Creating test users...
   ✅ Created test users: e2e_alice, e2e_bob

📝 Step 1: Starting group chat...
   Response status: 200
   ✅ Session created: e2e_test_abc123
   Status: pending_approval
   Total messages: 20

🔍 Step 2: Verifying TravelPlan generation...
   ✅ Plan generated:
      Location: Cancun, Mexico
      Dates: {'departure_date': '2024-12-15', 'return_date': '2024-12-22'}
      Budget: $2500
      Flight: LAX → CUN
      Hotel: Cancun Hotel Zone
   ✅ Plan emails sent to 2 users

✅ Step 3: Simulating approval webhooks...
   User e2e_alice: APPROVE
   User e2e_bob: APPROVE
   ✅ All users approved!

🚀 Step 4: Triggering parallel bookings...
   ⚠️  This will use real ExpediaAgent with browser automation
   ⚠️  Expected duration: 2-5 minutes
   [Browser automation logs...]
   ✅ Booking complete for e2e_alice
   ✅ Booking complete for e2e_bob

✅ Step 5: Verifying booking results...
   ✅ Booking confirmation sent: 2 call(s)

================================================================================
✅ TEST PASSED: Full flow with approval
================================================================================

PASSED                                                                  [100%]
```

## Performance Notes

- **Group chat phase:** 30-60 seconds (LLM API calls)
- **Browser automation:** 2-3 minutes per user (parallel execution)
- **Total test time:** 5-8 minutes for full flow test

## Integration with CI/CD

Mark as integration test to exclude from unit test runs:

```python
@pytest.mark.integration
def test_full_flow_with_approval(self):
    ...
```

Run only integration tests:
```bash
pytest -m integration
```

Skip integration tests:
```bash
pytest -m "not integration"
```

## Support

For issues or questions:
1. Check test output for specific error messages
2. Review main.py webhook handlers
3. Verify api/group_chat/orchestrator.py LLM configuration
4. Check api/expedia_agent/agent_browser.py Browser Use setup

