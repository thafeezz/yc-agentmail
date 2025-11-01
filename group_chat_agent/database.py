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
    GroupChatSessionResponse
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
        return UserProfile(
            user_id=self.user_id,
            user_name=self.user_name,
            email=self.email,
            preferences=UserPreferences(**self.preferences),
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
    status = Column(String, nullable=False, default="active")  # active, completed, rejected
    current_volley = Column(Integer, default=0)
    messages_per_agent = Column(Integer, default=10)
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
    current_volley: Optional[int] = None
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


# Initialize database on module import
init_db()

