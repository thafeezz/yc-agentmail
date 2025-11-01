from .cfg import settings
from hyperspell import Hyperspell
from agentmail import AgentMail

# Use agent_mail_api_key if agentmail_api_key is not set
agentmail_key = settings.agentmail_api_key or settings.agent_mail_api_key
agentmail_client = AgentMail(api_key=agentmail_key) if agentmail_key else None

hyperspell_client = Hyperspell(api_key=settings.hyperspell_api_key) if settings.hyperspell_api_key else None

# Initialize Perplexity client
try:
    from perplexity import Perplexity
    perplexity_client = Perplexity(api_key=settings.perplexity_api_key) if settings.perplexity_api_key else None
except ImportError:
    perplexity_client = None