from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini")

def tool() -> str:
    """Tool used for testing."""
    return "This is a tool response."

agent = create_react_agent(
    model=model,
    tools=[tool]
)
