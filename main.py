import agentmail
from fastapi import FastAPI, Request
from agentmail import AgentMail
from cfg import settings
from pydantic import BaseModel
from typing import Any

app = FastAPI()

agentmail_client = AgentMail(api_key=settings.agentmail_api_key)

# todo: rename me
class SomeSchema(BaseModel):
    ctx: dict[str, Any]


@app.post()


@app.post("/webhooks/store-ctx")
async def store_ctx(request: Request):
    # store ctx in hyperspell
    pass


# need to expose tools for stripe payment and agentmail
@app.post("/api/payment")
async def payment(request: Request):
    pass



@app.post("webhooks/create-email")
async def create_email(request: Request):
    agentmail_client.inboxes.create()

    return {"message": "Email created"}





def main():
    print("Hello from yc-agentmail!")


if __name__ == "__main__":
    main()
