"""
Pydantic Models for Group Chat Agent System
All data structures use Pydantic for validation and type safety.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Annotated
from datetime import datetime
from typing_extensions import TypedDict


# ============================================================================
# State Schemas for LangGraph
# ============================================================================

class GroupChatState(TypedDict):
    """
    Main state for the group chat workflow.
    Uses TypedDict as recommended by LangGraph for best performance.
    """
    messages: Annotated[List[Any], "add_messages"]  # Will use add_messages reducer
    current_volley: int
    messages_per_agent: int
    active_agent: Optional[str]
    agent_message_counts: Dict[str, int]
    current_agent_index: int  # Track position in sequential order
    total_turns: int  # Total number of turns taken
    current_plan: Optional[Dict[str, Any]]  # TravelPlan as dict
    rejection_feedback: Optional[str]
    is_complete: bool


# ============================================================================
# User & Memory Models
# ============================================================================

class UserMemory(BaseModel):
    """Individual memory entry for a user"""
    memory_id: str = Field(..., description="Unique memory identifier")
    user_id: str = Field(..., description="Associated user ID")
    content: str = Field(..., description="Memory content")
    memory_type: str = Field(
        ...,
        description="Memory type: preference, interaction, constraint"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    relevance_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Relevance score for retrieval"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "mem_001",
                "user_id": "user_001",
                "content": "Prefers morning flights and window seats",
                "memory_type": "preference",
                "created_at": "2025-11-01T00:00:00",
                "relevance_score": 0.95
            }
        }


class UserPreferences(BaseModel):
    """User's travel preferences"""
    budget_range: tuple[int, int] = Field(
        ...,
        description="Budget range in USD (min, max)"
    )
    preferred_destinations: List[str] = Field(
        default_factory=list,
        description="List of preferred destination types"
    )
    travel_style: str = Field(
        ...,
        description="Travel style: adventure, relaxation, cultural, luxury, budget"
    )
    dietary_restrictions: List[str] = Field(
        default_factory=list,
        description="Dietary restrictions or preferences"
    )
    mobility_requirements: List[str] = Field(
        default_factory=list,
        description="Mobility or accessibility requirements"
    )
    preferred_airlines: List[str] = Field(
        default_factory=list,
        description="Preferred airlines"
    )
    hotel_amenities: List[str] = Field(
        default_factory=list,
        description="Required hotel amenities"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "budget_range": (1000, 3000),
                "preferred_destinations": ["beaches", "mountains"],
                "travel_style": "adventure",
                "dietary_restrictions": ["vegetarian"],
                "mobility_requirements": [],
                "preferred_airlines": ["Delta", "United"],
                "hotel_amenities": ["pool", "gym"]
            }
        }


class UserProfile(BaseModel):
    """Complete user profile with preferences and memories"""
    user_id: str = Field(..., description="Unique user identifier")
    user_name: str = Field(..., description="User's display name")
    email: str = Field(..., description="User's email address")
    preferences: UserPreferences
    memories: List[UserMemory] = Field(
        default_factory=list,
        description="User's memory history"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_001",
                "user_name": "Alice",
                "email": "alice@example.com",
                "preferences": {
                    "budget_range": (1500, 2500),
                    "preferred_destinations": ["beaches"],
                    "travel_style": "relaxation",
                    "dietary_restrictions": [],
                    "mobility_requirements": []
                },
                "memories": []
            }
        }


# ============================================================================
# Travel Plan Models
# ============================================================================

class TravelDates(BaseModel):
    """Travel date information"""
    departure_date: str = Field(
        ...,
        description="Departure date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    return_date: str = Field(
        ...,
        description="Return date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    flexibility_days: int = Field(
        default=0,
        ge=0,
        description="Number of days flexible on dates"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "departure_date": "2025-12-15",
                "return_date": "2025-12-20",
                "flexibility_days": 2
            }
        }


class FlightDetails(BaseModel):
    """Flight booking details"""
    origin: str = Field(..., description="Departure city or airport code")
    destination: str = Field(..., description="Arrival city or airport code")
    preferences: str = Field(
        ...,
        description="Flight preferences (class, stops, airline, etc.)"
    )
    max_budget_per_person: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum budget per person in USD"
    )
    preferred_departure_time: Optional[str] = Field(
        None,
        description="Preferred departure time (morning, afternoon, evening)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "origin": "LAX",
                "destination": "JFK",
                "preferences": "Economy class, prefer nonstop",
                "max_budget_per_person": 500,
                "preferred_departure_time": "morning"
            }
        }


