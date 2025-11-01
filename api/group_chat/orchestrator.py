"""
LangGraph Multi-Agent Orchestrator
StateGraph-based system for orchestrating multiple user agents in group chat.
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

# Import both LLM providers
try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

if not ANTHROPIC_AVAILABLE and not OPENAI_AVAILABLE:
    raise ImportError("Please install either langchain-anthropic or langchain-openai")

# Determine provider based on available API keys
def get_llm_provider():
    """Determine which LLM provider to use based on available API keys"""
    if os.getenv("OPENAI_API_KEY") and OPENAI_AVAILABLE:
        return "openai"
    elif os.getenv("ANTHROPIC_API_KEY") and ANTHROPIC_AVAILABLE:
        return "anthropic"
    elif OPENAI_AVAILABLE:
        return "openai"
    elif ANTHROPIC_AVAILABLE:
        return "anthropic"
    else:
        raise ValueError("No LLM provider available")

from .models import (
    GroupChatState,
    UserProfile,
    TravelPlan,
    TravelDates,
    FlightDetails,
    HotelDetails,
    BudgetBreakdown,
    TravelPreferences
)


class GroupChatOrchestrator:
    """
    Orchestrates multi-agent group chat for collaborative travel planning.
    Uses LangGraph's StateGraph with supervisor pattern.
    """
    
    def __init__(
        self,
        users: List[UserProfile],
        messages_per_volley: int = 10,
        llm_model: str = "claude-sonnet-4"
    ):
        """
        Initialize the orchestrator with user agents.
        
        Args:
            users: List of UserProfile objects representing participants
            messages_per_volley: Number of messages each agent sends per volley
            llm_model: LLM model to use
        """
        self.users = users
        self.user_ids = [user.user_id for user in users]
        self.messages_per_volley = messages_per_volley
        self.llm_model = llm_model
        
        # Determine which LLM provider to use
        llm_provider = get_llm_provider()
        
        # Initialize LLM
        if llm_provider == "anthropic":
            self.llm = ChatAnthropic(
                model=llm_model,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=0.7
            )
            print(f"🤖 Using Anthropic Claude")
        else:
            self.llm = ChatOpenAI(
                model=llm_model,
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.7
            )
            print(f"🤖 Using OpenAI GPT")
        
        # Build the graph
        self.graph = self._build_graph()
        
        print(f"🎭 GroupChatOrchestrator initialized")
        print(f"   Participants: {[u.user_name for u in users]}")
        print(f"   Messages per volley: {messages_per_volley}")
        print(f"   LLM: {llm_model}")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph with all nodes and edges"""
        
        # Create StateGraph with TypedDict state
        builder = StateGraph(GroupChatState)
        
        # Add agent nodes for each user
        for user in self.users:
            builder.add_node(
                f"agent_{user.user_id}",
                self._create_agent_node(user)
            )
        
        # Add master planner node
        builder.add_node("master_planner", self._master_planner_node)
        
        # Define routing function for conditional edges
        def route_supervisor(state: GroupChatState) -> str:
            """Route to next agent or master planner"""
            total_turns = state.get("total_turns", 0)
            expected_turns = len(self.user_ids) * self.messages_per_volley
            
            print(f"🔍 Router: total_turns={total_turns}, expected={expected_turns}")
            
            if total_turns >= expected_turns:
                print("🎯 Routing to Master Planner...")
                return "master_planner"
            
            # Get next agent in sequential order
            current_idx = state.get("current_agent_index", 0)
            next_agent_user_id = self.user_ids[current_idx % len(self.user_ids)]
            print(f"👉 Routing to agent_{next_agent_user_id}")
            return f"agent_{next_agent_user_id}"
        
        # Set entry point to first agent via router
        builder.add_conditional_edges(
            START,
            route_supervisor
        )
        
        # Agents return via router after speaking
        for user in self.users:
            builder.add_conditional_edges(
                f"agent_{user.user_id}",
                route_supervisor
            )
        
        # Master planner ends the flow
        builder.add_edge("master_planner", END)
        
        # Compile the graph
        return builder.compile()
    
    
    def _create_agent_node(self, user: UserProfile):
        """
        Factory method to create an agent node for a specific user.
        Returns a function that can be added as a node.
        """
        def agent_node(state: GroupChatState) -> Dict[str, Any]:
            """Agent node - generates message for user in group chat"""
            
            # Check if this is the first agent in first volley
            is_first = (state.get("total_turns", 0) == 0)
            
            # Build context from user memories
            memories_text = "\n".join([
                f"- {m.content}" for m in user.memories
            ]) if user.memories else "No specific memories recorded"
            
            # Get current plan if exists
            current_plan_text = "None yet"
            if state.get("current_plan"):
                current_plan_text = json.dumps(state["current_plan"], indent=2)
            
            # Get chat history
            messages = state.get("messages", [])
            history_text = "\n".join([
                f"{msg.name}: {msg.content}" if hasattr(msg, 'name') else f"Unknown: {msg.content}"
                for msg in messages[-20:]  # Last 20 messages for context
            ]) if messages else "No messages yet"
            
            # Build system prompt based on role
            if is_first:
                system_prompt = f"""You are an AI travel planning agent representing {user.user_name}.

You are the FIRST agent in this group chat. Your role is to CREATE AN INITIAL TRAVEL PLAN PROPOSAL.

User Profile:
- Budget Range: ${user.preferences.budget_range[0]} - ${user.preferences.budget_range[1]}
- Travel Style: {user.preferences.travel_style}
- Preferred Destinations: {', '.join(user.preferences.preferred_destinations) if user.preferences.preferred_destinations else 'flexible'}
- Dietary Restrictions: {', '.join(user.preferences.dietary_restrictions) if user.preferences.dietary_restrictions else 'none'}

User Memories:
{memories_text}

Create an initial plan proposal that includes:
- Suggested dates (specific dates)
- Flight details (origin, destination, preferences)
- Hotel details (location, type, amenities)
- Budget estimate
- Destination and activities

Keep your message concise (3-5 sentences). Make it collaborative and open to adjustments."""

            else:
                system_prompt = f"""You are an AI travel planning agent representing {user.user_name} in a group travel planning discussion.

Your role is to advocate for your user's preferences while being collaborative.

User Profile:
- Budget Range: ${user.preferences.budget_range[0]} - ${user.preferences.budget_range[1]}
- Travel Style: {user.preferences.travel_style}
- Preferred Destinations: {', '.join(user.preferences.preferred_destinations) if user.preferences.preferred_destinations else 'flexible'}
- Dietary Restrictions: {', '.join(user.preferences.dietary_restrictions) if user.preferences.dietary_restrictions else 'none'}

User Memories:
{memories_text}

Current Plan Being Discussed:
{current_plan_text}

Recent Chat History:
{history_text}

Provide constructive feedback:
- What works well for your user
- What needs adjustment
- Specific suggestions or alternatives
- Compromises you can make

Keep your message concise (2-4 sentences). Be collaborative but ensure your user's key needs are addressed."""
            
            # Handle rejection feedback if present
            if state.get("rejection_feedback"):
                system_prompt += f"\n\nIMPORTANT: The previous plan was rejected with this feedback:\n{state['rejection_feedback']}\n\nAddress these concerns in your response."
            
            user_prompt = "Generate your message for the group chat."
            
            # Generate response
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            message_content = response.content
            
            # Create message with agent name
            agent_message = AIMessage(
                content=message_content,
                name=user.user_name
            )
            
            # Update counts
            counts = state.get("agent_message_counts", {}).copy()
            counts[user.user_id] = counts.get(user.user_id, 0) + 1
            
            total_turns = state.get("total_turns", 0) + 1
            current_idx = state.get("current_agent_index", 0) + 1
            
            print(f"💬 {user.user_name}: {message_content[:100]}...")
            
            return {
                "messages": [agent_message],
                "agent_message_counts": counts,
                "total_turns": total_turns,
                "current_agent_index": current_idx,
                "active_agent": user.user_id
            }
        
        return agent_node
    
    def _validate_plan(self, plan: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate that plan has all required fields before sending.
        Plan cannot be submitted unless all required fields are present.
        """
        required_fields = {
            "dates": ["departure_date", "return_date"],
            "flight": ["origin", "destination"],
            "hotel": ["location", "type"],
            "budget": ["total_per_person"],
            "location": None,  # Just check existence
        }
        
        missing = []
        
        for field, subfields in required_fields.items():
            if field not in plan:
                missing.append(field)
                continue
            
            if subfields:
                for subfield in subfields:
                    if subfield not in plan[field]:
                        missing.append(f"{field}.{subfield}")
        
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        
        return True, None
    
    def _master_planner_node(self, state: GroupChatState) -> Dict[str, Any]:
        """
        Master planner node - synthesizes chat history into final TravelPlan.
        """
        print("\n" + "="*60)
        print("🎯 MASTER PLANNER - Synthesizing Final Plan")
        print("="*60)
        
        messages = state.get("messages", [])
        
        # Build context for master planner
        chat_history_text = "\n".join([
            f"{msg.name if hasattr(msg, 'name') else 'Unknown'}: {msg.content}"
            for msg in messages
        ])
        
        # Build user preferences summary
        users_summary = "\n".join([
            f"- {user.user_name} (Budget: ${user.preferences.budget_range[0]}-${user.preferences.budget_range[1]}, Style: {user.preferences.travel_style})"
            for user in self.users
        ])
        
        system_prompt = f"""You are a master travel planning AI synthesizing a group discussion into a comprehensive plan.

Participating Users:
{users_summary}

Complete Chat History:
{chat_history_text}

Create a FINAL, COMPREHENSIVE travel plan that:
1. Balances all users' preferences as much as possible
2. Makes reasonable compromises where preferences conflict
3. Includes all required details
4. Is practical and bookable

Output ONLY valid JSON matching this exact structure:
{{
  "dates": {{
    "departure_date": "YYYY-MM-DD",
    "return_date": "YYYY-MM-DD",
    "flexibility_days": 0
  }},
  "flight": {{
    "origin": "City or airport code",
    "destination": "City or airport code",
    "preferences": "Flight preferences",
    "max_budget_per_person": 500
  }},
  "hotel": {{
    "location": "Hotel location",
    "type": "hotel",
    "amenities": ["wifi", "breakfast"],
    "star_rating_min": 3,
    "max_budget_per_night": 200
  }},
  "budget": {{
    "total_per_person": 2000,
    "flight_cost": 500,
    "hotel_cost": 1000,
    "activities_cost": 300,
    "food_cost": 200
  }},
  "location": "Primary destination",
  "preferences": {{
    "activities": ["activity1", "activity2"],
    "dining": "dining preferences",
    "special_requirements": []
  }},
  "compromises_made": "Explanation of how you balanced different preferences"
}}

Respond ONLY with the JSON, no other text."""
        
        # Generate plan
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content="Synthesize the discussion into a final travel plan (JSON only).")
        ])
        
        plan_text = response.content
        
        # Parse JSON
        try:
            # Extract JSON if wrapped in markdown
            if "```json" in plan_text:
                plan_text = plan_text.split("```json")[1].split("```")[0]
            elif "```" in plan_text:
                plan_text = plan_text.split("```")[1].split("```")[0]
            
            plan_dict = json.loads(plan_text.strip())
            
            # VALIDATE PLAN - must have all required fields
            is_valid, error_msg = self._validate_plan(plan_dict)
            
            if not is_valid:
                print(f"❌ Plan validation failed: {error_msg}")
                return {
                    "current_plan": {
                        "error": "Plan validation failed",
                        "details": error_msg,
                        "status": "error"
                    },
                    "is_complete": False  # Don't complete, force retry
                }
            
            # Add metadata
            plan_dict["plan_id"] = f"plan_{uuid.uuid4().hex[:8]}"
            plan_dict["created_at"] = datetime.now().isoformat()
            plan_dict["status"] = "draft"
            plan_dict["participants"] = self.user_ids
            
            print("✅ Final plan synthesized and validated successfully!")
            print(f"   Location: {plan_dict.get('location', 'N/A')}")
            print(f"   Budget: ${plan_dict.get('budget', {}).get('total_per_person', 'N/A')} per person")
            
            return {
                "current_plan": plan_dict,
                "is_complete": True
            }
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse plan JSON: {e}")
            print(f"Raw response: {plan_text}")
            
            # Return error plan
            return {
                "current_plan": {
                    "error": "Failed to parse plan",
                    "raw_response": plan_text,
                    "plan_id": f"plan_{uuid.uuid4().hex[:8]}",
                    "status": "error"
                },
                "is_complete": True
            }
    
    def run_volley(self, initial_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run a complete volley (all agents send messages_per_volley messages).
        
        Args:
            initial_state: Optional initial state, otherwise creates fresh state
            
        Returns:
            Final state after volley completion
        """
        if initial_state is None:
            initial_state = {
                "messages": [],
                "current_volley": 0,
                "messages_per_agent": self.messages_per_volley,
                "active_agent": None,
                "agent_message_counts": {uid: 0 for uid in self.user_ids},
                "current_agent_index": 0,
                "total_turns": 0,
                "current_plan": None,
                "rejection_feedback": None,
                "is_complete": False
            }
        
        print(f"\n{'='*60}")
        print(f"🔄 Starting Volley {initial_state['current_volley'] + 1}")
        print(f"{'='*60}")
        print(f"Order: {[self.users[i].user_name for i in range(len(self.users))]}")
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        return final_state
    
    def handle_rejection(
        self,
        current_state: Dict[str, Any],
        feedback: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Handle plan rejection by adding feedback and preparing for next volley.
        
        Args:
            current_state: Current state from previous volley
            feedback: Rejection feedback
            user_id: ID of user who rejected
            
        Returns:
            Updated state ready for next volley
        """
        print(f"\n{'='*60}")
        print(f"❌ Plan Rejected by User {user_id}")
        print(f"{'='*60}")
        print(f"Feedback: {feedback}")
        
        # Add rejection as system message
        rejection_msg = SystemMessage(
            content=f"[USER {user_id} FEEDBACK] Plan rejected: {feedback}"
        )
        
        # Update state for next volley
        updated_state = current_state.copy()
        updated_state["messages"].append(rejection_msg)
        updated_state["rejection_feedback"] = feedback
        updated_state["current_volley"] += 1
        updated_state["agent_message_counts"] = {uid: 0 for uid in self.user_ids}
        updated_state["current_agent_index"] = 0
        updated_state["total_turns"] = 0
        updated_state["is_complete"] = False
        
        return updated_state

