from cfg import USER_TO_RESOURCE
from langchain.agents import create_agent
from langchain.tools import tool
from typing import Any
from clients import hyperspell_client
from prompts import PERSONA_PROMPT

# define tools for persona agent
# 1. agentmail for discussions
# 2. stripe for payments

@tool
def agentmail(ctx: dict[str, Any]) -> str:
    # todo: implement agentmail tool
    pass

@tool
def stripe(ctx: dict[str, Any]) -> str:
    # todo: implement stripe tool
    pass

@tool
def hyperspell(agent_query: str) -> str:
    # todo: get memories
    memories = hyperspell_client.memories.search(
        query=agent_query,
    )
    return str(memories)


class PersonaAgent():
    def __init__(self, user_id: str):
        resource_id = USER_TO_RESOURCE[user_id]

        memories = hyperspell_client.memories.list(collection=user_id, source="collections")
        
        # todo shove memories into context
        self.agent = create_agent(
                        system_prompt=PERSONA_PROMPT,
                        tools=[agentmail, stripe, hyperspell])

    # todo: add async invoke/callback or run loop for the agent
    def invoke(self) -> str:
        while True:
            # debate with user

    def chat_
        

    

        