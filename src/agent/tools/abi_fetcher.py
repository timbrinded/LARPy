"""Fetch contract ABIs dynamically from Etherscan."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List

import requests
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

logger = logging.getLogger(__name__)


class ABIFetcher:
    """Fetch and cache contract ABIs from Etherscan."""

    def __init__(self, api_key: str | None = None, cache_dir: str | None = None):
        """Initialize the ABI fetcher.

        Args:
            api_key: Etherscan API key. If not provided, tries ETHERSCAN_API_KEY env var.
            cache_dir: Directory to cache ABIs. Defaults to ~/.cache/contract_abis
        """
        self.api_key = api_key or os.environ.get("ETHERSCAN_API_KEY", "")
        self.base_url = "https://api.etherscan.io/api"

        # Set up cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".cache" / "contract_abis"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_abi(
        self, contract_address: str, force_refresh: bool = False
    ) -> List[Dict] | None:
        """Get ABI for a contract address, using cache if available.

        Args:
            contract_address: The contract address to get ABI for
            force_refresh: Force refresh from Etherscan even if cached

        Returns:
            The contract ABI as a list of dicts, or None if not found
        """
        address = Web3.to_checksum_address(contract_address)

        cache_file = self.cache_dir / f"{address.lower()}.json"
        if not force_refresh and cache_file.exists():
            try:
                with open(cache_file) as f:
                    return json.load(f)
            except Exception:
                pass

        abi = self._fetch_from_etherscan(address)

        if abi:
            try:
                with open(cache_file, "w") as f:
                    json.dump(abi, f, indent=2)
            except Exception:
                pass

        return abi

    def _fetch_from_etherscan(self, address: str) -> List[Dict] | None:
        """Fetch ABI from Etherscan API.

        Args:
            address: The contract address

        Returns:
            The ABI or None if not found/verified
        """
        if not self.api_key:
            logger.info(
                "Warning: No Etherscan API key provided. Using public rate limit."
            )

        params = {
            "module": "contract",
            "action": "getabi",
            "address": address,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get("status") == "1" and data.get("result"):
                # Parse the ABI JSON string
                return json.loads(data["result"])
            else:
                # Contract not verified or other error
                return None

        except Exception as e:
            logger.info(f"Error fetching ABI from Etherscan: {e}")
            return None

    def get_curve_pool_abi(self, pool_address: str) -> List[Dict] | None:
        """Get ABI for a Curve pool, with fallback to common Curve ABIs.

        Args:
            pool_address: The Curve pool address

        Returns:
            The pool ABI or a minimal fallback ABI
        """
        # Try to get from Etherscan first
        abi = self.get_abi(pool_address)

        if abi:
            return abi

        # For 3pool specifically, use int128 (legacy Vyper 0.1.x)
        if pool_address.lower() == "0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7":
            return [
                {
                    "name": "coins",
                    "inputs": [{"type": "int128", "name": "i"}],
                    "outputs": [{"type": "address", "name": ""}],
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "name": "get_dy",
                    "inputs": [
                        {"type": "int128", "name": "i"},
                        {"type": "int128", "name": "j"},
                        {"type": "uint256", "name": "dx"},
                    ],
                    "outputs": [{"type": "uint256", "name": ""}],
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "name": "balances",
                    "inputs": [{"type": "int128", "name": "i"}],
                    "outputs": [{"type": "uint256", "name": ""}],
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "name": "fee",
                    "inputs": [],
                    "outputs": [{"type": "uint256", "name": ""}],
                    "stateMutability": "view",
                    "type": "function",
                },
            ]

        # Fallback for newer Curve pools (Vyper 0.2.x)
        return [
            {
                "name": "coins",
                "inputs": [{"type": "uint256", "name": "i"}],
                "outputs": [{"type": "address", "name": ""}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "name": "get_dy",
                "inputs": [
                    {"type": "uint256", "name": "i"},
                    {"type": "uint256", "name": "j"},
                    {"type": "uint256", "name": "dx"},
                ],
                "outputs": [{"type": "uint256", "name": ""}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "name": "balances",
                "inputs": [{"type": "int128", "name": "i"}],
                "outputs": [{"type": "uint256", "name": ""}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "name": "fee",
                "inputs": [],
                "outputs": [{"type": "uint256", "name": ""}],
                "stateMutability": "view",
                "type": "function",
            },
        ]

    def get_uniswap_v3_factory_abi(self) -> List[Dict]:
        """Get minimal Uniswap V3 factory ABI."""
        return [
            {
                "inputs": [
                    {"internalType": "address", "name": "tokenA", "type": "address"},
                    {"internalType": "address", "name": "tokenB", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                ],
                "name": "getPool",
                "outputs": [
                    {"internalType": "address", "name": "pool", "type": "address"}
                ],
                "stateMutability": "view",
                "type": "function",
            }
        ]

    def get_uniswap_v3_pool_abi(self) -> List[Dict]:
        """Get minimal Uniswap V3 pool ABI."""
        return [
            {
                "inputs": [],
                "name": "token0",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "token1",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function",
            },
        ]


_abi_fetcher = None


def get_abi_fetcher() -> ABIFetcher:
    """Get global ABI fetcher instance."""
    global _abi_fetcher
    if _abi_fetcher is None:
        _abi_fetcher = ABIFetcher()
    return _abi_fetcher
