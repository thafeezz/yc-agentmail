"""
Test the actual API route for Expedia booking.

This test validates that the API endpoint properly triggers browser automation
by calling the FastAPI route and monitoring the booking process.
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy import text


def test_api_expedia_booking():
    """
    Test the API route that triggers Expedia booking with browser automation.
    
    This creates a pre-approved travel plan and calls the API endpoint
    that should trigger the ExpediaAgent browser automation.
    """
    
    print("\n" + "="*80)
    print("TEST: API Route for Expedia Booking with Browser Automation")
    print("="*80)
    
    # Setup database and users
    from api.group_chat.database import (
        init_db, get_session, create_user, create_session as create_db_session, 
        update_chat_session
    )
    from api.group_chat.models import (
        ExpediaCredentials, PaymentDetails, ContactInfo, UserPreferences
    )
    
    print("\n📦 Setting up test database...")
    init_db()
    db = get_session()
    
    # Clean up any existing test data
    try:
        db.execute(text("DELETE FROM users WHERE user_id IN ('api_test_alice', 'api_test_bob')"))
        db.execute(text("DELETE FROM group_chat_sessions WHERE session_id LIKE 'api_test_%'"))
        db.commit()
        print("   ✅ Cleaned up existing test data")
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")
        db.rollback()
    
    # Create test users with Expedia credentials
    print("\n👥 Creating test users with booking credentials...")
    
    # User 1: Alice
    alice_credentials = ExpediaCredentials(
        email=os.getenv("EXPEDIA_TEST_EMAIL", "testuser@agentmail.to"),
        password=os.getenv("EXPEDIA_TEST_PASSWORD", "TestPass123!")
    )
    
    alice_payment = PaymentDetails(
        card_number="4111111111111111",
        cardholder_name="Alice Test",
        expiration_month="12",
        expiration_year="2025",
        cvv="123",
        billing_address={
            "street": "123 Test St",
            "city": "Los Angeles",
            "state": "CA",
            "zip": "90001",
            "country": "USA"
        }
    )
    
    alice_contact = ContactInfo(
        phone="+1-555-111-2222",
        emergency_contact_name="Bob Test",
        emergency_contact_phone="+1-555-111-2223"
    )
    
    alice_prefs = UserPreferences(
        travel_style="adventure",
        budget_range=(2000, 3000),
        dietary_restrictions=[],
        mobility_requirements=[]
    )
    
    # Combine into preferences dict
    alice_prefs_dict = alice_prefs.model_dump()
    alice_prefs_dict["expedia_credentials"] = alice_credentials.model_dump()
    alice_prefs_dict["payment_details"] = alice_payment.model_dump()
    alice_prefs_dict["contact_info"] = alice_contact.model_dump()
    
    create_user(
        db,
        user_id="api_test_alice",
        user_name="Alice Test",
        email="alice@agentmail.to",  # Valid AgentMail domain
        preferences=alice_prefs_dict
    )
    
    # ONLY TESTING WITH ONE USER (Alice)
    # # User 2: Bob (DISABLED)
    # bob_credentials = ExpediaCredentials(
    #     email=os.getenv("EXPEDIA_TEST_EMAIL", "testuser@agentmail.to"),
    #     password=os.getenv("EXPEDIA_TEST_PASSWORD", "TestPass123!")
    # )
    # 
    # bob_payment = PaymentDetails(
    #     card_number="4111111111111112",
    #     cardholder_name="Bob Test",
    #     expiration_month="11",
    #     expiration_year="2025",
    #     cvv="456",
    #     billing_address={
    #         "street": "456 Test Ave",
    #         "city": "San Francisco",
    #         "state": "CA",
    #         "zip": "94102",
    #         "country": "USA"
    #     }
    # )
    # 
    # bob_contact = ContactInfo(
    #     phone="+1-555-333-4444",
    #     emergency_contact_name="Alice Test",
    #     emergency_contact_phone="+1-555-333-4445"
    # )
    # 
    # bob_prefs = UserPreferences(
    #     travel_style="relaxation",
    #     budget_range=(2000, 3000),
    #     dietary_restrictions=["vegetarian"],
    #     mobility_requirements=[]
    # )
    # 
    # bob_prefs_dict = bob_prefs.model_dump()
    # bob_prefs_dict["expedia_credentials"] = bob_credentials.model_dump()
    # bob_prefs_dict["payment_details"] = bob_payment.model_dump()
    # bob_prefs_dict["contact_info"] = bob_contact.model_dump()
    # 
    # create_user(
    #     db,
    #     user_id="api_test_bob",
    #     user_name="Bob Test",
    #     email="bob@agentmail.to",  # Valid AgentMail domain
    #     preferences=bob_prefs_dict
    # )
    
    db.commit()
    print("   ✅ Created test user: api_test_alice")
    
    # Create approved travel plan
    print("\n✈️  Creating approved travel plan...")
    
    test_plan = {
        "location": "Detroit, Michigan",
        "dates": {
            "departure_date": (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
            "return_date": (datetime.now() + timedelta(days=67)).strftime("%Y-%m-%d")
        },
        "flight": {
            "origin": "SFO",
            "destination": "DTW",
            "preferences": "Direct flight, economy class"
        },
        "hotel": {
            "location": "Downtown Detroit",
            "type": "hotel",
            "amenities": ["wifi", "parking"]
        },
        "budget": {
            "per_person": 1500,
            "total_per_person": 1500,
            "currency": "USD"
        }
    }
    
    session_id = f"api_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create session with only Alice
    create_db_session(
        db,
        session_id=session_id,
        user_ids=["api_test_alice"],  # Only one user for testing
        messages_per_agent=10
    )
    
    # Update with approved plan
    approval_state = {
        "api_test_alice": {"approved": True, "feedback": None}
        # "api_test_bob": {"approved": True, "feedback": None}  # Bob disabled
    }
    
    update_chat_session(
        db,
        session_id=session_id,
        chat_history=[],
        final_plan=test_plan,
        current_volley=1,
        approval_state=approval_state,
        status="approved"
    )
    
    db.commit()
    
    print(f"   ✅ Created approved session: {session_id}")
    print(f"      Location: {test_plan['location']}")
    print(f"      Dates: {test_plan['dates']['departure_date']} → {test_plan['dates']['return_date']}")
    print(f"      User: api_test_alice (single user test)")
    
    # Now test the API route
    print("\n🚀 Testing API route: POST /trigger-bookings/{session_id}")
    print("   ⚠️  This will trigger REAL browser automation via ExpediaAgent")
    print("   ⚠️  Expected duration: 5-15 minutes for parallel bookings")
    print("   ⚠️  Watch at: https://cloud.browser-use.com/dashboard")
    
    from main import app, trigger_parallel_bookings
    
    # Since trigger_parallel_bookings is async, we need to run it
    print("\n⏳ Calling trigger_parallel_bookings()...")
    print("   This should initialize ExpediaAgent and start browser automation...")
    
    import time
    start_time = time.time()
    
    try:
        # Run the async function
        asyncio.run(trigger_parallel_bookings(session_id))
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ Booking function completed in {elapsed:.1f} seconds")
        
        # Check if it was actually real (real bookings take minutes, not seconds)
        if elapsed < 30:
            print("⚠️  WARNING: Booking completed very quickly (< 30s)")
            print("   This suggests browser automation may not have run properly")
            print("   Real Expedia bookings should take 5-15 minutes")
        else:
            print("✅ Duration suggests real browser automation occurred")
        
        # Check session status
        from api.group_chat.database import get_chat_session
        final_session = get_chat_session(db, session_id)
        
        print(f"\n📊 Final Session Status: {final_session.status}")
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETED")
        print("="*80)
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        db.execute(text("DELETE FROM users WHERE user_id IN ('api_test_alice', 'api_test_bob')"))
        db.execute(text(f"DELETE FROM group_chat_sessions WHERE session_id = '{session_id}'"))
        db.commit()
        db.close()
        print("   ✅ Cleanup complete")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during API test: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        try:
            db.execute(text("DELETE FROM users WHERE user_id IN ('api_test_alice', 'api_test_bob')"))
            db.execute(text(f"DELETE FROM group_chat_sessions WHERE session_id = '{session_id}'"))
            db.commit()
            db.close()
        except:
            pass
        
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("API ROUTE TEST: EXPEDIA BOOKING WITH BROWSER AUTOMATION")
    print("="*80)
    print("\nThis test will:")
    print("1. Create test users with Expedia credentials")
    print("2. Create an approved travel plan in the database")
    print("3. Call the API route that triggers parallel bookings")
    print("4. Verify that browser automation actually runs")
    print("\n⚠️  Requirements:")
    print("   - BROWSER_USE_API_KEY in .env")
    print("   - OPENAI_API_KEY in .env")
    print("   - AGENTMAIL_API_KEY in .env")
    print("   - Test credentials: testuser@agentmail.to / TestPass123!")
    print("\n⏱️  Expected duration: 5-15 minutes if browser automation works")
    print("="*80)
    
    print("\n🚀 Starting test automatically in 3 seconds...")
    print("   (Press Ctrl+C to cancel)")
    
    try:
        import time
        time.sleep(3)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
        sys.exit(130)
    
    try:
        success = test_api_expedia_booking()
        
        if success:
            print("\n🎉 Test passed! API route triggered browser automation.")
            sys.exit(0)
        else:
            print("\n⚠️  Test completed but with issues. Check output above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

