"""Transaction optimizer for improving Ethereum transactions based on evaluation feedback."""



class TransactionOptimizer:
    """Optimizes Ethereum transactions based on evaluation feedback."""

    def __init__(self) -> None:
        """Initialize the transaction optimizer with optimization strategies."""
        # Lazy import to avoid circular dependency
        from src.dexter.config_loader import get_config_loader

        self.loader = get_config_loader()
        self.optimization_strategies = {
            "gas": self._optimize_gas,
            "security": self._optimize_security,
            "efficiency": self._optimize_efficiency,
            "correctness": self._optimize_correctness,
        }

    def optimize_transaction(
        self, transaction: dict, evaluation_results: list[dict], objective: dict
    ) -> tuple[dict, list[str]]:
        """Optimize a transaction based on evaluation feedback.

        Args:
            transaction: Original transaction
            evaluation_results: Results from evaluator
            objective: User objective

        Returns:
            Tuple of (optimized_transaction, applied_optimizations)
        """
        optimized_tx = transaction.copy()
        applied = []

        # Group results by category
        issues_by_category: dict[str, list[dict]] = {}
        for result in evaluation_results:
            if not result["passed"]:
                category = result["category"]
                if category not in issues_by_category:
                    issues_by_category[category] = []
                issues_by_category[category].append(result)

        # Apply optimizations by category
        for category, issues in issues_by_category.items():
            if category in self.optimization_strategies:
                strategy = self.optimization_strategies[category]
                optimized_tx, optimizations = strategy(optimized_tx, issues, objective)
                applied.extend(optimizations)

        return optimized_tx, applied

    def _optimize_gas(
        self, tx: dict, issues: list[dict], objective: dict
    ) -> tuple[dict, list[str]]:
        """Optimize gas usage."""
        optimizations = []

        for issue in issues:
            if "exceeds threshold" in issue["message"]:
                # Try to reduce gas by optimizing call data
                if "data" in tx and len(tx["data"]) > 10:
                    # Check if we can use a more efficient encoding
                    optimized_data = self._optimize_calldata(tx["data"], objective)
                    if optimized_data != tx["data"]:
                        tx["data"] = optimized_data
                        optimizations.append(
                            "Optimized calldata encoding for gas efficiency"
                        )

                # Adjust gas limit to reasonable value
                if "gas" in tx:
                    original_gas = tx["gas"]
                    # Use 110% of estimated gas instead of excessive padding
                    tx["gas"] = int(original_gas * 0.75)
                    optimizations.append(
                        f"Reduced gas limit from {original_gas} to {tx['gas']}"
                    )

        return tx, optimizations

    def _optimize_security(
        self, tx: dict, issues: list[dict], objective: dict
    ) -> tuple[dict, list[str]]:
        """Optimize security aspects."""
        optimizations = []

        for issue in issues:
            if "Slippage" in issue["message"]:
                # Implement tighter slippage protection
                slippage_optimization = self._add_slippage_protection(tx, objective)
                if slippage_optimization:
                    tx = slippage_optimization
                    optimizations.append("Added improved slippage protection")

            elif "MEV vulnerable" in issue["message"]:
                # Add MEV protection
                mev_protection = self._add_mev_protection(tx, objective)
                if mev_protection:
                    tx.update(mev_protection)
                    optimizations.append("Added MEV protection measures")

            elif "value exceeds confirmation threshold" in issue["message"]:
                # Suggest transaction splitting
                optimizations.append(
                    "Consider splitting into multiple smaller transactions"
                )

        return tx, optimizations

    def _optimize_efficiency(
        self, tx: dict, issues: list[dict], objective: dict
    ) -> tuple[dict, list[str]]:
        """Optimize transaction efficiency."""
        optimizations = []

        for issue in issues:
            if "hop path when direct path is available" in issue["message"]:
                # Find and use direct path
                direct_path_data = self._find_direct_path(tx, objective)
                if direct_path_data:
                    tx["data"] = direct_path_data
                    optimizations.append("Switched to direct trading path")

            elif "exceeds maximum" in issue["message"] and "hops" in issue["message"]:
                # Reduce hop count
                reduced_hop_data = self._reduce_hop_count(tx, objective)
                if reduced_hop_data:
                    tx["data"] = reduced_hop_data
                    optimizations.append("Reduced swap path complexity")

        return tx, optimizations

    def _optimize_correctness(
        self, tx: dict, issues: list[dict], objective: dict
    ) -> tuple[dict, list[str]]:
        """Fix correctness issues."""
        optimizations = []

        for issue in issues:
            if "target doesn't match" in issue["message"]:
                # Fix target address
                if "target_address" in objective:
                    tx["to"] = objective["target_address"]
                    optimizations.append(
                        f"Corrected target address to {objective['target_address']}"
                    )

            elif "simulation failed" in issue["message"]:
                # Try to fix common simulation failures
                fixes = self._fix_simulation_issues(tx, issue, objective)
                tx.update(fixes["transaction"])
                optimizations.extend(fixes["optimizations"])

        return tx, optimizations

    def _optimize_calldata(self, data: str, objective: dict) -> str:
        """Optimize calldata for gas efficiency."""
        # This is a simplified example - real optimization would be more complex
        # Check if we can use packed encoding for certain functions
        if len(data) > 200 and "swap" in objective.get("type", "").lower():
            # Could implement more efficient encoding here
            return data
        return data

    def _add_slippage_protection(self, tx: dict, objective: dict) -> dict | None:
        """Add or improve slippage protection."""
        # This would modify the transaction data to include better slippage parameters
        # Implementation depends on the specific DEX protocol
        return None

    def _add_mev_protection(self, tx: dict, objective: dict) -> dict | None:
        """Add MEV protection to transaction."""
        # Could add flashbots bundle information or other MEV protection
        return {
            "flashbots_bundle": True,
            "max_priority_fee_per_gas": str(int(5e9)),  # 5 gwei priority fee
        }

    def _find_direct_path(self, tx: dict, objective: dict) -> str | None:
        """Find direct trading path for swap."""
        # This would analyze available DEX pools and find direct routes
        # Placeholder implementation
        return None

    def _reduce_hop_count(self, tx: dict, objective: dict) -> str | None:
        """Reduce the number of hops in a swap path."""
        # Would implement logic to find more efficient paths
        return None

    def _fix_simulation_issues(self, tx: dict, issue: dict, objective: dict) -> dict:
        """Attempt to fix common simulation failures."""
        fixes: dict[str, dict | list] = {"transaction": {}, "optimizations": []}

        error_msg = issue.get("message", "").lower()

        if "insufficient balance" in error_msg:
            # Reduce transaction amount
            if "value" in tx and int(tx["value"]) > 0:
                fixes["transaction"]["value"] = str(int(tx["value"]) // 2)
                if isinstance(fixes["optimizations"], list):
                    fixes["optimizations"].append(
                        "Reduced transaction value to avoid insufficient balance"
                    )

        elif "gas required exceeds allowance" in error_msg:
            # Increase gas limit
            if "gas" in tx:
                fixes["transaction"]["gas"] = int(tx["gas"] * 1.5)
                if isinstance(fixes["optimizations"], list):
                    fixes["optimizations"].append(
                        "Increased gas limit to ensure execution"
                    )

        return fixes

    def generate_optimization_report(
        self,
        original_tx: dict,
        optimized_tx: dict,
        applied_optimizations: list[str],
        evaluation_before: dict,
        evaluation_after: dict | None = None,
    ) -> dict:
        """Generate a detailed optimization report."""
        report = {
            "original_transaction": original_tx,
            "optimized_transaction": optimized_tx,
            "applied_optimizations": applied_optimizations,
            "improvements": [],
        }

        # Calculate improvements
        if "gas" in original_tx and "gas" in optimized_tx:
            gas_saved = original_tx["gas"] - optimized_tx["gas"]
            if gas_saved > 0:
                if isinstance(report["improvements"], list):
                    report["improvements"].append(f"Reduced gas by {gas_saved} units")

        # Compare evaluation results if available
        if evaluation_after:
            original_issues = len(
                [r for r in evaluation_before.get("results", []) if not r["passed"]]
            )
            optimized_issues = len(
                [r for r in evaluation_after.get("results", []) if not r["passed"]]
            )

            if optimized_issues < original_issues:
                if isinstance(report["improvements"], list):
                    report["improvements"].append(
                        f"Resolved {original_issues - optimized_issues} validation issues"
                    )

        return report

    def suggest_alternative_approaches(
        self, objective: dict, issues: list[dict]
    ) -> list[dict]:
        """Suggest alternative approaches when optimization isn't sufficient."""
        suggestions = []

        # Analyze patterns in issues
        has_gas_issues = any(i["category"] == "gas" for i in issues)
        has_security_issues = any(i["category"] == "security" for i in issues)
        has_efficiency_issues = any(i["category"] == "efficiency" for i in issues)

        if has_gas_issues and has_efficiency_issues:
            suggestions.append(
                {
                    "approach": "Transaction Batching",
                    "description": "Combine multiple operations into a single transaction using a multicall contract",
                    "benefits": [
                        "Reduced total gas cost",
                        "Atomic execution",
                        "Fewer approvals needed",
                    ],
                }
            )

        if has_security_issues and "swap" in objective.get("type", "").lower():
            suggestions.append(
                {
                    "approach": "Use Aggregator",
                    "description": "Use a DEX aggregator like 1inch that handles routing and protection",
                    "benefits": [
                        "Built-in MEV protection",
                        "Optimal routing",
                        "Professional slippage handling",
                    ],
                }
            )

        if has_efficiency_issues:
            suggestions.append(
                {
                    "approach": "Split Orders",
                    "description": "Split large orders into smaller chunks executed over time",
                    "benefits": [
                        "Reduced price impact",
                        "Better average execution price",
                        "Lower slippage",
                    ],
                }
            )

        return suggestions
