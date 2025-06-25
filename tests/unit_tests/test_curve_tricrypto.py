"""Test Curve TriCrypto pool functionality."""


class TestCurveTriCrypto:
    """Test that Curve TriCrypto pools work correctly."""

    def test_curve_tricrypto_eth_usdc_configured(self):
        """Test that TriCryptoUSDC pool is properly configured."""
        # Import config to check
        from agent.config_loader import get_config

        config = get_config()
        curve_config = config.dexes.get("curve")

        # Find TriCryptoUSDC pool
        tricrypto_pool = None
        for pool in curve_config.pools:
            if pool.name == "TriCryptoUSDC":
                tricrypto_pool = pool
                break

        assert tricrypto_pool is not None
        assert tricrypto_pool.address == "0x7F86Bf177Dd4F3494b841a37e810A34dD56c829B"
        assert "ETH" in tricrypto_pool.tokens
        assert "USDC" in tricrypto_pool.tokens
        assert "WBTC" in tricrypto_pool.tokens
        assert tricrypto_pool.pool_type == "tricrypto"
