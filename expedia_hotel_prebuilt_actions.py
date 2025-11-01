"""
Expedia Prebuilt Actions (Hotels) - High-level tools for browser-use agent
Mirrors the working selectors/flow from test_hotel_tools_direct.py
"""

import asyncio
import logging
from typing import Optional
from urllib.parse import quote_plus

from browser_use.controller.registry.service import Registry
from browser_use.browser.browser import BrowserSession


logger = logging.getLogger(__name__)

# Initialize prebuilt actions registry for hotels
expedia_hotel_prebuilt = Registry()


# ============================================================================
# AUTHENTICATION (delegates to shared auth)
# ============================================================================

@expedia_hotel_prebuilt.action('Ensure signed in (idempotent)')
async def ensure_signed_in(
    browser_session: BrowserSession,
    email: Optional[str] = None
) -> str:
    from expedia_auth import ensure_signed_in as _ensure
    return await _ensure(browser_session, email)


# ============================================================================
# HOTEL SEARCH ACTIONS
# ============================================================================

@expedia_hotel_prebuilt.action('Search for hotels with direct URL')
async def search_hotels(
    browser_session: BrowserSession,
    destination: str,
    check_in: str,   # YYYY-MM-DD
    check_out: str,  # YYYY-MM-DD
    adults: int = 2,
    rooms: int = 1,
) -> str:
    """
    Navigate directly to hotel search results using a pre-built URL.
    Uses the same reliable pattern as the working test.
    """
    try:
        page = await browser_session.get_current_page()

        search_url = (
            f"https://www.expedia.com/Hotel-Search?"
            f"destination={quote_plus(destination)}"
            f"&d1={check_in}&startDate={check_in}"
            f"&d2={check_out}&endDate={check_out}"
            f"&adults={adults}&rooms={rooms}"
        )

        logger.info("Navigating to hotel search results...")
        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)
        return f"✅ Hotel results loaded: {page.url}"

    except Exception as e:
        logger.error(f"Hotel search error: {e}")
        return f"❌ Error searching hotels: {str(e)}"


# ============================================================================
# HOTEL SELECTION / ROOMS
# ============================================================================

@expedia_hotel_prebuilt.action('Open first hotel details (new tab)')
async def open_first_hotel_details(browser_session: BrowserSession) -> str:
    """Click the first hotel card and switch to the details tab (popup)."""
    try:
        page = await browser_session.get_current_page()

        logger.info("Opening first hotel details (will open a new tab)...")
        async with page.expect_popup() as popup_info:
            await page.click('a[data-stid="open-hotel-information"]', timeout=10000)

        new_page = await popup_info.value
        await new_page.wait_for_load_state("domcontentloaded", timeout=30000)
        await new_page.bring_to_front()
        await asyncio.sleep(1.5)

        # Close old tab to force agent focus to the new one
        try:
            await page.close()
        except Exception:
            pass

        logger.info(f"✅ Switched to hotel details tab: {new_page.url}")
        return "✅ Hotel details opened in new tab"

    except Exception as e:
        logger.error(f"Open hotel details error: {e}")
        return f"❌ Error opening hotel details: {str(e)}"


@expedia_hotel_prebuilt.action('Click Select a room')
async def click_select_a_room(browser_session: BrowserSession) -> str:
    try:
        page = await browser_session.get_current_page()

        await page.evaluate("""() => {
            const btn = document.querySelector('button[data-stid="sticky-button"]');
            if (btn) btn.scrollIntoView({behavior: 'smooth', block: 'center'});
        }""")
        await asyncio.sleep(1)

        await page.wait_for_selector('button[data-stid="sticky-button"]', state='visible', timeout=10000)
        await page.click('button[data-stid="sticky-button"]')
        await asyncio.sleep(1.5)
        return "✅ Clicked Select a room"

    except Exception as e:
        logger.error(f"Select a room error: {e}")
        return f"❌ Error clicking Select a room: {str(e)}"


