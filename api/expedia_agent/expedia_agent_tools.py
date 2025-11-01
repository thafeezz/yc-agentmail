"""
Expedia Agent Tools - Combined Registry
Exports all tool registries for the ExpediaAgent to use.
"""

from browser_use.controller.registry.service import Registry
from .expedia_flight_tools import flight_tools
from .expedia_hotel_prebuilt_actions import expedia_hotel_prebuilt
from .expedia_prebuilt_actions import expedia_prebuilt

# Combine all tool registries into one
# The agent will have access to flight, hotel, and general Expedia tools
expedia_tools = Registry()

# Register all actions from flight tools
for action_name, registered_action in flight_tools.registry.actions.items():
    expedia_tools.registry.actions[action_name] = registered_action

# Register all actions from hotel prebuilt tools
for action_name, registered_action in expedia_hotel_prebuilt.registry.actions.items():
    expedia_tools.registry.actions[action_name] = registered_action

# Register all actions from general Expedia prebuilt tools
for action_name, registered_action in expedia_prebuilt.registry.actions.items():
    expedia_tools.registry.actions[action_name] = registered_action

print(f"✅ Combined {len(expedia_tools.registry.actions)} Expedia tools from all registries")

