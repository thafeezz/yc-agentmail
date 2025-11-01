"""
AgentMail integration helpers for sending plan emails and handling responses.

This module provides functions to:
- Send travel plans via email using AgentMail API
- Format plans as HTML and plain text
- Send booking confirmations
- Handle email responses
"""

from agentmail import AgentMail
from typing import Dict, Any, Optional, List
import os
import time

# Initialize AgentMail client
# Try both env var names for compatibility
api_key = os.getenv("AGENTMAIL_API_KEY") or os.getenv("AGENT_MAIL_API_KEY") or "dummy_key_for_testing"
client = AgentMail(api_key=api_key)

# Store inbox_id (global for simplicity; could be in config or database in production)
_inbox_id: Optional[str] = None


def get_or_create_inbox() -> str:
    """
    Get or create AgentMail inbox for the app.
    Inbox is created once and reused for all emails using idempotent client_id.
    
    Uses a deterministic client_id to ensure the same inbox is always returned,
    following AgentMail best practices for production applications.
    """
    global _inbox_id
    
    if _inbox_id:
        return _inbox_id
    
    # Create inbox with deterministic client_id for idempotency
    # This ensures the same inbox is returned even across different test runs
    app_name = os.getenv("APP_NAME", "yc-agentmail")
    client_id = f"{app_name}-system-inbox"
    
    inbox = client.inboxes.create(
        client_id=client_id  # Idempotent - same client_id always returns same inbox
    )
    _inbox_id = inbox.inbox_id
    
    print(f"✅ Created/retrieved AgentMail inbox: {_inbox_id} (client_id: {client_id})")
    
    return _inbox_id


def reset_inbox():
    """Reset the cached inbox ID. Useful for testing."""
    global _inbox_id
    _inbox_id = None




def send_plan_email(
    to: str,
    plan: Dict[str, Any],
    session_id: str,
    user_id: str,
    message_id: str,
    base_url: str
) -> str:
    """
    Send travel plan to user via email.
    
    Args:
        to: Recipient email address
        plan: TravelPlan dictionary
        session_id: Group chat session ID
        user_id: User ID for tracking
        message_id: AgentMail message ID for URL generation
        base_url: Base URL for webhook links
    
    Returns:
        message_id: AgentMail message ID for webhook tracking
    """
    inbox_id = get_or_create_inbox()
    
    # Format plan as HTML and text (both required by AgentMail best practices)
    html_content = _format_plan_html(plan, message_id, base_url)
    text_content = _format_plan_text(plan, message_id, base_url)
    
    # Send email
    print(f"📧 Sending plan email to {to}...")
    # Send email via AgentMail with retry for inbox readiness
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.inboxes.messages.send(
                inbox_id,
                to=to,
                subject=f"Travel Plan Proposal: {plan['location']}",
                html=html_content,
                text=text_content
            )
            
            print(f"✅ Email sent! Message ID: {response.message_id}")
            return response.message_id
            
        except Exception as e:
            if "NotFoundError" in str(type(e).__name__) or "404" in str(e):
                if attempt < max_retries - 1:
                    print(f"⚠️  Inbox not ready (attempt {attempt + 1}/{max_retries}), retrying in 1s...")
                    time.sleep(1)
                    continue
            # Re-raise for other errors or last attempt
            raise


