# Auto Trendlines — multi-TF confluence

How the engine uses TradingView's **Auto Trendlines** indicator. It's a SEPARATE indicator from SMC
(LuxAlgo) — they're read and scored independently. We only **read** the trendlines (the indicator already
draws them on the chart); we do NOT redraw them.

## What it is
The Auto Trendlines indicator draws diagonal trend lines. We read each line **projected to the current bar**
(a price level) via a raw chart-model eval (`smc.read_trendlines` — the pine line-reader can't see
diagonals). A trade gets **+1 confluence** when its entry sits within tolerance of one of these levels.

## Multi-timeframe (4h / 1h / 15m)
The indicator recomputes per chart timeframe, so a single read only sees the current TF's lines.
`smc.read_trendlines_mtf(chart, tfs=("240","60","15"), base_tf=BASE_TF)`:
1. shows the indicator, then for each of **4h, 1h, 15m**: switches TF → waits for render → reads the
   projected levels,
2. hides the indicator and **restores the execution TF** (`BASE_TF`, 5m),
3. returns one **deduped** list of levels across all three TFs.

It's wired into `smc_context()` (which **caches** the result for `SMC_TTL` ≈ 1h), so the TF sweep — and its
brief on-chart flicker — only happens on the hourly refresh, not every tick.

## Decoupled from SMC
Previously the trendline score lived **inside** the SMC-present branch, so when the SMC indicator read failed
or was absent the trendlines were silently dropped (despite being readable). Now SMC and Auto-Trendline
confluence are scored **independently** in `scalp_fast`, behind separate flags `smc_confluence` and
`auto_trendlines`. A trendline touch counts on its own.

## Mandatory — fails loud
When `auto_trendlines` is on (default), the Auto Trendlines indicator **must be enabled on the chart**:
- `smc.assert_trendlines(chart)` raises `smc.TrendlinesMissing` if the study isn't found.
- The engine calls it at the top of every scan tick (`scalp_fast.main`), and `read_trendlines_mtf` raises too.
- So a missing indicator **throws an error** instead of silently scoring without it. (Turn off the
  `auto_trendlines` flag to opt out.)

## Files
`smc.py` — `read_trendlines`, `read_trendlines_mtf`, `assert_trendlines` / `TrendlinesMissing`.
`scalp_fast.py` — `smc_context()` (multi-TF read + cache), the independent confluence scoring, the mandatory
assertion. Tests: `test_smc.py`.
