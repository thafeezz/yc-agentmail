"""
Group Chat Agent System for Multi-User Travel Planning
A LangGraph-based multi-agent system where user agents collaborate
to create travel plans through turn-based group chat.
"""

from .models import (
    UserProfile,
    UserPreferences,
    UserMemory,
    TravelPlan,
    TravelDates,
    FlightDetails,
    HotelDetails,
    BudgetBreakdown,
    TravelPreferences,
    GroupChatState,
    StartGroupChatRequest,
    RejectPlanRequest,
    GroupChatSessionResponse,
    ChatMessage,
    VolleyResult,
)

__all__ = [
    "UserProfile",
    "UserPreferences",
    "UserMemory",
    "TravelPlan",
    "TravelDates",
    "FlightDetails",
    "HotelDetails",
    "BudgetBreakdown",
    "TravelPreferences",
    "GroupChatState",
    "StartGroupChatRequest",
    "RejectPlanRequest",
    "GroupChatSessionResponse",
    "ChatMessage",
    "VolleyResult",
]

__version__ = "1.0.0"

