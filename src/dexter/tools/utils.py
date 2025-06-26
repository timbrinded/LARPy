"""Utility functions for tools."""

import os
from typing import Optional
from web3 import Web3


def resolve_wallet_address(address: Optional[str]) -> Optional[str]:
    """Resolve wallet address, handling special '0xYourWalletAddress' keyword.
    
    Args:
        address: The address to resolve. Can be:
            - None: Will return None
            - "0xYourWalletAddress": Will resolve to agent's address from AGENT_ETH_KEY
            - Any other address: Will be returned as-is
    
    Returns:
        The resolved address or None if resolution fails
    
    Raises:
        ValueError: If AGENT_ETH_KEY is not found or invalid when needed
    """
    if address is None:
        return None
        
    if address.lower() == "0xyourwalletaddress":
        private_key = os.getenv("AGENT_ETH_KEY")
        if not private_key:
            raise ValueError("AGENT_ETH_KEY not found in environment")
        try:
            # Derive address from private key
            w3 = Web3()
            account = w3.eth.account.from_key(private_key)
            return account.address
        except Exception as e:
            raise ValueError(f"Invalid private key in AGENT_ETH_KEY: {str(e)}")
    
    return address