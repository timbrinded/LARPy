#!/bin/bash

# Load environment variables
source .env

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the agent address from private key
AGENT_ADDRESS=$(cast wallet address --private-key $AGENT_ETH_KEY)

echo -e "${BLUE}🚀 Starting Anvil fork of Ethereum mainnet...${NC}"

# Start Anvil in the background with mainnet fork
anvil \
    --fork-url https://eth-mainnet.g.alchemy.com/v2/$ALCHEMY_API_KEY \
    --port 8545 \
    --accounts 10 \
    --balance 1000 \
    --block-time 12 \
    --hardfork london \
    --silent &

ANVIL_PID=$!

# Wait for Anvil to be ready
echo -e "${BLUE}⏳ Waiting for Anvil to be ready...${NC}"
while ! nc -z localhost 8545; do
    sleep 0.1
done
sleep 2

echo -e "${GREEN}✅ Anvil is running on http://localhost:8545${NC}"
echo -e "${BLUE}💰 Funding agent account: $AGENT_ADDRESS${NC}"

# Fund the agent account with ETH (10 ETH)
if cast send $AGENT_ADDRESS --value 10ether --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --rpc-url http://localhost:8545 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Funded with 10 ETH${NC}"
else
    echo -e "${RED}❌ Failed to fund ETH${NC}"
fi

# Fund with USDC (10,000 USDC)
USDC_ADDRESS="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

# Use a different approach - directly set storage slot for USDC balance
# USDC uses slot 2 for balances mapping
# Calculate storage slot: keccak256(abi.encode(address, uint256(2)))
SLOT=$(cast keccak "$(cast abi-encode "f(address,uint256)" $AGENT_ADDRESS 2)")
# Set balance to 10,000 USDC (10000 * 10^6)
cast rpc anvil_setStorageAt $USDC_ADDRESS $SLOT "0x$(printf '%064x' 10000000000)" --rpc-url http://localhost:8545 > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Funded with 10,000 USDC${NC}"
else
    echo -e "${RED}❌ Failed to fund USDC${NC}"
fi

# Fund with USDT (10,000 USDT)
USDT_ADDRESS="0xdAC17F958D2ee523a2206206994597C13D831ec7"

# USDT also uses slot 2 for balances
SLOT=$(cast keccak "$(cast abi-encode "f(address,uint256)" $AGENT_ADDRESS 2)")
# Set balance to 10,000 USDT (10000 * 10^6)
cast rpc anvil_setStorageAt $USDT_ADDRESS $SLOT "0x$(printf '%064x' 10000000000)" --rpc-url http://localhost:8545 > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Funded with 10,000 USDT${NC}"
else
    echo -e "${RED}❌ Failed to fund USDT${NC}"
fi

# Verify balances
echo -e "\n${BLUE}📊 Verifying balances...${NC}"
ETH_BALANCE=$(cast balance $AGENT_ADDRESS --rpc-url http://localhost:8545 | cast from-wei)

# Get USDC balance and convert from hex
USDC_HEX=$(cast call $USDC_ADDRESS "balanceOf(address)(uint256)" $AGENT_ADDRESS --rpc-url http://localhost:8545 2>/dev/null || echo "0x0")
USDC_BALANCE=$(cast --to-dec $USDC_HEX 2>/dev/null || echo "0")
USDC_FORMATTED=$(echo "scale=2; $USDC_BALANCE / 1000000" | bc 2>/dev/null || echo "0")

# Get USDT balance and convert from hex
USDT_HEX=$(cast call $USDT_ADDRESS "balanceOf(address)(uint256)" $AGENT_ADDRESS --rpc-url http://localhost:8545 2>/dev/null || echo "0x0")
USDT_BALANCE=$(cast --to-dec $USDT_HEX 2>/dev/null || echo "0")
USDT_FORMATTED=$(echo "scale=2; $USDT_BALANCE / 1000000" | bc 2>/dev/null || echo "0")

echo -e "Agent: $AGENT_ADDRESS"
echo -e "  • ETH:  $ETH_BALANCE"
echo -e "  • USDC: $USDC_FORMATTED"
echo -e "  • USDT: $USDT_FORMATTED"

# Update RPC URL to point to local Anvil
export ETHEREUM_RPC_URL="http://localhost:8545"

echo -e "\n${BLUE}🚀 Starting LangGraph server...${NC}"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${BLUE}🛑 Shutting down...${NC}"
    kill $ANVIL_PID 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Run LangGraph dev server on port 8123 to match docs
uv run langgraph dev --port 8123

# Keep script running
wait $ANVIL_PID