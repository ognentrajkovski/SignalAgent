import os
import random
from typing import TypedDict, Annotated, Sequence
import operator
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
import google.generativeai as genai
from api.db import SessionLocal, AgentAction

class LeadAgentState(TypedDict):
    lead_id: int
    person_id: str
    messages: Annotated[Sequence[BaseMessage], operator.add]
    actions_taken: Annotated[Sequence[str], operator.add]

def mock_reply_prediction(lead_id: int, action: str) -> float:
    # A mock stub as requested by the prompt
    return round(random.uniform(0.01, 0.4), 2)

def llm_node(state: LeadAgentState):
    """
    Calls Gemini to decide the next action based on memory.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"messages": [AIMessage(content="Wait: Missing API key")]}
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # Reconstruct conversation
    history = []
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            history.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            history.append(f"Agent: {msg.content}")
            
    prompt = f"""
    You are a Lead Engagement Agent. Your goal is to engage a B2B lead.
    You have the following actions available:
    - like_post
    - draft_connection_request
    - send_email
    - wait
    
    Previous actions taken: {state.get('actions_taken', [])}
    
    Choose exactly one next action from the list above.
    Format your response as:
    ACTION: <action_name>
    RATIONALE: <your reasoning>
    """
    
    response = model.generate_content(prompt)
    return {"messages": [AIMessage(content=response.text)]}

def execute_node(state: LeadAgentState):
    """
    Parses the LLM's chosen action, calls the mock reply prediction,
    and commits the action to the DB.
    """
    last_msg = state["messages"][-1].content
    
    action = "wait"
    rationale = "Default fallback"
    
    # Parse the LLM output
    for line in last_msg.split("\n"):
        if line.startswith("ACTION:"):
            action = line.replace("ACTION:", "").strip()
        elif line.startswith("RATIONALE:"):
            rationale = line.replace("RATIONALE:", "").strip()
            
    # Stub reply prediction
    prob = mock_reply_prediction(state["lead_id"], action)
    rationale += f" (Reply probability: {prob})"
    
    # Commit to DB
    db = SessionLocal()
    try:
        new_action = AgentAction(
            lead_id=state["lead_id"],
            action_type=action,
            rationale=rationale
        )
        db.add(new_action)
        db.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        db.close()
        
    return {"actions_taken": [action]}

def should_continue(state: LeadAgentState):
    # Stop if we sent an email, otherwise we could loop up to a max (enforced outside)
    actions = state.get("actions_taken", [])
    if "send_email" in actions or len(actions) >= 3:
        return END
    return "execute"

def build_lead_graph():
    workflow = StateGraph(LeadAgentState)
    
    workflow.add_node("agent", llm_node)
    workflow.add_node("execute", execute_node)
    
    workflow.set_entry_point("agent")
    
    workflow.add_edge("agent", "execute")
    workflow.add_conditional_edges("execute", should_continue, {
        END: END,
        "execute": "agent"  # Loop back for next action
    })
    
    return workflow.compile()

graph = build_lead_graph()

def run_lead_agent(lead_id: int, person_id: str):
    """
    Runs the agent for a given lead.
    """
    initial_state = {
        "lead_id": lead_id,
        "person_id": person_id,
        "messages": [HumanMessage(content="Start engagement.")],
        "actions_taken": []
    }
    
    final_state = graph.invoke(initial_state)
    return final_state
