"""Etherscan tool for fetching contract ABIs and information."""

import os

import requests
from langchain_core.tools import tool


@tool
def get_contract_abi(contract_address: str, network: str = "mainnet") -> str:
    """Fetch the ABI for a verified contract from Etherscan.
    
    This helps you understand what functions a contract has, their parameters,
    and how to interact with them. Essential for working with any smart contract.
    
    Args:
        contract_address: The contract address to fetch ABI for
        network: Network name (mainnet, goerli, sepolia, etc.)
        
    Returns:
        The contract ABI as a JSON string, or error message
    """
    try:
        # Get API key from environment
        api_key = os.getenv("ETHERSCAN_API_KEY")
        if not api_key:
            return "Error: ETHERSCAN_API_KEY not found in environment"
        
        # Determine the right Etherscan domain
        if network == "mainnet":
            base_url = "https://api.etherscan.io"
        else:
            base_url = f"https://api-{network}.etherscan.io"
        
        # Make the API request
        url = f"{base_url}/api"
        params = {
            "module": "contract",
            "action": "getabi",
            "address": contract_address,
            "apikey": api_key
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "1":
            # Return the ABI
            return data["result"]
        else:
            return f"Error fetching ABI: {data.get('message', 'Unknown error')}"
            
    except Exception as e:
        return f"Error: {str(e)}"


@tool 
def get_contract_source(contract_address: str, network: str = "mainnet") -> str:
    """Fetch the source code and metadata for a verified contract.
    
    Useful when you need to understand the contract's implementation details,
    constructor parameters, or compilation settings.
    
    Args:
        contract_address: The contract address
        network: Network name (mainnet, goerli, sepolia, etc.)
        
    Returns:
        Contract source code and metadata, or error message
    """
    try:
        api_key = os.getenv("ETHERSCAN_API_KEY")
        if not api_key:
            return "Error: ETHERSCAN_API_KEY not found in environment"
        
        if network == "mainnet":
            base_url = "https://api.etherscan.io"
        else:
            base_url = f"https://api-{network}.etherscan.io"
        
        url = f"{base_url}/api"
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": contract_address,
            "apikey": api_key
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "1" and data["result"]:
            result = data["result"][0]
            
            # Format the response nicely
            output = []
            output.append(f"Contract Name: {result.get('ContractName', 'Unknown')}")
            output.append(f"Compiler: {result.get('CompilerVersion', 'Unknown')}")
            output.append(f"Optimization: {result.get('OptimizationUsed', 'Unknown')}")
            
            if result.get('ABI') and result['ABI'] != "Contract source code not verified":
                output.append("\nABI Available: Yes")
            
            if result.get('SourceCode'):
                output.append("\nSource Code:")
                output.append("-" * 50)
                # Limit source code preview
                source = result['SourceCode']
                if len(source) > 2000:
                    output.append(source[:2000] + "\n... (truncated)")
                else:
                    output.append(source)
                    
            return "\n".join(output)
        else:
            return f"Error: {data.get('message', 'Contract not verified or not found')}"
            
    except Exception as e:
        return f"Error: {str(e)}"


# Export tools
etherscan_tools = [get_contract_abi, get_contract_source]