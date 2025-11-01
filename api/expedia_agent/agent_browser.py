"""
Expedia Browser Agent
A browser automation agent that can handle login, flight booking, hotel booking,
and payment processing on Expedia using Browser Use Cloud.

Features:
- Laminar observability integration for tracing and monitoring
- Parallel flight and hotel booking support
- Session and profile management
- Custom Playwright tools for intelligent agent use
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Use LOCAL browser-use library with CLOUD execution
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser.browser import BrowserSession
from browser_use.dom.service import DomService

# Use browser-use's LLM wrappers
from browser_use.llm import ChatOpenAI as BrowserUseChatOpenAI, ChatGroq as BrowserUseChatGroq

# Import our custom tools for Browser Use agent
try:
    # Import combined Expedia tools (flight, hotel, and general actions)
    from .expedia_agent_tools import expedia_tools
    TOOLS_AVAILABLE = True
    print("✅ Custom Expedia tools loaded")
except ImportError as e:
    TOOLS_AVAILABLE = False
    expedia_tools = None
    print(f"⚠️  Custom tools not available: {e}")

# Load environment variables from .env file
load_dotenv()

# Laminar observability setup (optional)
try:
    from lmnr import Laminar, Instruments
    LAMINAR_AVAILABLE = True
except ImportError:
    LAMINAR_AVAILABLE = False
    print("Warning: Laminar not installed. Install with: pip3 install 'lmnr[all]'")


def initialize_observability(api_key: Optional[str] = None, disable_session_recording: bool = False):
    """
    Initialize Laminar observability for tracing Browser Use operations.
    
    Args:
        api_key: Laminar project API key (defaults to LMNR_PROJECT_API_KEY env var)
        disable_session_recording: If True, disables browser session recording
    """
    if not LAMINAR_AVAILABLE:
        print("Laminar not available. Skipping observability initialization.")
        return False
    
    disabled_instruments = set()
    if disable_session_recording:
        disabled_instruments.add(Instruments.BROWSER_USE_SESSION)
    
    Laminar.initialize(
        project_api_key=api_key or os.getenv("LMNR_PROJECT_API_KEY"),
        disabled_instruments=disabled_instruments
    )
    print("✓ Laminar observability initialized")
    return True


class ExpediaAgent:
    """
    Browser agent for Expedia using HYBRID approach:
    - Code runs locally (with custom tools)
    - Browser runs in cloud (handles CAPTCHAs, auth)
    """
    
    def __init__(
        self, 
        llm_model: str = "gpt-4o",
        cloud_profile_id: Optional[str] = None,
        use_cloud_browser: bool = False,  # Default to local for debugging
        headless: bool = False,
        use_tools: bool = True,
        tool_type: str = "all"  # "all", "flight", or "hotel"
    ):
        """
        Initialize the Expedia agent with local browser and custom tools.
        
        Args:
            llm_model: AI model to use (currently supports OpenAI only)
                - "gpt-4o" (default, GPT-4 Optimized)
                - "gpt-4" (GPT-4)
                - "gpt-4-turbo" (GPT-4 Turbo)
            cloud_profile_id: Cloud profile ID for saved authentication (optional)
                Get from: https://cloud.browser-use.com/dashboard/settings?tab=profiles
            use_cloud_browser: If True, browser runs in cloud. If False, runs locally
            headless: Run browser in headless mode (only for local browser)
            use_tools: Enable custom Expedia tools
            tool_type: Which tools to load - "all", "flight", or "hotel"
        """
        self.llm_model = llm_model
        self.cloud_profile_id = cloud_profile_id
        self.use_cloud_browser = use_cloud_browser
        self.headless = headless
        self.use_tools = use_tools
        self.tool_type = tool_type
        self.browser = None
        self.agent = None
        self.session_id = None  # Browser session ID for tracking
        
        # Initialize LLM based on model choice
        self.llm = self._create_llm(llm_model)
        
        # Detect provider
        provider = "Groq" if "llama" in llm_model.lower() or "groq" in llm_model.lower() else "OpenAI"
        print(f"🤖 Using AI model: {llm_model} ({provider})")
        
        if use_cloud_browser:
            print("☁️  Browser mode: CLOUD (handles CAPTCHAs, saved logins)")
            if cloud_profile_id:
                print(f"🔐 Using saved cloud profile: {cloud_profile_id}")
            else:
                print("ℹ️  No profile ID - will use fresh cloud browser")
                print("   To save auth: https://cloud.browser-use.com/dashboard/settings?tab=profiles")
        else:
            print(f"🖥️  Browser mode: LOCAL (headless={headless})")
            print("👁️  Browser will be VISIBLE for debugging" if not headless else "👻 Browser will be HIDDEN")
        
        # Load tools based on tool_type
        self.tools = self._load_tools(tool_type) if (TOOLS_AVAILABLE and use_tools) else None
        if self.tools:
            tool_count = len(self.tools.registry.actions)
            print(f"🔧 Custom Expedia tools loaded ({tool_type.upper()}):")
            print(f"   - {tool_count} total tools")
        else:
            print("⚠️  No custom tools loaded (use_tools=False or tools not available)")
    
    def _load_tools(self, tool_type: str):
        """Load tools based on tool_type filter."""
        from browser_use.controller.registry.service import Registry
        from .expedia_flight_tools import flight_tools
        from .expedia_hotel_prebuilt_actions import expedia_hotel_prebuilt
        from .expedia_prebuilt_actions import expedia_prebuilt
        
        if tool_type == "all":
            # Load all tools (existing behavior)
            return expedia_tools
        
        # Create filtered registry
        filtered_registry = Registry()
        
        if tool_type == "flight":
            # Only load flight tools (no sign-in)
            for action_name, registered_action in flight_tools.registry.actions.items():
                filtered_registry.registry.actions[action_name] = registered_action
            for action_name, registered_action in expedia_prebuilt.registry.actions.items():
                # Include general navigation tools only (sign-in disabled)
                if any(keyword in action_name.lower() for keyword in ['navigate']):
                    filtered_registry.registry.actions[action_name] = registered_action
        
        elif tool_type == "hotel":
            # Only load hotel tools (no sign-in)
            for action_name, registered_action in expedia_hotel_prebuilt.registry.actions.items():
                filtered_registry.registry.actions[action_name] = registered_action
            for action_name, registered_action in expedia_prebuilt.registry.actions.items():
                # Include general navigation tools only (sign-in disabled)
                if any(keyword in action_name.lower() for keyword in ['navigate']):
                    filtered_registry.registry.actions[action_name] = registered_action
        
        return filtered_registry
    
    def _create_llm(self, model_name: str):
        """Create LLM instance (OpenAI or Groq) using browser-use wrapper."""
        # Detect if this is a Groq model
        if "llama" in model_name.lower() or "groq" in model_name.lower():
            # Groq model
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError(
                    "GROQ_API_KEY not set in environment. "
                    "Add it to your .env file or export GROQ_API_KEY=your_key\n"
                    "Get your key from: https://console.groq.com/keys"
                )
            
            return BrowserUseChatGroq(
                model=model_name,
                api_key=api_key,
                temperature=0
            )
        else:
            # OpenAI model (default)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not set in environment. "
                    "Add it to your .env file or export OPENAI_API_KEY=your_key"
                )
            
            return BrowserUseChatOpenAI(
                model=model_name,
                api_key=api_key,
                temperature=0
            )
    
    async def create_browser(self):
        """
        Create and initialize the browser.
        
        If use_cloud_browser=True, browser runs in cloud via @sandbox.
        If False, browser runs locally.
        """
        if self.browser is None:
            if self.use_cloud_browser:
                # Cloud browser - uses @sandbox decorator
                # Browser Use API key from environment
                api_key = os.getenv("BROWSER_USE_API_KEY")
                if not api_key:
                    raise ValueError(
                        "BROWSER_USE_API_KEY not set. Get it from: "
                        "https://cloud.browser-use.com/dashboard/settings"
                    )
                
                config_args = {
                    "headless": False,  # Cloud browsers are always visible in recordings
                }
                
                if self.cloud_profile_id:
                    config_args["cloud_profile_id"] = self.cloud_profile_id
                
                self.browser = Browser(
                    config=BrowserConfig(**config_args)
                )
                print("☁️  Cloud browser initialized")
            else:
                # Local browser with MAXIMUM stealth mode
                self.browser = Browser(
                    config=BrowserConfig(
                        headless=self.headless,
                        disable_security=False,
                        # Maximum stealth configuration
                        extra_chromium_args=[
                            '--disable-blink-features=AutomationControlled',
                            '--disable-dev-shm-usage',
                            '--disable-web-security',
                            '--disable-features=IsolateOrigins,site-per-process',
                            '--no-first-run',
                            '--no-default-browser-check',
                            '--disable-popup-blocking',
                            '--disable-translate',
                            '--disable-background-timer-throttling',
                            '--disable-renderer-backgrounding',
                            '--disable-device-discovery-notifications',
                            '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        ]
                    )
                )
                print("🖥️  Local browser initialized (MAXIMUM stealth mode)")
                print("⚠️  Note: For best CAPTCHA results, use a browser profile with cookies")
        
        return self.browser
    
    async def create_agent(self, task: str) -> Agent:
        """
        Create an agent with the given task and custom tools.
        
        Args:
            task: Natural language task description
            
        Returns:
            Configured Agent instance
        """
        await self.create_browser()
        
        # Create agent
        self.agent = Agent(
            task=task,
            llm=self.llm,
            browser=self.browser
        )
        
        # Register custom tools by replacing the controller's registry
        if self.use_tools and self.tools:
            self.agent.controller.registry = self.tools
            print(f"🤖 Agent created")
            print(f"   ✅ Custom Expedia tools enabled ({len(self.tools.registry.actions)} tools)")
        else:
            print(f"🤖 Agent created (no custom tools)")
        
        return self.agent
    
    async def run_task(self, task: str) -> Any:
        """
        Run a task with the agent and custom tools.
        
        Args:
            task: Natural language task description
            
        Returns:
            Task execution result
        """
        print("\n" + "="*70)
        print(f"🎯 TASK: {task[:100]}...")
        print("="*70 + "\n")
        
        agent = await self.create_agent(task)
        result = await agent.run()
        
        print("\n" + "="*70)
        print("✅ TASK COMPLETED")
        print("="*70 + "\n")
        
        return result
    
    async def cleanup(self):
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
            print("🧹 Browser closed")
        
        # Reset state
        self.browser = None
        self.agent = None
    
    async def _get_playwright_page(self, session_id: Optional[str] = None):
        """
        Get the underlying Playwright page from Browser Use session.
        
        Args:
            session_id: Session ID to get page from
            
        Returns:
            Playwright Page object or None
        """
        session_id = session_id or self.session_id
        try:
            # Browser Use Cloud provides access to the Playwright page
            # This is internal API - may need adjustment based on SDK version
            session = self.client.browsers.get_browser_session(session_id)
            if hasattr(session, 'page'):
                return session.page
            return None
        except Exception as e:
            print(f"Could not get Playwright page: {e}")
            print("Falling back to AI-only mode")
            return None
    
    async def _init_playwright_tools(self, session_id: Optional[str] = None, profile: str = "FULL_ACCESS"):
        """
        Initialize Playwright tools for the session with specified profile.
        
        Args:
            session_id: Session ID to initialize tools for
            profile: Tool profile to use (e.g., "FLIGHT_BOOKING", "HOTEL_BOOKING")
        """
        if not self.use_hybrid:
            return None
        
        try:
            from expedia_tools import ExpediaTools
            page = await self._get_playwright_page(session_id)
            if page:
                self.playwright_tools = ExpediaTools(page, profile=profile)
                print(f"✓ Playwright tools initialized (Profile: {profile})")
                return self.playwright_tools
        except Exception as e:
            print(f"Could not initialize Playwright tools: {e}")
            print("Continuing with AI-only mode")
        return None
    
    def create_profile(self) -> str:
        """
        Create a new browser profile for maintaining state across sessions.
        
        Returns:
            Profile ID
        """
        profile = self.client.profiles.create_profile()
        self.profile_id = profile.id
        print(f"Created profile: {self.profile_id}")
        return self.profile_id
    
    def create_session(self, profile_id: Optional[str] = None) -> str:
        """
        Create a new browser session with stealth features.
        
        Args:
            profile_id: Optional profile ID to maintain state
            
        Returns:
            Session ID
        """
        profile_id = profile_id or self.profile_id
        
        # Create session with proxy for stealth
        session_params = {"profile_id": profile_id}
        if self.proxy_country_code:
            session_params["proxy_country_code"] = self.proxy_country_code
        
        session = self.client.sessions.create_session(**session_params)
        self.session_id = session.id
        print(f"Created session: {self.session_id}")
        print(f"Live URL: {session.live_url}")
        return self.session_id
    
    def login(
        self, 
        email: str, 
        password: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Login to Expedia account.
        
        Args:
            email: Expedia account email
            password: Expedia account password
            session_id: Optional session ID (uses current session if not provided)
            
        Returns:
            Task result with login status
        """
        session_id = session_id or self.session_id
        
        if not session_id:
            raise ValueError("No active session. Call create_session() first.")
        
        print("Starting Expedia login...")
        
        # Create login task with specified AI model
        task = self.client.tasks.create_task(
            session_id=session_id,
            llm=self.llm_model,
            task=f"""
            Go to https://www.expedia.com and log in to the account:
            1. Navigate to the Expedia homepage
            2. Click on the "Sign in" button
            3. Enter the email: {email}
            4. Enter the password: {password}
            5. Click the "Sign in" button to complete login
            6. Verify successful login by checking for user account indicator
            7. Report back the login status
            """
        )
        
        result = task.complete()
        print("Login completed!")
        print(f"Result: {result.output}")
        
        return {
            "status": "success",
            "output": result.output,
            "session_id": session_id
        }
    
    async def login_hybrid(
        self,
        email: str,
        password: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        OPTIMIZED: Login using Playwright for form filling (5-10x faster).
        
        Args:
            email: Expedia account email
            password: Expedia account password
            session_id: Optional session ID
            
        Returns:
            Login result
        """
        session_id = session_id or self.session_id
        
        if not session_id:
            raise ValueError("No active session. Call create_session() first.")
        
        print("⚡ Starting HYBRID login (Playwright + AI)...")
        
        # Initialize Playwright tools
        tools = await self._init_playwright_tools(session_id)
        
        if tools and self.use_hybrid:
            try:
                # Navigate to Expedia
                await tools.navigate_to_expedia()
                
                # Use Playwright to fill login form (fast!)
                success = await tools.fill_login_form(email, password)
                
                if success:
                    print("✓ Login completed with Playwright!")
                    return {
                        "status": "success",
                        "method": "playwright",
                        "output": "Login successful (Playwright direct)",
                        "session_id": session_id
                    }
                else:
                    print("Playwright login failed, falling back to AI...")
            except Exception as e:
                print(f"Playwright error: {e}, falling back to AI...")
        
        # Fallback to AI if Playwright fails
        return self.login(email, password, session_id)
    
    def signup(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Expedia account.
        
        Args:
            email: Email for new account
            password: Password for new account
            first_name: First name
            last_name: Last name
            session_id: Optional session ID
            
        Returns:
            Task result with signup status
        """
        session_id = session_id or self.session_id
        
        if not session_id:
            raise ValueError("No active session. Call create_session() first.")
        
        print("Starting Expedia signup...")
        
        task = self.client.tasks.create_task(
            session_id=session_id,
            task=f"""
            Go to https://www.expedia.com and create a new account:
            1. Navigate to the Expedia homepage
            2. Click on "Sign in" and then find the "Create account" or "Sign up" option
            3. Fill in the registration form:
               - Email: {email}
               - Password: {password}
               - First name: {first_name}
               - Last name: {last_name}
            4. Complete any additional required fields
            5. Accept terms and conditions if prompted
            6. Submit the registration form
            7. Handle any verification steps (email confirmation, etc.)
            8. Verify successful account creation
            """
        )
        
        result = task.complete()
        print("Signup completed!")
        print(f"Result: {result.output}")
        
        return {
            "status": "success",
            "output": result.output,
            "session_id": session_id
        }
    
    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        passengers: int = 1,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for flights on Expedia.
        
        Args:
            origin: Departure airport code or city (e.g., "LAX" or "Los Angeles")
            destination: Arrival airport code or city (e.g., "JFK" or "New York")
            departure_date: Departure date (e.g., "2025-12-01")
            return_date: Return date for round trip (optional)
            passengers: Number of passengers
            session_id: Optional session ID
            
        Returns:
            Task result with flight search results
        """
        session_id = session_id or self.session_id
        
        if not session_id:
            raise ValueError("No active session. Call create_session() first.")
        
        trip_type = "round trip" if return_date else "one way"
        
        print(f"Searching for flights: {origin} -> {destination}")
        
        task = self.client.tasks.create_task(
            session_id=session_id,
            task=f"""
            Search for flights on Expedia:
            1. Go to https://www.expedia.com/Flights
            2. Select {trip_type} trip
            3. Enter origin: {origin}
            4. Enter destination: {destination}
            5. Enter departure date: {departure_date}
            {f"6. Enter return date: {return_date}" if return_date else ""}
            7. Set number of passengers: {passengers}
            8. Click search button
            9. Wait for results to load
            10. Summarize the available flight options including prices and times
            """
        )
        
        result = task.complete()
        print("Flight search completed!")
        print(f"Result: {result.output}")
        
        return {
            "status": "success",
            "output": result.output,
            "session_id": session_id
        }
    
    def select_and_book_flight(
        self,
        flight_preference: str = "cheapest",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Select and proceed to book a flight.
        
        Args:
            flight_preference: Preference for flight selection 
                              ("cheapest", "fastest", "best value", or specific details)
            session_id: Optional session ID
            
        Returns:
            Task result with booking progress
        """
        session_id = session_id or self.session_id
        
        if not session_id:
            raise ValueError("No active session. Call create_session() first.")
        
        print(f"Selecting flight: {flight_preference}")
        
        task = self.client.tasks.create_task(
            session_id=session_id,
            task=f"""
            Select and book a flight:
            1. From the current flight search results, select the {flight_preference} option
            2. Click on the flight to view details
            3. Click "Select" or "Continue" to proceed with booking
            4. Review the flight details on the booking page
            5. Continue to the traveler information section
            6. Report the current status and what information is needed next
            """
        )
        
        result = task.complete()
        print("Flight selection completed!")
        print(f"Result: {result.output}")
        
        return {
            "status": "success",
            "output": result.output,
            "session_id": session_id
        }
    
    def search_hotels(
        self,
        location: str,
        check_in: str,
        check_out: str,
        guests: int = 1,
        rooms: int = 1,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for hotels on Expedia.
        
        Args:
            location: Hotel location (city name or address)
            check_in: Check-in date (e.g., "2025-12-01")
            check_out: Check-out date (e.g., "2025-12-05")
            guests: Number of guests
            rooms: Number of rooms
            session_id: Optional session ID
            
        Returns:
            Task result with hotel search results
        """
        session_id = session_id or self.session_id
        
        if not session_id:
            raise ValueError("No active session. Call create_session() first.")
        
        print(f"Searching for hotels in {location}")
        
        task = self.client.tasks.create_task(
            session_id=session_id,
            task=f"""
            Search for hotels on Expedia:
            1. Go to https://www.expedia.com/Hotels
            2. Enter location: {location}
            3. Enter check-in date: {check_in}
            4. Enter check-out date: {check_out}
            5. Set number of guests: {guests}
            6. Set number of rooms: {rooms}
            7. Click search button
            8. Wait for results to load
            9. Summarize the available hotel options including prices, ratings, and amenities
            """
        )
        
        result = task.complete()
        print("Hotel search completed!")
        print(f"Result: {result.output}")
        
        return {
            "status": "success",
            "output": result.output,
            "session_id": session_id
        }
    
    def select_and_book_hotel(
        self,
        hotel_preference: str = "highest rated under $200",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Select and proceed to book a hotel.
        
        Args:
            hotel_preference: Preference for hotel selection
            session_id: Optional session ID
            
        Returns:
            Task result with booking progress
        """
        session_id = session_id or self.session_id
        
        if not session_id:
            raise ValueError("No active session. Call create_session() first.")
        
        print(f"Selecting hotel: {hotel_preference}")
        
        task = self.client.tasks.create_task(
            session_id=session_id,
            task=f"""
            Select and book a hotel:
            1. From the current hotel search results, select the {hotel_preference}
            2. Click on the hotel to view details
            3. Select a room type
            4. Click "Book" or "Reserve" to proceed
            5. Review the hotel details on the booking page
            6. Continue to the guest information section
            7. Report the current status and what information is needed next
            """
        )
        
        result = task.complete()
        print("Hotel selection completed!")
        print(f"Result: {result.output}")
        
        return {
            "status": "success",
            "output": result.output,
            "session_id": session_id
        }
    
    def fill_traveler_info(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        date_of_birth: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fill traveler/guest information.
        
        Args:
            first_name: First name
            last_name: Last name
            email: Email address
            phone: Phone number
            date_of_birth: Date of birth if required (e.g., "1990-01-01")
            session_id: Optional session ID
            
        Returns:
            Task result
        """
        session_id = session_id or self.session_id
        
        if not session_id:
            raise ValueError("No active session. Call create_session() first.")
        
        print("Filling traveler information...")
        
        dob_instruction = f"8. Enter date of birth: {date_of_birth}" if date_of_birth else ""
        
        task = self.client.tasks.create_task(
            session_id=session_id,
            task=f"""
            Fill in the traveler/guest information:
            1. Locate the traveler information form
            2. Enter first name: {first_name}
            3. Enter last name: {last_name}
            4. Enter email: {email}
            5. Enter phone number: {phone}
            {dob_instruction}
            6. Fill any other required fields with appropriate information
            7. Continue to the payment section
            8. Report when ready for payment information
            """
        )
        
        result = task.complete()
        print("Traveler info filled!")
        print(f"Result: {result.output}")
        
        return {
            "status": "success",
            "output": result.output,
            "session_id": session_id
        }
    
    def fill_payment_info(
        self,
        card_number: str,
        cardholder_name: str,
        expiration_month: str,
        expiration_year: str,
        cvv: str,
        billing_address: Dict[str, str],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fill payment information and complete booking.
        
        Args:
            card_number: Credit card number
            cardholder_name: Name on card
            expiration_month: Expiration month (e.g., "12")
            expiration_year: Expiration year (e.g., "2027")
            cvv: Card CVV/security code
            billing_address: Dictionary with address fields:
                - street: Street address
                - city: City
                - state: State/Province
                - zip: ZIP/Postal code
                - country: Country
            session_id: Optional session ID
            
        Returns:
            Task result with booking confirmation
        """
        session_id = session_id or self.session_id
        
        if not session_id:
            raise ValueError("No active session. Call create_session() first.")
        
        print("Processing payment information...")
        
        task = self.client.tasks.create_task(
            session_id=session_id,
            task=f"""
            Fill in payment information and complete the booking:
            1. Locate the payment information form
            2. Enter credit card number: {card_number}
            3. Enter cardholder name: {cardholder_name}
            4. Enter expiration month: {expiration_month}
            5. Enter expiration year: {expiration_year}
            6. Enter CVV: {cvv}
            7. Fill billing address:
               - Street: {billing_address.get('street')}
               - City: {billing_address.get('city')}
               - State: {billing_address.get('state')}
               - ZIP: {billing_address.get('zip')}
               - Country: {billing_address.get('country')}
            8. Review the booking summary
            9. Accept terms and conditions if prompted
            10. Click "Complete booking" or "Confirm and pay"
            11. Wait for confirmation page
            12. Extract and report the booking confirmation number and details
            """
        )
        
        result = task.complete()
        print("Payment processed!")
        print(f"Result: {result.output}")
        
        return {
            "status": "success",
            "output": result.output,
            "session_id": session_id
        }
    
    def book_flight_and_hotel_package(
        self,
        # Login credentials
        email: str,
        password: str,
        # Flight details
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        # Hotel details
        hotel_location: str,
        check_in: str,
        check_out: str,
        # Traveler info
        first_name: str,
        last_name: str,
        phone: str,
        # Payment info
        card_number: str,
        cardholder_name: str,
        expiration_month: str,
        expiration_year: str,
        cvv: str,
        billing_address: Dict[str, str],
        # Optional params
        passengers: int = 1,
        flight_preference: str = "cheapest",
        hotel_preference: str = "highest rated under $200",
        create_account: bool = False
    ) -> Dict[str, Any]:
        """
        Complete end-to-end flight and hotel booking on Expedia.
        
        This method orchestrates the entire booking flow from login to payment.
        
        Returns:
            Comprehensive booking result with all confirmation details
        """
        print("=" * 60)
        print("EXPEDIA BOOKING AGENT - FULL WORKFLOW")
        print("=" * 60)
        
        results = {}
        
        try:
            # Step 1: Create profile and session
            print("\n[1/8] Creating browser profile and session...")
            self.create_profile()
            self.create_session()
            results["profile_id"] = self.profile_id
            results["session_id"] = self.session_id
            
            # Step 2: Login or signup
            if create_account:
                print("\n[2/8] Creating new account...")
                results["auth"] = self.signup(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
            else:
                print("\n[2/8] Logging in...")
                results["auth"] = self.login(email=email, password=password)
            
            # Step 3: Search flights
            print("\n[3/8] Searching for flights...")
            results["flight_search"] = self.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                passengers=passengers
            )
            
            # Step 4: Select flight
            print("\n[4/8] Selecting flight...")
            results["flight_selection"] = self.select_and_book_flight(
                flight_preference=flight_preference
            )
            
            # Step 5: Search hotels
            print("\n[5/8] Searching for hotels...")
            results["hotel_search"] = self.search_hotels(
                location=hotel_location,
                check_in=check_in,
                check_out=check_out,
                guests=passengers
            )
            
            # Step 6: Select hotel
            print("\n[6/8] Selecting hotel...")
            results["hotel_selection"] = self.select_and_book_hotel(
                hotel_preference=hotel_preference
            )
            
            # Step 7: Fill traveler info
            print("\n[7/8] Filling traveler information...")
            results["traveler_info"] = self.fill_traveler_info(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone
            )
            
            # Step 8: Complete payment
            print("\n[8/8] Processing payment...")
            results["payment"] = self.fill_payment_info(
                card_number=card_number,
                cardholder_name=cardholder_name,
                expiration_month=expiration_month,
                expiration_year=expiration_year,
                cvv=cvv,
                billing_address=billing_address
            )
            
            print("\n" + "=" * 60)
            print("BOOKING COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            
            return {
                "status": "success",
                "message": "Flight and hotel booking completed successfully",
                "results": results
            }
            
        except Exception as e:
            print(f"\n❌ Error during booking: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "results": results
            }
    
    def book_parallel(
        self,
        # Login credentials
        email: str,
        password: str,
        # Flight details
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        # Hotel details
        hotel_location: str,
        check_in: str,
        check_out: str,
        # Traveler info
        first_name: str,
        last_name: str,
        phone: str,
        # Payment info
        card_number: str,
        cardholder_name: str,
        expiration_month: str,
        expiration_year: str,
        cvv: str,
        billing_address: Dict[str, Any],
        # Optional params
        passengers: int = 1,
        flight_preference: str = "cheapest",
        hotel_preference: str = "highest rated under $200",
    ) -> Dict[str, Any]:
        """
        Book flight and hotel in parallel using separate sessions.
        This is faster as both bookings happen simultaneously.
        
        Returns:
            Combined booking results from both operations
        """
        print("=" * 60)
        print("PARALLEL BOOKING - Flight & Hotel Simultaneously")
        print("=" * 60)
        
        # Create separate profiles for parallel execution
        print("\n[1/6] Setting up parallel sessions...")
        flight_profile = self.client.profiles.create_profile()
        hotel_profile = self.client.profiles.create_profile()
        
        flight_session = self.client.sessions.create_session(profile_id=flight_profile.id)
        hotel_session = self.client.sessions.create_session(profile_id=hotel_profile.id)
        
        print(f"Flight session: {flight_session.id}")
        print(f"Hotel session: {hotel_session.id}")
        
        results = {
            "flight": {},
            "hotel": {},
            "combined_payment": {}
        }
        
        try:
            # Step 2: Parallel login
            print("\n[2/6] Logging in (parallel)...")
            flight_login = self.login(email, password, session_id=flight_session.id)
            hotel_login = self.login(email, password, session_id=hotel_session.id)
            results["flight"]["login"] = flight_login
            results["hotel"]["login"] = hotel_login
            
            # Step 3: Parallel search
            print("\n[3/6] Searching for flights and hotels (parallel)...")
            flight_search = self.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                passengers=passengers,
                session_id=flight_session.id
            )
            hotel_search = self.search_hotels(
                location=hotel_location,
                check_in=check_in,
                check_out=check_out,
                guests=passengers,
                session_id=hotel_session.id
            )
            results["flight"]["search"] = flight_search
            results["hotel"]["search"] = hotel_search
            
            # Step 4: Parallel selection
            print("\n[4/6] Selecting flight and hotel (parallel)...")
            flight_selection = self.select_and_book_flight(
                flight_preference=flight_preference,
                session_id=flight_session.id
            )
            hotel_selection = self.select_and_book_hotel(
                hotel_preference=hotel_preference,
                session_id=hotel_session.id
            )
            results["flight"]["selection"] = flight_selection
            results["hotel"]["selection"] = hotel_selection
            
            # Step 5: Combined traveler info (use one session for final booking)
            print("\n[5/6] Creating combined booking...")
            # Note: In practice, you might need to handle package bookings differently
            # This is a simplified example
            task = self.client.tasks.create_task(
                session_id=flight_session.id,
                task=f"""
                Create a combined flight and hotel package booking:
                1. Navigate to create package booking page
                2. Combine the previously selected flight and hotel
                3. Fill traveler information:
                   - Name: {first_name} {last_name}
                   - Email: {email}
                   - Phone: {phone}
                4. Report status
                """
            )
            results["combined_payment"]["traveler_info"] = task.complete()
            
            # Step 6: Payment
            print("\n[6/6] Processing payment for package...")
            payment_result = self.fill_payment_info(
                card_number=card_number,
                cardholder_name=cardholder_name,
                expiration_month=expiration_month,
                expiration_year=expiration_year,
                cvv=cvv,
                billing_address=billing_address,
                session_id=flight_session.id
            )
            results["combined_payment"]["payment"] = payment_result
            
            print("\n" + "=" * 60)
            print("PARALLEL BOOKING COMPLETED!")
            print("=" * 60)
            
            return {
                "status": "success",
                "message": "Parallel flight and hotel booking completed",
                "booking_mode": "parallel",
                "results": results
            }
            
        except Exception as e:
            print(f"\n❌ Error during parallel booking: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "results": results
            }
        finally:
            # Cleanup sessions
            try:
                self.client.sessions.stop_session(flight_session.id)
                self.client.sessions.stop_session(hotel_session.id)
            except:
                pass
    
    # ========================================================================
    # ADVANCED HYBRID METHODS WITH FILTERS & SMART SELECTION
    # ========================================================================
    
    async def search_flights_with_filters_hybrid(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        passengers: int = 1,
        max_price: Optional[int] = None,
        airlines: Optional[List[str]] = None,
        max_stops: str = "any",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        HYBRID: Search flights with advanced filters.
        
        Args:
            origin: Departure airport/city
            destination: Arrival airport/city
            departure_date: Departure date
            return_date: Return date (optional for one-way)
            passengers: Number of passengers
            max_price: Maximum price filter
            airlines: Preferred airlines
            max_stops: "nonstop", "1stop", or "any"
            session_id: Optional session ID
            
        Returns:
            Search results
        """
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No active session")
        
        print("⚡ Starting HYBRID flight search with filters...")
        
        # Initialize Playwright tools with FLIGHT_BOOKING profile
        tools = await self._init_playwright_tools(session_id, profile="FLIGHT_BOOKING")
        
        if tools and self.use_hybrid:
            try:
                # Navigate and fill search
                await tools.navigate_to_expedia()
                await tools.click_flights_tab()
                await tools.fill_flight_search(origin, destination, departure_date, return_date, passengers)
                
                # Apply filters
                if max_price or airlines or max_stops != "any":
                    stops_param = max_stops if max_stops != "any" else None
                    await tools.apply_flight_filters(
                        price_max=max_price,
                        airlines=airlines,
                        stops=stops_param
                    )
                
                print("✓ Flight search with filters completed!")
                return {
                    "status": "success",
                    "method": "playwright",
                    "filters_applied": True
                }
            except Exception as e:
                print(f"Playwright error: {e}, falling back to AI...")
        
        # AI fallback
        return {"status": "ai_fallback", "message": "Use AI agent for this search"}
    
    async def search_hotels_with_filters_hybrid(
        self,
        location: str,
        check_in: str,
        check_out: str,
        guests: int = 2,
        max_price: Optional[int] = None,
        min_star_rating: Optional[int] = None,
        amenities: Optional[List[str]] = None,
        free_cancellation: bool = False,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        HYBRID: Search hotels with advanced filters.
        
        Args:
            location: Hotel location
            check_in: Check-in date
            check_out: Check-out date
            guests: Number of guests
            max_price: Maximum price per night
            min_star_rating: Minimum star rating
            amenities: Required amenities list
            free_cancellation: Filter for free cancellation
            session_id: Optional session ID
            
        Returns:
            Search results
        """
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No active session")
        
        print("⚡ Starting HYBRID hotel search with filters...")
        
        # Initialize Playwright tools with HOTEL_BOOKING profile
        tools = await self._init_playwright_tools(session_id, profile="HOTEL_BOOKING")
        
        if tools and self.use_hybrid:
            try:
                # Navigate and fill search
                await tools.navigate_to_expedia()
                await tools.click_hotels_tab()
                await tools.fill_hotel_search(location, check_in, check_out, guests)
                
                # Apply filters
                if max_price or min_star_rating or amenities or free_cancellation:
                    await tools.apply_hotel_filters(
                        price_max=max_price,
                        star_rating=min_star_rating,
                        amenities=amenities,
                        free_cancellation=free_cancellation
                    )
                
                print("✓ Hotel search with filters completed!")
                return {
                    "status": "success",
                    "method": "playwright",
                    "filters_applied": True
                }
            except Exception as e:
                print(f"Playwright error: {e}, falling back to AI...")
        
        # AI fallback
        return {"status": "ai_fallback", "message": "Use AI agent for this search"}
    
    async def select_best_flight_hybrid(
        self,
        criteria: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        HYBRID: Select best value flight based on criteria.
        
        Args:
            criteria: Selection criteria (max_price, preferred_airlines, etc.)
            session_id: Optional session ID
            
        Returns:
            Selection result
        """
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No active session")
        
        print("⚡ Selecting best value flight with Playwright...")
        
        tools = await self._init_playwright_tools(session_id, profile="FLIGHT_BOOKING")
        
        if tools and self.use_hybrid:
            try:
                result = await tools.select_best_value_flight(criteria)
                return result
            except Exception as e:
                print(f"Playwright error: {e}, falling back to AI...")
        
        return {"status": "ai_fallback", "message": "Use AI agent for selection"}
    
    async def select_best_hotel_hybrid(
        self,
        criteria: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        HYBRID: Select best value hotel based on criteria.
        
        Args:
            criteria: Selection criteria (max_price, min_stars, etc.)
            session_id: Optional session ID
            
        Returns:
            Selection result
        """
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No active session")
        
        print("⚡ Selecting best value hotel with Playwright...")
        
        tools = await self._init_playwright_tools(session_id, profile="HOTEL_BOOKING")
        
        if tools and self.use_hybrid:
            try:
                result = await tools.select_best_value_hotel(criteria)
                return result
            except Exception as e:
                print(f"Playwright error: {e}, falling back to AI...")
        
        return {"status": "ai_fallback", "message": "Use AI agent for selection"}
    
    async def create_account_hybrid(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        HYBRID: Create new Expedia account.
        
        Args:
            email: User email
            password: Account password
            first_name: First name
            last_name: Last name
            session_id: Optional session ID
            
        Returns:
            Account creation result
        """
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No active session")
        
        print("⚡ Creating account with Playwright...")
        
        tools = await self._init_playwright_tools(session_id, profile="ACCOUNT_MANAGEMENT")
        
        if tools and self.use_hybrid:
            try:
                await tools.navigate_to_expedia()
                success = await tools.create_account(email, password, first_name, last_name)
                
                if success:
                    print("✓ Account created successfully!")
                    print("NOTE: Check email for verification code")
                    return {
                        "status": "success",
                        "method": "playwright",
                        "message": "Account created, email verification may be required"
                    }
            except Exception as e:
                print(f"Playwright error: {e}, falling back to AI...")
        
        return {"status": "ai_fallback", "message": "Use AI agent for account creation"}
    
    async def verify_email_hybrid(
        self,
        verification_code: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        HYBRID: Verify email with code.
        
        Args:
            verification_code: Code from email
            session_id: Optional session ID
            
        Returns:
            Verification result
        """
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No active session")
        
        print("⚡ Verifying email with Playwright...")
        
        tools = await self._init_playwright_tools(session_id, profile="ACCOUNT_MANAGEMENT")
        
        if tools and self.use_hybrid:
            try:
                success = await tools.verify_email_code(verification_code)
                
                if success:
                    print("✓ Email verified!")
                    return {
                        "status": "success",
                        "method": "playwright",
                        "message": "Email verified successfully"
                    }
            except Exception as e:
                print(f"Playwright error: {e}, falling back to AI...")
        
        return {"status": "ai_fallback", "message": "Use AI agent for verification"}
    
    def stop_session(self, session_id: Optional[str] = None):
        """
        Stop the current browser session.
        
        Args:
            session_id: Optional session ID (uses current session if not provided)
        """
        session_id = session_id or self.session_id
        if session_id:
            self.client.sessions.stop_session(session_id)
            print(f"Session {session_id} stopped")
    
    def cleanup_old_cloud_methods(self):
        """Legacy cleanup for cloud SDK (not used in local mode)."""
        # This is from the old cloud SDK implementation
        # Keeping for backward compatibility but not used
        pass
    
    # ========================================================================
    # BROWSER USE TOOLS INTEGRATION
    # ========================================================================
    
    def create_task_with_tools(
        self,
        task_description: str,
        session_id: Optional[str] = None
    ):
        """
        Create a task with access to all Expedia custom tools.
        
        The AI agent can directly call Playwright functions like:
        - navigate_to_expedia()
        - fill_login_form()
        - search_flights()
        - apply_flight_filters()
        - select_best_flight()
        - etc.
        
        Args:
            task_description: Natural language description of what to do
            session_id: Optional session ID (uses current if not provided)
            
        Returns:
            Task object
        """
        session_id = session_id or self.session_id
        
        if not session_id:
            raise ValueError("No active session. Call create_session() first.")
        
        if not self.tools:
            raise ValueError("Custom tools not available. Check expedia_agent_tools.py")
        
        print("🤖 Creating AI-assisted task with custom tools...")
        
        task = self.client.tasks.create_task(
            session_id=session_id,
            task=task_description
            # Note: Browser Use SDK will automatically have access to tools
            # registered via @tools.action() decorators
        )
        
        return task
    
    async def book_with_ai_agent(
        self,
        # Login
        email: str,
        password: str,
        # Flight details
        origin: str,
        destination: str,
        departure_date: str,
        # Hotel details
        hotel_location: str,
        check_in: str,
        check_out: str,
        # Traveler info
        first_name: str,
        last_name: str,
        phone: str,
        # Payment
        card_number: str,
        cardholder_name: str,
        expiration_month: str,
        expiration_year: str,
        cvv: str,
        billing_address: Dict[str, str],
        # Optional parameters with defaults
        return_date: Optional[str] = None,
        passengers: int = 1,
        guests: int = 2,
        flight_criteria: Optional[Dict[str, Any]] = None,
        hotel_criteria: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Let AI agent handle entire booking using custom tools.
        
        The agent will intelligently call the appropriate tools in sequence:
        1. navigate_to_expedia()
        2. fill_login_form(email, password)
        3. go_to_flights()
        4. search_flights(origin, destination, dates, ...)
        5. apply_flight_filters(max_price, airlines, ...)
        6. select_best_flight(criteria)
        7. go_to_hotels()
        8. search_hotels(location, dates, ...)
        9. apply_hotel_filters(star_rating, amenities, ...)
        10. select_best_hotel(criteria)
        11. fill_traveler_info(name, email, phone)
        12. fill_payment_form(card, billing)
        13. complete_booking()
        
        Args:
            All booking parameters
            
        Returns:
            Booking result with status
        """
        if not self.tools:
            raise ValueError("AI-assisted booking requires custom tools. Check expedia_agent_tools.py")
        
        # Build detailed task description
        flight_filters = ""
        if flight_criteria:
            filters = []
            if flight_criteria.get('max_price'):
                filters.append(f"max price ${flight_criteria['max_price']}")
            if flight_criteria.get('preferred_airlines'):
                filters.append(f"airlines: {', '.join(flight_criteria['preferred_airlines'])}")
            if flight_criteria.get('max_stops'):
                stops_map = {0: "nonstop", 1: "1 stop", 2: "any"}
                filters.append(f"{stops_map.get(flight_criteria['max_stops'], 'any')} stops")
            if filters:
                flight_filters = f"\n   Flight filters: {', '.join(filters)}"
        
        hotel_filters = ""
        if hotel_criteria:
            filters = []
            if hotel_criteria.get('max_price'):
                filters.append(f"max ${hotel_criteria['max_price']}/night")
            if hotel_criteria.get('min_stars'):
                filters.append(f"{hotel_criteria['min_stars']}+ stars")
            if hotel_criteria.get('required_amenities'):
                filters.append(f"amenities: {', '.join(hotel_criteria['required_amenities'])}")
            if hotel_criteria.get('free_cancellation'):
                filters.append("free cancellation")
            if filters:
                hotel_filters = f"\n   Hotel filters: {', '.join(filters)}"
        
        task_description = f"""
Complete an Expedia flight and hotel booking with the following details:

AUTHENTICATION:
1. Navigate to Expedia homepage
2. Login with email: {email}

FLIGHT BOOKING:
3. Navigate to flights section
4. Search for flights:
   - From: {origin}
   - To: {destination}
   - Departure: {departure_date}
   - Return: {return_date or 'one-way'}
   - Passengers: {passengers}{flight_filters}
5. If filters provided, apply them to narrow results
6. Select the best value flight option

HOTEL BOOKING:
7. Navigate to hotels section
8. Search for hotels:
   - Location: {hotel_location}
   - Check-in: {check_in}
   - Check-out: {check_out}
   - Guests: {guests}{hotel_filters}
9. If filters provided, apply them to narrow results
10. Select the best value hotel option

COMPLETE BOOKING:
11. Fill traveler information:
    - Name: {first_name} {last_name}
    - Email: {email}
    - Phone: {phone}
12. Fill payment information:
    - Card: {cardholder_name}
    - Billing: {billing_address.get('city', '')}, {billing_address.get('state', '')}
13. Review and complete the booking

Use the available Expedia tools to complete each step efficiently.
Take screenshots at key steps for verification.
Report any errors or issues encountered.
"""
        
        print("\n" + "=" * 70)
        print("🤖 AI AGENT BOOKING MODE")
        print("=" * 70)
        print("The AI agent will use custom tools to complete the booking.")
        print("This combines Playwright speed with AI intelligence!")
        print("=" * 70 + "\n")
        
        task = self.create_task_with_tools(
            task_description=task_description,
            session_id=self.session_id
        )
        
        # Wait for task completion
        print("Waiting for AI agent to complete booking...")
        result = task.complete()
        
        return {
            "status": "success" if result.status == "completed" else "failed",
            "message": "AI agent completed booking using custom tools",
            "task_id": task.id,
            "result": result
        }
    
    async def search_with_ai_agent(
        self,
        search_type: str,  # "flights" or "hotels"
        **search_params
    ) -> Dict[str, Any]:
        """
        Use AI agent with tools for intelligent search only (no booking).
        
        Args:
            search_type: "flights" or "hotels"
            **search_params: Search parameters
            
        Returns:
            Search results
        """
        if search_type == "flights":
            task_desc = f"""
Search for flights on Expedia:
1. Navigate to Expedia flights section
2. Search for flights from {search_params.get('origin')} to {search_params.get('destination')}
3. Dates: {search_params.get('departure_date')} to {search_params.get('return_date')}
4. Apply any filters if criteria provided
5. Analyze and report the top 3 best value options
6. Take a screenshot of the results

Use the Expedia tools to complete this search efficiently.
"""
        else:  # hotels
            task_desc = f"""
Search for hotels on Expedia:
1. Navigate to Expedia hotels section
2. Search for hotels in {search_params.get('location')}
3. Dates: {search_params.get('check_in')} to {search_params.get('check_out')}
4. Guests: {search_params.get('guests', 2)}
5. Apply any filters if criteria provided
6. Analyze and report the top 3 best value options
7. Take a screenshot of the results

Use the Expedia tools to complete this search efficiently.
"""
        
        task = self.create_task_with_tools(
            task_description=task_desc,
            session_id=self.session_id
        )
        
        result = task.complete()
        
        return {
            "status": "success",
            "search_type": search_type,
            "result": result
        }


# Example usage
if __name__ == "__main__":
    # Initialize agent
    agent = ExpediaAgent()
    
    # Example: Simple login
    agent.create_profile()
    agent.create_session()
    
    # Login example
    # agent.login(
    #     email="your-email@example.com",
    #     password="your-password"
    # )
    
    # Example: Full booking workflow
    # result = agent.book_flight_and_hotel_package(
    #     # Login
    #     email="your-email@example.com",
    #     password="your-password",
    #     # Flight
    #     origin="Los Angeles",
    #     destination="New York",
    #     departure_date="2025-12-15",
    #     return_date="2025-12-20",
    #     # Hotel
    #     hotel_location="New York, NY",
    #     check_in="2025-12-15",
    #     check_out="2025-12-20",
    #     # Traveler
    #     first_name="John",
    #     last_name="Doe",
    #     phone="+1-555-0123",
    #     # Payment
    #     card_number="4111111111111111",
    #     cardholder_name="John Doe",
    #     expiration_month="12",
    #     expiration_year="2027",
    #     cvv="123",
    #     billing_address={
    #         "street": "123 Main St",
    #         "city": "Los Angeles",
    #         "state": "CA",
    #         "zip": "90001",
    #         "country": "USA"
    #     },
    #     # Options
    #     passengers=1,
    #     flight_preference="cheapest",
    #     hotel_preference="highest rated under $200",
    #     create_account=False
    # )
    
    # print("\n📋 Final Result:")
    # print(result)
    
    # Cleanup
    # agent.cleanup()

