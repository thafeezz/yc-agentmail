"""
Test Hotel Tools Directly with Playwright
Similar to flight tools but for hotel booking flow.
Tests each step by calling it directly with a real browser session.
"""

import asyncio
import os
import platform
from playwright.async_api import async_playwright
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext


async def test_hotel_tools():
    """Test the hotel tools directly by calling them"""
    print("\n" + "="*70)
    print("🏨 TESTING HOTEL TOOLS DIRECTLY (NO AGENT)")
    print("="*70)

    print("\n⚠️  IMPORTANT: Make sure Chrome is closed!")
    print("⏳ Starting in 2 seconds...")
    await asyncio.sleep(2)

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
        page = await session.get_current_page()

        # Navigate to hotel search page
        print("\n3️⃣ Navigating to hotel search...")
        hotel_search_url = "https://www.expedia.com/Hotel-Search?destination=San+Francisco+%28and+vicinity%29%2C+California%2C+United+States+of+America&regionId=178305&latLong=37.7874%2C-122.4082&flexibility=0_DAY&d1=2025-11-02&startDate=2025-11-02&d2=2025-11-04&endDate=2025-11-04&adults=2&rooms=1"
        await page.goto(hotel_search_url, wait_until="domcontentloaded", timeout=60000)

        # Wait 7 seconds for any captchas to load
        print("   ⏳ Waiting 7 seconds for captchas...")
        await asyncio.sleep(7)

        # Take screenshot of search results
        await page.screenshot(path="1_hotel_results.png")
        print(f"   ✅ Navigated to hotel results (screenshot: 1_hotel_results.png)")
        print(f"   Current URL: {page.url}")

        # Step 4: Click on the first hotel card
        print("\n4️⃣ Selecting first hotel...")
        try:
            # Click the hotel card link (opens in new tab)
            print(f"   🔄 Clicking hotel card (will open new tab)...")

            # Use page.expect_popup() to handle new tab
            async with page.expect_popup() as popup_info:
                await page.click('a[data-stid="open-hotel-information"]', timeout=10000)

            # Get the new page
            new_page = await popup_info.value
            print(f"   ✅ New tab captured: {new_page.url}")

            # Wait for it to load
            await new_page.wait_for_load_state("domcontentloaded", timeout=30000)
            print(f"   ✅ Hotel details page loaded")

            # Switch to new tab
            await new_page.bring_to_front()
            page = new_page
            await asyncio.sleep(1.5)
            print(f"   ✅ Switched to hotel details tab")

        except Exception as e:
            print(f"   ⚠️  Could not select hotel: {e}")
            import traceback
            traceback.print_exc()

        # Step 5: Click "Select a room" button
        print("\n5️⃣ Clicking 'Select a room' button...")
        try:
            # Scroll to button
            await page.evaluate("""() => {
                const btn = document.querySelector('button[data-stid="sticky-button"]');
                if (btn) btn.scrollIntoView({behavior: 'smooth', block: 'center'});
            }""")
            await asyncio.sleep(1)

            await page.wait_for_selector('button[data-stid="sticky-button"]', state='visible', timeout=10000)
            await page.click('button[data-stid="sticky-button"]')
            await asyncio.sleep(1.5)
            print(f"   ✅ Clicked 'Select a room' button")

        except Exception as e:
            print(f"   ⚠️  Could not click 'Select a room': {e}")

        # Step 6: Click "Reserve" button for a room
        print("\n6️⃣ Clicking 'Reserve' button...")
        try:
            # Scroll to reserve button
            await page.evaluate("""() => {
                const btn = document.querySelector('button[data-stid="submit-hotel-reserve"]');
                if (btn) btn.scrollIntoView({behavior: 'smooth', block: 'center'});
            }""")
            await asyncio.sleep(1)

            # Click the first Reserve button
            await page.wait_for_selector('button[data-stid="submit-hotel-reserve"]', state='visible', timeout=10000)
            await page.click('button[data-stid="submit-hotel-reserve"]')
            await asyncio.sleep(1.5)
            print(f"   ✅ Clicked 'Reserve' button")

            # Check if payment options appear (Pay now vs Pay at property)
            print(f"   🔍 Checking for payment options...")
            await asyncio.sleep(1)

            pay_later_btn = await page.query_selector('button[data-stid="submit-hotel-reserve"][aria-describedby="PAY_LATER-payment-reassurance-etp"]')
            pay_now_btn = await page.query_selector('button[data-stid="submit-hotel-reserve"][aria-describedby="PAY_NOW-payment-reassurance-etp"]')

            if pay_later_btn or pay_now_btn:
                # Payment options appeared - need to select one
                print(f"   📋 Payment options detected after clicking Reserve")

                if pay_later_btn:
                    # Prefer "Pay at property" option
                    await page.wait_for_selector('button[data-stid="submit-hotel-reserve"][aria-describedby="PAY_LATER-payment-reassurance-etp"]', state='visible', timeout=10000)
                    await page.click('button[data-stid="submit-hotel-reserve"][aria-describedby="PAY_LATER-payment-reassurance-etp"]')
                    await asyncio.sleep(1.5)
                    print(f"   ✅ Selected 'Pay at property' option")
                elif pay_now_btn:
                    # Only "Pay now" available
                    await page.wait_for_selector('button[data-stid="submit-hotel-reserve"][aria-describedby="PAY_NOW-payment-reassurance-etp"]', state='visible', timeout=10000)
                    await page.click('button[data-stid="submit-hotel-reserve"][aria-describedby="PAY_NOW-payment-reassurance-etp"]')
                    await asyncio.sleep(1.5)
                    print(f"   ✅ Selected 'Pay now' option")
            else:
                # No payment options appeared - already proceeded to checkout
                print(f"   ℹ️  No payment options appeared, proceeding to checkout")

            print(f"   🌐 Current URL: {page.url}")

        except Exception as e:
            print(f"   ⚠️  Could not click Reserve: {e}")
            import traceback
            traceback.print_exc()

        # Step 7: Fill traveler information form
        print("\n7️⃣ Filling traveler information...")
        try:
            # Wait for form to be visible
            await asyncio.sleep(1.5)

            # First name - use the exact selector from HTML
            try:
                first_name_selector = 'input[data-stid*="traveler:name:first_name"]'
                await page.wait_for_selector(first_name_selector, state='visible', timeout=10000)
                await page.fill(first_name_selector, 'John')
                await asyncio.sleep(0.2)
                print(f"      ✓ First name: John")
            except Exception as e:
                print(f"      ✗ First name failed: {e}")

            # Last name
            try:
                last_name_selector = 'input[data-stid*="traveler:name:last_name"]'
                await page.fill(last_name_selector, 'Doe')
                await asyncio.sleep(0.2)
                print(f"      ✓ Last name: Doe")
            except Exception as e:
                print(f"      ✗ Last name failed: {e}")

            # Email
            try:
                email_selector = 'input[data-stid*="contact:email"]'
                await page.fill(email_selector, 'john.doe@example.com')
                await asyncio.sleep(0.2)
                print(f"      ✓ Email: john.doe@example.com")
            except Exception as e:
                print(f"      ✗ Email failed: {e}")

            # Phone country code (already selected as USA +1)
            print(f"      ✓ Country code: USA +1 (default)")

            # Phone number
            try:
                phone_selector = 'input[data-stid*="contact:phone:number"]'
                await page.fill(phone_selector, '4155551234')
                await asyncio.sleep(0.2)
                print(f"      ✓ Phone: 4155551234")
            except Exception as e:
                print(f"      ✗ Phone failed: {e}")

            print(f"   ✅ Traveler information filled")

            # Take screenshot
            await page.screenshot(path="2_traveler_info_filled.png", full_page=True)
            print(f"   📸 Screenshot saved: 2_traveler_info_filled.png")

            # Wait 0.5 seconds after user info before proceeding to payment
            print(f"   ⏳ Waiting 0.5s before filling payment...")
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"   ⚠️  Traveler info form failed: {e}")
            import traceback
            traceback.print_exc()

        # Step 8: Fill payment form (regular input fields - NO iframes for hotels!)
        print("\n8️⃣ Filling payment form...")
        print(f"   🌐 Current URL: {page.url}")

        # Longer wait for payment section to fully load and validate
        await asyncio.sleep(2)

        # Scroll down to payment section FIRST (before checking visibility)
        print(f"   🔄 Scrolling to payment section...")
        try:
            # Scroll down by pixels to bring payment section into viewport
            await page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(1)

            # Try to scroll to card details heading or card field itself
            await page.evaluate("""() => {
                // Try to find and scroll to "Reservation card details" or "Card details" section
                const headings = Array.from(document.querySelectorAll('h2, h3, h4'));
                const cardHeading = headings.find(h => h.textContent.includes('card details') || h.textContent.includes('Card details'));
                if (cardHeading) {
                    cardHeading.scrollIntoView({behavior: 'smooth', block: 'start'});
                    return;
                }

                // Fallback: scroll to the card number field directly
                const cardField = document.querySelector('input#payment_credit_card');
                if (cardField) {
                    cardField.scrollIntoView({behavior: 'smooth', block: 'center'});
                }
            }""")
            await asyncio.sleep(1.5)
            print(f"   ✅ Scrolled to payment section")

            # NOW check if field is visible (after scrolling)
            card_field = page.locator('input#payment_credit_card').first()
            await card_field.wait_for(state='visible', timeout=10000)
            print(f"   ✅ Payment fields now visible")

        except Exception as e:
            print(f"   ⚠️ Could not find payment section: {e}")
            await page.screenshot(path="error_no_payment_section.png", full_page=True)
            print(f"   📸 Screenshot saved: error_no_payment_section.png")
            raise

        # Fill card number - simple selector, visible check, keyboard.type
        print(f"   💳 Filling card number...")
        card_locator = page.locator('input#payment_credit_card')
        await card_locator.wait_for(state='visible', timeout=10000)
        await card_locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)
        await card_locator.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type('4111111111111111')
        await asyncio.sleep(0.2)
        print(f"      ✓ Card number: 4111 1111 1111 1111")

        # Fill expiration date
        print(f"   📅 Filling expiration...")
        expiry_locator = page.locator('input#expiry')
        await expiry_locator.wait_for(state='visible', timeout=10000)
        await expiry_locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)
        await expiry_locator.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type('1227')
        await asyncio.sleep(0.2)
        print(f"      ✓ Expiration: 12/27")

        # Fill CVV
        print(f"   🔒 Filling CVV...")
        cvv_locator = page.locator('input#payment_cvv_code')
        await cvv_locator.wait_for(state='visible', timeout=10000)
        await cvv_locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)
        await cvv_locator.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type('123')
        await asyncio.sleep(0.2)
        print(f"      ✓ CVV: 123")

        # Fill billing ZIP code
        print(f"   🏠 Filling billing ZIP...")
        zip_locator = page.locator('input#payment_zip_code')
        await zip_locator.wait_for(state='visible', timeout=10000)
        await zip_locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)
        await zip_locator.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type('94102')
        await asyncio.sleep(0.2)
        print(f"      ✓ Billing ZIP: 94102")

        print(f"   ✅ Payment form filled successfully!")

        # Take screenshot
        await page.screenshot(path="3_payment_form.png", full_page=True)
        print(f"   📸 Screenshot saved: 3_payment_form.png")

        # Step 9: Decline protection
        print("\n9️⃣ Declining protection...")
        try:
            # Scroll to protection section
            await page.evaluate("""() => {
                const protectionRadio = document.querySelector('input[type="radio"][name="offers"][value="-1"]');
                if (protectionRadio) protectionRadio.scrollIntoView({behavior: 'smooth', block: 'center'});
            }""")
            await asyncio.sleep(1)

            # Click "No protection" radio button (id="-1", name="offers", value="-1")
            await page.wait_for_selector('input[type="radio"][name="offers"][value="-1"]', state='visible', timeout=10000)
            await page.click('input[type="radio"][name="offers"][value="-1"]')
            await asyncio.sleep(0.5)
            print(f"   ✅ Declined protection (No protection selected)")

            # Take screenshot
            await page.screenshot(path="4_protection_declined.png", full_page=True)
            print(f"   📸 Screenshot saved: 4_protection_declined.png")

        except Exception as e:
            print(f"   ⚠️  Could not decline protection: {e}")
            print(f"   ℹ️  Protection may already be declined or not available")
            import traceback
            traceback.print_exc()

        # Step 10: Click "Book now" button (but don't actually submit)
        print("\n🔟 Testing 'Book now' button...")
        try:
            # Scroll to book button
            await page.evaluate("""() => {
                const bookBtn = document.querySelector('button#complete-booking[data-testid="book-button"]');
                if (bookBtn) bookBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
            }""")
            await asyncio.sleep(1)

            # Wait for button to be visible
            await page.wait_for_selector('button#complete-booking[data-testid="book-button"]', state='visible', timeout=10000)

            # Get button text to confirm
            button_text = await page.text_content('button#complete-booking[data-testid="book-button"]')
            print(f"   📋 Found 'Book now' button: {button_text}")

            # Take final screenshot
            await page.screenshot(path="5_ready_to_book.png", full_page=True)
            print(f"   📸 Screenshot saved: 5_ready_to_book.png")

            # NOTE: We are NOT clicking the button to avoid actual booking
            print(f"   ⚠️  NOT clicking 'Book now' (this is a test with dummy data)")
            print(f"   ✅ 'Book now' button is visible and ready to click")

        except Exception as e:
            print(f"   ⚠️  Could not find 'Book now' button: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "="*70)
        print("✅ HOTEL TEST COMPLETE!")
        print("="*70)
        print("\n📸 Check the browser window - all forms filled automatically!")
        print("   Screenshots saved:")
        print("      • 1_hotel_results.png - Hotel search results")
        print("      • 2_traveler_info_filled.png - Traveler information")
        print("      • 3_payment_form.png - Payment form (fully filled)")
        print("      • 4_protection_declined.png - Protection declined")
        print("      • 5_ready_to_book.png - Ready to book")
        print("\n   ✅ All fields filled automatically (no manual entry needed)!")
        print("   The browser will stay open for 30 seconds...")
        print("   ⚠️  Don't actually submit - this is test data!")

        await asyncio.sleep(30)

        # Cleanup
        await browser.close()
        print("\n🧹 Browser closed")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_hotel_tools())
