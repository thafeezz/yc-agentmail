"""
Expedia Agent API Service
FastAPI service that exposes the Expedia browser agent as REST endpoints.

Features:
- RESTful API for booking flights and hotels
- Parallel booking support
- Laminar observability integration
- Flexible date format handling
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
from .expedia_agent import ExpediaAgent, initialize_observability
from typing import Tuple

# Group Chat imports for plan-driven booking
try:
    from .group_chat.models import TravelPlan
    from .group_chat.database import (
        get_session as gc_get_session,
        get_chat_session as gc_get_chat_session,
    )
    GROUP_CHAT_AVAILABLE = True
except Exception as _e:
    GROUP_CHAT_AVAILABLE = False
    print(f"⚠️  Group Chat DB access not available: {_e}")

# Load environment variables from .env file
load_dotenv()

# Initialize observability if Laminar is configured
if os.getenv("LMNR_PROJECT_API_KEY"):
    initialize_observability()

app = FastAPI(
    title="Expedia Booking Agent API",
    description="Automated flight and hotel booking service using Browser Use",
    version="1.0.0"
)

# Import and include Group Chat Agent router
try:
    from .group_chat_agent.api import router as group_chat_router
    app.include_router(group_chat_router)
    print("✅ Group Chat Agent endpoints loaded")
except ImportError as e:
    print(f"⚠️  Group Chat Agent not available: {e}")


class Address(BaseModel):
    """Billing address model"""
    street: str
    city: str
    state: str
    zip: str
    country: str = "USA"


class FlightSearchCriteria(BaseModel):
    """Criteria for flight search and selection"""
    max_price: Optional[int] = Field(None, description="Maximum acceptable price")
    preferred_airlines: Optional[List[str]] = Field(None, description="Preferred airlines list")
    max_stops: str = Field("any", description="Maximum stops: 'nonstop', '1stop', or 'any'")
    departure_time: Optional[str] = Field(None, description="Preferred departure time: 'morning', 'afternoon', 'evening'")
    refundable_only: bool = Field(False, description="Only show refundable flights")


class HotelSearchCriteria(BaseModel):
    """Criteria for hotel search and selection"""
    max_price: Optional[int] = Field(None, description="Maximum price per night")
    min_stars: Optional[int] = Field(None, ge=1, le=5, description="Minimum star rating (1-5)")
    min_guest_rating: Optional[float] = Field(None, ge=0, le=10, description="Minimum guest rating (0-10)")
    required_amenities: Optional[List[str]] = Field(None, description="Required amenities (e.g., ['wifi', 'pool', 'parking'])")
    free_cancellation: bool = Field(False, description="Filter for free cancellation only")
    property_types: Optional[List[str]] = Field(None, description="Property types (e.g., ['hotel', 'resort'])")


class AccountCreationRequest(BaseModel):
    """Request model for creating a new Expedia account"""
    email: str = Field(..., description="Account email address")
    password: str = Field(..., description="Account password")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    llm_model: str = Field("claude-sonnet-4", description="AI model to use")
    proxy_country_code: str = Field("us", description="Proxy country code")


class EmailVerificationRequest(BaseModel):
    """Request model for email verification"""
    verification_code: str = Field(..., description="Verification code from email")


class BookingRequest(BaseModel):
    """Request model for booking flights and hotels"""
    
    # Authentication
    email: str = Field(..., description="Expedia account email")
    password: str = Field(..., description="Expedia account password")
    create_account: bool = Field(False, description="Create new account if True")
    
    # Flight details
    origin: str = Field(..., description="Departure city or airport code")
    destination: str = Field(..., description="Arrival city or airport code")
    departure_date: str = Field(..., description="Departure date (various formats accepted)")
    return_date: Optional[str] = Field(None, description="Return date for round trip")
    
    # Hotel details
    hotel_location: str = Field(..., description="Hotel location (city or address)")
    check_in: str = Field(..., description="Hotel check-in date")
    check_out: str = Field(..., description="Hotel check-out date")
    
    # Traveler information
    first_name: str = Field(..., description="Traveler first name")
    last_name: str = Field(..., description="Traveler last name")
    phone: str = Field(..., description="Contact phone number")
    
    # Payment information
    card_number: str = Field(..., description="Credit card number")
    cardholder_name: str = Field(..., description="Name on card")
    expiration_month: str = Field(..., description="Card expiration month (01-12)")
    expiration_year: str = Field(..., description="Card expiration year (YYYY)")
    cvv: str = Field(..., description="Card CVV/security code")
    billing_address: Address = Field(..., description="Billing address")
    
    # Options
    passengers: int = Field(1, ge=1, le=9, description="Number of passengers/guests")
    flight_preference: str = Field("cheapest", description="Flight preference")
    hotel_preference: str = Field("highest rated under $200", description="Hotel preference")
    parallel_booking: bool = Field(True, description="Use parallel booking (faster)")
    
    # Advanced Options
    llm_model: str = Field(
        "claude-sonnet-4", 
        description="AI model: claude-sonnet-4 (most powerful), o3, gemini-flash-latest, gpt-4.1"
    )
    proxy_country_code: str = Field(
        "us",
        description="Proxy country code for stealth (us, uk, ca, etc.) - helps avoid CAPTCHAs"
    )
    use_hybrid: bool = Field(
        True,
        description="Use hybrid Playwright + AI mode for 5-10x speed improvement"
    )
    agent_profile: str = Field(
        "COMPLETE_BOOKING",
        description="Tool profile: COMPLETE_BOOKING, FLIGHT_BOOKING, HOTEL_BOOKING, FULL_ACCESS"
    )
    
    # Search Filters & Criteria
    flight_criteria: Optional[FlightSearchCriteria] = Field(
        None,
        description="Advanced flight search and selection criteria"
    )
    hotel_criteria: Optional[HotelSearchCriteria] = Field(
        None,
        description="Advanced hotel search and selection criteria"
    )
    
    @validator('departure_date', 'return_date', 'check_in', 'check_out', pre=True)
    def parse_date(cls, v):
        """Parse various date formats to YYYY-MM-DD"""
        if v is None:
            return v
        
        # If already in correct format, return as-is
        if isinstance(v, str) and len(v) == 10 and v[4] == '-' and v[7] == '-':
            return v
        
        # Try to parse various date formats
        date_formats = [
            '%Y-%m-%d',      # 2025-12-15
            '%m/%d/%Y',      # 12/15/2025
            '%d/%m/%Y',      # 15/12/2025
            '%B %d, %Y',     # December 15, 2025
            '%b %d, %Y',     # Dec 15, 2025
            '%Y/%m/%d',      # 2025/12/15
            '%d-%m-%Y',      # 15-12-2025
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(str(v), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If we couldn't parse it, return as-is and let the agent handle it
        return str(v)


class BookingResponse(BaseModel):
    """Response model for booking operations"""
    status: str
    message: str
    booking_id: Optional[str] = None
    booking_mode: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==========================
# Plan-driven booking shapes
# ==========================

class AuthCredentials(BaseModel):
    email: str
    password: str


class TravelerInfo(BaseModel):
    first_name: str
    last_name: str
    phone: str


class PaymentDetails(BaseModel):
    card_number: str
    cardholder_name: str
    expiration_month: str
    expiration_year: str
    cvv: str
    billing_address: Address


class PlanBookingRequest(BaseModel):
    credentials: AuthCredentials
    traveler: TravelerInfo
    payment: PaymentDetails
    passengers: Optional[int] = Field(None, ge=1, le=9)
    parallel_booking: bool = True
    flight_criteria: Optional[FlightSearchCriteria] = None
    hotel_criteria: Optional[HotelSearchCriteria] = None
    llm_model: str = Field("claude-sonnet-4")
    proxy_country_code: str = Field("us")
    use_hybrid: bool = True
    agent_profile: str = Field("COMPLETE_BOOKING")
    create_account: bool = False


# ==========================
# Helpers: mapping TravelPlan → BookingRequest
# ==========================

def _derive_flight_criteria_from_plan(plan: Dict[str, Any]) -> Optional[FlightSearchCriteria]:
    try:
        flight = plan.get("flight", {})
        prefs = (flight.get("preferences") or "").lower()
        max_stops = "any"
        if "nonstop" in prefs or "non-stop" in prefs:
            max_stops = "nonstop"
        elif "1 stop" in prefs or "one stop" in prefs:
            max_stops = "1stop"
        return FlightSearchCriteria(
            max_price=flight.get("max_budget_per_person"),
            preferred_airlines=None,
            max_stops=max_stops,
            departure_time=flight.get("preferred_departure_time"),
            refundable_only=False,
        )
    except Exception:
        return None


def _derive_hotel_criteria_from_plan(plan: Dict[str, Any]) -> Optional[HotelSearchCriteria]:
    try:
        hotel = plan.get("hotel", {})
        return HotelSearchCriteria(
            max_price=hotel.get("max_budget_per_night"),
            min_stars=hotel.get("star_rating_min"),
            min_guest_rating=None,
            required_amenities=hotel.get("amenities") or [],
            free_cancellation=False,
            property_types=None,
        )
    except Exception:
        return None


def build_booking_request_from_plan(plan: Dict[str, Any], payload: PlanBookingRequest) -> "BookingRequest":
    # Handle both Dict and Pydantic TravelPlan objects
    if isinstance(plan, dict):
        participants = plan.get("participants", [])
        hotel = plan.get("hotel", {})
        flight = plan.get("flight", {})
        dates = plan.get("dates", {})
        location = plan.get("location")
    else:
        # It's a Pydantic model
        participants = getattr(plan, "participants", [])
        hotel = plan.hotel if hasattr(plan, "hotel") else {}
        flight = plan.flight if hasattr(plan, "flight") else {}
        dates = plan.dates if hasattr(plan, "dates") else {}
        location = getattr(plan, "location", None)
    
    passengers = payload.passengers if payload.passengers is not None else (len(participants) if participants else 1)
    
    # Get values depending on type
    if isinstance(plan, dict):
        hotel_location = hotel.get("location") if hotel.get("location") else location
        flight_pref = flight.get("preferences") if flight.get("preferences") else "cheapest"
        hotel_budget = hotel.get("max_budget_per_night")
        flight_origin = flight.get("origin")
        flight_destination = flight.get("destination")
        departure_date = dates.get("departure_date")
        return_date = dates.get("return_date")
    else:
        # Pydantic objects
        hotel_location = hotel.location if hasattr(hotel, "location") and hotel.location else location
        flight_pref = flight.preferences if hasattr(flight, "preferences") and flight.preferences else "cheapest"
        hotel_budget = hotel.max_budget_per_night if hasattr(hotel, "max_budget_per_night") else None
        flight_origin = flight.origin if hasattr(flight, "origin") else None
        flight_destination = flight.destination if hasattr(flight, "destination") else None
        departure_date = dates.departure_date if hasattr(dates, "departure_date") else None
        return_date = dates.return_date if hasattr(dates, "return_date") else None
    
    hotel_pref = (
        f"highest rated under ${hotel_budget}" if hotel_budget else "highest rated under $200"
    )

    # Prefer explicit criteria from payload; otherwise derive from plan
    # Convert to dict for the derive functions
    plan_dict = plan if isinstance(plan, dict) else plan.dict()
    flight_crit = payload.flight_criteria or _derive_flight_criteria_from_plan(plan_dict)
    hotel_crit = payload.hotel_criteria or _derive_hotel_criteria_from_plan(plan_dict)

    return BookingRequest(
        # Auth
        email=payload.credentials.email,
        password=payload.credentials.password,
        create_account=payload.create_account,
        # Flight
        origin=flight_origin,
        destination=flight_destination,
        departure_date=departure_date,
        return_date=return_date,
        # Hotel
        hotel_location=hotel_location,
        check_in=departure_date,
        check_out=return_date,
        # Traveler
        first_name=payload.traveler.first_name,
        last_name=payload.traveler.last_name,
        phone=payload.traveler.phone,
        # Payment
        card_number=payload.payment.card_number,
        cardholder_name=payload.payment.cardholder_name,
        expiration_month=payload.payment.expiration_month,
        expiration_year=payload.payment.expiration_year,
        cvv=payload.payment.cvv,
        billing_address=payload.payment.billing_address,
        # Options
        passengers=passengers,
        flight_preference=flight_pref,
        hotel_preference=hotel_pref,
        parallel_booking=payload.parallel_booking,
        # Advanced
        llm_model=payload.llm_model,
        proxy_country_code=payload.proxy_country_code,
        use_hybrid=payload.use_hybrid,
        agent_profile=payload.agent_profile,
        # Criteria
        flight_criteria=flight_crit,
        hotel_criteria=hotel_crit,
    )


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    browser_use_configured: bool
    laminar_configured: bool


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    """
    return HealthResponse(
        status="healthy",
        service="expedia-booking-agent",
        browser_use_configured=bool(os.getenv("BROWSER_USE_API_KEY")),
        laminar_configured=bool(os.getenv("LMNR_PROJECT_API_KEY"))
    )