@expedia_hotel_prebuilt.action('Reserve first available room')
async def reserve_room(browser_session: BrowserSession) -> str:
    try:
        page = await browser_session.get_current_page()

        # Scroll and click the first Reserve button
        await page.evaluate("""() => {
            const btn = document.querySelector('button[data-stid="submit-hotel-reserve"]');
            if (btn) btn.scrollIntoView({behavior: 'smooth', block: 'center'});
        }""")
        await asyncio.sleep(1)

        await page.wait_for_selector('button[data-stid="submit-hotel-reserve"]', state='visible', timeout=10000)
        await page.click('button[data-stid="submit-hotel-reserve"]')
        await asyncio.sleep(1.5)

        # Check for pay options (prefer Pay Later)
        pay_later_btn = await page.query_selector('button[data-stid="submit-hotel-reserve"][aria-describedby="PAY_LATER-payment-reassurance-etp"]')
        pay_now_btn = await page.query_selector('button[data-stid="submit-hotel-reserve"][aria-describedby="PAY_NOW-payment-reassurance-etp"]')

        if pay_later_btn:
            await pay_later_btn.click()
            await asyncio.sleep(1.5)
            return "✅ Selected 'Pay at property'"
        if pay_now_btn:
            await pay_now_btn.click()
            await asyncio.sleep(1.5)
            return "✅ Selected 'Pay now'"

        return "ℹ️ No payment choice dialog; proceeded to checkout"

    except Exception as e:
        logger.error(f"Reserve room error: {e}")
        return f"❌ Error reserving room: {str(e)}"


# ============================================================================
# GUEST INFO & PAYMENT
# ============================================================================

@expedia_hotel_prebuilt.action('Fill guest information on checkout')
async def fill_guest_info(
    browser_session: BrowserSession,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
) -> str:
    try:
        page = await browser_session.get_current_page()
        await asyncio.sleep(1.5)

        # First name
        await page.wait_for_selector('input[data-stid*="traveler:name:first_name"]', state='visible', timeout=10000)
        await page.fill('input[data-stid*="traveler:name:first_name"]', first_name)
        await asyncio.sleep(0.2)

        # Last name
        await page.fill('input[data-stid*="traveler:name:last_name"]', last_name)
        await asyncio.sleep(0.2)

        # Email
        await page.fill('input[data-stid*="contact:email"]', email)
        await asyncio.sleep(0.2)

        # Phone
        await page.fill('input[data-stid*="contact:phone:number"]', phone)
        await asyncio.sleep(0.2)

        return "✅ Guest information filled"

    except Exception as e:
        logger.error(f"Guest info error: {e}")
        return f"❌ Error filling guest info: {str(e)}"


@expedia_hotel_prebuilt.action('Fill hotel payment form')
async def fill_hotel_payment(
    browser_session: BrowserSession,
    card_number: str,
    exp_mmYY: str,  # e.g., "1227"
    cvv: str,
    zip_code: str,
) -> str:
    try:
        page = await browser_session.get_current_page()

        # Scroll to payment area
        await asyncio.sleep(2)
        await page.evaluate("window.scrollBy(0, 600)")
        await asyncio.sleep(1)
        await page.evaluate(
            """() => {
                const headings = Array.from(document.querySelectorAll('h2, h3, h4'));
                const cardHeading = headings.find(h => h.textContent?.includes('card details') || h.textContent?.includes('Card details'));
                if (cardHeading) { cardHeading.scrollIntoView({behavior: 'smooth', block: 'start'}); return; }
                const cardField = document.querySelector('input#payment_credit_card');
                if (cardField) { cardField.scrollIntoView({behavior: 'smooth', block: 'center'}); }
            }"""
        )
        await asyncio.sleep(1.5)

        # Card number
        card_locator = page.locator('input#payment_credit_card').first()
        await card_locator.wait_for(state='visible', timeout=10000)
        await card_locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)
        await card_locator.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type(card_number)
        await asyncio.sleep(0.2)

        # Expiry
        expiry_locator = page.locator('input#expiry')
        await expiry_locator.wait_for(state='visible', timeout=10000)
        await expiry_locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)
        await expiry_locator.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type(exp_mmYY)
        await asyncio.sleep(0.2)

        # CVV
        cvv_locator = page.locator('input#payment_cvv_code')
        await cvv_locator.wait_for(state='visible', timeout=10000)
        await cvv_locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)
        await cvv_locator.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type(cvv)
        await asyncio.sleep(0.2)

        # ZIP
        zip_locator = page.locator('input#payment_zip_code')
        await zip_locator.wait_for(state='visible', timeout=10000)
        await zip_locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)
        await zip_locator.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type(zip_code)
        await asyncio.sleep(0.2)

        return "✅ Hotel payment filled"

    except Exception as e:
        logger.error(f"Hotel payment error: {e}")
        return f"❌ Error filling hotel payment: {str(e)}"


