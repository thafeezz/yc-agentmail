import agentmail
from fastapi import FastAPI, Request
from agentmail import AgentMail
from api.cfg import settings
from pydantic import BaseModel
from typing import Any
from api.clients import hyperspell_client, agentmail_client
from api.cfg import USER_TO_RESOURCE
from api.agent import PersonaAgent
from api import app as api_app

# Create main app that includes API routes
app = FastAPI()

# Mount the API app
app.mount("/api", api_app)

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


@app.post("webhooks/create-email")
async def create_email(request: Request):
    agentmail_client.inboxes.create()

    return {"message": "Email created"}


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
        # Validate user has required credentials
        if not user.expedia_credentials:
            return {
                "user_id": user.user_id,
                "email": user.email,
                "success": False,
                "error": "No Expedia credentials provided"
            }
        
        if not user.payment_details:
            return {
                "user_id": user.user_id,
                "email": user.email,
                "success": False,
                "error": "No payment details provided"
            }
        
        if not user.contact_info:
            return {
                "user_id": user.user_id,
                "email": user.email,
                "success": False,
                "error": "No contact info provided"
            }
        
        try:
            agent = ExpediaAgent()
            
            # Parse user name
            name_parts = user.user_name.split()
            first_name = name_parts[0]
            last_name = name_parts[-1] if len(name_parts) > 1 else ""
            
            # Book flight and hotel using onboarding data
            result = await asyncio.to_thread(
                agent.book_parallel,
                email=user.expedia_credentials.email,
                password=user.expedia_credentials.password,
                origin=plan["flight"]["origin"],
                destination=plan["flight"]["destination"],
                departure_date=plan["dates"]["departure_date"],
                return_date=plan["dates"]["return_date"],
                hotel_location=plan["hotel"]["location"],
                check_in=plan["dates"]["departure_date"],
                check_out=plan["dates"]["return_date"],
                first_name=first_name,
                last_name=last_name,
                phone=user.contact_info.phone,
                card_number=user.payment_details.card_number,
                cardholder_name=user.payment_details.cardholder_name,
                expiration_month=user.payment_details.expiration_month,
                expiration_year=user.payment_details.expiration_year,
                cvv=user.payment_details.cvv,
                billing_address=user.payment_details.billing_address,
                # Pass preferences as string
                flight_criteria=str(plan["flight"].get("preferences", "")),
                hotel_criteria=str(plan["hotel"].get("amenities", ""))
            )
            
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
    
    # Send confirmation emails
    for result in results:
        if isinstance(result, Exception):
            result = {
                "email": "unknown@example.com",
                "success": False,
                "error": str(result)
            }
        
        send_booking_confirmation(
            to=result["email"],
            result=result
        )
    
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
        user_profiles = load_user_profiles(db, chat_session.user_ids)
        message_ids = {}
        
        for user in user_profiles:
            msg_id = send_plan_email(
                to=user.email,
                plan=final_state["current_plan"],
                session_id=session_id,
                user_id=user.user_id
            )
            message_ids[user.user_id] = msg_id
            store_message_mapping(msg_id, session_id, user.user_id)
        
        # Reset approval state for new round
        chat_session.approval_state = {}
        chat_session.agentmail_message_ids = message_ids
        chat_session.final_plan = final_state["current_plan"]
        chat_session.current_volley += 1
        chat_session.status = "pending_approval"
        db.commit()
        
        print(f"✅ New plan sent via email for session {session_id}")


# Import Optional for type hints
from typing import Optional



def main():
    print("Hello from yc-agentmail!")


if __name__ == "__main__":
    main()
