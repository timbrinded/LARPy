# LARPy - Ethereum Arbitrage Bot

[![CI](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml)
[![Integration Tests](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml)

LARPy is an Ethereum DEX arbitrage detection bot built with LangGraph. This agent uses an **evaluator-optimizer pattern** to validate and optimize Ethereum transactions before execution. It analyzes price differences across major DEXs (Uniswap V3, SushiSwap, Curve Finance) to identify profitable arbitrage opportunities for popular tokens.

## Architecture

![LARPy Architecture](./static/architecture.png)

### Evaluator-Optimizer Pattern

LARPy implements a sophisticated evaluator-optimizer pattern for transaction validation:

1. **Transaction Generation**: Creates initial transaction proposals based on user objectives
2. **Evaluation**: Validates transactions against multiple criteria:
   - Gas efficiency
   - Security (MEV protection, slippage)
   - Correctness (state changes match objectives)
   - Efficiency (optimal routing)
3. **Optimization**: Improves transactions based on evaluation feedback
4. **Subagent Analysis**: Spawns specialized agents for deep validation:
   - **Gas Analyzer**: Optimizes gas usage patterns
   - **Security Validator**: Checks for vulnerabilities
   - **MEV Inspector**: Assesses MEV attack risks
   - **State Validator**: Confirms expected state changes
5. **Finalization**: Prepares validated transactions for execution

## Overview

LARPy (LangGraph ARbitrage Python bot) is a proof-of-concept that demonstrates how to build a crypto trading agent using LangGraph's evaluator-optimizer pattern. The bot:

- **Generates Transactions**: Creates Ethereum transactions based on user objectives (swaps, arbitrage, transfers)
- **Evaluates Transactions**: Validates against gas efficiency, security, correctness, and MEV protection
- **Optimizes Automatically**: Improves transactions based on evaluation feedback
- **Spawns Subagents**: Uses specialized validators for deep analysis
- **Monitors Multiple DEXs**: Fetches real-time prices from Uniswap V3, SushiSwap, and Curve Finance
- **Identifies Arbitrage**: Automatically detects profitable price discrepancies between exchanges
- **Calculates Profits**: Factors in gas costs and provides net profit estimates

## Features

### Transaction Evaluation & Optimization
- **Multi-criteria validation**: Gas, security, efficiency, correctness
- **Automatic optimization**: Improves transactions based on validation feedback
- **Subagent coordination**: Parallel analysis by specialized validators
- **Configurable rules**: Customizable thresholds and validation criteria
- **Optimization tips**: Actionable feedback for transaction improvement
- **Error recovery**: Intelligent handling of validation errors with retry capabilities
- **Direct query support**: Balance checks and price queries without transaction generation

### Blockchain Tools
- Check ETH and ERC-20 token balances
- Monitor current gas prices
- Estimate transaction costs
- **Submit transactions**: Execute blockchain transactions with gas optimization
- **Simulate transactions**: Preview asset changes using Alchemy's simulateAssetChanges API

### DEX Price Tools
- **Uniswap V3**: Uses Quoter contract for accurate swap simulation
- **SushiSwap**: Direct pool queries via getReserves()
- **Curve Finance**: Supports stableswap (3pool) and crypto pools (ETH pairs)
- **Extended Support**: Placeholders for Fluid DEX and Maverick Protocol
- Compare prices across all DEXs simultaneously
- Supports popular pairs: ETH/USDC, ETH/USDT, WBTC/ETH, ETH/DAI, stETH/ETH

### Arbitrage Analysis
- Identify profitable opportunities above configurable thresholds
- Calculate expected profits after gas costs
- Generate formatted trading strategies
- Analyze multiple token pairs in batch

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager (replaces pip)
- OpenAI API key (for the LLM agent)

### Installation

1. Clone the repository and install dependencies using uv:

```bash
cd path/to/test-agent
uv sync
```

2. Set up environment variables:

```bash
# Create .env file
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env

# Required for transaction tools
echo "ALCHEMY_API_KEY=your-alchemy-api-key" >> .env
echo "AGENT_ETH_KEY=your-ethereum-private-key" >> .env

# Optional: Add LangSmith for tracing
echo "LANGSMITH_API_KEY=your-langsmith-key" >> .env
```

3. (Optional) Configure custom RPC endpoints for better reliability:

```bash
# Add to .env for custom Ethereum RPC (default uses public endpoints)
echo "ETH_RPC_URL=https://your-eth-rpc-endpoint" >> .env
```

⚠️ **SECURITY WARNING**: Never commit your `.env` file to version control. The `AGENT_ETH_KEY` contains your private key and must be kept secure.

### Running the Agent

Start the LangGraph development server:

```bash
uv run langgraph dev
```

The server will start on `http://localhost:8123` with LangGraph Studio available for visual debugging.

### Available Graphs

1. **`agent`** (Recommended) - Smart agent-driven workflow
   - Intelligent intent classification without hardcoded patterns
   - Two specialized agents: Generator and Evaluator
   - Clean separation of concerns with minimal routing logic
   - Leverages model reasoning for better flexibility

2. **`react`** - React pattern agent
   - Direct tool execution
   - Good for exploration and debugging
   - Simple single-agent approach

### Testing the Arbitrage Bot

Once the server is running, select the **`agent`** graph in LangGraph Studio and interact with it. Here are example queries:

#### 1. Check current gas prices:
```
"What's the current gas price on Ethereum?"
```

#### 2. Compare prices across DEXs:
```
"Show me ETH/USDC prices on all major DEXs"
"Get DAI/USDC price on Curve"
"Check stETH/ETH price on Curve Finance"
```

#### 3. Generate and evaluate transactions:
```
"I want to swap 2 ETH for USDC"
# The agent will:
# 1. Generate the swap transaction
# 2. Evaluate it for gas, security, and correctness
# 3. Suggest optimizations if needed
# 4. Ask for approval before finalizing
```

#### 4. Find arbitrage opportunities:
```
"Find arbitrage opportunities for ETH/USDC"
# The agent will:
# 1. Check prices across DEXs
# 2. Generate arbitrage transaction if profitable
# 3. Evaluate the transaction
# 4. Optimize for maximum profit
```

#### 4. Get a full arbitrage analysis:
```
"Analyze ETH/USDC for arbitrage opportunities and show me the potential profit for trading 10 ETH"
```

#### 5. Check token balances:
```
"What's the USDC balance for address 0x..."
```

#### 6. Simulate a transaction:
```
"Simulate sending 1 ETH to 0x..."
```
Note: Uses ALCHEMY_API_KEY and derives sender address from AGENT_ETH_KEY

#### 7. Submit a transaction:
```
"Submit a transaction to send 0.1 ETH to 0x..."
```
Note: Uses AGENT_ETH_KEY from environment for signing

### Example Arbitrage Detection Flow

1. The agent fetches prices from multiple DEXs
2. Identifies price discrepancies above the threshold (default 0.5%)
3. Calculates potential profit after gas costs
4. Provides a detailed execution strategy

Example output:
```
🎯 ARBITRAGE OPPORTUNITY FOUND!

Buy on: SushiSwap
Price: 1 ETH = 3,245.50 USDC

Sell on: Uniswap V3  
Price: 1 ETH = 3,262.75 USDC

Profit: 0.53%
Strategy: Buy ETH on SushiSwap, sell on Uniswap V3
Net profit after gas: 0.41% (assuming 0.01 ETH gas cost)
```

## Configuration System

LARPy uses a YAML-based configuration system with Pydantic validation for all static data:

- **`configs/chains.yaml`** - Blockchain networks and RPC endpoints
- **`configs/tokens.yaml`** - Token addresses, symbols, and decimals
- **`configs/dexes.yaml`** - DEX pools, contracts, and ABIs
- **`configs/arbitrage.yaml`** - Trading parameters and thresholds
- **`configs/models.yaml`** - LLM model settings

### Using Configuration

```python
from agent.config_loader import get_config

# Access configuration
config = get_config()
rpc_url = config.default_chain.rpc_url
min_profit = config.arbitrage.min_profit_percentage
```

## Customization & Extension

### Adding New DEXs

1. Add pool configurations to `configs/dexes.yaml`
2. Create new tools in `src/agent/tools/dex_prices.py`:

```python
@tool
def get_new_dex_price(from_token: str, to_token: str) -> str:
    """Get token price from New DEX."""
    config = get_config()
    # Use config for pool addresses, ABIs, etc.
```

### Adjusting Arbitrage Parameters

Edit `configs/arbitrage.yaml`:

```yaml
# Change minimum profit threshold
min_profit_percentage: 1.0  # Changed from 0.5%
gas_cost_estimate_eth: 0.015  # Adjust gas estimates
```

### Adding New Token Pairs

Add tokens to `configs/tokens.yaml`:

```yaml
NEW_TOKEN:
  address: "0x..."
  symbol: "NEW"
  name: "New Token"
  decimals: 18
  chain_id: 1
```

## Development

### Package Management with UV

This project uses [UV](https://docs.astral.sh/uv/) exclusively - a fast Rust-based Python package manager that replaces pip:

```bash
# Install dependencies (NOT pip install -r requirements.txt)
uv sync

# Add a new package
uv add <package-name>

# List installed packages
uv tree

# Run any command in the project environment
uv run <command>
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest tests/unit_tests/

# Run integration tests
uv run pytest tests/integration_tests/

# Or use Make targets (which use UV internally)
make test
make integration_tests
```

### Code Quality

```bash
# Run linting and formatting
make lint        # Runs ruff + mypy
make format      # Auto-formats code

# Or run directly with UV
uv run ruff check .
uv run ruff check --fix .
uv run mypy src/
```

### Working with LangGraph Studio

- **Hot reload**: Edit your graph code and changes are automatically applied
- **State debugging**: Edit past state and rerun from any point to debug specific nodes
- **Thread management**: Use the `+` button to create new threads with fresh state
- **Tracing**: Integrated with [LangSmith](https://smith.langchain.com/) for detailed execution traces

### Security Considerations

⚠️ **IMPORTANT**: This is a proof-of-concept. For production use:

1. **Never store private keys in code or environment variables**
2. **Use hardware wallets or secure key management systems**
3. **Implement proper slippage protection**
4. **Add MEV protection for transaction execution**
5. **Use private mempools or flashbots for sensitive transactions**
6. **Implement circuit breakers and position limits**
7. **Monitor for sandwich attacks**

### Known Limitations

- **Limited Execution**: Transaction submission requires private keys (use with extreme caution)
- **Direct Contract Queries**: Uniswap V3 and SushiSwap use on-chain queries which require checksummed addresses
- **Gas Estimation**: Simple gas estimates may not reflect actual costs during high congestion
- **Limited Pools**: Only includes major token pairs; less liquid pairs not supported
- **No Aggregator**: Without 1inch, we only compare two DEXs instead of aggregated best prices

### Future Enhancements

- **Flashloan Integration**: Add tools for capital-free arbitrage using Aave/dYdX
- **Transaction Execution**: Implement secure transaction signing and submission
- **Real-time Monitoring**: WebSocket connections for live price feeds
- **Multi-hop Arbitrage**: Support complex paths like ETH → USDC → DAI → ETH
- **Cross-chain Arbitrage**: Add support for L2s and bridges
- **Analytics Dashboard**: Track historical performance and opportunities

### Smart Agent Architecture (New)

The new `agent` graph uses a simplified two-agent architecture that leverages model intelligence:

1. **Generator Agent** - Smart intent understanding and transaction creation
   - Uses model reasoning to classify intent (no hardcoded patterns)
   - Has access to all blockchain/DEX tools
   - Handles direct queries immediately (balance, price checks)
   - Creates complete transaction blocks for complex operations
   - Formats transactions for evaluator when needed

2. **Evaluator Agent** - Transaction validation and execution
   - Receives transaction blocks from generator
   - Simulates using Alchemy tools
   - Either executes valid transactions or provides specific feedback
   - Feedback loops back to generator for improvements

Key improvements:
- No string manipulation or regex patterns
- Model decides tool usage based on understanding
- Clean separation between generation and evaluation
- Flexible intent handling for new use cases
- Better error recovery through agent intelligence


<!--
Configuration auto-generated by `langgraph template lock`. DO NOT EDIT MANUALLY.
{
  "config_schemas": {
    "agent": {
      "type": "object",
      "properties": {}
    }
  }
}
-->
