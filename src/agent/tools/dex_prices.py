"""DEX price fetching tools for various protocols."""


import requests
from langchain_core.tools import tool

POPULAR_TOKENS = {
    "ETH": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
    "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
    "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
    "MKR": "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
}


@tool
def get_1inch_price(
    from_token: str, 
    to_token: str, 
    amount: str = "1000000000000000000"
) -> str:
    """Get token price from 1inch API.
    
    Args:
        from_token: Source token symbol (e.g., "ETH", "USDC")
        to_token: Destination token symbol
        amount: Amount in wei (defaults to 1 ETH worth)
        
    Returns:
        Price quote and route information
    """
    try:
        # Convert symbols to addresses
        from_address = POPULAR_TOKENS.get(from_token.upper(), from_token)
        to_address = POPULAR_TOKENS.get(to_token.upper(), to_token)
        
        url = "https://api.1inch.dev/swap/v6.0/1/quote"
        headers = {
            "Accept": "application/json",
        }
        params = {
            "src": from_address,
            "dst": to_address,
            "amount": amount,
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            return f"Error: 1inch API returned status {response.status_code}"
            
        data = response.json()
        
        # Calculate price
        src_decimals = 18 if from_token.upper() in ["ETH", "WETH"] else 6 if from_token.upper() in ["USDC", "USDT"] else 18
        dst_decimals = 18 if to_token.upper() in ["ETH", "WETH"] else 6 if to_token.upper() in ["USDC", "USDT"] else 18
        
        from_amount = int(amount) / (10 ** src_decimals)
        to_amount = int(data["dstAmount"]) / (10 ** dst_decimals)
        price = to_amount / from_amount
        
        return f"1inch: 1 {from_token} = {price:.6f} {to_token} (via {len(data.get('protocols', [[]]))} routes)"
    except Exception as e:
        return f"Error fetching 1inch price: {str(e)}"


@tool
def get_uniswap_v3_price(from_token: str, to_token: str) -> str:
    """Get token price from Uniswap V3 subgraph.
    
    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        
    Returns:
        Current price from Uniswap V3
    """
    try:
        # Convert symbols to addresses
        from_address = POPULAR_TOKENS.get(from_token.upper(), from_token).lower()
        to_address = POPULAR_TOKENS.get(to_token.upper(), to_token).lower()
        
        # Uniswap V3 subgraph
        url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
        
        # Query for pool data
        query = f"""
        query {{
            pools(
                where: {{
                    token0_in: ["{from_address}", "{to_address}"]
                    token1_in: ["{from_address}", "{to_address}"]
                }}
                first: 5
                orderBy: volumeUSD
                orderDirection: desc
            ) {{
                id
                token0 {{
                    symbol
                    decimals
                }}
                token1 {{
                    symbol
                    decimals
                }}
                token0Price
                token1Price
                volumeUSD
                feeTier
            }}
        }}
        """
        
        response = requests.post(url, json={"query": query})
        
        if response.status_code != 200:
            return f"Error: Uniswap subgraph returned status {response.status_code}"
            
        data = response.json()
        pools = data.get("data", {}).get("pools", [])
        
        if not pools:
            return f"No Uniswap V3 pools found for {from_token}/{to_token}"
            
        # Find the pool with highest volume
        best_pool = pools[0]
        
        # Determine price based on token order
        if best_pool["token0"]["symbol"].upper() == from_token.upper():
            price = float(best_pool["token0Price"])
        else:
            price = float(best_pool["token1Price"])
            
        fee_tier = int(best_pool["feeTier"]) / 10000
        
        return f"Uniswap V3: 1 {from_token} = {price:.6f} {to_token} (fee: {fee_tier}%)"
    except Exception as e:
        return f"Error fetching Uniswap price: {str(e)}"


@tool
def get_sushiswap_price(from_token: str, to_token: str) -> str:
    """Get token price from SushiSwap.
    
    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        
    Returns:
        Current price from SushiSwap
    """
    try:
        # Convert symbols to addresses
        from_address = POPULAR_TOKENS.get(from_token.upper(), from_token).lower()
        to_address = POPULAR_TOKENS.get(to_token.upper(), to_token).lower()
        
        # SushiSwap subgraph
        url = "https://api.thegraph.com/subgraphs/name/sushi-v2/sushiswap-ethereum"
        
        query = f"""
        query {{
            pairs(
                where: {{
                    token0_in: ["{from_address}", "{to_address}"]
                    token1_in: ["{from_address}", "{to_address}"]
                }}
                first: 5
                orderBy: volumeUSD
                orderDirection: desc
            ) {{
                id
                token0 {{
                    symbol
                    decimals
                }}
                token1 {{
                    symbol
                    decimals
                }}
                token0Price
                token1Price
                volumeUSD
            }}
        }}
        """
        
        response = requests.post(url, json={"query": query})
        
        if response.status_code != 200:
            return f"Error: SushiSwap subgraph returned status {response.status_code}"
            
        data = response.json()
        pairs = data.get("data", {}).get("pairs", [])
        
        if not pairs:
            return f"No SushiSwap pairs found for {from_token}/{to_token}"
            
        best_pair = pairs[0]
        
        # Determine price based on token order
        if best_pair["token0"]["symbol"].upper() == from_token.upper():
            price = float(best_pair["token0Price"])
        else:
            price = float(best_pair["token1Price"])
            
        return f"SushiSwap: 1 {from_token} = {price:.6f} {to_token}"
    except Exception as e:
        return f"Error fetching SushiSwap price: {str(e)}"


@tool 
def get_all_dex_prices(from_token: str, to_token: str) -> str:
    """Get prices from multiple DEXs for comparison.
    
    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        
    Returns:
        Prices from all available DEXs
    """
    results = []
    
    # Get prices from each DEX
    inch_price = get_1inch_price(from_token, to_token)
    results.append(inch_price)
    
    uni_price = get_uniswap_v3_price(from_token, to_token)
    results.append(uni_price)
    
    sushi_price = get_sushiswap_price(from_token, to_token)
    results.append(sushi_price)
    
    return "\n".join(results)