@app.post("/book", response_model=BookingResponse)
async def book_flight_and_hotel(request: BookingRequest):
    """
    Book a flight and hotel on Expedia.
    
    This endpoint handles the complete booking flow:
    1. Login/signup to Expedia
    2. Search for flights and hotels (in parallel if enabled)
    3. Select options based on preferences
    4. Fill traveler information
    5. Process payment
    6. Return confirmation
    
    Args:
        request: Booking request with all necessary details
        
    Returns:
        Booking confirmation with results
    """
    try:
        # Initialize agent with advanced model and stealth features
        agent = ExpediaAgent(
            llm_model=request.llm_model,
            proxy_country_code=request.proxy_country_code
        )
        
        # Set hybrid mode preference
        agent.use_hybrid = request.use_hybrid
        if not request.use_hybrid:
            print("ℹ️  Hybrid mode disabled - using AI-only approach")
        
        # Prepare billing address
        billing_address = request.billing_address.dict()
        
        # Execute booking based on mode
        if request.parallel_booking:
            result = agent.book_parallel(
                # Auth
                email=request.email,
                password=request.password,
                # Flight
                origin=request.origin,
                destination=request.destination,
                departure_date=request.departure_date,
                return_date=request.return_date or "",
                # Hotel
                hotel_location=request.hotel_location,
                check_in=request.check_in,
                check_out=request.check_out,
                # Traveler
                first_name=request.first_name,
                last_name=request.last_name,
                phone=request.phone,
                # Payment
                card_number=request.card_number,
                cardholder_name=request.cardholder_name,
                expiration_month=request.expiration_month,
                expiration_year=request.expiration_year,
                cvv=request.cvv,
                billing_address=billing_address,
                # Options
                passengers=request.passengers,
                flight_preference=request.flight_preference,
                hotel_preference=request.hotel_preference,
            )
        else:
            result = agent.book_flight_and_hotel_package(
                # Auth
                email=request.email,
                password=request.password,
                # Flight
                origin=request.origin,
                destination=request.destination,
                departure_date=request.departure_date,
                return_date=request.return_date or "",
                # Hotel
                hotel_location=request.hotel_location,
                check_in=request.check_in,
                check_out=request.check_out,
                # Traveler
                first_name=request.first_name,
                last_name=request.last_name,
                phone=request.phone,
                # Payment
                card_number=request.card_number,
                cardholder_name=request.cardholder_name,
                expiration_month=request.expiration_month,
                expiration_year=request.expiration_year,
                cvv=request.cvv,
                billing_address=billing_address,
                # Options
                passengers=request.passengers,
                flight_preference=request.flight_preference,
                hotel_preference=request.hotel_preference,
                create_account=request.create_account,
            )
        
        # Cleanup
        agent.cleanup()
        
        if result["status"] == "success":
            return BookingResponse(
                status="success",
                message=result.get("message", "Booking completed successfully"),
                booking_mode=result.get("booking_mode", "sequential"),
                results=result.get("results")
            )
        else:
            return BookingResponse(
                status="error",
                message=result.get("message", "Booking failed"),
                error=result.get("message"),
                results=result.get("results")
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Booking failed: {str(e)}"
        )


