"""Ethereum arbitrage bot agent with DEX price monitoring and analysis tools."""

import logging

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .config_loader import get_config
from .tools.arbitrage import (
    analyze_token_pair_opportunities,
    calculate_profit,
    find_arbitrage_opportunities,
    format_arbitrage_strategy,
)
from .tools.blockchain import (
    estimate_transaction_cost,
    get_eth_balance,
    get_gas_price,
    get_token_balance,
)
from .tools.dex_prices import (
    discover_curve_pools,
    get_all_dex_prices,
    get_all_dex_prices_extended,
    get_curve_price,
    get_fluid_dex_price,
    get_maverick_price,
    get_sushiswap_price,
    get_uniswap_v3_price,
)
from .tools.swap_encoder import (
    encode_erc20_approve,
    encode_sushiswap_swap,
    encode_uniswap_v3_swap,
)
from .tools.transactions import (
    alchemy_simulate_tool,
    submit_transaction_tool,
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
    # Transaction tools
    submit_transaction_tool,
    alchemy_simulate_tool,
    # Swap encoding tools
    encode_uniswap_v3_swap,
    encode_sushiswap_swap,
    encode_erc20_approve,
]

system_prompt = """
You are an Ethereum Dex (decentralised exchange) assistant bot agent. 
Use the tools provided to analyze DEX prices and find arbitrage opportunities. 
Respond with actionable strategies based on the analysis.

IMPORTANT: When executing swaps:
1. First use encode_uniswap_v3_swap or encode_sushiswap_swap to properly encode the transaction
2. For token swaps (not ETH), first use encode_erc20_approve to approve the router
3. Use alchemy_simulate_tool to test the transaction before submitting
4. Only then use submit_transaction with the encoded data

Your tools already all know what their own private keys are.
All users are assumed to have address 0xYourWalletAddress unless specified otherwise.

Key points:
- Always encode swaps properly using the encoding tools
- ETH swaps need value in the transaction, token swaps need approval first
- Use the correct fee tier for Uniswap V3 (usually 3000 for 0.3%)
- Set reasonable deadlines (20 minutes default)
"""

graph = create_react_agent(model=model, tools=tools, prompt=system_prompt)
