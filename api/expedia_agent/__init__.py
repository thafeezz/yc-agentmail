"""
Expedia Agent Module

Browser automation and booking tools for Expedia travel services.

Components:
- agent_browser.py: Main browser agent (ExpediaAgent) for login, search, booking
- expedia_prebuilt_actions.py: High-level prebuilt actions for browser-use integration
- expedia_flight_tools.py: Flight-specific tools and selectors
- expedia_hotel_prebuilt_actions.py: Hotel-specific tools and actions
- test_prebuilt_actions.py: Test suite for prebuilt actions
"""

from .agent_browser import ExpediaAgent, initialize_observability

__all__ = [
    "ExpediaAgent",
    "initialize_observability",
]

__version__ = "1.0.0"
