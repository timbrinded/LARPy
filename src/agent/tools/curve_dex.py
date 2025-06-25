"""Curve DEX tools with support for both legacy pools and Stableswap-NG."""

from typing import Dict, List, Tuple

from langchain_core.tools import tool
from web3 import Web3

from ..config_loader import get_config, get_config_loader
from .dex_prices import get_token_decimals


def get_curve_native_eth_address() -> str:
    """Get the native ETH address used by Curve."""
    config = get_config()
    eth_token = config.tokens.get("ETH")
    return (
        eth_token.curve_address
        if eth_token and eth_token.curve_address
        else "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
    )


def normalize_token_address_for_curve(token_symbol: str) -> str | None:
    """Get token address normalized for Curve (handles ETH special case)."""
    if token_symbol.upper() == "ETH":
        return get_curve_native_eth_address()

    loader = get_config_loader()
    return loader.get_token_address(token_symbol.upper())


def find_token_index_in_pool(
    pool_contract, token_address: str, num_tokens: int = 8
) -> int | None:
    """Find the index of a token in a Curve pool."""
    for i in range(num_tokens):
        try:
            coin_addr = pool_contract.functions.coins(i).call()
            if coin_addr.lower() == token_address.lower():
                return i
        except Exception:
            # No more coins in this pool
            break
    return None


def get_legacy_curve_price(
    pool_address: str, from_token: str, to_token: str, w3: Web3, pool_abi: List[Dict]
) -> float | None:
    """Get price from a legacy Curve pool."""
    try:
        # Get normalized addresses
        from_addr = normalize_token_address_for_curve(from_token)
        to_addr = normalize_token_address_for_curve(to_token)

        if not from_addr or not to_addr:
            return None

        # Get pool contract
        pool = w3.eth.contract(address=pool_address, abi=pool_abi)

        # Find token indices
        from_idx = find_token_index_in_pool(pool, from_addr)
        to_idx = find_token_index_in_pool(pool, to_addr)

        if from_idx is None or to_idx is None:
            return None

        # Get decimals
        from_decimals = get_token_decimals(from_token)
        to_decimals = get_token_decimals(to_token)

        # Query with 1 token
        amount_in = 10**from_decimals

        # Use get_dy to get output amount
        amount_out = pool.functions.get_dy(from_idx, to_idx, amount_in).call()

        # Calculate price
        price = amount_out / (10**to_decimals)
        return price

    except Exception:
        return None


def get_stableswap_ng_price(
    pool_address: str,
    from_token: str,
    to_token: str,
    w3: Web3,
    views_contract,
    pool_abi: List[Dict],
) -> Tuple[float | None, float | None]:
    """Get price from a Stableswap-NG pool. Returns (spot_price, oracle_price)."""
    try:
        # Get normalized addresses
        from_addr = normalize_token_address_for_curve(from_token)
        to_addr = normalize_token_address_for_curve(to_token)

        if not from_addr or not to_addr:
            return None, None

        # Get pool contract
        pool = w3.eth.contract(address=pool_address, abi=pool_abi)

        # Find token indices
        from_idx = find_token_index_in_pool(pool, from_addr)
        to_idx = find_token_index_in_pool(pool, to_addr)

        if from_idx is None or to_idx is None:
            return None, None

        # Get decimals
        from_decimals = get_token_decimals(from_token)
        to_decimals = get_token_decimals(to_token)

        # Query with 1 token
        amount_in = 10**from_decimals

        # Get spot price using Views contract
        spot_amount_out = views_contract.functions.get_dy(
            pool_address, from_idx, to_idx, amount_in
        ).call()

        spot_price = spot_amount_out / (10**to_decimals)

        # Try to get oracle price
        oracle_price = None
        try:
            # Price oracle returns the price of coin i in terms of coin 0
            if from_idx == 0:
                # Direct oracle price
                oracle_raw = pool.functions.price_oracle(to_idx).call()
                oracle_price = oracle_raw / (10**18)  # Oracle prices are in 18 decimals
            elif to_idx == 0:
                # Inverse of oracle price
                oracle_raw = pool.functions.price_oracle(from_idx).call()
                oracle_price = (10**18) / oracle_raw
            else:
                # Cross rate through coin 0
                oracle_from = pool.functions.price_oracle(from_idx).call()
                oracle_to = pool.functions.price_oracle(to_idx).call()
                oracle_price = oracle_to / oracle_from
        except Exception:
            # Oracle might not be available for all pools
            pass

        return spot_price, oracle_price

    except Exception:
        return None, None


