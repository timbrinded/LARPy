"""Validation rules and criteria for transaction evaluation."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    category: str  # gas, security, efficiency, correctness
    message: str
    severity: str  # critical, warning, info
    optimization_tip: str | None = None


@dataclass
class GasThresholds:
    """Gas thresholds for different transaction types."""

    eth_transfer: int = 21000
    erc20_transfer: int = 65000
    simple_swap: int = 150000
    complex_swap: int = 300000
    multi_hop_swap: int = 500000


@dataclass
class SecurityRules:
    """Security validation rules."""

    max_slippage_percent: Decimal = Decimal("2.0")
    require_simulation: bool = True
    max_value_without_confirmation: int = 10**18  # 1 ETH
    allowed_protocols: list[str] | None = None

    def __post_init__(self):
        """Initialize allowed protocols if not provided."""
        if self.allowed_protocols is None:
            self.allowed_protocols = [
                "uniswap_v3",
                "sushiswap",
                "curve",
                "balancer",
                "1inch",
            ]


@dataclass
class EfficiencyRules:
    """Efficiency validation rules."""

    max_price_impact_percent: Decimal = Decimal("1.0")
    min_output_ratio: Decimal = Decimal("0.98")  # 98% of expected output
    prefer_direct_paths: bool = True
    max_hops: int = 3


class ValidationRuleEngine:
    """Engine for applying validation rules to transactions."""

    def __init__(self):
        """Initialize validation rule engine with default thresholds and rules."""
        self.gas_thresholds = GasThresholds()
        self.security_rules = SecurityRules()
        self.efficiency_rules = EfficiencyRules()

    def validate_gas(self, tx_data: dict, tx_type: str) -> ValidationResult:
        """Validate gas usage for a transaction."""
        gas_limit = tx_data.get("gas", 0)

        threshold_map = {
            "eth_transfer": self.gas_thresholds.eth_transfer,
            "erc20_transfer": self.gas_thresholds.erc20_transfer,
            "simple_swap": self.gas_thresholds.simple_swap,
            "complex_swap": self.gas_thresholds.complex_swap,
            "multi_hop_swap": self.gas_thresholds.multi_hop_swap,
        }

        threshold = threshold_map.get(tx_type, self.gas_thresholds.complex_swap)

        if gas_limit > threshold * 1.5:
            return ValidationResult(
                passed=False,
                category="gas",
                message=f"Gas limit {gas_limit} exceeds threshold {threshold} by >50%",
                severity="warning",
                optimization_tip=f"Consider optimizing transaction path or splitting into smaller transactions. Target gas: {threshold}",
            )

        return ValidationResult(
            passed=True,
            category="gas",
            message=f"Gas limit {gas_limit} is within acceptable range",
            severity="info",
        )

    def validate_slippage(
        self, expected_output: int, min_output: int
    ) -> ValidationResult:
        """Validate slippage tolerance."""
        if expected_output == 0:
            return ValidationResult(
                passed=False,
                category="correctness",
                message="Expected output is zero",
                severity="critical",
            )

        slippage = (
            Decimal(expected_output - min_output) / Decimal(expected_output) * 100
        )

        if slippage > self.security_rules.max_slippage_percent:
            return ValidationResult(
                passed=False,
                category="security",
                message=f"Slippage {slippage:.2f}% exceeds maximum {self.security_rules.max_slippage_percent}%",
                severity="warning",
                optimization_tip="Reduce transaction size or use a different liquidity source with better depth",
            )

        return ValidationResult(
            passed=True,
            category="security",
            message=f"Slippage {slippage:.2f}% is acceptable",
            severity="info",
        )

    def validate_value(
        self, value: int, requires_confirmation: bool = True
    ) -> ValidationResult:
        """Validate transaction value."""
        if (
            requires_confirmation
            and value > self.security_rules.max_value_without_confirmation
        ):
            return ValidationResult(
                passed=False,
                category="security",
                message=f"Transaction value {value} exceeds confirmation threshold",
                severity="warning",
                optimization_tip="Consider splitting into smaller transactions or implementing additional confirmation steps",
            )

        return ValidationResult(
            passed=True,
            category="security",
            message="Transaction value is within limits",
            severity="info",
        )

    def validate_protocol(self, protocol: str) -> ValidationResult:
        """Validate the protocol being used."""
        if protocol not in self.security_rules.allowed_protocols:
            return ValidationResult(
                passed=False,
                category="security",
                message=f"Protocol {protocol} is not in allowed list",
                severity="critical",
                optimization_tip=f"Use one of the allowed protocols: {', '.join(self.security_rules.allowed_protocols)}",
            )

        return ValidationResult(
            passed=True,
            category="security",
            message=f"Protocol {protocol} is allowed",
            severity="info",
        )

    def validate_path_efficiency(
        self, path: list[str], direct_available: bool
    ) -> ValidationResult:
        """Validate swap path efficiency."""
        hop_count = len(path) - 1

        if hop_count > self.efficiency_rules.max_hops:
            return ValidationResult(
                passed=False,
                category="efficiency",
                message=f"Path has {hop_count} hops, exceeds maximum {self.efficiency_rules.max_hops}",
                severity="warning",
                optimization_tip="Look for more direct routes or split the trade",
            )

        if (
            direct_available
            and hop_count > 1
            and self.efficiency_rules.prefer_direct_paths
        ):
            return ValidationResult(
                passed=False,
                category="efficiency",
                message=f"Using {hop_count}-hop path when direct path is available",
                severity="warning",
                optimization_tip="Use the direct trading pair for better gas efficiency",
            )

        return ValidationResult(
            passed=True,
            category="efficiency",
            message=f"Path with {hop_count} hop(s) is acceptable",
            severity="info",
        )
