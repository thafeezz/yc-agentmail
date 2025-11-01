"""
Test script for Expedia booking API endpoints.

Tests both the group chat flow and the Expedia booking flow:
1. Create fake users with complete onboarding data
2. Start a group chat session (simulated)
3. Test the Expedia booking endpoints with the plan
"""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def setup_fake_data():
    """Set up fake users with complete onboarding information"""
    from api.group_chat.database import (
        get_session, create_user, create_session,
        update_chat_session
    )
    from api.group_chat.models import (
        UserProfile, UserPreferences, ExpediaCredentials,
        PaymentDetails, ContactInfo
    )
    
    db = get_session()
    
    # Clear existing test data
    print("\n🧹 Cleaning up existing test data...")
    
    # Delete existing test users and sessions
    try:
        from sqlalchemy import text
        db.execute(text("DELETE FROM users WHERE user_id IN ('alice_001', 'bob_002')"))
        db.execute(text("DELETE FROM group_chat_sessions WHERE session_id = 'test_session_001'"))
        db.commit()
        print("   ✅ Cleaned up existing test data")
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")
        db.rollback()
    
    # Create user 1: Alice (adventure seeker)
    alice_profile = UserProfile(
        user_id="alice_001",
        user_name="Alice Johnson",
        email="alice@example.com",
        preferences=UserPreferences(
            budget_range=(2000, 4000),
            preferred_destinations=["mountains", "hiking"],
            travel_style="adventure",
            dietary_restrictions=["vegetarian"],
            mobility_requirements=[],
            preferred_airlines=["Delta", "United"],
            hotel_amenities=["gym", "wifi"]
        ),
        expedia_credentials=ExpediaCredentials(
            email="alice@expedia-test.com",
            password="test_password_123"
        ),
        payment_details=PaymentDetails(
            card_number="4111111111111111",
            cardholder_name="Alice Johnson",
            expiration_month="12",
            expiration_year="2026",
            cvv="123",
            billing_address={
                "street": "123 Mountain View Dr",
                "city": "Denver",
                "state": "CO",
                "zip": "80202",
                "country": "USA"
            }
        ),
        contact_info=ContactInfo(
            phone="+1-555-0001"
        ),
        memories=[]
    )
    
    # Create user 2: Bob (relaxation lover)
    bob_profile = UserProfile(
        user_id="bob_002",
        user_name="Bob Smith",
        email="bob@example.com",
        preferences=UserPreferences(
            budget_range=(1500, 3000),
            preferred_destinations=["beaches", "resorts"],
            travel_style="relaxation",
            dietary_restrictions=[],
            mobility_requirements=[],
            preferred_airlines=["Southwest", "JetBlue"],
            hotel_amenities=["pool", "spa", "beach access"]
        ),
        expedia_credentials=ExpediaCredentials(
            email="bob@expedia-test.com",
            password="test_password_456"
        ),
        payment_details=PaymentDetails(
            card_number="5500000000000004",
            cardholder_name="Bob Smith",
            expiration_month="08",
            expiration_year="2027",
            cvv="456",
            billing_address={
                "street": "456 Beach Blvd",
                "city": "Miami",
                "state": "FL",
                "zip": "33101",
                "country": "USA"
            }
        ),
        contact_info=ContactInfo(
            phone="+1-555-0002"
        ),
        memories=[]
    )
    
    # Save users
    print("👤 Creating test users with complete onboarding data...")
    create_user(
        db,
        user_id=alice_profile.user_id,
        user_name=alice_profile.user_name,
        email=alice_profile.email,
        preferences=alice_profile.dict()  # Convert to dict
    )
    create_user(
        db,
        user_id=bob_profile.user_id,
        user_name=bob_profile.user_name,
        email=bob_profile.email,
        preferences=bob_profile.dict()  # Convert to dict
    )
    
    # Create a test travel plan
    departure_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    return_date = (datetime.now() + timedelta(days=37)).strftime("%Y-%m-%d")
    
    test_plan = {
        "plan_id": "test_plan_001",
        "dates": {
            "departure_date": departure_date,
            "return_date": return_date,
            "flexibility_days": 2
        },
        "flight": {
            "origin": "Denver",
            "destination": "Cancun",
            "preferences": "Non-stop, morning departure",
            "max_budget_per_person": 600
        },
        "hotel": {
            "location": "Cancun Hotel Zone",
            "type": "resort",
            "amenities": ["pool", "gym", "beach access", "wifi"],
            "star_rating_min": 4,
            "max_budget_per_night": 250
        },
        "budget": {
            "total_per_person": 2500,
            "flight_cost": 600,
            "hotel_cost": 1750,
            "activities_cost": 100,
            "food_cost": 50
        },
        "location": "Cancun, Mexico",
        "preferences": {
            "activities": ["snorkeling", "beach relaxation", "hiking"],
            "dining": "Mix of local and resort dining",
            "special_requirements": []
        },
        "compromises_made": "Chose Cancun as it offers both beach relaxation (Bob's preference) and adventure activities like snorkeling and hiking (Alice's preference). Budget balanced at $2500/person, midpoint between their ranges.",
        "created_at": datetime.now().isoformat(),
        "status": "approved",
        "participants": ["alice_001", "bob_002"]
    }
    
    # Create a chat session with approved plan
    session_id = "test_session_001"
    create_session(
        db,
        session_id=session_id,
        user_ids=["alice_001", "bob_002"],
        messages_per_agent=10
    )
    
    update_chat_session(
        db,
        session_id=session_id,
        chat_history=[],
        final_plan=test_plan,
        status="approved",
        current_volley=1
    )
    
    print(f"✅ Created test session: {session_id}")
    print(f"   Plan: {test_plan['location']}")
    print(f"   Users: Alice (adventure) + Bob (relaxation)")
    print(f"   Budget: ${test_plan['budget']['total_per_person']}/person")
    
    return {
        "session_id": session_id,
        "plan": test_plan,
        "users": [alice_profile, bob_profile]
    }


