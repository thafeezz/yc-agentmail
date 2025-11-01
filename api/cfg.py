from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Required for email integration
    agentmail_api_key: Optional[str] = None
    agent_mail_api_key: Optional[str] = None  # Alternative naming
    
    # Required for memory/context storage
    hyperspell_api_key: Optional[str] = None
    
    # Browser automation
    browser_use_api_key: Optional[str] = None
    
    # LLM providers
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    
    # Search providers
    perplexity_api_key: Optional[str] = None
    
    # Webhook configuration
    webhook_base_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env

settings = Settings()


# user_id -> resource_id
USER_TO_RESOURCE = {}