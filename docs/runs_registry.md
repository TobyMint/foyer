# Run registry (auto-generated — source: each run's metadata.json)

Config vocabulary: `static=N` = fixed concurrency cap | `budget3` = capacity-accounting controller (defaults: target=0.75, margin=1.15) | `budget3:k=v` overrides: `target` = fraction of pool usable, `sf=0` = single-flight admission OFF, `hw=0` = high-water floor OFF, `sg=0` = starve guard OFF, `predictor=` = growth forecaster | `aimd2` = Concur-style reactive control | `budget2` = clairvoyant reservation (non-deployable)

⚠ = KV pool differs from the aligned 101,432 — another job held VRAM at server start, so the run is NOT comparable to the current tables (run_matrix now aborts on this instead of recording it)

Status: `done` = summary.json exists; `running` = started but no summary yet (in flight or killed). Wall falls back to the step span when the run was killed before writing its wall.

| run | policy | tier | trace | pool | wall(min) | status | started |
|---|---|---|---|---|---|---|---|
| aimd2_paper | `aimd2:u_low=0.2;u_high=0.5;h_thresh=0.2` | 200 | night200_clean | 101432 | 267.3 | running | 09-18 14:08 |
| aimd2_uh75 | `aimd2:u_low=0.2;u_high=0.75;h_thresh=0.2` | 200 | night200_clean | 101432 | 279.8 | done | 09-18 05:19 |
| pois200_cap3_r2 | `static=3` | 200 | pois200_l04 | 101432 | 259.2 | done | 09-17 07:06 |
| load25c_cap5r | `static=5` | 25 | night25 | 101432 | 28.7 | done | 09-17 06:10 |
| p200_fix_r2 | `budget3:hw=0;target=0.95` | 200 | night200_clean | 101432 | 311.4 | done | 09-17 05:53 |
| load25c_cap3r | `static=3` | 25 | night25 | 101432 | 30.4 | done | 09-17 05:38 |
| realhr_cap2 | `static=2` | peak | realhr | 101432 | 131.9 | done | 09-16 03:21 |
| realhr_foyer | `budget3:hw=0;target=0.95` | peak | realhr | 101432 | 79.3 | done | 09-16 02:00 |
| pois200_cap4 | `static=4` | 200 | pois200_l04 | 101432 | 257.6 | done | 09-15 21:39 |
| pois200_cap2 | `static=2` | 200 | pois200_l04 | 101432 | 310.5 | done | 09-15 11:43 |
| pois200_foyer | `budget3:hw=0;target=0.95` | 200 | pois200_l04 | 101432 | 299.3 | done | 09-15 11:43 |
| thr25_hwsf | `budget3:hw=0;sf=0` | 25 | night25 | 101432 | 34.1 | done | 09-15 10:15 |
| thr25_push_r2 | `budget3:hw=0;target=0.95` | 25 | night25 | 101432 | 33.9 | done | 09-15 10:15 |
| thr25_push | `budget3:hw=0;target=0.95` | 25 | night25 | 101432 | 33.0 | done | 09-14 18:02 |
| thr25_nohw | `budget3:hw=0` | 25 | night25 | 101432 | 41.8 | done | 09-14 17:07 |
| thr25_t95 | `budget3:target=0.95` | 25 | night25 | 101432 | 43.4 | done | 09-14 17:07 |
| thr25_base | `budget3` | 25 | night25 | 101432 | 62.1 | done | 09-14 14:16 |
| thr25_nosf | `budget3:sf=0` | 25 | night25 | 101432 | 53.2 | done | 09-14 14:16 |
| load25c_cap2r | `static=2` | 25 | night25 | 101432 | 37.4 | done | 09-13 20:18 |
| load25c_cap7r | `static=7` | 25 | night25 | 101432 | 32.1 | done | 09-13 20:18 |
| load25c_cap8r | `static=8` | 25 | night25 | 101432 | 33.4 | done | 09-13 20:18 |
| budget200c_budget3_zero | `budget3:predictor=zero` | 200 | night200_clean | 101432 | 424.5 | done | 09-13 10:25 |
| load25c_budget3_sg0 | `budget3:sg=0` | 25 | night25 | 101432 | 76.7 | done | 09-13 10:25 |
| load25c_budget3_glob | `budget3:predictor=global` | 25 | night25 | 101432 | 58.9 | done | 09-13 07:32 |
| load25c_budget3_oracle | `budget3:predictor=oracle` | 25 | night25 | 101432 | 92.4 | done | 09-13 07:32 |
| budget200c_cap2_hc | `static=2` | 200 | night200_clean | 101432 | 298.2 | done | 09-12 22:25 |
| budget200c_budget3_agg_hc | `budget3:target=0.85;sf=0` | 200 | night200_clean | 101432 | 459.1 | done | 09-12 19:24 |
| load25c_budget3_agg_hc | `budget3:target=0.85;sf=0` | 25 | night25 | 101432 | 42.0 | done | 09-12 18:24 |
| load25c_budget3_hc | `budget3` | 25 | night25 | 101432 | 59.0 | done | 09-12 17:07 |
| load25c_cap6_hc | `static=6` | 25 | night25 | 101432 | 22.8 | done | 09-12 16:43 |
| budget200c_cap1 | `static=1` | 200 | night200_clean | 101432 | 515.7 | done | 09-12 13:27 |
| budget200c_cap2 | `static=2` | 200 | night200_clean | 101432 | 301.7 | done | 09-12 10:53 |
| load25c_budget3_zero | `budget3:predictor=zero` | 25 | night25 | 101432 | 46.7 | done | 09-12 10:53 |
| budget200c_budget3_r2 | `budget3` | 200 | night200_clean | 101432 | 540.1 | done | 09-12 02:27 |
| load25c_budget3_t80 | `budget3:target=0.80` | 25 | night25 | 101432 | 54.9 | done | 09-12 01:14 |
| budget200c_budget3_r3 | `budget3` | 200 | night200_clean | 101432 | 555.3 | done | 09-11 17:52 |
| margin=1.0 | `margin=1.0` | 25 | night25 | 101432 | 19.9 | done | 09-11 17:40 |
| load25c_budget3_t85 | `budget3:target=0.85` | 25 | night25 | 101432 | 33.5 | done | 09-11 17:06 |
| load25c_budget3_t90 | `budget3:target=0.90` | 25 | night25 | 101432 | 35.9 | done | 09-11 17:06 |
| budget200c_cap5 | `static=5` | 200 | night200_clean | 101432 | 265.5 | done | 09-11 10:26 |
| budget200c_aimd2 | `aimd2` | 200 | night200_clean | 101432 | 291.4 | done | 09-11 04:54 |
| budget200c_default | `default` | 200 | night200_clean | 101432 | 228.1 | done | 09-11 01:03 |
| budget200c_cap3 | `static=3` | 200 | night200_clean | 101432 | 249.4 | done | 09-11 00:30 |
| budget200c_budget3 | `budget3` | 200 | night200_clean | 101432 | 669.2 | done | 09-10 20:36 |
| budget200c_cap4 | `static=4` | 200 | night200_clean | 101432 | 265.6 | done | 09-10 20:36 |
| budget200c_budget3_timedout_591steps | `budget3` | 200 | night200_clean | 101432 | 360.0 | running | 09-10 12:31 |
| load25c_cap1 | `static=1` | 25 | night25 | 101432 | 63.3 | done | 09-10 11:16 |
| load25c_budget2 | `budget2` | 25 | night25 | 101432 | 27.9 | done | 09-10 10:47 |
| load25c_aimd2_i2 | `aimd2:interval=2` | 25 | night25 | 101432 | 39.4 | done | 09-10 10:05 |
| load25c_aimd2 | `aimd2` | 25 | night25 | 101432 | 35.5 | done | 09-10 09:28 |
| load25c_cap6 | `static=6` | 25 | night25 | 101432 | 27.9 | done | 09-10 08:58 |
| budget2_nosv | `budget2_nosv` | 200 | night200 | 114495 ⚠114495 | 230.8 | done | 09-10 08:33 |
| load25c_cap4 | `static=4` | 25 | night25 | 101432 | 30.4 | done | 09-10 08:26 |
| load25c_default | `default` | 25 | night25 | 101432 | 32.2 | done | 09-10 07:52 |
| load25c_budget3 | `budget3` | 25 | night25 | 101432 | 54.8 | done | 09-10 06:56 |
| budget2_nosf | `budget2_nosf` | 200 | night200 | 114495 ⚠114495 | 224.6 | done | 09-10 04:46 |
| cap4_r3 | `static=4` | 200 | night200 | 114495 ⚠114495 | 224.3 | done | 09-10 03:02 |
| budget2_nohw | `budget2_nohw` | 200 | night200 | 114495 ⚠114495 | 272.5 | done | 09-10 00:11 |
| cap4_r2 | `static=4` | 200 | night200 | 114495 ⚠114495 | 223.4 | done | 09-09 23:17 |
| aimd_r3 | `aimd` | 200 | night200 | 114495 ⚠114495 | 277.3 | done | 09-09 19:32 |
| budget2_r3 | `budget2` | 200 | night200 | 114495 ⚠114495 | 263.6 | done | 09-09 18:51 |
| aimd_r2 | `aimd` | 200 | night200 | 114495 ⚠114495 | 272.1 | done | 09-09 14:58 |
| budget2_r2 | `budget2` | 200 | night200 | 114495 ⚠114495 | 231.4 | done | 09-09 14:58 |
| budget2 | `budget2` | 200 | night200 | 114495 ⚠114495 | 227.1 | done | 09-09 10:48 |
| load50_budget2 | `budget2` | 50 | night50 | 101432 | 63.6 | done | 09-09 10:02 |
| load25_budget2 | `budget2` | 25 | night25 | 101432 | 31.1 | done | 09-09 09:30 |
| load50_budget | `budget` | 50 | night50 | 101432 | 71.6 | done | 09-08 22:48 |
| load25_aimd | `aimd` | 25 | night25 | 114495 ⚠114495 | 30.5 | done | 09-08 21:49 |
| load50_aimd | `aimd` | 50 | night50 | 114495 ⚠114495 | 69.2 | done | 09-08 21:48 |
| load50_cap6 | `static=6` | 50 | night50 | 101432 | 73.8 | done | 09-08 21:32 |
| load50_default | `default` | 50 | night50 | 76018 ⚠76018 | 79.9 | done | 09-08 20:10 |
| load25_budget | `budget` | 25 | night25 | 72647 ⚠72647 | 46.3 | done | 09-08 15:00 |
| load25_cap6 | `static=6` | 25 | night25 | 114495 ⚠114495 | 27.0 | done | 09-08 14:00 |
| load25_default | `default` | 25 | night25 | 114495 ⚠114495 | 31.5 | done | 09-08 13:27 |
| cap4 | `static=4` | 200 | night200 | 114495 ⚠114495 | 233.8 | done | 09-08 10:32 |
| aimd | `aimd` | 200 | night200 | 114495 ⚠114495 | 267.1 | done | 09-08 08:59 |
| cap16 | `static=16` | 200 | night200 | 114495 ⚠114495 | 240.0 | running | 09-08 06:30 |
| cap8 | `static=8` | 200 | night200 | 114495 ⚠114495 | 240.0 | running | 09-08 04:17 |
| budget | `budget` | 200 | night200 | 114495 ⚠114495 | 240.0 | running | 09-08 02:28 |
| default | `default` | 200 | night200 | 114495 ⚠114495 | 221.7 | done | 09-08 00:33 |
