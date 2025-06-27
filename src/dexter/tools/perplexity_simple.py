"""Simple Perplexity search tool."""

import os

from langchain_core.tools import tool


@tool
def search_online(query: str) -> str:
    """Search online for current information about protocols, contracts, and documentation.
    
    Use this to find:
    - Current protocol addresses
    - Smart contract documentation  
    - DeFi protocol information
    - Recent updates and changes
    
    Args:
        query: What to search for
        
    Returns:
        Search results or instructions to use perplexity
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return """To search online, you need a Perplexity API key in PERPLEXITY_API_KEY env var.
        
For now, here are some common addresses:
- Uniswap V3 Router: 0xE592427A0AEce92De3Edee1F18E0157C05861564
- WETH: 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
- USDC: 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
- USDT: 0xdAC17F958D2ee523a2206206994597C13D831ec7

You can also use eth_call with known addresses to explore contracts."""
    
    # If we have the API key, we could implement the search here
    # For now, return a helpful message
    return f"Online search for '{query}' would require implementing Perplexity API. Use contract addresses above or eth_call to explore."