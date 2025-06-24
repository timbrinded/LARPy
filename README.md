# Ethereum Arbitrage Bot - LangGraph Agent

[![CI](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml)
[![Integration Tests](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml)

An Ethereum DEX arbitrage detection bot built with LangGraph. This agent analyzes price differences across major DEXs (Uniswap, SushiSwap, 1inch) to identify profitable arbitrage opportunities for popular tokens.

## Architecture

![LangGraph Agent Template Architecture](./static/architecture.png)

<div align="center">
  <img src="./static/studio_ui.png" alt="Graph view in LangGraph studio UI" width="75%" />
</div>

## Overview

This arbitrage bot is a proof-of-concept that demonstrates how to build a crypto trading agent using LangGraph. The bot:

- **Monitors Multiple DEXs**: Fetches real-time prices from Uniswap V3, SushiSwap, and 1inch
- **Identifies Arbitrage**: Automatically detects profitable price discrepancies between exchanges
- **Calculates Profits**: Factors in gas costs and provides net profit estimates
- **Focuses on Major Tokens**: Works with well-audited tokens like ETH, USDC, USDT, WBTC, UNI, AAVE
- **Provides Clear Strategies**: Generates step-by-step execution plans for identified opportunities

## Features

### Blockchain Tools
- Check ETH and ERC-20 token balances
- Monitor current gas prices
- Estimate transaction costs

### DEX Price Tools
- Fetch prices from 1inch aggregator
- Query Uniswap V3 pools via subgraph
- Get SushiSwap pair prices
- Compare prices across all DEXs simultaneously

### Arbitrage Analysis
- Identify profitable opportunities above configurable thresholds
- Calculate expected profits after gas costs
- Generate formatted trading strategies
- Analyze multiple token pairs in batch

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API key (for the LLM agent)

### Installation

1. Clone the repository and install dependencies using uv:

```bash
cd path/to/test-agent
uv sync
uv run pip install -e .
```

2. Set up environment variables:

```bash
# Create .env file
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env

# Optional: Add LangSmith for tracing
echo "LANGSMITH_API_KEY=your-langsmith-key" >> .env
```

3. (Optional) Configure custom RPC endpoints for better reliability:

```bash
# Add to .env for custom Ethereum RPC (default uses public endpoints)
echo "ETH_RPC_URL=https://your-eth-rpc-endpoint" >> .env
```

### Running the Agent

Start the LangGraph development server:

```bash
uv run langgraph dev
```

The server will start on `http://localhost:8123` with LangGraph Studio available for visual debugging.

### Testing the Arbitrage Bot

Once the server is running, you can interact with the bot through the LangGraph Studio UI or API. Here are example queries:

#### 1. Check current gas prices:
```
"What's the current gas price on Ethereum?"
```

#### 2. Compare prices across DEXs:
```
"Show me ETH/USDC prices on all major DEXs"
```

#### 3. Find arbitrage opportunities:
```
"Find arbitrage opportunities for ETH/USDC, ETH/USDT, and WBTC/ETH pairs"
```

#### 4. Get a full arbitrage analysis:
```
"Analyze ETH/USDC for arbitrage opportunities and show me the potential profit for trading 10 ETH"
```

#### 5. Check token balances:
```
"What's the USDC balance for address 0x..."
```

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

## Customization & Extension

### Adding New DEXs

To add support for more DEXs, create new tools in `src/agent/tools/dex_prices.py`:

```python
@tool
def get_curve_price(from_token: str, to_token: str) -> str:
    """Get token price from Curve Finance."""
    # Implementation here
```

### Adjusting Arbitrage Parameters

Modify the minimum profit threshold in `src/agent/tools/arbitrage.py`:

```python
# Change from default 0.5% to 1%
find_arbitrage_opportunities(price_data, min_profit_percentage=1.0)
```

### Adding New Token Pairs

Update the `POPULAR_TOKENS` dict in `src/agent/tools/dex_prices.py`:

```python
POPULAR_TOKENS = {
    "NEW_TOKEN": "0x...",  # Add new token address
    # ... existing tokens
}
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest tests/unit_tests/

# Run integration tests
uv run pytest tests/integration_tests/
```

### Code Quality

```bash
# Run linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Type checking
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

- **Read-only**: Current implementation only detects opportunities, doesn't execute trades
- **API Rate Limits**: Public endpoints may have rate limits
- **Latency**: Subgraph queries can be slow for real-time arbitrage
- **Gas Estimation**: Simple gas estimates may not reflect actual costs during high congestion

### Future Enhancements

- **Flashloan Integration**: Add tools for capital-free arbitrage using Aave/dYdX
- **Transaction Execution**: Implement secure transaction signing and submission
- **Real-time Monitoring**: WebSocket connections for live price feeds
- **Multi-hop Arbitrage**: Support complex paths like ETH → USDC → DAI → ETH
- **Cross-chain Arbitrage**: Add support for L2s and bridges
- **Analytics Dashboard**: Track historical performance and opportunities

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
