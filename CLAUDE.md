# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important: UV Package Manager

This project uses **UV** exclusively for package management - it is a complete replacement for pip written in Rust that offers 8-100x faster performance. **Do not use pip commands** in this repository.

Key UV commands:
- `uv sync` - Install all dependencies from pyproject.toml
- `uv add <package>` - Install a specific package
- `uv run <command>` - Run a command in the project environment

## Development Commands

### Core Development
```bash
# Setup and install
uv sync                           # Install dependencies (NOT pip install)

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

LARPy is a LangGraph agent that implements a state-based graph processing system for Ethereum arbitrage. The core architecture consists of:

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

## Configuration System

The project now uses a formalized configuration system with Pydantic models and YAML files:

### Configuration Structure
```
configs/
├── chains.yaml        # Blockchain network configurations (RPC URLs, chain IDs)
├── tokens.yaml        # Token addresses, symbols, and decimals
├── dexes.yaml        # DEX pools, contracts, and ABIs
├── arbitrage.yaml     # Arbitrage strategy parameters
└── models.yaml        # LLM model configurations
```

### Using Configuration in Code
```python
from agent.config_loader import get_config, get_config_loader

# Get full configuration
config = get_config()
rpc_url = config.default_chain.rpc_url

# Get specific token address
loader = get_config_loader()
weth_address = loader.get_token_address("WETH")

# Find a specific pool
pool = loader.get_pool("uniswap_v3", "WETH", "USDC", fee=3000)
```

### Configuration Models (`src/agent/config_models.py`)
- `ChainConfig` - Blockchain network settings
- `TokenConfig` - Token metadata
- `PoolConfig` - DEX pool configurations
- `ContractConfig` - Smart contract addresses and ABIs
- `DexConfig` - DEX-specific settings
- `ArbitrageConfig` - Trading parameters
- `ModelConfig` - LLM settings

### Adding New Configurations
1. Update the appropriate YAML file in `configs/`
2. The configuration loader automatically validates against Pydantic models
3. Access via `get_config()` or specific helper methods

### Example: Adding a New Chain
```yaml
# In configs/chains.yaml
polygon:
  name: "Polygon"
  chain_id: 137
  rpc_url: "https://polygon-rpc.com"
  explorer_url: "https://polygonscan.com"
  native_token: "MATIC"
  block_time: 2.0
```