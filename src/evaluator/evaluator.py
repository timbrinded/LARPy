"""Transaction evaluator for validating Ethereum transactions against objectives."""

from web3 import Web3

from .validation_rules import ValidationResult, ValidationRuleEngine


class TransactionEvaluator:
    """Evaluates Ethereum transactions against user objectives and validation rules."""

    def __init__(self) -> None:
        """Initialize the transaction evaluator with validation rule engine."""
        self.rule_engine = ValidationRuleEngine()
        self.w3 = Web3()

    def evaluate_transaction(
        self,
        transaction: dict,
        objective: dict,
        simulation_result: dict | None = None,
    ) -> tuple[bool, list[ValidationResult]]:
        """Evaluate a single transaction against objectives and rules.

        Args:
            transaction: Transaction data (to, value, data, gas, etc.)
            objective: User objective describing desired state change
            simulation_result: Optional simulation result from Alchemy

        Returns:
            Tuple of (is_valid, validation_results)
        """
        results = []

        # Extract transaction details
        tx_type = self._determine_transaction_type(transaction, objective)

        # 1. Validate gas usage
        if "gas" in transaction:
            gas_result = self.rule_engine.validate_gas(transaction, tx_type)
            results.append(gas_result)

        # 2. Validate transaction value
        value = int(transaction.get("value", 0))
        if value > 0:
            value_result = self.rule_engine.validate_value(value)
            results.append(value_result)

        # 3. Validate against objective
        objective_results = self._validate_objective_alignment(transaction, objective)
        results.extend(objective_results)

        # 4. Validate simulation results if available
        if simulation_result:
            sim_results = self._validate_simulation(simulation_result, objective)
            results.extend(sim_results)

        # 5. Check for security issues
        security_results = self._validate_security(transaction, objective)
        results.extend(security_results)

        # Determine overall validity
        critical_failures = [
            r for r in results if not r.passed and r.severity == "critical"
        ]
        is_valid = len(critical_failures) == 0

        return is_valid, results

    def evaluate_transaction_batch(
        self,
        transactions: list[dict],
        objective: dict,
        simulation_results: list[dict] | None = None,
    ) -> dict:
        """Evaluate a batch of transactions.

        Returns:
            Dict with overall assessment and individual transaction results
        """
        if simulation_results is None:
            simulation_results = [{} for _ in range(len(transactions))]

        batch_results = []
        all_valid = True

        for i, tx in enumerate(transactions):
            is_valid, results = self.evaluate_transaction(
                tx, objective, simulation_results[i]
            )

            batch_results.append(
                {"transaction_index": i, "valid": is_valid, "results": results}
            )

            if not is_valid:
                all_valid = False

        # Generate optimization tips
        tips = self._generate_optimization_tips(batch_results)

        return {
            "all_valid": all_valid,
            "transaction_results": batch_results,
            "optimization_tips": tips,
            "summary": self._generate_summary(batch_results),
        }

    def _determine_transaction_type(self, transaction: dict, objective: dict) -> str:
        """Determine the type of transaction for validation rules."""
        data = transaction.get("data", "0x")

        if data == "0x" or len(data) <= 10:
            return "eth_transfer"

        # Check for common function selectors
        selector = data[:10] if len(data) >= 10 else data

        # ERC20 transfer: 0xa9059cbb
        if selector == "0xa9059cbb":
            return "erc20_transfer"

        # Check objective for swap indicators
        obj_type = objective.get("type", "").lower()
        if "swap" in obj_type:
            if "multi" in obj_type or "triangular" in obj_type:
                return "multi_hop_swap"
            elif "complex" in obj_type:
                return "complex_swap"
            else:
                return "simple_swap"

        return "complex_swap"  # Default for unknown

    def _validate_objective_alignment(
        self, transaction: dict, objective: dict
    ) -> list[ValidationResult]:
        """Validate that transaction aligns with stated objective."""
        results = []

        # Check if transaction target matches objective
        if "target_address" in objective:
            if transaction.get("to", "").lower() != objective["target_address"].lower():
                results.append(
                    ValidationResult(
                        passed=False,
                        category="correctness",
                        message="Transaction target doesn't match objective target",
                        severity="critical",
                        optimization_tip="Ensure transaction is sent to the correct contract",
                    )
                )

        # Validate token amounts if specified
        if "expected_output" in objective and "min_output" in objective:
            slippage_result = self.rule_engine.validate_slippage(
                objective["expected_output"], objective["min_output"]
            )
            results.append(slippage_result)

        return results

    def _validate_simulation(
        self, simulation: dict, objective: dict
    ) -> list[ValidationResult]:
        """Validate simulation results."""
        results = []

        if not simulation.get("success", False):
            error_msg = simulation.get("error", "Unknown error")
            results.append(
                ValidationResult(
                    passed=False,
                    category="correctness",
                    message=f"Transaction simulation failed: {error_msg}",
                    severity="critical",
                    optimization_tip="Review transaction parameters and ensure sufficient balances",
                )
            )
            return results

        # Check asset changes align with objective
        if "asset_changes" in simulation:
            changes = simulation["asset_changes"]
            expected_changes = objective.get("expected_changes", {})

            # Validate each expected change
            for asset, expected_delta in expected_changes.items():
                actual_delta = changes.get(asset, 0)
                if (
                    abs(actual_delta - expected_delta) / abs(expected_delta) > 0.02
                ):  # 2% tolerance
                    results.append(
                        ValidationResult(
                            passed=False,
                            category="correctness",
                            message=f"Asset {asset} change {actual_delta} differs from expected {expected_delta}",
                            severity="warning",
                            optimization_tip="Adjust transaction parameters to achieve desired asset changes",
                        )
                    )

        return results

    def _validate_security(
        self, transaction: dict, objective: dict
    ) -> list[ValidationResult]:
        """Perform security validations."""
        results = []

        # Check for MEV vulnerability
        if self._is_mev_vulnerable(transaction, objective):
            results.append(
                ValidationResult(
                    passed=False,
                    category="security",
                    message="Transaction is vulnerable to MEV attacks",
                    severity="warning",
                    optimization_tip="Consider using Flashbots or implementing commit-reveal pattern",
                )
            )

        # Validate protocol if specified
        if "protocol" in objective:
            protocol_result = self.rule_engine.validate_protocol(objective["protocol"])
            results.append(protocol_result)

        return results

    def _is_mev_vulnerable(self, transaction: dict, objective: dict) -> bool:
        """Check if transaction is vulnerable to MEV."""
        # Simple heuristic: large value swaps without protection
        value = int(transaction.get("value", 0))
        obj_type = objective.get("type", "").lower()

        if "swap" in obj_type and value > 10**18:  # > 1 ETH
            # Check if using private mempool or protection
            if not objective.get("mev_protection", False):
                return True

        return False

    def _generate_optimization_tips(self, batch_results: list[dict]) -> list[str]:
        """Generate actionable optimization tips from results."""
        tips = []
        tip_set = set()  # Avoid duplicates

        for tx_result in batch_results:
            for result in tx_result["results"]:
                if not result.passed and result.optimization_tip:
                    if result.optimization_tip not in tip_set:
                        tips.append(result.optimization_tip)
                        tip_set.add(result.optimization_tip)

        # Add batch-level tips
        failed_txs = [r for r in batch_results if not r["valid"]]
        if len(failed_txs) > 1:
            tips.append("Consider breaking this into smaller, simpler transactions")

        return tips

    def _generate_summary(self, batch_results: list[dict]) -> str:
        """Generate a summary of the evaluation."""
        total = len(batch_results)
        valid = sum(1 for r in batch_results if r["valid"])

        if valid == total:
            return f"All {total} transactions passed validation"
        elif valid == 0:
            return f"All {total} transactions failed validation"
        else:
            return f"{valid} of {total} transactions passed validation"
