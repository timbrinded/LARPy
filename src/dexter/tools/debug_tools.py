"""Debug and testing tools for local blockchain environments."""


from langchain_core.tools import tool
from web3 import Web3

from ..config_loader import get_config_loader
from .wallet_utils import resolve_address


@tool
def debug_traceTransaction(tx_hash: str, **kwargs) -> str:
    """Trace a transaction to see its execution details, state changes, and gas usage.
    
    Useful for understanding why a transaction failed or what it actually did.
    Works with local test networks like Anvil that support debug_traceTransaction.
    
    You can pass various tracer options like:
    - tracer: "callTracer" for call stack
    - tracer: "prestateTracer" for pre-execution state
    - Custom JS tracer code for specific analysis
    
    Args:
        tx_hash: Transaction hash to trace
        **kwargs: Additional options for the tracer
        
    Returns:
        Detailed trace information about the transaction
    """
    try:
        loader = get_config_loader()
        config = loader.load()
        
        # Use default chain RPC
        rpc_url = config.default_chain.rpc_url
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Build trace options
        trace_config = {}
        if "tracer" in kwargs:
            trace_config["tracer"] = kwargs["tracer"]
        if "timeout" in kwargs:
            trace_config["timeout"] = kwargs["timeout"]
            
        # Make the trace call
        result = w3.provider.make_request(
            "debug_traceTransaction",
            [tx_hash, trace_config] if trace_config else [tx_hash]
        )
        
        if "error" in result:
            return f"Error tracing transaction: {result['error']}"
            
        # Format the response nicely
        trace = result.get("result", {})
        
        # If using callTracer, format the call tree
        if kwargs.get("tracer") == "callTracer":
            return format_call_trace(trace)
        
        # Otherwise return raw trace
        import json
        return json.dumps(trace, indent=2)
        
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def eth_call(
    to: str,
    data: str,
    from_address: str | None = None,
    value: str | None = None,
    gas: int | None = None,
    block: str | None = "latest",
    **kwargs
) -> str:
    """Execute a call to a smart contract without creating a transaction.
    
    Perfect for:
    - Reading contract state
    - Simulating transactions before sending
    - Testing contract interactions
    - Checking what a transaction would return
    
    The beauty of eth_call is you can override any state you want for testing.
    Pass state_overrides to modify account balances, storage, or even contract code.
    
    Args:
        to: Contract address to call
        data: Encoded function call data
        from_address: Caller address (optional)
        value: ETH to send with call (optional)
        gas: Gas limit (optional)
        block: Block to execute against (optional)
        **kwargs: Additional parameters like state_overrides
        
    Returns:
        The return data from the call
    """
    try:
        loader = get_config_loader()
        config = loader.load()
        
        # Use default chain RPC
        rpc_url = config.default_chain.rpc_url
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Build transaction dict
        tx = {
            "to": Web3.to_checksum_address(resolve_address(to)),
            "data": data
        }
        
        if from_address:
            tx["from"] = Web3.to_checksum_address(resolve_address(from_address))
        if value:
            tx["value"] = Web3.to_hex(int(value))
        if gas:
            tx["gas"] = Web3.to_hex(gas)
            
        # Make the call
        result = w3.eth.call(tx, block)
        
        # Return hex result
        return Web3.to_hex(result)
        
    except Exception as e:
        # Check if it's a revert with message
        error_msg = str(e)
        if "execution reverted" in error_msg:
            # Try to extract revert reason
            import re
            match = re.search(r'execution reverted: (.*?)(?:\n|$)', error_msg)
            if match:
                return f"Execution reverted: {match.group(1)}"
        return f"Error: {error_msg}"


def format_call_trace(trace: dict, depth: int = 0) -> str:
    """Format a call trace into a readable tree structure."""
    indent = "  " * depth
    output = []
    
    # Basic call info
    call_type = trace.get("type", "CALL")
    to = trace.get("to", "???")
    value = trace.get("value", "0x0")
    
    # Convert value from hex if needed
    if value != "0x0":
        try:
            value_wei = int(value, 16)
            value_eth = value_wei / 10**18
            value_str = f" (value: {value_eth} ETH)"
        except Exception:
            value_str = f" (value: {value})"
    else:
        value_str = ""
    
    output.append(f"{indent}{call_type} → {to}{value_str}")
    
    # Add input data preview if present
    if "input" in trace and trace["input"] != "0x":
        input_preview = trace["input"][:10] + "..." if len(trace["input"]) > 10 else trace["input"]
        output.append(f"{indent}  Input: {input_preview}")
    
    # Add output/error
    if "output" in trace:
        output_preview = trace["output"][:66] + "..." if len(trace["output"]) > 66 else trace["output"]
        output.append(f"{indent}  Output: {output_preview}")
    elif "error" in trace:
        output.append(f"{indent}  Error: {trace['error']}")
    
    # Add gas info
    if "gasUsed" in trace:
        gas_used = int(trace["gasUsed"], 16) if isinstance(trace["gasUsed"], str) else trace["gasUsed"]
        output.append(f"{indent}  Gas used: {gas_used:,}")
    
    # Process nested calls
    if "calls" in trace:
        for subcall in trace["calls"]:
            output.append("")  # Empty line before subcall
            output.append(format_call_trace(subcall, depth + 1))
    
    return "\n".join(output)


# Export tools
debug_tools = [debug_traceTransaction, eth_call]