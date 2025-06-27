"""Tools that are aware of the agent's wallet address."""

from langchain_core.tools import tool
from web3 import Web3

from .wallet_utils import get_agent_address


@tool
def get_my_balance(token_address: str | None = None) -> str:
    """Get the balance of the agent's wallet.
    
    Args:
        token_address: ERC20 token contract address. If None, returns ETH balance.
        
    Returns:
        Balance as a string with units
    """
    try:
        from ..config_loader import get_config_loader
        
        loader = get_config_loader()
        config = loader.load()
        rpc_url = config.default_chain.rpc_url
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        agent_address = get_agent_address()
        
        if token_address is None:
            # Get ETH balance
            balance_wei = w3.eth.get_balance(agent_address)
            balance_eth = balance_wei / 10**18
            return f"{balance_eth:.4f} ETH"
        else:
            # Get ERC20 balance
            # Standard balanceOf function selector
            data = "0x70a08231" + agent_address[2:].lower().zfill(64)
            
            result = w3.eth.call({
                "to": Web3.to_checksum_address(token_address),
                "data": data
            })
            
            # Convert result to int
            balance_raw = int(result.hex(), 16)
            
            # Try to get token info (decimals)
            try:
                # decimals() function selector
                decimals_data = "0x313ce567"
                decimals_result = w3.eth.call({
                    "to": Web3.to_checksum_address(token_address),
                    "data": decimals_data
                })
                decimals = int(decimals_result.hex(), 16)
            except Exception:
                decimals = 18  # Default to 18 if can't get decimals
            
            balance = balance_raw / (10 ** decimals)
            return f"{balance:.4f} tokens (contract: {token_address})"
            
    except Exception as e:
        return f"Error getting balance: {str(e)}"


@tool
def call_contract(
    to: str,
    function_signature: str,
    params: list | None = None,
    value: str = "0"
) -> str:
    """Call a contract function from the agent's address.
    
    Args:
        to: Contract address
        function_signature: Function signature like "balanceOf(address)" 
        params: List of parameters to encode
        value: ETH value to send (in wei)
        
    Returns:
        The result of the call
    """
    try:
        from ..config_loader import get_config_loader
        
        loader = get_config_loader()
        config = loader.load()
        rpc_url = config.default_chain.rpc_url
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Encode function call
        if params is None:
            params = []
            
        # Get function selector (first 4 bytes of keccak hash)
        function_selector = Web3.keccak(text=function_signature)[:4].hex()
        
        # Simple encoding for common types
        encoded_params = ""
        for param in params:
            if isinstance(param, str) and param.startswith("0x"):
                # Address parameter
                encoded_params += param[2:].lower().zfill(64)
            elif isinstance(param, int):
                # Integer parameter
                encoded_params += hex(param)[2:].zfill(64)
            else:
                # String representation
                encoded_params += str(param).encode().hex().zfill(64)
        
        data = function_selector + encoded_params
        
        # Make the call
        tx = {
            "from": get_agent_address(),
            "to": Web3.to_checksum_address(to),
            "data": data,
            "value": Web3.to_hex(int(value))
        }
        
        result = w3.eth.call(tx)
        return Web3.to_hex(result)
        
    except Exception as e:
        return f"Error calling contract: {str(e)}"


# Export tools
agent_tools = [get_my_balance, call_contract]