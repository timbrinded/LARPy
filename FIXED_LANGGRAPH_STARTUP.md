# Fixed LangGraph Startup Issue

## Problem
The LangGraph server wouldn't start due to import errors:
```
ImportError: attempted relative import with no known parent package
```

## Solution
Created a single entry point file `graphs.py` that uses absolute imports to expose the graphs to LangGraph.

## Files Created:
1. **graphs.py** - Entry point with absolute imports:
```python
"""Entry point for LangGraph graphs with absolute imports."""

from src.dexter.agent_graph import graph as agent_graph
from src.dexter.premade import graph as react_graph

# Export graphs
agent = agent_graph
react = react_graph
```

## Files Modified:
1. **langgraph.json** - Updated to use the new entry point:
```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./graphs.py:agent",
    "react": "./graphs.py:react"
  },
  "env": ".env",
  "image_distro": "wolfi"
}
```

2. **src/dexter/__init__.py** - Fixed relative import:
```python
from .premade import graph as react_graph
```

## Result
The server now starts successfully:
- API: http://127.0.0.1:2024
- Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- Both graphs registered: 'agent' and 'react'

## To Start the Server:
```bash
uv run langgraph dev
```

The server is now running and you can access the Studio UI to interact with the agents.