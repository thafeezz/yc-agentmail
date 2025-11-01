"""
Test ExpediaAgent book_parallel with real browser automation.

This test bypasses the group chat and directly tests the Expedia booking agent
with a sample travel plan output to verify browser automation is working.
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api.expedia_agent.agent_browser import ExpediaAgent


async def test_expedia_agent_booking():
    """
    Test real Expedia browser automation with sample group chat output.
    
    This simulates the output from a group chat and sends it directly
    to the ExpediaAgent to verify browser automation works.
    """
    
    print("\n" + "="*80)
    print("TEST: ExpediaAgent Book Parallel - Real Browser Automation")
    print("="*80)
    
    # Sample travel plan output from group chat
    # This is what the group chat would generate
    sample_plan = {
        "location": "Cancun, Mexico",
        "dates": {
            "departure_date": (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
            "return_date": (datetime.now() + timedelta(days=67)).strftime("%Y-%m-%d")
        },
        "flight": {
            "origin": "LAX",
            "destination": "CUN",
            "preferences": "Direct flight preferred, economy class"
        },
        "hotel": {
            "location": "Cancun Hotel Zone",
            "type": "resort",
            "amenities": ["beach access", "pool", "wifi"],
            "preferences": "4-star hotel with ocean view"
        },
        "budget": {
            "total_per_person": 2000,
            "flight_cost": 500,
            "hotel_cost": 1000,
            "activities_cost": 300,
            "food_cost": 200
        }
    }
    
    # Sample user credentials and payment info
    # In real scenario, this comes from user onboarding
    # Using default test credentials (override with EXPEDIA_TEST_EMAIL and EXPEDIA_TEST_PASSWORD env vars)
    test_user = {
        "expedia_credentials": {
            "email": os.getenv("EXPEDIA_TEST_EMAIL", "testuser@agentmail.to"),
            "password": os.getenv("EXPEDIA_TEST_PASSWORD", "TestPass123!")
        },
        "traveler_info": {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1-555-123-4567"
        },
        "payment_info": {
            "card_number": "4111111111111111",  # Test card
            "cardholder_name": "John Doe",
            "expiration_month": "12",
            "expiration_year": "2025",
            "cvv": "123",
            "billing_address": {
                "street": "123 Test Street",
                "city": "Los Angeles",
                "state": "CA",
                "zip": "90001",
                "country": "USA"
            }
        }
    }
    
    print("\n📋 Sample Travel Plan:")
    print(f"   Destination: {sample_plan['location']}")
    print(f"   Dates: {sample_plan['dates']['departure_date']} → {sample_plan['dates']['return_date']}")
    print(f"   Flight: {sample_plan['flight']['origin']} → {sample_plan['flight']['destination']}")
    print(f"   Hotel: {sample_plan['hotel']['location']}")
    print(f"   Budget: ${sample_plan['budget']['total_per_person']} per person")
    
    print("\n👤 Test User:")
    print(f"   Name: {test_user['traveler_info']['first_name']} {test_user['traveler_info']['last_name']}")
    print(f"   Email: {test_user['expedia_credentials']['email']}")
    
    # Initialize ExpediaAgent
    print("\n🤖 Initializing ExpediaAgent...")
    print("   ⚠️  This will use Browser Use Cloud for real browser automation")
    print("   ⚠️  Expected duration: 5-15 minutes for full booking flow")
    
    agent = ExpediaAgent(
        llm_model="gpt-4o",
        use_cloud_browser=True,  # Use cloud browser for CAPTCHA handling
        use_tools=True  # Enable custom Expedia tools
    )
    
    print(f"   ✅ Agent initialized with LLM: gpt-4o")
    
    # Execute booking
    print("\n🚀 Starting parallel booking (flight + hotel)...")
    print("   This will open real browser sessions and interact with Expedia")
    print("   Watch the Browser Use Cloud dashboard: https://cloud.browser-use.com/dashboard")
    
    try:
        # Use the working async method with Agent
        # Build the task description
        task_description = f"""
