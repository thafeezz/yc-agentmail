"""
Test script for the Expedia agent inbox reading tool.
Demonstrates how the agent can access emails from its dedicated inbox.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_expedia_inbox_tool():
    """Test the read_expedia_inbox tool functionality."""
    print("\n" + "="*60)
    print("Testing Expedia Agent Inbox Tool")
    print("="*60 + "\n")
    
    try:
        # Import the tool
        from api.expedia_agent.expedia_prebuilt_actions import read_expedia_inbox
        
        # Create a mock browser session (the tool doesn't actually use it for inbox reading)
        class MockBrowserSession:
            pass
        
        mock_session = MockBrowserSession()
        
        # Test reading inbox with default limit
        print("📧 Reading Expedia inbox (limit: 10)...")
        result = await read_expedia_inbox(mock_session, limit=10)
        print(result)
        
        # Test reading inbox with custom limit
        print("\n" + "-"*60)
        print("📧 Reading Expedia inbox (limit: 5)...")
        result_limited = await read_expedia_inbox(mock_session, limit=5)
        print(result_limited)
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_tool_registration():
    """Verify the tool is properly registered in the expedia_tools registry."""
    print("\n" + "="*60)
    print("Verifying Tool Registration")
    print("="*60 + "\n")
    
    try:
        from api.expedia_agent.expedia_agent_tools import expedia_tools
        
        # List all registered actions
        actions = list(expedia_tools.registry.actions.keys())
        print(f"Total registered tools: {len(actions)}\n")
        
        # Check if our inbox tool is registered
        inbox_tool_name = 'Read emails from Expedia agent inbox'
        if inbox_tool_name in actions:
            print(f"✅ '{inbox_tool_name}' is registered!")
        else:
            print(f"❌ '{inbox_tool_name}' NOT found in registry")
        
        # Show a sample of registered tools
        print("\nSample of registered tools:")
        for i, action in enumerate(actions[:5], 1):
            print(f"  {i}. {action}")
        
        if len(actions) > 5:
            print(f"  ... and {len(actions) - 5} more")
        
        print("\n✅ Registration check completed!")
        
    except Exception as e:
        print(f"\n❌ Registration check failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    # Test 1: Verify tool registration
    await test_tool_registration()
    
    # Test 2: Test inbox reading functionality
    await test_expedia_inbox_tool()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