def _format_plan_html(plan: Dict[str, Any], message_id: str, base_url: str) -> str:
    """Format TravelPlan as HTML email with styling"""
    approve_url = f"{base_url}/webhooks/agentmail/approve/{message_id}"
    reject_url = f"{base_url}/webhooks/agentmail/reject/{message_id}"
    
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #2c3e50;">Your Travel Plan is Ready! ✈️</h1>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h2 style="color: #3498db; margin-top: 0;">📍 {plan['location']}</h2>
        </div>
        
        <div style="margin: 20px 0;">
            <h3 style="color: #2c3e50;">📅 Dates</h3>
            <p><strong>Departure:</strong> {plan['dates']['departure_date']}</p>
            <p><strong>Return:</strong> {plan['dates']['return_date']}</p>
        </div>
        
        <div style="margin: 20px 0;">
            <h3 style="color: #2c3e50;">✈️ Flight</h3>
            <p><strong>From:</strong> {plan['flight']['origin']}</p>
            <p><strong>To:</strong> {plan['flight']['destination']}</p>
            <p><strong>Preferences:</strong> {plan['flight'].get('preferences', 'Economy class')}</p>
        </div>
        
        <div style="margin: 20px 0;">
            <h3 style="color: #2c3e50;">🏨 Hotel</h3>
            <p><strong>Location:</strong> {plan['hotel']['location']}</p>
            <p><strong>Type:</strong> {plan['hotel']['type']}</p>
            <p><strong>Amenities:</strong> {', '.join(plan['hotel'].get('amenities', []))}</p>
        </div>
        
        <div style="margin: 20px 0;">
            <h3 style="color: #2c3e50;">💰 Budget</h3>
            <p><strong>Total per person:</strong> ${plan['budget']['total_per_person']}</p>
            <p><em>Flight: ${plan['budget'].get('flight_cost', 'TBD')} | Hotel: ${plan['budget'].get('hotel_cost', 'TBD')}</em></p>
        </div>
        
        <div style="background: #e8f4f8; padding: 20px; border-radius: 8px; margin: 30px 0; border-left: 4px solid #3498db;">
            <h3 style="margin-top: 0; color: #2c3e50;">How compromises were made:</h3>
            <p style="font-style: italic;">{plan.get('compromises_made', 'Balanced all preferences')}</p>
        </div>
        
        <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 30px 0; text-align: center;">
            <p style="font-size: 18px; margin: 0 0 20px 0;"><strong>📧 Take Action:</strong></p>
            <div style="margin: 10px 0;">
                <a href="{approve_url}" style="display: inline-block; background: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 5px; font-size: 16px;">
                    ✅ APPROVE & BOOK
                </a>
            </div>
            <div style="margin: 10px 0;">
                <a href="{reject_url}" style="display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 5px; font-size: 16px;">
                    ❌ REJECT & REVISE
                </a>
            </div>
        </div>
        
        <p style="color: #6c757d; font-size: 12px; margin-top: 40px;">
            This is an automated travel planning system. Your response will be processed immediately.
        </p>
    </body>
    </html>
    """


def _format_plan_text(plan: Dict[str, Any], message_id: str, base_url: str) -> str:
    """Format TravelPlan as plain text (required by AgentMail for deliverability)"""
    approve_url = f"{base_url}/webhooks/agentmail/approve/{message_id}"
    reject_url = f"{base_url}/webhooks/agentmail/reject/{message_id}"
    
    return f"""
Your Travel Plan is Ready!

DESTINATION: {plan['location']}

DATES:
  Departure: {plan['dates']['departure_date']}
  Return: {plan['dates']['return_date']}

FLIGHT:
  From: {plan['flight']['origin']}
  To: {plan['flight']['destination']}
  Preferences: {plan['flight'].get('preferences', 'Economy class')}

HOTEL:
  Location: {plan['hotel']['location']}
  Type: {plan['hotel']['type']}
  Amenities: {', '.join(plan['hotel'].get('amenities', []))}

BUDGET:
  Total per person: ${plan['budget']['total_per_person']}
  Flight: ${plan['budget'].get('flight_cost', 'TBD')}
  Hotel: ${plan['budget'].get('hotel_cost', 'TBD')}

COMPROMISES MADE:
{plan.get('compromises_made', 'Balanced all preferences')}

---
APPROVE: {approve_url}
REJECT: {reject_url}
---
    """


def send_booking_confirmation(
    to: str,
    result: Dict[str, Any]
) -> None:
    """
    Send booking confirmation or failure email.
    
    Args:
        to: Recipient email address
        result: Booking result dict with 'success', 'message', or 'error'
    """
    inbox_id = get_or_create_inbox()
    
    success = result.get("success", False)
    
    if success:
        html = _format_booking_success_html(result)
        text = _format_booking_success_text(result)
        subject = "✅ Your Trip is Booked!"
    else:
        html = _format_booking_failure_html(result)
        text = _format_booking_failure_text(result)
        subject = "❌ Booking Failed"
    
    print(f"📧 Sending booking confirmation to {to}...")
    # Send email with retry for inbox readiness
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client.inboxes.messages.send(
                inbox_id,
                to=to,
                subject=subject,
                html=html,
                text=text
            )
            
            print(f"✅ Confirmation email sent!")
            return  # Success, exit function
            
        except Exception as e:
            if "NotFoundError" in str(type(e).__name__) or "404" in str(e):
                if attempt < max_retries - 1:
                    print(f"⚠️  Inbox not ready (attempt {attempt + 1}/{max_retries}), retrying in 1s...")
                    time.sleep(1)
                    continue
            # Re-raise for other errors or last attempt
            raise


def _format_booking_success_html(result: Dict[str, Any]) -> str:
    """Format successful booking confirmation as HTML"""
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #28a745;">✅ Your Trip is Booked!</h1>
        <p>Congratulations! Your flights and hotel have been successfully booked.</p>
        
        <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
            <h2 style="margin-top: 0;">Booking Details</h2>
            <p>{result.get('message', 'Booking completed successfully')}</p>
        </div>
        
        <p style="color: #6c757d;">Check your email for confirmation details from Expedia.</p>
    </body>
    </html>
    """


