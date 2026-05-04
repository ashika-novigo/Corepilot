from langgraph.graph import StateGraph
from typing import TypedDict

from ai.agents.router_agent import route_query
from ai.agents.hr_agent import hr_agent

# 🧠 Define state

class GraphState(TypedDict):
    message: str
    agent: str
    response: str
    db: object

# 🧠 Router node

def router_node(state: GraphState):
    agent = route_query(state["message"])
    return {"agent": agent}

# 🧠 HR node

def hr_node(state: GraphState):
    response = hr_agent(state["message"], state["db"])
    return {"response": response}

# 🧠 Build graph

def build_graph():
    builder = StateGraph(GraphState)
    
    
    builder.add_node("router", router_node)
    builder.add_node("hr", hr_node)
    
    # Entry
    builder.set_entry_point("router")
    
    # Conditional routing
    def route(state: GraphState):
        return state["agent"]
    
    builder.add_conditional_edges(
        "router",
        route,
        {
            "hr": "hr",
            "general": "__end__"
        }
    )
    
    builder.set_finish_point("hr")
    
    return builder.compile()

