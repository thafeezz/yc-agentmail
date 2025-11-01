import agentmail
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from agentmail import AgentMail
from api.cfg import settings
from pydantic import BaseModel
from typing import Any, Optional
from api.clients import hyperspell_client, agentmail_client
from api.cfg import USER_TO_RESOURCE
from api.agent import PersonaAgent
from api import app as api_app

# Create main app that includes API routes
app = FastAPI()

# Mount the API app
app.mount("/api", api_app)


# ============================================================================
# Startup Event - Register AgentMail Webhook
# ============================================================================

@app.on_event("startup")
async def register_agentmail_webhook():
    """Register webhook with AgentMail on app startup."""
    if not settings.webhook_base_url:
        print("⚠️  WEBHOOK_BASE_URL not set - skipping AgentMail webhook registration")
        return
    
    if not agentmail_client:
        print("⚠️  AgentMail client not initialized - skipping webhook registration")
        return
    
    webhook_url = f"{settings.webhook_base_url}/webhooks/agentmail"
    
    try:
        # Try to create webhook (idempotent if using same URL)
        webhook = agentmail_client.webhooks.create(
            url=webhook_url,
            events=["message.received"]
        )
        print(f"✅ AgentMail webhook registered: {webhook_url}")
        print(f"   Webhook ID: {webhook.id}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"✅ AgentMail webhook already registered: {webhook_url}")
        else:
            print(f"❌ Failed to register AgentMail webhook: {e}")

# todo: rename me
class Context(BaseModel):
    transcript: dict[str, Any]
    user_id: str


# invoked after onboarding completed with context of conversation
@app.post("/webhooks/store-ctx")
async def store_ctx(ctx: Context):
    # store ctx in hyperspell
    response = hyperspell_client.memories.add(text=ctx.transcript, collection=ctx.user_id)
    USER_TO_RESOURCE[ctx.user_id] = response.resource_id

    # create an agent for this persona/user
    persona_agent = PersonaAgent(user_id=ctx.user_id)
    # invoked some kind of run loop or callback for the agent
    persona_agent.invoke()


@app.post("/webhooks/create-email")
async def create_email(request: Request):
    agentmail_client.inboxes.create()

    return {"message": "Email created"}


# ============================================================================
# Approve/Reject Routes - Handle Email Link Clicks
# ============================================================================

@app.get("/webhooks/agentmail/approve/{message_id}")
async def approve_via_link(message_id: str):
    """Handle user approval via email link click."""
    from api.group_chat.database import get_session, get_session_by_message_id
    
    db = get_session()
    result = get_session_by_message_id(db, message_id)
    
    if not result:
        return HTMLResponse(content="""
            <html><body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>❌ Link Expired</h1>
                <p>This approval link is no longer valid or has already been used.</p>
            </body></html>
        """, status_code=404)
    
    chat_session, user_id = result
    session_id = chat_session.session_id
    
    # Call existing approval handler
    await handle_plan_approval(db, session_id, user_id)
    
    return HTMLResponse(content="""
        <html><body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #28a745;">✅ Plan Approved!</h1>
            <p style="font-size: 18px;">Your travel plan has been approved. We'll proceed with booking.</p>
            <p style="color: #666; margin-top: 30px;">You'll receive a confirmation email shortly with your booking details.</p>
        </body></html>
    """)


@app.get("/webhooks/agentmail/reject/{message_id}")
async def reject_via_link(message_id: str, feedback: str = ""):
    """Handle user rejection via email link click."""
    from api.group_chat.database import get_session, get_session_by_message_id
    
    db = get_session()
    result = get_session_by_message_id(db, message_id)
    
    if not result:
        return HTMLResponse(content="""
            <html><body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>❌ Link Expired</h1>
                <p>This rejection link is no longer valid or has already been used.</p>
            </body></html>
        """, status_code=404)
    
    chat_session, user_id = result
    session_id = chat_session.session_id
    
    # If no feedback, show form to collect it
    if not feedback:
        return HTMLResponse(content=f"""
            <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h1 style="color: #dc3545;">❌ Reject Travel Plan</h1>
                <p style="font-size: 16px; color: #333;">Please tell us what you'd like to change about the plan:</p>
                <form method="get" action="/webhooks/agentmail/reject/{message_id}" style="margin-top: 20px;">
                    <textarea name="feedback" 
                              style="width: 100%; height: 150px; padding: 10px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; font-family: Arial;" 
                              placeholder="E.g., The budget is too high, I prefer a different hotel location, the dates don't work for me..." 
                              required></textarea>
                    <button type="submit" 
                            style="background: #dc3545; color: white; padding: 12px 30px; border: none; 
                                   border-radius: 5px; font-size: 16px; cursor: pointer; margin-top: 10px; font-weight: bold;">
                        Submit Feedback
                    </button>
                </form>
            </body></html>
        """)
    
    # Call existing rejection handler
    await handle_plan_rejection(db, session_id, user_id, feedback)
    
    return HTMLResponse(content="""
        <html><body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #dc3545;">🔄 Plan Rejected</h1>
            <p style="font-size: 18px;">Thank you for your feedback! We're working on a revised plan.</p>
            <p style="color: #666; margin-top: 30px;">You'll receive a new travel proposal via email shortly that addresses your concerns.</p>
        </body></html>
    """)


@app.post("/webhooks/agentmail")
async def handle_agentmail_webhook(request: Request):
    """
    Handle AgentMail message.received webhook.
    Triggered when users reply to plan emails with APPROVE or REJECT.
    """
    payload = await request.json()
    
    # Only handle message.received events
    if payload.get("event_type") != "message.received":
        return {"status": "ignored", "reason": "not_message_received"}
    
    message = payload.get("message", {})
    in_reply_to = message.get("in_reply_to")
    
    if not in_reply_to:
        return {"status": "ignored", "reason": "not_a_reply"}
    
    # Get session and user from parent message_id
    from api.group_chat.database import get_session, get_session_by_message_id
    
    db = get_session()
    result = get_session_by_message_id(db, in_reply_to)
    
    if not result:
        return {"status": "error", "reason": "session_not_found"}
    
    chat_session, user_id = result
    session_id = chat_session.session_id
    
    # Fetch the reply content
    reply_content = await get_message_content(message.get("message_id"))
    
    if not reply_content:
        return {"status": "error", "reason": "cannot_fetch_message"}
    
    reply_lower = reply_content.lower()
    
    # Parse approval/rejection
    if "approve" in reply_lower:
        await handle_plan_approval(db, session_id, user_id)
        return {"status": "approved", "session_id": session_id}
        
    elif "reject" in reply_lower:
        # Extract feedback (everything after "reject")
        feedback = reply_content.strip()
        await handle_plan_rejection(db, session_id, user_id, feedback)
        return {"status": "rejected", "session_id": session_id}
    
    return {"status": "unclear_response"}


async def get_message_content(message_id: str) -> Optional[str]:
    """
    Fetch message content from AgentMail API.
    
    TODO: Implement proper message fetching via AgentMail API
    For now, this is a placeholder that should be replaced with actual API calls.
    """
    # Placeholder implementation
    # In production, this would call:
    # message = agentmail_client.inboxes.messages.get(inbox_id, message_id)
    # return message.text_content or message.html_content
    
    print(f"⚠️ get_message_content is placeholder - implement AgentMail API call for message {message_id}")
    return "APPROVE"  # Placeholder


async def handle_plan_approval(db: Any, session_id: str, user_id: str):
    """Handle user approving the travel plan"""
    from api.group_chat.database import update_approval_state
    
    print(f"✅ User {user_id} approved plan for session {session_id}")
    
    state = update_approval_state(db, session_id, user_id, approved=True)
    
    if state["all_approved"]:
        # All users approved! Trigger bookings
        print(f"🎉 All users approved session {session_id}. Starting parallel bookings...")
        await trigger_parallel_bookings(session_id)


async def handle_plan_rejection(
    db: Any,
    session_id: str,
    user_id: str,
    feedback: str
):
    """Handle user rejecting the travel plan"""
    from api.group_chat.database import update_approval_state
    
    print(f"❌ User {user_id} rejected plan for session {session_id}")
    
    state = update_approval_state(
        db, session_id, user_id, approved=False, feedback=feedback
    )
    
    if state["any_rejected"]:
        # Start new volley with feedback
        print(f"🔄 Plan rejected for session {session_id}. Starting new volley with feedback...")
        await start_new_volley_with_feedback(session_id, feedback)


async def trigger_parallel_bookings(session_id: str):
    """
    Book flights and hotels for all participants in parallel.
    Uses onboarding data (credentials, payment) from UserProfile.
    """
    from api.group_chat.database import get_session, get_chat_session, load_user_profiles
    from api.expedia_agent.agent_browser import ExpediaAgent
    from api.agentmail_helper import send_booking_confirmation
    import asyncio
    
    db = get_session()
    chat_session = get_chat_session(db, session_id)
    
    if not chat_session or not chat_session.final_plan:
        print(f"❌ Cannot book: no session or plan for {session_id}")
        return
    
    plan = chat_session.final_plan
    user_profiles = load_user_profiles(db, chat_session.user_ids)
    
    async def book_for_user(user):
        """Book for a single user using their onboarding data"""
        print(f"\n🔍 Booking for user {user.user_id} ({user.email})...")
        print(f"   Has expedia_credentials: {user.expedia_credentials is not None}")
        print(f"   Has payment_details: {user.payment_details is not None}")
        print(f"   Has contact_info: {user.contact_info is not None}")
        
        # Validate user has required credentials
        if not user.expedia_credentials:
            print(f"❌ {user.user_id}: Missing Expedia credentials")
            return {
                "user_id": user.user_id,
                "email": user.email,
                "success": False,
                "error": "No Expedia credentials provided"
            }
        
        if not user.payment_details:
            print(f"❌ {user.user_id}: Missing payment details")
            return {
                "user_id": user.user_id,
                "email": user.email,
                "success": False,
                "error": "No payment details provided"
            }
        
        if not user.contact_info:
            print(f"❌ {user.user_id}: Missing contact info")
            return {
                "user_id": user.user_id,
                "email": user.email,
                "success": False,
                "error": "No contact info provided"
            }
        
        try:
            print(f"✅ {user.user_id}: All credentials present, setting up AgentMail inbox...")
            
            # Create dedicated AgentMail inbox for this booking agent
            import uuid
            inbox_id = str(uuid.uuid4())
            
            # Create inbox directly with AgentMail client
            from api.clients import agentmail_client
            inbox = agentmail_client.inboxes.create(client_id=inbox_id)
            
            # AgentMail Inbox object structure:
            # - inbox.inbox_id = email address (e.g., "user123@agentmail.to")
            # - inbox.client_id = UUID we provided
            # According to AgentMail docs, use the EMAIL ADDRESS for API calls, not UUID!
            inbox_email = inbox.inbox_id  # Email address for both Expedia signup AND API calls
            print(f"📧 {user.user_id}: AgentMail inbox created: {inbox_email}")
            
            # Initialize Flight Agent with cloud browser and flight tools only
            print(f"✈️  {user.user_id}: Initializing Flight Agent...")
            flight_agent = ExpediaAgent(
                llm_model="gpt-4o",
                use_cloud_browser=True,
                use_tools=True,
                tool_type="flight"  # Only flight tools
            )
            
            # HOTEL AGENT DISABLED - Only testing flight booking
            # # Initialize Hotel Agent with cloud browser and hotel tools only
            # print(f"🏨 {user.user_id}: Initializing Hotel Agent...")
            # hotel_agent = ExpediaAgent(
            #     llm_model="gpt-4o",
            #     use_cloud_browser=True,
            #     use_tools=True,
            #     tool_type="hotel"  # Only hotel tools
            # )
            
            print(f"🤖 {user.user_id}: Flight agent initialized, starting booking task...")
            
            # Parse user name
            name_parts = user.user_name.split()
            first_name = name_parts[0]
            last_name = name_parts[-1] if len(name_parts) > 1 else ""
            
            # Build task descriptions for both agents
            
            # FLIGHT BOOKING TASK
            flight_task = f"""
🎯 EXPEDIA FLIGHT BOOKING WITH SIGN-IN

CRITICAL: YOU MUST USE THE CUSTOM EXPEDIA TOOLS PROVIDED.

⚠️ IMPORTANT: If ANY popups, promotions, dialogs, or modal windows appear at ANY point:
   - IMMEDIATELY close them using X button, Close button, or ESC key
   - DO NOT interact with promotional content
   - DO NOT click "Sign up", "Save", "Subscribe", or similar buttons
   - Exit the popup and continue with the booking flow

YOUR AVAILABLE CUSTOM TOOLS:
1. sign_in_expedia(email="{inbox_email}") - Signs in to Expedia (automatically handles OTP from AgentMail)
2. navigate_to_search_results(origin="{plan["flight"]["origin"]}", destination="{plan["flight"]["destination"]}", departure_date="{plan["dates"]["departure_date"]}", return_date="{plan["dates"].get("return_date", plan["dates"]["departure_date"])}") - Goes directly to flight search results
3. sort_by_price() - Sorts flights by price
4. select_outbound_basic_fare() - Selects cheapest outbound flight
5. select_return_basic_fare() - Selects cheapest return flight
6. fill_traveler_details(first_name="{first_name}", last_name="{last_name}", email="{inbox_email}", phone="{user.contact_info.phone}") - Fills traveler info
7. click_continue_checkout() - Continues to payment
8. fill_payment_form(card_number="{user.payment_details.card_number}", cardholder_name="{user.payment_details.cardholder_name}", expiration_month="{user.payment_details.expiration_month}", expiration_year="{user.payment_details.expiration_year}", cvv="{user.payment_details.cvv}", billing_address=...) - Fills payment

EXACT WORKFLOW (follow this order):
Step 1: Call sign_in_expedia(email="{inbox_email}")
        → This will automatically fetch OTP from your AgentMail inbox and complete sign-in
        
Step 2: Call navigate_to_search_results(origin="{plan["flight"]["origin"]}", destination="{plan["flight"]["destination"]}", departure_date="{plan["dates"]["departure_date"]}", return_date="{plan["dates"].get("return_date", plan["dates"]["departure_date"])}")
        → Close any popups that appear after navigation

Step 3: Call sort_by_price()
Step 4: Call select_outbound_basic_fare()
        → Close any popups/promotions that appear after selection
        
Step 5: Call select_return_basic_fare()
        → Close any popups/promotions that appear after selection
        
Step 6: Call fill_traveler_details(first_name="{first_name}", last_name="{last_name}", email="{inbox_email}", phone="{user.contact_info.phone}")
Step 7: Call click_continue_checkout()
        → Close any popups/promotions before proceeding to payment
        
Step 8: Call fill_payment_form(
    card_number="{user.payment_details.card_number}",
    cardholder_name="{user.payment_details.cardholder_name}",
    expiration_month="{user.payment_details.expiration_month}",
    expiration_year="{user.payment_details.expiration_year}",
    cvv="{user.payment_details.cvv}",
    billing_country="USA",
    billing_street="{user.payment_details.billing_address.get('street', '123 Main St')}",
    billing_city="{user.payment_details.billing_address.get('city', 'San Francisco')}",
    billing_state="{user.payment_details.billing_address.get('state', 'CA')}",
    billing_zip="{user.payment_details.billing_address.get('zip', '94102')}"
)
Step 9: Decline insurance if offered
Step 10: Verify the Complete Booking button (DO NOT CLICK - test data only!)

IMPORTANT: Complete all steps in order. Close ANY popups immediately. Use only the custom tools provided.
"""

            # HOTEL BOOKING TASK
            hotel_task = f"""
🏨 EXPEDIA HOTEL BOOKING - NO SIGN-IN REQUIRED

⚠️ IMPORTANT: If ANY popups, promotions, dialogs, or modal windows appear at ANY point:
   - IMMEDIATELY close them using X button, Close button, or ESC key
   - DO NOT interact with promotional content
   - DO NOT click "Sign up", "Save", "Subscribe", or similar buttons
   - Exit the popup and continue with the booking flow

Book a hotel on Expedia:

1. Navigate to Expedia hotels section
2. Search for hotels in {plan["hotel"]["location"]}
   - Check-in: {plan["dates"]["departure_date"]}
   - Check-out: {plan["dates"].get("return_date", plan["dates"]["departure_date"])}
3. Select a hotel (best rated under ${plan["budget"]["per_person"]}/night)
   - Preferences: {plan["hotel"].get("amenities", [])}
4. Complete booking with traveler info:
   - Name: {first_name} {last_name}
   - Email: {inbox_email}
   - Phone: {user.contact_info.phone}
5. Fill payment information and complete booking

IMPORTANT: Use custom Expedia hotel tools for efficient booking. Do NOT attempt to sign in.
"""
            
            # Run flight booking only
            print(f"✈️  {user.user_id}: Starting flight booking...")
            flight_result = await flight_agent.run_task(flight_task)
            
            # HOTEL BOOKING DISABLED - Only testing flights
            # # Then run hotel booking
            # print(f"🏨 {user.user_id}: Starting hotel booking...")
            # hotel_result = await hotel_agent.run_task(hotel_task)
            
            result = {
                "flight": flight_result,
                "hotel": "skipped"  # Hotel booking disabled for testing
            }
            
            # Clean up agent resources
            await flight_agent.cleanup()
            # await hotel_agent.cleanup()  # Hotel agent disabled
            
            return {
                "user_id": user.user_id,
                "email": user.email,
                "success": True,
                "result": result,
                "message": "Booking completed successfully"
            }
            
        except Exception as e:
            print(f"❌ Booking failed for {user.user_id}: {str(e)}")
            return {
                "user_id": user.user_id,
                "email": user.email,
                "success": False,
                "error": str(e)
            }
    
    # Execute all bookings in parallel
    print(f"🚀 Starting parallel bookings for {len(user_profiles)} users...")
    results = await asyncio.gather(
        *[book_for_user(user) for user in user_profiles],
        return_exceptions=True
    )
    
    # Send confirmation emails (only if successful to avoid AgentMail rejections)
    for result in results:
        if isinstance(result, Exception):
            result = {
                "email": "unknown@example.com",
                "success": False,
                "error": str(result)
            }
        
        # Skip sending email if booking failed or email is invalid
        if result.get("success", False) and result.get("email") and "@agentmail.to" in result["email"]:
            try:
                send_booking_confirmation(
                    to=result["email"],
                    result=result
                )
            except Exception as e:
                print(f"⚠️  Failed to send confirmation email to {result['email']}: {e}")
        else:
            print(f"⚠️  Skipping confirmation email for {result.get('email', 'unknown')} (success={result.get('success', False)})")
    
    # Update session status
    from api.group_chat.database import update_chat_session
    
    all_success = all(
        r.get("success", False) for r in results if isinstance(r, dict)
    )
    
    update_chat_session(
        db,
        session_id=session_id,
        status="bookings_completed" if all_success else "bookings_partial"
    )
    
    print(f"✅ Booking process completed for session {session_id}")


async def start_new_volley_with_feedback(session_id: str, feedback: str):
    """Start new deliberation volley after plan rejection"""
    from api.group_chat.database import get_session, get_chat_session, load_user_profiles
    from api.group_chat.orchestrator import GroupChatOrchestrator
    from api.group_chat.api import active_orchestrators, active_states
    from api.group_chat.database import update_chat_session, store_message_mapping
    from api.agentmail_helper import send_plan_email
    
    db = get_session()
    chat_session = get_chat_session(db, session_id)
    
    if not chat_session:
        print(f"❌ Cannot start new volley: session {session_id} not found")
        return
    
    # Get or recreate orchestrator
    orchestrator = active_orchestrators.get(session_id)
    if not orchestrator:
        user_profiles = load_user_profiles(db, chat_session.user_ids)
        orchestrator = GroupChatOrchestrator(
            users=user_profiles,
            messages_per_volley=chat_session.messages_per_agent
        )
        active_orchestrators[session_id] = orchestrator
    
    # Get current state
    current_state = active_states.get(session_id)
    if not current_state:
        print(f"❌ Cannot find state for session {session_id}")
        return
    
    # Handle rejection by adding feedback to state
    updated_state = orchestrator.handle_rejection(
        current_state=current_state,
        feedback=feedback,
        user_id="system"
    )
    
    # Run new volley
    print(f"🔄 Running new volley for session {session_id}...")
    final_state = orchestrator.run_volley(initial_state=updated_state)
    active_states[session_id] = final_state
    
    # Send new plan via email if generated
    if final_state.get("current_plan") and "error" not in final_state["current_plan"]:
        from api.cfg import settings
        import uuid
        
        user_profiles = load_user_profiles(db, chat_session.user_ids)
        message_ids = {}
        base_url = settings.webhook_base_url or "http://localhost:8000"
        
        for user in user_profiles:
            # Generate a unique message ID for tracking
            msg_id = f"msg_{uuid.uuid4().hex[:16]}"
            
            # Send email with approval/reject links
            returned_msg_id = send_plan_email(
                to=user.email,
                plan=final_state["current_plan"],
                session_id=session_id,
                user_id=user.user_id,
                message_id=msg_id,
                base_url=base_url
            )
            message_ids[user.user_id] = returned_msg_id
            store_message_mapping(db, msg_id, session_id, user.user_id)
        
        # Reset approval state for new round
        chat_session.approval_state = {}
        chat_session.agentmail_message_ids = message_ids
        chat_session.final_plan = final_state["current_plan"]
        chat_session.current_volley += 1
        chat_session.status = "pending_approval"
        db.commit()
        
        print(f"✅ New plan sent via email for session {session_id}")



def main():
    print("Hello from yc-agentmail!")


if __name__ == "__main__":
    main()