# ============================================================================
# PROTECTION & FINAL BUTTON
# ============================================================================

@expedia_hotel_prebuilt.action('Decline hotel protection')
async def decline_protection(browser_session: BrowserSession) -> str:
    try:
        page = await browser_session.get_current_page()

        await page.evaluate("""() => {
            const protectionRadio = document.querySelector('input[type="radio"][name="offers"][value="-1"]');
            if (protectionRadio) protectionRadio.scrollIntoView({behavior: 'smooth', block: 'center'});
        }""")
        await asyncio.sleep(1)

        await page.wait_for_selector('input[type="radio"][name="offers"][value="-1"]', state='visible', timeout=10000)
        await page.click('input[type="radio"][name="offers"][value="-1"]')
        await asyncio.sleep(0.5)
        return "✅ Declined protection"

    except Exception as e:
        logger.error(f"Decline protection error: {e}")
        return f"❌ Error declining protection: {str(e)}"


@expedia_hotel_prebuilt.action('Verify Book now button (DO NOT CLICK)')
async def verify_book_now(browser_session: BrowserSession) -> str:
    try:
        page = await browser_session.get_current_page()

        await page.evaluate("""() => {
            const bookBtn = document.querySelector('button#complete-booking[data-testid="book-button"]');
            if (bookBtn) bookBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
        }""")
        await asyncio.sleep(1)

        await page.wait_for_selector('button#complete-booking[data-testid="book-button"]', state='visible', timeout=10000)
        return "✅ 'Book now' button visible (NOT clicked)"

    except Exception as e:
        logger.error(f"Verify book now error: {e}")
        return f"❌ Error verifying book now: {str(e)}"


# ============================================================================
# END-TO-END FLOW
# ============================================================================

@expedia_hotel_prebuilt.action('Complete hotel booking flow (no submission)')
async def complete_hotel_booking(
    browser_session: BrowserSession,
    destination: str,
    check_in: str,
    check_out: str,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    card_number: str,
    exp_mmYY: str,
    cvv: str,
    zip_code: str,
    adults: int = 2,
    rooms: int = 1,
    login_email: Optional[str] = None,
) -> str:
    steps = []
    try:
        steps.append(await ensure_signed_in(browser_session, login_email))
        steps.append(await search_hotels(browser_session, destination, check_in, check_out, adults, rooms))
        steps.append(await open_first_hotel_details(browser_session))
        steps.append(await click_select_a_room(browser_session))
        steps.append(await reserve_room(browser_session))
        steps.append(await fill_guest_info(browser_session, first_name, last_name, email, phone))
        steps.append(await fill_hotel_payment(browser_session, card_number, exp_mmYY, cvv, zip_code))
        steps.append(await decline_protection(browser_session))
        steps.append(await verify_book_now(browser_session))
        return "\n".join(steps)
    except Exception as e:
        logger.error(f"Hotel booking flow error: {e}")
        return f"❌ Error in hotel booking flow: {str(e)}"


__all__ = [
    'expedia_hotel_prebuilt'
]


