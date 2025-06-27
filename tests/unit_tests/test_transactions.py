"""Unit tests for transaction tools."""

import os
from unittest.mock import Mock, patch

from dexter.tools.transactions import (
    alchemy_simulate_asset_changes,
    submit_transaction,
)


class TestTransactionTools:
    """Test transaction submission and simulation tools."""

    def setup_method(self):
        """Save and clear environment variables before each test."""
        self.original_alchemy_key = os.environ.get("ALCHEMY_API_KEY")
        self.original_eth_key = os.environ.get("AGENT_ETH_KEY")
        # Clear them for tests
        os.environ.pop("ALCHEMY_API_KEY", None)
        os.environ.pop("AGENT_ETH_KEY", None)

    def teardown_method(self):
        """Restore environment variables after each test."""
        if self.original_alchemy_key:
            os.environ["ALCHEMY_API_KEY"] = self.original_alchemy_key
        else:
            os.environ.pop("ALCHEMY_API_KEY", None)
        if self.original_eth_key:
            os.environ["AGENT_ETH_KEY"] = self.original_eth_key
        else:
            os.environ.pop("AGENT_ETH_KEY", None)

    @patch("dexter.tools.transactions.Web3")
    @patch("dexter.tools.transactions.get_config")
    def test_submit_transaction_eth_transfer(self, mock_get_config, mock_web3_class):
        """Test submitting a simple ETH transfer."""
        # Mock configuration
        mock_config = Mock()
        mock_config.default_chain.rpc_url = "https://eth-mainnet.example.com"
        mock_config.arbitrage.default_gas_limit = 200000
        mock_get_config.return_value = mock_config

        # Mock Web3 instance
        mock_w3 = Mock()
        mock_web3_class.return_value = mock_w3
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 1
        mock_w3.eth.gas_price = 30000000000  # 30 gwei

        # Mock account
        mock_account = Mock()
        mock_account.address = "0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e"
        mock_w3.eth.account.from_key.return_value = mock_account

        # Mock transaction methods
        mock_w3.to_checksum_address.side_effect = lambda x: x
        mock_w3.eth.get_transaction_count.return_value = 5
        mock_w3.eth.estimate_gas.return_value = 21000

        # Mock signing and sending
        mock_signed_tx = Mock()
        mock_signed_tx.raw_transaction = b"signed_tx_data"
        mock_account.sign_transaction.return_value = mock_signed_tx

        mock_tx_hash = Mock()
        mock_tx_hash.hex.return_value = "0x1234567890abcdef"
        mock_w3.eth.send_raw_transaction.return_value = mock_tx_hash

        # Mock receipt
        mock_receipt = {
            "gasUsed": 21000,
            "effectiveGasPrice": 30000000000,
            "blockNumber": 12345678,
            "status": 1,
        }
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        # Execute
        result = submit_transaction(
            to_address="0x8f977e912ef692455868871b3c6f632479c9e7f7",
            value="1000000000000000000",  # 1 ETH
            private_key="0xprivatekey",
        )

        # Verify
        assert result["success"] is True
        assert result["transaction_hash"] == "0x1234567890abcdef"
        assert result["from"] == "0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e"
        assert result["to"] == "0x8f977e912ef692455868871b3c6f632479c9e7f7"
        assert result["gas_used"] == 21000
        assert result["status"] == 1

    @patch("dexter.tools.transactions.Web3")
    def test_submit_transaction_connection_error(self, mock_web3_class):
        """Test handling connection errors."""
        # Mock Web3 instance
        mock_w3 = Mock()
        mock_web3_class.return_value = mock_w3
        mock_w3.is_connected.return_value = False

        result = submit_transaction(
            to_address="0x8f977e912ef692455868871b3c6f632479c9e7f7",
            value="1000000000000000000",
            private_key="0xprivatekey",
            rpc_url="https://eth-mainnet.example.com",
        )

        assert result["error"] == "Failed to connect to Ethereum node"
        assert "success" not in result or result["success"] is False

    @patch("requests.post")
    @patch("dexter.tools.transactions.Web3")
    def test_alchemy_simulate_asset_changes_success(
        self, mock_web3_class, mock_requests
    ):
        """Test successful Alchemy simulation."""
        # Mock Web3 for address validation
        mock_w3 = Mock()
        mock_web3_class.return_value = mock_w3
        mock_w3.to_checksum_address.side_effect = lambda x: x

        # Mock successful Alchemy response
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "changes": [
                    {
                        "assetType": "ETH",
                        "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e",
                        "to": "0x8f977e912ef692455868871b3c6f632479c9e7f7",
                        "amount": "0xde0b6b3a7640000",  # 1 ETH in hex
                    }
                ],
                "gasUsed": "0x5208",  # 21000 in hex
            },
        }
        mock_requests.return_value = mock_response

        result = alchemy_simulate_asset_changes(
            to_address="0x8f977e912ef692455868871b3c6f632479c9e7f7",
            value="1000000000000000000",  # 1 ETH
            from_address="0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e",
            alchemy_api_key="test_api_key",
        )

        assert result["success"] is True
        assert len(result["changes"]) == 1
        assert result["changes"][0]["asset_type"] == "ETH"
        assert (
            result["changes"][0]["from"] == "0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e"
        )
        assert (
            result["changes"][0]["to"] == "0x8f977e912ef692455868871b3c6f632479c9e7f7"
        )
        assert result["gas_used"] == "0x5208"

    @patch("requests.post")
    @patch("dexter.tools.transactions.Web3")
    def test_alchemy_simulate_erc20_transfer(self, mock_web3_class, mock_requests):
        """Test Alchemy simulation with ERC20 token transfer."""
        # Mock Web3 for address validation
        mock_w3 = Mock()
        mock_web3_class.return_value = mock_w3
        mock_w3.to_checksum_address.side_effect = lambda x: x

        # Mock Alchemy response with ERC20 transfer
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "changes": [
                    {
                        "assetType": "ERC20",
                        "contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                        "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e",
                        "to": "0x8f977e912ef692455868871b3c6f632479c9e7f7",
                        "amount": "0x3b9aca00",  # 1000000000 (1000 USDC with 6 decimals)
                        "symbol": "USDC",
                        "decimals": 6,
                    }
                ],
                "gasUsed": "0xea60",  # ~60000 in hex
            },
        }
        mock_requests.return_value = mock_response

        # ERC20 transfer data (transfer(address,uint256))
        transfer_data = "0xa9059cbb0000000000000000000000008f977e912ef692455868871b3c6f632479c9e7f70000000000000000000000000000000000000000000000000000000003b9aca00"

        result = alchemy_simulate_asset_changes(
            to_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC contract
            value="0",
            data=transfer_data,
            from_address="0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e",
            alchemy_api_key="test_api_key",
        )

        assert result["success"] is True
        assert len(result["changes"]) == 1
        assert result["changes"][0]["asset_type"] == "ERC20"
        assert result["changes"][0]["symbol"] == "USDC"
        assert result["changes"][0]["decimals"] == 6
        assert result["changes"][0]["amount_formatted"] == 1000.0  # 1000 USDC

    @patch("requests.post")
    @patch("dexter.tools.transactions.Web3")
    def test_alchemy_simulate_error_response(self, mock_web3_class, mock_requests):
        """Test handling Alchemy error response."""
        # Mock Web3 for address validation
        mock_w3 = Mock()
        mock_web3_class.return_value = mock_w3
        mock_w3.to_checksum_address.side_effect = lambda x: x

        # Mock error response
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32000,
                "message": "execution reverted",
            },
        }
        mock_requests.return_value = mock_response

        result = alchemy_simulate_asset_changes(
            to_address="0x8f977e912ef692455868871b3c6f632479c9e7f7",
            value="1000000000000000000",
            from_address="0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e",
            alchemy_api_key="test_api_key",
        )

        assert result["success"] is False
        assert result["error"] == "execution reverted"
        assert result["error_code"] == -32000

    @patch("dexter.tools.transactions.Web3")
    @patch("dexter.tools.transactions.get_config")
    def test_submit_transaction_with_env_key(self, mock_get_config, mock_web3_class):
        """Test submitting transaction using AGENT_ETH_KEY from environment."""
        # Set environment variable
        os.environ["AGENT_ETH_KEY"] = "0xenvprivatekey"

        # Mock configuration
        mock_config = Mock()
        mock_config.default_chain.rpc_url = "https://eth-mainnet.example.com"
        mock_config.arbitrage.default_gas_limit = 200000
        mock_get_config.return_value = mock_config

        # Mock Web3 instance
        mock_w3 = Mock()
        mock_web3_class.return_value = mock_w3
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 1
        mock_w3.eth.gas_price = 30000000000  # 30 gwei

        # Mock account
        mock_account = Mock()
        mock_account.address = "0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e"
        mock_w3.eth.account.from_key.return_value = mock_account

        # Mock transaction methods
        mock_w3.to_checksum_address.side_effect = lambda x: x
        mock_w3.eth.get_transaction_count.return_value = 5
        mock_w3.eth.estimate_gas.return_value = 21000

        # Mock signing and sending
        mock_signed_tx = Mock()
        mock_signed_tx.raw_transaction = b"signed_tx_data"
        mock_account.sign_transaction.return_value = mock_signed_tx

        mock_tx_hash = Mock()
        mock_tx_hash.hex.return_value = "0x1234567890abcdef"
        mock_w3.eth.send_raw_transaction.return_value = mock_tx_hash

        # Mock receipt
        mock_receipt = {
            "gasUsed": 21000,
            "effectiveGasPrice": 30000000000,
            "blockNumber": 12345678,
            "status": 1,
        }
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        # Execute without providing private key
        result = submit_transaction(
            to_address="0x8f977e912ef692455868871b3c6f632479c9e7f7",
            value="1000000000000000000",  # 1 ETH
        )

        # Verify
        assert result["success"] is True
        # Verify that from_key was called with the env key
        mock_w3.eth.account.from_key.assert_called_once_with("0xenvprivatekey")

    @patch("requests.post")
    @patch("dexter.tools.transactions.Web3")
    def test_alchemy_simulate_with_env_keys(self, mock_web3_class, mock_requests):
        """Test Alchemy simulation using ALCHEMY_API_KEY and AGENT_ETH_KEY from environment."""
        # Set environment variables
        os.environ["ALCHEMY_API_KEY"] = "env_test_api_key"
        os.environ["AGENT_ETH_KEY"] = (
            "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )

        # Mock Web3 for address validation and account derivation
        mock_w3 = Mock()
        mock_web3_class.return_value = mock_w3
        mock_w3.to_checksum_address.side_effect = lambda x: x

        # Mock account derivation from private key
        mock_account = Mock()
        mock_account.address = "0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e"
        mock_w3.eth.account.from_key.return_value = mock_account

        # Mock successful Alchemy response
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "changes": [
                    {
                        "assetType": "ETH",
                        "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e",
                        "to": "0x8f977e912ef692455868871b3c6f632479c9e7f7",
                        "amount": "0xde0b6b3a7640000",  # 1 ETH in hex
                    }
                ],
                "gasUsed": "0x5208",  # 21000 in hex
            },
        }
        mock_requests.return_value = mock_response

        # Execute without providing API key or from_address
        result = alchemy_simulate_asset_changes(
            to_address="0x8f977e912ef692455868871b3c6f632479c9e7f7",
            value="1000000000000000000",  # 1 ETH
        )

        # Verify
        assert result["success"] is True
        # Verify that the correct URL was called with env API key
        mock_requests.assert_called_once()
        call_args = mock_requests.call_args
        assert "env_test_api_key" in call_args[0][0]  # URL contains the API key
        # Verify that from_key was called to derive address
        mock_w3.eth.account.from_key.assert_called_once_with(
            "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )

    @patch("dexter.tools.transactions.Web3")
    def test_submit_transaction_no_key_error(self, mock_web3_class):
        """Test error when no private key is provided and not in environment."""
        # Ensure no env key
        os.environ.pop("AGENT_ETH_KEY", None)

        result = submit_transaction(
            to_address="0x8f977e912ef692455868871b3c6f632479c9e7f7",
            value="1000000000000000000",
        )

        assert result["success"] is False
        assert "AGENT_ETH_KEY not found" in result["error"]

    @patch("dexter.tools.transactions.Web3")
    def test_alchemy_simulate_no_key_error(self, mock_web3_class):
        """Test error when no Alchemy API key is provided and not in environment."""
        # Ensure no env key
        os.environ.pop("ALCHEMY_API_KEY", None)

        # Mock Web3 for address validation
        mock_w3 = Mock()
        mock_web3_class.return_value = mock_w3
        mock_w3.to_checksum_address.side_effect = lambda x: x

        result = alchemy_simulate_asset_changes(
            to_address="0x8f977e912ef692455868871b3c6f632479c9e7f7",
            value="1000000000000000000",
            from_address="0x742d35Cc6634C0532925a3b844Bc9e7595f62d6e",
        )

        assert result["success"] is False
        assert "ALCHEMY_API_KEY not found" in result["error"]

    @patch("dexter.tools.transactions.Web3")
    def test_alchemy_simulate_no_from_address_error(self, mock_web3_class):
        """Test error when no from_address is provided and AGENT_ETH_KEY not in environment."""
        # Ensure no env keys
        os.environ.pop("AGENT_ETH_KEY", None)

        result = alchemy_simulate_asset_changes(
            to_address="0x8f977e912ef692455868871b3c6f632479c9e7f7",
            value="1000000000000000000",
            alchemy_api_key="test_api_key",
        )

        assert result["success"] is False
        assert "AGENT_ETH_KEY not found" in result["error"]
