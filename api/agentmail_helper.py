"""
AgentMail integration helpers for sending plan emails and handling responses.

This module provides functions to:
- Send travel plans via email using AgentMail API
- Format plans as HTML and plain text
- Send booking confirmations
- Handle email responses
"""

from agentmail import AgentMailClient
from typing import Dict, Any, Optional
import os

# Initialize AgentMail client
client = AgentMailClient(api_key=os.getenv("AGENTMAIL_API_KEY"))

# Store inbox_id (global for simplicity; could be in config or database in production)
_inbox_id: Optional[str] = None


def get_or_create_inbox() -> str:
    """
    Get or create AgentMail inbox for the app.
    Inbox is created once and reused for all emails.
    """
    global _inbox_id
    
    if _inbox_id:
        return _inbox_id
    
    # Create inbox (idempotent operation)
    inbox = client.inboxes.create()
    _inbox_id = inbox.inbox_id
    
    print(f"✅ Created AgentMail inbox: {_inbox_id}")
    
    return _inbox_id


def send_plan_email(
    to: str,
    plan: Dict[str, Any],
    session_id: str,
    user_id: str
) -> str:
    """
    Send travel plan to user via email.
    
    Args:
        to: Recipient email address
        plan: TravelPlan dictionary
        session_id: Group chat session ID
        user_id: User ID for tracking
    
    Returns:
        message_id: AgentMail message ID for webhook tracking
    """
    inbox_id = get_or_create_inbox()
    
    # Format plan as HTML and text (both required by AgentMail best practices)
    html_content = _format_plan_html(plan)
    text_content = _format_plan_text(plan)
    
    # Send email
    print(f"📧 Sending plan email to {to}...")
    response = client.inboxes.messages.send(
        inbox_id,
        to=to,
        subject=f"Travel Plan Proposal: {plan['location']}",
        html=html_content,
        text=text_content
    )
    
    print(f"✅ Email sent! Message ID: {response.message_id}")
    
    return response.message_id


def _format_plan_html(plan: Dict[str, Any]) -> str:
    """Format TravelPlan as HTML email with styling"""
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
            <p style="font-size: 18px; margin: 0;"><strong>📧 Reply to this email with:</strong></p>
            <p style="font-size: 16px; color: #28a745; margin: 10px 0;"><strong>"APPROVE"</strong> to book this trip</p>
            <p style="font-size: 14px; margin: 5px 0;">or</p>
            <p style="font-size: 16px; color: #dc3545; margin: 10px 0;"><strong>"REJECT [your feedback]"</strong> to suggest changes</p>
        </div>
        
        <p style="color: #6c757d; font-size: 12px; margin-top: 40px;">
            This is an automated travel planning system. Your response will be processed immediately.
        </p>
    </body>
    </html>
    """


def _format_plan_text(plan: Dict[str, Any]) -> str:
    """Format TravelPlan as plain text (required by AgentMail for deliverability)"""
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
Reply with "APPROVE" to book this trip
or "REJECT [your feedback]" to suggest changes
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
    client.inboxes.messages.send(
        inbox_id,
        to=to,
        subject=subject,
        html=html,
        text=text
    )
    
    print(f"✅ Confirmation email sent!")


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

