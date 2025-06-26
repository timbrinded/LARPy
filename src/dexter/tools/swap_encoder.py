"""Tools for encoding swap transactions for various DEX protocols."""

import time
from typing import Dict, Optional, Union

from eth_abi import encode
from langchain_core.tools import tool
from web3 import Web3

from ..config_loader import get_config_loader


@tool
def encode_uniswap_v3_swap(
    token_in: str,
    token_out: str,
    amount_in: str,
    recipient: str = "0xYourWalletAddress",
    fee_tier: int = 3000,
    slippage_percent: float = 0.5,
    deadline_minutes: int = 20
) -> Dict[str, Union[str, bool]]:
    """Encode a Uniswap V3 swap transaction.
    
    Args:
        token_in: Symbol of token to swap from (e.g., "ETH", "WETH", "USDC")
        token_out: Symbol of token to swap to (e.g., "USDC", "WETH")
        amount_in: Amount to swap in token's smallest unit (wei for ETH/WETH, etc.)
        recipient: Address to receive tokens. Use "0xYourWalletAddress" for agent's wallet
        fee_tier: Uniswap V3 fee tier (100, 500, 3000, or 10000 for 0.01%, 0.05%, 0.3%, 1%)
        slippage_percent: Maximum slippage tolerance as percentage (e.g., 0.5 for 0.5%)
        deadline_minutes: Transaction deadline in minutes from now
        
    Returns:
        Dict containing:
        - to: Router contract address
        - data: Encoded transaction data
        - value: ETH value to send (if swapping from ETH)
        - success: Whether encoding succeeded
        - error: Error message if failed
    """
    try:
        # Get configuration
        loader = get_config_loader()
        
        # Handle special recipient address
        if recipient == "0xYourWalletAddress":
            import os
            private_key = os.getenv("AGENT_ETH_KEY")
            if not private_key:
                return {"success": False, "error": "AGENT_ETH_KEY not found in environment"}
            try:
                w3 = Web3()
                account = w3.eth.account.from_key(private_key)
                recipient = account.address
            except Exception as e:
                return {"success": False, "error": f"Invalid private key: {str(e)}"}
        
        # Get token addresses
        if token_in.upper() == "ETH":
            token_in_address = None  # Native ETH
            weth_address = loader.get_token_address("WETH")
        else:
            token_in_address = loader.get_token_address(token_in.upper())
            if token_in.upper() == "WETH":
                weth_address = token_in_address
            else:
                weth_address = loader.get_token_address("WETH")
                
        token_out_address = loader.get_token_address(token_out.upper())
        
        if not token_out_address:
            return {"success": False, "error": f"Token {token_out} not found in configuration"}
        
        # Get Uniswap V3 router address
        config = loader.load()
        router_address = config.dexes.get("uniswap_v3", {}).router_address
        if not router_address:
            return {"success": False, "error": "Uniswap V3 router address not found"}
        
        # Calculate deadline
        deadline = int(time.time()) + (deadline_minutes * 60)
        
        # Calculate minimum amount out with slippage
        # For now, we'll use 0 as minimum (any amount accepted)
        # In production, you'd calculate this based on current price
        amount_out_minimum = 0
        
        # Encode based on whether we're swapping ETH or tokens
        if token_in.upper() == "ETH":
            # Swapping ETH for tokens - use exactInputSingle with ETH value
            # Function: exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))
            
            # Encode the params struct
            params = encode(
                ['(address,address,uint24,address,uint256,uint256,uint256,uint160)'],
                [(
                    weth_address,  # tokenIn (WETH for ETH swaps)
                    token_out_address,  # tokenOut
                    fee_tier,  # fee
                    recipient,  # recipient
                    deadline,  # deadline
                    int(amount_in),  # amountIn
                    amount_out_minimum,  # amountOutMinimum
                    0  # sqrtPriceLimitX96 (0 = no limit)
                )]
            )
            
            # Function selector for exactInputSingle
            function_selector = "0x414bf389"
            
            return {
                "success": True,
                "to": router_address,
                "data": function_selector + params.hex(),
                "value": amount_in,  # Send ETH with transaction
                "function": "exactInputSingle",
                "params": {
                    "tokenIn": weth_address,
                    "tokenOut": token_out_address,
                    "fee": fee_tier,
                    "recipient": recipient,
                    "deadline": deadline,
                    "amountIn": amount_in,
                    "amountOutMinimum": amount_out_minimum
                }
            }
            
        else:
            # Swapping tokens for tokens or tokens for ETH
            if token_out.upper() == "ETH":
                # Token to ETH swap - need special handling
                # Use exactInputSingle but with WETH as output, then unwrap
                
                params = encode(
                    ['(address,address,uint24,address,uint256,uint256,uint256,uint160)'],
                    [(
                        token_in_address,  # tokenIn
                        weth_address,  # tokenOut (WETH)
                        fee_tier,  # fee
                        router_address,  # recipient (router will unwrap)
                        deadline,  # deadline
                        int(amount_in),  # amountIn
                        amount_out_minimum,  # amountOutMinimum
                        0  # sqrtPriceLimitX96
                    )]
                )
                
                function_selector = "0x414bf389"
                
                # Need to add unwrapWETH9 call
                # This would require multicall, simplified for now
                
                return {
                    "success": True,
                    "to": router_address,
                    "data": function_selector + params.hex(),
                    "value": "0",  # No ETH sent
                    "function": "exactInputSingle (token to WETH)",
                    "note": "This swaps to WETH. Additional unwrapWETH9 call needed for ETH",
                    "params": {
                        "tokenIn": token_in_address,
                        "tokenOut": weth_address,
                        "fee": fee_tier,
                        "recipient": router_address,
                        "deadline": deadline,
                        "amountIn": amount_in,
                        "amountOutMinimum": amount_out_minimum
                    }
                }
                
            else:
                # Token to token swap
                params = encode(
                    ['(address,address,uint24,address,uint256,uint256,uint256,uint160)'],
                    [(
                        token_in_address,  # tokenIn
                        token_out_address,  # tokenOut
                        fee_tier,  # fee
                        recipient,  # recipient
                        deadline,  # deadline
                        int(amount_in),  # amountIn
                        amount_out_minimum,  # amountOutMinimum
                        0  # sqrtPriceLimitX96
                    )]
                )
                
                function_selector = "0x414bf389"
                
                return {
                    "success": True,
                    "to": router_address,
                    "data": function_selector + params.hex(),
                    "value": "0",  # No ETH sent
                    "function": "exactInputSingle",
                    "params": {
                        "tokenIn": token_in_address,
                        "tokenOut": token_out_address,
                        "fee": fee_tier,
                        "recipient": recipient,
                        "deadline": deadline,
                        "amountIn": amount_in,
                        "amountOutMinimum": amount_out_minimum
                    }
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to encode swap: {str(e)}"
        }


