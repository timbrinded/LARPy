"""Transaction tools for submitting and simulating blockchain transactions."""

import os
from typing import Any, Dict

from eth_typing import HexStr
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from web3 import Web3
from web3.types import TxParams

from ..config_loader import get_config


class SubmitTransactionInput(BaseModel):
    """Input for submitting a transaction to the blockchain."""

    to_address: str = Field(description="The recipient address")
    value: str = Field(default="0", description="Amount of ETH to send in wei")
    data: str = Field(default="0x", description="Transaction data (for contract calls)")
    gas_limit: int | None = Field(
        default=None, description="Gas limit for the transaction"
    )
    gas_price: str | None = Field(
        default=None,
        description="Gas price in wei (optional, will use current if not set)",
    )
    max_fee_per_gas: str | None = Field(
        default=None, description="Max fee per gas for EIP-1559 transactions (wei)"
    )
    max_priority_fee_per_gas: str | None = Field(
        default=None,
        description="Max priority fee per gas for EIP-1559 transactions (wei)",
    )
    private_key: str | None = Field(
        default=None,
        description="Private key of the sender. If not provided, uses AGENT_ETH_KEY from environment",
    )
    rpc_url: str | None = Field(
        default=None,
        description="RPC URL to use. If not provided, uses default from config",
    )
    nonce: int | None = Field(
        default=None, description="Transaction nonce (optional, will fetch if not set)"
    )


class AlchemySimulateInput(BaseModel):
    """Input for simulating transactions using Alchemy's simulateAssetChanges."""

    to_address: str = Field(description="The recipient address")
    value: str = Field(default="0", description="Amount of ETH to send in wei")
    data: str = Field(default="0x", description="Transaction data (for contract calls)")
    from_address: str | None = Field(
        default=None,
        description="The sender address. If not provided, derives from AGENT_ETH_KEY environment variable",
    )
    alchemy_api_key: str | None = Field(
        default=None,
        description="Alchemy API key. If not provided, uses ALCHEMY_API_KEY from environment",
    )
    network: str = Field(
        default="eth-mainnet",
        description="Network to simulate on (e.g., eth-mainnet, eth-sepolia)",
    )


def submit_transaction(
    to_address: str,
    value: str = "0",
    data: str = "0x",
    gas_limit: int | None = None,
    gas_price: str | None = None,
    max_fee_per_gas: str | None = None,
    max_priority_fee_per_gas: str | None = None,
    private_key: str | None = None,
    rpc_url: str | None = None,
    nonce: int | None = None,
) -> Dict[str, Any]:
    """Submit a transaction to the blockchain.

    SECURITY WARNING: This function handles private keys. Never log or expose private keys.
    """
    # Get RPC URL from config if not provided
    if rpc_url is None:
        config = get_config()
        rpc_url = config.default_chain.rpc_url

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        return {"error": "Failed to connect to Ethereum node"}

    try:
        # Get private key from environment if not provided
        if not private_key:
            private_key = os.getenv("AGENT_ETH_KEY")
            if not private_key:
                return {
                    "error": "No private key provided and AGENT_ETH_KEY not found in environment",
                    "success": False,
                }

        # Get account from private key
        account = w3.eth.account.from_key(private_key)
        from_address = account.address

        # Validate addresses
        to_address = w3.to_checksum_address(to_address)

        # Build transaction
        tx: TxParams = {
            "from": from_address,
            "to": to_address,
            "value": int(value),
            "data": HexStr(data),
        }

        # Get nonce if not provided
        if nonce is None:
            tx["nonce"] = w3.eth.get_transaction_count(from_address)
        else:
            tx["nonce"] = nonce

        # Handle gas settings
        if gas_limit is None:
            # Estimate gas
            try:
                tx["gas"] = w3.eth.estimate_gas(tx)
                # Add 20% buffer for safety
                tx["gas"] = int(tx["gas"] * 1.2)
            except Exception:
                # Use default from config if estimation fails
                config = get_config()
                tx["gas"] = config.arbitrage.default_gas_limit
        else:
            tx["gas"] = gas_limit

        # Handle gas price (EIP-1559 vs legacy)
        if max_fee_per_gas and max_priority_fee_per_gas:
            # EIP-1559 transaction
            tx["maxFeePerGas"] = int(max_fee_per_gas)
            tx["maxPriorityFeePerGas"] = int(max_priority_fee_per_gas)
        elif gas_price:
            # Legacy transaction
            tx["gasPrice"] = int(gas_price)
        else:
            # Get current gas price
            current_gas_price = w3.eth.gas_price
            tx["gasPrice"] = current_gas_price

        # Get chain ID
        tx["chainId"] = w3.eth.chain_id

        # Sign transaction
        signed_tx = account.sign_transaction(tx)

        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Get transaction receipt (wait for confirmation)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            "success": True,
            "transaction_hash": tx_hash.hex(),
            "from": from_address,
            "to": to_address,
            "value": value,
            "gas_used": receipt["gasUsed"],
            "gas_price": str(receipt.get("effectiveGasPrice", tx.get("gasPrice", 0))),
            "block_number": receipt["blockNumber"],
            "status": receipt["status"],  # 1 for success, 0 for failure
        }

    except Exception as e:
        return {"error": str(e), "success": False}


