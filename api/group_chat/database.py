"""
Database Layer for Group Chat Agent System
SQLAlchemy models and CRUD operations for users, memories, and chat sessions.
"""

import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, Column, String, JSON, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship, sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool

from .models import (
    UserProfile,
    UserPreferences,
    UserMemory,
    TravelPlan,
    GroupChatSessionResponse,
    ExpediaCredentials,
    PaymentDetails,
    ContactInfo
)

# Create declarative base
Base = declarative_base()

# Database URL - defaults to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./group_chat_agent.db")


# ============================================================================
# SQLAlchemy Models
# ============================================================================

class UserDB(Base):
    """Database model for users"""
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    user_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    preferences = Column(JSON, nullable=False)  # Stored as JSON
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    memories = relationship("UserMemoryDB", back_populates="user", cascade="all, delete-orphan")
    
    def to_pydantic(self) -> UserProfile:
        """Convert to Pydantic UserProfile model"""
        # Extract nested objects from preferences
        prefs_dict = self.preferences.copy() if self.preferences else {}
        
        # Extract and parse expedia_credentials
        expedia_creds_data = prefs_dict.pop("expedia_credentials", None)
        expedia_creds = ExpediaCredentials(**expedia_creds_data) if expedia_creds_data else None
        
        # Extract and parse payment_details
        payment_data = prefs_dict.pop("payment_details", None)
        payment_details = PaymentDetails(**payment_data) if payment_data else None
        
        # Extract and parse contact_info
        contact_data = prefs_dict.pop("contact_info", None)
        contact_info = ContactInfo(**contact_data) if contact_data else None
        
        # Parse remaining preferences
        user_prefs = UserPreferences(**prefs_dict) if prefs_dict else UserPreferences()
        
        return UserProfile(
            user_id=self.user_id,
            user_name=self.user_name,
            email=self.email,
            preferences=user_prefs,
            expedia_credentials=expedia_creds,
            payment_details=payment_details,
            contact_info=contact_info,
            memories=[m.to_pydantic() for m in self.memories]
        )


class UserMemoryDB(Base):
    """Database model for user memories"""
    __tablename__ = "user_memories"
    
    memory_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String, nullable=False)  # preference, interaction, constraint
    created_at = Column(DateTime, default=datetime.now)
    relevance_score = Column(Integer, nullable=True)  # Store as int (0-100)
    
    # Relationships
    user = relationship("UserDB", back_populates="memories")
    
    def to_pydantic(self) -> UserMemory:
        """Convert to Pydantic UserMemory model"""
        return UserMemory(
            memory_id=self.memory_id,
            user_id=self.user_id,
            content=self.content,
            memory_type=self.memory_type,
            created_at=self.created_at,
            relevance_score=self.relevance_score / 100.0 if self.relevance_score else None
        )


class GroupChatSessionDB(Base):
    """Database model for group chat sessions"""
    __tablename__ = "group_chat_sessions"
    
    session_id = Column(String, primary_key=True, index=True)
    user_ids = Column(JSON, nullable=False)  # List of participating user IDs
    chat_history = Column(JSON, nullable=False)  # Serialized messages
    final_plan = Column(JSON, nullable=True)  # TravelPlan as JSON
    status = Column(String, nullable=False, default="active")  # active, completed, rejected, pending_approval
    current_volley = Column(Integer, default=0)
    messages_per_agent = Column(Integer, default=10)
    approval_state = Column(JSON, nullable=True)  # Track user approvals/rejections
    agentmail_message_ids = Column(JSON, nullable=True)  # Map user_id -> message_id
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_pydantic(self) -> GroupChatSessionResponse:
        """Convert to Pydantic response model"""
        return GroupChatSessionResponse(
            session_id=self.session_id,
            status=self.status,
            current_volley=self.current_volley,
            total_messages=len(self.chat_history) if self.chat_history else 0,
            participants=self.user_ids,
            current_plan=TravelPlan(**self.final_plan) if self.final_plan else None
        )


class MessageMappingDB(Base):
    """Database model for AgentMail message ID mappings"""
    __tablename__ = "message_mappings"
    
    message_id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("group_chat_sessions.session_id"), nullable=False, index=True)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


# ============================================================================
# Database Engine and Session Setup
# ============================================================================

