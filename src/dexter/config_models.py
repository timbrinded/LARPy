"""Pydantic models for configuration schemas."""

from typing import Dict, List

from pydantic import BaseModel, Field


class ChainConfig(BaseModel):
    """Configuration for a blockchain network."""

    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str | None = None
    native_token: str = "ETH"
    block_time: float = Field(default=12.0, description="Average block time in seconds")


class TokenConfig(BaseModel):
    """Configuration for a token."""

    address: str
    symbol: str
    name: str
    decimals: int
    chain_id: int = 1  # Default to Ethereum mainnet
    curve_address: str | None = None  # Special address for Curve protocol


class PoolConfig(BaseModel):
    """Configuration for a DEX pool."""

    address: str
    token0: str | None = None  # Optional for compatibility with multi-token pools
    token1: str | None = None  # Optional for compatibility with multi-token pools
    tokens: List[str] | None = None  # For Curve pools with multiple tokens
    fee: int | None = None  # For Uniswap V3
    dex: str
    chain_id: int = 1
    pool_type: str | None = None  # e.g. "legacy", "stableswap-ng"
    name: str | None = None  # Human-readable pool name


class ContractConfig(BaseModel):
    """Configuration for a smart contract."""

    address: str
    name: str
    abi: List[Dict]
    chain_id: int = 1


class DexConfig(BaseModel):
    """Configuration for a DEX."""

    name: str
    router_address: str | None = None
    factory_address: str | None = None
    quoter_address: str | None = None
    views_address: str | None = None  # For Curve Stableswap-NG Views contract
    registry_address: str | None = None  # For Curve main registry
    liquidity_address: str | None = None  # For Fluid liquidity contract
    resolver_address: str | None = None  # For Fluid resolver contract
    reserves_resolver_address: str | None = None  # For Fluid reserves resolver
    pools: List[PoolConfig] = []
    contracts: List[ContractConfig] = []


class ArbitrageConfig(BaseModel):
    """Configuration for arbitrage parameters."""

    min_profit_percentage: float = Field(
        default=0.5, description="Minimum profit percentage"
    )
    gas_cost_estimate_eth: float = Field(
        default=0.01, description="Estimated gas cost in ETH"
    )
    max_slippage: float = Field(default=0.5, description="Maximum slippage percentage")
    flash_loan_fee: float = Field(default=0.09, description="Flash loan fee percentage")
    default_gas_limit: int = Field(
        default=200000, description="Default gas limit for transactions"
    )
    default_token_pairs: List[List[str]] = Field(
        default_factory=lambda: [
            ["WETH", "USDC"],
            ["WETH", "USDT"],
            ["USDC", "USDT"],
            ["WETH", "DAI"],
            ["USDC", "DAI"],
        ]
    )


class ModelConfig(BaseModel):
    """Configuration for LLM models."""

    provider: str = "openai"
    model_name: str = "gpt-4o-mini"
    max_tokens: int | None = None


class Config(BaseModel):
    """Main configuration container."""

    chains: Dict[str, ChainConfig] = {}
    tokens: Dict[str, TokenConfig] = {}
    dexes: Dict[str, DexConfig] = {}
    arbitrage: ArbitrageConfig = ArbitrageConfig()
    models: ModelConfig = ModelConfig()

    @property
    def default_chain(self) -> ChainConfig:
        """Get the default chain configuration (Ethereum mainnet)."""
        return self.chains.get(
            "ethereum",
            ChainConfig(
                name="Ethereum", chain_id=1, rpc_url="https://eth.llamarpc.com"
            ),
        )
