"""Unit tests for run_matrix run-string parsing and policy routing.
GPT-audit-2 precondition: parser and command construction get tests BEFORE more
GPU time. Run: python3 tests/test_run_matrix_routing.py"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.path.join(HERE, "..", "scripts", "run_matrix.py"),            # laptop repo layout
    os.path.join(HERE, "..", "TraceLab", "replay", "scripts", "run_matrix.py"),  # server layout
]
_RM = next(p for p in _CANDIDATES if os.path.exists(p))
spec = importlib.util.spec_from_file_location("run_matrix", _RM)
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
    """Tests call the PRODUCTION routing function — not a copy of its logic
    (Codex audit: a duplicated-logic test is a false-confidence test)."""
    return rm.route_mode(mode)


def test_param_modes_route_to_their_controllers():
    cases = {
        "budget3": "budget3",
        "budget3:target=0.80": "budget3",
        "budget3:margin=1.0;sf=0": "budget3",
        "budget3:target=0.85;margin=1.0;sf=0": "budget3",
        "aimd2": "aimd2",
        "aimd2:alpha=4;interval=2": "aimd2",
        "budget2_nohw": "budget2_ablation",
        "static=4": "static",
        "default": "static",
    }
    for mode, expect in cases.items():
        got = routes_to_controller(mode)
        assert got == expect, f"mode {mode!r} routed to {got!r}, want {expect!r}"


def test_unknown_mode_is_rejected():
    # the audit's core scenario: an unknown mode must never silently fall through
    # to an ungated runner. Protection chain: parse_runs splits the comma-broken
    # string into fragments, route_mode() returns None for fragments, main() raises.
    assert routes_to_controller("sf=0") is None
    assert routes_to_controller("margin=1.0") is None
    fragments = rm.parse_runs("x:budget3:target=0.85,margin=1.0,sf=0")
    # production main() raises if ANY fragment lacks a routed controller:
    assert any(routes_to_controller(m) is None for _, m in fragments), fragments


def test_budget3_param_args_build():
    args = rm.budget3_param_args("budget3:target=0.85;sf=0")
    assert args == ["--target-util", "0.85", "--disable-single-flight"], args
    assert rm.budget3_param_args("budget3") == []


def test_aimd2_param_args_build():
    args = rm.aimd2_param_args("aimd2:alpha=4;interval=2")
    assert args == ["--alpha", "4", "--interval", "2"], args


if __name__ == "__main__":
    test_parse_runs_splits_on_comma_only()
    test_parse_runs_plain_modes()
    test_param_modes_route_to_their_controllers()
    test_unknown_mode_is_rejected()
    test_budget3_param_args_build()
    test_aimd2_param_args_build()
    print("ALL ROUTING TESTS PASS")
