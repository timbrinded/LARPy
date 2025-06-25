"""Extended DEX price fetching tools for Curve, Fluid, and Maverick."""

from langchain_core.tools import tool
from web3 import Web3

from agent.tools.dex_prices import get_token_decimals

# CurveRouterNG contract address on mainnet
CURVE_ROUTER_NG = "0x99a58482BD75cbab83b27EC03CA68fF489b5788f"

# Token addresses for common tokens
CURVE_TOKEN_ADDRESSES = {
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "ETH": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    "stETH": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
    "frxETH": "0x5E8422345238F34275888049021821E8E08CAa1f",
    "crvUSD": "0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E",
}

# Minimal ABI for CurveRouterNG
CURVE_ROUTER_NG_ABI = [
    {
        "name": "get_dy",
        "inputs": [
            {"name": "route", "type": "address[9]"},
            {"name": "swap_params", "type": "uint256[3][4]"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "name": "get_dx",
        "inputs": [
            {"name": "route", "type": "address[9]"},
            {"name": "swap_params", "type": "uint256[3][4]"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "name": "get_best_rate",
        "inputs": [
            {"name": "_from", "type": "address"},
            {"name": "_to", "type": "address"},
            {"name": "_amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "address"}, {"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Popular Curve pools for building routes
CURVE_POOLS = {
    "3pool": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
    "tricryptoUSDT": "0xD51a44d3FaE010294C616388b506AcdA1bfAAE46",
    "tricryptoUSDC": "0x0c0e5f2fF0ff18a3Be9b835635039256dC4B4963",
    "stETH/ETH": "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022",
    "frxETH/ETH": "0xa1F8A6807c402E4A15ef4EBa36528A3FED24E577",
    "crvUSD/USDC": "0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E",
}

# Token indices in popular pools
POOL_TOKEN_INDICES = {
    "tricryptoUSDT": {"USDT": 0, "WBTC": 1, "WETH": 2},
    "tricryptoUSDC": {"USDC": 0, "WBTC": 1, "WETH": 2},
    "3pool": {"DAI": 0, "USDC": 1, "USDT": 2},
}

# Maverick Protocol - we'll need to discover pools dynamically
MAVERICK_FACTORY = (
    "0xEb6625D65a0553c9dBc64449e56abFe519bd9c9B"  # Maverick Factory on mainnet
)

# Minimal ABI for Maverick pools (simplified)
MAVERICK_POOL_ABI = [
    {
        "name": "getReserves",
        "outputs": [
            {"name": "reserve0", "type": "uint256"},
            {"name": "reserve1", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
        "inputs": [],
    },
    {
        "name": "tokenA",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
        "inputs": [],
    },
    {
        "name": "tokenB",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
        "inputs": [],
    },
]


def build_curve_route(from_token: str, to_token: str, pool_address: str) -> list:
    """Build route array for CurveRouterNG."""
    # Get token addresses
    from_address = CURVE_TOKEN_ADDRESSES.get(from_token.upper())
    to_address = CURVE_TOKEN_ADDRESSES.get(to_token.upper())

    if not from_address or not to_address:
        return None

    # For CurveRouterNG, use the native ETH address (0xEeee...) for ETH swaps
    # The router handles ETH<->WETH conversion internally

    # Build route: [from_token, pool, to_token, 0x0, 0x0, ...]
    route = [from_address, pool_address, to_address] + [
        "0x0000000000000000000000000000000000000000"
    ] * 6
    return route[:9]  # Route must be exactly 9 addresses


@tool
def get_curve_price(
    from_token: str, to_token: str, rpc_url: str = "https://eth.llamarpc.com"
) -> str:
    """Get token price from Curve Finance using CurveRouterNG.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        rpc_url: Ethereum RPC endpoint

    Returns:
        Current price from Curve
    """
    try:
        # Connect to web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"

        # Get the RouterNG contract
        router = w3.eth.contract(address=CURVE_ROUTER_NG, abi=CURVE_ROUTER_NG_ABI)

        # Try different pools to find the best route
        best_price = 0
        best_pool = None

        # Check common pools that might have this pair
        pools_to_check = []

        # For ETH/WETH to stablecoins, check tricrypto pools
        if from_token.upper() in ["ETH", "WETH"] and to_token.upper() in [
            "USDC",
            "USDT",
            "DAI",
        ]:
            if to_token.upper() == "USDT":
                pools_to_check.append("tricryptoUSDT")
            elif to_token.upper() == "USDC":
                pools_to_check.append("tricryptoUSDC")
        elif to_token.upper() in ["ETH", "WETH"] and from_token.upper() in [
            "USDC",
            "USDT",
            "DAI",
        ]:
            if from_token.upper() == "USDT":
                pools_to_check.append("tricryptoUSDT")
            elif from_token.upper() == "USDC":
                pools_to_check.append("tricryptoUSDC")

        # For stablecoin to stablecoin
        if from_token.upper() in ["USDC", "USDT", "DAI"] and to_token.upper() in [
            "USDC",
            "USDT",
            "DAI",
        ]:
            pools_to_check.append("3pool")

        # For ETH liquid staking derivatives
        if from_token.upper() in [
            "ETH",
            "WETH",
            "stETH",
            "frxETH",
        ] and to_token.upper() in ["ETH", "WETH", "stETH", "frxETH"]:
            pools_to_check.extend(["stETH/ETH", "frxETH/ETH"])

        # Amount to query (1 token)
        from_decimals = get_token_decimals(from_token)
        amount_in = 10**from_decimals

        for pool_name in pools_to_check:
            if pool_name not in CURVE_POOLS:
                continue

            pool_address = CURVE_POOLS[pool_name]
            route = build_curve_route(from_token, to_token, pool_address)

            if not route:
                continue

            # Build swap params - [i, j, swap_type] for each hop
            # Need to determine correct token indices based on pool
            i, j = 0, 1  # Default indices

            # Get correct indices for known pools
            if pool_name in POOL_TOKEN_INDICES:
                indices = POOL_TOKEN_INDICES[pool_name]
                from_key = from_token.upper()
                to_key = to_token.upper()

                # Handle ETH/WETH mapping
                if from_key == "ETH":
                    from_key = "WETH"
                if to_key == "ETH":
                    to_key = "WETH"

                if from_key in indices and to_key in indices:
                    i = indices[from_key]
                    j = indices[to_key]
                else:
                    continue  # Skip this pool if tokens not found

            swap_params = [
                [i, j, 2],  # Use 2 for crypto swap pools
                [0, 0, 0],
                [0, 0, 0],
                [0, 0, 0],
            ]

            try:
                # Try to get quote from RouterNG
                amount_out = router.functions.get_dy(
                    route, swap_params, amount_in
                ).call()

                if amount_out > 0:
                    to_decimals = get_token_decimals(to_token)
                    price = amount_out / (10**to_decimals)

                    if price > best_price:
                        best_price = price
                        best_pool = pool_name
            except Exception:
                # This pool doesn't support this pair, try next
                continue

        if best_price > 0:
            return (
                f"Curve: 1 {from_token} = {best_price:.6f} {to_token} (via {best_pool})"
            )
        else:
            # Try using get_best_rate as fallback
            try:
                from_addr = CURVE_TOKEN_ADDRESSES.get(from_token.upper())
                to_addr = CURVE_TOKEN_ADDRESSES.get(to_token.upper())

                if from_addr and to_addr:
                    # Try get_best_rate
                    pool_address, amount_out = router.functions.get_best_rate(
                        from_addr, to_addr, amount_in
                    ).call()

                    if amount_out > 0:
                        to_decimals = get_token_decimals(to_token)
                        price = amount_out / (10**to_decimals)
                        return f"Curve: 1 {from_token} = {price:.6f} {to_token} (via best rate)"
            except Exception:
                pass

            return f"No Curve route found for {from_token}/{to_token}"

    except Exception as e:
        return f"Error fetching Curve price: {str(e)}"


@tool
def get_fluid_dex_price(
    from_token: str, to_token: str, rpc_url: str = "https://eth.llamarpc.com"
) -> str:
    """Get token price from Fluid DEX.

    Note: Fluid DEX is a new protocol with dynamic pool addresses.
    This is a placeholder that would need pool discovery logic.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        rpc_url: Ethereum RPC endpoint

    Returns:
        Current price from Fluid DEX or unavailable message
    """
    return f"Fluid DEX integration pending - requires dynamic pool discovery for {from_token}/{to_token}"


@tool
def get_maverick_price(
    from_token: str, to_token: str, rpc_url: str = "https://eth.llamarpc.com"
) -> str:
    """Get token price from Maverick Protocol.

    Note: Maverick uses dynamic pools with different fee tiers.
    This is a simplified implementation.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        rpc_url: Ethereum RPC endpoint

    Returns:
        Current price from Maverick or unavailable message
    """
    return f"Maverick integration pending - requires pool discovery via factory for {from_token}/{to_token}"


@tool
def get_all_dex_prices_extended(from_token: str, to_token: str) -> str:
    """Get prices from all DEXs including extended protocols.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol

    Returns:
        Prices from all available DEXs
    """
    # Import the price functions directly (not as tools)
    from agent.tools.dex_prices import get_sushiswap_price, get_uniswap_v3_price

    results = []

    # Get Uniswap V3 price
    uni_price = get_uniswap_v3_price.func(from_token, to_token)
    results.append(uni_price)

    # Get SushiSwap price
    sushi_price = get_sushiswap_price.func(from_token, to_token)
    results.append(sushi_price)

    # Add Curve price
    curve_price = get_curve_price.func(from_token, to_token)
    if "No Curve pool found" not in curve_price:
        results.append(curve_price)

    # Add Fluid DEX (when implemented)
    fluid_price = get_fluid_dex_price.func(from_token, to_token)
    if "pending" not in fluid_price:
        results.append(fluid_price)

    # Add Maverick (when implemented)
    maverick_price = get_maverick_price.func(from_token, to_token)
    if "pending" not in maverick_price:
        results.append(maverick_price)

    return "\n".join(results)
