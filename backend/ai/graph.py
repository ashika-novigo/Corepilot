from langgraph.graph import StateGraph
from typing import TypedDict

from ai.agents.router_agent import route_query
from ai.agents.hr_agent import hr_agent
from ai.agents.it_agent import it_agent

# 🧠 Define state

class GraphState(TypedDict):
    message: str
    agent: str
    response: str
    db: object
    user:object

# 🧠 Router node

def router_node(state: GraphState):
    agent = route_query(state["message"])
    return {"agent": agent}

# 🧠 HR node

def hr_node(state: GraphState):
    response = hr_agent(state["message"], state["db"],state["user"])
    return {"response": response,  "agent": "hr"}

# it node
def it_node(state):
    response = it_agent(state["message"], state["db"],state["user"])
    return {"response": response,  "agent": "it"}

# 🧠 Build graph

def build_graph():
    builder = StateGraph(GraphState)
    
    
    builder.add_node("router", router_node)
    builder.add_node("hr", hr_node)
    builder.add_node("it", it_node)
    
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
            "it": "it",
            "general": "__end__"
        }
    )
    
    builder.add_edge("hr", "__end__")
    builder.add_edge("it", "__end__")
    
    return builder.compile()

