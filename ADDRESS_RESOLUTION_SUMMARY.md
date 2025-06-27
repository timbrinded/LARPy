# Address Resolution Implementation Summary

## Problem
The system was passing "0xYourWalletAddress" literally to blockchain functions, causing errors like:
```
Error: when sending a str, it must be a hex string. Got: '0x70a08231000000000000000000000000YourWalletAddress'
```

## Solution
Created address resolution utilities to automatically replace "0xYourWalletAddress" with the actual agent address from the AGENT_ETH_KEY environment variable.

## Files Created/Modified

### New Files:
1. **src/dexter/tools/wallet_utils.py**
   - `get_agent_address()`: Gets agent address from AGENT_ETH_KEY private key
   - `resolve_address()`: Converts "0xYourWalletAddress" to actual address

2. **src/dexter/tools/agent_tools.py**
   - `get_my_balance()`: Gets balance of agent wallet (ETH or ERC20)
   - `call_contract()`: Call contracts from agent address
   - Both tools automatically use agent's address

### Modified Files:
1. **src/dexter/tools/debug_tools.py**
   - Updated `eth_call` to use `resolve_address()` for to/from addresses

2. **src/dexter/tools/transactions.py**
   - Updated `submit_transaction` to use `resolve_address()` for to_address
   - Updated `alchemy_simulate_asset_changes` to use `resolve_address()`

3. **src/dexter/tools/__init__.py**
   - Added exports for new agent tools

4. **src/dexter/agent_graph.py**
   - Updated generator agent to include new agent-aware tools
   - Added note about not using "0xYourWalletAddress" literally

## How It Works

1. **Address Resolution**: Any address passed to tools is checked:
   ```python
   if address.lower() == "0xyourwalletaddress":
       return get_agent_address()  # Returns actual address from private key
   ```

2. **Agent Tools**: New tools that automatically know the agent's address:
   ```python
   # No need to specify address - it knows!
   balance = get_my_balance()  # Returns agent's ETH balance
   balance = get_my_balance(token_address="0xUSDC...")  # Returns agent's token balance
   ```

3. **Backwards Compatible**: All existing tools still work, but now handle the special address:
   ```python
   # These all work now:
   eth_call(to="0xContract", from_address="0xYourWalletAddress")
   submit_transaction(to_address="0xYourWalletAddress")
   ```

## Testing
```bash
# Set test private key
export AGENT_ETH_KEY=0x0000000000000000000000000000000000000000000000000000000000000001

# Test resolution
uv run python -c "from src.dexter.tools.wallet_utils import resolve_address; print(resolve_address('0xYourWalletAddress'))"
# Output: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf
```

## Key Benefits
1. **No More Hex Errors**: Special addresses are resolved before being encoded
2. **Case Insensitive**: Works with any case variation
3. **Agent-Aware Tools**: New tools that automatically use agent's address
4. **Transparent**: Works seamlessly with existing code