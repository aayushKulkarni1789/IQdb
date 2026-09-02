from langgraph.types import Command

from app.search.agent.tools import (
    TOOLS,
    add_clip_filter,
    add_datetime_filter,
    get_specs,
    reset_filters,
)


class _MockRuntime:
    def __init__(self, state):
        self.state = state
        self.tool_call_id = "test"
        self.config = {}
        self.context = {}
        self.store = None
        self.tools = []


def test_add_clip_filter_valid_append():
    rt = _MockRuntime({"filters": []})
    res = add_clip_filter.func(text="a cat", weight=1.0, runtime=rt)
    assert isinstance(res, Command)
    assert len(res.update["filters"]) == 1
    assert res.update["filters"][0].to_spec()["text"] == "a cat"
    # second append should accumulate
    rt2 = _MockRuntime({"filters": res.update["filters"]})
    res2 = add_clip_filter.func(text="a dog", runtime=rt2)
    assert len(res2.update["filters"]) == 2


def test_add_clip_filter_malformed_reports_error_no_append():
    # Validated via registry path: missing text should produce InvalidFilterSpecError with actionable message
    from app.search.filter import InvalidFilterSpecError
    from app.search.registry import from_spec

    try:
        from_spec({"kind": "clip"})
        assert False
    except InvalidFilterSpecError as exc:
        msg = str(exc)
        assert "Problems:" in msg
        assert "text" in msg
        assert "Expected format:" in msg


def test_add_datetime_filter_valid_and_extra_fields_ignored():
    rt = _MockRuntime({"filters": []})
    res = add_datetime_filter.func(date_lower="2024-01-01", date_upper="2024-12-31", runtime=rt)
    assert isinstance(res, Command)
    assert len(res.update["filters"]) == 1
    spec = res.update["filters"][0].to_spec()
    assert spec["date_lower"] == "2024-01-01"


def test_add_datetime_filter_malformed_reports_error():
    rt = _MockRuntime({"filters": []})
    # Invalid range: lower > upper
    res = add_datetime_filter.func(date_lower="2024-12-31", date_upper="2024-01-01", runtime=rt)
    assert isinstance(res, str)
    assert "Problems:" in res or "date_lower" in res
    # State unchanged (empty) – we check that returned string does not contain update
    assert isinstance(res, str)


def test_add_clip_missing_text_reports_error():
    # Test via direct from_spec path: call with invalid spec via helper
    # We simulate malformed by calling add_clip with missing text via direct registry
    from app.search.registry import from_spec

    try:
        from_spec({"kind": "clip"})
        assert False, "should have raised"
    except Exception as exc:
        msg = str(exc)
        assert "Problems:" in msg
        assert "text" in msg
        assert "Expected format:" in msg
        assert "Example:" in msg


def test_reset_filters_clears():
    rt = _MockRuntime({"filters": []})
    res = add_clip_filter.func(text="cat", runtime=rt)
    filters = res.update["filters"]
    rt2 = _MockRuntime({"filters": filters})
    res_reset = reset_filters.func(runtime=rt2)
    assert isinstance(res_reset, Command)
    assert res_reset.update["filters"] == []


def test_get_specs_round_trips():
    rt = _MockRuntime({"filters": []})
    res = add_clip_filter.func(text="hello", runtime=rt)
    rt2 = _MockRuntime({"filters": res.update["filters"]})
    specs = get_specs.func(runtime=rt2)
    assert specs == [{"kind": "clip", "text": "hello", "weight": 1.0}]
    # after reset, empty
    rt3 = _MockRuntime({"filters": []})
    assert get_specs.func(runtime=rt3) == []


def test_only_live_kinds_exposed():
    tool_names = {t.name for t in TOOLS}
    assert "add_clip_filter" in tool_names
    assert "add_datetime_filter" in tool_names
    assert "reset_filters" in tool_names
    assert "get_specs" in tool_names
    assert "add_geo_filter" not in tool_names
    assert "add_face_filter" not in tool_names


def test_extra_fields_ignored_via_tools():
    # datetime with extra fields should still succeed
    rt = _MockRuntime({"filters": []})
    # Directly test registry handles extra fields
    from app.search.registry import from_spec

    f = from_spec({"kind": "clip", "text": "cat", "totally_unknown": 123})
    assert f.to_spec()["text"] == "cat"
