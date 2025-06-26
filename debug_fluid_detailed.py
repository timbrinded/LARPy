#!/usr/bin/env python3
"""Detailed debug of Fluid DEX to understand pool availability"""

from web3 import Web3
from agent.config_loader import get_config, get_config_loader

# Get configuration
config = get_config()
loader = get_config_loader()

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
    
    # Get common token addresses
    weth_address = loader.get_token_address("WETH")
    usdc_address = loader.get_token_address("USDC")
    usdt_address = loader.get_token_address("USDT")
    
    print(f"\nLooking for pools with:")
    print(f"  WETH: {weth_address}")
    print(f"  USDC: {usdc_address}")
    print(f"  USDT: {usdt_address}")
    
    found_any_pool = False
    
    # Check each pool
    for i, dex_address in enumerate(dex_addresses[:5]):  # Just check first 5 pools
        print(f"\nChecking pool {i+1}: {dex_address}")
        
        try:
            # Try a simpler approach - just get the DEX ID
            dex_id = resolver.functions.getDexAddress(i).call()
            print(f"  Pool verified at: {dex_id}")
            
            # Try to get basic pool info using a different method
            # Since getDexEntireData is failing, let's see if there's another way
            found_any_pool = True
            
        except Exception as e:
            print(f"  Error: {str(e)}")
    
    if not found_any_pool:
        print("\nNo accessible Fluid pools found")
    
except Exception as e:
    print(f"Error querying Fluid resolver: {str(e)}")