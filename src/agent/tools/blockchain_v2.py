"""Blockchain tools for interacting with Ethereum - v2 with config support."""

from typing import Dict, List, Union

from eth_typing import HexStr
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from web3 import Web3

from ..config_loader import get_config


class GetBalanceInput(BaseModel):
    """Input for getting balance."""

    address: str = Field(description="Ethereum address to check balance for")
    token_address: str | None = Field(
        default=None,
        description="Token contract address. If not provided, returns ETH balance",
    )
    rpc_url: str | None = Field(
        default=None,
        description="RPC URL to use. If not provided, uses default from config",
    )


class GetTransactionInput(BaseModel):
    """Input for getting transaction details."""

    tx_hash: str = Field(description="Transaction hash to look up")
    rpc_url: str | None = Field(
        default=None,
        description="RPC URL to use. If not provided, uses default from config",
    )


class GetBlockInput(BaseModel):
    """Input for getting block details."""

    block_number: Union[int, str] = Field(
        default="latest", description="Block number or 'latest', 'pending', 'earliest'"
    )
    rpc_url: str | None = Field(
        default=None,
        description="RPC URL to use. If not provided, uses default from config",
    )


class EstimateGasInput(BaseModel):
    """Input for estimating gas."""

    from_address: str = Field(description="Address sending the transaction")
    to_address: str = Field(description="Address receiving the transaction")
    value: str = Field(default="0", description="Value in wei to send")
    data: str = Field(default="0x", description="Transaction data")
    rpc_url: str | None = Field(
        default=None,
        description="RPC URL to use. If not provided, uses default from config",
    )


# ERC-20 ABI for balance and transfer functions
ERC20_ABI = [
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


def get_balance(
    address: str, token_address: str | None = None, rpc_url: str | None = None
) -> Dict[str, Union[str, float]]:
    """Get ETH or token balance for an address using configuration."""
    # Get RPC URL from config if not provided
    if rpc_url is None:
        config = get_config()
        rpc_url = config.default_chain.rpc_url

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        return {"error": "Failed to connect to Ethereum node"}

    try:
        address = w3.to_checksum_address(address)

        if token_address is None:
            # Get ETH balance
            balance_wei = w3.eth.get_balance(address)
            balance_eth = w3.from_wei(balance_wei, "ether")

            return {
                "address": address,
                "balance_wei": str(balance_wei),
                "balance_eth": float(balance_eth),
                "token": "ETH",
            }
        else:
            # Get token balance
            token_address = w3.to_checksum_address(token_address)
            token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)

            # Get balance
            balance = token_contract.functions.balanceOf(address).call()

            # Try to get decimals and symbol
            try:
                decimals = token_contract.functions.decimals().call()
                symbol = token_contract.functions.symbol().call()
                balance_formatted = balance / (10**decimals)
            except Exception:
                decimals = None
                symbol = "UNKNOWN"
                balance_formatted = balance

            return {
                "address": address,
                "token_address": token_address,
                "balance": str(balance),
                "balance_formatted": float(balance_formatted) if decimals else balance,
                "decimals": decimals,
                "symbol": symbol,
            }

    except Exception as e:
        return {"error": str(e)}


def get_transaction(
    tx_hash: str, rpc_url: str | None = None
) -> Dict[str, Union[str, int, bool]]:
    """Get transaction details by hash using configuration."""
    # Get RPC URL from config if not provided
    if rpc_url is None:
        config = get_config()
        rpc_url = config.default_chain.rpc_url

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        return {"error": "Failed to connect to Ethereum node"}

    try:
        tx = w3.eth.get_transaction(HexStr(tx_hash))
        receipt = w3.eth.get_transaction_receipt(HexStr(tx_hash))

        return {
            "hash": tx["hash"].hex(),
            "from": tx["from"],
            "to": tx["to"] if tx["to"] else None,
            "value": str(tx["value"]),
            "value_eth": float(w3.from_wei(tx["value"], "ether")),
            "gas": tx["gas"],
            "gasPrice": str(tx["gasPrice"]),
            "nonce": tx["nonce"],
            "blockNumber": tx["blockNumber"],
            "blockHash": tx["blockHash"].hex() if tx["blockHash"] else None,
            "status": receipt["status"] if receipt else "pending",
            "gasUsed": receipt["gasUsed"] if receipt else None,
            "effectiveGasPrice": str(receipt["effectiveGasPrice"])
            if receipt and "effectiveGasPrice" in receipt
            else None,
        }
    except Exception as e:
        return {"error": str(e)}


