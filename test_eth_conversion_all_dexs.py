#!/usr/bin/env python3
"""Test ETH/WETH conversion across all DEXs"""

from agent.tools.dex_prices import (
    get_uniswap_v3_price,
    get_sushiswap_price,
    get_curve_price,
    get_fluid_dex_price
)

print("Testing ETH vs WETH handling across all DEXs\n")

# Test Uniswap V3
print("=== Uniswap V3 ===")
print("ETH/USDC:", get_uniswap_v3_price.func("ETH", "USDC"))
print("WETH/USDC:", get_uniswap_v3_price.func("WETH", "USDC"))
print()

# Test SushiSwap
print("=== SushiSwap ===")
print("ETH/USDC:", get_sushiswap_price.func("ETH", "USDC"))
print("WETH/USDC:", get_sushiswap_price.func("WETH", "USDC"))
print()

# Test Curve
print("=== Curve ===")
print("ETH/USDC:", get_curve_price.func("ETH", "USDC"))
print("WETH/USDC:", get_curve_price.func("WETH", "USDC"))
print()

# Test Fluid
print("=== Fluid DEX ===")
print("ETH/USDC:", get_fluid_dex_price.func("ETH", "USDC"))
print("WETH/USDC:", get_fluid_dex_price.func("WETH", "USDC"))