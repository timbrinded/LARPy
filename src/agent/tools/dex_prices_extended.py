"""Extended DEX price tools (Curve, Fluid, Maverick) using configuration system."""

from langchain_core.tools import tool

from ..config_loader import get_config

# Import the new Curve implementation
from .curve_dex import get_curve_price


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