@app.post("/group-chat/{session_id}/book", response_model=BookingResponse, summary="Book from approved group travel plan")
async def book_from_plan(
    session_id: str,
    payload: PlanBookingRequest,
    segment: str = "both",  # both|flight|hotel
    force: bool = False,
):
    """
    Execute booking based on an approved `TravelPlan` produced by the Group Chat.

    - segment="both" uses combined flight+hotel booking
    - segment="flight" or "hotel" runs the respective flow only
    - set force=true to bypass approval status check
    """
    if not GROUP_CHAT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Group Chat subsystem not available")

    # Load session and plan
    db = gc_get_session()
    try:
        db_session = gc_get_chat_session(db, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        if not db_session.final_plan:
            raise HTTPException(status_code=400, detail="No plan available to book")
        if not force and db_session.status != "approved":
            raise HTTPException(status_code=400, detail="Plan must be approved before booking (use force=true to override)")

        plan = TravelPlan(**db_session.final_plan)
        request = build_booking_request_from_plan(plan, payload)

        # Initialize agent
        agent = ExpediaAgent(
            llm_model=request.llm_model,
            proxy_country_code=request.proxy_country_code,
        )
        agent.use_hybrid = request.use_hybrid

        billing_address = request.billing_address.dict()

        if segment not in {"both", "flight", "hotel"}:
            raise HTTPException(status_code=400, detail="segment must be one of: both, flight, hotel")

        try:
            if segment == "both":
                if request.parallel_booking:
                    result = agent.book_parallel(
                        email=request.email,
                        password=request.password,
                        origin=request.origin,
                        destination=request.destination,
                        departure_date=request.departure_date,
                        return_date=request.return_date or "",
                        hotel_location=request.hotel_location,
                        check_in=request.check_in,
                        check_out=request.check_out,
                        first_name=request.first_name,
                        last_name=request.last_name,
                        phone=request.phone,
                        card_number=request.card_number,
                        cardholder_name=request.cardholder_name,
                        expiration_month=request.expiration_month,
                        expiration_year=request.expiration_year,
                        cvv=request.cvv,
                        billing_address=billing_address,
                        passengers=request.passengers,
                        flight_preference=request.flight_preference,
                        hotel_preference=request.hotel_preference,
                    )
                else:
                    result = agent.book_flight_and_hotel_package(
                        email=request.email,
                        password=request.password,
                        origin=request.origin,
                        destination=request.destination,
                        departure_date=request.departure_date,
                        return_date=request.return_date or "",
                        hotel_location=request.hotel_location,
                        check_in=request.check_in,
                        check_out=request.check_out,
                        first_name=request.first_name,
                        last_name=request.last_name,
                        phone=request.phone,
                        card_number=request.card_number,
                        cardholder_name=request.cardholder_name,
                        expiration_month=request.expiration_month,
                        expiration_year=request.expiration_year,
                        cvv=request.cvv,
                        billing_address=billing_address,
                        passengers=request.passengers,
                        flight_preference=request.flight_preference,
                        hotel_preference=request.hotel_preference,
                        create_account=request.create_account,
                    )

                agent.cleanup()
                if result.get("status") == "success":
                    return BookingResponse(
                        status="success",
                        message=result.get("message", "Booking completed successfully"),
                        booking_mode=result.get("booking_mode", "sequential"),
                        results=result.get("results"),
                    )
                return BookingResponse(status="error", message=result.get("message", "Booking failed"), error=result.get("message"), results=result.get("results"))

            elif segment == "flight":
                # Flight-only flow
                agent.create_profile()
                agent.create_session()
                agent.login(email=request.email, password=request.password)
                search = agent.search_flights(
                    origin=request.origin,
                    destination=request.destination,
                    departure_date=request.departure_date,
                    return_date=request.return_date or None,
                    passengers=request.passengers,
                )
                select = agent.select_and_book_flight(flight_preference=request.flight_preference)
                traveler = agent.fill_traveler_info(
                    first_name=request.first_name,
                    last_name=request.last_name,
                    email=request.email,
                    phone=request.phone,
                )
                payment = agent.fill_payment_info(
                    card_number=request.card_number,
                    cardholder_name=request.cardholder_name,
                    expiration_month=request.expiration_month,
                    expiration_year=request.expiration_year,
                    cvv=request.cvv,
                    billing_address=billing_address,
                )
                agent.cleanup()
                return BookingResponse(
                    status="success",
                    message="Flight booking flow executed",
                    booking_mode="flight_only",
                    results={"search": search, "selection": select, "traveler": traveler, "payment": payment},
                )

            else:  # hotel
                agent.create_profile()
                agent.create_session()
                agent.login(email=request.email, password=request.password)
                search = agent.search_hotels(
                    location=request.hotel_location,
                    check_in=request.check_in,
                    check_out=request.check_out,
                    guests=request.passengers,
                )
                select = agent.select_and_book_hotel(hotel_preference=request.hotel_preference)
                traveler = agent.fill_traveler_info(
                    first_name=request.first_name,
                    last_name=request.last_name,
                    email=request.email,
                    phone=request.phone,
                )
                payment = agent.fill_payment_info(
                    card_number=request.card_number,
                    cardholder_name=request.cardholder_name,
                    expiration_month=request.expiration_month,
                    expiration_year=request.expiration_year,
                    cvv=request.cvv,
                    billing_address=billing_address,
                )
                agent.cleanup()
                return BookingResponse(
                    status="success",
                    message="Hotel booking flow executed",
                    booking_mode="hotel_only",
                    results={"search": search, "selection": select, "traveler": traveler, "payment": payment},
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Booking from plan failed: {str(e)}")
    finally:
        try:
            db.close()
        except Exception:
            pass


@app.post("/group-chat/{session_id}/book/flight", response_model=BookingResponse, summary="Book flight from group plan")
async def book_flight_from_plan(session_id: str, payload: PlanBookingRequest, force: bool = False):
    return await book_from_plan(session_id=session_id, payload=payload, segment="flight", force=force)


@app.post("/group-chat/{session_id}/book/hotel", response_model=BookingResponse, summary="Book hotel from group plan")
async def book_hotel_from_plan(session_id: str, payload: PlanBookingRequest, force: bool = False):
    return await book_from_plan(session_id=session_id, payload=payload, segment="hotel", force=force)

@app.post("/search/flights")
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    passengers: int = 1,
    email: Optional[str] = None,
    password: Optional[str] = None
):
    """
    Search for flights without booking.
    
    Args:
        origin: Departure location
        destination: Arrival location
        departure_date: Departure date
        return_date: Return date (optional)
        passengers: Number of passengers
        email: Expedia email (optional, for logged-in search)
        password: Expedia password (optional)
    
    Returns:
        Flight search results
    """
    try:
        agent = ExpediaAgent()
        agent.create_profile()
        agent.create_session()
        
        # Login if credentials provided
        if email and password:
            agent.login(email=email, password=password)
        
        # Search flights
        result = agent.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=passengers
        )
        
        agent.cleanup()
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Flight search failed: {str(e)}"
        )


