"""Blockchain tools for interacting with Ethereum with config support."""

import logging
import os
from typing import Dict, List, Union

from eth_typing import HexStr
from langchain.tools import StructuredTool
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from web3 import Web3

from ..config_loader import get_config

logger = logging.getLogger(__name__)


class GetBalanceInput(BaseModel):
    """Input for getting balance."""

    address: str = Field(
        description="Ethereum address to check balance for. Use '0xYourWalletAddress' for the agent's wallet"
    )
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


class EthCallInput(BaseModel):
    """Input for eth_call with state override support."""

    to_address: str = Field(description="Contract address to call")
    data: str = Field(description="Encoded function call data (hex string)")
    from_address: str | None = Field(
        default=None,
        description="Address to call from (optional). Use '0xYourWalletAddress' for the agent's wallet",
    )
    block_number: Union[int, str] = Field(
        default="latest",
        description="Block number or 'latest', 'pending', 'earliest'",
    )
    state_overrides: Dict[str, Dict[str, str]] | None = Field(
        default=None,
        description=(
            "State overrides as a dict of address -> state changes. "
            "Each address can have: balance (wei), nonce, code, state (storage slots). "
            "Example: {'0xAddress': {'balance': '0x1234', 'state': {'0x0': '0x5678'}}}"
        ),
    )
    rpc_url: str | None = Field(
        default=None,
        description="RPC URL to use. If not provided, uses default from config",
    )


class EstimateGasInput(BaseModel):
    """Input for estimating gas."""

    from_address: str = Field(
        description="Address sending the transaction. Use '0xYourWalletAddress' for the agent's wallet"
    )
    to_address: str = Field(description="Address receiving the transaction")
    value: str = Field(default="0", description="Value in wei to send")
    data: str = Field(default="0x", description="Transaction data")
    rpc_url: str | None = Field(
        default=None,
        description="RPC URL to use. If not provided, uses default from config",
    )


