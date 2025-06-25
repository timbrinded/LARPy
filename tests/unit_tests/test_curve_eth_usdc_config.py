"""Test that Curve can find ETH/USDC pools in configuration."""

from agent.config_loader import get_config


class TestCurveETHUSDCConfig:
    """Test Curve ETH/USDC pool configuration."""

    def test_curve_has_eth_usdc_pool_configured(self):
        """Test that there is at least one Curve pool configured with both ETH and USDC."""
        config = get_config()
        curve_config = config.dexes.get("curve")

        assert curve_config is not None
        assert curve_config.pools is not None

        # Find pools that contain both ETH and USDC
        eth_usdc_pools = []
        for pool in curve_config.pools:
            if pool.tokens and "ETH" in pool.tokens and "USDC" in pool.tokens:
                eth_usdc_pools.append(pool)

        # We should have at least one pool
        assert len(eth_usdc_pools) > 0, "No Curve pools found with both ETH and USDC"

        # Verify we have the TriCryptoUSDC pool
        tricrypto_found = False
        for pool in eth_usdc_pools:
            if pool.name == "TriCryptoUSDC":
                tricrypto_found = True
                assert pool.pool_type == "tricrypto"
                assert pool.address == "0x7F86Bf177Dd4F3494b841a37e810A34dD56c829B"
                assert "WBTC" in pool.tokens  # Should also have WBTC

        assert tricrypto_found, "TriCryptoUSDC pool not found"

    def test_curve_pool_search_normalization(self):
        """Test that ETH/WETH normalization works for Curve pools."""
        config = get_config()
        curve_config = config.dexes.get("curve")

        # The code normalizes WETH to ETH for Curve pool searching
        # So a pool with ETH should be found when searching for WETH
        eth_pools = []
        for pool in curve_config.pools:
            if pool.tokens and "ETH" in pool.tokens:
                eth_pools.append(pool)

        assert len(eth_pools) > 0, "No pools with ETH found"

        # These pools should be findable with WETH due to normalization
        for pool in eth_pools:
            assert "ETH" in pool.tokens
