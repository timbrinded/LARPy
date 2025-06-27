"""Entry point for LangGraph graphs with absolute imports."""

from src.dexter.agent_graph import graph as agent_graph
from src.dexter.premade import graph as react_graph

# Export graphs
agent = agent_graph
react = react_graph