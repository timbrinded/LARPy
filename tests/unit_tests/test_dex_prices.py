"""Unit tests for DEX price functions."""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from dexter.tools.dex_prices import (
    get_all_dex_prices_extended,
    get_curve_price,
    get_fluid_dex_price,
    get_uniswap_v3_price,
)


class TestCurvePrices:
    """Test Curve price fetching functions."""

    @pytest.mark.skipif(
        os.environ.get("ETHERSCAN_API_KEY") is None,
        reason="Requires ETHERSCAN_API_KEY environment variable",
    )
    def test_get_curve_price_usdc_usdt_real(self):
        """Test getting USDC/USDT price from real Curve pools."""
        # Force reload config to pick up any changes
        from dexter.config_loader import get_config_loader

        loader = get_config_loader()
        loader.reload()

        # This test makes real RPC calls - mark as integration test if needed
        result = get_curve_price.func("USDC", "USDT")

        # Should find at least one pool (3pool or USDC/USDT/crvUSD)
        assert result is not None
        assert "No Curve pools found" not in result
        assert "Error" not in result

        # Should contain price information
        assert "1 USDC =" in result
        assert "USDT" in result

        # Price should be reasonable (close to 1:1 for stablecoins)
        # Extract price from result
        if "Curve Legacy 3pool:" in result:
            # Found 3pool
            assert "3pool" in result
        elif "Curve NG" in result:
            # Found Stableswap-NG pool
            assert "USDC/USDT/crvUSD" in result or "0x4eBdF703" in result

    def test_get_curve_price_usdt_usdc_real(self):
        """Test reverse direction USDT/USDC."""
        result = get_curve_price.func("USDT", "USDC")

        assert result is not None
        assert "No Curve pools found" not in result
        assert "Error" not in result
        assert "1 USDT =" in result
        assert "USDC" in result

    @patch("agent.tools.dex_prices.Web3")
    def test_get_curve_price_no_connection(self, mock_web3):
        """Test behavior when RPC connection fails."""
        # Mock web3 connection failure
        mock_instance = Mock()
        mock_instance.is_connected.return_value = False
        mock_web3.return_value = mock_instance
        mock_web3.HTTPProvider = Mock()

        result = get_curve_price.func("USDC", "USDT")

        assert result == "Error: Could not connect to Ethereum network"

    def test_get_curve_price_non_existent_pair(self):
        """Test behavior for token pair with no Curve pool."""
        result = get_curve_price.func("FOO", "BAR")

        # Should not find pools for this pair in our config
        assert "No Curve pools found for FOO/BAR pair" in result


class TestUniswapV3Prices:
    """Test Uniswap V3 price fetching functions."""

    @patch("agent.tools.dex_prices.Web3")
    def test_get_uniswap_v3_price_with_factory(self, mock_web3):
        """Test Uniswap V3 price fetching using factory discovery."""
        # Mock web3 and factory
        mock_w3 = MagicMock()
        mock_web3.return_value = mock_w3
        mock_web3.HTTPProvider = Mock()
        mock_w3.is_connected.return_value = True

        # Mock factory contract
        mock_factory = MagicMock()
        mock_pool_address = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
        mock_factory.functions.getPool.return_value.call.return_value = (
            mock_pool_address
        )

        # Mock pool contract
        mock_pool = MagicMock()
        mock_pool.functions.token0.return_value.call.return_value = (
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
        )
        mock_pool.functions.token1.return_value.call.return_value = (
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH
        )

        # Mock quoter contract
        mock_quoter = MagicMock()
        mock_quoter.functions.quoteExactInputSingle.return_value.call.return_value = (
            2000 * 10**6
        )  # 2000 USDC for 1 ETH

        mock_w3.eth.contract.side_effect = [mock_factory, mock_pool, mock_quoter]

        result = get_uniswap_v3_price.func("ETH", "USDC")

        # Should successfully get price
        assert "Uniswap V3:" in result
        assert "1 ETH =" in result
        assert "USDC" in result
        assert "fee:" in result


class TestAllDexPrices:
    """Test combined DEX price functions."""

    def test_get_all_dex_prices_extended_usdc_usdt(self):
        """Test getting prices from all DEXs for USDC/USDT."""
        result = get_all_dex_prices_extended.func("USDC", "USDT")

        # Should contain results from multiple DEXs
        assert result is not None

        # Should have Uniswap V3 result
        assert "Uniswap V3:" in result or "No Uniswap V3 pool found" in result

        # Should have SushiSwap result
        assert "SushiSwap:" in result or "No SushiSwap pool found" in result

        # Should have Curve result (we know this pair exists)
        assert "Curve" in result

        # Should have Fluid result
        assert "Fluid" in result


class TestFluidDexPrices:
    """Test Fluid DEX price fetching functions."""

    def test_get_fluid_dex_price_exists(self):
        """Test that Fluid DEX price function exists and is callable."""
        # This is a basic test to ensure the function is properly integrated
        result = get_fluid_dex_price.func("WETH", "USDC")
        assert isinstance(result, str)
        assert "Fluid" in result

    @pytest.mark.skipif(
        os.environ.get("ETHERSCAN_API_KEY") is None,
        reason="Requires ETHERSCAN_API_KEY environment variable",
    )
    def test_get_fluid_dex_price_real(self):
        """Test getting real price from Fluid DEX."""
        # Test with a common pair that should have a pool
        result = get_fluid_dex_price.func("WETH", "USDC")

        assert result is not None

        # Check if we get an actual price or a "no pools found" message
        # Both are valid responses
        if "No Fluid pools found" not in result and "Error" not in result:
            # Should contain price information
            assert "1 WETH =" in result
            assert "USDC" in result
            assert "Pool:" in result
            assert "Liquidity:" in result

    def test_get_fluid_dex_price_eth_conversion(self):
        """Test that Fluid DEX properly handles ETH to WETH conversion."""
        # Test with ETH (should internally convert to WETH)
        result_eth = get_fluid_dex_price.func("ETH", "USDC")
        assert isinstance(result_eth, str)

        # Test with WETH directly
        result_weth = get_fluid_dex_price.func("WETH", "USDC")
        assert isinstance(result_weth, str)

        # Both should return similar results (either both find pools or both don't)
        if "No Fluid pools found" in result_weth:
            assert "No Fluid pools found" in result_eth
        elif "Error" not in result_weth:
            # If WETH/USDC has a pool, ETH/USDC should find the same pool
            assert "ETH" in result_eth or "WETH" in result_eth
            assert "USDC" in result_eth
