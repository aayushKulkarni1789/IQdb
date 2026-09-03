from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call
from langchain.chat_models import init_chat_model

from app.core.config import settings
from app.search.agent.context import SYSTEM_PROMPT
from app.search.agent.state import FilterAgentState
from app.search.agent.tools import TOOLS


@wrap_model_call
def _disable_parallel_tool_calls(request, handler):
    """Middleware: disable parallel tool calls to avoid concurrent `filters` updates."""
    # Merge with existing model_settings so factory's bind_tools receives parallel_tool_calls=False
    return handler(
        request.override(model_settings={**request.model_settings, "parallel_tool_calls": False})
    )


def build_model():
    """Build OpenAI-compatible chat model from env (llama.cpp or Groq)."""
    return init_chat_model(
        model=settings.LLM_MODEL,
        model_provider="openai",
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        parallel_tool_calls=False,
    )


def build_agent():
    """Create LangChain agent with FilterAgentState and tools."""
    model = build_model()
    agent = create_agent(
        model,
        tools=TOOLS,
        state_schema=FilterAgentState,
        system_prompt=SYSTEM_PROMPT,
        middleware=[_disable_parallel_tool_calls],
    )
    return agent


def invoke(user_text: str) -> dict:
    """Run agent single-turn and return final state containing filters and messages."""
    agent = build_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": user_text}]})
    return result
