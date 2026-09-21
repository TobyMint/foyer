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


# audit-3: the previous tests checked that route_mode RETURNS the right name, but
# never that main() has a branch for every name it can return. "budget3_…" routes
# to "budget3_ablation", which is not None (so the unknown-mode guard passed), had
# no dispatch branch, and therefore left cap_args empty and started an UNGATED
# runner. The tests below close that gap.
KNOWN_UNIMPLEMENTED = {"budget3_ablation"}

_PROBE_MODES = [
    "budget3", "budget3:target=0.85", "budget3:target=0.80;margin=1.0;sf=0",
    "budget3_nohw", "budget3_anything",
    "foyer", "foyer:target=0.95;gs=0", "foyer:target=0.88;gs=0.5;hw=0",
    "aimd2", "aimd2:alpha=4;interval=2", "aimd",
    "budget2", "budget2_nohw", "budget",
    "static=4", "default",
]


def test_every_route_has_a_dispatch_branch():
    """The invariant main() relies on: route_mode's reachable outputs are exactly
    HANDLED_ROUTES plus the one deliberately unimplemented name."""
    reachable = {routes_to_controller(m) for m in _PROBE_MODES}
    reachable.discard(None)
    unhandled = reachable - rm.HANDLED_ROUTES
    assert unhandled == KNOWN_UNIMPLEMENTED, (
        f"route_mode can return {sorted(unhandled)} with no dispatch branch in "
        f"main() -> ungated runner. Either add the branch to HANDLED_ROUTES or "
        f"teach route_mode to refuse the mode.")
    missing = rm.HANDLED_ROUTES - reachable
    assert not missing, f"HANDLED_ROUTES names never produced: {sorted(missing)}"


def test_budget3_ablation_actually_refuses():
    """The hole audit-3 found, asserted directly: a mode that routes to an
    unimplemented branch must raise before any GPU work starts."""
    mode = "budget3_nohw"
    assert routes_to_controller(mode) not in rm.HANDLED_ROUTES
    src = open(_RM).read()
    assert "r not in HANDLED_ROUTES" in src, (
        "main() no longer guards on the ROUTE (only on the mode string), so a "
        "routed-but-undispatched mode can start an ungated runner again")


def test_solve_memfrac_survives_a_none_probe():
    """The pool guard's recovery path crashed on 2026-09-21.

    lane_memfrac starts as MEMFRAC_HINT (None) and start_server then runs at
    MEMFRAC, so the FIRST bad probe was recorded under the key None and the solver
    did `None + 0.01`. The guard had detected a shrunken pool correctly and then
    died inside its own recovery, aborting the lane with a traceback instead of a
    verdict. Every probe shape it can now be handed must return a float.
    """
    for probe in ({}, {None: 79212}, {0.85: 79212},
                  {None: 79212, 0.90: 100000},
                  {0.85: 79212, 0.90: 100000}):
        got = rm.solve_memfrac(probe, 101432)
        assert isinstance(got, float), (probe, got)


def test_solve_memfrac_steps_up_from_a_lone_point():
    """One point gives no slope, so the answer must be strictly higher than the
    dial that produced it — otherwise the retry re-probes the same memfrac and the
    lane burns all MAX_POOL_ATTEMPTS without ever moving."""
    assert rm.solve_memfrac({0.85: 79212}, 101432) > 0.85
    assert rm.solve_memfrac({None: 79212}, 101432) > float(rm.MEMFRAC)


def test_expected_pool_is_reachable_under_the_memfrac_ceiling():
    """A shrunken pool is compensated by RAISING memfrac, bounded by MAX_MEMFRAC.
    If a resolve needs more than the ceiling the lane is meant to abort cleanly —
    but the ceiling must at least be above the start, or the first retry is a
    no-op that re-probes the same dial."""
    assert rm.MAX_MEMFRAC > float(rm.MEMFRAC), (rm.MAX_MEMFRAC, rm.MEMFRAC)


if __name__ == "__main__":
    # Discover every test_* in this module rather than listing them by hand. The
    # hand-written list had drifted: it silently omitted
    # test_every_route_has_a_dispatch_branch — the one invariant that catches a
    # routed-but-undispatched mode — so adding a route without a dispatch branch
    # printed "ALL ROUTING TESTS PASS". A test that cannot fail is not a test.
    _tests = sorted((n, f) for n, f in globals().items()
                    if n.startswith("test_") and callable(f))
    for _name, _fn in _tests:
        _fn()
        print("  ok   %s" % _name)
    print("\nALL %d ROUTING TESTS PASS" % len(_tests))
