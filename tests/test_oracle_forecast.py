"""Unit tests for the oracle ablation arm's forecast.

audit-3: the old oracle summed input_len+output_len over a session's whole lifetime
and returned that constant on every tick — it never decayed as rounds completed and
double-counted round 0's input (already inside ctx). That made the arm a permanently
reserved lifetime footprint, so its makespan could not be read as "a more accurate
prediction is more conservative".

These tests pin the replacement definition: G*(t) = max(0, C(t+h) - C(t)), anchored
at the last COMPLETED round — the same anchor the EMA/global/zero arms use.
Run: python3 tests/test_oracle_forecast.py
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.path.join(HERE, "..", "scripts", "controller_budget3.py"),
    os.path.join(HERE, "..", "TraceLab", "replay", "scripts", "controller_budget3.py"),
]
_CB = next(p for p in _CANDIDATES if os.path.exists(p))
spec = importlib.util.spec_from_file_location("controller_budget3", _CB)
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)

# one session, contexts: round0=1000, round1=1200, round2=1500, round3=2200, round4=2300
TRAJ = {"s": {0: 1000, 1: 1200, 2: 1500, 3: 2200, 4: 2300}}
H = 3


def test_forecast_is_the_h_round_delta():
    # anchored at round 1 -> C(4) - C(1) = 2300 - 1200 = 1100
    assert cb.oracle_forecast(TRAJ, "s", 1, H) == 1100.0


def test_forecast_is_not_the_lifetime_total():
    """The bug audit-3 caught: a lifetime sum would be 1000+1200+1500+2200+2300."""
    lifetime = sum(TRAJ["s"].values())
    got = cb.oracle_forecast(TRAJ, "s", 1, H)
    assert got != lifetime and got < lifetime, (got, lifetime)


def test_forecast_decays_as_rounds_complete():
    """Monotone non-increasing in the anchor round: a reservation that never
    releases is exactly what made the old arm unusable for attribution."""
    vals = [cb.oracle_forecast(TRAJ, "s", t, H) for t in (0, 1, 2, 3, 4)]
    assert vals == sorted(vals, reverse=True), vals
    assert vals[-1] == 0.0, vals


def test_forecast_zero_at_and_past_session_end():
    # the session's last round is 4; at/past it there is nothing left to reserve
    for t in (4, 99):
        assert cb.oracle_forecast(TRAJ, "s", t, H) == 0.0, t


def test_forecast_window_is_clamped_at_session_end():
    """Fewer than h rounds remain -> take the last available round, do not run off."""
    # anchored at round 3, only round 4 remains -> C(4) - C(3) = 100
    assert cb.oracle_forecast(TRAJ, "s", 3, H) == 100.0


def test_forecast_unknown_session_and_empty_traj():
    assert cb.oracle_forecast(TRAJ, "nope", 0, H) == 0.0
    assert cb.oracle_forecast({}, "s", 0, H) == 0.0


def test_forecast_before_first_round_anchors_at_round_zero():
    """last_round == -1 means nothing completed; ctx holds prompt0 == round 0, so
    the anchor is round 0 and the window is rounds 1..h."""
    assert cb.oracle_forecast(TRAJ, "s", -1, H) == 1200.0  # C(3) - C(0) = 2200-1000


def test_forecast_never_negative_on_shrinking_context():
    shrinking = {"s": {0: 5000, 1: 4000}}
    assert cb.oracle_forecast(shrinking, "s", 0, H) == 0.0


def test_build_growth_traj_uses_prefix_plus_input(tmp_path=None):
    import tempfile
    csv_text = ("session_id,round_idx,prefix_len,input_len,output_len\n"
                "a,0,100,50,10\n"
                "a,1,150,30,10\n"
                "b,0,0,900,10\n")
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(csv_text)
        path = f.name
    traj = cb.build_growth_traj(path)
    os.unlink(path)
    assert traj == {"a": {0: 150, 1: 180}, "b": {0: 900}}, traj


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("ALL ORACLE TESTS PASS")