def get_engine():
    """Create and return database engine"""
    if DATABASE_URL.startswith("sqlite"):
        # SQLite specific settings
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
    else:
        engine = create_engine(DATABASE_URL)
    
    return engine


def init_db():
    """Initialize database and create all tables"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    return engine


def get_session() -> Session:
    """Get database session"""
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


# ============================================================================
# CRUD Operations for Users
# ============================================================================

def create_user(
    session: Session,
    user_id: str,
    user_name: str,
    email: str,
    preferences: Dict[str, Any]
) -> UserDB:
    """Create a new user"""
    user = UserDB(
        user_id=user_id,
        user_name=user_name,
        email=email,
        preferences=preferences
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user(session: Session, user_id: str) -> Optional[UserDB]:
    """Get user by ID"""
    return session.query(UserDB).filter(UserDB.user_id == user_id).first()


def get_user_by_email(session: Session, email: str) -> Optional[UserDB]:
    """Get user by email"""
    return session.query(UserDB).filter(UserDB.email == email).first()


def get_all_users(session: Session) -> List[UserDB]:
    """Get all users"""
    return session.query(UserDB).all()


def update_user_preferences(
    session: Session,
    user_id: str,
    preferences: Dict[str, Any]
) -> Optional[UserDB]:
    """Update user preferences"""
    user = get_user(session, user_id)
    if user:
        user.preferences = preferences
        user.updated_at = datetime.now()
        session.commit()
        session.refresh(user)
    return user


def delete_user(session: Session, user_id: str) -> bool:
    """Delete user and all associated memories"""
    user = get_user(session, user_id)
    if user:
        session.delete(user)
        session.commit()
        return True
    return False


# ============================================================================
# CRUD Operations for Memories
# ============================================================================

def create_memory(
    session: Session,
    memory_id: str,
    user_id: str,
    content: str,
    memory_type: str,
    relevance_score: Optional[float] = None
) -> UserMemoryDB:
    """Create a new memory for a user"""
    memory = UserMemoryDB(
        memory_id=memory_id,
        user_id=user_id,
        content=content,
        memory_type=memory_type,
        relevance_score=int(relevance_score * 100) if relevance_score else None
    )
    session.add(memory)
    session.commit()
    session.refresh(memory)
    return memory


def get_user_memories(
    session: Session,
    user_id: str,
    memory_type: Optional[str] = None
) -> List[UserMemoryDB]:
    """Get all memories for a user, optionally filtered by type"""
    query = session.query(UserMemoryDB).filter(UserMemoryDB.user_id == user_id)
    if memory_type:
        query = query.filter(UserMemoryDB.memory_type == memory_type)
    return query.order_by(UserMemoryDB.created_at.desc()).all()


def get_memory(session: Session, memory_id: str) -> Optional[UserMemoryDB]:
    """Get a specific memory by ID"""
    return session.query(UserMemoryDB).filter(UserMemoryDB.memory_id == memory_id).first()


def delete_memory(session: Session, memory_id: str) -> bool:
    """Delete a specific memory"""
    memory = get_memory(session, memory_id)
    if memory:
        session.delete(memory)
        session.commit()
        return True
    return False


# ============================================================================
# CRUD Operations for Group Chat Sessions
# ============================================================================

def create_session(
    session: Session,
    session_id: str,
    user_ids: List[str],
    messages_per_agent: int = 10
) -> GroupChatSessionDB:
    """Create a new group chat session"""
    chat_session = GroupChatSessionDB(
        session_id=session_id,
        user_ids=user_ids,
        chat_history=[],
        status="active",
        messages_per_agent=messages_per_agent
    )
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


def get_chat_session(session: Session, session_id: str) -> Optional[GroupChatSessionDB]:
    """Get a group chat session by ID"""
    return session.query(GroupChatSessionDB).filter(
        GroupChatSessionDB.session_id == session_id
    ).first()


def update_chat_session(
    session: Session,
    session_id: str,
    chat_history: Optional[List[Dict]] = None,
    final_plan: Optional[Dict] = None,
    status: Optional[str] = None,
    current_volley: Optional[int] = None,
    approval_state: Optional[Dict] = None,
    agentmail_message_ids: Optional[Dict] = None
) -> Optional[GroupChatSessionDB]:
    """Update a group chat session"""
    chat_session = get_chat_session(session, session_id)
    if chat_session:
        if chat_history is not None:
            chat_session.chat_history = chat_history
        if final_plan is not None:
            chat_session.final_plan = final_plan
        if status is not None:
            chat_session.status = status
        if current_volley is not None:
            chat_session.current_volley = current_volley
        if approval_state is not None:
            chat_session.approval_state = approval_state
        if agentmail_message_ids is not None:
            chat_session.agentmail_message_ids = agentmail_message_ids
        chat_session.updated_at = datetime.now()
        session.commit()
        session.refresh(chat_session)
    return chat_session


def get_user_sessions(session: Session, user_id: str) -> List[GroupChatSessionDB]:
    """Get all sessions a user has participated in"""
    return session.query(GroupChatSessionDB).filter(
        GroupChatSessionDB.user_ids.contains(user_id)
    ).order_by(GroupChatSessionDB.created_at.desc()).all()


def delete_chat_session(session: Session, session_id: str) -> bool:
    """Delete a group chat session"""
    chat_session = get_chat_session(session, session_id)
    if chat_session:
        session.delete(chat_session)
        session.commit()
        return True
    return False


# ============================================================================
# Helper Functions
# ============================================================================

def load_user_profile(session: Session, user_id: str) -> Optional[UserProfile]:
    """Load complete user profile with memories as Pydantic model"""
    user = get_user(session, user_id)
    if user:
        return user.to_pydantic()
    return None


def load_user_profiles(session: Session, user_ids: List[str]) -> List[UserProfile]:
    """Load multiple user profiles"""
    profiles = []
    for user_id in user_ids:
        profile = load_user_profile(session, user_id)
        if profile:
            profiles.append(profile)
    return profiles


# ============================================================================
# AgentMail Integration Helpers
# ============================================================================

def update_approval_state(
    session: Session,
    session_id: str,
    user_id: str,
    approved: bool,
    feedback: Optional[str] = None
) -> Dict[str, bool]:
    """
    Update approval state for a user.
    Returns dict with 'all_approved' and 'any_rejected' flags.
    
    Args:
        session: Database session
        session_id: Group chat session ID
        user_id: User ID who is approving/rejecting
        approved: True if approved, False if rejected
        feedback: Optional feedback for rejection
    
    Returns:
        Dict with 'all_approved' and 'any_rejected' boolean flags
    """
    chat_session = get_chat_session(session, session_id)
    if not chat_session:
        return {"all_approved": False, "any_rejected": False}
    
    approval_state = chat_session.approval_state or {}
    approval_state[user_id] = {
        "approved": approved,
        "feedback": feedback,
        "timestamp": datetime.now().isoformat()
    }
    
    chat_session.approval_state = approval_state
    session.commit()
    
    # Check if all users have approved
    all_approved = all(
        approval_state.get(uid, {}).get("approved", False)
        for uid in chat_session.user_ids
    )
    
    # Check if any user rejected with feedback
    any_rejected = any(
        approval_state.get(uid, {}).get("approved") == False
        and approval_state.get(uid, {}).get("feedback")
        for uid in chat_session.user_ids
    )
    
    return {
        "all_approved": all_approved,
        "any_rejected": any_rejected
    }


def store_message_mapping(session: Session, message_id: str, session_id: str, user_id: str):
    """
    Store mapping from AgentMail message_id to session and user in database.
    
    Args:
        session: Database session
        message_id: AgentMail message ID
        session_id: Group chat session ID
        user_id: User ID who received the message
    """
    mapping = MessageMappingDB(
        message_id=message_id,
        session_id=session_id,
        user_id=user_id
    )
    session.add(mapping)
    session.commit()
    session.refresh(mapping)


def get_session_by_message_id(
    session: Session,
    message_id: str
) -> Optional[tuple[GroupChatSessionDB, str]]:
    """
    Get chat session and user_id by AgentMail message_id from database.
    
    Args:
        session: Database session
        message_id: AgentMail message ID
    
    Returns:
        Tuple of (GroupChatSessionDB, user_id) or None if not found
    """
    mapping = session.query(MessageMappingDB).filter(
        MessageMappingDB.message_id == message_id
    ).first()
    
    if not mapping:
        return None
    
    chat_session = get_chat_session(session, mapping.session_id)
    
    if not chat_session:
        return None
    
    return (chat_session, mapping.user_id)


# Initialize database on module import
init_db()

