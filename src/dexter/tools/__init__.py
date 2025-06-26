"""Tools for the Ethereum arbitrage bot."""

from .arbitrage import (
    analyze_token_pair_opportunities,
    calculate_profit,
    find_arbitrage_opportunities,
    format_arbitrage_strategy,
)
from .blockchain import (
    blockchain_tools,
    estimate_gas_tool,
    estimate_transaction_cost,
    get_balance_tool,
    get_block_tool,
    get_eth_balance,
    get_gas_price,
    get_token_balance,
    get_transaction_tool,
)
from .dex_prices import (
    discover_curve_pools,
    get_all_dex_prices,
    get_all_dex_prices_extended,
    get_curve_price,
    get_fluid_dex_price,
    get_maverick_price,
    get_sushiswap_price,
    get_uniswap_v3_price,
)
from .transactions import (
    alchemy_simulate_tool,
    submit_transaction_tool,
    transaction_tools,
)
from .swap_encoder import (
    encode_uniswap_v3_swap,
    encode_sushiswap_swap,
    encode_erc20_approve,
    swap_encoding_tools,
)

__all__ = [
    # Arbitrage tools
    "analyze_token_pair_opportunities",
    "calculate_profit",
    "find_arbitrage_opportunities",
    "format_arbitrage_strategy",
    # Blockchain tools
    "blockchain_tools",
    "estimate_gas_tool",
    "estimate_transaction_cost",
    "get_balance_tool",
    "get_block_tool",
    "get_eth_balance",
    "get_gas_price",
    "get_token_balance",
    "get_transaction_tool",
    # DEX price tools
    "discover_curve_pools",
    "get_all_dex_prices",
    "get_all_dex_prices_extended",
    "get_curve_price",
    "get_fluid_dex_price",
    "get_maverick_price",
    "get_sushiswap_price",
    "get_uniswap_v3_price",
    # Transaction tools
    "alchemy_simulate_tool",
    "submit_transaction_tool",
    "transaction_tools",
    # Swap encoding tools
    "encode_uniswap_v3_swap",
    "encode_sushiswap_swap",
    "encode_erc20_approve",
    "swap_encoding_tools",
]
