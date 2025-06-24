"""DEX price fetching tools for various protocols."""


from langchain_core.tools import tool
from web3 import Web3

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

# Popular Uniswap V3 pool addresses (checksummed)
UNISWAP_V3_POOLS = {
    "WETH/USDC": {
        "address": "0x8ad599c3A0ff1De082011EfdDc58f1908eb6e6D8",
        "fee": 3000,  # 0.3%
        "token0": "USDC",
        "token1": "WETH"
    },
    "WETH/USDT": {
        "address": "0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36",
        "fee": 3000,
        "token0": "USDT", 
        "token1": "WETH"
    },
    "WBTC/WETH": {
        "address": "0xCBCdF9626bC03E24f779434178A73a0B4bad62eD",
        "fee": 3000,
        "token0": "WBTC",
        "token1": "WETH"
    },
    "WETH/WBTC": {  # Same pool, different direction for easier lookup
        "address": "0xCBCdF9626bC03E24f779434178A73a0B4bad62eD",
        "fee": 3000,
        "token0": "WBTC",
        "token1": "WETH"
    },
    "WETH/DAI": {
        "address": "0xC2e9F25Be6257c210d7Adf0D4cD6E3E881ba25f8",
        "fee": 3000,
        "token0": "DAI",
        "token1": "WETH"
    },
    "UNI/WETH": {
        "address": "0x1d42064Fc4Beb5F8aAF85F4617AE8b3b5B8Bd801",
        "fee": 3000,
        "token0": "UNI",
        "token1": "WETH"
    },
    "USDT/WETH": {
        "address": "0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36",
        "fee": 3000,
        "token0": "USDT",
        "token1": "WETH"
    }
}

# Popular SushiSwap pool addresses (checksummed)
SUSHISWAP_POOLS = {
    "WETH/USDC": {
        "address": "0x397FF1542f962076d0BFE58eA045FfA2d347ACa0",
        "token0": "USDC",
        "token1": "WETH"
    },
    "WETH/USDT": {
        "address": "0x06da0fd433C1A5d7a4faa01111c044910A184553",
        "token0": "WETH",
        "token1": "USDT"
    },
    "WETH/DAI": {
        "address": "0xC3D03e4F041Fd4cD388c549Ee2A29a9E5075882f",
        "token0": "DAI",
        "token1": "WETH"
    },
    "WBTC/WETH": {
        "address": "0xCEfF51756c56CeFFCA006cD410B03FFC46dd3a58",
        "token0": "WBTC",
        "token1": "WETH"
    }
}

# Uniswap V3 Quoter contract address on mainnet
UNISWAP_V3_QUOTER = "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6"

