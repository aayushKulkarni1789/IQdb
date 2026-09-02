from app.search.agent.state import FilterAgentState
from app.search.filter import Filter


def test_filter_agent_state_holds_plain_filter_objects():
    # Should hold plain Filter objects without Pydantic coercion (list[Any])
    f = Filter()
    f.kind = "clip"  # type: ignore
    state: FilterAgentState = {"messages": [], "filters": [f]}  # type: ignore
    assert state["filters"][0] is f
    assert isinstance(state["filters"], list)
