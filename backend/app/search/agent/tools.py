from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from app.search.filter import InvalidFilterSpecError
from app.search.registry import UnknownFilterKindError, from_spec


@tool
def add_clip_filter(text: str, weight: float = 1.0, runtime: ToolRuntime = None) -> str | Command:
    """Add a CLIP semantic search filter.

    Args:
        text: Natural language query for CLIP ranking, e.g. "a photo of a cat".
        weight: Rank weight (default 1.0).
        runtime: Injected ToolRuntime with state.
    """
    # Build spec dict and validate via registry.from_spec (design D2)
    spec: dict[str, Any] = {"kind": "clip", "text": text, "weight": weight}
    try:
        f = from_spec(spec)
    except (UnknownFilterKindError, InvalidFilterSpecError) as exc:
        return str(exc)
    except Exception as exc:
        return str(exc)
    if not f.is_live:
        return f"Filter 'clip' is not implemented"
    current = list(runtime.state.get("filters", [])) if runtime and runtime.state else []
    next_list = current + [f]
    return Command(
        update={
            "filters": next_list,
            "messages": [
                ToolMessage("Success", tool_call_id=runtime.tool_call_id if runtime else "unknown")
            ],
        }
    )


@tool
def add_datetime_filter(
    date_lower: str | None = None,
    date_upper: str | None = None,
    time_lower: str | None = None,
    time_upper: str | None = None,
    days_included: list[str] | None = None,
    runtime: ToolRuntime = None,
) -> str | Command:
    """Add a datetime subset filter.

    All date/time strings are ISO format. Days are MONDAY..SUNDAY.

    Args:
        date_lower: ISO date lower bound, e.g. "2024-01-01".
        date_upper: ISO date upper bound.
        time_lower: ISO time lower bound, e.g. "08:00:00".
        time_upper: ISO time upper bound.
        days_included: List of DayOfWeek names.
        runtime: Injected ToolRuntime with state.
    """
    spec: dict[str, Any] = {"kind": "datetime"}
    if date_lower is not None:
        spec["date_lower"] = date_lower
    if date_upper is not None:
        spec["date_upper"] = date_upper
    if time_lower is not None:
        spec["time_lower"] = time_lower
    if time_upper is not None:
        spec["time_upper"] = time_upper
    if days_included is not None:
        spec["days_included"] = days_included
    try:
        f = from_spec(spec)
    except (UnknownFilterKindError, InvalidFilterSpecError) as exc:
        return str(exc)
    except Exception as exc:
        return str(exc)
    if not f.is_live:
        return f"Filter 'datetime' is not implemented"
    current = list(runtime.state.get("filters", [])) if runtime and runtime.state else []
    next_list = current + [f]
    return Command(
        update={
            "filters": next_list,
            "messages": [
                ToolMessage("Success", tool_call_id=runtime.tool_call_id if runtime else "unknown")
            ],
        }
    )


@tool
def reset_filters(runtime: ToolRuntime = None) -> Command:
    """Reset Agent Filter State to empty list."""
    return Command(
        update={
            "filters": [],
            "messages": [
                ToolMessage("Success", tool_call_id=runtime.tool_call_id if runtime else "unknown")
            ],
        }
    )


@tool
def get_specs(runtime: ToolRuntime = None) -> list[dict[str, Any]]:
    """Return current filter specs in Agent Filter State via to_spec()."""
    filters = runtime.state.get("filters", []) if runtime and runtime.state else []
    return [f.to_spec() for f in filters]


TOOLS = [add_clip_filter, add_datetime_filter, reset_filters, get_specs]
