"""
Test Group Chat Tools Integration
Verifies that HyperSpell and Perplexity tools are available to group chat agents.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def test_tool_creation():
    """Test creating user-specific tools"""
    print("\n" + "="*80)
    print("Testing Group Chat Tools Creation")
    print("="*80 + "\n")
    
    from api.tools import get_group_chat_tools
    
    # Test with a sample user
    user_id = "test_user_001"
    user_name = "Alice"
    
    tools = get_group_chat_tools(user_id, user_name)
    
    print(f"Created {len(tools)} tools for {user_name}:\n")
    for tool in tools:
        print(f"  ✓ {tool.name}")
        print(f"    Description: {tool.description[:100]}...")
        print()
    
    # Verify expected tools
    tool_names = [tool.name for tool in tools]
    
    expected = []
    if os.getenv("HYPERSPELL_API_KEY"):
        expected.append(f"search_{user_name.lower()}_memories")
    if os.getenv("PERPLEXITY_API_KEY"):
        expected.append("search_travel_info")
    
    print(f"Expected tools: {expected}")
    print(f"Available tools: {tool_names}")
    
    for exp in expected:
        if exp in tool_names:
            print(f"  ✅ {exp} is available")
        else:
            print(f"  ❌ {exp} is missing")
    
    return tools


def test_hyperspell_tool():
    """Test HyperSpell memory search tool"""
    print("\n" + "="*80)
    print("Testing HyperSpell Tool")
    print("="*80 + "\n")
    
    if not os.getenv("HYPERSPELL_API_KEY"):
        print("⚠️  HYPERSPELL_API_KEY not set - skipping test")
        return
    
    from api.tools import create_user_hyperspell_tool
    
    user_id = "test_user_001"
    user_name = "Alice"
    
    tool = create_user_hyperspell_tool(user_id, user_name)
    
    print(f"Tool Name: {tool.name}")
    print(f"Description: {tool.description}\n")
    
    # Test search
    try:
        result = tool.invoke({"query": "travel preferences"})
        print("Search Result:")
        print(result)
        print("\n✅ HyperSpell tool test passed!")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_perplexity_tool():
    """Test Perplexity search tool"""
    print("\n" + "="*80)
    print("Testing Perplexity Tool")
    print("="*80 + "\n")
    
    if not os.getenv("PERPLEXITY_API_KEY"):
        print("⚠️  PERPLEXITY_API_KEY not set - skipping test")
        return
    
    from api.tools import search_travel_info
    
    print(f"Tool Name: {search_travel_info.name}")
    print(f"Description: {search_travel_info.description[:200]}...\n")
    
    # Test search
    try:
        result = search_travel_info.invoke({
            "query": "best beaches in Hawaii",
            "max_results": 3
        })
        print("Search Result:")
        print(result[:500] + "...")  # First 500 chars
        print("\n✅ Perplexity tool test passed!")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_orchestrator_integration():
    """Test tools are integrated into orchestrator"""
    print("\n" + "="*80)
    print("Testing Orchestrator Integration")
    print("="*80 + "\n")
    
    from api.group_chat.orchestrator import GroupChatOrchestrator
    from api.group_chat.models import UserProfile, UserPreferences
    
    # Create test users
    users = [
        UserProfile(
            user_id="user_001",
            user_name="Alice",
            email="alice@example.com",
            preferences=UserPreferences(
                budget_range=(1000, 2000),
                travel_style="adventure",
                preferred_destinations=["mountains", "beaches"]
            )
        ),
        UserProfile(
            user_id="user_002", 
            user_name="Bob",
            email="bob@example.com",
            preferences=UserPreferences(
                budget_range=(1500, 2500),
                travel_style="relaxation",
                preferred_destinations=["beaches", "resorts"]
            )
        )
    ]
    
    # Create orchestrator
    try:
        orchestrator = GroupChatOrchestrator(
            users=users,
            messages_per_volley=2
        )
        
        print(f"✅ Orchestrator created successfully")
        print(f"   Participants: {[u.user_name for u in users]}")
        print(f"   Base tools: {len(orchestrator.base_tools)}")
        
        # Check user-specific tools
        for user in users:
            tools = orchestrator.user_tools.get(user.user_id, [])
            print(f"   {user.user_name}'s tools: {len(tools)}")
            for tool in tools:
                print(f"     - {tool.name}")
        
        print("\n✅ Orchestrator integration test passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("GROUP CHAT TOOLS TEST SUITE")
    print("="*80)
    
    # Test 1: Tool creation
    tools = test_tool_creation()
    
    # Test 2: HyperSpell tool (if available)
    test_hyperspell_tool()
    
    # Test 3: Perplexity tool (if available)
    test_perplexity_tool()
    
    # Test 4: Orchestrator integration
    test_orchestrator_integration()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80 + "\n")
    
    # Summary
    print("Summary:")
    print(f"  - HyperSpell: {'✅ Available' if os.getenv('HYPERSPELL_API_KEY') else '❌ Not configured'}")
    print(f"  - Perplexity: {'✅ Available' if os.getenv('PERPLEXITY_API_KEY') else '❌ Not configured'}")
    print("\nTo enable missing tools, set the API keys in your .env file:")
    print("  - HYPERSPELL_API_KEY=your-key-here")
    print("  - PERPLEXITY_API_KEY=your-key-here")


if __name__ == "__main__":
    main()

