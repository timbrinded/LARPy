"""Test stablecoin fungibility functionality."""

from unittest.mock import patch

from dexter.tools.dex_prices import (
    get_all_dex_prices_with_stablecoin_fungibility,
    get_stablecoin_substitutes,
)


class TestStablecoinFungibility:
    """Test stablecoin fungibility features."""

    def test_get_stablecoin_substitutes(self):
        """Test getting stablecoin substitutes."""
        # Test USDC substitutes
        usdc_subs = get_stablecoin_substitutes("USDC")
        assert "USDT" in usdc_subs
        assert "DAI" in usdc_subs
        assert len(usdc_subs) == 2

        # Test USDT substitutes
        usdt_subs = get_stablecoin_substitutes("USDT")
        assert "USDC" in usdt_subs
        assert "DAI" in usdt_subs
        assert len(usdt_subs) == 2

        # Test DAI substitutes
        dai_subs = get_stablecoin_substitutes("DAI")
        assert "USDC" in dai_subs
        assert "USDT" in dai_subs
        assert len(dai_subs) == 2

        # Test non-stablecoin returns empty
        eth_subs = get_stablecoin_substitutes("ETH")
        assert eth_subs == []

        # Test case insensitive
        usdc_lower = get_stablecoin_substitutes("usdc")
        assert usdc_lower == usdc_subs

    @patch("agent.tools.dex_prices.get_all_dex_prices_extended")
    def test_get_prices_with_stablecoin_fungibility_eth_to_usdc(self, mock_get_prices):
        """Test getting prices with stablecoin fungibility for ETH->USDC."""

        # Mock the extended prices function to return strings directly
        def mock_func_return(from_token, to_token):
            if from_token == "ETH" and to_token == "USDC":
                return "Uniswap V3: 1 ETH = 2000.000000 USDC (fee: 0.05%)"
            elif from_token == "ETH" and to_token == "USDT":
                return "Uniswap V3: 1 ETH = 2001.000000 USDT (fee: 0.05%)"
            elif from_token == "USDT" and to_token == "USDC":
                return "Curve 3pool: 1 USDT = 0.999900 USDC"
            elif from_token == "ETH" and to_token == "DAI":
                return "SushiSwap: 1 ETH = 1999.500000 DAI"
            elif from_token == "DAI" and to_token == "USDC":
                return "Curve 3pool: 1 DAI = 1.000100 USDC"
            else:
                return f"No pool found for {from_token}/{to_token}"

        mock_get_prices.func = mock_func_return

        # Call the function
        result = get_all_dex_prices_with_stablecoin_fungibility.invoke(
            {"from_token": "ETH", "to_token": "USDC"}
        )

        # Verify results
        assert "=== Direct Prices ===" in result
        assert "2000.000000 USDC" in result

        assert "=== Prices via stablecoin substitutes for USDC ===" in result
        assert "Via USDT" in result
        assert "Step 1: ETH -> USDT" in result
        assert "2001.000000 USDT" in result
        assert "Step 2: USDT -> USDC" in result
        assert "0.999900 USDC" in result

        assert "Via DAI" in result
        assert "Step 1: ETH -> DAI" in result
        assert "1999.500000 DAI" in result
        assert "Step 2: DAI -> USDC" in result
        assert "1.000100 USDC" in result

    @patch("agent.tools.dex_prices.get_all_dex_prices_extended")
    def test_get_prices_with_stablecoin_fungibility_usdc_to_eth(self, mock_get_prices):
        """Test getting prices with stablecoin fungibility for USDC->ETH."""

        # Mock the extended prices function to return strings directly
        def mock_func_return(from_token, to_token):
            if from_token == "USDC" and to_token == "ETH":
                return "Uniswap V3: 1 USDC = 0.000500 ETH (fee: 0.05%)"
            elif from_token == "USDT" and to_token == "ETH":
                return "Uniswap V3: 1 USDT = 0.000499 ETH (fee: 0.05%)"
            elif from_token == "USDC" and to_token == "USDT":
                return "Curve 3pool: 1 USDC = 1.000100 USDT"
            elif from_token == "DAI" and to_token == "ETH":
                return "SushiSwap: 1 DAI = 0.000501 ETH"
            elif from_token == "USDC" and to_token == "DAI":
                return "Curve 3pool: 1 USDC = 0.999900 DAI"
            else:
                return f"No pool found for {from_token}/{to_token}"

        mock_get_prices.func = mock_func_return

        # Call the function
        result = get_all_dex_prices_with_stablecoin_fungibility.invoke(
            {"from_token": "USDC", "to_token": "ETH"}
        )

        # Verify results
        assert "=== Direct Prices ===" in result
        assert "0.000500 ETH" in result

        assert "=== Prices starting from stablecoin substitutes for USDC ===" in result
        assert "From USDT" in result
        assert "Step 1: USDT -> ETH" in result
        assert "0.000499 ETH" in result
        assert "Step 2: USDC -> USDT" in result
        assert "1.000100 USDT" in result
