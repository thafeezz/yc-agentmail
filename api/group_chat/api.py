"""
FastAPI Router for Group Chat Agent Endpoints
Provides REST API for managing group chat sessions and travel planning.
"""

import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from .models import (
    StartGroupChatRequest,
    RejectPlanRequest,
    GroupChatSessionResponse,
    TravelPlan,
    VolleyResult
)
from .database import (
    get_session,
    load_user_profiles,
    create_session as create_db_session,
    get_chat_session,
    update_chat_session
)
from .orchestrator import GroupChatOrchestrator

# Create router
router = APIRouter(prefix="/group-chat", tags=["Group Chat"])

# In-memory storage for active orchestrators (in production, use Redis or similar)
active_orchestrators: Dict[str, GroupChatOrchestrator] = {}
active_states: Dict[str, Dict[str, Any]] = {}


def get_db() -> Session:
    """Dependency to get database session"""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@router.post("/start", response_model=GroupChatSessionResponse)
async def start_group_chat(
    request: StartGroupChatRequest,
    db: Session = Depends(get_db)
):
    """
    Start a new group chat session for collaborative travel planning.
    
    Args:
        request: StartGroupChatRequest with user_ids and messages_per_volley
        
    Returns:
        GroupChatSessionResponse with session_id and initial status
        
    Example:
        ```json
        {
          "user_ids": ["user_001", "user_002", "user_003"],
          "messages_per_volley": 10
        }
        ```
    """
    try:
        # Validate user count
        if len(request.user_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 users required for group chat"
            )
        
        # Load user profiles from database
        user_profiles = load_user_profiles(db, request.user_ids)
        
        if len(user_profiles) != len(request.user_ids):
            missing = set(request.user_ids) - {u.user_id for u in user_profiles}
            raise HTTPException(
                status_code=404,
                detail=f"Users not found: {missing}"
            )
        
        # Generate session ID
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        
        # Create orchestrator
        orchestrator = GroupChatOrchestrator(
            users=user_profiles,
            messages_per_volley=request.messages_per_volley
        )
        
        # Store in memory (in production, serialize and store in Redis)
        active_orchestrators[session_id] = orchestrator
        
        # Create database session record
        db_session = create_db_session(
            db,
            session_id=session_id,
            user_ids=request.user_ids,
            messages_per_agent=request.messages_per_volley
        )
        
        # Run first volley
        print(f"\n🚀 Starting first volley for session {session_id}")
        final_state = orchestrator.run_volley()
        
        # Store state
        active_states[session_id] = final_state
        
        # Convert messages to serializable format
        serializable_messages = [
            {
                "content": msg.content,
                "type": msg.type,
                "name": getattr(msg, "name", "Unknown")
            }
            for msg in final_state.get("messages", [])
        ]
        
        # Check if plan was generated successfully
        if final_state.get("current_plan") and "error" not in final_state["current_plan"]:
            from api.agentmail_helper import send_plan_email
            from api.group_chat.database import store_message_mapping
            
            plan = final_state["current_plan"]
            message_ids = {}
            
            # Send plan to all participants via email
            print(f"📧 Sending plan emails to {len(user_profiles)} participants...")
            for user in user_profiles:
                msg_id = send_plan_email(
                    to=user.email,
                    plan=plan,
                    session_id=session_id,
                    user_id=user.user_id
                )
                message_ids[user.user_id] = msg_id
                
                # Store mapping for webhook lookup
                store_message_mapping(msg_id, session_id, user.user_id)
            
            # Update database with pending approval status
            update_chat_session(
                db,
                session_id=session_id,
                chat_history=serializable_messages,
                final_plan=plan,
                current_volley=1,
                status="pending_approval",
                agentmail_message_ids=message_ids
            )
            
            # Return response without plan (sent via email)
            return GroupChatSessionResponse(
                session_id=session_id,
                status="pending_approval",
                current_volley=1,
                total_messages=len(final_state.get("messages", [])),
                participants=request.user_ids,
                current_plan=None  # Don't return in API, sent via email
            )
        else:
            # Plan generation failed or validation failed
            update_chat_session(
                db,
                session_id=session_id,
                chat_history=serializable_messages,
                final_plan=final_state.get("current_plan"),
                current_volley=1,
                status="error"
            )
            
            return GroupChatSessionResponse(
                session_id=session_id,
                status="error",
                current_volley=1,
                total_messages=len(final_state.get("messages", [])),
                participants=request.user_ids,
                current_plan=None
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start group chat: {str(e)}"
        )


