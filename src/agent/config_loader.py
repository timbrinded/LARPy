"""Configuration loader utility for loading YAML configs into Pydantic models."""

from pathlib import Path
from typing import Dict

import yaml

from .config_models import (
    ArbitrageConfig,
    ChainConfig,
    Config,
    ContractConfig,
    DexConfig,
    ModelConfig,
    PoolConfig,
    TokenConfig,
)


class ConfigLoader:
    """Loads and manages configuration from YAML files."""

    def __init__(self, config_dir: str | None = None):
        """Initialize the config loader.

        Args:
            config_dir: Path to the configuration directory.
                       Defaults to 'configs' in the project root.
        """
        if config_dir is None:
            # Get the project root (two levels up from this file)
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "configs"

        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            raise ValueError(f"Configuration directory not found: {self.config_dir}")

        self._config: Config | None = None

    def load(self) -> Config:
        """Load all configuration files and return the combined config.

        Returns:
            Config: The loaded configuration object.
        """
        if self._config is not None:
            return self._config

        # Load chains
        chains = self._load_yaml("chains.yaml")
        chain_configs = {}
        if chains:
            for name, chain_data in chains.items():
                chain_configs[name] = ChainConfig(**chain_data)

        # Load tokens
        tokens = self._load_yaml("tokens.yaml")
        token_configs = {}
        if tokens:
            for symbol, token_data in tokens.items():
                token_configs[symbol] = TokenConfig(**token_data)

        # Load DEXes and their pools
        dexes = self._load_yaml("dexes.yaml")
        dex_configs = {}
        if dexes:
            for dex_name, dex_data in dexes.items():
                # Convert pool dicts to PoolConfig objects
                pools = []
                if "pools" in dex_data:
                    for pool_data in dex_data["pools"]:
                        pools.append(PoolConfig(**pool_data))
                    dex_data["pools"] = pools

                # Convert contract dicts to ContractConfig objects
                contracts = []
                if "contracts" in dex_data:
                    for contract_data in dex_data["contracts"]:
                        contracts.append(ContractConfig(**contract_data))
                    dex_data["contracts"] = contracts

                dex_configs[dex_name] = DexConfig(**dex_data)

        # Load arbitrage config
        arbitrage_data = self._load_yaml("arbitrage.yaml")
        arbitrage_config = (
            ArbitrageConfig(**arbitrage_data) if arbitrage_data else ArbitrageConfig()
        )

        # Load model config
        model_data = self._load_yaml("models.yaml")
        model_config = ModelConfig(**model_data) if model_data else ModelConfig()

        # Create the combined config
        self._config = Config(
            chains=chain_configs,
            tokens=token_configs,
            dexes=dex_configs,
            arbitrage=arbitrage_config,
            models=model_config,
        )

        return self._config

    def _load_yaml(self, filename: str) -> Dict | None:
        """Load a YAML file from the config directory.

        Args:
            filename: Name of the YAML file to load.

        Returns:
            Dict or None: The loaded YAML data or None if file doesn't exist.
        """
        filepath = self.config_dir / filename
        if not filepath.exists():
            return None

        with open(filepath) as f:
            return yaml.safe_load(f)

    def get_token_address(self, symbol: str) -> str | None:
        """Get token address by symbol.

        Args:
            symbol: Token symbol (e.g., "WETH", "USDC").

        Returns:
            Optional[str]: Token address or None if not found.
        """
        config = self.load()
        token = config.tokens.get(symbol)
        return token.address if token else None

    def get_pool(
        self, dex: str, token0: str, token1: str, fee: int | None = None
    ) -> PoolConfig | None:
        """Find a pool by DEX and token pair.

        Args:
            dex: DEX name (e.g., "uniswap_v3", "sushiswap").
            token0: First token symbol.
            token1: Second token symbol.
            fee: Optional fee tier for Uniswap V3.

        Returns:
            Optional[PoolConfig]: Pool configuration or None if not found.
        """
        config = self.load()
        dex_config = config.dexes.get(dex)
        if not dex_config:
            return None

        for pool in dex_config.pools:
            # Check both token order combinations
            if (pool.token0 == token0 and pool.token1 == token1) or (
                pool.token0 == token1 and pool.token1 == token0
            ):
                # For Uniswap V3, also match fee
                if dex == "uniswap_v3" and fee is not None and pool.fee != fee:
                    continue
                return pool

        return None

    def reload(self) -> Config:
        """Reload configuration from disk.

        Returns:
            Config: The reloaded configuration object.
        """
        self._config = None
        return self.load()


# Global config loader instance
_config_loader = None


def get_config_loader() -> ConfigLoader:
    """Get the global config loader instance.

    Returns:
        ConfigLoader: The global config loader.
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def get_config() -> Config:
    """Get the loaded configuration.

    Returns:
        Config: The loaded configuration object.
    """
    return get_config_loader().load()
