"""Extended DEX price tools (Curve, Fluid, Maverick) using configuration system."""

from langchain_core.tools import tool
from web3 import Web3

from ..config_loader import get_config, get_config_loader
from .dex_prices import get_token_decimals


def build_curve_route(from_token: str, to_token: str, pool_address: str) -> list | None:
    """Build route array for CurveRouterNG."""
    # Get token addresses from config
    loader = get_config_loader()
    from_address = loader.get_token_address(from_token.upper())
    to_address = loader.get_token_address(to_token.upper())

    # Special handling for ETH - use the native ETH address for Curve
    if from_token.upper() == "ETH":
        config = get_config()
        eth_token = config.tokens.get("ETH")
        from_address = (
            eth_token.curve_address
            if eth_token and eth_token.curve_address
            else "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
        )
    if to_token.upper() == "ETH":
        config = get_config()
        eth_token = config.tokens.get("ETH")
        to_address = (
            eth_token.curve_address
            if eth_token and eth_token.curve_address
            else "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
        )

    if not from_address or not to_address:
        return None

    # Build route: [from_token, pool, to_token, 0x0, 0x0, ...]
    route = [from_address, pool_address, to_address] + [
        "0x0000000000000000000000000000000000000000"
    ] * 6
    return route[:9]  # Route must be exactly 9 addresses


@tool
def get_curve_price(from_token: str, to_token: str, rpc_url: str | None = None) -> str:
    """Get token price from Curve Finance using CurveRouterNG.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        rpc_url: Ethereum RPC endpoint (optional, uses config default)

    Returns:
        Current price from Curve
    """
    try:
        # Get configuration
        config = get_config()
        loader = get_config_loader()

        # Get RPC URL from config if not provided
        if rpc_url is None:
            rpc_url = config.default_chain.rpc_url

        # Connect to web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"

        # Get Curve configuration
        curve_config = config.dexes.get("curve")
        if not curve_config or not curve_config.router_address:
            return "Error: Curve router address not configured"

        # Get router ABI
        router_abi = None
        for contract in curve_config.contracts:
            if contract.name == "Router NG":
                router_abi = contract.abi
                break

        if not router_abi:
            return "Error: Curve Router NG ABI not configured"

        # Get the RouterNG contract
        router = w3.eth.contract(address=curve_config.router_address, abi=router_abi)

        # Try different pools to find the best route
        best_price = 0

        # Get all Curve pools from config
        curve_pools = [p for p in curve_config.pools if p.dex == "curve"]

        # Amount to query (1 token)
        from_decimals = get_token_decimals(from_token)
        amount_in = 10**from_decimals

        for pool in curve_pools:
            # Check if this pool might have the token pair
            pool_tokens = {pool.token0, pool.token1}
            from_normalized = (
                "WETH" if from_token.upper() == "ETH" else from_token.upper()
            )
            to_normalized = "WETH" if to_token.upper() == "ETH" else to_token.upper()

            # Check if pool contains both tokens (in any order)
            if from_normalized in pool_tokens and to_normalized in pool_tokens:
                route = build_curve_route(from_token, to_token, pool.address)
                if not route:
                    continue

                # Determine token indices
                i = 0 if pool.token0 == from_normalized else 1
                j = 1 if pool.token1 == to_normalized else 0

                swap_params = [
                    [i, j, 2],  # Use 2 for crypto swap pools, 1 for stable
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
                except Exception:
                    # This pool doesn't support this pair, try next
                    continue

        if best_price > 0:
            return f"Curve: 1 {from_token} = {best_price:.6f} {to_token} (via pool)"
        else:
            # Try using get_best_rate as fallback
            try:
                from_addr = loader.get_token_address(from_token.upper())
                to_addr = loader.get_token_address(to_token.upper())

                # Special handling for ETH
                if from_token.upper() == "ETH":
                    config = get_config()
                    eth_token = config.tokens.get("ETH")
                    from_addr = (
                        eth_token.curve_address
                        if eth_token and eth_token.curve_address
                        else "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
                    )
                if to_token.upper() == "ETH":
                    config = get_config()
                    eth_token = config.tokens.get("ETH")
                    to_addr = (
                        eth_token.curve_address
                        if eth_token and eth_token.curve_address
                        else "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
                    )

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
    from_token: str, to_token: str, rpc_url: str | None = None
) -> str:
    """Get token price from Fluid DEX.

    Note: Fluid DEX is a new protocol with dynamic pool addresses.
    This is a placeholder that would need pool discovery logic.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        rpc_url: Ethereum RPC endpoint (optional, uses config default)

    Returns:
        Current price from Fluid DEX or unavailable message
    """
    return f"Fluid DEX integration pending - requires dynamic pool discovery for {from_token}/{to_token}"


@tool
def get_maverick_price(
    from_token: str, to_token: str, rpc_url: str | None = None
) -> str:
    """Get token price from Maverick Protocol.

    Note: Maverick uses dynamic pools with different fee tiers.
    This is a simplified implementation.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        rpc_url: Ethereum RPC endpoint (optional, uses config default)

    Returns:
        Current price from Maverick or unavailable message
    """
    # Get configuration
    config = get_config()
    maverick_config = config.dexes.get("maverick")

    if maverick_config and maverick_config.factory_address:
        return f"Maverick integration pending - requires pool discovery via factory at {maverick_config.factory_address}"
    else:
        return "Maverick integration pending - factory address not configured"


@tool
def get_all_dex_prices_extended(from_token: str, to_token: str) -> str:
    """Get prices from all DEXs including extended protocols.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol

    Returns:
        Prices from all available DEXs
    """
    # Import the basic price functions from v2
    from .dex_prices import get_sushiswap_price, get_uniswap_v3_price

    results = []

    # Get Uniswap V3 price
    uni_price = get_uniswap_v3_price.func(from_token, to_token)
    results.append(uni_price)

    # Get SushiSwap price
    sushi_price = get_sushiswap_price.func(from_token, to_token)
    results.append(sushi_price)

    # Add Curve price
    curve_price = get_curve_price.func(from_token, to_token)
    if "No Curve" not in curve_price:
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