@tool
def encode_sushiswap_swap(
    token_in: str,
    token_out: str,
    amount_in: str,
    recipient: str = "0xYourWalletAddress",
    slippage_percent: float = 0.5,
    deadline_minutes: int = 20
) -> Dict[str, Union[str, bool]]:
    """Encode a SushiSwap swap transaction.
    
    Args:
        token_in: Symbol of token to swap from (e.g., "ETH", "WETH", "USDC")
        token_out: Symbol of token to swap to (e.g., "USDC", "WETH")
        amount_in: Amount to swap in token's smallest unit (wei for ETH/WETH, etc.)
        recipient: Address to receive tokens. Use "0xYourWalletAddress" for agent's wallet
        slippage_percent: Maximum slippage tolerance as percentage
        deadline_minutes: Transaction deadline in minutes from now
        
    Returns:
        Dict containing to address, data, value, and success status
    """
    try:
        # Get configuration
        loader = get_config_loader()
        
        # Handle special recipient address
        if recipient == "0xYourWalletAddress":
            import os
            private_key = os.getenv("AGENT_ETH_KEY")
            if not private_key:
                return {"success": False, "error": "AGENT_ETH_KEY not found in environment"}
            try:
                w3 = Web3()
                account = w3.eth.account.from_key(private_key)
                recipient = account.address
            except Exception as e:
                return {"success": False, "error": f"Invalid private key: {str(e)}"}
        
        # Get token addresses
        if token_in.upper() == "ETH":
            # For ETH swaps, we'll use WETH address in the path
            weth_address = loader.get_token_address("WETH")
            token_in_address = weth_address
            is_eth_input = True
        else:
            token_in_address = loader.get_token_address(token_in.upper())
            is_eth_input = False
            
        if token_out.upper() == "ETH":
            # For ETH output, we'll use WETH in path
            weth_address = loader.get_token_address("WETH")
            token_out_address = weth_address
            is_eth_output = True
        else:
            token_out_address = loader.get_token_address(token_out.upper())
            is_eth_output = False
        
        if not token_in_address or not token_out_address:
            return {"success": False, "error": "Token addresses not found"}
        
        # Get SushiSwap router address
        config = loader.load()
        router_address = config.dexes.get("sushiswap", {}).router_address
        if not router_address:
            return {"success": False, "error": "SushiSwap router address not found"}
        
        # Calculate deadline
        deadline = int(time.time()) + (deadline_minutes * 60)
        
        # Path for swap
        path = [token_in_address, token_out_address]
        
        # Calculate minimum amount out (0 for simplicity, should calculate based on price)
        amount_out_min = 0
        
        # Encode based on swap type
        if is_eth_input:
            # ETH -> Token: swapExactETHForTokens
            # function swapExactETHForTokens(uint amountOutMin, address[] calldata path, address to, uint deadline)
            
            function_selector = Web3.keccak(
                text="swapExactETHForTokens(uint256,address[],address,uint256)"
            )[:4].hex()
            
            params = encode(
                ['uint256', 'address[]', 'address', 'uint256'],
                [amount_out_min, path, recipient, deadline]
            )
            
            return {
                "success": True,
                "to": router_address,
                "data": function_selector + params.hex(),
                "value": amount_in,  # Send ETH
                "function": "swapExactETHForTokens",
                "params": {
                    "amountOutMin": amount_out_min,
                    "path": path,
                    "to": recipient,
                    "deadline": deadline
                }
            }
            
        elif is_eth_output:
            # Token -> ETH: swapExactTokensForETH
            function_selector = Web3.keccak(
                text="swapExactTokensForETH(uint256,uint256,address[],address,uint256)"
            )[:4].hex()
            
            params = encode(
                ['uint256', 'uint256', 'address[]', 'address', 'uint256'],
                [int(amount_in), amount_out_min, path, recipient, deadline]
            )
            
            return {
                "success": True,
                "to": router_address,
                "data": function_selector + params.hex(),
                "value": "0",
                "function": "swapExactTokensForETH",
                "params": {
                    "amountIn": amount_in,
                    "amountOutMin": amount_out_min,
                    "path": path,
                    "to": recipient,
                    "deadline": deadline
                }
            }
            
        else:
            # Token -> Token: swapExactTokensForTokens
            function_selector = Web3.keccak(
                text="swapExactTokensForTokens(uint256,uint256,address[],address,uint256)"
            )[:4].hex()
            
            params = encode(
                ['uint256', 'uint256', 'address[]', 'address', 'uint256'],
                [int(amount_in), amount_out_min, path, recipient, deadline]
            )
            
            return {
                "success": True,
                "to": router_address,
                "data": function_selector + params.hex(),
                "value": "0",
                "function": "swapExactTokensForTokens",
                "params": {
                    "amountIn": amount_in,
                    "amountOutMin": amount_out_min,
                    "path": path,
                    "to": recipient,
                    "deadline": deadline
                }
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to encode swap: {str(e)}"
        }