@app.post("/search/hotels")
async def search_hotels(
    location: str,
    check_in: str,
    check_out: str,
    guests: int = 1,
    rooms: int = 1,
    email: Optional[str] = None,
    password: Optional[str] = None
):
    """
    Search for hotels without booking.
    
    Args:
        location: Hotel location
        check_in: Check-in date
        check_out: Check-out date
        guests: Number of guests
        rooms: Number of rooms
        email: Expedia email (optional)
        password: Expedia password (optional)
    
    Returns:
        Hotel search results
    """
    try:
        agent = ExpediaAgent()
        agent.create_profile()
        agent.create_session()
        
        # Login if credentials provided
        if email and password:
            agent.login(email=email, password=password)
        
        # Search hotels
        result = agent.search_hotels(
            location=location,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            rooms=rooms
        )
        
        agent.cleanup()
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Hotel search failed: {str(e)}"
        )


@app.post("/account/create", summary="Create Expedia Account")
async def create_account(request: AccountCreationRequest):
    """
    Create a new Expedia account.
    
    Returns:
        Account creation status
        
    Note:
        Email verification may be required after account creation.
        Use /account/verify endpoint with the verification code from email.
    """
    try:
        agent = ExpediaAgent(
            llm_model=request.llm_model,
            proxy_country_code=request.proxy_country_code
        )
        agent.create_profile()
        agent.create_session()
        
        # Use hybrid method for account creation
        result = await agent.create_account_hybrid(
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name
        )
        
        agent.cleanup()
        
        return {
            "status": "success",
            "message": "Account created successfully",
            "result": result,
            "note": "Check email for verification code if required"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Account creation failed: {str(e)}"
        )


