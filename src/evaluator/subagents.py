"""Specialized subagents for deep transaction analysis."""

import asyncio
from abc import ABC, abstractmethod

from web3 import Web3

from .validation_rules import ValidationResult


class SubAgent(ABC):
    """Base class for specialized validation subagents."""

    @abstractmethod
    async def analyze(
        self, transaction: dict, objective: dict, context: dict
    ) -> list[ValidationResult]:
        """Perform specialized analysis on the transaction."""
        pass


class GasAnalyzer(SubAgent):
    """Specialized agent for deep gas analysis."""

    def __init__(self):
        """Initialize the gas analyzer."""
        self.w3 = Web3()
        self.gas_patterns = {
            "storage_write": 20000,
            "storage_read": 2100,
            "sstore_init": 20000,
            "sstore_update": 5000,
            "log_base": 375,
            "log_topic": 375,
            "log_data_byte": 8,
        }

    async def analyze(
        self, transaction: dict, objective: dict, context: dict
    ) -> list[ValidationResult]:
        """Analyze gas usage patterns and optimization opportunities."""
        results = []

        # Decode transaction data
        data = transaction.get("data", "0x")
        if len(data) > 10:
            # Analyze calldata size impact
            calldata_gas = self._calculate_calldata_gas(data)

            if calldata_gas > 50000:
                results.append(
                    ValidationResult(
                        passed=False,
                        category="gas",
                        message=f"Calldata alone costs {calldata_gas} gas",
                        severity="warning",
                        optimization_tip="Consider using more efficient encoding or calldata compression",
                    )
                )

            # Check for storage access patterns
            storage_analysis = await self._analyze_storage_access(transaction, context)
            results.extend(storage_analysis)

        # Analyze gas price strategy
        gas_price_analysis = self._analyze_gas_price_strategy(transaction, context)
        results.extend(gas_price_analysis)

        return results

    def _calculate_calldata_gas(self, data: str) -> int:
        """Calculate gas cost of calldata."""
        if data.startswith("0x"):
            data = data[2:]

        byte_data = bytes.fromhex(data)
        gas = 0

        for byte in byte_data:
            if byte == 0:
                gas += 4  # Zero byte costs 4 gas
            else:
                gas += 16  # Non-zero byte costs 16 gas

        return gas

    async def _analyze_storage_access(
        self, transaction: dict, context: dict
    ) -> list[ValidationResult]:
        """Analyze potential storage access patterns."""
        results = []

        # This would ideally trace the transaction to identify storage operations
        # For now, we'll use heuristics based on function selectors
        data = transaction.get("data", "0x")
        if len(data) >= 10:
            selector = data[:10]

            # Common storage-heavy operations
            storage_heavy_selectors = {
                "0x095ea7b3": "approve",  # Often updates allowance mapping
                "0x23b872dd": "transferFrom",  # Multiple storage updates
                "0x40c10f19": "mint",  # Usually updates multiple storage slots
            }

            if selector in storage_heavy_selectors:
                func_name = storage_heavy_selectors[selector]
                results.append(
                    ValidationResult(
                        passed=True,
                        category="gas",
                        message=f"Function {func_name} typically involves multiple storage operations",
                        severity="info",
                        optimization_tip="Consider batching multiple calls if possible",
                    )
                )

        return results

    def _analyze_gas_price_strategy(
        self, transaction: dict, context: dict
    ) -> list[ValidationResult]:
        """Analyze gas price strategy."""
        results = []

        # Check if using EIP-1559
        if "maxFeePerGas" in transaction and "maxPriorityFeePerGas" in transaction:
            base_fee = context.get("current_base_fee", 30e9)  # 30 gwei default
            max_fee = int(transaction["maxFeePerGas"])
            priority_fee = int(transaction["maxPriorityFeePerGas"])

            if max_fee < base_fee * 1.25:
                results.append(
                    ValidationResult(
                        passed=False,
                        category="gas",
                        message="Max fee might be too low for timely inclusion",
                        severity="warning",
                        optimization_tip=f"Consider setting maxFeePerGas to at least {int(base_fee * 1.5)} wei",
                    )
                )

            if priority_fee < 1e9:  # Less than 1 gwei
                results.append(
                    ValidationResult(
                        passed=False,
                        category="gas",
                        message="Priority fee too low, transaction might be slow",
                        severity="warning",
                        optimization_tip="Set priority fee to at least 2 gwei for reasonable inclusion time",
                    )
                )

        return results


