import agentmail
from fastapi import FastAPI, Request
from agentmail import AgentMail
from cfg import settings
from pydantic import BaseModel
from typing import Any
from clients import hyperspell_client, agentmail_client
from cfg import USER_TO_RESOURCE
from agent import PersonaAgent

app = FastAPI()

# todo: rename me
class Context(BaseModel):
    transcript: dict[str, Any]
    user_id: str


# invoked after onboarding completed with context of conversation
@app.post("/webhooks/store-ctx")
async def store_ctx(ctx: Context):
    # store ctx in hyperspell
    response = hyperspell_client.memories.add(text=ctx.transcript, collection=ctx.user_id)
    USER_TO_RESOURCE[ctx.user_id] = response.resource_id

    # create an agent for this persona/user
    persona_agent = PersonaAgent(user_id=ctx.user_id)
    # invoked some kind of run loop or callback for the agent
    persona_agent.invoke()


@app.post("webhooks/create-email")
async def create_email(request: Request):
    agentmail_client.inboxes.create()

    return {"message": "Email created"}





def main():
    print("Hello from yc-agentmail!")


if __name__ == "__main__":
    main()
