"""The real app (app.main) serves every router, not only the per-router test apps."""

from app.main import app


def _served() -> set[tuple[str, str]]:
    paths = app.openapi()["paths"]
    return {(method.upper(), path) for path, ops in paths.items() for method in ops}


def test_feature_routes_are_registered_on_the_real_app():
    served = _served()
    for expected in [
        ("GET", "/api/v1/tickets"),
        ("GET", "/api/v1/services/status"),
        ("POST", "/api/v1/tool-calls/{tool_call_id}/confirm"),
        ("POST", "/api/v1/tool-calls/{tool_call_id}/cancel"),
        ("GET", "/api/v1/escalations"),
        ("POST", "/api/v1/rag/ask"),
    ]:
        assert expected in served, expected


def test_metrics_summary_stays_on_the_frontend_mock_for_now():
    # The dashboard needs the full MetricsSummary shape first (see app/routers/admin.py).
    assert ("GET", "/api/v1/metrics/summary") not in _served()
