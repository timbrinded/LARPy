"""Smart agent-driven generator-evaluator workflow for Ethereum transactions."""

import logging
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from src.dexter.config_loader import get_config
from src.dexter.tools import (
    alchemy_simulate_tool,
    calculate_profit,
    encode_erc20_approve,
    encode_sushiswap_swap,
    encode_uniswap_v3_swap,
    estimate_transaction_cost,
    find_arbitrage_opportunities,
    get_all_dex_prices,
    get_curve_price,
    get_eth_balance,
    get_gas_price,
    get_sushiswap_price,
    get_token_balance,
    get_uniswap_v3_price,
    submit_transaction_tool,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Simplified state for agent-driven workflow."""
    
    messages: Annotated[list[BaseMessage], add_messages] = field(default_factory=list)
    pending_transactions: list[dict] = field(default_factory=list)
    evaluation_feedback: dict = field(default_factory=dict)
    ready_to_execute: bool = False
    completed: bool = False


class AgentConfig(TypedDict):
    """Configuration for agent workflow."""
    
    model_name: str | None
    auto_execute: bool


def create_generator_agent():
    """Create the generator agent with all necessary tools."""
    config = get_config()
    model_config = config.models
    
    model = ChatOpenAI(
        model=model_config.model_name,
        max_tokens=model_config.max_tokens,
    )
    
    tools = [
        # Direct query tools
        get_eth_balance,
        get_token_balance,
        get_gas_price,
        estimate_transaction_cost,
        # Price tools
        get_uniswap_v3_price,
        get_sushiswap_price,
        get_all_dex_prices,
        get_curve_price,
        # Arbitrage tools
        find_arbitrage_opportunities,
        calculate_profit,
        # Transaction encoding
        encode_uniswap_v3_swap,
        encode_sushiswap_swap,
        encode_erc20_approve,
    ]
    
    system_prompt = """You are a smart Ethereum transaction generator agent.

Your job is to:
1. Understand what the user wants (balance check, price query, swap, arbitrage, etc.)
2. Use the appropriate tools to either:
   - Answer directly (for queries like balance or price)
   - Generate transaction blocks for execution

For transaction generation:
- Use encoding tools to create proper transaction data
- Format transactions as a list with: to, data, value, gas, description
- Include all necessary transactions (e.g., approval before token swap)
- Pass transactions to the evaluator by including "TRANSACTIONS_FOR_EVALUATION:" followed by the transaction list

For direct queries:
- Just answer the user directly using the tools
- No need to generate transactions

Remember:
- Users are at address 0xYourWalletAddress unless specified
- Be smart about understanding intent - don't rely on keywords
- Generate complete transaction blocks ready for execution
"""
    
    return create_react_agent(model=model, tools=tools, prompt=system_prompt)


def create_evaluator_agent():
    """Create the evaluator agent focused on validation and execution."""
    config = get_config()
    model_config = config.models
    
    model = ChatOpenAI(
        model=model_config.model_name,
        max_tokens=model_config.max_tokens,
    )
    
    tools = [
        alchemy_simulate_tool,
        submit_transaction_tool,
    ]
    
    system_prompt = """You are an Ethereum transaction evaluator agent.

Your job is to:
1. Receive transaction blocks from the generator
2. Simulate them using alchemy_simulate_tool
3. Decide whether to:
   - Execute (if simulation successful and safe)
   - Return feedback for improvement

When evaluating:
- Check simulation results for success
- Verify expected outcomes match intent
- Look for security issues (high slippage, MEV risk)
- Consider gas efficiency

If valid: Execute using submit_transaction_tool and report success
If invalid: Provide specific feedback on what needs improvement

Format feedback as: "EVALUATION_FEEDBACK: <specific issues and suggestions>"
"""
    
    return create_react_agent(model=model, tools=tools, prompt=system_prompt)


# Create agent instances
generator_agent = create_generator_agent()
evaluator_agent = create_evaluator_agent()


async def run_generator(state: AgentState, config: dict) -> dict[str, Any]:
    """Run the generator agent to process user request."""
    logger.info("Running generator agent")
    
    # Run the generator agent
    result = await generator_agent.ainvoke({
        "messages": state.messages
    })
    
    # Extract messages and check for transactions
    new_messages = result.get("messages", [])
    updates = {"messages": new_messages}
    
    # Check if generator created transactions for evaluation
    if new_messages:
        last_message = new_messages[-1]
        if hasattr(last_message, 'content'):
            content = last_message.content
            if "TRANSACTIONS_FOR_EVALUATION:" in content:
                # Extract transactions from message
                import json
                import re
                
                # Find JSON block after the marker
                match = re.search(r'TRANSACTIONS_FOR_EVALUATION:\s*```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                if not match:
                    match = re.search(r'TRANSACTIONS_FOR_EVALUATION:\s*(\[.*?\])', content, re.DOTALL)
                
                if match:
                    try:
                        transactions = json.loads(match.group(1))
                        updates["pending_transactions"] = transactions
                        logger.info(f"Extracted {len(transactions)} transactions for evaluation")
                    except json.JSONDecodeError:
                        logger.error("Failed to parse transactions from generator")
    
    # Check if this was just a query (no transactions needed)
    if not updates.get("pending_transactions") and not state.evaluation_feedback:
        updates["completed"] = True
    
    return updates


async def run_evaluator(state: AgentState, config: dict) -> dict[str, Any]:
    """Run the evaluator agent on pending transactions."""
    logger.info("Running evaluator agent")
    
    if not state.pending_transactions:
        return {"completed": True}
    
    # Prepare message for evaluator
    tx_message = f"Please evaluate these transactions:\n```json\n{state.pending_transactions}\n```"
    
    if state.evaluation_feedback:
        tx_message += f"\n\nPrevious feedback was addressed. The generator made these improvements:\n{state.evaluation_feedback.get('improvements', 'See updated transactions above')}"
    
    # Run evaluator
    result = await evaluator_agent.ainvoke({
        "messages": [HumanMessage(content=tx_message)]
    })
    
    # Process evaluator response
    new_messages = result.get("messages", [])
    updates = {"messages": new_messages}
    
    if new_messages:
        last_message = new_messages[-1]
        if hasattr(last_message, 'content'):
            content = last_message.content
            
            # Check for feedback (needs improvement)
            if "EVALUATION_FEEDBACK:" in content:
                import re
                match = re.search(r'EVALUATION_FEEDBACK:\s*(.*?)(?:\n\n|$)', content, re.DOTALL)
                if match:
                    feedback = match.group(1).strip()
                    updates["evaluation_feedback"] = {"feedback": feedback}
                    updates["pending_transactions"] = []  # Clear for regeneration
                    # Add feedback to messages for generator
                    updates["messages"].append(HumanMessage(
                        content=f"The evaluator provided this feedback: {feedback}\n\nPlease improve the transactions based on this feedback."
                    ))
            else:
                # Assume execution completed
                updates["completed"] = True
                updates["ready_to_execute"] = False
                updates["pending_transactions"] = []
    
    return updates


def should_continue(state: AgentState) -> str:
    """Determine next step in the workflow."""
    if state.completed:
        return END
    
    # If we have pending transactions, evaluate them
    if state.pending_transactions:
        return "evaluator"
    
    # If we have evaluation feedback, go back to generator
    if state.evaluation_feedback and not state.completed:
        return "generator"
    
    # Default to generator for new requests
    return "generator"


def create_agent_graph():
    """Create the simplified agent-driven graph."""
    workflow = StateGraph(AgentState, config_schema=AgentConfig)
    
    # Add nodes
    workflow.add_node("generator", run_generator)
    workflow.add_node("evaluator", run_evaluator)
    
    # Set entry point
    workflow.set_entry_point("generator")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "generator",
        should_continue,
        {
            "evaluator": "evaluator",
            "generator": "generator",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "evaluator",
        should_continue,
        {
            "generator": "generator",
            END: END
        }
    )
    
    return workflow.compile()


# Export the graph
graph = create_agent_graph()