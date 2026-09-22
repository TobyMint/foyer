#!/usr/bin/env python3
"""Did a static-cap run actually run at the cap its name claims?

Why this exists as a script. On 2026-09-17 a run named `cap3_r2` was judged to be
"really a cap4" from the very field this script reads, the judgement drove a
5-GPU-hour rerun, and it was wrong (claim register R11). The field was read
backwards. So the semantics are written down here once, next to the code that
depends on them, rather than re-derived at each use:

    src/session.rs:186-226
        while cur < cap {                        // cur = cap is UNREACHABLE
            compare_exchange_weak(cur, cur + 1)
        }
        log_admission(..., cur + 1, ...)         // logs the POST-increment value

    => a cap-2 run logs active in {1, 2};  a cap-3 run logs it in {1, 2, 3}.
    => max(active over admit events) == cap is the PASSING signature, not a
       symptom of over-admission.

This checks one run per invocation and reports; it never edits. A run whose
admissions log is missing or whose max(active) != cap is reported as
INCONSISTENT and should not enter a table.

    verify_static_cap.py <run_dir> [<run_dir> ...]
"""
import json
import os
import sys
from collections import Counter


def check(run_dir):
    path = os.path.join(run_dir, "admissions.jsonl")
    if not os.path.exists(path):
        return None, "no admissions.jsonl"
    caps, actives = Counter(), Counter()
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("event") != "admit":
            continue
        caps[r.get("cap")] += 1
        actives[r.get("active")] += 1
    if not actives:
        return None, "no admit events"
    if len(caps) != 1:
        return None, "cap field is not constant: %s" % dict(caps)
    cap = next(iter(caps))
    top = max(actives)
    detail = "cap=%s  admits=%d  active=%s" % (
        cap, sum(actives.values()),
        " ".join("%d:%d" % kv for kv in sorted(actives.items())))
    if top == cap:
        return True, detail
    return False, "%s  <-- max(active)=%d but cap=%d" % (detail, top, cap)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    bad = 0
    for d in sys.argv[1:]:
        ok, detail = check(d)
        name = os.path.basename(d.rstrip("/"))
        if ok is None:
            print("%-28s SKIP  %s" % (name, detail))
            bad += 1
        elif ok:
            print("%-28s OK    %s" % (name, detail))
        else:
            print("%-28s FAIL  %s" % (name, detail))
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
