"""
Example: Using Expedia Prebuilt Actions with browser-use Agent
Demonstrates how to use high-level prebuilt actions for faster execution
"""

import asyncio
import os
from dotenv import load_dotenv
from browser_use import Agent, ChatOpenAI
from browser_use.browser.browser import Browser, BrowserConfig
from expedia_prebuilt_actions import expedia_prebuilt

# Load environment variables
load_dotenv()

# Initialize LLM (using browser-use's ChatOpenAI wrapper)
def get_llm():
    """
    Get LLM instance. Set OPENAI_API_KEY in your .env file or environment.
    
    Note: We use browser_use.ChatOpenAI (not langchain_openai.ChatOpenAI)
    because browser-use requires its own LLM wrappers.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment. "
            "Please set it in your .env file or environment variables."
        )
    
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.0,
    )

async def run_all_tests_on_single_browser():
    """Run all tests sequentially on a single browser instance"""
    print("\n" + "="*70)
    print("EXPEDIA PREBUILT ACTIONS - E2E TEST")
    print("Running all tests on ONE browser instance")
    print("="*70)
    
    # Initialize LLM once
    llm = get_llm()
    
    # Initialize browser once
    browser = Browser(
        config=BrowserConfig(
            headless=False,
            disable_security=False,
        )
    )
    
    print("\n✅ Browser initialized - will be reused for all tasks")
    print("=" * 70)
    
    try:
        # Single comprehensive task that does everything
        print("\n🚀 Starting complete end-to-end booking flow...")
        
        agent = Agent(
            task=(
                "Complete a full flight booking on Expedia from SFO to LAX:\n"
                "\n"
                "STEP 1: Navigate to Expedia and search for flights\n"
                "- Origin: SFO (San Francisco)\n"
                "- Destination: LAX (Los Angeles)\n"
                "- Departure: 12/15/2025\n"
                "- Return: 12/20/2025\n"
                "- 1 adult, economy class\n"
                "\n"
                "STEP 2: Select flights\n"
                "- Sort results by price (lowest to highest)\n"
                "- Select the cheapest Basic fare option for both outbound and return\n"
                "\n"
                "STEP 3: Fill traveler information\n"
                "- First name: John\n"
                "- Last name: Doe\n"
                "- Email: john.doe@example.com\n"
                "- Phone: +1 4155551234\n"
                "- Gender: Male\n"
                "- Date of birth: 05/15/1990\n"
                "\n"
                "STEP 4: Proceed to checkout\n"
                "- Click the checkout button\n"
                "- Handle any popup/nudge dialogs\n"
                "\n"
                "STEP 5: Fill payment information\n"
                "- Cardholder name: John Doe\n"
                "- Card number: 4111 1111 1111 1111 (test card)\n"
                "- Expiration: 12/2027\n"
                "- CVV: 123\n"
                "- Billing address: 123 Main St\n"
                "- City: San Francisco\n"
                "- State: CA\n"
                "- ZIP: 94102\n"
                "\n"
                "IMPORTANT: DO NOT click the final 'Complete Booking' button.\n"
                "Stop after filling the payment form. This is test data only."
            ),
            llm=llm,
            browser=browser,
        )
        
        # Register prebuilt actions
        agent.controller.registry = expedia_prebuilt
        
        print("\n📋 Task registered with agent")
        print("🎯 Prebuilt actions enabled for 10-100x speed boost")
        print("\n" + "=" * 70)
        print("Starting agent execution...")
        print("=" * 70 + "\n")
        
        # Run the agent
        result = await agent.run(max_steps=100)
        
        print("\n" + "=" * 70)
        print("✅ AGENT EXECUTION COMPLETE!")
        print("=" * 70)
        print(f"\n📊 Final Result:\n{result}")
        
        print("\n⏳ Browser will stay open for 120 seconds to review...")
        print("   Press Ctrl+C to exit early")
        
        await asyncio.sleep(120)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔄 Closing browser...")
        await browser.close()
        print("✅ Browser closed")


async def main():
    """Run the E2E test"""
    await run_all_tests_on_single_browser()


if __name__ == "__main__":
    asyncio.run(main())