class MockExpediaAgent:
    """Mock Expedia agent for testing without browser automation"""
    
    def __init__(self, llm_model=None, proxy_country_code=None, **kwargs):
        """Initialize mock agent (accepts same args as real agent)"""
        self.llm_model = llm_model
        self.proxy_country_code = proxy_country_code
    
    def book_parallel(self, **kwargs):
        """Simulate successful parallel booking"""
        print(f"\n🤖 MockExpediaAgent.book_parallel called with:")
        print(f"   Email: {kwargs.get('email')}")
        print(f"   Origin: {kwargs.get('origin')} → Destination: {kwargs.get('destination')}")
        print(f"   Dates: {kwargs.get('departure_date')} to {kwargs.get('return_date')}")
        print(f"   Hotel: {kwargs.get('hotel_location')}")
        print(f"   Traveler: {kwargs.get('first_name')} {kwargs.get('last_name')}")
        
        return {
            "success": True,
            "flight_confirmation": f"FLIGHT-{kwargs.get('email', 'unknown')[:5].upper()}-001",
            "hotel_confirmation": f"HOTEL-{kwargs.get('email', 'unknown')[:5].upper()}-001",
            "message": "Successfully booked flight and hotel"
        }
    
    def create_profile(self, **kwargs):
        """Mock profile creation"""
        print(f"🤖 MockExpediaAgent.create_profile called")
        return {"success": True}
    
    def book_flight(self, **kwargs):
        """Mock flight booking"""
        print(f"🤖 MockExpediaAgent.book_flight called")
        return {
            "success": True,
            "confirmation": f"FLIGHT-MOCK-001",
            "message": "Flight booked successfully"
        }
    
    def book_hotel(self, **kwargs):
        """Mock hotel booking"""
        print(f"🤖 MockExpediaAgent.book_hotel called")
        return {
            "success": True,
            "confirmation": f"HOTEL-MOCK-001",
            "message": "Hotel booked successfully"
        }
    
    def create_session(self, **kwargs):
        """Mock session creation"""
        print(f"🤖 MockExpediaAgent.create_session called")
        return {"success": True}
    
    def login(self, **kwargs):
        """Mock login"""
        print(f"🤖 MockExpediaAgent.login called")
        return {"success": True}
    
    def search_flights(self, **kwargs):
        """Mock flight search"""
        print(f"🤖 MockExpediaAgent.search_flights called")
        return {"success": True, "results": []}
    
    def search_hotels(self, **kwargs):
        """Mock hotel search"""
        print(f"🤖 MockExpediaAgent.search_hotels called")
        return {"success": True, "results": []}
    
    def select_and_book_flight(self, **kwargs):
        """Mock flight booking with selection"""
        print(f"🤖 MockExpediaAgent.select_and_book_flight called")
        return {
            "success": True,
            "confirmation": "FLIGHT-MOCK-001",
            "message": "Flight booked successfully"
        }
    
    def select_and_book_hotel(self, **kwargs):
        """Mock hotel booking with selection"""
        print(f"🤖 MockExpediaAgent.select_and_book_hotel called")
        return {
            "success": True,
            "confirmation": "HOTEL-MOCK-001",
            "message": "Hotel booked successfully"
        }
    
    def fill_traveler_info(self, **kwargs):
        """Mock filling traveler information"""
        print(f"🤖 MockExpediaAgent.fill_traveler_info called")
        return {"success": True}
    
    def fill_payment_info(self, **kwargs):
        """Mock filling payment information"""
        print(f"🤖 MockExpediaAgent.fill_payment_info called")
        return {"success": True}
    
    def cleanup(self):
        """Mock cleanup"""
        print(f"🤖 MockExpediaAgent.cleanup called")
        pass