@app.post("/account/verify", summary="Verify Email")
async def verify_email(request: EmailVerificationRequest):
    """
    Verify email with verification code.
    
    Args:
        verification_code: Code sent to email
        
    Returns:
        Verification status
    """
    try:
        agent = ExpediaAgent()
        agent.create_profile()
        agent.create_session()
        
        # Use hybrid method for email verification
        result = await agent.verify_email_hybrid(
            verification_code=request.verification_code
        )
        
        agent.cleanup()
        
        return {
            "status": "success",
            "message": "Email verified successfully",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Email verification failed: {str(e)}"
        )


@app.post("/search/flights/advanced", summary="Advanced Flight Search with Filters")
async def search_flights_advanced(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    passengers: int = 1,
    criteria: Optional[FlightSearchCriteria] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    llm_model: str = "claude-sonnet-4",
    proxy_country_code: str = "us"
):
    """
    Search for flights with advanced filters and smart selection.
    
    Args:
        origin: Departure airport/city
        destination: Arrival airport/city
        departure_date: Departure date
        return_date: Return date (optional)
        passengers: Number of passengers
        criteria: Flight search criteria (filters and selection)
        email: Expedia email (optional)
        password: Expedia password (optional)
        llm_model: AI model to use
        proxy_country_code: Proxy country code
        
    Returns:
        Flight search results with filters applied
    """
    try:
        agent = ExpediaAgent(
            llm_model=llm_model,
            proxy_country_code=proxy_country_code
        )
        agent.create_profile()
        agent.create_session()
        
        # Login if credentials provided
        if email and password:
            await agent.login_hybrid(email=email, password=password)
        
        # Search with filters
        result = await agent.search_flights_with_filters_hybrid(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=passengers,
            max_price=criteria.max_price if criteria else None,
            airlines=criteria.preferred_airlines if criteria else None,
            max_stops=criteria.max_stops if criteria else "any"
        )
        
        # Select best value flight if criteria provided
        if criteria:
            selection = await agent.select_best_flight_hybrid(criteria=criteria.dict())
            result["selection"] = selection
        
        agent.cleanup()
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Advanced flight search failed: {str(e)}"
        )


