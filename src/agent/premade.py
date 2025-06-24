"""Ethereum arbitrage bot agent with DEX price monitoring and analysis tools."""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agent.tools.arbitrage import (
    analyze_token_pair_opportunities,
    calculate_profit,
    find_arbitrage_opportunities,
    format_arbitrage_strategy,
)

# Import all arbitrage bot tools
from agent.tools.blockchain import (
    estimate_transaction_cost,
    get_eth_balance,
    get_gas_price,
    get_token_balance,
)
from agent.tools.dex_prices import (
    get_1inch_price,
    get_all_dex_prices,
    get_sushiswap_price,
    get_uniswap_v3_price,
)

model = ChatOpenAI(model="gpt-4o-mini")

# Combine all tools for the arbitrage bot
tools = [
    # Blockchain tools
    get_eth_balance,
    get_token_balance,
    get_gas_price,
    estimate_transaction_cost,
    # DEX price tools
    get_1inch_price,
    get_uniswap_v3_price,
    get_sushiswap_price,
    get_all_dex_prices,
    # Arbitrage analysis tools
    find_arbitrage_opportunities,
    calculate_profit,
    format_arbitrage_strategy,
    analyze_token_pair_opportunities
]

agent = create_react_agent(
    model=model,
    tools=tools
)
