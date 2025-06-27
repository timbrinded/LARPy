"""Integrated generator-evaluator workflow for Ethereum transactions."""

import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dexter.tools import arbitrage, dex_prices, swap_encoder
from src.evaluator import TransactionEvaluator, TransactionOptimizer
from src.evaluator.subagents import SubAgentCoordinator

logger = logging.getLogger(__name__)


@dataclass
class IntegratedState:
    """State for integrated generator-evaluator workflow."""
    
    messages: Annotated[list[BaseMessage], add_messages] = field(default_factory=list)
    current_objective: dict[str, Any] = field(default_factory=dict)
    generated_transactions: list[dict] = field(default_factory=list)
    evaluation_results: list[dict] = field(default_factory=list)
    optimization_history: list[dict] = field(default_factory=list)
    final_transactions: list[dict] = field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 3
    awaiting_user_input: bool = False


class IntegratedConfig(TypedDict):
    """Configuration for integrated workflow."""
    
    model_name: str | None
    auto_evaluate: bool
    max_optimization_rounds: int
    enable_subagents: bool


async def analyze_request(state: IntegratedState, config: dict) -> dict[str, Any]:
    """Analyze user request and determine action."""
    logger.info("Analyzing user request")
    
    messages = state.messages
    if not messages:
        return {
            "messages": [AIMessage(content="Hello! I can help you generate and evaluate Ethereum transactions. What would you like to do?")],
            "awaiting_user_input": True
        }
    
    # Get latest user message
    user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break
    
    if not user_message:
        return {
            "messages": [AIMessage(content="Please provide a request.")],
            "awaiting_user_input": True
        }
    
    lower_msg = user_message.lower()
    
    # Check for transaction generation requests
    if any(word in lower_msg for word in ["swap", "arbitrage", "transfer", "send"]):
        objective = {"raw_message": user_message}
        
        if "swap" in lower_msg:
            objective["type"] = "swap"
            tokens = []
            amounts = []
            
            # Extract tokens
            for token in ["eth", "usdc", "usdt", "dai", "weth"]:
                if token in lower_msg:
                    tokens.append(token.upper())
            
            # Extract amounts
            import re
            numbers = re.findall(r'\d+\.?\d*', lower_msg)
            amounts.extend(numbers)
            
            if len(tokens) >= 2:
                objective["token_in"] = tokens[0]
                objective["token_out"] = tokens[1]
            if amounts:
                objective["amount"] = amounts[0]
        
        elif "arbitrage" in lower_msg:
            objective["type"] = "arbitrage"
        
        elif "transfer" in lower_msg or "send" in lower_msg:
            objective["type"] = "transfer"
        
        return {
            "current_objective": objective,
            "messages": [AIMessage(content=f"I'll help you with a {objective.get('type', 'transaction')} transaction. Let me generate the details...")],
            "awaiting_user_input": False
        }
    
    # Check for optimization approval
    elif any(word in lower_msg for word in ["yes", "apply", "optimize", "improve"]) and state.evaluation_results:
        last_eval = state.evaluation_results[-1]
        if not last_eval.get("all_valid", True):
            return {
                "messages": [AIMessage(content="Applying optimizations based on evaluation feedback...")],
                "awaiting_user_input": False
            }
    
    # Default response
    return {
        "messages": [AIMessage(content="I can help you generate and evaluate Ethereum transactions. Try asking me to swap tokens, find arbitrage opportunities, or transfer funds.")],
        "awaiting_user_input": True
    }