@app.post("/search/hotels/advanced", summary="Advanced Hotel Search with Filters")
async def search_hotels_advanced(
    location: str,
    check_in: str,
    check_out: str,
    guests: int = 2,
    criteria: Optional[HotelSearchCriteria] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    llm_model: str = "claude-sonnet-4",
    proxy_country_code: str = "us"
):
    """
    Search for hotels with advanced filters and smart selection.
    
    Args:
        location: Hotel location
        check_in: Check-in date
        check_out: Check-out date
        guests: Number of guests
        criteria: Hotel search criteria (filters and selection)
        email: Expedia email (optional)
        password: Expedia password (optional)
        llm_model: AI model to use
        proxy_country_code: Proxy country code
        
    Returns:
        Hotel search results with filters applied
    """
    try:
        agent = ExpediaAgent(
            llm_model=llm_model,
            proxy_country_code=proxy_country_code
        )
        agent.create_profile()
        agent.create_session()
        
        # Login if credentials provided
        if email and password:
            await agent.login_hybrid(email=email, password=password)
        
        # Search with filters
        result = await agent.search_hotels_with_filters_hybrid(
            location=location,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            max_price=criteria.max_price if criteria else None,
            min_star_rating=criteria.min_stars if criteria else None,
            amenities=criteria.required_amenities if criteria else None,
            free_cancellation=criteria.free_cancellation if criteria else False
        )
        
        # Select best value hotel if criteria provided
        if criteria:
            selection = await agent.select_best_hotel_hybrid(criteria=criteria.dict())
            result["selection"] = selection
        
        agent.cleanup()
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Advanced hotel search failed: {str(e)}"
        )


