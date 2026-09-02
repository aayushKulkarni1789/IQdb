from typing import Any, NotRequired

from langchain.agents import AgentState


class FilterAgentState(AgentState):
    """Agent Filter State holding mutable list of Filter objects.

    Typed as list[Any] so LangChain/LangGraph does not coerce plain Filter
    objects through Pydantic (they are not BaseModels). Replace semantics
    via Command(update={"filters": next_list}), no reducer.
    """

    filters: NotRequired[list[Any]]
