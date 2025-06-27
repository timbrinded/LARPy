"""Smart agent-driven generator-evaluator workflow for Ethereum transactions."""

import logging
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
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
- Create a JSON list with: to, data, value, gas, description
- Include all necessary transactions (e.g., approval before token swap)
- Format your response with TWO sections separated by a special marker:
  
  [USER_MESSAGE]
  I'll prepare that swap for you and check if it's safe to execute...
  
  [INTERNAL_DATA]
  {"transactions": [{"to": "0x...", "data": "0x...", "value": "...", "gas": 250000, "description": "..."}]}

For direct queries:
- Just answer the user directly using the tools
- No need for the [INTERNAL_DATA] section

IMPORTANT: 
- The [USER_MESSAGE] section is what the user sees
- The [INTERNAL_DATA] section contains transaction JSON (hidden from user)
- Keep user messages brief and friendly

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
3. Communicate results to the user

When evaluating:
- Simulate each transaction carefully
- Check for success and expected outcomes
- Look for security issues (high slippage, MEV risk)
- Consider gas costs

Communication rules:
- For successful simulations: Execute and tell user "✅ Transaction executed successfully! [details]"
- For failed simulations: Explain the issue and say "Let me try a different approach..."
- Always be user-friendly - no raw transaction data
- You are the ONLY agent that talks to the user about transaction results

Internal feedback format (not shown to user): "EVALUATION_FEEDBACK: <specific issues>"
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
    
    # Extract messages
    new_messages = result.get("messages", [])
    updates = {"messages": []}
    
    # Process the final AI message to extract user message and internal data
    for msg in new_messages:
        if isinstance(msg, AIMessage) and msg.content:
            content = msg.content
            
            # Check if message contains our special format
            if "[USER_MESSAGE]" in content and "[INTERNAL_DATA]" in content:
                import json
                import re
                
                # Extract user message
                user_match = re.search(r'\[USER_MESSAGE\]\s*(.*?)\s*\[INTERNAL_DATA\]', content, re.DOTALL)
                if user_match:
                    user_message = user_match.group(1).strip()
                    updates["messages"].append(AIMessage(content=user_message))
                
                # Extract internal data
                data_match = re.search(r'\[INTERNAL_DATA\]\s*({.*?})\s*$', content, re.DOTALL)
                if data_match:
                    try:
                        internal_data = json.loads(data_match.group(1))
                        if "transactions" in internal_data:
                            updates["pending_transactions"] = internal_data["transactions"]
                            logger.info(f"Extracted {len(internal_data['transactions'])} transactions for evaluation")
                        else:
                            logger.warning("Internal data found but no 'transactions' key")
                    except json.JSONDecodeError:
                        logger.error("Failed to parse internal data from generator")
            else:
                # Regular message without internal data
                updates["messages"].append(msg)
        else:
            # Include non-AI messages as-is
            updates["messages"].append(msg)
    
    # Don't mark as completed - let evaluator decide
    return updates


async def run_evaluator(state: AgentState, config: dict) -> dict[str, Any]:
    """Run the evaluator agent on pending transactions."""
    logger.info("Running evaluator agent")
    
    if not state.pending_transactions:
        # No transactions to evaluate - this was a direct query
        # Just mark as completed and let the generator's response stand
        return {"completed": True, "messages": []}
    
    # Prepare message for evaluator with transaction details
    import json
    tx_details = json.dumps(state.pending_transactions, indent=2)
    
    tx_message = f"Evaluate and process these transactions:\n```json\n{tx_details}\n```"
    
    if state.evaluation_feedback:
        tx_message += f"\n\nThe generator addressed previous feedback. Please re-evaluate."
    
    # Run evaluator
    result = await evaluator_agent.ainvoke({
        "messages": [HumanMessage(content=tx_message)]
    })
    
    # Process evaluator response
    new_messages = result.get("messages", [])
    updates = {"messages": []}
    
    # Look for feedback in tool messages (internal)
    feedback_found = False
    for msg in new_messages:
        if hasattr(msg, 'content'):
            # Check for internal feedback
            if "EVALUATION_FEEDBACK:" in msg.content:
                import re
                match = re.search(r'EVALUATION_FEEDBACK:\s*(.*?)(?:\n|$)', msg.content, re.DOTALL)
                if match:
                    feedback = match.group(1).strip()
                    updates["evaluation_feedback"] = {"feedback": feedback}
                    updates["pending_transactions"] = []  # Clear for regeneration
                    feedback_found = True
                    # Add internal message for generator
                    updates["messages"].append(HumanMessage(
                        content=f"Please improve the transaction based on this issue: {feedback}"
                    ))
                # Remove EVALUATION_FEEDBACK from user-visible content
                cleaned_content = re.sub(r'EVALUATION_FEEDBACK:.*?(?:\n|$)', '', msg.content)
                if cleaned_content.strip() and isinstance(msg, AIMessage):
                    updates["messages"].append(AIMessage(content=cleaned_content.strip()))
            else:
                # Include message as-is
                updates["messages"].append(msg)
    
    # If no feedback found, assume success
    if not feedback_found:
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
    
    # If no transactions and no feedback, go to evaluator to finalize
    return "evaluator"


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
            "generator": "generator"
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