from cfg import settings
from hyperspell import Hyperspell
from agentmail import AgentMail

agentmail_client = AgentMail(api_key=settings.agentmail_api_key)
hyperspell_client = Hyperspell(api_key=settings.hyperspell_api_key)