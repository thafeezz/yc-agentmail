from langchain_core.messages.tool import ToolOutputMixin
from cfg import USER_TO_RESOURCE
from langchain.agents import create_agent
from langchain.tools import tool
from typing import Any
from clients import hyperspell_client, agentmail_client
from prompts import PERSONA_PROMPT

@tool
def agentmail_create_inbox(ctx: dict[str, Any]) -> str:
    response = agentmail_client.inboxes.create()

    return "Successfully created inbox: " + response

@tool
def agentmail_read_inbox(ctx: dict[str, Any]) -> str:
    response = agentmail_client.inboxes.messages.list(
        inbox_id=ctx.inbox_id,
    )
    return "Successfully read inbox: " + response

@tool
def agentmail_send_message(ctx: dict[str, Any]) -> str:
    response = agentmail_client.inboxes.messages.send(
        inbox_id=ctx.inbox_id,
        to=ctx.to,
        subject=ctx.subject,
        html=ctx.html,
        text=ctx.text
    )
    return "Successfully sent message: " + response

@tool
def hyperspell(agent_query: str) -> str:
    # todo: get memories
    memories = hyperspell_client.memories.search(
        query=agent_query,
    )
    return str(memories)




    

        