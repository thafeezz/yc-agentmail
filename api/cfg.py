from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    agentmail_api_key: str
    hyperspell_api_key: str

    
    class Config:
        env_file = ".env"

settings = Settings()


# user_id -> resource_id
USER_TO_RESOURCE = {}