# Expedia Agent Inbox Tool

## Overview

The Expedia agent now has access to a dedicated AgentMail inbox for receiving and reading emails. This enables the agent to:

- Check booking confirmations from Expedia
- Monitor travel updates and itinerary changes
- Receive customer communications
- Access OTP codes or verification emails
- Track email-based notifications

## Tool Details

### Tool Name
`Read emails from Expedia agent inbox`

### Function
`read_expedia_inbox(browser_session, limit=10)`

### Parameters

- **limit** (int, optional): Maximum number of messages to return
  - Default: 10
  - Maximum: 50
  - Range: 1-50

### Returns

Formatted string containing:
- Number of messages found
- For each message:
  - From address
  - Subject line
  - Content preview (first 200 characters)
  - Received timestamp
  - Message ID

### Example Output

```
Found 3 message(s) in Expedia inbox:

📧 Email 1:
   From: noreply@expedia.com
   Subject: Booking Confirmation #12345678
   Preview: Thank you for booking with Expedia! Your reservation is confirmed. Flight: AA123 from LAX to JFK on 2025-12-15. Hotel: Marriott Manhattan, Check-in: 2025-12-15, Check-out: 2025-12-20...
   Received: 2025-11-01 19:30:00
   Message ID: msg_abc123def456

📧 Email 2:
   From: support@expedia.com
   Subject: Your verification code
   Preview: Your one-time verification code is: 847392. This code expires in 10 minutes...
   Received: 2025-11-01 18:45:00
   Message ID: msg_xyz789uvw012

📧 Email 3:
   From: updates@expedia.com
   Subject: Travel Alert for Your Upcoming Trip
   Preview: Important update regarding your flight AA123 on December 15th. Gate change from B12 to B15...
   Received: 2025-11-01 17:20:00
   Message ID: msg_pqr345stu678
```

## Integration

### Automatic Registration

The tool is automatically registered when the Expedia agent loads. It's included in the combined `expedia_tools` registry alongside:

- Flight booking tools
- Hotel booking tools  
- Authentication tools
- Payment processing tools

### How the Agent Uses It

The browser-use agent can invoke this tool at any time during its workflow:

1. **During Login**: Check for OTP verification codes
2. **After Booking**: Verify booking confirmation emails
3. **Monitoring**: Check for travel updates or alerts
4. **Troubleshooting**: Look for error notifications or support messages

### Code Example

```python
from api.expedia_agent.agent_browser import ExpediaAgent

# Initialize agent with tools enabled (default)
agent = ExpediaAgent(use_tools=True)

# The agent can now use the inbox tool automatically
# Example task that might trigger inbox reading:
result = await agent.book_parallel(
    email="user@example.com",
    password="password123",
    # ... other booking parameters
)

# Agent might check inbox during execution:
# "Let me check the inbox for the booking confirmation email..."
```

## Testing

Run the test script to verify the tool works:

```bash
cd /Users/charleswright/yc-agentmail
python -m api.expedia_agent.test_inbox_tool
```

The test will:
1. Verify the tool is registered in the expedia_tools registry
2. Test reading the inbox with default limit (10 messages)
3. Test reading the inbox with custom limit (5 messages)

## Technical Details

### Backend Integration

- Uses the shared `get_or_create_inbox()` function from `agentmail_helper.py`
- Leverages the same inbox used by the travel planning system
- Messages are fetched via `get_inbox_messages()` helper
- Supports idempotent inbox creation (same inbox returned across sessions)

### Inbox Management

- **Inbox ID**: Automatically created and cached using deterministic client_id
- **Persistence**: Inbox persists across agent restarts
- **Shared Access**: Same inbox accessible by all Expedia agent instances
- **Rate Limiting**: Respects AgentMail API rate limits

### Error Handling

The tool gracefully handles:
- AgentMail API unavailability
- Empty inboxes
- Network timeouts
- Authentication errors
- Invalid limit parameters (clamps to 1-50 range)

## Use Cases

### 1. OTP Verification During Login
When signing into Expedia requires email verification:
```
Agent: "I need to verify the email. Let me check the inbox..."
[Calls read_expedia_inbox tool]
Agent: "Found verification code 847392 in recent email. Entering it now..."
```

### 2. Booking Confirmation Verification
After completing a booking:
```
Agent: "Checking inbox for booking confirmation..."
[Calls read_expedia_inbox tool]
Agent: "Confirmed! Booking #12345678 received via email. Flight AA123 and hotel reservation both confirmed."
```

### 3. Travel Alert Monitoring
Periodically checking for updates:
```
Agent: "Let me check for any travel alerts..."
[Calls read_expedia_inbox tool]
Agent: "Found important update: Gate change from B12 to B15 for flight AA123."
```

### 4. Support Communication Tracking
Monitoring customer support emails:
```
Agent: "Checking inbox for support team response..."
[Calls read_expedia_inbox tool]
Agent: "Support has responded regarding the refund request. Processing their instructions..."
```

## Maintenance

### Inbox Cleanup
- Emails are retained according to AgentMail's retention policy
- No manual cleanup required
- Tool always fetches most recent messages first

### Monitoring
- Tool logs all inbox access attempts
- Errors are logged with full context
- Success metrics tracked via logger

### Updates
The tool automatically benefits from updates to:
- `agentmail_helper.py` inbox management
- AgentMail SDK improvements
- Message formatting enhancements

## Troubleshooting

### No messages returned
- Verify AgentMail API key is set in environment
- Check that inbox has been created: look for "✅ Created/retrieved AgentMail inbox" in logs
- Ensure network connectivity to AgentMail API

### Tool not found in registry
- Verify `expedia_prebuilt_actions.py` is being imported
- Check `expedia_agent_tools.py` combines all registries
- Look for "✅ Combined X Expedia tools" message in logs

### Authentication errors
- Confirm `AGENTMAIL_API_KEY` in `.env` file
- Check API key validity at AgentMail dashboard
- Verify API key has inbox read permissions

## Future Enhancements

Potential improvements:
- Filter messages by sender/subject
- Mark messages as read
- Delete old messages
- Reply to messages directly from agent
- Parse specific email types (confirmations, OTPs, alerts)
- Extract structured data from emails (flight numbers, booking IDs)

