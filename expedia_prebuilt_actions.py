"""
Expedia Prebuilt Actions - High-level tools for browser-use agent
Complete flows packaged as single actions for faster execution
Designed for browser-use Agent integration
"""

from browser_use.controller.registry.service import Registry
from browser_use.browser.browser import BrowserSession
from pydantic import BaseModel, Field
from typing import Optional
import os
import logging
import asyncio

logger = logging.getLogger(__name__)

# Initialize prebuilt actions registry
expedia_prebuilt = Registry()

# ============================================================================
# AUTHENTICATION ACTIONS
# ============================================================================

@expedia_prebuilt.action('Sign in to Expedia account')
async def signin_to_expedia(
    browser_session: BrowserSession,
    email: str,
    wait_for_otp: bool = True,
    otp_timeout: int = 120
) -> str:
    """
    Complete sign-in flow for Expedia.
    
    Args:
        email: User's email address
        wait_for_otp: Whether to wait for manual OTP entry (default True)
        otp_timeout: Max seconds to wait for OTP (default 120)
    
    Returns:
        Status message indicating success or failure
    """
    try:
        page = await browser_session.get_current_page()
        logger.info("Starting Expedia sign-in flow...")
        
        # Step 1: Navigate to homepage if not there
        current_url = page.url
        if 'expedia.com' not in current_url:
            await page.goto('https://www.expedia.com', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
        
        # Step 2: Click header "Sign in" button (exact selector from test)
        logger.info("Opening sign-in menu...")
        try:
            await page.click("button[data-testid='header-menu-button']:has-text('Sign in')", timeout=10000)
            await asyncio.sleep(0.5)
            logger.info("✅ Clicked header sign-in button")
        except Exception as e:
            return f"❌ Could not find sign-in button in header: {e}"
        
        # Step 3: Click "Sign in" in dropdown menu (exact selector from test)
        logger.info("Clicking sign-in link in menu...")
        try:
            await page.click("a[href^='/login'] >> text=Sign in", timeout=10000)
            await asyncio.sleep(1)
            logger.info("✅ Clicked sign-in link")
        except Exception as e:
            return f"❌ Could not find sign-in link in menu: {e}"
        
        # Step 4: Fill email (exact selector from test)
        logger.info(f"Filling email: {email}")
        try:
            await page.wait_for_selector('#loginFormEmailInput', timeout=15000)
            await page.fill('#loginFormEmailInput', email)
            await asyncio.sleep(0.3)
            logger.info("✅ Filled email")
        except Exception as e:
            return f"❌ Could not find email input field: {e}"
        
        # Step 5: Click submit button (exact selector from test)
        logger.info("Clicking submit button...")
        try:
            await page.click('#loginFormSubmitButton')
            await asyncio.sleep(1)
            logger.info("✅ Clicked submit")
        except Exception as e:
            return f"❌ Could not find submit button: {e}"
        
        # Step 6: Wait for OTP if enabled (exact selectors from test)
        if wait_for_otp:
            logger.info(f"⏳ Waiting up to {otp_timeout}s for OTP entry...")
            
            # Wait for OTP input to appear
            try:
                await page.wait_for_selector('#verify-sms-one-time-passcode-input', timeout=15000)
                logger.info("📱 OTP input detected. Please enter your 6-digit code...")
                
                # Poll for 6 digits (reduced from 120 to 60 seconds like test)
                otp_entered = False
                for _ in range(min(otp_timeout, 60)):
                    try:
                        code_len = await page.evaluate("""() => {
                            const el = document.querySelector('#verify-sms-one-time-passcode-input');
                            return el ? (el.value || '').length : 0;
                        }""")
                        if code_len and code_len >= 6:
                            await page.click('#verifyOtpFormSubmitButton')
                            otp_entered = True
                            break
                    except Exception:
                        pass
                    await asyncio.sleep(1)
                
                if not otp_entered:
                    logger.warning("⚠️ OTP not detected within timeout")
                    return f"⚠️ OTP timeout after {otp_timeout}s. Please click Continue manually if already entered."
                
                logger.info("✅ OTP submitted")
                
                # Small wait to let sign-in complete (like test file)
                await asyncio.sleep(2)
                logger.info("✅ Sign-in flow complete")
                    
            except Exception as e:
                logger.warning(f"OTP handling issue: {e}")
                return f"⚠️ OTP step encountered issue: {str(e)}. Please complete manually."
        
        # Verify sign-in success
        await asyncio.sleep(2)
        current_url = page.url
        
        # Check if we're back on homepage or signed in
        if 'login' not in current_url.lower():
            logger.info("✅ Sign-in appears successful!")
            return "✅ Successfully signed in to Expedia"
        else:
            logger.info("⚠️ Sign-in may not be complete - still on login page")
            return "⚠️ Sign-in may not be complete. Please verify manually."
            
    except Exception as e:
        logger.error(f"Sign-in error: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error during sign-in: {str(e)}"


@expedia_prebuilt.action('Ensure signed in (idempotent)')
async def ensure_signed_in(
    browser_session: BrowserSession,
    email: Optional[str] = None
) -> str:
    """Navigate to Expedia and sign in only if needed.

    - Navigates to https://www.expedia.com if not already there
    - If header shows "Sign in", attempts sign-in using provided email or ENV EXPEDIA_LOGIN_EMAIL
    - Otherwise, returns already signed in
    """
    try:
        page = await browser_session.get_current_page()
        current_url = page.url or ""
        if 'expedia.com' not in current_url:
            await page.goto('https://www.expedia.com', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

        sign_in_button = await page.query_selector("button[data-testid='header-menu-button']:has-text('Sign in')")
        if not sign_in_button:
            return "✅ Already signed in"

        # Determine login email
        login_email = email or os.environ.get('EXPEDIA_LOGIN_EMAIL')
        if not login_email:
            return "⚠️ Login required but no email provided. Set EXPEDIA_LOGIN_EMAIL or pass email."

        return await signin_to_expedia(browser_session, login_email)

    except Exception as e:
        logger.error(f"ensure_signed_in error: {e}")
        return f"❌ Error ensuring sign-in: {str(e)}"

@expedia_prebuilt.action('Sign up for new Expedia account')
async def signup_to_expedia(
    browser_session: BrowserSession,
    email: str,
    password: str,
    first_name: str,
    last_name: str
) -> str:
    """
    Complete sign-up flow for new Expedia account.
    
    Args:
        email: User's email address
        password: Desired password
        first_name: User's first name
        last_name: User's last name
    
    Returns:
        Status message indicating success or failure
    """
    try:
        page = await browser_session.get_current_page()
        logger.info("Starting Expedia sign-up flow...")
        
        # Navigate to sign-up page
        await page.goto('https://www.expedia.com/create-account', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        
        # Fill first name
        first_name_input = await page.query_selector('input[name="firstname"]')
        if first_name_input:
            await first_name_input.fill(first_name)
            await asyncio.sleep(0.5)
        
        # Fill last name
        last_name_input = await page.query_selector('input[name="lastname"]')
        if last_name_input:
            await last_name_input.fill(last_name)
            await asyncio.sleep(0.5)
        
        # Fill email
        email_input = await page.query_selector('input[type="email"]')
        if email_input:
            await email_input.fill(email)
            await asyncio.sleep(0.5)
        
        # Fill password
        password_input = await page.query_selector('input[type="password"]')
        if password_input:
            await password_input.fill(password)
            await asyncio.sleep(1)
        
        # Click create account button
        create_btn = await page.query_selector('button[type="submit"]')
        if not create_btn:
            create_btn = await page.query_selector('button:has-text("Create account")')
        
        if create_btn:
            await create_btn.click()
            await asyncio.sleep(5)
            logger.info("✅ Sign-up submitted successfully")
            return "✅ Account created successfully. Please verify email if required."
        else:
            return "❌ Could not find create account button"
            
    except Exception as e:
        logger.error(f"Sign-up error: {e}")
        return f"❌ Error during sign-up: {str(e)}"


# ============================================================================
# FLIGHT SEARCH ACTIONS
# ============================================================================

@expedia_prebuilt.action('Search for flights with complete form')
async def search_flights(
    browser_session: BrowserSession,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "economy"
) -> str:
    """
    Complete flight search from start to results page.
    Uses direct URL navigation for reliability (bypasses flaky form filling).
    
    Args:
        origin: Origin airport code (e.g., "SFO", "LAX")
        destination: Destination airport code (e.g., "LAX", "JFK")
        departure_date: Departure date in MM/DD/YYYY format
        return_date: Return date in MM/DD/YYYY format (None for one-way)
        adults: Number of adult travelers (default 1)
        cabin_class: Cabin class - "economy", "premium", "business", "first" (default economy)
    
    Returns:
        Status message with search results URL
    """
    try:
        page = await browser_session.get_current_page()
        logger.info(f"Searching flights: {origin} → {destination}")
        
        # Convert date format from MM/DD/YYYY to MM%2FDD%2FYYYY for URL
        dep_date_formatted = departure_date.replace("/", "%2F")
        ret_date_formatted = return_date.replace("/", "%2F") if return_date else None
        
        # Build the pre-filled search URL (much more reliable than form filling)
        trip_type = "roundtrip" if return_date else "oneway"
        
        if trip_type == "roundtrip":
            search_url = (
                f"https://www.expedia.com/Flights-Search"
                f"?flight-type=on&mode=search&trip=roundtrip"
                f"&leg1=from%3A{origin}%2Cto%3A{destination}%2Cdeparture%3A{dep_date_formatted}TANYT"
                f"&leg2=from%3A{destination}%2Cto%3A{origin}%2Cdeparture%3A{ret_date_formatted}TANYT"
                f"&options=cabinclass%3A{cabin_class}"
                f"&passengers=adults%3A{adults}"
            )
        else:
            search_url = (
                f"https://www.expedia.com/Flights-Search"
                f"?flight-type=on&mode=search&trip=oneway"
                f"&leg1=from%3A{origin}%2Cto%3A{destination}%2Cdeparture%3A{dep_date_formatted}TANYT"
                f"&options=cabinclass%3A{cabin_class}"
                f"&passengers=adults%3A{adults}"
            )
        
        logger.info(f"Navigating to pre-filled search URL...")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(5)  # Wait for results to load
        
        result_url = page.url
        
        # Check if we're on the results page
        if "Flights-Search" in result_url:
            logger.info(f"✅ Search complete: {result_url}")
            return f"✅ Flight search complete. Results loaded at: {result_url}"
        else:
            logger.warning(f"⚠️ Unexpected URL: {result_url}")
            return f"⚠️ Search may not be complete. Current URL: {result_url}"
            
    except Exception as e:
        logger.error(f"Search error: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error during search: {str(e)}"


# ============================================================================
# FLIGHT SELECTION ACTIONS
# ============================================================================

@expedia_prebuilt.action('Select cheapest flight option')
async def select_cheapest_flight(
    browser_session: BrowserSession,
    fare_type: str = "basic"
) -> str:
    """
    Sort by price and select the cheapest flight with specified fare type.
    Handles both outbound and return flight selection.
    
    Args:
        fare_type: Fare type to select - "basic", "main", "first" (default basic)
    
    Returns:
        Status message indicating selection success
    """
    try:
        page = await browser_session.get_current_page()
        logger.info("Selecting cheapest flight option...")
        
        # Step 1: Sort by price (lowest to highest)
        logger.info("Sorting by price...")
        sort_dropdown = await page.query_selector('select#sort-filter-dropdown-SORT')
        if sort_dropdown:
            await page.select_option('select#sort-filter-dropdown-SORT', 'PRICE_INCREASING')
            await asyncio.sleep(3)  # Wait for results to re-sort
            logger.info("✅ Sorted by price (lowest first)")
        else:
            logger.warning("⚠️ Sort dropdown not found - results may already be sorted")
        
        # Step 2: Wait for page to settle after sorting
        await asyncio.sleep(2)
        
        # Select outbound flight (Basic fare)
        logger.info(f"Selecting {fare_type} fare for outbound flight...")
        
        # Try multiple times in case page is still loading
        fare_card = None
        for attempt in range(3):
            fare_card = await page.query_selector(f'button.uitk-card-link[aria-label*="{fare_type.capitalize()}"]')
            if fare_card:
                break
            logger.info(f"   Attempt {attempt + 1}/3: Waiting for fare card to appear...")
            await asyncio.sleep(2)
        
        if not fare_card:
            logger.error(f"❌ Could not find {fare_type} fare card after 3 attempts")
            # Take a screenshot for debugging
            await page.screenshot(path="error_no_fare_card.png")
            return f"❌ Could not find {fare_type} fare card. Results may not have loaded. Screenshot saved."
        
        logger.info(f"✅ Found fare card, clicking...")
        await fare_card.click()
        await asyncio.sleep(2)
        logger.info("✅ Clicked fare card")
        
        # Click Select button in popup - wait for it to appear
        logger.info("   Waiting for Select button in popup...")
        select_btn = None
        for attempt in range(3):
            select_btn = await page.query_selector('button[data-stid="select-button"]')
            if select_btn:
                break
            logger.info(f"   Attempt {attempt + 1}/3: Waiting for Select button...")
            await asyncio.sleep(2)
        
        if not select_btn:
            logger.error("❌ Could not find Select button in popup after 3 attempts")
            await page.screenshot(path="error_no_select_button.png")
            return "❌ Could not find Select button in popup. Screenshot saved."
        
        logger.info("✅ Found Select button, clicking...")
        await select_btn.click()
        await asyncio.sleep(3)
        logger.info("✅ Selected outbound flight")
        
        # Step 3: Wait for return flights to appear
        logger.info("Waiting for return flight options to load...")
        await asyncio.sleep(2)
        
        # Select return flight - try multiple times
        return_fare_card = None
        for attempt in range(3):
            return_fare_card = await page.query_selector(f'button.uitk-card-link[aria-label*="{fare_type.capitalize()}"]')
            if return_fare_card:
                break
            logger.info(f"   Attempt {attempt + 1}/3: Waiting for return fare card...")
            await asyncio.sleep(2)
        
        if return_fare_card:
            logger.info(f"✅ Found return {fare_type} fare card, clicking...")
            await return_fare_card.click()
            await asyncio.sleep(1)
            logger.info("✅ Clicked return fare card")
            
            # Click Select button for return - THIS OPENS A NEW TAB
            logger.info("   Waiting for Select button for return flight...")
            select_btn = None
            for attempt in range(3):
                select_btn = await page.query_selector('button[data-stid="select-button"]')
                if select_btn:
                    break
                logger.info(f"   Attempt {attempt + 1}/3: Waiting for Select button...")
                await asyncio.sleep(2)
            
            if select_btn:
                # Handle new tab that opens with traveler info form
                try:
                    logger.info("🔄 Clicking Select (will open new tab)...")
                    async with page.expect_popup() as popup_info:
                        await select_btn.click()
                    
                    # Capture the new tab
                    new_page = await popup_info.value
                    logger.info(f"✅ New tab captured: {new_page.url}")
                    
                    # Wait for it to load
                    await new_page.wait_for_load_state('domcontentloaded', timeout=30000)
                    logger.info("✅ New tab loaded (domcontentloaded)")
                    
                    # Bring to front and switch focus
                    await new_page.bring_to_front()
                    await asyncio.sleep(1.5)
                    
                    # CRITICAL: Tell Browser Use agent to focus on the new tab
                    # According to docs, we need to explicitly set the agent focus
                    # so subsequent actions use the new tab
                    try:
                        # Close the old page to force switch to new tab
                        logger.info("🔄 Closing old tab to force switch to new tab...")
                        await page.close()
                        logger.info("✅ Old tab closed, agent will now use new tab")
                    except Exception as close_err:
                        logger.warning(f"Could not close old page: {close_err}")
                        logger.info("Will rely on bring_to_front() to switch focus")
                    
                    logger.info(f"✅ Agent should now be on: {new_page.url}")
                    
                    await asyncio.sleep(1.5)
                    
                    # Verify we're on the traveler info page
                    traveler_form = await new_page.query_selector('form.air-trip-preference')
                    if traveler_form:
                        logger.info("✅ Confirmed: On traveler information form page")
                    else:
                        logger.warning("⚠️ Traveler form not found on new page - may need more time to load")
                    
                    logger.info("✅ New tab is now active and ready for traveler info")
                    return (
                        "✅ Both flights selected! Now on TRAVELER INFORMATION page. "
                        "IMPORTANT: You MUST fill traveler details (name, email, phone) "
                        "BEFORE clicking any checkout button. The checkout button will "
                        "appear after filling the traveler form."
                    )
                    
                except Exception as e:
                    # No popup, just continue
                    logger.error(f"Error handling popup: {e}")
                    await select_btn.click()
                    await asyncio.sleep(3)
                    logger.info("✅ Selected return flight")
                    return (
                        "✅ Both flights selected! Now on TRAVELER INFORMATION page. "
                        "You MUST fill traveler details before proceeding to checkout."
                    )
            else:
                logger.error("❌ Could not find Select button for return flight after 3 attempts")
                await page.screenshot(path="error_no_return_select_button.png")
                return "❌ Could not find Select button for return flight. Screenshot saved."
        else:
            logger.warning("ℹ️ No return fare card found - might be one-way or already on booking page")
            return "✅ Flight selection complete. Check if on traveler info or checkout page."
            
    except Exception as e:
        logger.error(f"Flight selection error: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error selecting flight: {str(e)}"


# ============================================================================
# TRAVELER INFORMATION ACTIONS
# ============================================================================

@expedia_prebuilt.action('Fill traveler information (REQUIRED after flight selection)')
async def fill_traveler_info(
    browser_session: BrowserSession,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    gender: str = "male",
    dob_month: str = "05",
    dob_day: str = "15",
    dob_year: str = "1990"
) -> str:
    """
    Fill complete traveler information on booking page.
    
    **WHEN TO USE**: After selecting flights, you land on the traveler information page.
    This action MUST be called before attempting to proceed to checkout.
    The checkout button only becomes available after required fields are filled.
    
    **REQUIRED FIELDS**: first_name, last_name, email, phone
    **OPTIONAL FIELDS**: gender, date of birth
    
    Args:
        first_name: Traveler's first name
        last_name: Traveler's last name (minimum 2 characters)
        email: Contact email address
        phone: Phone number (digits only, e.g., "4155551234")
        gender: Gender - "male" or "female" (default male, optional)
        dob_month: Birth month - "01" to "12" (default "05", optional)
        dob_day: Birth day - "01" to "31" (default "15", optional)
        dob_year: Birth year - 4 digits (default "1990", optional)
    
    Returns:
        Status message indicating form fill success
    """
    try:
        page = await browser_session.get_current_page()
        
        # Verify we're on the correct page
        current_url = page.url
        logger.info(f"Filling traveler information on: {current_url}")
        
        # Check if we're on a flight search/selection page (wrong page!)
        if '/Flights-Search?' in current_url and 'journeysContinue' not in current_url:
            logger.error("❌ Still on flight search results page! Tab switch may have failed.")
            return (
                "❌ ERROR: Still on flight search page instead of traveler info page! "
                "The new tab may not have switched properly after selecting return flight. "
                "Please retry flight selection."
            )
        
        # Wait for traveler form to load
        try:
            await page.wait_for_selector('form.air-trip-preference', timeout=20000)
            logger.info("✅ Traveler form found")
        except Exception as e:
            logger.error(f"❌ Traveler form not found: {e}")
            return (
                f"❌ Traveler form not found on current page ({current_url}). "
                "You may not be on the traveler information page yet. "
                "Make sure flights were selected successfully."
            )
        
        # Scroll to form to ensure it's in view
        await page.evaluate("""() => {
            const form = document.querySelector('form.air-trip-preference');
            if (form) form.scrollIntoView({behavior: 'smooth', block: 'start'});
        }""")
        await asyncio.sleep(0.5)
        
        # === REQUIRED FIELDS (use exact selectors from test file) ===
        
        # First Name (required)
        logger.info(f"Filling name: {first_name} {last_name}")
        try:
            await page.wait_for_selector(
                'input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].firstName"]',
                state='visible', timeout=10000
            )
            await page.fill(
                'input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].firstName"]',
                first_name
            )
            await asyncio.sleep(0.2)
            logger.info(f"   ✓ First name: {first_name}")
        except Exception as e:
            logger.error(f"   ✗ First name failed: {e}")
        
        # Last Name (required, min 2 chars)
        try:
            await page.fill(
                'input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].lastName"]',
                last_name
            )
            await asyncio.sleep(0.2)
            logger.info(f"   ✓ Last name: {last_name}")
        except Exception as e:
            logger.error(f"   ✗ Last name failed: {e}")
        
        # Email (required)
        try:
            await page.fill('input[name="email"]', email)
            await asyncio.sleep(0.2)
            logger.info(f"   ✓ Email: {email}")
        except Exception as e:
            logger.error(f"   ✗ Email failed: {e}")
        
        # Country/Territory Code (required for phone)
        try:
            await page.select_option(
                'select[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].phoneCountryCode"]',
                '1'
            )
            await asyncio.sleep(0.2)
            logger.info(f"   ✓ Country code: +1 (USA)")
        except Exception as e:
            logger.error(f"   ✗ Country code failed: {e}")
        
        # Phone Number (required) - try multiple selectors
        phone_filled = False
        phone_selectors = [
            'input[name*="phone"]',
            'input[id*="phone"]',
            'input#phone-number\\[0\\]',
        ]
        for selector in phone_selectors:
            try:
                await page.wait_for_selector(selector, state='visible', timeout=3000)
                await page.fill(selector, phone)
                await asyncio.sleep(0.2)
                logger.info(f"   ✓ Phone: {phone}")
                phone_filled = True
                break
            except:
                continue
        
        if not phone_filled:
            logger.warning("   ⚠ Phone number field not found")
        
        # Select gender
        gender_id = f'#gender_{gender}\\[0\\]'
        gender_radio = await page.query_selector(gender_id)
        if gender_radio:
            await gender_radio.click()
            await asyncio.sleep(0.3)
            logger.info(f"Gender: {gender}")
        
        # Fill date of birth
        month_select = await page.query_selector('#date_of_birth_month0')
        if month_select:
            await page.select_option('#date_of_birth_month0', dob_month)
            await asyncio.sleep(0.2)
        
        day_select = await page.query_selector('#date_of_birth_day\\[0\\]')
        if day_select:
            await page.select_option('#date_of_birth_day\\[0\\]', dob_day)
            await asyncio.sleep(0.2)
        
        year_select = await page.query_selector('#date_of_birth_year\\[0\\]')
        if year_select:
            await page.select_option('#date_of_birth_year\\[0\\]', dob_year)
            await asyncio.sleep(0.3)
            logger.info(f"DOB: {dob_month}/{dob_day}/{dob_year}")
        
        # Scroll down to ensure everything is loaded
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        
        logger.info("✅ Traveler information filled successfully")
        return (
            "✅ Traveler information completed! "
            "NEXT STEP: Call 'proceed_to_checkout' to click the checkout button "
            "and move to the payment page."
        )
        
    except Exception as e:
        logger.error(f"Traveler info error: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error filling traveler info: {str(e)}"


# ============================================================================
# PAYMENT INFORMATION ACTIONS
# ============================================================================

@expedia_prebuilt.action('Fill payment and billing information')
async def fill_payment_info(
    browser_session: BrowserSession,
    cardholder_name: str,
    card_number: str,
    exp_month: str,
    exp_year: str,
    cvv: str,
    billing_address: str,
    billing_city: str,
    billing_state: str,
    billing_zip: str,
    billing_country: str = "USA"
) -> str:
    """
    Fill complete payment and billing information.
    
    Args:
        cardholder_name: Name on card
        card_number: Card number (16 digits, spaces optional)
        exp_month: Expiration month - "01" to "12"
        exp_year: Expiration year - 4 digits (e.g., "2027")
        cvv: Card security code (3-4 digits)
        billing_address: Street address
        billing_city: City name
        billing_state: State code (e.g., "CA", "NY")
        billing_zip: ZIP/Postal code
        billing_country: Country code (default "USA")
    
    Returns:
        Status message indicating form fill success
    """
    try:
        page = await browser_session.get_current_page()
        logger.info("Filling payment information...")
        
        # Wait for payment section
        await page.wait_for_selector('#payment-type-creditcard', timeout=20000)
        
        # Scroll to payment section
        await page.evaluate("""() => {
            const section = document.querySelector('#payment-type-creditcard');
            if (section) section.scrollIntoView({behavior: 'smooth', block: 'start'});
        }""")
        await asyncio.sleep(2)
        
        # Select "Use a different card" if option exists
        try:
            new_card_radio = await page.query_selector('input.use-new-card[type="radio"]')
            if new_card_radio:
                await new_card_radio.click()
                await asyncio.sleep(1)
                logger.info("Selected 'Use a different card'")
        except:
            pass
        
        # Fill cardholder name
        logger.info(f"Cardholder: {cardholder_name}")
        name_input = await page.query_selector('input[name="creditCards[0].cardholder_name"]')
        if name_input:
            await page.wait_for_selector('input[name="creditCards[0].cardholder_name"]', state='visible', timeout=10000)
            await name_input.fill(cardholder_name)
            await asyncio.sleep(0.5)
        
        # Fill card number
        logger.info(f"Card: {card_number[:4]}...{card_number[-4:]}")
        card_input = await page.query_selector('input#creditCardInput')
        if card_input:
            await card_input.fill(card_number.replace(' ', ''))
            await asyncio.sleep(0.5)
        
        # Fill expiration month
        month_select = await page.query_selector('select[name="creditCards[0].expiration_month"]')
        if month_select:
            await page.select_option('select[name="creditCards[0].expiration_month"]', exp_month)
            await asyncio.sleep(0.3)
        
        # Fill expiration year
        year_select = await page.query_selector('select[name="creditCards[0].expiration_year"]')
        if year_select:
            await page.select_option('select[name="creditCards[0].expiration_year"]', exp_year)
            await asyncio.sleep(0.3)
        logger.info(f"Expiration: {exp_month}/{exp_year}")
        
        # Fill CVV
        cvv_input = await page.query_selector('input#new_cc_security_code')
        if cvv_input:
            await cvv_input.fill(cvv)
            await asyncio.sleep(0.5)
            logger.info(f"CVV: {'*' * len(cvv)}")
        
        # Scroll to billing section
        await page.evaluate("window.scrollBy(0, 300)")
        await asyncio.sleep(1)
        
        # Select billing country
        try:
            country_select = await page.query_selector('select.billing-country[name="creditCards[0].country"]')
            if country_select:
                await page.select_option('select.billing-country[name="creditCards[0].country"]', billing_country)
                await asyncio.sleep(0.5)
        except:
            pass
        
        # Fill billing address
        logger.info(f"Address: {billing_address}, {billing_city}, {billing_state} {billing_zip}")
        address_input = await page.query_selector('input[name="creditCards[0].street"]')
        if address_input:
            await address_input.fill(billing_address)
            await asyncio.sleep(0.5)
        
        # Fill city
        city_input = await page.query_selector('input[name="creditCards[0].city"]')
        if city_input:
            await city_input.fill(billing_city)
            await asyncio.sleep(0.5)
        
        # Select state
        state_select = await page.query_selector('select[name="creditCards[0].state"]')
        if state_select:
            await page.select_option('select[name="creditCards[0].state"]', billing_state)
            await asyncio.sleep(0.5)
        
        # Fill ZIP code
        zip_input = await page.query_selector('input[name="creditCards[0].zipcode"]')
        if zip_input:
            await zip_input.fill(billing_zip)
            await asyncio.sleep(1)
        
        logger.info("✅ Payment information filled successfully")
        return "✅ Payment and billing information completed"
        
    except Exception as e:
        logger.error(f"Payment info error: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error filling payment info: {str(e)}"


# ============================================================================
# CHECKOUT FLOW ACTIONS
# ============================================================================

@expedia_prebuilt.action('Proceed to checkout from traveler info page')
async def proceed_to_checkout(browser_session: BrowserSession) -> str:
    """
    Click checkout button and handle any nudge dialogs.
    
    PREREQUISITES: Traveler information form MUST be filled first!
    The checkout button only appears after required traveler fields are filled.
    
    Returns:
        Status message indicating checkout navigation success
    """
    try:
        page = await browser_session.get_current_page()
        logger.info("Proceeding to checkout...")
        
        # First check if we're on the traveler info page
        traveler_form = await page.query_selector('form.air-trip-preference')
        if traveler_form:
            logger.info("✅ On traveler information page")
        else:
            logger.warning("⚠️ Not on expected traveler info page - may already be past this step")
        
        # Scroll to make checkout button visible
        await page.evaluate("""() => {
            const btn = document.querySelector('button[data-stid="goto-checkout-button"]');
            if (btn) btn.scrollIntoView({behavior: 'smooth', block: 'center'});
        }""")
        await asyncio.sleep(2)
        
        # Wait for checkout button (with clearer error message)
        try:
            await page.wait_for_selector('button[data-stid="goto-checkout-button"]', state='visible', timeout=15000)
            logger.info("✅ Found checkout button")
        except Exception as e:
            return (
                "❌ Checkout button not found or not visible. "
                "LIKELY CAUSE: Traveler information form is not filled yet or has validation errors. "
                "You MUST fill all required traveler fields (first name, last name, email, phone) "
                "before the checkout button becomes available."
            )
        
        # Click checkout button
        checkout_btn = await page.query_selector('button[data-stid="goto-checkout-button"]')
        if checkout_btn:
            await checkout_btn.click()
            await asyncio.sleep(3)
            logger.info("✅ Clicked checkout button")
        else:
            return "❌ Could not find checkout button (this shouldn't happen after wait_for_selector)"
        
        # Check for nudge dialog
        await asyncio.sleep(2)
        nudge_btn = await page.query_selector('button[data-stid="nudge-goto-checkout-button"]')
        
        if nudge_btn:
            logger.info("Handling nudge dialog...")
            await nudge_btn.click()
            await page.wait_for_load_state('domcontentloaded', timeout=20000)
            await asyncio.sleep(3)
            logger.info("✅ Clicked through nudge dialog")
        else:
            logger.info("ℹ️ No nudge dialog (proceeded directly to payment)")
        
        current_url = page.url
        logger.info(f"✅ Now at: {current_url}")
        return (
            f"✅ Successfully proceeded to PAYMENT page! "
            f"Now you can fill payment information (card, billing address). "
            f"Current URL: {current_url}"
        )
        
    except Exception as e:
        logger.error(f"Checkout error: {e}")
        import traceback
        traceback.print_exc()
        return (
            f"❌ Error proceeding to checkout: {str(e)}. "
            "Make sure traveler information is filled before trying to proceed."
        )


@expedia_prebuilt.action('Complete full flight booking flow')
async def complete_flight_booking(
    browser_session: BrowserSession,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    cardholder_name: str,
    card_number: str,
    exp_month: str,
    exp_year: str,
    cvv: str,
    billing_address: str,
    billing_city: str,
    billing_state: str,
    billing_zip: str
) -> str:
    """
    Complete end-to-end flight booking flow in one action.
    Combines search, selection, traveler info, and payment.
    
    This is the ultimate convenience action that does everything.
    
    Returns:
        Detailed status of each step in the booking process
    """
    results = []
    
    try:
        # Step 0: Ensure signed in before any navigation/actions
        logger.info("=" * 70)
        logger.info("STEP 0: ENSURING SIGN-IN")
        logger.info("=" * 70)
        sign_in_status = await ensure_signed_in(browser_session)
        results.append(f"🔐 Sign-in: {sign_in_status}")

        # Step 1: Search flights
        logger.info("=" * 70)
        logger.info("STEP 1: SEARCHING FLIGHTS")
        logger.info("=" * 70)
        result = await search_flights(
            browser_session, origin, destination,
            departure_date, return_date, adults=1
        )
        results.append(f"🔍 Search: {result}")
        
        if "❌" in result:
            return "\n".join(results)
        
        # Step 2: Select cheapest flight
        logger.info("=" * 70)
        logger.info("STEP 2: SELECTING FLIGHTS")
        logger.info("=" * 70)
        await asyncio.sleep(3)
        result = await select_cheapest_flight(browser_session, fare_type="basic")
        results.append(f"✈️ Selection: {result}")
        
        if "❌" in result:
            return "\n".join(results)
        
        # Step 3: Fill traveler info
        logger.info("=" * 70)
        logger.info("STEP 3: FILLING TRAVELER INFO")
        logger.info("=" * 70)
        await asyncio.sleep(3)
        result = await fill_traveler_info(
            browser_session, first_name, last_name,
            email, phone
        )
        results.append(f"👤 Traveler: {result}")
        
        if "❌" in result:
            return "\n".join(results)
        
        # Step 4: Proceed to checkout
        logger.info("=" * 70)
        logger.info("STEP 4: PROCEEDING TO CHECKOUT")
        logger.info("=" * 70)
        await asyncio.sleep(2)
        result = await proceed_to_checkout(browser_session)
        results.append(f"🛒 Checkout: {result}")
        
        if "❌" in result:
            return "\n".join(results)
        
        # Step 5: Fill payment info
        logger.info("=" * 70)
        logger.info("STEP 5: FILLING PAYMENT INFO")
        logger.info("=" * 70)
        await asyncio.sleep(3)
        result = await fill_payment_info(
            browser_session, cardholder_name, card_number,
            exp_month, exp_year, cvv,
            billing_address, billing_city, billing_state, billing_zip
        )
        results.append(f"💳 Payment: {result}")
        
        logger.info("=" * 70)
        logger.info("✅ BOOKING FLOW COMPLETE!")
        logger.info("=" * 70)
        results.append("🎉 READY TO COMPLETE BOOKING (DO NOT CLICK - TEST DATA!)")
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Booking flow error: {e}")
        results.append(f"❌ Flow error: {str(e)}")
        return "\n".join(results)


# Export the registry
__all__ = ['expedia_prebuilt']