@router.post("/{session_id}/reject", response_model=GroupChatSessionResponse)
async def reject_plan(
    session_id: str,
    request: RejectPlanRequest,
    db: Session = Depends(get_db)
):
    """
    Reject the current travel plan and provide feedback.
    Automatically starts a new volley with the feedback.
    
    Args:
        session_id: The group chat session ID
        request: RejectPlanRequest with user_id and feedback
        
    Returns:
        Updated GroupChatSessionResponse with new volley results
        
    Example:
        ```json
        {
          "user_id": "user_001",
          "feedback": "The budget is too high for me. Can we find more affordable options?"
        }
        ```
    """
    try:
        # Get orchestrator and state
        orchestrator = active_orchestrators.get(session_id)
        current_state = active_states.get(session_id)
        
        if not orchestrator or not current_state:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        # Verify user is participant
        if request.user_id not in orchestrator.user_ids:
            raise HTTPException(
                status_code=403,
                detail=f"User {request.user_id} is not a participant in this session"
            )
        
        # Handle rejection
        updated_state = orchestrator.handle_rejection(
            current_state=current_state,
            feedback=request.feedback,
            user_id=request.user_id
        )
        
        # Run new volley
        print(f"\n🔄 Starting new volley after rejection...")
        final_state = orchestrator.run_volley(initial_state=updated_state)
        
        # Update stored state
        active_states[session_id] = final_state
        
        # Convert messages to serializable format
        serializable_messages = [
            {
                "content": msg.content,
                "type": msg.type,
                "name": getattr(msg, "name", "Unknown")
            }
            for msg in final_state.get("messages", [])
        ]
        
        # Update database
        update_chat_session(
            db,
            session_id=session_id,
            chat_history=serializable_messages,
            final_plan=final_state.get("current_plan"),
            current_volley=final_state.get("current_volley", 0) + 1,
            status="completed" if final_state.get("is_complete") else "active"
        )
        
        return GroupChatSessionResponse(
            session_id=session_id,
            status="completed" if final_state.get("is_complete") else "active",
            current_volley=final_state.get("current_volley", 0) + 1,
            total_messages=len(final_state.get("messages", [])),
            participants=orchestrator.user_ids,
            current_plan=TravelPlan(**final_state["current_plan"]) if final_state.get("current_plan") and "error" not in final_state["current_plan"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reject plan: {str(e)}"
        )


@router.get("/{session_id}/status", response_model=GroupChatSessionResponse)
async def get_session_status(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the current status of a group chat session.
    
    Args:
        session_id: The group chat session ID
        
    Returns:
        GroupChatSessionResponse with current session status
    """
    try:
        # Try to get from active sessions first
        if session_id in active_states:
            state = active_states[session_id]
            orchestrator = active_orchestrators[session_id]
            
            return GroupChatSessionResponse(
                session_id=session_id,
                status="completed" if state.get("is_complete") else "active",
                current_volley=state.get("current_volley", 0) + 1,
                total_messages=len(state.get("messages", [])),
                participants=orchestrator.user_ids,
                current_plan=TravelPlan(**state["current_plan"]) if state.get("current_plan") and "error" not in state["current_plan"] else None
            )
        
        # Otherwise get from database
        db_session = get_chat_session(db, session_id)
        if not db_session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        return db_session.to_pydantic()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session status: {str(e)}"
        )


@router.get("/{session_id}/messages")
async def get_chat_messages(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all messages from a group chat session.
    
    Args:
        session_id: The group chat session ID
        
    Returns:
        List of chat messages
    """
    try:
        # Try active sessions first
        if session_id in active_states:
            state = active_states[session_id]
            messages = [
                {
                    "content": msg.content,
                    "type": msg.type,
                    "name": getattr(msg, "name", "Unknown"),
                    "timestamp": None  # Would need to track separately
                }
                for msg in state.get("messages", [])
            ]
            return {"session_id": session_id, "messages": messages}
        
        # Otherwise get from database
        db_session = get_chat_session(db, session_id)
        if not db_session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        return {
            "session_id": session_id,
            "messages": db_session.chat_history or []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get messages: {str(e)}"
        )


@router.post("/{session_id}/approve")
async def approve_plan(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Approve the current travel plan and finalize the session.
    
    Args:
        session_id: The group chat session ID
        
    Returns:
        Final approved TravelPlan
    """
    try:
        # Get session state
        state = active_states.get(session_id)
        
        if not state:
            # Try database
            db_session = get_chat_session(db, session_id)
            if not db_session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} not found"
                )
            
            if not db_session.final_plan:
                raise HTTPException(
                    status_code=400,
                    detail="No plan available to approve"
                )
            
            # Update status
            update_chat_session(db, session_id, status="approved")
            
            return {
                "status": "approved",
                "plan": TravelPlan(**db_session.final_plan)
            }
        
        # Update state and database
        if not state.get("current_plan"):
            raise HTTPException(
                status_code=400,
                detail="No plan available to approve"
            )
        
        plan = state["current_plan"].copy()
        plan["status"] = "approved"
        
        update_chat_session(
            db,
            session_id=session_id,
            final_plan=plan,
            status="approved"
        )
        
        # Clean up active sessions
        if session_id in active_orchestrators:
            del active_orchestrators[session_id]
        if session_id in active_states:
            del active_states[session_id]
        
        return {
            "status": "approved",
            "plan": TravelPlan(**plan)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve plan: {str(e)}"
        )