@app.post("/book/ai-assisted", summary="AI-Assisted Booking with Custom Tools")
async def book_with_ai_tools(request: BookingRequest):
    """
    Complete booking where AI agent intelligently uses Playwright tools.
    
    This endpoint uses Browser Use's custom tools system to give the AI agent
    direct access to Playwright functions. The agent will:
    
    - Decide when to use each tool based on the task
    - Call tools at appropriate times in the workflow
    - Handle errors and retries automatically
    - Combine Playwright speed with AI intelligence
    
    Available tools for the agent:
    - navigate_to_expedia(), go_to_flights(), go_to_hotels()
    - fill_login_form(), create_expedia_account()
    - search_flights(), apply_flight_filters(), select_best_flight()
    - search_hotels(), apply_hotel_filters(), select_best_hotel()
    - fill_traveler_info(), fill_payment_form(), complete_booking()
    
    Returns:
        Booking result from AI agent
    """
    try:
        agent = ExpediaAgent(
            llm_model=request.llm_model,
            proxy_country_code=request.proxy_country_code
        )
        
        agent.create_profile()
        agent.create_session()
        
        # Build criteria dicts
        flight_crit = None
        if request.flight_criteria:
            flight_crit = {
                'max_price': request.flight_criteria.max_price,
                'preferred_airlines': request.flight_criteria.preferred_airlines,
                'max_stops': 0 if request.flight_criteria.max_stops == "nonstop" else (1 if request.flight_criteria.max_stops == "1stop" else 2)
            }
        
        hotel_crit = None
        if request.hotel_criteria:
            hotel_crit = {
                'max_price': request.hotel_criteria.max_price,
                'min_stars': request.hotel_criteria.min_stars,
                'min_guest_rating': request.hotel_criteria.min_guest_rating,
                'required_amenities': request.hotel_criteria.required_amenities
            }
        
        # Let AI agent handle everything using custom tools
        result = await agent.book_with_ai_agent(
            # Login
            email=request.email,
            password=request.password,
            # Flight
            origin=request.origin,
            destination=request.destination,
            departure_date=request.departure_date,
            return_date=request.return_date,
            passengers=request.passengers,
            # Hotel
            hotel_location=request.hotel_location,
            check_in=request.check_in,
            check_out=request.check_out,
            guests=request.passengers,
            # Traveler
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
            # Payment
            card_number=request.card_number,
            cardholder_name=request.cardholder_name,
            expiration_month=request.expiration_month,
            expiration_year=request.expiration_year,
            cvv=request.cvv,
            billing_address={
                'street': request.billing_address.street,
                'city': request.billing_address.city,
                'state': request.billing_address.state,
                'zip': request.billing_address.zip,
                'country': request.billing_address.country
            },
            # Criteria
            flight_criteria=flight_crit,
            hotel_criteria=hotel_crit
        )
        
        agent.cleanup()
        
        return {
            "status": "success",
            "mode": "ai_assisted_with_tools",
            "message": "AI agent completed booking using intelligent tool selection",
            "result": result,
            "note": "The agent used custom Playwright tools for 5-10x speedup"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI-assisted booking failed: {str(e)}"
        )


