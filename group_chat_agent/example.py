"""
Example Usage of Group Chat Agent System
Demonstrates how to use the multi-agent travel planning system.
"""

import uuid
from datetime import datetime
from group_chat_agent.models import (
    UserProfile,
    UserPreferences,
    UserMemory,
)
from group_chat_agent.database import (
    get_session,
    create_user,
    create_memory,
    load_user_profiles
)
from group_chat_agent.orchestrator import GroupChatOrchestrator


def create_sample_users():
    """Create sample users with different preferences"""
    
    session = get_session()
    
    # User 1: Budget-conscious adventure traveler
    user1_id = f"user_{uuid.uuid4().hex[:8]}"
    user1 = create_user(
        session,
        user_id=user1_id,
        user_name="Alice",
        email=f"alice_{uuid.uuid4().hex[:6]}@example.com",
        preferences={
            "budget_range": (1000, 2000),
            "preferred_destinations": ["mountains", "hiking trails"],
            "travel_style": "adventure",
            "dietary_restrictions": ["vegetarian"],
            "mobility_requirements": [],
            "preferred_airlines": ["Southwest", "JetBlue"],
            "hotel_amenities": ["free breakfast", "hiking access"]
        }
    )
    
    # Add memories for Alice
    create_memory(
        session,
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        user_id=user1_id,
        content="Loves early morning hikes and prefers morning flights",
        memory_type="preference",
        relevance_score=0.9
    )
    create_memory(
        session,
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        user_id=user1_id,
        content="Had a great experience with budget lodges in Colorado",
        memory_type="interaction",
        relevance_score=0.8
    )
    create_memory(
        session,
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        user_id=user1_id,
        content="Strictly vegetarian, needs veggie options at all meals",
        memory_type="constraint",
        relevance_score=1.0
    )
    
    # User 2: Luxury relaxation traveler
    user2_id = f"user_{uuid.uuid4().hex[:8]}"
    user2 = create_user(
        session,
        user_id=user2_id,
        user_name="Bob",
        email=f"bob_{uuid.uuid4().hex[:6]}@example.com",
        preferences={
            "budget_range": (3000, 5000),
            "preferred_destinations": ["beaches", "resorts"],
            "travel_style": "luxury",
            "dietary_restrictions": [],
            "mobility_requirements": [],
            "preferred_airlines": ["Delta", "United"],
            "hotel_amenities": ["spa", "pool", "room service", "ocean view"]
        }
    )
    
    # Add memories for Bob
    create_memory(
        session,
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        user_id=user2_id,
        content="Prefers 5-star resorts with full spa services",
        memory_type="preference",
        relevance_score=0.95
    )
    create_memory(
        session,
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        user_id=user2_id,
        content="Likes to sleep in, prefers afternoon or evening flights",
        memory_type="preference",
        relevance_score=0.8
    )
    create_memory(
        session,
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        user_id=user2_id,
        content="Had amazing experience at Ritz-Carlton in Hawaii",
        memory_type="interaction",
        relevance_score=0.85
    )
    
    # User 3: Cultural explorer on moderate budget
    user3_id = f"user_{uuid.uuid4().hex[:8]}"
    user3 = create_user(
        session,
        user_id=user3_id,
        user_name="Charlie",
        email=f"charlie_{uuid.uuid4().hex[:6]}@example.com",
        preferences={
            "budget_range": (1500, 2500),
            "preferred_destinations": ["cities", "museums", "historical sites"],
            "travel_style": "cultural",
            "dietary_restrictions": ["gluten-free"],
            "mobility_requirements": [],
            "preferred_airlines": ["American", "Delta"],
            "hotel_amenities": ["wifi", "central location", "breakfast"]
        }
    )
    
    # Add memories for Charlie
    create_memory(
        session,
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        user_id=user3_id,
        content="Passionate about art museums and local history",
        memory_type="preference",
        relevance_score=0.9
    )
    create_memory(
        session,
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        user_id=user3_id,
        content="Prefers boutique hotels in walkable neighborhoods",
        memory_type="preference",
        relevance_score=0.85
    )
    create_memory(
        session,
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        user_id=user3_id,
        content="Has celiac disease, strictly gluten-free diet required",
        memory_type="constraint",
        relevance_score=1.0
    )
    
    session.close()
    
    return [user1_id, user2_id, user3_id]