async def generate_transactions(state: IntegratedState, config: dict) -> dict[str, Any]:
    """Generate transactions based on objective."""
    logger.info("Generating transactions")
    
    objective = state.current_objective
    if not objective:
        return {
            "messages": [AIMessage(content="No objective found. Please specify what you'd like to do.")],
            "awaiting_user_input": True
        }
    
    transactions = []
    
    try:
        if objective.get("type") == "swap":
            token_in = objective.get("token_in", "ETH")
            token_out = objective.get("token_out", "USDC")
            amount = objective.get("amount", "1")
            
            # Get prices
            prices = await dex_prices.get_all_dex_prices.ainvoke({
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": amount
            })
            
            # Generate swap transaction
            swap_data = await swap_encoder.encode_uniswap_v3_swap.ainvoke({
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": str(int(float(amount) * 1e18)) if token_in == "ETH" else amount,
                "recipient": "0xYourWalletAddress",
                "fee_tier": 3000,
                "slippage_percent": 0.5,
                "deadline_minutes": 20
            })
            
            if swap_data["success"]:
                transactions.append({
                    "to": swap_data["to"],
                    "data": swap_data["data"],
                    "value": swap_data["value"],
                    "gas": 250000,
                    "type": "swap",
                    "description": f"Swap {amount} {token_in} for {token_out}",
                    "dex": "Uniswap V3"
                })
        
        elif objective.get("type") == "arbitrage":
            # Find arbitrage
            prices = await dex_prices.get_all_dex_prices.ainvoke({
                "token_in": "ETH",
                "token_out": "USDC", 
                "amount_in": "1"
            })
            
            opportunities = await arbitrage.find_arbitrage_opportunities.ainvoke({
                "price_data": prices,
                "min_profit_percentage": 0.5
            })
            
            if opportunities.get("opportunities"):
                transactions.append({
                    "type": "arbitrage",
                    "description": "Multi-DEX arbitrage",
                    "estimated_profit": opportunities.get("max_profit", "Unknown"),
                    "gas": 400000,
                    "to": "0xArbitrageRouter",
                    "data": "0x",
                    "value": "0"
                })
    
    except Exception as e:
        logger.error(f"Error generating transactions: {e}")
        return {
            "messages": [AIMessage(content=f"Error generating transactions: {str(e)}")],
            "awaiting_user_input": True
        }
    
    if transactions:
        message = f"Generated {len(transactions)} transaction(s):\n\n"
        for i, tx in enumerate(transactions):
            message += f"Transaction {i+1}: {tx['description']}\n"
            message += f"  DEX: {tx.get('dex', 'Multi-DEX')}\n"
            message += f"  Gas: {tx['gas']}\n\n"
        
        message += "Now evaluating the transactions..."
        
        return {
            "generated_transactions": transactions,
            "messages": [AIMessage(content=message)],
            "awaiting_user_input": False
        }
    else:
        return {
            "messages": [AIMessage(content="No viable transactions found. Please try a different request.")],
            "awaiting_user_input": True
        }


async def evaluate_transactions(state: IntegratedState, config: dict) -> dict[str, Any]:
    """Evaluate generated transactions."""
    logger.info("Evaluating transactions")
    
    evaluator = TransactionEvaluator()
    transactions = state.generated_transactions
    objective = state.current_objective
    
    if not transactions:
        return {
            "messages": [AIMessage(content="No transactions to evaluate.")],
            "awaiting_user_input": True
        }
    
    # Simulate transactions
    simulation_results = []
    for tx in transactions:
        try:
            from src.dexter.tools import transactions as tx_tools
            sim = await tx_tools.alchemy_simulate_asset_changes.ainvoke({
                "to_address": tx.get("to", ""),
                "value": tx.get("value", "0"),
                "data": tx.get("data", "0x"),
                "from_address": "0xYourWalletAddress"
            })
            simulation_results.append(sim)
        except Exception as e:
            simulation_results.append({"success": False, "error": str(e)})
    
    # Evaluate
    evaluation = evaluator.evaluate_transaction_batch(
        transactions, objective, simulation_results
    )
    
    # Run subagents if enabled
    if config.get("configurable", {}).get("enable_subagents", True):
        coordinator = SubAgentCoordinator()
        context = {
            "current_base_fee": 30e9,
            "simulation_results": simulation_results
        }
        
        for i, tx in enumerate(transactions):
            subagent_analysis = await coordinator.analyze_transaction(
                tx, objective, context
            )
            # Merge results
            for agent_name, results in subagent_analysis.items():
                evaluation["transaction_results"][i]["results"].extend(results)
    
    # Prepare response
    message = "Evaluation Results:\n\n"
    
    if evaluation["all_valid"]:
        message += "✅ All transactions passed validation!\n\n"
        for i, tx in enumerate(transactions):
            message += f"Transaction {i+1}: APPROVED ✓\n"
        
        message += "\nTransactions are ready for execution."
        
        return {
            "evaluation_results": state.evaluation_results + [evaluation],
            "final_transactions": transactions,
            "messages": [AIMessage(content=message)],
            "awaiting_user_input": True
        }
    else:
        message += f"⚠️ {evaluation['summary']}\n\n"
        
        issues_found = []
        for i, tx_result in enumerate(evaluation["transaction_results"]):
            if not tx_result["valid"]:
                message += f"Transaction {i+1}: NEEDS OPTIMIZATION\n"
                for result in tx_result["results"]:
                    if not result["passed"]:
                        message += f"  - {result['message']}\n"
                        if result.get("optimization_tip"):
                            message += f"    💡 {result['optimization_tip']}\n"
                        issues_found.append(result)
        
        message += "\nWould you like me to apply optimizations? (yes/no)"
        
        return {
            "evaluation_results": state.evaluation_results + [evaluation],
            "messages": [AIMessage(content=message)],
            "awaiting_user_input": True
        }