def alchemy_simulate_asset_changes(
    to_address: str,
    value: str = "0",
    data: str = "0x",
    from_address: str | None = None,
    alchemy_api_key: str | None = None,
    network: str = "eth-mainnet",
) -> Dict[str, Any]:
    """Simulate a transaction using Alchemy's simulateAssetChanges API.

    This simulates the asset changes that would occur if the transaction were executed,
    without actually submitting it to the blockchain.
    """
    import requests

    # Get Alchemy API key from environment if not provided
    if not alchemy_api_key:
        alchemy_api_key = os.getenv("ALCHEMY_API_KEY")
        if not alchemy_api_key:
            return {
                "success": False,
                "error": "No Alchemy API key provided and ALCHEMY_API_KEY not found in environment",
            }

    # Get from_address from private key if not provided
    if not from_address:
        private_key = os.getenv("AGENT_ETH_KEY")
        if not private_key:
            return {
                "success": False,
                "error": "No from_address provided and AGENT_ETH_KEY not found in environment",
            }
        try:
            # Derive address from private key
            w3 = Web3()
            account = w3.eth.account.from_key(private_key)
            from_address = account.address
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid private key in AGENT_ETH_KEY: {str(e)}",
            }

    # Alchemy API endpoint
    url = f"https://{network}.g.alchemy.com/v2/{alchemy_api_key}"

    try:
        # Validate addresses
        w3 = Web3()
        from_address = w3.to_checksum_address(from_address)
        to_address = w3.to_checksum_address(to_address)

        # Build the request
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_simulateAssetChanges",
            "params": [
                {
                    "from": from_address,
                    "to": to_address,
                    "value": hex(int(value)) if value != "0x" else "0x0",
                    "data": data,
                }
            ],
        }

        # Make the request
        response = requests.post(url, json=payload)
        result = response.json()

        if "error" in result:
            return {
                "success": False,
                "error": result["error"].get("message", "Unknown error"),
                "error_code": result["error"].get("code", -1),
            }

        # Extract asset changes
        if "result" in result:
            changes = result["result"].get("changes", [])

            # Format the changes for better readability
            formatted_changes = []
            for change in changes:
                formatted_change = {
                    "asset_type": change.get("assetType", "UNKNOWN"),
                    "from": change.get("from"),
                    "to": change.get("to"),
                    "amount": change.get("amount"),
                }

                # Add token-specific information if available
                if "contractAddress" in change:
                    formatted_change["contract_address"] = change["contractAddress"]
                if "tokenId" in change:
                    formatted_change["token_id"] = change["tokenId"]
                if "symbol" in change:
                    formatted_change["symbol"] = change["symbol"]
                if "decimals" in change:
                    formatted_change["decimals"] = change["decimals"]
                    # Calculate human-readable amount for ERC20 tokens
                    if change.get("assetType") == "ERC20" and "amount" in change:
                        try:
                            raw_amount = (
                                int(change["amount"], 16)
                                if isinstance(change["amount"], str)
                                else change["amount"]
                            )
                            formatted_change["amount_formatted"] = raw_amount / (
                                10 ** change["decimals"]
                            )
                        except Exception:
                            pass

                formatted_changes.append(formatted_change)

            # Get gas estimation if available
            gas_used = result["result"].get("gasUsed")

            return {
                "success": True,
                "changes": formatted_changes,
                "gas_used": gas_used,
                "raw_result": result["result"],
            }
        else:
            return {
                "success": False,
                "error": "No result in response",
                "raw_response": result,
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


# Create the tools
submit_transaction_tool = StructuredTool(
    name="submit_transaction",
    description="""Submit a transaction to the blockchain. This can be used for:
    - Sending ETH transfers
    - Calling smart contract functions
    - Executing arbitrage transactions
    
    SECURITY: Private key defaults to AGENT_ETH_KEY from environment if not provided.
    NEVER log or expose private keys.
    Returns transaction hash and receipt details.""",
    func=lambda **kwargs: submit_transaction(**kwargs),
    args_schema=SubmitTransactionInput,
)

alchemy_simulate_tool = StructuredTool(
    name="alchemy_simulate_asset_changes",
    description="""Simulate a transaction using Alchemy's simulateAssetChanges API to preview:
    - Token transfers that would occur
    - NFT transfers
    - ETH balance changes
    - Gas consumption
    
    This is useful for testing transactions before submitting them.
    Uses ALCHEMY_API_KEY from environment if not provided.""",
    func=lambda **kwargs: alchemy_simulate_asset_changes(**kwargs),
    args_schema=AlchemySimulateInput,
)

# Export the tools
transaction_tools = [submit_transaction_tool, alchemy_simulate_tool]