# Get ERC20 ABI from config (with fallback for compatibility)
def get_erc20_abi():
    """Get ERC20 ABI from config or use default."""
    from ..config_loader import get_config_loader

    loader = get_config_loader()
    abi = loader.get_common_abi("erc20")
    if abi:
        return abi
    # Fallback to default if not in config
    return [
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
    """Get ETH or token balance for an address using configuration.

    Special handling: if address is "0xYourWalletAddress", it will use the
    agent's address derived from AGENT_ETH_KEY environment variable.
    """
    # Handle special "0xYourWalletAddress" keyword
    if address.lower() == "0xyourwalletaddress":
        private_key = os.getenv("AGENT_ETH_KEY")
        if not private_key:
            return {"error": "AGENT_ETH_KEY not found in environment"}
        try:
            # Derive address from private key
            temp_w3 = Web3()
            account = temp_w3.eth.account.from_key(private_key)
            logger.info(f"Using agent address: {account.address}")
            address = account.address
        except Exception as e:
            return {"error": f"Invalid private key in AGENT_ETH_KEY: {str(e)}"}

    # Get RPC URL from config if not provided
    if rpc_url is None:
        config = get_config()
        rpc_url = config.default_chain.rpc_url

    logger.info(f"Connecting to Ethereum node at {rpc_url}")
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
            token_contract = w3.eth.contract(address=token_address, abi=get_erc20_abi())

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
    """Estimate gas for a transaction using configuration.

    Special handling: if from_address is "0xYourWalletAddress", it will use the
    agent's address derived from AGENT_ETH_KEY environment variable.
    """
    # Handle special "0xYourWalletAddress" keyword for from_address
    if from_address.lower() == "0xyourwalletaddress":
        private_key = os.getenv("AGENT_ETH_KEY")
        if not private_key:
            return {"error": "AGENT_ETH_KEY not found in environment"}
        try:
            # Derive address from private key
            temp_w3 = Web3()
            account = temp_w3.eth.account.from_key(private_key)
            from_address = account.address
        except Exception as e:
            return {"error": f"Invalid private key in AGENT_ETH_KEY: {str(e)}"}

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
        default_gas_limit = config.arbitrage.default_gas_limit

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


def eth_call(
    to_address: str,
    data: str,
    from_address: str | None = None,
    block_number: Union[int, str] = "latest",
    state_overrides: Dict[str, Dict[str, str]] | None = None,
    rpc_url: str | None = None,
) -> Dict[str, Union[str, Dict]]:
    """Execute eth_call to read contract state with optional state overrides.

    This is useful for:
    - Reading contract state without sending a transaction
    - Simulating contract calls with modified state
    - Testing "what if" scenarios by overriding balances, storage, etc.

    State overrides allow you to modify:
    - balance: Set ETH balance for an address
    - nonce: Set transaction count
    - code: Replace contract bytecode
    - state: Override specific storage slots

    Special handling: if from_address is "0xYourWalletAddress", it will use the
    agent's address derived from AGENT_ETH_KEY environment variable.
    """
    # Handle special "0xYourWalletAddress" keyword for from_address
    if from_address and from_address.lower() == "0xyourwalletaddress":
        private_key = os.getenv("AGENT_ETH_KEY")
        if not private_key:
            return {"success": False, "error": "AGENT_ETH_KEY not found in environment"}
        try:
            # Derive address from private key
            temp_w3 = Web3()
            account = temp_w3.eth.account.from_key(private_key)
            from_address = account.address
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid private key in AGENT_ETH_KEY: {str(e)}",
            }
    # Get RPC URL from config if not provided
    if rpc_url is None:
        config = get_config()
        rpc_url = config.default_chain.rpc_url

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        return {"error": "Failed to connect to Ethereum node"}

    try:
        to_address = w3.to_checksum_address(to_address)

        # Build the call parameters
        call_params = {
            "to": to_address,
            "data": data,
        }

        if from_address:
            call_params["from"] = w3.to_checksum_address(from_address)

        # Handle state overrides if provided
        if state_overrides:
            # Convert addresses to checksum format and ensure proper hex formatting
            formatted_overrides = {}
            for addr, overrides in state_overrides.items():
                # Handle special "0xYourWalletAddress" in state overrides
                if addr.lower() == "0xyourwalletaddress":
                    if not from_address:
                        # Need to derive it again if not already done
                        private_key = os.getenv("AGENT_ETH_KEY")
                        if private_key:
                            try:
                                account = w3.eth.account.from_key(private_key)
                                addr = account.address
                            except Exception:
                                pass  # Use the original address if derivation fails
                    else:
                        # Use the already derived from_address
                        addr = from_address

                checksummed_addr = w3.to_checksum_address(addr)
                formatted_overrides[checksummed_addr] = {}

                for key, value in overrides.items():
                    if key == "balance":
                        # Ensure balance is hex
                        if isinstance(value, int):
                            formatted_overrides[checksummed_addr][key] = hex(value)
                        else:
                            formatted_overrides[checksummed_addr][key] = value
                    elif key == "nonce":
                        # Ensure nonce is hex
                        if isinstance(value, int):
                            formatted_overrides[checksummed_addr][key] = hex(value)
                        else:
                            formatted_overrides[checksummed_addr][key] = value
                    elif key == "code":
                        # Code should be hex string
                        formatted_overrides[checksummed_addr][key] = value
                    elif key == "state":
                        # State is a dict of storage slot -> value
                        formatted_state = {}
                        for slot, slot_value in value.items():
                            # Ensure slot and value are properly formatted hex
                            if not slot.startswith("0x"):
                                slot = "0x" + slot
                            if isinstance(slot_value, int):
                                slot_value = hex(slot_value)
                            elif not slot_value.startswith("0x"):
                                slot_value = "0x" + slot_value
                            formatted_state[slot] = slot_value
                        formatted_overrides[checksummed_addr][key] = formatted_state
                    else:
                        formatted_overrides[checksummed_addr][key] = value

            # Make the call with state overrides
            result = w3.eth.call(call_params, block_number, formatted_overrides)
        else:
            # Make the call without state overrides
            result = w3.eth.call(call_params, block_number)

        return {
            "success": True,
            "result": "0x" + result.hex(),
            "to": to_address,
            "data": data,
            "block": block_number,
            "state_overrides": state_overrides if state_overrides else None,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


# Create the tools
get_balance_tool = StructuredTool(
    name="get_balance",
    description="Get ETH or token balance for an address. Use '0xYourWalletAddress' to check the agent's wallet. Uses configuration for RPC URL.",
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
    description="Estimate gas for a transaction. Use '0xYourWalletAddress' as from_address to estimate from the agent's wallet. Uses configuration for RPC URL.",
    func=lambda **kwargs: estimate_gas(**kwargs),
    args_schema=EstimateGasInput,
)

eth_call_tool = StructuredTool(
    name="eth_call",
    description=(
        "Execute eth_call to read contract state with optional state overrides. "
        "Use '0xYourWalletAddress' as from_address or in state_overrides to reference the agent's wallet. "
        "Useful for reading contract data, simulating calls with modified state, "
        "and testing 'what if' scenarios by overriding balances, storage, etc."
    ),
    func=lambda **kwargs: eth_call(**kwargs),
    args_schema=EthCallInput,
)


# Compatibility wrapper functions for v1 interface
def get_eth_balance(address: str, rpc_url: str | None = None) -> str:
    """Get ETH balance for a given address (v1 compatibility wrapper)."""
    result = get_balance(address, token_address=None, rpc_url=rpc_url)
    if "error" in result:
        return f"Error: {result['error']}"
    return f"{result['balance_eth']} ETH"


def get_token_balance(
    token_address: str, wallet_address: str, rpc_url: str | None = None
) -> str:
    """Get ERC-20 token balance for a given address (v1 compatibility wrapper)."""
    result = get_balance(wallet_address, token_address=token_address, rpc_url=rpc_url)
    if "error" in result:
        return f"Error: {result['error']}"
    return f"{result['balance_formatted']} {result['symbol']}"


def get_gas_price(rpc_url: str | None = None) -> str:
    """Get current gas price on Ethereum network (v1 compatibility wrapper)."""
    if rpc_url is None:
        config = get_config()
        rpc_url = config.default_chain.rpc_url

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        return "Error: Could not connect to Ethereum network"

    try:
        gas_price_wei = w3.eth.gas_price
        gas_price_gwei = w3.from_wei(gas_price_wei, "gwei")
        return f"{gas_price_gwei} Gwei"
    except Exception as e:
        return f"Error: {str(e)}"


def estimate_transaction_cost(
    gas_limit: int = 200000, rpc_url: str | None = None
) -> str:
    """Estimate transaction cost in ETH based on current gas price (v1 compatibility wrapper)."""
    if rpc_url is None:
        config = get_config()
        rpc_url = config.default_chain.rpc_url

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        return "Error: Could not connect to Ethereum network"

    try:
        gas_price_wei = w3.eth.gas_price
        cost_wei = gas_price_wei * gas_limit
        cost_eth = w3.from_wei(cost_wei, "ether")
        gas_price_gwei = w3.from_wei(gas_price_wei, "gwei")

        return f"Estimated cost: {cost_eth} ETH (at {gas_price_gwei} Gwei)"
    except Exception as e:
        return f"Error: {str(e)}"


# Create v1 compatibility tools with @tool decorator
get_eth_balance = tool(get_eth_balance)
get_token_balance = tool(get_token_balance)
get_gas_price = tool(get_gas_price)
estimate_transaction_cost = tool(estimate_transaction_cost)

# Export all tools
blockchain_tools = [
    get_balance_tool,
    get_transaction_tool,
    get_block_tool,
    estimate_gas_tool,
    eth_call_tool,
]
