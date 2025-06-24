# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Development
```bash
# Setup and install
uv sync                           # Install dependencies
uv run pip install -e .          # Install package in editable mode

# Run development server
uv run langgraph dev             # Start LangGraph server with Studio UI

# Testing
make test                        # Run unit tests
make integration_tests           # Run integration tests
make test TEST_FILE=path/to/test # Run specific test file
make test_watch                  # Watch mode for tests
make extended_tests              # Run extended tests only

# Code quality
make lint                        # Run ruff + mypy
make format                      # Auto-format with ruff
make lint_package                # Lint src/ only
make lint_tests                  # Lint tests/ only
```

### Testing Individual Components
```bash
# Run specific test
uv run pytest tests/unit_tests/test_graph.py::test_specific_function

# Run with verbose output
uv run pytest -v tests/integration_tests/

# Run with LangSmith tracing
LANGSMITH_TRACING=true uv run pytest tests/integration_tests/
```

## Architecture Overview

This is a LangGraph agent template that implements a state-based graph processing system. The core architecture consists of:

### Core Graph System (`src/agent/graph.py`)
- **State Management**: Uses `@dataclass` for type-safe state handling
- **Configuration**: Runtime parameters via `TypedDict` that can be set at assistant creation or invocation
- **Graph Definition**: Declarative graph using `StateGraph` with nodes and edges
- **Entry Point**: Exports compiled `graph` object referenced in `langgraph.json`

### Alternative Implementation (`src/agent/premade.py`)
- Pre-built agent using `create_react_agent` with OpenAI
- Example of tool integration and multi-agent setup
- Useful reference for extending the main graph

### LangGraph Server Integration
- `langgraph.json` maps the graph path for server hosting
- Studio UI provides visual debugging at http://localhost:8123
- Hot reload enabled for development
- Thread management for stateful conversations

## Key Development Patterns

### Adding New Nodes
When extending the graph, follow this pattern:
```python
async def new_node(state: State, config: RunnableConfig) -> Dict[str, Any]:
    configuration = config["configurable"]
    # Process state and return updates
    return {"field_to_update": new_value}

# Add to graph
graph_builder.add_node("new_node", new_node)
graph_builder.add_edge("existing_node", "new_node")
```

### State Extensions
Extend the State dataclass for new fields:
```python
@dataclass
class State:
    existing_field: str = "default"
    new_field: List[str] = field(default_factory=list)  # For mutable defaults
```

### Configuration Parameters
Add runtime configurables to the Configuration TypedDict:
```python
class Configuration(TypedDict):
    my_configurable_param: str
    new_param: Optional[int]  # Optional parameters
```

## Creating/Updating Architecture Diagrams

To create or update architecture diagrams for the README:

1. Create a Python script that uses matplotlib to generate the diagram:
   ```python
   import matplotlib.pyplot as plt
   import matplotlib.patches as patches
   from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
   ```

2. Set dark theme colors:
   - Background: #1a1a1a
   - Boxes: #2d2d2d
   - Text: #e0e0e0
   - Arrows: #4a9eff
   - Groups: #252525

3. Use helper functions to create boxes and arrows
4. Save as PNG with: `plt.savefig('static/architecture.png', dpi=300, facecolor=bg_color)`
5. Reference in README as: `![Architecture](./static/architecture.png)`

Note: System Python has matplotlib installed, use `python script.py` directly instead of `uv run python`.