async def optimize_transactions(state: IntegratedState, config: dict) -> dict[str, Any]:
    """Optimize transactions based on evaluation."""
    logger.info("Optimizing transactions")
    
    optimizer = TransactionOptimizer()
    transactions = state.generated_transactions
    
    if not state.evaluation_results:
        return {
            "messages": [AIMessage(content="No evaluation results to optimize.")],
            "awaiting_user_input": True
        }
    
    evaluation = state.evaluation_results[-1]
    objective = state.current_objective
    
    # Check iteration limit
    if state.iteration_count >= state.max_iterations:
        return {
            "messages": [AIMessage(content=f"Reached maximum optimization iterations ({state.max_iterations}). Using best available transactions.")],
            "final_transactions": transactions,
            "awaiting_user_input": True
        }
    
    # Optimize each transaction
    optimized_transactions = []
    all_optimizations = []
    
    for i, tx in enumerate(transactions):
        tx_evaluation = evaluation["transaction_results"][i]
        if not tx_evaluation["valid"]:
            optimized_tx, optimizations = optimizer.optimize_transaction(
                tx, tx_evaluation["results"], objective
            )
            optimized_transactions.append(optimized_tx)
            all_optimizations.extend(optimizations)
        else:
            optimized_transactions.append(tx)
    
    message = f"Applied {len(all_optimizations)} optimizations:\n"
    for opt in all_optimizations[:5]:
        message += f"  ✓ {opt}\n"
    if len(all_optimizations) > 5:
        message += f"  ... and {len(all_optimizations) - 5} more\n"
    
    message += "\nRe-evaluating optimized transactions..."
    
    return {
        "generated_transactions": optimized_transactions,
        "optimization_history": state.optimization_history + [{
            "round": state.iteration_count + 1,
            "optimizations": all_optimizations
        }],
        "iteration_count": state.iteration_count + 1,
        "messages": [AIMessage(content=message)],
        "awaiting_user_input": False
    }


def should_continue(state: IntegratedState) -> str:
    """Determine next step in the workflow."""
    # If awaiting user input, end the graph
    if state.awaiting_user_input:
        return END
    
    # If we have an objective but no transactions, generate them
    if state.current_objective and not state.generated_transactions:
        return "generate"
    
    # If we have transactions but no evaluation, evaluate them
    if state.generated_transactions and not state.evaluation_results:
        return "evaluate"
    
    # If we have evaluation results
    if state.evaluation_results:
        last_eval = state.evaluation_results[-1]
        
        # If all valid, we're done
        if last_eval.get("all_valid", False):
            return END
        
        # If not valid and we haven't hit iteration limit, check for user approval
        if state.iteration_count < state.max_iterations:
            # Check if user approved optimization
            last_message = state.messages[-1] if state.messages else None
            if last_message and isinstance(last_message, HumanMessage):
                if any(word in last_message.content.lower() for word in ["yes", "apply", "optimize"]):
                    return "optimize"
            
            # If we just evaluated and found issues, wait for user
            if len(state.evaluation_results) > len(state.optimization_history):
                return END
        
        # If we just optimized, re-evaluate
        if len(state.optimization_history) > 0 and state.generated_transactions:
            # Check if we need to re-evaluate after optimization
            if len(state.evaluation_results) <= len(state.optimization_history):
                return "evaluate"
    
    return END


def create_integrated_graph():
    """Create the integrated generator-evaluator graph."""
    workflow = StateGraph(IntegratedState, config_schema=IntegratedConfig)
    
    # Add nodes
    workflow.add_node("analyze", analyze_request)
    workflow.add_node("generate", generate_transactions)
    workflow.add_node("evaluate", evaluate_transactions)
    workflow.add_node("optimize", optimize_transactions)
    
    # Set entry point
    workflow.set_entry_point("analyze")
    
    # Add conditional edges from analyze
    workflow.add_conditional_edges(
        "analyze",
        should_continue,
        {
            "generate": "generate",
            "evaluate": "evaluate",
            "optimize": "optimize",
            END: END
        }
    )
    
    # Add conditional edges from other nodes
    workflow.add_conditional_edges(
        "generate",
        should_continue,
        {
            "evaluate": "evaluate",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "optimize": "optimize",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "optimize",
        should_continue,
        {
            "evaluate": "evaluate",
            END: END
        }
    )
    
    return workflow.compile()


# Export the integrated graph
graph = create_integrated_graph()