#!/usr/bin/env python3
"""Simple test of Fluid DEX price function"""

from agent.tools.dex_prices import get_fluid_dex_price

print("Testing Fluid DEX prices...\n")

# Test different token pairs
test_pairs = [
    ("ETH", "USDC"),
    ("WETH", "USDC"),
    ("USDC", "USDT"),
    ("WETH", "USDT"),
]

for from_token, to_token in test_pairs:
    print(f"Testing {from_token}/{to_token}:")
    result = get_fluid_dex_price.func(from_token, to_token)
    print(f"  Result: {result}")
    print()