def run_group_chat_example():
    """Run a complete group chat example"""
    
    print("="*70)
    print("GROUP CHAT AGENT SYSTEM - EXAMPLE")
    print("="*70)
    
    # Create sample users
    print("\n1. Creating sample users with different preferences...")
    user_ids = create_sample_users()
    print(f"   ✅ Created {len(user_ids)} users: {user_ids}")
    
    # Load user profiles
    print("\n2. Loading user profiles from database...")
    session = get_session()
    user_profiles = load_user_profiles(session, user_ids)
    session.close()
    
    print(f"   ✅ Loaded {len(user_profiles)} profiles:")
    for profile in user_profiles:
        print(f"      - {profile.user_name}: {profile.preferences.travel_style}, "
              f"${profile.preferences.budget_range[0]}-${profile.preferences.budget_range[1]}")
    
    # Create orchestrator
    print("\n3. Creating GroupChatOrchestrator...")
    orchestrator = GroupChatOrchestrator(
        users=user_profiles,
        messages_per_volley=10,
        llm_model="claude-sonnet-4"
    )
    print("   ✅ Orchestrator created")
    
    # Run first volley
    print("\n4. Running first volley (each agent sends 10 messages)...")
    print("-" * 70)
    final_state = orchestrator.run_volley()
    print("-" * 70)
    
    # Display results
    print("\n5. Volley Results:")
    print(f"   Total messages: {len(final_state.get('messages', []))}")
    print(f"   Volley complete: {final_state.get('is_complete', False)}")
    
    if final_state.get('current_plan'):
        plan = final_state['current_plan']
        print("\n6. Generated Travel Plan:")
        print(f"   📍 Location: {plan.get('location', 'N/A')}")
        print(f"   📅 Dates: {plan.get('dates', {}).get('departure_date', 'N/A')} to {plan.get('dates', {}).get('return_date', 'N/A')}")
        print(f"   ✈️  Flight: {plan.get('flight', {}).get('origin', 'N/A')} → {plan.get('flight', {}).get('destination', 'N/A')}")
        print(f"   🏨 Hotel: {plan.get('hotel', {}).get('type', 'N/A')} in {plan.get('hotel', {}).get('location', 'N/A')}")
        print(f"   💰 Budget: ${plan.get('budget', {}).get('total_per_person', 'N/A')} per person")
        print(f"   🤝 Compromises: {plan.get('compromises_made', 'N/A')[:100]}...")
    
    # Simulate rejection
    print("\n7. Simulating plan rejection...")
    feedback = "The budget is too high. Can we find more affordable options while still enjoying the trip?"
    updated_state = orchestrator.handle_rejection(
        current_state=final_state,
        feedback=feedback,
        user_id=user_ids[0]
    )
    
    # Run second volley
    print("\n8. Running second volley after rejection...")
    print("-" * 70)
    final_state_2 = orchestrator.run_volley(initial_state=updated_state)
    print("-" * 70)
    
    # Display updated results
    if final_state_2.get('current_plan'):
        plan = final_state_2['current_plan']
        print("\n9. Updated Travel Plan (After Feedback):")
        print(f"   📍 Location: {plan.get('location', 'N/A')}")
        print(f"   💰 New Budget: ${plan.get('budget', {}).get('total_per_person', 'N/A')} per person")
        print(f"   🤝 New Compromises: {plan.get('compromises_made', 'N/A')[:100]}...")
    
    print("\n" + "="*70)
    print("EXAMPLE COMPLETED!")
    print("="*70)
    print(f"\nTotal messages in final state: {len(final_state_2.get('messages', []))}")
    print(f"Final plan ID: {final_state_2.get('current_plan', {}).get('plan_id', 'N/A')}")
    
    return final_state_2


def simple_example():
    """Simple example with minimal setup"""
    print("="*70)
    print("SIMPLE GROUP CHAT EXAMPLE")
    print("="*70)
    
    # Create 2 users with contrasting preferences
    user1 = UserProfile(
        user_id="user_simple_1",
        user_name="Budget Traveler",
        email="budget@example.com",
        preferences=UserPreferences(
            budget_range=(800, 1500),
            preferred_destinations=["hostels", "budget hotels"],
            travel_style="budget",
            dietary_restrictions=[],
            mobility_requirements=[]
        ),
        memories=[
            UserMemory(
                memory_id="mem_1",
                user_id="user_simple_1",
                content="Loves finding cheap flights and staying in hostels",
                memory_type="preference",
                created_at=datetime.now()
            )
        ]
    )
    
    user2 = UserProfile(
        user_id="user_simple_2",
        user_name="Luxury Seeker",
        email="luxury@example.com",
        preferences=UserPreferences(
            budget_range=(4000, 6000),
            preferred_destinations=["5-star hotels", "luxury resorts"],
            travel_style="luxury",
            dietary_restrictions=[],
            mobility_requirements=[]
        ),
        memories=[
            UserMemory(
                memory_id="mem_2",
                user_id="user_simple_2",
                content="Only stays in 5-star accommodations with premium amenities",
                memory_type="preference",
                created_at=datetime.now()
            )
        ]
    )
    
    # Create orchestrator
    orchestrator = GroupChatOrchestrator(
        users=[user1, user2],
        messages_per_volley=5,  # Shorter for demo
        llm_model="claude-sonnet-4"
    )
    
    # Run volley
    print("\nRunning negotiation between budget and luxury travelers...")
    print("-" * 70)
    result = orchestrator.run_volley()
    print("-" * 70)
    
    if result.get('current_plan'):
        plan = result['current_plan']
        print("\n🎉 Compromised Plan Created!")
        print(f"   Budget: ${plan.get('budget', {}).get('total_per_person', 'N/A')} per person")
        print(f"   Compromises: {plan.get('compromises_made', 'N/A')}")
    
    return result


if __name__ == "__main__":
    # Run the full example
    # Uncomment the example you want to run:
    
    # Full example with database
    run_group_chat_example()
    
    # Simple in-memory example
    # simple_example()

