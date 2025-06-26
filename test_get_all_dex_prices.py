#!/usr/bin/env python3
"""Test get_all_dex_prices function"""

from agent.tools.dex_prices import get_all_dex_prices

print("Testing get_all_dex_prices for ETH/USDC...\n")

result = get_all_dex_prices.func("ETH", "USDC")
print(result)