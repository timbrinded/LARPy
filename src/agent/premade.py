"""Ethereum arbitrage bot agent with DEX price monitoring and analysis tools."""

import logging

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agent.config_loader import get_config
from agent.tools.arbitrage import (
    analyze_token_pair_opportunities,
    calculate_profit,
    find_arbitrage_opportunities,
    format_arbitrage_strategy,
)
from agent.tools.blockchain import (
    estimate_transaction_cost,
    get_eth_balance,
    get_gas_price,
    get_token_balance,
)
from agent.tools.dex_prices import (
    discover_curve_pools,
    get_all_dex_prices,
    get_all_dex_prices_extended,
    get_curve_price,
    get_fluid_dex_price,
    get_maverick_price,
    get_sushiswap_price,
    get_uniswap_v3_price,
)

# Set up logging
logger = logging.getLogger(__name__)

# Load model configuration
config = get_config()
model_config = config.models

# Create the ChatOpenAI model with configuration
logger.info(f"Loading model {model_config.model_name} from {model_config.provider}")
model = ChatOpenAI(
    model=model_config.model_name,
    max_tokens=model_config.max_tokens,
)

# Combine all tools for the arbitrage bot
tools = [
    # Blockchain tools
    get_eth_balance,
    get_token_balance,
    get_gas_price,
    estimate_transaction_cost,
    # DEX price tools
    get_uniswap_v3_price,
    get_sushiswap_price,
    get_all_dex_prices,
    get_curve_price,
    discover_curve_pools,
    get_fluid_dex_price,
    get_maverick_price,
    get_all_dex_prices_extended,
    # Arbitrage analysis tools
    find_arbitrage_opportunities,
    calculate_profit,
    format_arbitrage_strategy,
    analyze_token_pair_opportunities,
]

graph = create_react_agent(model=model, tools=tools)
