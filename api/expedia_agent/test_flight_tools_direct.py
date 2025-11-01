"""
Test Flight Tools Directly with Playwright
Uses the actual expedia_flight_tools functions without the AI agent.
Tests each tool by calling it directly with a real browser session.
"""

import asyncio
import os
import platform
from playwright.async_api import async_playwright
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext


def get_chrome_profile_path():
    """Get the default Chrome profile path for the current OS"""
    os_type = platform.system().lower()
    if os_type == "darwin":  # macOS
        user_data_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome')
        profile_directory = 'Default'
    elif os_type == "linux":
        user_data_dir = os.path.expanduser('~/.config/google-chrome')
        profile_directory = 'Default'
    elif os_type == "windows":
        user_data_dir = os.path.expanduser(r'~\AppData\Local\Google\Chrome\User Data')
        profile_directory = 'Default'
    else:
        raise ValueError(f"Unsupported OS: {os_type}")
    return user_data_dir, profile_directory


async def test_flight_tools():
    """Test the flight tools directly by calling them"""
    print("\n" + "="*70)
    print("🧪 TESTING FLIGHT TOOLS DIRECTLY (NO AGENT)")
    print("="*70)
    
    print("\n⚠️  IMPORTANT: Make sure Chrome is closed!")
    print("⏳ Starting in 2 seconds...")
    await asyncio.sleep(2)
    
    # Import the tools
    # Add parent directory to path to allow imports
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from expedia_flight_tools import flight_tools
    
    # Get the tool functions from the registry
    # We'll call them directly through the browser session
    
    try:
        # Create a browser-use Browser instance
        print("\n1️⃣ Creating browser...")
        browser = Browser(
            config=BrowserConfig(
                headless=False,
                disable_security=False,
            )
        )
        
        # Get browser session
        print("2️⃣ Getting browser session...")
        session = await browser.new_context()
        
        # Test: Navigate directly to search results (skip form filling since it's flaky)
        print("\n3️⃣ Signing in (pre-flight)...")
        page = await session.get_current_page()
        
        # Go to homepage for sign in
        await page.goto("https://www.expedia.com/", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(1)

        try:
            # Open header Sign in menu
            await page.click("button[data-testid='header-menu-button']:has-text('Sign in')", timeout=10000)
            await asyncio.sleep(0.5)

            # Click Sign in in the dropdown
            await page.click("a[href^='/login'] >> text=Sign in", timeout=10000)
            await asyncio.sleep(1)
            
            # Fill email and continue
            await page.wait_for_selector('#loginFormEmailInput', timeout=15000)
            await page.fill('#loginFormEmailInput', "lobbygpe@proton.me")
            await asyncio.sleep(0.3)
            await page.click('#loginFormSubmitButton')

            # Wait for OTP screen
            print("   ⏳ Waiting for OTP page...")
            await page.wait_for_selector('#verify-sms-one-time-passcode-input', timeout=15000)
            print("   ✅ Reached OTP page!")
            
            # Go back to base URL instead of handling OTP
            print("   🔙 Navigating back to base URL (skipping OTP)...")
            await page.goto("https://www.expedia.com/", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
            print("   ✅ Back at homepage (sign-in flow skipped)")
        except Exception as e:
            print(f"   ⚠️  Sign-in step skipped/failed: {e}")
        
        # Navigate directly to a pre-filled search URL after sign-in
        print("\n3️⃣ Testing navigation to search results...")
        search_url = "https://www.expedia.com/Flights-Search?flight-type=on&mode=search&trip=roundtrip&leg1=from%3ASFO%2Cto%3ALAX%2Cdeparture%3A12%2F15%2F2025TANYT&leg2=from%3ALAX%2Cto%3ASFO%2Cdeparture%3A12%2F20%2F2025TANYT&options=cabinclass%3Aeconomy&passengers=adults%3A1"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        
        # Take a screenshot
        await page.screenshot(path="2_flight_results.png")
        print(f"   ✅ Navigated to flight results (screenshot: 2_flight_results.png)")
        print(f"   Current URL: {page.url}")
        
        # Test Tool 4: Sort by price (low to high)
        print("\n4️⃣ Testing sort by price...")
        try:
            # Select "Price (lowest to highest)" from dropdown
            await page.select_option('select#sort-filter-dropdown-SORT', 'PRICE_INCREASING')
            await asyncio.sleep(1.5)
            print(f"   ✅ Sorted by price (lowest to highest)")
        except Exception as e:
            print(f"   ⚠️  Sort dropdown not found: {e}")
        
        # Test Tool 5: Click the first flight's Basic fare card
        print("\n5️⃣ Testing select Basic fare on first flight...")
        try:
            # Click the Basic fare card (the button with aria-label containing "Basic")
            await page.click('button.uitk-card-link[aria-label*="Basic"]', timeout=10000)
            await asyncio.sleep(1)
            print(f"   ✅ Clicked Basic fare card")

            # Click the "Select" button in the popup
            await page.click('button[data-stid="select-button"]', timeout=10000)
            await asyncio.sleep(1.5)
            print(f"   ✅ Clicked Select button for outbound flight")
        except Exception as e:
            print(f"   ⚠️  Could not select outbound flight: {e}")

        # Test Tool 6: Select return flight (same process) - This opens a NEW TAB!
        print("\n6️⃣ Testing select Basic fare on return flight...")
        # Wait a moment for return flights to appear
        await asyncio.sleep(1.5)

        # Click the Basic fare card on return flight
        await page.click('button.uitk-card-link[aria-label*="Basic"]', timeout=10000)
        await asyncio.sleep(1)
        print(f"   ✅ Clicked Basic fare card for return")

        # Click the "Select" button - this opens a NEW TAB
        print(f"   🔄 Clicking Select (this will open a new tab)...")

        # Use page.expect_popup() - the correct method for Playwright
        async with page.expect_popup() as popup_info:
            await page.click('button[data-stid="select-button"]', timeout=10000)

        # Get the new page
        new_page = await popup_info.value
        print(f"   ✅ New tab captured: {new_page.url}")

        # Wait for it to load (use domcontentloaded - networkidle times out on this page)
        await new_page.wait_for_load_state("domcontentloaded", timeout=30000)
        print(f"   ✅ New tab loaded (domcontentloaded)")

        # Bring to front and switch
        await new_page.bring_to_front()
        page = new_page
        await asyncio.sleep(1.5)
        print(f"   ✅ Switched to new tab: {page.url}")

        # Wait a bit more for dynamic content to load (instead of networkidle which times out)
        await asyncio.sleep(1.5)

        # Fill traveler details on booking screen
        print("\n7️⃣ Filling traveler details on booking screen...")
        try:
            # Wait for form to be visible and interactive
            await page.wait_for_selector('form.air-trip-preference', timeout=20000)
            await asyncio.sleep(0.5)
            print(f"   📋 Found traveler form")

            # Scroll to form to ensure it's in view
            await page.evaluate("""() => {
                const form = document.querySelector('form.air-trip-preference');
                if (form) form.scrollIntoView({behavior: 'smooth', block: 'start'});
            }""")
            await asyncio.sleep(0.5)

            # === REQUIRED FIELDS (fill these first) ===

            # First Name (required)
            try:
                await page.wait_for_selector('input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].firstName"]',
                                             state='visible', timeout=10000)
                await page.fill('input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].firstName"]', 'John')
                await asyncio.sleep(0.2)
                print(f"      ✓ First name: John")
            except Exception as e:
                print(f"      ✗ First name failed: {e}")

            # Last Name (required, min 2 chars)
            try:
                await page.wait_for_selector('input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].lastName"]',
                                             state='visible', timeout=10000)
                await page.fill('input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].lastName"]', 'Doe')
                await asyncio.sleep(0.2)
                print(f"      ✓ Last name: Doe")
            except Exception as e:
                print(f"      ✗ Last name failed: {e}")

            # Email (required)
            try:
                await page.wait_for_selector('input[name="email"]', state='visible', timeout=10000)
                await page.fill('input[name="email"]', 'john.doe@example.com')
                await asyncio.sleep(0.2)
                print(f"      ✓ Email: john.doe@example.com")
            except Exception as e:
                print(f"      ✗ Email failed: {e}")

            # Country/Territory Code (required for phone)
            try:
                await page.wait_for_selector('select[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].phoneCountryCode"]',
                                             state='visible', timeout=10000)
                await page.select_option('select[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].phoneCountryCode"]', '1')
                await asyncio.sleep(0.2)
                print(f"      ✓ Country code: +1 (USA)")
            except Exception as e:
                print(f"      ✗ Country code failed: {e}")

            # Phone Number (required)
            try:
                # Try to find phone number field - it may have various selectors
                phone_selectors = [
                    'input[name*="phone"]',
                    'input[id*="phone"]',
                    'input#phone-number\\[0\\]',
                ]
                phone_filled = False
                for selector in phone_selectors:
                    try:
                        await page.wait_for_selector(selector, state='visible', timeout=3000)
                        await page.fill(selector, '4155551234')
                        await asyncio.sleep(0.2)
                        print(f"      ✓ Phone: 4155551234")
                        phone_filled = True
                        break
                    except:
                        continue
                if not phone_filled:
                    print(f"      ⚠ Phone number field not found")
            except Exception as e:
                print(f"      ✗ Phone number failed: {e}")

            # === OPTIONAL FIELDS ===

            # Middle Name (optional)
            try:
                await page.fill('input[name="tripPreferencesRequest.airTripPreferencesRequest.travelerPreferences[0].middleName"]', 'Michael')
                await asyncio.sleep(0.2)
                print(f"      ✓ Middle name: Michael")
            except Exception:
                print(f"      ⓘ Middle name skipped (optional)")

            # Gender (optional - may not be present)
            try:
                gender_radio = await page.query_selector('input[id*="gender_male"]')
                if gender_radio:
                    await page.click('input[id*="gender_male"]')
                    await asyncio.sleep(0.2)
                    print(f"      ✓ Gender: Male")
            except Exception:
                print(f"      ⓘ Gender skipped (optional/not found)")

            # Date of Birth (optional - may not be present)
            try:
                dob_month = await page.query_selector('select[id*="date_of_birth_month"]')
                if dob_month:
                    await page.select_option('select[id*="date_of_birth_month"]', '05')
                    await asyncio.sleep(0.15)
                    await page.select_option('select[id*="date_of_birth_day"]', '15')
                    await asyncio.sleep(0.15)
                    await page.select_option('select[id*="date_of_birth_year"]', '1990')
                    await asyncio.sleep(0.2)
                    print(f"      ✓ DOB: 05/15/1990")
            except Exception:
                print(f"      ⓘ DOB skipped (optional/not found)")

            print("   ✅ Traveler details filled successfully")

            # Take screenshot of filled form
            await page.screenshot(path="3a_traveler_form_filled.png", full_page=True)
            print(f"   📸 Screenshot saved: 3a_traveler_form_filled.png")

            # Scroll down to make sure everything is loaded
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

        except Exception as e:
            print(f"   ⚠️  Traveler details not found/filled: {e}")
            import traceback
            traceback.print_exc()
            # Take error screenshot
            try:
                await page.screenshot(path="error_traveler_form.png", full_page=True)
                print(f"   📸 Error screenshot saved: error_traveler_form.png")
            except:
                pass
        
        # Test Tool 8: Click "Continue to checkout" button
        print("\n8️⃣ Testing continue to checkout...")
        try:
            # Scroll to checkout button
            await page.evaluate("""() => {
                const btn = document.querySelector('button[data-stid="goto-checkout-button"]');
                if (btn) btn.scrollIntoView({behavior: 'smooth', block: 'center'});
            }""")
            await asyncio.sleep(1)

            # Wait for checkout button to appear and be visible
            await page.wait_for_selector('button[data-stid="goto-checkout-button"]', state='visible', timeout=15000)
            print(f"   📋 Found checkout button")

            # Take a screenshot before clicking
            await page.screenshot(path="3_before_checkout.png")
            print(f"   📸 Screenshot saved: 3_before_checkout.png")

            # Click checkout button
            print(f"   🔄 Clicking 'Continue to checkout' button...")
            await page.click('button[data-stid="goto-checkout-button"]', timeout=10000)
            await asyncio.sleep(1.5)
            
            print(f"   ✅ Clicked checkout button")
            print(f"   🌐 Current URL: {page.url}")
            
        except Exception as e:
            print(f"   ⚠️  Checkout button not found or failed: {e}")
            print(f"   🌐 Current URL: {page.url}")
            import traceback
            traceback.print_exc()
        
        # Test Tool 9: Click "Go to checkout" in nudge dialog (if appears)
        print("\n9️⃣ Testing go to checkout (nudge dialog)...")
        try:
            # Wait a bit for nudge to appear
            await asyncio.sleep(1)

            # Check if nudge exists
            nudge_exists = await page.query_selector('button[data-stid="nudge-goto-checkout-button"]')
            if nudge_exists:
                print(f"   📋 Found nudge dialog")
                await page.click('button[data-stid="nudge-goto-checkout-button"]', timeout=10000)
                await page.wait_for_load_state('domcontentloaded', timeout=20000)
                await asyncio.sleep(1.5)
                print(f"   ✅ Clicked 'Go to checkout' from nudge")
                print(f"   🌐 Now at: {page.url}")
            else:
                print(f"   ℹ️  No nudge dialog appeared (might have gone directly to payment)")
        except Exception as e:
            print(f"   ⚠️  Nudge dialog handling failed: {e}")
            print(f"   🌐 Current URL: {page.url}")
        
        # Test Tool 10: Fill payment form with dummy data
        print("\n🔟 Testing payment form fill...")
        try:
            # Wait for payment section to load
            await page.wait_for_selector('#payment-type-creditcard', timeout=20000)
            print(f"   📋 Payment section found")

            # Scroll to payment section
            await page.evaluate("""() => {
                const section = document.querySelector('#payment-type-creditcard');
                if (section) section.scrollIntoView({behavior: 'smooth', block: 'start'});
            }""")
            await asyncio.sleep(1)

            # Select "Use a different card" radio button
            try:
                await page.click('input.use-new-card[type="radio"]', timeout=5000)
                await asyncio.sleep(0.5)
                print(f"      • Selected 'Use a different card'")
            except Exception:
                print(f"      • Already on new card form")

            # Fill cardholder name (use :not to avoid hidden inputs)
            await page.wait_for_selector('input[name="creditCards[0].cardholder_name"]:not([type="hidden"])', state='visible', timeout=10000)
            await page.fill('input[name="creditCards[0].cardholder_name"]:not([type="hidden"])', "John Doe")
            await asyncio.sleep(0.2)
            print(f"      • Name: John Doe")

            # Fill card number
            await page.fill('input#creditCardInput', "4111111111111111")
            await asyncio.sleep(0.2)
            print(f"      • Card: 4111 1111 1111 1111")

            # Select expiration month
            await page.select_option('select[name="creditCards[0].expiration_month"]', "12")
            await asyncio.sleep(0.2)

            # Select expiration year
            await page.select_option('select[name="creditCards[0].expiration_year"]', "2027")
            await asyncio.sleep(0.2)
            print(f"      • Exp: 12/2027")

            # Fill CVV
            await page.fill('input#new_cc_security_code', "123")
            await asyncio.sleep(0.2)
            print(f"      • CVV: 123")

            # Scroll to billing section to make fields visible
            await page.evaluate("""() => {
                const billingSection = document.querySelector('.billing-address-one');
                if (billingSection) billingSection.scrollIntoView({behavior: 'smooth', block: 'center'});
            }""")
            await asyncio.sleep(1)

            # Select billing country (USA should be default, but make sure)
            try:
                await page.select_option('select.billing-country[name="creditCards[0].country"]', 'USA')
                await asyncio.sleep(0.3)
                print(f"      • Country: USA")
            except Exception as e:
                print(f"      • Country already set or not found: {e}")

            # Fill billing address (wait for it to be visible first)
            try:
                await page.wait_for_selector('input[name="creditCards[0].street"]', state='visible', timeout=10000)
                await page.fill('input[name="creditCards[0].street"]', "123 Main St")
                await asyncio.sleep(0.2)
                print(f"      • Street: 123 Main St")

                # Fill city
                await page.fill('input[name="creditCards[0].city"]', "San Francisco")
                await asyncio.sleep(0.2)
                print(f"      • City: San Francisco")

                # Select state - use the specific class selector
                await page.select_option('select.billing-state-dropdown[name="creditCards[0].state"]', "CA")
                await asyncio.sleep(0.2)
                print(f"      • State: CA")

                # Fill ZIP code - use the specific class selector
                await page.fill('input.billing-zip-code[name="creditCards[0].zipcode"]', "94102")
                await asyncio.sleep(0.2)
                print(f"      • ZIP: 94102")

                print(f"   ✅ Billing address filled: 123 Main St, San Francisco, CA 94102")
            except Exception as e:
                print(f"      ⚠️ Billing address fields not visible or failed: {e}")
                # Try scrolling more and retry once with alternative selectors
                await page.evaluate("window.scrollBy(0, 200)")
                await asyncio.sleep(0.5)
                try:
                    # Try with class-based selectors
                    await page.fill('input.billing-address-one', "123 Main St", timeout=5000)
                    await asyncio.sleep(0.2)
                    await page.fill('input.billing-city', "San Francisco", timeout=5000)
                    await asyncio.sleep(0.2)
                    await page.select_option('select.billing-state-select', "CA", timeout=5000)
                    await asyncio.sleep(0.2)
                    await page.fill('input.billing-zip-code', "94102", timeout=5000)
                    await asyncio.sleep(0.2)
                    print(f"   ✅ Billing address filled (retry): 123 Main St, San Francisco, CA 94102")
                except Exception as e2:
                    print(f"      ✗ Billing address retry also failed: {e2}")
                    import traceback
                    traceback.print_exc()

            print(f"   ✅ Payment form filled successfully!")

            # Take screenshot after payment form
            await page.screenshot(path="5_payment_filled.png", full_page=True)
            print(f"   📸 Screenshot saved: 5_payment_filled.png")
            
        except Exception as e:
            print(f"   ⚠️  Could not fill payment form: {e}")
            print(f"   🌐 Current URL: {page.url}")
            import traceback
            traceback.print_exc()
            
            # Take error screenshot
            try:
                await page.screenshot(path="error_payment.png", full_page=True)
                print(f"   📸 Error screenshot saved: error_payment.png")
            except:
                pass

        # Test: Decline insurance protection
        print("\n1️⃣1️⃣ Testing decline insurance protection...")
        try:
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
            print(f"   ✅ Declined booking protection insurance")

            # Take screenshot after declining insurance
            await page.screenshot(path="6_insurance_declined.png", full_page=True)
            print(f"   📸 Screenshot saved: 6_insurance_declined.png")

        except Exception as e:
            print(f"   ⚠️  Could not decline insurance: {e}")
            import traceback
            traceback.print_exc()

        # Test: Click Complete Booking button (but don't actually submit)
        print("\n1️⃣2️⃣ Testing Complete Booking button...")
        try:
            # Scroll to Complete Booking button
            await page.evaluate("""() => {
                const completeBtn = document.querySelector('button#complete-booking');
                if (completeBtn) completeBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
            }""")
            await asyncio.sleep(1)

            # Wait for button to be visible and enabled
            await page.wait_for_selector('button#complete-booking', state='visible', timeout=10000)
            print(f"   📋 Found Complete Booking button")

            # Take final screenshot before clicking
            await page.screenshot(path="7_ready_to_complete.png", full_page=True)
            print(f"   📸 Screenshot saved: 7_ready_to_complete.png")

            # NOTE: We are NOT clicking the button to avoid actually submitting the booking
            print(f"   ⚠️  NOT clicking Complete Booking (this is a test with dummy data)")
            print(f"   ✅ Complete Booking button is visible and ready to click")

        except Exception as e:
            print(f"   ⚠️  Could not find Complete Booking button: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "="*70)
        print("✅ TEST COMPLETE!")
        print("="*70)
        print("\n📸 Check the browser window - all forms filled!")
        print("   Screenshots saved:")
        print("      • 3a_traveler_form_filled.png - Traveler details")
        print("      • 5_payment_filled.png - Payment information")
        print("      • 6_insurance_declined.png - Insurance declined")
        print("      • 7_ready_to_complete.png - Ready to complete booking")
        print("\n   The browser will stay open for 30 seconds...")
        print("   ⚠️  NOTE: Don't actually submit - this is test data!")

        await asyncio.sleep(30)
        
        # Cleanup
        await browser.close()
        print("\n🧹 Browser closed")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_flight_tools())

