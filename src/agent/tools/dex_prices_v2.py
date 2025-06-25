"""DEX price fetching tools using configuration system."""

from langchain_core.tools import tool
from web3 import Web3

from ..config_loader import get_config, get_config_loader


def get_token_decimals(token_symbol: str) -> int:
    """Get decimals for a token from configuration."""
    config = get_config()
    token = config.tokens.get(token_symbol.upper())
    return token.decimals if token else 18


def find_uniswap_pool(from_token: str, to_token: str) -> dict | None:
    """Find Uniswap V3 pool for a token pair from configuration."""
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

    # Try both token orderings
    pool = loader.get_pool("uniswap_v3", from_token, to_token)
    if pool:
        return {
            "address": pool.address,
            "fee": pool.fee,
            "token0": pool.token0,
            "token1": pool.token1,
        }

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
        pool_info = find_uniswap_pool(from_token, to_token)
        if not pool_info:
            return f"No Uniswap V3 pool found for {from_token}/{to_token}"

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
