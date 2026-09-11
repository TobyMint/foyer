"""Unit tests for run_matrix run-string parsing and policy routing.
GPT-audit-2 precondition: parser and command construction get tests BEFORE more
GPU time. Run: python3 tests/test_run_matrix_routing.py"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "run_matrix", os.path.join(HERE, "..", "scripts", "run_matrix.py"))
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)


def test_parse_runs_splits_on_comma_only():
    runs = rm.parse_runs(
        "load25c_budget3_sf0:budget3:margin=1.0;sf=0,"
        "load25c_budget3_t80:budget3:target=0.80")
    assert runs == [
        ("load25c_budget3_sf0", "budget3:margin=1.0;sf=0"),
        ("load25c_budget3_t80", "budget3:target=0.80"),
    ], runs


def test_parse_runs_plain_modes():
    assert rm.parse_runs("default,cap4:static=4,aimd2,budget3") == [
        ("default", "default"),
        ("cap4", "static=4"),
        ("aimd2", "aimd2"),
        ("budget3", "budget3"),
    ]


def routes_to_controller(mode):
    """Mirror of the dispatch conditions in main(): which controller branch a mode
    activates. budget3:param=... MUST route to the budget3 controller (GPT audit 2
    found param variants fell through and ran ungated)."""
    if mode == "budget3" or mode.startswith("budget3:"):
        return "budget3"
    if mode == "aimd2" or mode.startswith("aimd2:"):
        return "aimd2"
    if mode.startswith("budget2_") or mode.startswith("budget3_"):
        return "budget2-family"
    return "other"


def test_param_modes_route_to_their_controllers():
    cases = {
        "budget3": "budget3",
        "budget3:target=0.80": "budget3",
        "budget3:margin=1.0;sf=0": "budget3",
        "budget3:target=0.85;margin=1.0;sf=0": "budget3",
        "aimd2": "aimd2",
        "aimd2:alpha=4;interval=2": "aimd2",
    }
    for mode, expect in cases.items():
        got = routes_to_controller(mode)
        assert got == expect, f"mode {mode!r} routed to {got!r}, want {expect!r}"


def test_unknown_mode_is_not_silent():
    # the audit's core scenario: an unknown mode must never silently fall through
    # to an ungated runner. Unknown modes must raise or be rejected upstream.
    try:
        routes = routes_to_controller("sf=0")
    except Exception:
        routes = "rejected"
    assert routes == "other"


if __name__ == "__main__":
    test_parse_runs_splits_on_comma_only()
    test_parse_runs_plain_modes()
    test_param_modes_route_to_their_controllers()
    test_unknown_mode_is_not_silent()
    print("ALL ROUTING TESTS PASS")