@tool
def encode_erc20_approve(
    token: str,
    spender: str,
    amount: str
) -> Dict[str, Union[str, bool]]:
    """Encode an ERC20 approve transaction to allow a contract to spend tokens.
    
    This is required before swapping tokens on most DEXs.
    
    Args:
        token: Symbol of token to approve (e.g., "USDC", "WETH")
        spender: Address of contract to approve (usually DEX router)
        amount: Amount to approve in token's smallest unit. Use max uint256 for unlimited.
        
    Returns:
        Dict containing to address, data, and success status
    """
    try:
        # Get configuration
        loader = get_config_loader()
        
        # Get token address
        token_address = loader.get_token_address(token.upper())
        if not token_address:
            return {"success": False, "error": f"Token {token} not found"}
        
        # Encode approve(address,uint256)
        function_selector = Web3.keccak(text="approve(address,uint256)")[:4].hex()
        
        # Handle "max" amount
        if amount.lower() == "max":
            amount_int = 2**256 - 1  # Max uint256
        else:
            amount_int = int(amount)
        
        params = encode(['address', 'uint256'], [spender, amount_int])
        
        return {
            "success": True,
            "to": token_address,
            "data": function_selector + params.hex(),
            "value": "0",
            "function": "approve",
            "params": {
                "spender": spender,
                "amount": str(amount_int)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to encode approve: {str(e)}"
        }


# Export tools
swap_encoding_tools = [
    encode_uniswap_v3_swap,
    encode_sushiswap_swap,
    encode_erc20_approve
]