def test_expedia_booking_endpoints():
    """Test the Expedia booking API endpoints"""
    from fastapi.testclient import TestClient
    
    # Import and patch before creating the app
    import api.agent_service as agent_service
    
    # Mock the ExpediaAgent
    with patch.object(agent_service, 'ExpediaAgent', MockExpediaAgent):
        from api import app as api_app
        
        client = TestClient(api_app)
        
        # Setup test data
        test_data = setup_fake_data()
        session_id = test_data["session_id"]
        plan = test_data["plan"]
        
        print("\n" + "="*80)
        print("🧪 TESTING EXPEDIA BOOKING API ENDPOINTS")
        print("="*80)
        
        # Test 1: Combined booking (flight + hotel)
        print("\n📝 Test 1: Combined Flight + Hotel Booking")
        print("-" * 80)
        
        combined_payload = {
            "traveler": {
                "first_name": "Alice",
                "last_name": "Johnson",
                "email": "alice@example.com",
                "phone": "+1-555-0001"
            },
            "credentials": {
                "email": "alice@expedia-test.com",
                "password": "test_password_123"
            },
            "payment": {
                "card_number": "4111111111111111",
                "cardholder_name": "Alice Johnson",
                "expiration_month": "12",
                "expiration_year": "2026",
                "cvv": "123",
                "billing_address": {
                    "street": "123 Mountain View Dr",
                    "city": "Denver",
                    "state": "CO",
                    "zip": "80202",
                    "country": "USA"
                }
            },
            "segment": "both"
        }
        
        response = client.post(
            f"/group-chat/{session_id}/book",
            json=combined_payload
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Combined booking successful!")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Combined booking failed: {response.text}")
        
        # Test 2: Flight-only booking
        print("\n📝 Test 2: Flight-Only Booking")
        print("-" * 80)
        
        flight_payload = {
            "traveler": {
                "first_name": "Bob",
                "last_name": "Smith",
                "email": "bob@example.com",
                "phone": "+1-555-0002"
            },
            "credentials": {
                "email": "bob@expedia-test.com",
                "password": "test_password_456"
            },
            "payment": {
                "card_number": "5500000000000004",
                "cardholder_name": "Bob Smith",
                "expiration_month": "08",
                "expiration_year": "2027",
                "cvv": "456",
                "billing_address": {
                    "street": "456 Beach Blvd",
                    "city": "Miami",
                    "state": "FL",
                    "zip": "33101",
                    "country": "USA"
                }
            }
        }
        
        response = client.post(
            f"/group-chat/{session_id}/book/flight",
            json=flight_payload
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Flight-only booking successful!")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Flight-only booking failed: {response.text}")
        
        # Test 3: Hotel-only booking
        print("\n📝 Test 3: Hotel-Only Booking")
        print("-" * 80)
        
        hotel_payload = {
            "traveler": {
                "first_name": "Alice",
                "last_name": "Johnson",
                "email": "alice@example.com",
                "phone": "+1-555-0001"
            },
            "credentials": {
                "email": "alice@expedia-test.com",
                "password": "test_password_123"
            },
            "payment": {
                "card_number": "4111111111111111",
                "cardholder_name": "Alice Johnson",
                "expiration_month": "12",
                "expiration_year": "2026",
                "cvv": "123",
                "billing_address": {
                    "street": "123 Mountain View Dr",
                    "city": "Denver",
                    "state": "CO",
                    "zip": "80202",
                    "country": "USA"
                }
            }
        }
        
        response = client.post(
            f"/group-chat/{session_id}/book/hotel",
            json=hotel_payload
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Hotel-only booking successful!")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Hotel-only booking failed: {response.text}")
        
        # Test 4: Error case - invalid session
        print("\n📝 Test 4: Error Handling - Invalid Session")
        print("-" * 80)
        
        response = client.post(
            "/group-chat/invalid_session/book",
            json=combined_payload
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 404:
            print("✅ Correctly returned 404 for invalid session!")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)


if __name__ == "__main__":
    print("\n╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                            ║")
    print("║              EXPEDIA BOOKING API - INTEGRATION TEST SUITE                 ║")
    print("║                                                                            ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝\n")
    
    try:
        test_expedia_booking_endpoints()
        print("\n✅ Test suite completed successfully!")
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

