#!/usr/bin/env python3
"""Debug Fluid DEX pools to see what's available"""

from web3 import Web3
from agent.config_loader import get_config

# Get configuration
config = get_config()

# Connect to Web3
w3 = Web3(Web3.HTTPProvider(config.default_chain.rpc_url))
if not w3.is_connected():
    print("Failed to connect to Ethereum network")
    exit(1)

print(f"Connected to network: {config.default_chain.rpc_url}")

# Get Fluid configuration
fluid_config = config.dexes.get("fluid")
if not fluid_config:
    print("Fluid configuration not found")
    exit(1)

# Get resolver contract
resolver_contract = None
for contract in fluid_config.contracts:
    if contract.name == "DexResolver":
        resolver_contract = contract
        break

if not resolver_contract:
    print("Fluid DEX resolver contract not found")
    exit(1)

resolver_abi = resolver_contract.abi
resolver_address = resolver_contract.address

print(f"Using resolver at: {resolver_address}")

resolver = w3.eth.contract(address=resolver_address, abi=resolver_abi)

# Get all DEX addresses
try:
    dex_addresses = resolver.functions.getAllDexAddresses().call()
    print(f"\nFound {len(dex_addresses)} Fluid DEX pools:")
    
    # Query each DEX for its data
    for i, dex_address in enumerate(dex_addresses):
        try:
            # Get detailed data for this specific DEX
            pool_data = resolver.functions.getDexEntireData(dex_address).call()
            
            # Extract basic info
            pool_address = pool_data[0]
            constant_views = pool_data[1]
            col_reserves = pool_data[5]
            debt_reserves = pool_data[6]
            
            # Extract token addresses
            token0 = constant_views[5]  # token0 is at index 5 in constantViews
            token1 = constant_views[6]  # token1 is at index 6 in constantViews
            
            # Get token symbols
            token0_symbol = "Unknown"
            token1_symbol = "Unknown"
            
            for symbol, token_config in config.tokens.items():
                if token_config.address.lower() == token0.lower():
                    token0_symbol = symbol
                if token_config.address.lower() == token1.lower():
                    token1_symbol = symbol
            
            # Extract reserves
            token0_col_reserves = int(col_reserves[0])
            token1_col_reserves = int(col_reserves[1])
            token0_debt_reserves = int(debt_reserves[2])
            token1_debt_reserves = int(debt_reserves[3])
            
            # Total reserves
            token0_total = token0_col_reserves + token0_debt_reserves
            token1_total = token1_col_reserves + token1_debt_reserves
            
            print(f"\nPool {i+1}: {pool_address}")
            print(f"  Token0: {token0_symbol} ({token0})")
            print(f"  Token1: {token1_symbol} ({token1})")
            print(f"  Reserves: {token0_total} / {token1_total}")
            
            # Check if this is a WETH/USDC pool
            if (token0_symbol == "WETH" and token1_symbol == "USDC") or \
               (token0_symbol == "USDC" and token1_symbol == "WETH"):
                print("  *** This is a WETH/USDC pool! ***")
                
        except Exception as e:
            print(f"\nError reading pool {i+1} at {dex_address}: {str(e)}")
            
except Exception as e:
    print(f"Error querying Fluid resolver: {str(e)}")