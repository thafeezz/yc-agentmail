from langchain_core.messages.tool import ToolOutputMixin
from .cfg import USER_TO_RESOURCE
from langchain.tools import tool
from typing import Any
from .clients import hyperspell_client, agentmail_client
from .prompts import PERSONA_PROMPT

# Import Perplexity tools if available
try:
    from .perplexity_tools import (
        search_travel_destinations,
        search_multiple_travel_topics,
        search_local_travel_info
    )
    PERPLEXITY_TOOLS_AVAILABLE = True
except ImportError:
    PERPLEXITY_TOOLS_AVAILABLE = False

@tool
def agentmail_create_inbox(ctx: dict[str, Any]) -> str:
    """Create a new AgentMail inbox for receiving emails.
    
    Returns:
        str: Confirmation message with the created inbox details.
    """
    response = agentmail_client.inboxes.create()
    return "Successfully created inbox: " + response

@tool
def agentmail_read_inbox(inbox_id: str, limit: int = 20) -> str:
    """Read ALL messages from an AgentMail inbox including spam/junk folder to find verification codes or OTP.
    Returns complete message content for LLM to analyze.
    
    Args:
        inbox_id: The AgentMail inbox ID to read from (email address format)
        limit: Maximum number of messages to return (default: 20)
        
    Returns:
        str: Complete message content including body, subject, sender for ALL folders including junk/spam.
    """
    from api.agentmail_helper import get_inbox_messages
    
    messages = get_inbox_messages(inbox_id, limit)
    
    if not messages:
        return f"❌ No messages found in inbox {inbox_id}. The inbox may be empty or emails are still being delivered. Wait 5-10 seconds and try again."
    
    result = f"📬 Found {len(messages)} message(s) in {inbox_id} (including spam/junk):\n\n"
    result += "="*80 + "\n\n"
    
    for i, msg in enumerate(messages, 1):
        result += f"MESSAGE #{i}:\n"
        result += f"From: {msg['from']}\n"
        result += f"Subject: {msg['subject']}\n"
        result += f"Received: {msg['received_at']}\n"
        result += f"\nFULL MESSAGE BODY:\n{'-'*40}\n"
        
        # Include FULL body - let LLM extract OTP
        body = msg.get('body', '')
        result += f"{body}\n"
        result += f"{'-'*40}\n\n"
    
    result += "="*80 + "\n"
    result += f"✅ All {len(messages)} messages shown above. Look for verification codes, OTP, or passcodes in the message bodies.\n"
    
    return result

@tool
def agentmail_send_message(ctx: dict[str, Any]) -> str:
    """Send an email message through AgentMail.
    
    Args:
        ctx: Context dictionary containing inbox_id, to, subject, html, and text.
        
    Returns:
        str: Confirmation message with send status.
    """
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
    """Search for relevant memories using HyperSpell.
    
    Args:
        agent_query: Natural language query to search memories.
        
    Returns:
        str: Retrieved memories matching the query.
    """
    # todo: get memories
    memories = hyperspell_client.memories.search(
        query=agent_query,
    )
    return str(memories)


