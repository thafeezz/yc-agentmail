"""
YC AgentMail API Package

Complete API implementation including:
- Expedia agent for flight and hotel bookings
- Group chat orchestration for travel planning
- Integration with AgentMail and HyperSpell
"""

from .agent_service import app
from . import agentmail_helper

__all__ = ["app", "agentmail_helper"]
