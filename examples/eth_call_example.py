"""Example of using eth_call with state overrides to test arbitrage scenarios."""


from web3 import Web3

from dexter.tools.blockchain import eth_call


# Example 1: Read USDC balance
def example_read_balance():
    """Read USDC balance for an address."""
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    user_address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"

    # Encode balanceOf(address) call
    # Function selector for balanceOf: 0x70a08231
    data = "0x70a08231" + user_address[2:].zfill(64)

    result = eth_call(to_address=usdc_address, data=data)

    if result["success"]:
        balance_hex = result["result"]
        balance = int(balance_hex, 16)
        balance_decimal = balance / 10**6  # USDC has 6 decimals
        print(f"USDC Balance: {balance_decimal:,.2f}")
    else:
        print(f"Error: {result['error']}")


# Example 2: Test with modified balance
def example_override_balance():
    """Test what happens if user had 1M USDC."""
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    user_address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"

    # Calculate storage slot for USDC balance
    # USDC uses slot 2 for balances mapping
    w3 = Web3()
    slot_data = w3.solidity_keccak(["address", "uint256"], [user_address, 2])
    storage_slot = "0x" + slot_data.hex()

    # Override state to give user 1M USDC
    state_overrides = {
        usdc_address: {
            "state": {
                storage_slot: hex(1_000_000 * 10**6)  # 1M USDC
            }
        }
    }

    # Read balance with override
    data = "0x70a08231" + user_address[2:].zfill(64)

    result = eth_call(
        to_address=usdc_address, data=data, state_overrides=state_overrides
    )

    if result["success"]:
        balance_hex = result["result"]
        balance = int(balance_hex, 16)
        balance_decimal = balance / 10**6
        print(f"Modified USDC Balance: {balance_decimal:,.2f}")
    else:
        print(f"Error: {result['error']}")


# Example 3: Test DEX swap with overridden balances
def example_test_swap():
    """Test a Uniswap swap with modified token balances."""
    # This is a more complex example showing how to test swaps
    # with state overrides to simulate having tokens

    user_address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    # usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # Not used in this example

    # Calculate storage slots
    w3 = Web3()

    # Give user 100 WETH
    weth_slot = w3.solidity_keccak(
        ["address", "uint256"], [user_address, 3]
    )  # WETH uses slot 3
    weth_balance = hex(100 * 10**18)  # 100 WETH

    # Give user ETH for gas
    eth_balance = hex(10 * 10**18)  # 10 ETH

    state_overrides = {
        weth_address: {"state": {"0x" + weth_slot.hex(): weth_balance}},
        user_address: {"balance": eth_balance},
    }

    print("State overrides configured:")
    print("- User will have 100 WETH")
    print("- User will have 10 ETH for gas")
    print("\nNow you can test DEX swaps with these balances!")

    return state_overrides


if __name__ == "__main__":
    print("=== ETH Call Examples ===\n")

    print("1. Reading current balance:")
    example_read_balance()

    print("\n2. Testing with overridden balance:")
    example_override_balance()

    print("\n3. Preparing swap test:")
    overrides = example_test_swap()