# Minimal ABI for Uniswap V3 Quoter
UNISWAP_V3_QUOTER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenIn", "type": "address"},
            {"internalType": "address", "name": "tokenOut", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Minimal ABI for SushiSwap V2 pools
SUSHISWAP_POOL_ABI = [
    {
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
            {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
            {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
        ],
        "stateMutability": "view",
        "type": "function",
        "inputs": []
    },
    {
        "name": "token0",
        "outputs": [{"type": "address", "name": ""}],
        "stateMutability": "view",
        "type": "function",
        "inputs": []
    },
    {
        "name": "token1", 
        "outputs": [{"type": "address", "name": ""}],
        "stateMutability": "view",
        "type": "function",
        "inputs": []
    }
]




def get_token_decimals(token_symbol: str) -> int:
    """Get decimals for a token."""
    decimals_map = {
        "USDC": 6,
        "USDT": 6, 
        "WETH": 18,
        "ETH": 18,
        "WBTC": 8,
        "DAI": 18,
        "UNI": 18,
        "AAVE": 18,
        "LINK": 18,
        "MKR": 18
    }
    return decimals_map.get(token_symbol.upper(), 18)


def find_uniswap_pool(from_token: str, to_token: str) -> dict | None:
    """Find Uniswap V3 pool for a token pair."""
    # Normalize token symbols
    from_token = from_token.upper()
    to_token = to_token.upper()
    
    # Convert ETH to WETH for pool lookup
    if from_token == "ETH":
        from_token = "WETH"
    if to_token == "ETH":
        to_token = "WETH"
    
    # Check both orderings
    pair1 = f"{from_token}/{to_token}"
    pair2 = f"{to_token}/{from_token}"
    
    for pair_key, pool_info in UNISWAP_V3_POOLS.items():
        if pair_key == pair1 or pair_key == pair2:
            return pool_info
    
    return None


@tool
def get_uniswap_v3_price(from_token: str, to_token: str, rpc_url: str = "https://eth.llamarpc.com") -> str:
    """Get token price from Uniswap V3 using the Quoter contract.
    
    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        rpc_url: Ethereum RPC endpoint
        
    Returns:
        Current price from Uniswap V3
    """
    try:
        pool_info = find_uniswap_pool(from_token, to_token)
        if not pool_info:
            return f"No Uniswap V3 pool found for {from_token}/{to_token}"
        
        # Connect to web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"
        
        # Get the Quoter contract
        quoter = w3.eth.contract(address=UNISWAP_V3_QUOTER, abi=UNISWAP_V3_QUOTER_ABI)
        
        # Convert token symbols to addresses
        from_address = POPULAR_TOKENS.get(from_token.upper(), from_token)
        to_address = POPULAR_TOKENS.get(to_token.upper(), to_token)
        
        # Use WETH address for ETH
        if from_address == POPULAR_TOKENS["ETH"]:
            from_address = POPULAR_TOKENS["WETH"]
        if to_address == POPULAR_TOKENS["ETH"]:
            to_address = POPULAR_TOKENS["WETH"]
        
        # Amount to quote (1 token of from_token)
        from_decimals = get_token_decimals(from_token)
        amount_in = 10 ** from_decimals
        
        # Call quoteExactInputSingle
        try:
            amount_out = quoter.functions.quoteExactInputSingle(
                Web3.to_checksum_address(from_address),
                Web3.to_checksum_address(to_address),
                pool_info["fee"],
                amount_in,
                0  # sqrtPriceLimitX96 = 0 means no price limit
            ).call()
            
            # Calculate price
            to_decimals = get_token_decimals(to_token)
            price = amount_out / (10 ** to_decimals)
            
            fee_tier = pool_info["fee"] / 10000
            
            return f"Uniswap V3: 1 {from_token} = {price:.6f} {to_token} (fee: {fee_tier}%)"
        except Exception as quote_error:
            # If quoter fails, it might be because the tokens are in wrong order
            # Try swapping them
            try:
                amount_out = quoter.functions.quoteExactInputSingle(
                    Web3.to_checksum_address(to_address),
                    Web3.to_checksum_address(from_address),
                    pool_info["fee"],
                    10 ** get_token_decimals(to_token),
                    0
                ).call()
                
                # Calculate inverted price
                from_decimals = get_token_decimals(from_token)
                inverted_price = amount_out / (10 ** from_decimals)
                price = 1 / inverted_price
                
                fee_tier = pool_info["fee"] / 10000
                
                return f"Uniswap V3: 1 {from_token} = {price:.6f} {to_token} (fee: {fee_tier}%)"
            except Exception:
                return f"Error getting quote: {str(quote_error)}"
    except Exception as e:
        return f"Error fetching Uniswap price: {str(e)}"


def find_sushiswap_pool(from_token: str, to_token: str) -> dict | None:
    """Find SushiSwap pool for a token pair."""
    # Normalize token symbols
    from_token = from_token.upper()
    to_token = to_token.upper()
    
    # Convert ETH to WETH for pool lookup
    if from_token == "ETH":
        from_token = "WETH"
    if to_token == "ETH":
        to_token = "WETH"
    
    # Check both orderings
    pair1 = f"{from_token}/{to_token}"
    pair2 = f"{to_token}/{from_token}"
    
    for pair_key, pool_info in SUSHISWAP_POOLS.items():
        if pair_key == pair1 or pair_key == pair2:
            return pool_info
    
    return None


@tool
def get_sushiswap_price(from_token: str, to_token: str, rpc_url: str = "https://eth.llamarpc.com") -> str:
    """Get token price directly from SushiSwap pool contract.
    
    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        rpc_url: Ethereum RPC endpoint
        
    Returns:
        Current price from SushiSwap
    """
    try:
        pool_info = find_sushiswap_pool(from_token, to_token)
        if not pool_info:
            return f"No SushiSwap pool found for {from_token}/{to_token}"
        
        # Connect to web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"
        
        # Get pool contract
        pool = w3.eth.contract(address=pool_info["address"], abi=SUSHISWAP_POOL_ABI)
        
        # Get reserves
        reserves = pool.functions.getReserves().call()
        reserve0 = reserves[0]
        reserve1 = reserves[1]
        
        # Get token decimals
        token0_decimals = get_token_decimals(pool_info["token0"])
        token1_decimals = get_token_decimals(pool_info["token1"])
        
        # Normalize token names for comparison
        from_token_normalized = "WETH" if from_token.upper() == "ETH" else from_token.upper()
        to_token_normalized = "WETH" if to_token.upper() == "ETH" else to_token.upper()
        
        # Calculate price based on which token we're converting from/to
        if pool_info["token0"] == from_token_normalized and pool_info["token1"] == to_token_normalized:
            # from_token is token0, to_token is token1
            # Price = reserve1 / reserve0 (adjusted for decimals)
            final_price = (reserve1 / reserve0) * (10**token0_decimals) / (10**token1_decimals)
        elif pool_info["token1"] == from_token_normalized and pool_info["token0"] == to_token_normalized:
            # from_token is token1, to_token is token0
            # Price = reserve0 / reserve1 (adjusted for decimals)
            final_price = (reserve0 / reserve1) * (10**token1_decimals) / (10**token0_decimals)
        else:
            return f"Token pair mismatch in pool for {from_token}/{to_token}"
            
        return f"SushiSwap: 1 {from_token} = {final_price:.6f} {to_token}"
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
    uni_price = get_uniswap_v3_price(from_token, to_token)
    results.append(uni_price)
    
    sushi_price = get_sushiswap_price(from_token, to_token)
    results.append(sushi_price)
    
    return "\n".join(results)