class SecurityValidator(SubAgent):
    """Specialized agent for security validation."""

    def __init__(self):
        """Initialize the security validator."""
        self.known_vulnerabilities = {
            "reentrancy": ["0x", "call", "delegatecall"],
            "front_running": ["swap", "exchange", "trade"],
            "access_control": ["owner", "admin", "governance"],
        }

    async def analyze(
        self, transaction: dict, objective: dict, context: dict
    ) -> list[ValidationResult]:
        """Perform security analysis."""
        results = []

        # Check for reentrancy risks
        reentrancy_check = await self._check_reentrancy_risk(transaction)
        results.extend(reentrancy_check)

        # Check for front-running vulnerability
        frontrun_check = self._check_frontrunning_risk(transaction, objective)
        results.extend(frontrun_check)

        # Validate permissions and access control
        access_check = await self._check_access_control(transaction, context)
        results.extend(access_check)

        # Check for known vulnerable contracts
        contract_check = self._check_contract_safety(transaction)
        results.extend(contract_check)

        return results

    async def _check_reentrancy_risk(self, transaction: dict) -> list[ValidationResult]:
        """Check for potential reentrancy vulnerabilities."""
        results = []

        # Check if transaction involves ETH transfer with complex logic
        if (
            int(transaction.get("value", 0)) > 0
            and len(transaction.get("data", "0x")) > 10
        ):
            results.append(
                ValidationResult(
                    passed=False,
                    category="security",
                    message="Transaction sends ETH while executing complex logic",
                    severity="warning",
                    optimization_tip="Ensure the target contract follows checks-effects-interactions pattern",
                )
            )

        return results

    def _check_frontrunning_risk(
        self, transaction: dict, objective: dict
    ) -> list[ValidationResult]:
        """Check for front-running vulnerabilities."""
        results = []

        obj_type = objective.get("type", "").lower()
        value = int(transaction.get("value", 0))

        # High-value swaps without protection
        if "swap" in obj_type and value > 5 * 10**18:  # > 5 ETH
            if not objective.get("mev_protection", False):
                results.append(
                    ValidationResult(
                        passed=False,
                        category="security",
                        message="Large swap without MEV protection is vulnerable to sandwich attacks",
                        severity="critical",
                        optimization_tip="Use Flashbots RPC or implement commit-reveal pattern",
                    )
                )

        return results

    async def _check_access_control(
        self, transaction: dict, context: dict
    ) -> list[ValidationResult]:
        """Verify access control requirements."""
        results = []

        # Check if calling privileged functions
        data = transaction.get("data", "0x")
        if len(data) >= 10:
            # Common privileged function selectors
            privileged_selectors = {
                "0x715018a6": "renounceOwnership",
                "0xf2fde38b": "transferOwnership",
                "0x3ccfd60b": "withdraw",
                "0x853828b6": "withdrawAll",
            }

            selector = data[:10]
            if selector in privileged_selectors:
                results.append(
                    ValidationResult(
                        passed=False,
                        category="security",
                        message=f"Calling privileged function {privileged_selectors[selector]}",
                        severity="critical",
                        optimization_tip="Ensure you have the required permissions before calling",
                    )
                )

        return results

    def _check_contract_safety(self, transaction: dict) -> list[ValidationResult]:
        """Check if interacting with known vulnerable contracts."""
        results = []

        # This would check against a database of known vulnerable contracts
        # For now, we'll implement a simple check
        to_address = transaction.get("to", "").lower()

        # Example: Check if contract is verified
        if to_address and not to_address.startswith(
            "0x00000"
        ):  # Not a known system contract
            results.append(
                ValidationResult(
                    passed=True,
                    category="security",
                    message="Ensure target contract is verified and audited",
                    severity="info",
                )
            )

        return results


class MEVInspector(SubAgent):
    """Specialized agent for MEV vulnerability analysis."""

    async def analyze(
        self, transaction: dict, objective: dict, context: dict
    ) -> list[ValidationResult]:
        """Analyze MEV vulnerabilities and profit opportunities."""
        results = []

        # Calculate potential MEV profit
        mev_profit = await self._calculate_mev_profit(transaction, objective)

        if mev_profit > 0.1 * 10**18:  # > 0.1 ETH potential profit
            results.append(
                ValidationResult(
                    passed=False,
                    category="security",
                    message=f"Transaction could be targeted by MEV bots (potential profit: {mev_profit / 10**18:.3f} ETH)",
                    severity="critical",
                    optimization_tip="Use private mempool or implement MEV protection strategies",
                )
            )

        # Check for specific MEV attack vectors
        attack_vectors = self._identify_attack_vectors(transaction, objective)
        for vector in attack_vectors:
            results.append(
                ValidationResult(
                    passed=False,
                    category="security",
                    message=f"Vulnerable to {vector['type']} attack",
                    severity="warning",
                    optimization_tip=vector["mitigation"],
                )
            )

        return results

    async def _calculate_mev_profit(self, transaction: dict, objective: dict) -> int:
        """Estimate potential MEV profit from this transaction."""
        # Simplified calculation based on transaction type and value
        obj_type = objective.get("type", "").lower()

        if "swap" in obj_type:
            # Estimate based on slippage tolerance
            expected_output = objective.get("expected_output", 0)
            min_output = objective.get("min_output", 0)

            if expected_output and min_output:
                max_extractable = expected_output - min_output
                return int(max_extractable * 0.5)  # Assume 50% could be extracted

        return 0

    def _identify_attack_vectors(
        self, transaction: dict, objective: dict
    ) -> list[dict]:
        """Identify specific MEV attack vectors."""
        vectors = []

        obj_type = objective.get("type", "").lower()

        if "swap" in obj_type:
            # Sandwich attack vulnerability
            if not objective.get("mev_protection", False):
                vectors.append(
                    {
                        "type": "sandwich",
                        "mitigation": "Use MEV-protected RPC or split into smaller trades",
                    }
                )

        if "liquidation" in obj_type:
            # Liquidation front-running
            vectors.append(
                {
                    "type": "liquidation front-running",
                    "mitigation": "Use flashloan-based atomic liquidation",
                }
            )

        return vectors


