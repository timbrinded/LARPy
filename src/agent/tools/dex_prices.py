"""DEX price fetching tools using configuration system."""

from typing import Dict, List, Tuple

from langchain_core.tools import tool
from web3 import Web3

from ..config_loader import get_config, get_config_loader
from .abi_fetcher import get_abi_fetcher


def get_token_decimals(token_symbol: str) -> int:
    """Get decimals for a token from configuration."""
    config = get_config()
    token = config.tokens.get(token_symbol.upper())
    return token.decimals if token else 18


def find_uniswap_pool(
    from_token: str, to_token: str, fee_tier: int | None = None, w3: Web3 | None = None
) -> dict | None:
    """Find Uniswap V3 pool for a token pair using factory getPool method.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        fee_tier: Fee tier in basis points (100, 500, 3000, 10000). If None, tries common tiers.
        w3: Web3 instance (optional, creates new if not provided)

    Returns:
        Dict with pool info or None if not found
    """
    # Get configuration
    config = get_config()
    loader = get_config_loader()

    # Create web3 instance if not provided
    if w3 is None:
        w3 = Web3(Web3.HTTPProvider(config.default_chain.rpc_url))
        if not w3.is_connected():
            return None

    # Get Uniswap V3 configuration
    uniswap_config = config.dexes.get("uniswap_v3")
    if not uniswap_config or not uniswap_config.factory_address:
        return None

    # Get factory address from config
    factory_address = uniswap_config.factory_address

    # Get ABI fetcher
    abi_fetcher = get_abi_fetcher()

    # Get factory ABI
    factory_abi = abi_fetcher.get_uniswap_v3_factory_abi()

    factory = w3.eth.contract(
        address=Web3.to_checksum_address(factory_address), abi=factory_abi
    )

    # Get token addresses
    from_token_symbol = from_token.upper()
    to_token_symbol = to_token.upper()

    # Convert ETH to WETH for pool lookup
    if from_token_symbol == "ETH":
        from_token_symbol = "WETH"
    if to_token_symbol == "ETH":
        to_token_symbol = "WETH"

    from_address = loader.get_token_address(from_token_symbol)
    to_address = loader.get_token_address(to_token_symbol)

    if not from_address or not to_address:
        return None

    # Common fee tiers for Uniswap V3 (in basis points)
    fee_tiers = [fee_tier] if fee_tier else [100, 500, 3000, 10000]

    for fee in fee_tiers:
        try:
            pool_address = factory.functions.getPool(
                Web3.to_checksum_address(from_address),
                Web3.to_checksum_address(to_address),
                fee,
            ).call()

            if pool_address != "0x0000000000000000000000000000000000":
                # Get pool contract to determine token order
                pool_abi = abi_fetcher.get_uniswap_v3_pool_abi()

                pool = w3.eth.contract(address=pool_address, abi=pool_abi)
                token0_address = pool.functions.token0().call()
                token1_address = pool.functions.token1().call()

                # Map addresses back to symbols
                token0_symbol = None
                token1_symbol = None

                for symbol, token_config in config.tokens.items():
                    if token_config.address.lower() == token0_address.lower():
                        token0_symbol = symbol
                    if token_config.address.lower() == token1_address.lower():
                        token1_symbol = symbol

                return {
                    "address": pool_address,
                    "fee": fee,
                    "token0": token0_symbol or token0_address,
                    "token1": token1_symbol or token1_address,
                }
        except Exception:
            continue

    return None


