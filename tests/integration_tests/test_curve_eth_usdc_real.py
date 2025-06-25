"""Integration test to verify Curve ETH/USDC actually works with real config."""

from agent.tools.dex_prices import get_curve_price


class TestCurveETHUSDCReal:
    """Test real Curve ETH/USDC functionality."""

    def test_curve_eth_to_usdc_works(self):
        """Test that ETH to USDC pricing works on Curve."""
        result = get_curve_price.func("ETH", "USDC")

        # Should find a pool
        assert "No Curve pools found" not in result
        assert "Curve" in result
        assert "ETH" in result
        assert "USDC" in result

        # Should be from TriCryptoUSDC pool
        assert "TriCryptoUSDC" in result

    def test_curve_usdc_to_eth_works(self):
        """Test that USDC to ETH pricing works on Curve."""
        result = get_curve_price.func("USDC", "ETH")

        # Should find a pool
        assert "No Curve pools found" not in result
        assert "Curve" in result
        assert "USDC" in result
        assert "ETH" in result

        # Should be from TriCryptoUSDC pool
        assert "TriCryptoUSDC" in result

    def test_curve_weth_to_usdc_works(self):
        """Test that WETH to USDC also works (should normalize to ETH)."""
        result = get_curve_price.func("WETH", "USDC")

        # Should find a pool (ETH gets normalized)
        assert "No Curve pools found" not in result
        assert "Curve" in result
        assert "USDC" in result
