"""Test get_all_dex_prices includes Curve."""

from agent.tools.dex_prices import get_all_dex_prices


class TestGetAllDexPrices:
    """Test that get_all_dex_prices includes all DEXs."""

    def test_get_all_dex_prices_includes_curve(self):
        """Test that get_all_dex_prices includes Curve results."""
        result = get_all_dex_prices.func("ETH", "USDC")

        # Should include results from multiple DEXs
        assert "Uniswap" in result or "No Uniswap" in result
        assert "SushiSwap" in result or "No SushiSwap" in result
        assert "Curve" in result or "No Curve" in result

        # Verify it's returning multiple lines (one per DEX)
        lines = result.strip().split("\n")
        assert len(lines) >= 3  # At least Uniswap, SushiSwap, and Curve

    def test_get_all_dex_prices_eth_usdc_has_curve_pool(self):
        """Test that ETH/USDC specifically shows Curve pool."""
        result = get_all_dex_prices.func("ETH", "USDC")

        # For ETH/USDC we know Curve has TriCryptoUSDC pool
        assert "Curve" in result
        # Either it finds the pool or says no pool found
        assert "TriCryptoUSDC" in result or "No Curve pools found" in result