def create_user_hyperspell_tool(user_id: str, user_name: str):
    """
    Create a HyperSpell search tool scoped to a specific user's memories.
    
    Args:
        user_id: User ID for scoping memory search
        user_name: User's display name for tool description
    
    Returns:
        LangChain tool for searching this user's memories
    """
    @tool
    def search_user_memories(query: str) -> str:
        f"""Search {user_name}'s travel memories and preferences.
        
        Use this to recall {user_name}'s past travel experiences, preferences, 
        constraints, or any context from their onboarding conversation.
        
        Args:
            query: Natural language query about {user_name}'s memories
            
        Returns:
            str: Relevant memories and preferences for {user_name}
            
        Examples:
            - "What destinations does {user_name} prefer?"
            - "Does {user_name} have any dietary restrictions?"
            - "What was {user_name}'s previous travel budget?"
        """
        if not hyperspell_client:
            return f"HyperSpell not available. Cannot search {user_name}'s memories."
        
        try:
            # Search memories in user's collection
            memories = hyperspell_client.memories.search(
                query=query,
                collection=user_id
            )
            
            if not memories or not hasattr(memories, 'results') or not memories.results:
                return f"No relevant memories found for {user_name} matching: {query}"
            
            # Format memories for agent consumption
            result = f"Memories for {user_name}:\n\n"
            for i, memory in enumerate(memories.results[:5], 1):  # Top 5 results
                content = memory.text if hasattr(memory, 'text') else str(memory)
                score = memory.score if hasattr(memory, 'score') else 'N/A'
                result += f"{i}. [Relevance: {score}]\n{content}\n\n"
            
            return result
            
        except Exception as e:
            return f"Error searching {user_name}'s memories: {str(e)}"
    
    # Set proper metadata
    search_user_memories.name = f"search_{user_name.lower().replace(' ', '_')}_memories"
    search_user_memories.__name__ = search_user_memories.name
    
    return search_user_memories


@tool
def search_travel_info(query: str, max_results: int = 5) -> str:
    """Search for travel information using Perplexity.
    
    Use this to research destinations, activities, hotels, flights, travel tips,
    current travel conditions, visa requirements, or any travel-related information.
    
    Args:
        query: Travel-related search query (e.g., "best hotels in Paris", 
               "visa requirements for Japan", "things to do in Bali")
        max_results: Maximum number of results to return (1-10, default: 5)
        
    Returns:
        str: Search results with titles, URLs, and snippets
        
    Examples:
        - "affordable hotels in Tokyo with good reviews"
        - "best time to visit Santorini Greece"
        - "family-friendly activities in Orlando Florida"
        - "budget travel tips for Southeast Asia"
    """
    if not PERPLEXITY_TOOLS_AVAILABLE:
        return "Perplexity search not available. Please install the perplexity package."
    
    try:
        from api.clients import perplexity_client
        
        if not perplexity_client:
            return "Perplexity API key not configured. Set PERPLEXITY_API_KEY in environment."
        
        # Perform search
        search_result = perplexity_client.search.create(
            query=query,
            max_results=min(max_results, 10),
            return_images=False,
            return_snippets=True
        )
        
        if not search_result.results:
            return f"No results found for: {query}"
        
        # Format results
        result = f"Travel Search Results for: {query}\n"
        result += f"Found {len(search_result.results)} results\n"
        result += "=" * 80 + "\n\n"
        
        for i, res in enumerate(search_result.results, 1):
            result += f"{i}. {res.title}\n"
            result += f"   URL: {res.url}\n"
            
            if hasattr(res, 'snippet') and res.snippet:
                result += f"   {res.snippet}\n"
            
            result += "\n"
        
        return result
        
    except Exception as e:
        return f"Error performing travel search: {str(e)}"


# Export all tools
def get_all_tools():
    """Get all available tools including Perplexity tools if configured."""
    base_tools = [
        agentmail_create_inbox,
        agentmail_read_inbox,
        agentmail_send_message,
        hyperspell,
    ]
    
    if PERPLEXITY_TOOLS_AVAILABLE:
        base_tools.extend([
            search_travel_destinations,
            search_multiple_travel_topics,
            search_local_travel_info,
            search_travel_info,
        ])
    
    return base_tools


def get_group_chat_tools(user_id: str, user_name: str):
    """
    Get tools for a group chat agent representing a specific user.
    
    Args:
        user_id: User ID for memory scoping
        user_name: User's display name
    
    Returns:
        List of tools including user-specific memory search and travel search
    """
    tools = []
    
    # Add user-specific HyperSpell tool
    if hyperspell_client:
        user_memory_tool = create_user_hyperspell_tool(user_id, user_name)
        tools.append(user_memory_tool)
    
    # Add Perplexity travel search
    if PERPLEXITY_TOOLS_AVAILABLE and perplexity_client:
        tools.append(search_travel_info)
    
    return tools
