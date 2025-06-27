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

LARPy is a LangGraph agent that implements an evaluator-optimizer pattern for Ethereum transactions. The system has been refactored from a React agent pattern to provide better validation and optimization of blockchain transactions.

### Evaluator-Optimizer Pattern
The core architecture now consists of:

1. **Integrated Graph** (`src/dexter/integrated_graph.py`) - Main entry point
   - Unified chat interface for users  
   - Routes between generation, evaluation, and optimization
   - Manages the complete transaction lifecycle
   - **Use this graph** when interacting through LangGraph Studio

2. **Evaluator Module** (`src/evaluator/`) - Core validation logic
   - `evaluator.py` - Main evaluation engine with batch processing
   - `optimizer.py` - Transaction optimization strategies
   - `validation_rules.py` - Configurable validation criteria
   - `subagents.py` - Specialized validators:
     - **GasAnalyzer**: Optimizes gas usage patterns
     - **SecurityValidator**: Checks for MEV vulnerabilities
     - **MEVInspector**: Assesses sandwich attack risks
     - **StateValidator**: Confirms expected state changes

### Key Improvements from React Pattern
- **Better validation**: Multi-criteria checks before execution
- **Automatic optimization**: Improves transactions based on feedback
- **User interaction**: Clear feedback loop for transaction approval
- **Parallel analysis**: Subagents run concurrently for faster validation

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

## Web3 and Blockchain Integration

### Agent Private Key Configuration
The project uses the `AGENT_ETH_KEY` environment variable to store the agent's private key for blockchain transactions. This key is automatically used by transaction tools when no explicit private key is provided.

**Security Note**: Never commit private keys to version control. Always use environment variables.

### Working with Blockchain Tools

#### Transaction Submission
```python
# The submit_transaction tool automatically uses AGENT_ETH_KEY if no private key is provided
result = submit_transaction(
    to_address="0x...",
    value="1000000000000000000",  # 1 ETH in wei
    data="0x..."  # Contract call data
)
```

#### Transaction Simulation
```python
# Simulate transactions before submitting using Alchemy
simulation = alchemy_simulate_asset_changes(
    to_address="0x...",
    value="1000000000000000000",
    data="0x..."
)
# Automatically derives from_address from AGENT_ETH_KEY
```

### Development with Local Fork

Use `make dev_anvil` to:
1. Fork Ethereum mainnet locally using Anvil
2. Fund the agent account (from AGENT_ETH_KEY) with:
   - 10 ETH
   - 10,000 USDC
   - 10,000 USDT
3. Start LangGraph server pointing to the local fork

This allows safe testing of arbitrage strategies without using real funds.

### Key Blockchain Tools Available

1. **Transaction Tools** (`src/dexter/tools/transactions.py`)
   - `submit_transaction` - Submit transactions to blockchain
   - `alchemy_simulate_asset_changes` - Simulate transaction effects
   - Both tools automatically use AGENT_ETH_KEY when needed

2. **Blockchain Query Tools** (`src/dexter/tools/blockchain.py`)
   - `get_eth_balance` - Check ETH balances
   - `get_token_balance` - Check ERC20 token balances
   - `get_recent_transactions` - View transaction history
   - `get_block` - Get block information
   - `eth_call` - Execute eth_call with state override support

3. **DEX Price Tools** (`src/dexter/tools/dex_prices.py`)
   - `get_token_price_1inch` - Get prices from 1inch
   - `get_token_price_uniswap_v3` - Get Uniswap V3 prices
   - `get_token_price_sushiswap` - Get SushiSwap prices
   - `get_token_price_curve` - Get Curve prices
   - `get_all_dex_prices` - Compare prices across all DEXs

4. **Arbitrage Tools** (`src/dexter/tools/arbitrage.py`)
   - `find_arbitrage_opportunities` - Analyze price differences
   - `calculate_arbitrage_profit` - Calculate potential profits
   - `find_triangular_arbitrage` - Find multi-hop opportunities

5. **Swap Encoding Tools** (`src/dexter/tools/swap_encoder.py`)
   - `encode_uniswap_v3_swap` - Properly encode Uniswap V3 swap transactions
   - `encode_sushiswap_swap` - Encode SushiSwap transactions
   - `encode_erc20_approve` - Encode token approval transactions

### Environment Variables for Blockchain

Required in `.env`:
```bash
AGENT_ETH_KEY=your_private_key_here  # Agent's private key
ALCHEMY_API_KEY=your_alchemy_key    # For RPC and simulations
ETHERSCAN_API_KEY=your_etherscan_key # For blockchain data
```

### Best Practices

1. **Always simulate before executing** - Use `alchemy_simulate_asset_changes` to preview transaction effects
2. **Check balances first** - Ensure sufficient ETH for gas and tokens for trades
3. **Use local fork for testing** - Run `make dev_anvil` for safe experimentation
4. **Monitor gas prices** - Tools automatically estimate gas, but you can override
5. **Handle errors gracefully** - All tools return structured error responses

### Common Workflows

#### Executing a DEX Swap Properly
```python
# 1. Get current prices
prices = get_all_dex_prices("ETH", "USDC", "1")

# 2. Encode the swap transaction
swap_data = encode_uniswap_v3_swap(
    token_in="ETH",
    token_out="USDC", 
    amount_in="1000000000000000000",  # 1 ETH in wei
    recipient="0xYourWalletAddress",
    fee_tier=3000  # 0.3% fee tier
)

# 3. Simulate the transaction
simulation = alchemy_simulate_asset_changes(
    to_address=swap_data["to"],
    data=swap_data["data"],
    value=swap_data["value"],
    from_address="0xYourWalletAddress"
)

# 4. If simulation successful, submit
if simulation["success"]:
    result = submit_transaction(
        to_address=swap_data["to"],
        data=swap_data["data"],
        value=swap_data["value"]
    )
```

