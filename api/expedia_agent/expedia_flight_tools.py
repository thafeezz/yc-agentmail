"""
Expedia Playwright Tools - Direct Page Manipulation
Tools for all 5 pages of the Expedia booking flow using real selectors.
Each tool executes instant Playwright commands for 10-100x speed improvement.
"""

from browser_use.controller.registry.service import Registry
from browser_use.browser.browser import BrowserSession
from pydantic import BaseModel, Field
from typing import Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

# Initialize tools registry
flight_tools = Registry()

# ============================================================================
# PAGE 1: SIGN IN & NAVIGATION
# ============================================================================

@flight_tools.action('Sign in to Expedia account')
async def sign_in_expedia(
    browser_session: BrowserSession,
    email: str
) -> str:
    """
    Sign in to Expedia account - automatically fetches OTP from AgentMail inbox.
    Opens sign-in flow, waits 10 seconds, then retrieves emails with OTP code.
    
    Args:
        email: Expedia account email (AgentMail inbox address, used for API calls)
    """
    try:
        page = await browser_session.get_current_page()
        
        # Go to homepage for sign in
        logger.info("🌐 Navigating to Expedia homepage...")
        await page.goto("https://www.expedia.com/", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        
        # Open header Sign in menu (with longer timeout for CAPTCHA pages)
        logger.info("👆 Clicking Sign in button...")
        try:
            await page.click("button[data-testid='header-menu-button']:has-text('Sign in')", timeout=20000)
        except Exception as e:
            # Might be on CAPTCHA page, try waiting longer
            logger.warning(f"Sign in button not found, waiting 5s: {e}")
            await asyncio.sleep(5)
            await page.click("button[data-testid='header-menu-button']:has-text('Sign in')", timeout=20000)
        
        await asyncio.sleep(0.5)
        
        # Click Sign in in the dropdown
        logger.info("📝 Opening sign-in form...")
        await page.click("a[href^='/login'] >> text=Sign in", timeout=10000)
        await asyncio.sleep(1)
        
        # Fill email and continue
        logger.info(f"📧 Entering email: {email}")
        await page.wait_for_selector('#loginFormEmailInput', timeout=15000)
        await page.fill('#loginFormEmailInput', email)
        await asyncio.sleep(0.3)
        await page.click('#loginFormSubmitButton')
        await asyncio.sleep(1)
        
        # Wait for OTP screen
        logger.info("⏳ Waiting for OTP entry page...")
        await page.wait_for_selector('#verify-sms-one-time-passcode-input', timeout=30000)
        logger.info("✅ OTP page loaded successfully!")
        
        # Wait 10 seconds for email to arrive
        logger.info("📬 Waiting 10 seconds for email delivery...")
        await asyncio.sleep(10)
        
        # Automatically fetch inbox messages with OTP and enter it
        logger.info("📬 Fetching inbox messages...")
        try:
            # Import here to avoid circular dependencies
            import sys
            import os
            import re
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from api.agentmail_helper import get_inbox_messages
            
            # Use email address as inbox_id (AgentMail API uses email format)
            messages = get_inbox_messages(email, limit=20)
            
            otp_code = None
            if messages:
                logger.info(f"✅ Retrieved {len(messages)} messages, searching for OTP...")
                # Search for 6-digit OTP code in message SUBJECTS and bodies
                for msg in messages:
                    body = msg.get('body', '')
                    subject = msg.get('subject', '')
                    
                    # Log message details for debugging
                    logger.info(f"📧 Checking message - Subject: {subject}")
                    logger.info(f"📄 Body preview: {body[:200] if body else '(empty)'}...")
                    
                    # CRITICAL FIX: Check SUBJECT line first (Expedia puts OTP in subject!)
                    # Subject format: "Your secure code is 170918 - never share this"
                    matches = re.findall(r'\d{6}', subject)
                    if matches:
                        otp_code = matches[0]
                        logger.info(f"🔑 Found OTP code in SUBJECT: {otp_code}")
                        break
                    
                    # Try multiple regex patterns for OTP codes in body
                    # Pattern 1: 6 consecutive digits (most common)
                    matches = re.findall(r'\d{6}', body)
                    if matches:
                        otp_code = matches[0]
                        logger.info(f"🔑 Found OTP code in body (pattern 1): {otp_code}")
                        break
                    
                    # Pattern 2: "code is XXXXXX" or "code: XXXXXX"
                    matches = re.findall(r'(?:code|verification|passcode)[:\s]+(\d{6})', body, re.IGNORECASE)
                    if matches:
                        otp_code = matches[0]
                        logger.info(f"🔑 Found OTP code in body (pattern 2): {otp_code}")
                        break
                    
                    # Pattern 3: Check in HTML if body is empty
                    html = msg.get('html', '')
                    if html:
                        matches = re.findall(r'\d{6}', html)
                        if matches:
                            otp_code = matches[0]
                            logger.info(f"🔑 Found OTP code in HTML (pattern 3): {otp_code}")
                            break
            
            if otp_code:
                # Automatically enter the OTP
                logger.info(f"⌨️  Entering OTP code {otp_code} into input field...")
                await page.fill('#verify-sms-one-time-passcode-input', otp_code)
                await asyncio.sleep(0.5)
                
                logger.info("👆 Clicking Continue button...")
                await page.click('#verifyOtpFormSubmitButton')
                await asyncio.sleep(2)
                
                return f"✅ Successfully signed in! OTP {otp_code} was automatically entered and submitted."
            else:
                # Return detailed message with message previews for debugging
                msg_summary = []
                for i, msg in enumerate(messages[:3]):  # Show first 3 messages
                    subject = msg.get('subject', 'no subject')
                    body_preview = msg.get('body', '')[:100] if msg.get('body') else '(empty)'
                    msg_summary.append(f"Message {i+1}: From={msg.get('from', 'unknown')}\n  Subject: {subject}\n  Body: {body_preview}")
                
                logger.error(f"❌ No OTP found in {len(messages)} messages!")
                for summary in msg_summary:
                    logger.error(f"  {summary}")
                
                return f"⚠️ OTP page reached but no 6-digit OTP code found in {len(messages)} inbox messages.\n\nMessages received:\n" + "\n".join(msg_summary)
                
        except Exception as e:
            logger.error(f"Failed to fetch/enter OTP: {e}")
            return f"⚠️ Could not auto-enter OTP: {str(e)}\nPlease enter OTP manually from your inbox."
        
    except Exception as e:
        logger.error(f"Sign-in error: {e}")
        return f"Sign-in skipped/failed: {str(e)}"


@flight_tools.action('Ensure signed in (idempotent)')
async def ensure_signed_in(
    browser_session: BrowserSession,
    email: str
) -> str:
    """Sign in only if the header shows 'Sign in'; otherwise do nothing.

    This should be called at the start of any Expedia flow to guarantee the
    session is authenticated before performing actions that may require it.
    """
    try:
        page = await browser_session.get_current_page()

        # If header Sign in button exists, run sign-in; otherwise assume signed in
        sign_in_button = await page.query_selector("button[data-testid='header-menu-button']:has-text('Sign in')")
        if sign_in_button:
            return await sign_in_expedia(browser_session, email)
        return "✅ Already signed in"
    except Exception as e:
        logger.error(f"ensure_signed_in error: {e}")
        return f"Error ensuring sign-in: {str(e)}"


@flight_tools.action('Navigate directly to flight search results')
async def navigate_to_search_results(
    browser_session: BrowserSession,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    travelers: int = 1
) -> str:
    """
    Navigate directly to flight search results using a pre-built URL.
    This bypasses the form filling which can be unreliable.
    
    Args:
        origin: Airport code (e.g., "SFO", "LAX")
        destination: Airport code (e.g., "LAX", "JFK")
        departure_date: Format "MM/DD/YYYY" (e.g., "12/15/2025")
        return_date: Format "MM/DD/YYYY" (e.g., "12/20/2025")
        travelers: Number of adults (default 1)
    """
    try:
        page = await browser_session.get_current_page()
        
        # Build the search URL
        search_url = (
            f"https://www.expedia.com/Flights-Search?"
            f"flight-type=on&mode=search&trip=roundtrip"
            f"&leg1=from%3A{origin}%2Cto%3A{destination}%2Cdeparture%3A{departure_date.replace('/', '%2F')}TANYT"
            f"&leg2=from%3A{destination}%2Cto%3A{origin}%2Cdeparture%3A{return_date.replace('/', '%2F')}TANYT"
            f"&options=cabinclass%3Aeconomy&passengers=adults%3A{travelers}"
        )
        
        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        
        logger.info(f"✅ Navigated to search results: {origin} → {destination}")
        return f"Navigated to flight results: {origin} → {destination}, {departure_date} - {return_date}, {travelers} traveler(s)"
        
    except Exception as e:
        logger.error(f"Navigation error: {e}")
        return f"Error navigating: {str(e)}"


# ============================================================================
# PAGE 2: FLIGHT RESULTS TOOLS
# ============================================================================

@flight_tools.action('Sort flights by price (lowest first)')
async def sort_by_price(browser_session: BrowserSession) -> str:
    """Sort flight results by price from lowest to highest using the actual dropdown"""
    try:
        page = await browser_session.get_current_page()
        
        # Use the exact selector from the test
        await page.select_option('select#sort-filter-dropdown-SORT', 'PRICE_INCREASING')
        await asyncio.sleep(1.5)
        
        logger.info("✅ Sorted by price (lowest to highest)")
        return "Sorted by price (lowest first)"
        
    except Exception as e:
        logger.error(f"Error sorting by price: {e}")
        return f"Sort dropdown not found: {str(e)}"


@flight_tools.action('Select Basic fare on outbound flight')
async def select_outbound_basic_fare(browser_session: BrowserSession) -> str:
    """
    Click the Basic fare card on the first (cheapest) outbound flight,
    then click the Select button in the popup.
    """
    try:
        page = await browser_session.get_current_page()
        
        # Click the Basic fare card
        await page.click('button.uitk-card-link[aria-label*="Basic"]', timeout=10000)
        await asyncio.sleep(1)
        logger.info("✅ Clicked Basic fare card")
        
        # Click the "Select" button in the popup
        await page.click('button[data-stid="select-button"]', timeout=10000)
        await asyncio.sleep(1.5)
        logger.info("✅ Selected outbound flight")
        
        return "Selected Basic fare for outbound flight"
        
    except Exception as e:
        logger.error(f"Error selecting outbound flight: {e}")
        return f"Could not select outbound flight: {str(e)}"


@flight_tools.action('Select Basic fare on return flight')
async def select_return_basic_fare(browser_session: BrowserSession) -> str:
    """
    Click the Basic fare card on the first (cheapest) return flight,
    then click the Select button (which opens a NEW TAB).
    Automatically switches to the new tab.
    """
    try:
        page = await browser_session.get_current_page()
        
        # Wait for return flights to appear
        await asyncio.sleep(1.5)
        
        # Click the Basic fare card on return flight
        await page.click('button.uitk-card-link[aria-label*="Basic"]', timeout=10000)
        await asyncio.sleep(1)
        logger.info("✅ Clicked Basic fare card for return")
        
        # Click Select button - this opens a NEW TAB
        logger.info("🔄 Clicking Select (will open new tab)...")
        
        # Use page.expect_popup() to capture the new tab
        async with page.expect_popup() as popup_info:
            await page.click('button[data-stid="select-button"]', timeout=10000)
        
        # Get the new page
        new_page = await popup_info.value
        logger.info(f"✅ New tab captured: {new_page.url}")
        
        # Wait for it to load
        await new_page.wait_for_load_state("domcontentloaded", timeout=30000)
        
        # Bring to front and switch; close old tab to force focus on new one
        await new_page.bring_to_front()
        await asyncio.sleep(1.0)
        try:
            await page.close()
            logger.info("✅ Closed previous tab to focus new traveler-info tab")
        except Exception:
            logger.info("ⓘ Could not close previous tab; relying on bring_to_front()")
        await asyncio.sleep(0.5)
        logger.info(f"✅ Switched to new tab: {new_page.url}")
        
        return "Selected Basic fare for return flight (switched to new tab)"
        
    except Exception as e:
        logger.error(f"Error selecting return flight: {e}")
        return f"Could not select return flight: {str(e)}"


# ============================================================================
# PAGE 3: TRAVELER INFO & CHECKOUT
# ============================================================================

@flight_tools.action('Fill traveler details on booking screen')
async def fill_traveler_details(
    browser_session: BrowserSession,
    first_name: str = "John",
    middle_name: str = "Michael",
    last_name: str = "Doe",
    email: str = "john.doe@example.com",
    phone_country_code: str = "1",
    phone: str = "4155551234"
) -> str:
    """
    Fill traveler information form on the booking screen.
    Uses exact selectors from the working test.
    """
    try:
        page = await browser_session.get_current_page()
        
        # Wait for form to be visible
        await page.wait_for_selector('form.air-trip-preference', timeout=20000)
        await asyncio.sleep(0.5)
        
        # Scroll to form
        await page.evaluate("""() => {
            const form = document.querySelector('form.air-trip-preference');
            if (form) form.scrollIntoView({behavior: 'smooth', block: 'start'});
        }""")
        await asyncio.sleep(0.5)
        
        # First Name (required)
        await page.wait_for_selector(
            'input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].firstName"]',
            state='visible', timeout=10000
        )
        await page.fill(
            'input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].firstName"]',
            first_name
        )
        await asyncio.sleep(0.2)
        logger.info(f"✓ First name: {first_name}")
        
        # Last Name (required)
        await page.fill(
            'input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].lastName"]',
            last_name
        )
        await asyncio.sleep(0.2)
        logger.info(f"✓ Last name: {last_name}")
        
        # Email (required)
        await page.fill('input[name="email"]', email)
        await asyncio.sleep(0.2)
        logger.info(f"✓ Email: {email}")
        
        # Country code (required for phone)
        await page.select_option(
            'select[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].phoneCountryCode"]',
            phone_country_code
        )
        await asyncio.sleep(0.2)
        logger.info(f"✓ Country code: +{phone_country_code}")
        
        # Phone Number (required)
        phone_selectors = [
            'input[name*="phone"]',
            'input[id*="phone"]',
            'input#phone-number\\[0\\]',
        ]
        phone_filled = False
        for selector in phone_selectors:
            try:
                await page.wait_for_selector(selector, state='visible', timeout=3000)
                await page.fill(selector, phone)
                await asyncio.sleep(0.2)
                logger.info(f"✓ Phone: {phone}")
                phone_filled = True
                break
            except:
                continue
        
        if not phone_filled:
            logger.warning("⚠ Phone number field not found")
        
        # Middle Name (optional)
        try:
            await page.fill(
                'input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].middleName"]',
                middle_name
            )
            await asyncio.sleep(0.2)
            logger.info(f"✓ Middle name: {middle_name}")
        except:
            logger.info("ⓘ Middle name skipped (optional)")
        
        logger.info("✅ Traveler details filled successfully")
        return "Traveler details filled successfully"
        
    except Exception as e:
        logger.error(f"Error filling traveler details: {e}")
        return f"Could not fill traveler details: {str(e)}"


@flight_tools.action('Click Continue to checkout button')
async def click_continue_checkout(browser_session: BrowserSession) -> str:
    """
    Scroll to and click the 'Continue to checkout' button.
    Uses exact selector from the working test.
    """
    try:
        page = await browser_session.get_current_page()
        
        # Scroll to checkout button
        await page.evaluate("""() => {
            const btn = document.querySelector('button[data-stid="goto-checkout-button"]');
            if (btn) btn.scrollIntoView({behavior: 'smooth', block: 'center'});
        }""")
        await asyncio.sleep(1)
        
        # Wait for button to be visible
        await page.wait_for_selector('button[data-stid="goto-checkout-button"]', state='visible', timeout=15000)
        
        # Click checkout button
        await page.click('button[data-stid="goto-checkout-button"]', timeout=10000)
        await asyncio.sleep(1.5)
        
        logger.info("✅ Clicked Continue to checkout")
        return "Clicked Continue to checkout button"
        
    except Exception as e:
        logger.error(f"Error clicking checkout button: {e}")
        return f"Could not click checkout button: {str(e)}"


@flight_tools.action('Handle nudge dialog if appears')
async def handle_nudge_dialog(browser_session: BrowserSession) -> str:
    """
    Click 'Go to checkout' in the nudge dialog if it appears.
    If no nudge appears, returns info message (not an error).
    """
    try:
        page = await browser_session.get_current_page()
        
        # Wait a bit for nudge to appear
        await asyncio.sleep(1)
        
        # Check if nudge exists
        nudge_exists = await page.query_selector('button[data-stid="nudge-goto-checkout-button"]')
        if nudge_exists:
            await page.click('button[data-stid="nudge-goto-checkout-button"]', timeout=10000)
            await page.wait_for_load_state('domcontentloaded', timeout=20000)
            await asyncio.sleep(1.5)
            logger.info("✅ Clicked 'Go to checkout' from nudge")
            return "Clicked Go to checkout from nudge dialog"
        else:
            logger.info("ℹ️ No nudge dialog appeared")
            return "No nudge dialog appeared (went directly to payment)"
            
    except Exception as e:
        logger.error(f"Error handling nudge dialog: {e}")
        return f"Nudge dialog handling failed: {str(e)}"


# ============================================================================
# PAGE 4: PAYMENT FORM
# ============================================================================

@flight_tools.action('Fill payment form with dummy data')
async def fill_payment_form(
    browser_session: BrowserSession,
    cardholder_name: str = "John Doe",
    card_number: str = "4111111111111111",
    exp_month: str = "12",
    exp_year: str = "2027",
    cvv: str = "123",
    billing_country: str = "USA",
    billing_street: str = "123 Main St",
    billing_city: str = "San Francisco",
    billing_state: str = "CA",
    billing_zip: str = "94102"
) -> str:
    """
    Fill the payment form with dummy test data.
    **WARNING**: Uses test card number - do NOT submit!
    Uses exact selectors from the working test.
    """
    try:
        page = await browser_session.get_current_page()
        
        # Wait for payment section
        await page.wait_for_selector('#payment-type-creditcard', timeout=20000)
        
        # Scroll to payment section
        await page.evaluate("""() => {
            const section = document.querySelector('#payment-type-creditcard');
            if (section) section.scrollIntoView({behavior: 'smooth', block: 'start'});
        }""")
        await asyncio.sleep(1)
        
        # Select "Use a different card" if needed
        try:
            await page.click('input.use-new-card[type="radio"]', timeout=5000)
            await asyncio.sleep(0.5)
            logger.info("• Selected 'Use a different card'")
        except:
            logger.info("• Already on new card form")
        
        # Fill cardholder name (avoid hidden inputs)
        await page.wait_for_selector('input[name="creditCards[0].cardholder_name"]:not([type="hidden"])', 
                                     state='visible', timeout=10000)
        await page.fill('input[name="creditCards[0].cardholder_name"]:not([type="hidden"])', cardholder_name)
        await asyncio.sleep(0.2)
        logger.info(f"• Name: {cardholder_name}")
        
        # Fill card number
        await page.fill('input#creditCardInput', card_number)
        await asyncio.sleep(0.2)
        logger.info(f"• Card: {card_number}")
        
        # Select expiration month & year
        await page.select_option('select[name="creditCards[0].expiration_month"]', exp_month)
        await asyncio.sleep(0.2)
        await page.select_option('select[name="creditCards[0].expiration_year"]', exp_year)
        await asyncio.sleep(0.2)
        logger.info(f"• Exp: {exp_month}/{exp_year}")
        
        # Fill CVV
        await page.fill('input#new_cc_security_code', cvv)
        await asyncio.sleep(0.2)
        logger.info(f"• CVV: {cvv}")
        
        # Scroll to billing section
        await page.evaluate("""() => {
            const billingSection = document.querySelector('.billing-address-one');
            if (billingSection) billingSection.scrollIntoView({behavior: 'smooth', block: 'center'});
        }""")
        await asyncio.sleep(1)
        
        # Select billing country
        try:
            await page.select_option('select.billing-country[name="creditCards[0].country"]', billing_country)
            await asyncio.sleep(0.3)
            logger.info(f"• Country: {billing_country}")
        except:
            logger.info("• Country already set")
        
        # Fill billing address
        await page.wait_for_selector('input[name="creditCards[0].street"]', state='visible', timeout=10000)
        await page.fill('input[name="creditCards[0].street"]', billing_street)
        await asyncio.sleep(0.2)
        logger.info(f"• Street: {billing_street}")
        
        # Fill city
        await page.fill('input[name="creditCards[0].city"]', billing_city)
        await asyncio.sleep(0.2)
        logger.info(f"• City: {billing_city}")
        
        # Select state
        await page.select_option('select.billing-state-dropdown[name="creditCards[0].state"]', billing_state)
        await asyncio.sleep(0.2)
        logger.info(f"• State: {billing_state}")
        
        # Fill ZIP code
        await page.fill('input.billing-zip-code[name="creditCards[0].zipcode"]', billing_zip)
        await asyncio.sleep(0.2)
        logger.info(f"• ZIP: {billing_zip}")
        
        logger.info("✅ Payment form filled successfully!")
        return f"Payment form filled: {billing_street}, {billing_city}, {billing_state} {billing_zip}"
        
    except Exception as e:
        logger.error(f"Error filling payment form: {e}")
        return f"Could not fill payment form: {str(e)}"


@flight_tools.action('Decline booking protection insurance')
async def decline_insurance(browser_session: BrowserSession) -> str:
    """
    Click "No" on the booking protection insurance option.
    Uses exact selector from the working test.
    """
    try:
        page = await browser_session.get_current_page()
        
        # Scroll to insurance section
        await page.evaluate("""() => {
            const insuranceSection = document.querySelector('input#no_insurance');
            if (insuranceSection) insuranceSection.scrollIntoView({behavior: 'smooth', block: 'center'});
        }""")
        await asyncio.sleep(1)
        
        # Click "No" insurance radio button
        await page.wait_for_selector('input#no_insurance', state='visible', timeout=10000)
        await page.click('input#no_insurance')
        await asyncio.sleep(0.5)
        
        logger.info("✅ Declined booking protection insurance")
        return "Declined booking protection insurance"
        
    except Exception as e:
        logger.error(f"Error declining insurance: {e}")
        return f"Could not decline insurance: {str(e)}"


@flight_tools.action('Verify Complete Booking button (DO NOT CLICK)')
async def verify_complete_booking_button(browser_session: BrowserSession) -> str:
    """
    Scroll to and verify the Complete Booking button is visible and ready.
    **IMPORTANT**: This does NOT click the button - it only confirms we're ready.
    This is the final step before actual booking.
    """
    try:
        page = await browser_session.get_current_page()
        
        # Scroll to Complete Booking button
        await page.evaluate("""() => {
            const completeBtn = document.querySelector('button#complete-booking');
            if (completeBtn) completeBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
        }""")
        await asyncio.sleep(1)
        
        # Wait for button to be visible
        await page.wait_for_selector('button#complete-booking', state='visible', timeout=10000)
        
        logger.info("✅ Complete Booking button is visible and ready")
        logger.info("⚠️  NOT clicking - this is test data only!")
        return "✅ Complete Booking button verified (NOT clicked - test data only)"
        
    except Exception as e:
        logger.error(f"Error verifying Complete Booking button: {e}")
        return f"Could not find Complete Booking button: {str(e)}"


# ============================================================================
# UTILITY TOOLS
# ============================================================================

@flight_tools.action('Wait for page to load')
async def wait_for_load(
    browser_session: BrowserSession,
    seconds: int = 3
) -> str:
    """Wait for a specified number of seconds for page to load"""
    try:
        await asyncio.sleep(seconds)
        return f"Waited {seconds} seconds"
    except Exception as e:
        return f"Error: {str(e)}"


@flight_tools.action('Take screenshot of current page')
async def take_screenshot(
    browser_session: BrowserSession,
    filename: str = "expedia_screenshot.png"
) -> str:
    """Take a screenshot of the current page for debugging"""
    try:
        page = await browser_session.get_current_page()
        await page.screenshot(path=filename)
        return f"Screenshot saved: {filename}"
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        return f"Error: {str(e)}"


# Export the registry
__all__ = ['flight_tools']
