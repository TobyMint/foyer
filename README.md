# Foyer

**Anticipatory admission control for agentic LLM serving on memory-constrained GPUs.**

Coding-agent sessions arrive with heterogeneous, fast-growing KV working sets (median peak
context ≈ 69K tokens on real coding-agent traces). On a 24 GB GPU the KV pool (~115K tokens)
holds only a handful of such sessions, so *who gets admitted — and when* — decides whether the
system thrashes or serves. Foyer studies admission policies for this regime: an unbounded
engine degrades catastrophically (TTFT p50 34.6 min, 12.3% failed steps, prefix-hit rate 0%),
while arrival-time-informed admission keeps execution healthy (TTFT p50 80 s, 0.1% failures).

This repository contains the experiment infrastructure built to establish those findings on
real traces (4300+ sanitized coding-agent sessions from UW's TraceLab) replayed against SGLang
on a single RTX 3090.

## Layout

| Path | Contents |
|---|---|
| `runner/` | Patched [TraceLab](https://github.com/uw-syfi/TraceLab) `session_runner` (Apache-2.0): adds `--cap-file` (dynamic admission cap polled at runtime, for external controllers) and `--admission-log` (per-session admit/release events with wait times). See `UPSTREAM_README.md` for the unmodified upstream design. |
| `scripts/controller_aimd.py` | Concur-style cache-feedback AIMD admission controller (count-window, congestion signal = token usage above target AND hit-rate collapse). |
| `scripts/controller_budget.py` | Feed-forward token-budget controller: admits a queued session while its arrival-time-observable demand (first prompt + next-few-round growth, capped by session peak) fits the budget; engine-usage hard stop; rate-limited starvation guard. |
| `scripts/run_matrix.py` | Per-policy experiment driver: restarts a dedicated SGLang server, attaches monitor/controller, replays the trace, archives per-run artifacts. |
| `scripts/monitor.py` / `agg.py` | Metrics sampling (Prometheus exposition with labels) and cross-run aggregation/figures. |
| `scripts/launch_sglang.sh` | Working SGLang 0.5.10 launch environment for RTX 3090 (YaRN-extended 96K context; gcc-12/NVCC fixes for JIT kernels). |
| `results/night/` | One directory per admission policy over the 200-session replay: per-step logs, engine metrics, admission events, controller decisions, summaries. |
| `docs/NIGHT_REPORT.md` | Full findings, caveats, and next steps. |

## Key night-matrix results (200 sessions, Qwen2.5-Coder-7B, RTX 3090 24 GB)

| Policy | Failed steps | Prefix-hit rate | TTFT p50 |
|---|---|---|---|
| default (no gate) | **121 / 980 (12.3%)** | **0.0%** | **34.6 min** |
| static cap = 8 | 1 | 2.0% | 80 s |
| token-budget (ours) | 1 | 4.7% | 472 s |
| static cap = 16 | 1 | 0.0% | 166 s |

Static caps fail late (phase drift: short sessions finish, survivors are large, fixed count
over-commits the pool) — the motivation for demand-aware, dynamic admission.

## Reproducing

1. Server: Ubuntu + RTX 3090/4090, driver ≥ 550. Install Miniconda env with
   `sglang[all]==0.5.10.post1`, `conda` gcc-12 (`gxx_linux-64=12`) for JIT kernels, and rust
   (crates vendored: `cd runner && cargo vendor vendor` on a networked machine, then build
   with `.cargo/config.toml` pointing at `vendor/`).
2. Model: Qwen2.5-Coder-7B-Instruct with a patched `config.json`
   (`max_position_embeddings=98304`, `rope_scaling=yarn/3.0`) — see `scripts/launch_sglang.sh`.
3. Data: TraceLab public dataset (`syfi_coding_trace.duckdb`, GitHub releases) + a large
   UTF-8 corpus (enwik9) for the synthetic-token pool. Export replay CSVs with the schema
   `session_id,round_idx,prefix_len,input_len,output_len,tool_wait_after_ms`.
4. Run: `python scripts/run_matrix.py --lane A --gpu 3 --port 30000 --runs default,cap8:static=8,aimd`.

## Status

Work in progress (results are preliminary snapshots; some runs are time-censored — see
`docs/NIGHT_REPORT.md` for caveats). Not yet peer-reviewed.

## Attribution

`runner/` modifies [uw-syfi/TraceLab](https://github.com/uw-syfi/TraceLab) (Apache-2.0),
which also provides the public coding-agent dataset used here.