def discover_stableswap_ng_pools(
    from_token: str, to_token: str, w3: Web3, factory_contract, max_search: int = 3
) -> List[str]:
    """Discover Stableswap-NG pools for a token pair using the factory."""
    pools = []

    try:
        # Get normalized addresses
        from_addr = normalize_token_address_for_curve(from_token)
        to_addr = normalize_token_address_for_curve(to_token)

        if not from_addr or not to_addr:
            return pools

        # Search for pools containing this pair
        for i in range(max_search):
            try:
                pool_addr = factory_contract.functions.find_pool_for_coins(
                    from_addr, to_addr, i
                ).call()

                if pool_addr != "0x0000000000000000000000000000000000000000":
                    pools.append(pool_addr)
                else:
                    break
            except Exception:
                break

    except Exception:
        pass

    return pools


@tool
def get_curve_price(
    from_token: str,
    to_token: str,
    include_oracle: bool = False,
    rpc_url: str | None = None,
) -> str:
    """Get token price from Curve Finance supporting both legacy and Stableswap-NG pools.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        include_oracle: Whether to include oracle prices for Stableswap-NG pools
        rpc_url: Ethereum RPC endpoint (optional, uses config default)

    Returns:
        Current price(s) from Curve pools
    """
    try:
        # Get configuration
        config = get_config()

        # Get RPC URL from config if not provided
        if rpc_url is None:
            rpc_url = config.default_chain.rpc_url

        # Connect to web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"

        # Get Curve configuration
        curve_config = config.dexes.get("curve")
        if not curve_config:
            return "Error: Curve configuration not found"

        # Get contract ABIs
        pool_abi = None
        factory_abi = None
        views_abi = None

        for contract in curve_config.contracts:
            if contract.name == "Generic Pool":
                pool_abi = contract.abi
            elif contract.name == "Stableswap-NG Factory":
                factory_abi = contract.abi
            elif contract.name == "Stableswap-NG Views":
                views_abi = contract.abi

        if not pool_abi:
            return "Error: Curve pool ABI not configured"

        # Initialize contracts for Stableswap-NG
        factory_contract = None
        views_contract = None

        if curve_config.factory_address and factory_abi:
            factory_contract = w3.eth.contract(
                address=curve_config.factory_address, abi=factory_abi
            )

        if curve_config.views_address and views_abi:
            views_contract = w3.eth.contract(
                address=curve_config.views_address, abi=views_abi
            )

        results = []

        # Check legacy pools from config
        legacy_pools = [
            p
            for p in curve_config.pools
            if p.pool_type == "legacy"
            and p.tokens
            and from_token.upper() in [t.upper() for t in p.tokens]
            and to_token.upper() in [t.upper() for t in p.tokens]
        ]

        for pool in legacy_pools:
            price = get_legacy_curve_price(
                pool.address, from_token, to_token, w3, pool_abi
            )
            if price:
                pool_name = pool.name or pool.address[:8]
                results.append(
                    f"Curve Legacy {pool_name}: 1 {from_token} = {price:.6f} {to_token}"
                )

        # Check Stableswap-NG pools from config
        ng_pools = [
            p
            for p in curve_config.pools
            if p.pool_type == "stableswap-ng"
            and p.tokens
            and from_token.upper() in [t.upper() for t in p.tokens]
            and to_token.upper() in [t.upper() for t in p.tokens]
        ]

        if views_contract:
            for pool in ng_pools:
                spot_price, oracle_price = get_stableswap_ng_price(
                    pool.address, from_token, to_token, w3, views_contract, pool_abi
                )
                if spot_price:
                    pool_name = pool.name or pool.address[:8]
                    price_str = f"Curve NG {pool_name}: 1 {from_token} = {spot_price:.6f} {to_token}"
                    if include_oracle and oracle_price:
                        price_str += f" (Oracle: {oracle_price:.6f})"
                    results.append(price_str)

        # Discover additional Stableswap-NG pools dynamically
        if factory_contract and views_contract:
            discovered_pools = discover_stableswap_ng_pools(
                from_token, to_token, w3, factory_contract
            )

            # Filter out pools we already checked
            known_addresses = [p.address.lower() for p in ng_pools]
            new_pools = [
                p for p in discovered_pools if p.lower() not in known_addresses
            ]

            for pool_addr in new_pools:
                spot_price, oracle_price = get_stableswap_ng_price(
                    pool_addr, from_token, to_token, w3, views_contract, pool_abi
                )
                if spot_price:
                    price_str = f"Curve NG {pool_addr[:8]}: 1 {from_token} = {spot_price:.6f} {to_token}"
                    if include_oracle and oracle_price:
                        price_str += f" (Oracle: {oracle_price:.6f})"
                    results.append(price_str)

        if results:
            return "\n".join(results)
        else:
            return f"No Curve pools found for {from_token}/{to_token} pair"

    except Exception as e:
        return f"Error: {str(e)}"