@tool
def get_uniswap_v3_price(
    from_token: str, to_token: str, rpc_url: str | None = None
) -> str:
    """Get token price from Uniswap V3 using the Quoter contract.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        rpc_url: Ethereum RPC endpoint (optional, uses config default)

    Returns:
        Current price from Uniswap V3
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

        # Find pool using factory
        pool_info = find_uniswap_pool(from_token, to_token, w3=w3)
        if not pool_info:
            return f"No Uniswap V3 pool found for {from_token}/{to_token}"

        # Get the Quoter contract
        uniswap_config = config.dexes.get("uniswap_v3")
        if not uniswap_config or not uniswap_config.quoter_address:
            return "Error: Uniswap V3 Quoter address not configured"

        # Find the quoter ABI from contracts
        quoter_abi = None
        for contract in uniswap_config.contracts:
            if contract.name == "Quoter":
                quoter_abi = contract.abi
                break

        if not quoter_abi:
            return "Error: Uniswap V3 Quoter ABI not configured"

        quoter = w3.eth.contract(address=uniswap_config.quoter_address, abi=quoter_abi)

        # Get token addresses from config
        from_address = loader.get_token_address(from_token.upper())
        to_address = loader.get_token_address(to_token.upper())

        if not from_address or not to_address:
            return f"Error: Token address not found in configuration for {from_token} or {to_token}"

        # Use WETH address for ETH
        if from_token.upper() == "ETH":
            from_address = loader.get_token_address("WETH")
        if to_token.upper() == "ETH":
            to_address = loader.get_token_address("WETH")

        # Amount to quote (1 token of from_token)
        from_decimals = get_token_decimals(from_token)
        amount_in = 10**from_decimals

        # Call quoteExactInputSingle
        try:
            amount_out = quoter.functions.quoteExactInputSingle(
                Web3.to_checksum_address(from_address),
                Web3.to_checksum_address(to_address),
                pool_info["fee"],
                amount_in,
                0,  # sqrtPriceLimitX96 = 0 means no price limit
            ).call()

            # Calculate price
            to_decimals = get_token_decimals(to_token)
            price = amount_out / (10**to_decimals)

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
                    0,
                ).call()

                # Calculate inverted price
                from_decimals = get_token_decimals(from_token)
                inverted_price = amount_out / (10**from_decimals)
                price = 1 / inverted_price

                fee_tier = pool_info["fee"] / 10000

                return f"Uniswap V3: 1 {from_token} = {price:.6f} {to_token} (fee: {fee_tier}%)"
            except Exception:
                return f"Error getting quote: {str(quote_error)}"
    except Exception as e:
        return f"Error fetching Uniswap price: {str(e)}"


def find_sushiswap_pool(from_token: str, to_token: str) -> dict | None:
    """Find SushiSwap pool for a token pair from configuration."""
    # Normalize token symbols
    from_token = from_token.upper()
    to_token = to_token.upper()

    # Convert ETH to WETH for pool lookup
    if from_token == "ETH":
        from_token = "WETH"
    if to_token == "ETH":
        to_token = "WETH"

    # Get pool from configuration
    loader = get_config_loader()
    pool = loader.get_pool("sushiswap", from_token, to_token)

    if pool:
        return {"address": pool.address, "token0": pool.token0, "token1": pool.token1}

    return None


@tool
def get_sushiswap_price(
    from_token: str, to_token: str, rpc_url: str | None = None
) -> str:
    """Get token price directly from SushiSwap pool contract.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol
        rpc_url: Ethereum RPC endpoint (optional, uses config default)

    Returns:
        Current price from SushiSwap
    """
    try:
        pool_info = find_sushiswap_pool(from_token, to_token)
        if not pool_info:
            return f"No SushiSwap pool found for {from_token}/{to_token}"

        # Get configuration
        config = get_config()

        # Get RPC URL from config if not provided
        if rpc_url is None:
            rpc_url = config.default_chain.rpc_url

        # Connect to web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"

        # Get pool ABI from config
        sushi_config = config.dexes.get("sushiswap")
        if not sushi_config:
            return "Error: SushiSwap configuration not found"

        pool_abi = None
        for contract in sushi_config.contracts:
            if contract.name == "Pool":
                pool_abi = contract.abi
                break

        if not pool_abi:
            return "Error: SushiSwap pool ABI not configured"

        # Get pool contract
        pool = w3.eth.contract(address=pool_info["address"], abi=pool_abi)

        # Get reserves
        reserves = pool.functions.getReserves().call()
        reserve0 = reserves[0]
        reserve1 = reserves[1]

        # Get token decimals
        token0_decimals = get_token_decimals(pool_info["token0"])
        token1_decimals = get_token_decimals(pool_info["token1"])

        # Normalize token names for comparison
        from_token_normalized = (
            "WETH" if from_token.upper() == "ETH" else from_token.upper()
        )
        to_token_normalized = "WETH" if to_token.upper() == "ETH" else to_token.upper()

        # Calculate price based on which token we're converting from/to
        if (
            pool_info["token0"] == from_token_normalized
            and pool_info["token1"] == to_token_normalized
        ):
            # from_token is token0, to_token is token1
            # Price = reserve1 / reserve0 (adjusted for decimals)
            final_price = (
                (reserve1 / reserve0) * (10**token0_decimals) / (10**token1_decimals)
            )
        elif (
            pool_info["token1"] == from_token_normalized
            and pool_info["token0"] == to_token_normalized
        ):
            # from_token is token1, to_token is token0
            # Price = reserve0 / reserve1 (adjusted for decimals)
            final_price = (
                (reserve0 / reserve1) * (10**token1_decimals) / (10**token0_decimals)
            )
        else:
            return f"Token pair mismatch in pool for {from_token}/{to_token}"

        return f"SushiSwap: 1 {from_token} = {final_price:.6f} {to_token}"
    except Exception as e:
        return f"Error fetching SushiSwap price: {str(e)}"


# Curve DEX integration
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
    # For ETH, we need to try multiple representations
    if token_symbol.upper() in ["ETH", "WETH"]:
        # Return ETH native address for now, but pools might use WETH
        return get_curve_native_eth_address()

    loader = get_config_loader()
    return loader.get_token_address(token_symbol.upper())


def find_token_index_in_pool(
    pool_contract, token_address: str, num_tokens: int = 8
) -> int | None:
    """Find the index of a token in a Curve pool."""
    # For ETH, we need to check multiple possible addresses
    eth_addresses = []
    if token_address.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
        # Also check for WETH address
        eth_addresses = [
            token_address.lower(),
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH
        ]
    else:
        eth_addresses = [token_address.lower()]

    for i in range(num_tokens):
        try:
            coin_addr = pool_contract.functions.coins(i).call()
            if coin_addr.lower() in eth_addresses:
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


def discover_curve_registry_pools(
    from_token: str, to_token: str, w3: Web3, registry_contract, max_search: int = 5
) -> List[Tuple[str, str]]:
    """Discover pools from the main Curve registry.

    Returns list of (pool_address, pool_type) tuples.
    """
    pools = []

    try:
        # Get normalized addresses
        from_addr = normalize_token_address_for_curve(from_token)
        to_addr = normalize_token_address_for_curve(to_token)

        if not from_addr or not to_addr:
            return pools

        # Main registry can find pools directly
        try:
            # Try the version without index first (returns best pool)
            pool_addr = registry_contract.functions.find_pool_for_coins(
                from_addr, to_addr
            ).call()

            if pool_addr != "0x0000000000000000000000000000000000000000":
                pools.append((pool_addr, "registry"))
        except Exception:
            pass

        # Try indexed search
        for i in range(max_search):
            try:
                pool_addr = registry_contract.functions.find_pool_for_coins(
                    from_addr, to_addr, i
                ).call()

                if pool_addr != "0x0000000000000000000000000000000000000000":
                    if (pool_addr, "registry") not in pools:
                        pools.append((pool_addr, "registry"))
                else:
                    break
            except Exception:
                break

    except Exception:
        pass

    return pools


def find_curve_pools_from_registry(
    from_token: str, to_token: str, w3: Web3, max_search: int = 10
) -> List[str]:
    """Find Curve pools from both main and crypto registries.

    Returns list of unique pool addresses.
    """
    pools = set()
    config = get_config()

    # Get curve config
    curve_config = config.dexes.get("curve")
    if not curve_config:
        return list(pools)

    # Get registry ABIs
    registry_abi = None
    for contract in curve_config.contracts:
        if contract.name == "Registry":
            registry_abi = contract.abi
            break

    if not registry_abi:
        return list(pools)

    # Get normalized addresses
    from_addr = normalize_token_address_for_curve(from_token)
    to_addr = normalize_token_address_for_curve(to_token)

    if not from_addr or not to_addr:
        return list(pools)

    # Check main registry
    if hasattr(curve_config, "registry_address") and curve_config.registry_address:
        try:
            registry = w3.eth.contract(
                address=curve_config.registry_address, abi=registry_abi
            )

            # Search for pools
            for i in range(max_search):
                try:
                    pool_addr = registry.functions.find_pool_for_coins(
                        from_addr, to_addr, i
                    ).call()

                    if pool_addr != "0x0000000000000000000000000000000000000000":
                        pools.add(pool_addr)
                    else:
                        break
                except Exception:
                    break
        except Exception:
            pass

    # Check crypto registry (for ETH pairs)
    if (
        hasattr(curve_config, "crypto_registry_address")
        and curve_config.crypto_registry_address
    ):
        try:
            crypto_registry = w3.eth.contract(
                address=curve_config.crypto_registry_address, abi=registry_abi
            )

            # Search for pools
            for i in range(max_search):
                try:
                    pool_addr = crypto_registry.functions.find_pool_for_coins(
                        from_addr, to_addr, i
                    ).call()

                    if pool_addr != "0x0000000000000000000000000000000000000000":
                        pools.add(pool_addr)
                    else:
                        break
                except Exception:
                    break
        except Exception:
            pass

    return list(pools)


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

        # Get ABI fetcher
        abi_fetcher = get_abi_fetcher()

        # Get contract ABIs from config or use minimal ones
        factory_abi = None
        views_abi = None
        registry_abi = None

        for contract in curve_config.contracts:
            if contract.name == "Stableswap-NG Factory":
                factory_abi = contract.abi
            elif contract.name == "Stableswap-NG Views":
                views_abi = contract.abi
            elif contract.name == "Registry":
                registry_abi = contract.abi

        # Initialize contracts
        factory_contract = None
        views_contract = None
        registry_contract = None

        if curve_config.factory_address and factory_abi:
            factory_contract = w3.eth.contract(
                address=curve_config.factory_address, abi=factory_abi
            )

        if curve_config.views_address and views_abi:
            views_contract = w3.eth.contract(
                address=curve_config.views_address, abi=views_abi
            )

        if (
            hasattr(curve_config, "registry_address")
            and curve_config.registry_address
            and registry_abi
        ):
            registry_contract = w3.eth.contract(
                address=curve_config.registry_address, abi=registry_abi
            )

        results = []

        # Normalize WETH to ETH for Curve pool searching
        search_from_token = (
            "ETH" if from_token.upper() == "WETH" else from_token.upper()
        )
        search_to_token = "ETH" if to_token.upper() == "WETH" else to_token.upper()

        # Check legacy pools from config (including tricrypto) if available
        legacy_pools = []
        ng_pools = []

        if hasattr(curve_config, "pools") and curve_config.pools:
            legacy_pools = [
                p
                for p in curve_config.pools
                if p.pool_type in ["legacy", "tricrypto"]
                and p.tokens
                and search_from_token in [t.upper() for t in p.tokens]
                and search_to_token in [t.upper() for t in p.tokens]
            ]

        for pool in legacy_pools:
            # Get ABI for this specific pool
            pool_abi = abi_fetcher.get_curve_pool_abi(pool.address)
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
                and search_from_token in [t.upper() for t in p.tokens]
                and search_to_token in [t.upper() for t in p.tokens]
            ]

        if views_contract:
            for pool in ng_pools:
                # Get ABI for this specific pool
                pool_abi = abi_fetcher.get_curve_pool_abi(pool.address)
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
                # Get ABI for this specific pool
                pool_abi = abi_fetcher.get_curve_pool_abi(pool_addr)
                spot_price, oracle_price = get_stableswap_ng_price(
                    pool_addr, from_token, to_token, w3, views_contract, pool_abi
                )
                if spot_price:
                    price_str = f"Curve NG {pool_addr[:8]}: 1 {from_token} = {spot_price:.6f} {to_token}"
                    if include_oracle and oracle_price:
                        price_str += f" (Oracle: {oracle_price:.6f})"
                    results.append(price_str)

        # Discover pools from main registry if we have it
        if registry_contract:
            registry_pools = discover_curve_registry_pools(
                from_token, to_token, w3, registry_contract
            )

            # Get all known addresses from previous searches
            known_addresses = (
                [p.address.lower() for p in legacy_pools]
                + [p.address.lower() for p in ng_pools]
                + [p.lower() for p in new_pools]
            )

            for pool_addr, pool_type in registry_pools:
                if pool_addr.lower() not in known_addresses:
                    # Get ABI for this pool
                    pool_abi = abi_fetcher.get_curve_pool_abi(pool_addr)

                    # Try as legacy pool first
                    price = get_legacy_curve_price(
                        pool_addr, from_token, to_token, w3, pool_abi
                    )
                    if price:
                        results.append(
                            f"Curve {pool_addr[:8]}: 1 {from_token} = {price:.6f} {to_token}"
                        )

        # Also check crypto registry for ETH pairs
        crypto_registry_contract = None
        if (
            hasattr(curve_config, "crypto_registry_address")
            and curve_config.crypto_registry_address
            and registry_abi
        ):
            try:
                crypto_registry_contract = w3.eth.contract(
                    address=curve_config.crypto_registry_address, abi=registry_abi
                )
            except Exception:
                pass

        if crypto_registry_contract:
            crypto_pools = discover_curve_registry_pools(
                from_token, to_token, w3, crypto_registry_contract
            )

            # Get all known addresses from all previous searches
            known_addresses = (
                [p.address.lower() for p in legacy_pools]
                + [p.address.lower() for p in ng_pools]
                + [p.lower() for p in new_pools]
                + [p[0].lower() for p in registry_pools]
            )

            for pool_addr, pool_type in crypto_pools:
                if pool_addr.lower() not in known_addresses:
                    # Get ABI for this pool
                    pool_abi = abi_fetcher.get_curve_pool_abi(pool_addr)

                    # Try as legacy pool
                    price = get_legacy_curve_price(
                        pool_addr, from_token, to_token, w3, pool_abi
                    )
                    if price:
                        results.append(
                            f"Curve Crypto {pool_addr[:8]}: 1 {from_token} = {price:.6f} {to_token}"
                        )

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


# Placeholder DEX implementations
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


# Combined price tools
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
    uni_price = get_uniswap_v3_price.func(from_token, to_token)
    results.append(uni_price)

    sushi_price = get_sushiswap_price.func(from_token, to_token)
    results.append(sushi_price)

    # Add Curve price
    curve_price = get_curve_price.func(from_token, to_token)
    results.append(curve_price)

    return "\n".join(results)


def get_stablecoin_substitutes(token: str) -> List[str]:
    """Get fungible stablecoin substitutes for a given token.

    For major stablecoins (USDC, USDT, DAI), returns other stablecoins
    that can be used as substitutes in trading pairs.
    """
    stablecoin_groups = {
        "USDC": ["USDT", "DAI"],
        "USDT": ["USDC", "DAI"],
        "DAI": ["USDC", "USDT"],
    }

    return stablecoin_groups.get(token.upper(), [])


@tool
def get_all_dex_prices_extended(from_token: str, to_token: str) -> str:
    """Get prices from all DEXs including extended protocols.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol

    Returns:
        Prices from all available DEXs
    """
    results = []

    # Get Uniswap V3 price
    uni_price = get_uniswap_v3_price.func(from_token, to_token)
    results.append(uni_price)

    # Get SushiSwap price
    sushi_price = get_sushiswap_price.func(from_token, to_token)
    results.append(sushi_price)

    # Add Curve price
    curve_price = get_curve_price.func(from_token, to_token)
    results.append(curve_price)

    # Add Fluid DEX (when implemented)
    fluid_price = get_fluid_dex_price.func(from_token, to_token)
    results.append(fluid_price)

    # Add Maverick (when implemented)
    maverick_price = get_maverick_price.func(from_token, to_token)
    results.append(maverick_price)

    return "\n".join(results)


@tool
def get_all_dex_prices_with_stablecoin_fungibility(
    from_token: str, to_token: str
) -> str:
    """Get prices from all DEXs including stablecoin substitute paths.

    For stablecoin pairs, this will also check paths through other stablecoins
    to find more liquidity. For example, ETH->USDC will also check ETH->USDT->USDC.

    Args:
        from_token: Source token symbol
        to_token: Destination token symbol

    Returns:
        Direct prices and prices via stablecoin substitutes
    """
    results = []

    # Get direct prices first
    results.append("=== Direct Prices ===")
    direct_prices = get_all_dex_prices_extended.func(from_token, to_token)
    results.append(direct_prices)

    # Check if either token is a stablecoin
    from_substitutes = get_stablecoin_substitutes(from_token)
    to_substitutes = get_stablecoin_substitutes(to_token)

    # If the destination is a stablecoin, check paths through other stablecoins
    if to_substitutes:
        results.append(f"\n=== Prices via stablecoin substitutes for {to_token} ===")
        for substitute in to_substitutes:
            results.append(f"\n--- Via {substitute} ---")
            # Get price from source to substitute
            step1_prices = get_all_dex_prices_extended.func(from_token, substitute)
            results.append(f"Step 1: {from_token} -> {substitute}")
            results.append(step1_prices)

            # Get price from substitute to destination
            step2_prices = get_all_dex_prices_extended.func(substitute, to_token)
            results.append(f"\nStep 2: {substitute} -> {to_token}")
            results.append(step2_prices)

    # If the source is a stablecoin, check reverse paths
    if from_substitutes:
        results.append(
            f"\n=== Prices starting from stablecoin substitutes for {from_token} ==="
        )
        for substitute in from_substitutes:
            results.append(f"\n--- From {substitute} ---")
            # Get price from substitute to destination
            step1_prices = get_all_dex_prices_extended.func(substitute, to_token)
            results.append(f"Step 1: {substitute} -> {to_token}")
            results.append(step1_prices)

            # Get price from source to substitute
            step2_prices = get_all_dex_prices_extended.func(from_token, substitute)
            results.append(f"\nStep 2: {from_token} -> {substitute}")
            results.append(step2_prices)

    return "\n".join(results)
