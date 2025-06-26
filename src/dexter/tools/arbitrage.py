"""Arbitrage analysis tools for finding profitable opportunities."""

import re
from typing import List

from langchain_core.tools import tool


def parse_price(price_string: str) -> float | None:
    """Extract price value from DEX price string."""
    match = re.search(r"= ([\d.]+)", price_string)
    if match:
        return float(match.group(1))
    return None


def parse_dex_name(price_string: str) -> str:
    """Extract DEX name from price string."""
    if price_string.startswith("1inch"):
        return "1inch"
    elif price_string.startswith("Uniswap"):
        return "Uniswap V3"
    elif price_string.startswith("SushiSwap"):
        return "SushiSwap"
    elif price_string.startswith("Curve"):
        return "Curve Finance"
    return "Unknown"


@tool
def find_arbitrage_opportunities(
    price_data: str, min_profit_percentage: float = 0.5
) -> str:
    """Analyze price data to find arbitrage opportunities.

    Args:
        price_data: Multi-line string with prices from different DEXs
        min_profit_percentage: Minimum profit percentage to consider (default 0.5%)

    Returns:
        Analysis of arbitrage opportunities
    """
    try:
        lines = price_data.strip().split("\n")
        prices = []

        for line in lines:
            price = parse_price(line)
            if price and not line.startswith("Error"):
                dex = parse_dex_name(line)
                prices.append((dex, price, line))

        if len(prices) < 2:
            return "Not enough valid price data to find arbitrage opportunities"

        # Find min and max prices
        min_price_data = min(prices, key=lambda x: x[1])
        max_price_data = max(prices, key=lambda x: x[1])

        min_dex, min_price, min_line = min_price_data
        max_dex, max_price, max_line = max_price_data

        # Calculate profit
        profit_percentage = ((max_price - min_price) / min_price) * 100

        if profit_percentage < min_profit_percentage:
            return f"No profitable arbitrage found. Best opportunity: {profit_percentage:.3f}% (below {min_profit_percentage}% threshold)"

        # Extract token pair from the price line
        token_match = re.search(r"1 (\w+) = [\d.]+ (\w+)", min_line)
        if token_match:
            from_token = token_match.group(1)
            to_token = token_match.group(2)
        else:
            from_token = "Token1"
            to_token = "Token2"

        return f"""🎯 ARBITRAGE OPPORTUNITY FOUND!

Buy on: {min_dex}
Price: 1 {from_token} = {min_price:.6f} {to_token}

Sell on: {max_dex}  
Price: 1 {from_token} = {max_price:.6f} {to_token}

Profit: {profit_percentage:.2f}%
Price difference: {max_price - min_price:.6f} {to_token}

Strategy:
1. Buy {from_token} on {min_dex}
2. Transfer to {max_dex}
3. Sell {from_token} for {to_token}
4. Gross profit: {profit_percentage:.2f}% (before gas costs)"""

    except Exception as e:
        return f"Error analyzing arbitrage opportunities: {str(e)}"


@tool
def calculate_profit(
    buy_price: float, sell_price: float, amount_eth: float, gas_cost_eth: float = 0.01
) -> str:
    """Calculate net profit after gas costs.

    Args:
        buy_price: Price to buy at (in target token)
        sell_price: Price to sell at (in target token)
        amount_eth: Amount of ETH to arbitrage
        gas_cost_eth: Estimated gas cost in ETH (default 0.01)

    Returns:
        Detailed profit calculation
    """
    try:
        # Calculate gross profit
        tokens_bought = amount_eth * buy_price
        eth_received = tokens_bought / sell_price
        gross_profit_eth = eth_received - amount_eth
        gross_profit_percentage = (gross_profit_eth / amount_eth) * 100

        # Calculate net profit
        net_profit_eth = gross_profit_eth - gas_cost_eth
        net_profit_percentage = (net_profit_eth / amount_eth) * 100

        return f"""Profit Calculation:
        
Investment: {amount_eth} ETH
Buy price: {buy_price:.6f} tokens/ETH
Tokens acquired: {tokens_bought:.2f}
Sell price: {sell_price:.6f} tokens/ETH
ETH received: {eth_received:.6f}

Gross profit: {gross_profit_eth:.6f} ETH ({gross_profit_percentage:.2f}%)
Gas cost: {gas_cost_eth:.6f} ETH
Net profit: {net_profit_eth:.6f} ETH ({net_profit_percentage:.2f}%)

Break-even: {"Profitable ✅" if net_profit_eth > 0 else "Not profitable ❌"}"""

    except Exception as e:
        return f"Error calculating profit: {str(e)}"


@tool
def format_arbitrage_strategy(
    from_token: str,
    to_token: str,
    buy_dex: str,
    sell_dex: str,
    amount: str,
    expected_profit_percentage: float,
) -> str:
    """Format a complete arbitrage strategy for execution.

    Args:
        from_token: Token to arbitrage
        to_token: Quote token
        buy_dex: DEX to buy on
        sell_dex: DEX to sell on
        amount: Amount to trade
        expected_profit_percentage: Expected profit %

    Returns:
        Formatted strategy ready for execution
    """
    return f"""
📋 ARBITRAGE STRATEGY SUMMARY
=============================

Token Pair: {from_token}/{to_token}
Amount: {amount} {from_token}
Expected Profit: {expected_profit_percentage:.2f}%

EXECUTION STEPS:
1. Ensure you have {amount} {from_token} available
2. Check current gas prices (aim for < 50 Gwei)
3. Buy on {buy_dex}:
   - Swap {from_token} → {to_token}
   - Use high slippage tolerance (1-2%)
   
4. Sell on {sell_dex}:
   - Swap {to_token} → {from_token}
   - Monitor for MEV protection
   
5. Calculate final profit after all fees

⚠️ RISKS:
- Price may change during execution
- High gas costs can eliminate profits
- MEV bots may front-run transactions
- Slippage on large trades

💡 TIPS:
- Use flashloans for larger capital
- Execute during low gas periods
- Consider using MEV protection
- Start with small test amounts"""


@tool
def analyze_token_pair_opportunities(token_pairs: List[str]) -> str:
    """Analyze multiple token pairs for best arbitrage opportunities.

    Args:
        token_pairs: List of token pairs in format "TOKEN1/TOKEN2"

    Returns:
        Summary of opportunities across all pairs
    """
    if not token_pairs:
        # Default popular pairs
        token_pairs = [
            "ETH/USDC",
            "ETH/USDT",
            "WBTC/ETH",
            "UNI/ETH",
            "AAVE/ETH",
            "LINK/ETH",
        ]

    return f"""Analyzing {len(token_pairs)} token pairs for arbitrage opportunities:

Token Pairs to check:
{chr(10).join(f"- {pair}" for pair in token_pairs)}

To analyze each pair:
1. Use get_all_dex_prices_extended() for each pair
2. Use find_arbitrage_opportunities() on the results
3. Calculate expected profits with calculate_profit()

This will identify the most profitable opportunities across major DEXs."""
