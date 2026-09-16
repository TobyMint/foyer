
### §5.1 cliff (25-tier static sweep, aligned pool)

| strategy | policy | wall(min) | fails | hit% | TTFT p50(ms) | SLO% | avg conc |
|---|---|---|---|---|---|---|---|
| cap1 | `static=1` | 63.3 | 0 | 68.2 | 1273 | 95.2 | 1.00 |
| cap2 | `static=2` | 37.4 | 0 | 68.1 | 1369 | 93.6 | 1.98 |
| cap3 | `static=3` | 30.4 | 0 | 64.9 | 1655 | 86.4 | 2.73 |
| cap4 | `static=4` | 30.4 | 0 | 55.2 | 2528 | 74.4 | 3.49 |
| cap5 | `static=5` | 28.7 | 0 | 36.6 | 11028 | 46.4 | 4.80 |
| cap6 | `static=6` | 27.9 | 0 | 31.7 | 13505 | 36.0 | 5.12 |
| cap7 | `static=7` | 32.1 | 0 | 7.5 | 38146 | 6.4 | 6.42 |
| cap8 | `static=8` | 33.4 | 0 | 4.5 | 57107 | 3.2 | 7.70 |

### §5.2 main (200-tier, all strategies)

| strategy | policy | wall(min) | fails | hit% | TTFT p50(ms) | SLO% | avg conc |
|---|---|---|---|---|---|---|---|
| default | `default` | 228.1 | 121 | 0.0 | 2415006 | 0.2 | 135.25 |
| cap1 | `static=1` | 515.7 | 0 | 69.9 | 1595 | 94.8 | 1.00 |
| cap2 | `static=2` | 301.7 | 0 | 67.0 | 2117 | 90.0 | 2.00 |
| cap3 | `static=3` | 249.4 | 0 | 59.0 | 3466 | 76.9 | 2.99 |
| cap4 | `static=4` | 265.6 | 0 | 45.1 | 8401 | 52.8 | 3.93 |
| cap5 | `static=5` | 265.5 | 0 | 28.0 | 22732 | 31.0 | 4.98 |
| budget2 (clairvoyant) ⚠ no metadata: wall from step spans, pool unchecked | `budget2` | 247.4 | 0 | 46.9 | 7167 | 56.0 | 3.88 |
| aimd2 (Concur repro) | `aimd2` | 291.4 | 0 | 48.4 | 5558 | 65.9 | 3.62 |
| Foyer (agg+HiCache) | `budget3:target=0.85;sf=0` | 459.1 | 0 | 69.8 | 1902 | 92.6 | 1.34 |
| Foyer r3 | `budget3` | 555.3 | 0 | 68.6 | 1838 | 93.6 | 0.98 |
| Foyer fixed cfg | `p200_fix_r2` | — | — | — | — | — | — |

> ⚠ issues: budget200c_budget2: no metadata: wall from step spans, pool unchecked; p200_fix_r2: no result yet

### §5.3 predictor attribution (25-tier)

| strategy | policy | wall(min) | fails | hit% | TTFT p50(ms) | SLO% | avg conc |
|---|---|---|---|---|---|---|---|
| zero-growth | `budget3:predictor=zero` | 46.7 | 0 | 65.7 | 1585 | 92.8 | 1.52 |
| global | `budget3:predictor=global` | 58.9 | 0 | 66.8 | 1527 | 94.4 | 1.11 |
| EMA (default) | `budget3` | 54.8 | 0 | 66.8 | 1325 | 93.6 | 1.20 |
| oracle | `budget3:predictor=oracle` | 92.4 | 0 | 68.2 | 1257 | 95.2 | 0.66 |
| EMA, no starve guard | `budget3:sg=0` | 76.7 | 0 | 68.2 | 1286 | 95.2 | 0.83 |

### §5.4 HiCache rescue (25-tier cap6)

| strategy | policy | wall(min) | fails | hit% | TTFT p50(ms) | SLO% | avg conc |
|---|---|---|---|---|---|---|---|
| cap6 (no HiCache) | `static=6` | 27.9 | 0 | 31.7 | 13505 | 36.0 | 5.12 |
| cap6 + HiCache | `static=6` | 22.8 | 0 | 64.1 | 10210 | 49.6 | 5.69 |
| Foyer + HiCache | `budget3:target=0.85;sf=0` | 42.0 | 0 | 66.3 | 1407 | 90.4 | 2.65 |
| Foyer (no HiCache) | `budget3` | 54.8 | 0 | 66.8 | 1325 | 93.6 | 1.20 |

### HiCache control (200-tier — low concurrency, no eviction pressure)

| strategy | policy | wall(min) | fails | hit% | TTFT p50(ms) | SLO% | avg conc |
|---|---|---|---|---|---|---|---|
| cap2 (no HiCache) | `static=2` | 301.7 | 0 | 67.0 | 2117 | 90.0 | 2.00 |
| cap2 + HiCache | `static=2` | 298.2 | 0 | 67.2 | 2216 | 90.3 | 2.00 |
| Foyer + HiCache | `budget3:target=0.85;sf=0` | 459.1 | 0 | 69.8 | 1902 | 92.6 | 1.34 |

### throttle ablation (25-tier, current code)

| strategy | policy | wall(min) | fails | hit% | TTFT p50(ms) | SLO% | avg conc |
|---|---|---|---|---|---|---|---|
| baseline | `budget3` | 62.1 | 0 | 67.7 | 1372 | 95.2 | 1.03 |
| no single-flight | `budget3:sf=0` | 53.2 | 0 | 66.4 | 1575 | 92.8 | 1.25 |
| no high-water floor | `budget3:hw=0` | 41.8 | 0 | 65.0 | 1447 | 92.8 | 1.87 |
| target 0.95 | `budget3:target=0.95` | 43.4 | 0 | 62.3 | 1607 | 89.6 | 1.72 |
| floor off + target 0.95 | `budget3:hw=0;target=0.95` | 33.0 | 0 | 64.4 | 1679 | 92.8 | 2.28 |
|   … repeat | `budget3:hw=0;target=0.95` | 33.9 | 0 | 64.4 | 1820 | 89.6 | 2.42 |
| floor off + no single-flight | `budget3:hw=0;sf=0` | 34.1 | 0 | 65.6 | 1593 | 88.0 | 2.25 |

### arrival shape — Poisson λ=0.04/s (200 sessions)

| strategy | policy | wall(min) | fails | hit% | TTFT p50(ms) | SLO% | avg conc |
|---|---|---|---|---|---|---|---|
| cap2 | `static=2` | 310.5 | 0 | 67.7 | 2183 | 89.5 | 1.99 |
| cap3 | `pois200_cap3_r2` | — | — | — | — | — | — |
| cap4 | `static=4` | 257.6 | 0 | 45.9 | 7215 | 55.7 | 3.94 |
| Foyer fixed cfg | `budget3:hw=0;target=0.95` | 299.3 | 0 | 65.6 | 2369 | 88.6 | 2.12 |

> ⚠ issues: pois200_cap3_r2: no result yet

### arrival shape — real measured peak hour (117 sessions)

| strategy | policy | wall(min) | fails | hit% | TTFT p50(ms) | SLO% | avg conc |
|---|---|---|---|---|---|---|---|
| cap2 | `static=2` | 131.9 | 0 | 64.5 | 1126 | 100.0 | 1.85 |
| Foyer fixed cfg | `budget3:hw=0;target=0.95` | 79.3 | 0 | 59.8 | 1372 | 100.0 | 3.25 |