@tool
def discover_curve_pools(
    token_a: str | None = None,
    token_b: str | None = None,
    pool_type: str = "all",
    rpc_url: str | None = None,
) -> str:
    """Discover Curve pools, optionally filtered by tokens and pool type.

    Args:
        token_a: First token symbol (optional)
        token_b: Second token symbol (optional)
        pool_type: "legacy", "stableswap-ng", or "all"
        rpc_url: Ethereum RPC endpoint (optional, uses config default)

    Returns:
        List of discovered pools with their details
    """
    try:
        # Get configuration
        config = get_config()

        # Get RPC URL from config if not provided
        if rpc_url is None:
            rpc_url = config.default_chain.rpc_url

        # Connect to web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"

        # Get Curve configuration
        curve_config = config.dexes.get("curve")
        if not curve_config:
            return "Error: Curve configuration not found"

        results = []

        # List configured pools
        if pool_type in ["legacy", "all"]:
            legacy_pools = [p for p in curve_config.pools if p.pool_type == "legacy"]

            for pool in legacy_pools:
                # Filter by tokens if specified
                if token_a and pool.tokens:
                    tokens_upper = [t.upper() for t in pool.tokens]
                    if token_a.upper() not in tokens_upper:
                        continue
                    if token_b and token_b.upper() not in tokens_upper:
                        continue

                pool_info = f"Legacy Pool: {pool.name or 'Unnamed'}\n"
                pool_info += f"  Address: {pool.address}\n"
                pool_info += f"  Tokens: {', '.join(pool.tokens or [])}"
                results.append(pool_info)

        if pool_type in ["stableswap-ng", "all"]:
            ng_pools = [p for p in curve_config.pools if p.pool_type == "stableswap-ng"]

            for pool in ng_pools:
                # Filter by tokens if specified
                if token_a and pool.tokens:
                    tokens_upper = [t.upper() for t in pool.tokens]
                    if token_a.upper() not in tokens_upper:
                        continue
                    if token_b and token_b.upper() not in tokens_upper:
                        continue

                pool_info = f"Stableswap-NG Pool: {pool.name or 'Unnamed'}\n"
                pool_info += f"  Address: {pool.address}\n"
                pool_info += f"  Tokens: {', '.join(pool.tokens or [])}"
                results.append(pool_info)

        # Try to discover more pools if we have factory
        if pool_type in ["stableswap-ng", "all"] and token_a and token_b:
            factory_abi = None
            for contract in curve_config.contracts:
                if contract.name == "Stableswap-NG Factory":
                    factory_abi = contract.abi
                    break

            if curve_config.factory_address and factory_abi:
                factory = w3.eth.contract(
                    address=curve_config.factory_address, abi=factory_abi
                )

                discovered = discover_stableswap_ng_pools(
                    token_a, token_b, w3, factory, max_search=5
                )

                for pool_addr in discovered:
                    # Skip if already in results
                    if any(pool_addr in r for r in results):
                        continue

                    pool_info = "Stableswap-NG Pool (Discovered):\n"
                    pool_info += f"  Address: {pool_addr}\n"
                    pool_info += f"  Tokens: {token_a}/{token_b}"
                    results.append(pool_info)

        if results:
            return "\n\n".join(results)
        else:
            return "No Curve pools found matching the criteria"

    except Exception as e:
        return f"Error: {str(e)}"