@app.post("/search/ai-assisted", summary="AI-Assisted Search with Tools")
async def search_with_ai_tools(
    search_type: str,  # "flights" or "hotels"
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    location: Optional[str] = None,
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
    passengers: int = 1,
    guests: int = 2,
    llm_model: str = "claude-sonnet-4",
    proxy_country_code: str = "us"
):
    """
    Search for flights or hotels using AI agent with custom tools.
    
    The agent will intelligently use tools to search and analyze results.
    No booking is performed - only search and analysis.
    
    Args:
        search_type: "flights" or "hotels"
        (other params as needed for the search type)
    """
    try:
        agent = ExpediaAgent(
            llm_model=llm_model,
            proxy_country_code=proxy_country_code
        )
        
        agent.create_profile()
        agent.create_session()
        
        if search_type == "flights":
            search_params = {
                'origin': origin,
                'destination': destination,
                'departure_date': departure_date,
                'return_date': return_date,
                'passengers': passengers
            }
        else:  # hotels
            search_params = {
                'location': location,
                'check_in': check_in,
                'check_out': check_out,
                'guests': guests
            }
        
        result = await agent.search_with_ai_agent(
            search_type=search_type,
            **search_params
        )
        
        agent.cleanup()
        
        return {
            "status": "success",
            "search_type": search_type,
            "result": result,
            "message": "AI agent completed search using custom tools"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI-assisted search failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    # Check for required environment variables
    if not os.getenv("BROWSER_USE_API_KEY"):
        print("⚠️  Warning: BROWSER_USE_API_KEY not set!")
        print("   Set it with: export BROWSER_USE_API_KEY=bu_your_key")
    
    if not os.getenv("LMNR_PROJECT_API_KEY"):
        print("ℹ️  Info: LMNR_PROJECT_API_KEY not set (observability disabled)")
        print("   To enable: export LMNR_PROJECT_API_KEY=your_key")
    
    print("\n🚀 Starting Expedia Booking Agent API...")
    print("📚 API docs: http://localhost:8000/docs")
    print("🔍 Health check: http://localhost:8000/health")
    print("🤖 AI-assisted endpoints: /book/ai-assisted, /search/ai-assisted")
    print("🔧 Custom tools: Available for intelligent agent use\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