class StateValidator(SubAgent):
    """Specialized agent for validating state changes."""

    async def analyze(
        self, transaction: dict, objective: dict, context: dict
    ) -> list[ValidationResult]:
        """Validate that transaction achieves desired state changes."""
        results = []

        # Check balance changes
        balance_validation = await self._validate_balance_changes(
            transaction, objective, context
        )
        results.extend(balance_validation)

        # Check approval states
        approval_validation = self._validate_approvals(transaction, objective)
        results.extend(approval_validation)

        # Check contract state changes
        state_validation = await self._validate_state_changes(
            transaction, objective, context
        )
        results.extend(state_validation)

        return results

    async def _validate_balance_changes(
        self, transaction: dict, objective: dict, context: dict
    ) -> list[ValidationResult]:
        """Validate expected balance changes."""
        results = []

        expected_changes = objective.get("expected_changes", {})

        for token, expected_delta in expected_changes.items():
            # This would simulate the transaction to check actual balance changes
            # For now, we'll add a reminder
            results.append(
                ValidationResult(
                    passed=True,
                    category="correctness",
                    message=f"Expecting {token} balance change of {expected_delta}",
                    severity="info",
                )
            )

        return results

    def _validate_approvals(
        self, transaction: dict, objective: dict
    ) -> list[ValidationResult]:
        """Check if necessary approvals are in place."""
        results = []

        # Check for ERC20 operations that need approval
        data = transaction.get("data", "0x")
        if len(data) >= 10:
            selector = data[:10]

            # transferFrom requires approval
            if selector == "0x23b872dd":
                results.append(
                    ValidationResult(
                        passed=True,
                        category="correctness",
                        message="Ensure token approval is set before transferFrom",
                        severity="info",
                        optimization_tip="Check allowance before attempting transfer",
                    )
                )

        return results

    async def _validate_state_changes(
        self, transaction: dict, objective: dict, context: dict
    ) -> list[ValidationResult]:
        """Validate complex state changes."""
        results = []

        # This would trace the transaction to validate state changes
        # For now, we'll provide general validation
        if "expected_state" in objective:
            results.append(
                ValidationResult(
                    passed=True,
                    category="correctness",
                    message="Transaction should be simulated to verify state changes",
                    severity="info",
                    optimization_tip="Use transaction simulation to confirm expected state",
                )
            )

        return results


class SubAgentCoordinator:
    """Coordinates multiple subagents for comprehensive analysis."""

    def __init__(self):
        """Initialize the subagent coordinator."""
        self.subagents = {
            "gas": GasAnalyzer(),
            "security": SecurityValidator(),
            "mev": MEVInspector(),
            "state": StateValidator(),
        }

    async def analyze_transaction(
        self,
        transaction: dict,
        objective: dict,
        context: dict | None = None,
        agents: list[str] | None = None,
    ) -> dict[str, list[ValidationResult]]:
        """Run specified subagents on the transaction.

        Args:
            transaction: Transaction to analyze
            objective: User objective
            context: Additional context (gas prices, etc.)
            agents: List of agent names to run (None = all)

        Returns:
            Dict mapping agent name to their results
        """
        if context is None:
            context = {}

        if agents is None:
            agents = list(self.subagents.keys())

        # Run subagents concurrently
        tasks = []
        for agent_name in agents:
            if agent_name in self.subagents:
                agent = self.subagents[agent_name]
                task = asyncio.create_task(
                    agent.analyze(transaction, objective, context)
                )
                tasks.append((agent_name, task))

        # Collect results
        results = {}
        for agent_name, task in tasks:
            try:
                agent_results = await task
                results[agent_name] = agent_results
            except Exception as e:
                # Handle errors gracefully
                results[agent_name] = [
                    ValidationResult(
                        passed=False,
                        category="error",
                        message=f"Subagent {agent_name} failed: {str(e)}",
                        severity="warning",
                    )
                ]

        return results