def _format_booking_success_text(result: Dict[str, Any]) -> str:
    """Format successful booking confirmation as plain text"""
    return f"""
Your Trip is Booked!

Congratulations! Your flights and hotel have been successfully booked.

{result.get('message', 'Booking completed successfully')}

Check your email for confirmation details from Expedia.
    """


def _format_booking_failure_html(result: Dict[str, Any]) -> str:
    """Format booking failure notification as HTML"""
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #dc3545;">❌ Booking Failed</h1>
        <p>Unfortunately, we encountered an issue while booking your trip.</p>
        
        <div style="background: #f8d7da; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545;">
            <h2 style="margin-top: 0;">Error Details</h2>
            <p>{result.get('error', 'Unknown error occurred')}</p>
        </div>
        
        <p style="color: #6c757d;">Please contact support or try booking again.</p>
    </body>
    </html>
    """


def _format_booking_failure_text(result: Dict[str, Any]) -> str:
    """Format booking failure notification as plain text"""
    return f"""
Booking Failed

Unfortunately, we encountered an issue while booking your trip.

Error: {result.get('error', 'Unknown error occurred')}

Please contact support or try booking again.
    """


def get_inbox_messages(inbox_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch recent messages from AgentMail inbox using threads API.
    
    Args:
        inbox_id: AgentMail inbox ID (email address format)
        limit: Maximum number of messages to return
    
    Returns:
        List of message dictionaries with sender, subject, preview, body
    """
    try:
        # Step 1: List all threads in the inbox

        inbox_response = client.inboxes.threads.list(inbox_id=inbox_id)
        
        all_messages = []
        
        # The response has a .threads attribute which is a list of thread objects
        if not inbox_response or not inbox_response.threads:
            print(f"⚠️ No threads found in inbox {inbox_id}")
            return []
        
        # Step 2: Get full thread details to access messages
        for thread in inbox_response.threads:
            # thread might be a tuple (thread_id, ...) or an object with .id
            if isinstance(thread, tuple):
                thread_id = thread[0] if len(thread) > 0 else None
            elif hasattr(thread, 'id'):
                thread_id = thread.id
            elif hasattr(thread, 'thread_id'):
                thread_id = thread.thread_id
            else:
                print(f"⚠️ Unknown thread type: {type(thread)}, skipping")
                continue
            
            if not thread_id:
                continue
            
            # Get the full thread object to access its messages
            thread_details = client.threads.get(thread_id=thread_id)
            
            # Extract messages from thread
            for message in thread_details.messages:
                # Get message body (prefer text, fallback to HTML)
                body = ""
                if hasattr(message, 'text') and message.text:
                    body = message.text
                elif hasattr(message, 'html') and message.html:
                    body = message.html
                elif hasattr(message, 'body'):
                    body = message.body
                
                all_messages.append({
                    "message_id": message.id if hasattr(message, 'id') else "unknown",
                    "from": message.from_ if hasattr(message, 'from_') else "unknown",
                    "subject": message.subject if hasattr(message, 'subject') else "(no subject)",
                    "preview": body[:200] if body else "",
                    "body": body,  # Full body for OTP extraction
                    "received_at": str(message.created_at) if hasattr(message, 'created_at') else "unknown"
                })
                
                # Stop if we've collected enough messages
                if len(all_messages) >= limit:
                    break
            
            if len(all_messages) >= limit:
                break
        
        print(f"✅ Retrieved {len(all_messages)} messages from {inbox_id}")
        return all_messages
        
    except Exception as e:
        print(f"❌ Failed to fetch inbox messages from {inbox_id}: {e}")
        import traceback
        traceback.print_exc()
        return []