def get_block(
    block_number: Union[int, str] = "latest", rpc_url: str | None = None
) -> Dict[str, Union[str, int, List]]:
    """Get block details by number or tag using configuration."""
    # Get RPC URL from config if not provided
    if rpc_url is None:
        config = get_config()
        rpc_url = config.default_chain.rpc_url

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        return {"error": "Failed to connect to Ethereum node"}

    try:
        block = w3.eth.get_block(block_number)

        return {
            "number": block["number"],
            "hash": block["hash"].hex() if block["hash"] else None,
            "parentHash": block["parentHash"].hex(),
            "timestamp": block["timestamp"],
            "miner": block["miner"],
            "difficulty": str(block["difficulty"]),
            "totalDifficulty": str(block["totalDifficulty"])
            if "totalDifficulty" in block
            else None,
            "size": block["size"],
            "gasLimit": block["gasLimit"],
            "gasUsed": block["gasUsed"],
            "baseFeePerGas": str(block["baseFeePerGas"])
            if "baseFeePerGas" in block
            else None,
            "transactions": len(block["transactions"]),
            "transactionHashes": [
                tx.hex() if isinstance(tx, bytes) else tx
                for tx in block["transactions"][:10]
            ],  # First 10
        }
    except Exception as e:
        return {"error": str(e)}


def estimate_gas(
    from_address: str,
    to_address: str,
    value: str = "0",
    data: str = "0x",
    rpc_url: str | None = None,
) -> Dict[str, Union[str, int]]:
    """Estimate gas for a transaction using configuration."""
    # Get RPC URL from config if not provided
    if rpc_url is None:
        config = get_config()
        rpc_url = config.default_chain.rpc_url

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        return {"error": "Failed to connect to Ethereum node"}

    try:
        from_address = w3.to_checksum_address(from_address)
        to_address = w3.to_checksum_address(to_address)

        # Get current gas price
        gas_price = w3.eth.gas_price

        # Estimate gas
        config = get_config()
        default_gas_limit = 200000  # Could also move this to config

        tx_params = {
            "from": from_address,
            "to": to_address,
            "value": int(value),
            "data": data,
        }

        try:
            estimated_gas = w3.eth.estimate_gas(tx_params)
        except Exception:
            # Use default gas limit if estimation fails
            estimated_gas = default_gas_limit

        # Calculate cost
        estimated_cost_wei = estimated_gas * gas_price
        estimated_cost_eth = w3.from_wei(estimated_cost_wei, "ether")

        return {
            "estimated_gas": estimated_gas,
            "gas_price_wei": str(gas_price),
            "gas_price_gwei": float(w3.from_wei(gas_price, "gwei")),
            "estimated_cost_wei": str(estimated_cost_wei),
            "estimated_cost_eth": float(estimated_cost_eth),
        }
    except Exception as e:
        return {"error": str(e)}


# Create the tools
get_balance_tool = StructuredTool(
    name="get_balance",
    description="Get ETH or token balance for an address. Uses configuration for RPC URL.",
    func=lambda **kwargs: get_balance(**kwargs),
    args_schema=GetBalanceInput,
)

get_transaction_tool = StructuredTool(
    name="get_transaction",
    description="Get transaction details by hash. Uses configuration for RPC URL.",
    func=lambda **kwargs: get_transaction(**kwargs),
    args_schema=GetTransactionInput,
)

get_block_tool = StructuredTool(
    name="get_block",
    description="Get block details by number or tag. Uses configuration for RPC URL.",
    func=lambda **kwargs: get_block(**kwargs),
    args_schema=GetBlockInput,
)

estimate_gas_tool = StructuredTool(
    name="estimate_gas",
    description="Estimate gas for a transaction. Uses configuration for RPC URL.",
    func=lambda **kwargs: estimate_gas(**kwargs),
    args_schema=EstimateGasInput,
)

# Export all tools
blockchain_tools = [
    get_balance_tool,
    get_transaction_tool,
    get_block_tool,
    estimate_gas_tool,
]