class HotelDetails(BaseModel):
    """Hotel booking details"""
    location: str = Field(..., description="Hotel location")
    type: str = Field(
        ...,
        description="Hotel type: hotel, resort, airbnb, hostel"
    )
    amenities: List[str] = Field(
        default_factory=list,
        description="Required amenities"
    )
    star_rating_min: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Minimum star rating (1-5)"
    )
    max_budget_per_night: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum budget per night in USD"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "location": "Manhattan, New York",
                "type": "hotel",
                "amenities": ["wifi", "breakfast", "gym"],
                "star_rating_min": 3,
                "max_budget_per_night": 200
            }
        }


class BudgetBreakdown(BaseModel):
    """Budget breakdown for the trip"""
    total_per_person: int = Field(..., ge=0, description="Total cost per person")
    flight_cost: Optional[int] = Field(None, ge=0)
    hotel_cost: Optional[int] = Field(None, ge=0)
    activities_cost: Optional[int] = Field(None, ge=0)
    food_cost: Optional[int] = Field(None, ge=0)
    other_cost: Optional[int] = Field(None, ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "total_per_person": 2000,
                "flight_cost": 500,
                "hotel_cost": 800,
                "activities_cost": 400,
                "food_cost": 250,
                "other_cost": 50
            }
        }


class TravelPreferences(BaseModel):
    """Travel preferences and activities"""
    activities: List[str] = Field(
        default_factory=list,
        description="Planned activities"
    )
    dining: str = Field(
        default="casual",
        description="Dining preferences"
    )
    special_requirements: List[str] = Field(
        default_factory=list,
        description="Special requirements or needs"
    )


class TravelPlan(BaseModel):
    """Complete travel plan synthesized from group chat"""
    plan_id: str = Field(..., description="Unique plan identifier")
    dates: TravelDates
    flight: FlightDetails
    hotel: HotelDetails
    budget: BudgetBreakdown
    location: str = Field(..., description="Primary destination")
    preferences: TravelPreferences
    compromises_made: str = Field(
        ...,
        description="Explanation of compromises and how different preferences were balanced"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = Field(
        default="draft",
        description="Plan status: draft, approved, rejected"
    )
    participants: List[str] = Field(
        default_factory=list,
        description="User IDs of participants"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "plan_001",
                "dates": {
                    "departure_date": "2025-12-15",
                    "return_date": "2025-12-20",
                    "flexibility_days": 1
                },
                "flight": {
                    "origin": "LAX",
                    "destination": "JFK",
                    "preferences": "Economy, nonstop preferred",
                    "max_budget_per_person": 500
                },
                "hotel": {
                    "location": "Manhattan",
                    "type": "hotel",
                    "amenities": ["wifi", "breakfast"],
                    "star_rating_min": 3,
                    "max_budget_per_night": 200
                },
                "budget": {
                    "total_per_person": 2000,
                    "flight_cost": 500,
                    "hotel_cost": 1000,
                    "activities_cost": 300,
                    "food_cost": 200
                },
                "location": "New York City",
                "preferences": {
                    "activities": ["museums", "dining", "broadway"],
                    "dining": "variety",
                    "special_requirements": []
                },
                "compromises_made": "Balanced budget-conscious preferences with luxury desires",
                "status": "draft",
                "participants": ["user_001", "user_002"]
            }
        }


# ============================================================================
# API Request/Response Models
# ============================================================================

class StartGroupChatRequest(BaseModel):
    """Request to start a new group chat session"""
    user_ids: List[str] = Field(
        ...,
        min_length=2,
        description="List of user IDs participating (minimum 2)"
    )
    messages_per_volley: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of messages each agent sends per volley"
    )


class RejectPlanRequest(BaseModel):
    """Request to reject a travel plan"""
    user_id: str = Field(..., description="ID of user rejecting the plan")
    feedback: str = Field(
        ...,
        min_length=10,
        description="Feedback explaining why the plan was rejected"
    )


class GroupChatSessionResponse(BaseModel):
    """Response containing group chat session information"""
    session_id: str
    status: str
    current_volley: int
    total_messages: int
    participants: List[str]
    current_plan: Optional[TravelPlan] = None


class ChatMessage(BaseModel):
    """Individual chat message"""
    agent_name: str
    agent_id: str
    content: str
    timestamp: datetime
    volley: int
    turn: int


class VolleyResult(BaseModel):
    """Result from completing a volley"""
    volley_number: int
    messages_this_volley: int
    total_messages: int
    is_complete: bool
    plan_generated: bool

