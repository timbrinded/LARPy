"""Tests for the eth_call tool with state override support."""

from unittest.mock import MagicMock, patch

import pytest
from web3.exceptions import ContractLogicError

from dexter.tools.blockchain import eth_call


class TestEthCall:
    """Test cases for eth_call function."""

    @patch("dexter.tools.blockchain.Web3")
    @patch("dexter.tools.blockchain.get_config")
    def test_eth_call_success(self, mock_get_config, mock_web3_class):
        """Test successful eth_call without state overrides."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.default_chain.rpc_url = "http://localhost:8545"
        mock_get_config.return_value = mock_config

        mock_web3 = MagicMock()
        mock_web3.is_connected.return_value = True
        mock_web3.to_checksum_address = lambda x: x
        mock_web3.eth.call.return_value = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xe8"
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider.return_value = MagicMock()

        # Test call
        result = eth_call(
            to_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            data="0x70a08231000000000000000000000000f39fd6e51aad88f6f4ce6ab8827279cfffb92266",
        )

        assert result["success"] is True
        assert result["result"] == "0x00000000000000000000000000000000000000000000000000000000000003e8"
        assert result["to"] == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        assert result["state_overrides"] is None

    @patch("dexter.tools.blockchain.Web3")
    @patch("dexter.tools.blockchain.get_config")
    def test_eth_call_with_state_overrides(self, mock_get_config, mock_web3_class):
        """Test eth_call with state overrides."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.default_chain.rpc_url = "http://localhost:8545"
        mock_get_config.return_value = mock_config

        mock_web3 = MagicMock()
        mock_web3.is_connected.return_value = True
        mock_web3.to_checksum_address = lambda x: x
        mock_web3.eth.call.return_value = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x27\x10"
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider.return_value = MagicMock()

        # Test call with state overrides
        state_overrides = {
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": {
                "state": {
                    "0x0": "0x1234",
                    "0x1": "0x5678",
                }
            }
        }

        result = eth_call(
            to_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            data="0x70a08231000000000000000000000000f39fd6e51aad88f6f4ce6ab8827279cfffb92266",
            state_overrides=state_overrides,
        )

        assert result["success"] is True
        assert result["result"] == "0x0000000000000000000000000000000000000000000000000000000000002710"
        assert result["state_overrides"] == state_overrides

        # Verify state overrides were passed to web3.eth.call
        call_args = mock_web3.eth.call.call_args
        assert len(call_args[0]) == 3  # call_params, block_number, state_overrides
        assert call_args[0][2] == state_overrides

    @patch("dexter.tools.blockchain.Web3")
    @patch("dexter.tools.blockchain.get_config")
    def test_eth_call_with_balance_override(self, mock_get_config, mock_web3_class):
        """Test eth_call with balance override."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.default_chain.rpc_url = "http://localhost:8545"
        mock_get_config.return_value = mock_config

        mock_web3 = MagicMock()
        mock_web3.is_connected.return_value = True
        mock_web3.to_checksum_address = lambda x: x
        mock_web3.eth.call.return_value = b"\x00" * 32
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider.return_value = MagicMock()

        # Test with balance override (integer value)
        state_overrides = {
            "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266": {
                "balance": 1000000000000000000  # 1 ETH in wei
            }
        }

        result = eth_call(
            to_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            data="0x70a08231",
            from_address="0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266",
            state_overrides=state_overrides,
        )

        assert result["success"] is True
        
        # Check that integer balance was converted to hex
        call_args = mock_web3.eth.call.call_args
        actual_overrides = call_args[0][2]
        assert actual_overrides["0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"]["balance"] == "0xde0b6b3a7640000"

    @patch("dexter.tools.blockchain.Web3")
    @patch("dexter.tools.blockchain.get_config")
    def test_eth_call_with_code_override(self, mock_get_config, mock_web3_class):
        """Test eth_call with contract code override."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.default_chain.rpc_url = "http://localhost:8545"
        mock_get_config.return_value = mock_config

        mock_web3 = MagicMock()
        mock_web3.is_connected.return_value = True
        mock_web3.to_checksum_address = lambda x: x
        mock_web3.eth.call.return_value = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider.return_value = MagicMock()

        # Test with code override
        state_overrides = {
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": {
                "code": "0x60806040"  # Simple bytecode
            }
        }

        result = eth_call(
            to_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            data="0x",
            state_overrides=state_overrides,
        )

        assert result["success"] is True

    @patch("dexter.tools.blockchain.Web3")
    @patch("dexter.tools.blockchain.get_config")
    def test_eth_call_connection_error(self, mock_get_config, mock_web3_class):
        """Test eth_call with connection error."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.default_chain.rpc_url = "http://localhost:8545"
        mock_get_config.return_value = mock_config

        mock_web3 = MagicMock()
        mock_web3.is_connected.return_value = False
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider.return_value = MagicMock()

        result = eth_call(
            to_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            data="0x70a08231",
        )

        assert result["error"] == "Failed to connect to Ethereum node"

    @patch("dexter.tools.blockchain.Web3")
    @patch("dexter.tools.blockchain.get_config")
    def test_eth_call_contract_error(self, mock_get_config, mock_web3_class):
        """Test eth_call with contract execution error."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.default_chain.rpc_url = "http://localhost:8545"
        mock_get_config.return_value = mock_config

        mock_web3 = MagicMock()
        mock_web3.is_connected.return_value = True
        mock_web3.to_checksum_address = lambda x: x
        mock_web3.eth.call.side_effect = ContractLogicError("execution reverted")
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider.return_value = MagicMock()

        result = eth_call(
            to_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            data="0x70a08231",
        )

        assert result["success"] is False
        assert "execution reverted" in result["error"]
        assert result["error_type"] == "ContractLogicError"

    @patch("dexter.tools.blockchain.Web3")
    @patch("dexter.tools.blockchain.get_config")
    def test_eth_call_with_block_number(self, mock_get_config, mock_web3_class):
        """Test eth_call with specific block number."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.default_chain.rpc_url = "http://localhost:8545"
        mock_get_config.return_value = mock_config

        mock_web3 = MagicMock()
        mock_web3.is_connected.return_value = True
        mock_web3.to_checksum_address = lambda x: x
        mock_web3.eth.call.return_value = b"\x00" * 32
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider.return_value = MagicMock()

        result = eth_call(
            to_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            data="0x70a08231",
            block_number=15000000,
        )

        assert result["success"] is True
        assert result["block"] == 15000000

        # Verify block number was passed to web3.eth.call
        call_args = mock_web3.eth.call.call_args
        assert call_args[0][1] == 15000000

    @patch("dexter.tools.blockchain.Web3")
    @patch("dexter.tools.blockchain.get_config")
    def test_eth_call_with_custom_rpc(self, mock_get_config, mock_web3_class):
        """Test eth_call with custom RPC URL."""
        mock_web3 = MagicMock()
        mock_web3.is_connected.return_value = True
        mock_web3.to_checksum_address = lambda x: x
        mock_web3.eth.call.return_value = b"\x00" * 32
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider.return_value = MagicMock()

        result = eth_call(
            to_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            data="0x70a08231",
            rpc_url="https://custom-rpc.example.com",
        )

        assert result["success"] is True
        
        # Verify custom RPC was used
        mock_web3_class.HTTPProvider.assert_called_with("https://custom-rpc.example.com")
        # Config should not be called when custom RPC is provided
        mock_get_config.assert_not_called()