Complete an Expedia flight and hotel booking:

1. Navigate to Expedia homepage
2. Login with email: {test_user["expedia_credentials"]["email"]}
3. Search for flights:
   - From: {sample_plan["flight"]["origin"]}
   - To: {sample_plan["flight"]["destination"]}
   - Departure: {sample_plan["dates"]["departure_date"]}
   - Return: {sample_plan["dates"]["return_date"]}
4. Select a flight (cheapest available)
5. Search for hotels in {sample_plan["hotel"]["location"]}
   - Check-in: {sample_plan["dates"]["departure_date"]}
   - Check-out: {sample_plan["dates"]["return_date"]}
6. Select a hotel (best rated under $200/night)
7. Fill traveler information:
   - Name: {test_user["traveler_info"]["first_name"]} {test_user["traveler_info"]["last_name"]}
   - Phone: {test_user["traveler_info"]["phone"]}
8. Fill payment information with provided card details
9. Complete the booking

Use the custom Expedia tools to complete each step efficiently.
Take screenshots at key verification points.
"""
        
        result = await agent.run_task(task_description)
        
        # Format result for compatibility
        result = {
            "status": "success" if result else "failed",
            "message": "Booking completed via AI agent",
            "result": result
        }
        
        
        print("\n" + "="*80)
        print("BOOKING RESULT")
        print("="*80)
        
        if result.get("status") == "success":
            print("✅ Booking completed successfully!")
            print(f"\nBooking Mode: {result.get('booking_mode', 'unknown')}")
            print("\n📋 Results Summary:")
            
            if "results" in result:
                results = result["results"]
                
                # Flight results
                if "flight" in results:
                    print("\n  ✈️  FLIGHT:")
                    for step, data in results["flight"].items():
                        print(f"     {step}: {data.get('status', 'completed')}")
                
                # Hotel results
                if "hotel" in results:
                    print("\n  🏨 HOTEL:")
                    for step, data in results["hotel"].items():
                        print(f"     {step}: {data.get('status', 'completed')}")
                
                # Payment results
                if "combined_payment" in results:
                    print("\n  💳 PAYMENT:")
                    for step, data in results["combined_payment"].items():
                        print(f"     {step}: {data.get('status', 'completed')}")
        else:
            print(f"❌ Booking failed: {result.get('message', 'Unknown error')}")
            if "results" in result:
                print(f"\nPartial results: {result['results']}")
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETED")
        print("="*80)
        
        # Cleanup
        print("\n🧹 Cleaning up agent resources...")
        await agent.cleanup()
        print("   ✅ Cleanup complete")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error during booking: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        
        # Cleanup on error
        try:
            await agent.cleanup()
        except:
            pass
        
        raise


if __name__ == "__main__":
    print("\n" + "="*80)
    print("EXPEDIA AGENT BROWSER AUTOMATION TEST")
    print("="*80)
    print("\nThis test will:")
    print("1. Use a sample travel plan (as if from group chat)")
    print("2. Initialize ExpediaAgent with Browser Use Cloud")
    print("3. Execute real browser automation to book flight + hotel")
    print("4. Report results")
    print("\n⚠️  Requirements:")
    print("   - BROWSER_USE_API_KEY in .env")
    print("   - OPENAI_API_KEY in .env")
    print("   - Test credentials: testuser@agentmail.to / TestPass123!")
    print("     (override with EXPEDIA_TEST_EMAIL and EXPEDIA_TEST_PASSWORD)")
    print("\n⏱️  Expected duration: 5-15 minutes")
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
        result = asyncio.run(test_expedia_agent_booking())
        
        if result.get("status") == "success":
            print("\n🎉 Test passed! Browser automation is working.")
            sys.exit(0)
        else:
            print("\n⚠️  Test completed but booking failed. Check the output above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

