"""Utility functions for wallet operations."""

import os
from functools import lru_cache

from web3 import Web3


@lru_cache(maxsize=1)
def get_agent_address() -> str:
    """Get the agent's wallet address from the private key in environment.
    
    Returns:
        The agent's Ethereum address
        
    Raises:
        ValueError: If AGENT_ETH_KEY is not set or invalid
    """
    private_key = os.getenv("AGENT_ETH_KEY")
    if not private_key:
        raise ValueError("AGENT_ETH_KEY not found in environment variables")
    
    try:
        w3 = Web3()
        account = w3.eth.account.from_key(private_key)
        return account.address
    except Exception as e:
        raise ValueError(f"Invalid private key in AGENT_ETH_KEY: {str(e)}")


def resolve_address(address: str) -> str:
    """Resolve special address placeholders to actual addresses.
    
    Args:
        address: The address to resolve (e.g., "0xYourWalletAddress")
        
    Returns:
        The resolved address
    """
    if address.lower() == "0xyourwalletaddress":
        return get_agent_address()
    return address