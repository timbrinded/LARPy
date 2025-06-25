"""Blockchain interaction tools for Ethereum."""

from langchain_core.tools import tool
from web3 import Web3


@tool
def get_eth_balance(address: str, rpc_url: str = "https://eth.llamarpc.com") -> str:
    """Get ETH balance for a given address.

    Args:
        address: Ethereum address to check
        rpc_url: RPC endpoint URL (defaults to public RPC)

    Returns:
        Balance in ETH as a string
    """
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"

        if not Web3.is_address(address):
            return f"Error: Invalid Ethereum address: {address}"

        balance_wei = w3.eth.get_balance(address)
        balance_eth = w3.from_wei(balance_wei, "ether")
        return f"{balance_eth} ETH"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_token_balance(
    token_address: str, wallet_address: str, rpc_url: str = "https://eth.llamarpc.com"
) -> str:
    """Get ERC-20 token balance for a given address.

    Args:
        token_address: ERC-20 token contract address
        wallet_address: Wallet address to check
        rpc_url: RPC endpoint URL

    Returns:
        Token balance with decimals applied
    """
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"

        # Minimal ERC-20 ABI for balanceOf and decimals
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function",
            },
        ]

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=erc20_abi
        )

        balance = contract.functions.balanceOf(
            Web3.to_checksum_address(wallet_address)
        ).call()
        decimals = contract.functions.decimals().call()
        symbol = contract.functions.symbol().call()

        adjusted_balance = balance / (10**decimals)
        return f"{adjusted_balance} {symbol}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_gas_price(rpc_url: str = "https://eth.llamarpc.com") -> str:
    """Get current gas price on Ethereum network.

    Args:
        rpc_url: RPC endpoint URL

    Returns:
        Gas price in Gwei
    """
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"

        gas_price_wei = w3.eth.gas_price
        gas_price_gwei = w3.from_wei(gas_price_wei, "gwei")
        return f"{gas_price_gwei} Gwei"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def estimate_transaction_cost(
    gas_limit: int = 200000, rpc_url: str = "https://eth.llamarpc.com"
) -> str:
    """Estimate transaction cost in ETH based on current gas price.

    Args:
        gas_limit: Estimated gas limit for transaction
        rpc_url: RPC endpoint URL

    Returns:
        Estimated cost in ETH
    """
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network"

        gas_price_wei = w3.eth.gas_price
        cost_wei = gas_price_wei * gas_limit
        cost_eth = w3.from_wei(cost_wei, "ether")
        gas_price_gwei = w3.from_wei(gas_price_wei, "gwei")

        return f"Estimated cost: {cost_eth} ETH (at {gas_price_gwei} Gwei)"
    except Exception as e:
        return f"Error: {str(e)}"