#### Finding and Executing Arbitrage
```python
# 1. Get prices across DEXs
prices = get_all_dex_prices("WETH", "USDC", "1")

# 2. Find opportunities
opportunities = find_arbitrage_opportunities(prices)

# 3. Simulate the arbitrage transaction
simulation = alchemy_simulate_asset_changes(
    to_address=dex_router,
    data=swap_calldata
)

# 4. If profitable, execute
if simulation["profit"] > 0:
    result = submit_transaction(
        to_address=dex_router,
        data=swap_calldata
    )
```

## Important Context for Claude

When working with this Web3/blockchain project:

1. **The agent has its own Ethereum wallet** - The private key is stored in `AGENT_ETH_KEY` environment variable
2. **Transaction tools are smart** - They automatically use the agent's private key when not explicitly provided
3. **Always think about gas costs** - Every blockchain transaction costs ETH for gas
4. **Simulation is crucial** - Always simulate transactions before executing to check for errors and estimate costs
5. **Local testing is available** - Use `make dev_anvil` to test with forked mainnet and funded accounts

### Special Address Convention: 0xYourWalletAddress

When users ask about "their wallet" or "my wallet", use the special address `0xYourWalletAddress`. The blockchain tools will automatically resolve this to the agent's actual address from the AGENT_ETH_KEY environment variable.

Examples:
- User: "What's my balance?" → Use: `get_eth_balance("0xYourWalletAddress")`
- User: "Check my USDC" → Use: `get_token_balance("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "0xYourWalletAddress")`
- User: "Send from my wallet" → The transaction tools already use AGENT_ETH_KEY automatically

This ensures consistency and security - the actual private key and address are never exposed in conversations.

### Key Commands to Remember

- `make dev_anvil` - Start local blockchain fork with funded agent account
- `cast wallet address --private-key $AGENT_ETH_KEY` - Get the agent's address
- Tools that need the private key will automatically use `AGENT_ETH_KEY` from environment

### When Asked About Blockchain Tasks

1. **For balance checks** - Use the blockchain query tools
2. **For price comparisons** - Use DEX price tools to check multiple exchanges
3. **For arbitrage** - Use arbitrage analysis tools, then simulate before executing
4. **For transactions** - Always simulate first, check gas costs, then execute if profitable
5. **For testing** - Recommend using `make dev_anvil` for safe local testing

## Advanced: eth_call with State Overrides

The `eth_call` tool allows you to read contract state and simulate calls with modified blockchain state. This is extremely powerful for testing "what if" scenarios without actually modifying the blockchain.

### Basic eth_call Usage

```python
# Read token balance
result = eth_call(
    to_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC contract
    data="0x70a08231000000000000000000000000f39fd6e51aad88f6f4ce6ab8827279cfffb92266",  # balanceOf(address)
)
# Returns the balance as hex in result["result"]
```

### State Override Examples

State overrides allow you to temporarily modify blockchain state for the duration of the call:

#### 1. Override Token Balance
```python
# Check what would happen if an address had 1M USDC
state_overrides = {
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": {  # USDC contract
        "state": {
            # Storage slot for user balance (slot 2 for USDC)
            # keccak256(abi.encode(userAddress, 2))
            "0x...calculated_slot...": "0xf4240"  # 1,000,000 * 10^6
        }
    }
}

result = eth_call(
    to_address=dex_router,
    data=swap_calldata,
    state_overrides=state_overrides
)
```

#### 2. Override ETH Balance
```python
# Test a swap with modified ETH balance
state_overrides = {
    "0xYourAddress": {
        "balance": "0xde0b6b3a7640000"  # 1 ETH in wei (hex)
    }
}
```

#### 3. Override Multiple States
```python
# Complex state override for testing arbitrage
state_overrides = {
    # Give user tokens
    "0xTokenContract": {
        "state": {
            "0x...user_balance_slot...": "0x1234567890"
        }
    },
    # Modify DEX liquidity
    "0xDEXContract": {
        "state": {
            "0x...reserve0_slot...": "0x999999999",
            "0x...reserve1_slot...": "0x888888888"
        }
    },
    # Give user ETH for gas
    "0xUserAddress": {
        "balance": "0xde0b6b3a7640000"
    }
}
```

#### 4. Override Contract Code
```python
# Replace contract bytecode (useful for testing upgrades)
state_overrides = {
    "0xContractAddress": {
        "code": "0x6080604052..."  # New bytecode
    }
}
```

#### 5. Finding Storage Slots
To use state overrides effectively, you need to know storage slot locations:

```python
# For mappings: slot = keccak256(abi.encode(key, mappingSlot))
# Example for ERC20 balances (usually slot 0, 1, or 2):
from web3 import Web3
user_address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
balance_slot = 2  # Common for many tokens

# Calculate storage slot for user balance
slot_data = Web3.solidity_keccak(['address', 'uint256'], [user_address, balance_slot])
print(f"Storage slot: {slot_data.hex()}")
```

### Common Use Cases for State Overrides

1. **Test Arbitrage Opportunities**
   - Override token balances to test if you had enough capital
   - Modify DEX reserves to test different market conditions

2. **Verify Smart Contract Behavior**
   - Test contract functions with different balance conditions
   - Verify access control by overriding ownership

3. **Simulate Liquidations**
   - Override collateral values to test liquidation scenarios
   - Test flash loan strategies without capital

4. **Debug Failed Transactions**
   - Override state to understand why a transaction failed
   - Test fixes before deploying

### Important Notes

- State overrides are temporary and only affect the single eth_call
- They don't modify the actual blockchain state
- Useful for testing without spending gas or holding tokens
- Can simulate complex scenarios impossible to test otherwise