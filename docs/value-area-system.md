# Prior-Day Value-Area System (end to end)

How the engine harvests, stores, judges, trades, and draws prior-day value areas (POC/VAH/VAL + single
prints) from the **Kioseff "Realtime TPO Profile" indicator**. We *read* the indicator — we never recompute
the profile. Companion specs: `value-area-framework.md` (Rules 1–7) and `gold-vwap-strategy.md` (the
VWAP-bias execution strategy the AI applies).

```
TPO indicator ──harvest──> va_store (sqlite) ──read──> engine level map + va_reject + Level State ──draw──> live chart overlay
   (read)        tpo.py        value_areas.db      prior_day_vas / va_state          va_reject.py         draw_overlay.py
```

## 1. Chart topology (which tab does what)
Authoritative live mapping = `instruments.json` (`XAUUSD.chart`). Two tabs carry PEPPERSTONE:XAUUSD + the TPO
indicator:
- **`eabXWKAd` = LIVE gold chart** — the engine reads it; the overlay draws here. **Never replay here.**
- **`eFMec2F9` = BACKTEST / spare tab** — all replay-based harvesting runs here, isolated from live.

Tab *index* ≠ chart_id and tab order changes — always target by chart_id (`TV_CHART`). See `src/connection.js`.

## 2. Harvest — reading a day's value area (`tpo.py`)
`fetch_va(symbol, date, chart)`:
- Runs on the **backtest tab** (`TV_BACKTEST_CHART`, default `eFMec2F9`). Pins the pair to PEPPERSTONE:XAUUSD
  and **verifies** it before reading (refuses to harvest the wrong instrument).
- Replays to `date`, steps into the day's late "close window", and reads the **VAH/VAL/POC text labels**
  (these are a single current-session set — clean). The daily TPO session rolls over at ~22:00 UTC.
- **Confirmed-date guard:** only reads while the replay cursor is *confirmed on the target date*. Replay's
  `current_date` intermittently returns `None`; reading then would capture the realtime/latest session and
  mislabel it as a past day (silent corruption). If the date is never confirmed → returns INCOMPLETE.
- **Single prints (SP):** the indicator draws SP labels for *every* session on screen and they accumulate
  replay residue. `session_sp()` keeps only the SP at the VA anchor's bar-`x` (±1) — the current session's —
  using the **verbose** label read (which carries `x`). Verbose only returns data for the latest/realtime
  session, so past-day backfills get no SP; the daily harvest of the just-closed session gets clean,
  session-scoped SP. `group_sp()` then groups SP levels into `[lo,hi]` zones.

## 3. Store — immutable cache (`va_store.py`)
Sqlite `value_areas.db`, key `(symbol, date)`, columns `poc/vah/val/sp/ts`. A closed day never changes, so a
COMPLETE row (poc+vah+val) is served forever and never re-fetched. `get_or_fetch` falls back to `fetch_va`.
**SP-preservation:** the harvest never overwrites an existing non-empty `sp` with an empty read (so a
re-harvest can't wipe verified single prints).

## 4. Schedule — daily harvest (`harvest_daily.py`)
Self-dating (most-recent closed weekday session), idempotent (skips complete days), and scanner-safe (pauses
the live scanner LaunchAgent only if it's actually loaded; always restores realtime). Scheduled via
`~/Library/LaunchAgents/com.yassir.vaharvest.plist` for the daily 22:00 UTC rollover (00:20–03:20 local,
idempotent retries; UTC-internal so DST-proof). `reharvest_week.py` force-backfills a date range.

## 5. Level State — Rules 6/7 (`va_state.py`)
Classifies a prior level against the CURRENT session's bars into **Untested / Rejected / Accepted / Flipped**,
price-only (no footprint/delta):
- **Untested** — price hasn't reached it. **Rejected** — tested and held (valid S/R). **Accepted** — pushed
  through and stayed (≥2 of: 2 closes beyond · retest holds beyond · >50% of bars beyond · POC migrated
  beyond · >30 min beyond) → level is dead, don't trade first touch. **Flipped** — accepted *and* a retest
  from the far side held (now role-reversed S/R).
- `rejection()` detects the wick-back + close-back + break-of-rejection-candle pattern.

## 6. Engine use
- **Level map / confluence:** `prior_day_vas()` (in `scalp_fast.py`) reads the last N cached days from the DB
  (date-faithful, no chart I/O) and adds `prevVAH/prevPOC/prevVAL` as confluence levels (a hugging POC+VAH or
  POC+VAL is merged to avoid double-counting).
- **Entry #13 `va_reject`** (`va_reject.py`, flag `va_reject`): the VWAP value-area rejection setup as a
  first-class trigger. LONG = above/reclaiming VWAP + confirmed rejection off a VALID prior VAL/POC/flipped-VAH
  (Rejected/Flipped, not Accepted) + R:R ≥ 1:2 to the nearest VWAP/POC. SHORT mirrors. Reversal-class.
- **`--review` output:** prints the open-vs-value regime, each prior level's side + pip distance, the Level
  State, and SP target zones — the inputs the AI judges per `gold-vwap-strategy.md`.

## 7. Draw — live overlay (`draw_overlay.py`, flag `draw_overlay`)
Draws the value-area level map on the **live chart** so it's visible: prior-day POC (yellow) / VAH (blue) /
VAL (purple) as horizontal lines labeled with the **date + Level State** (e.g. `prevVAH 06-05 [Rejected]`),
SP zones as orange boxes, and near-price SMC order blocks (read from the LuxAlgo indicator; green=demand below
price, red=supply above). Refreshed by the loop, **throttled** (`OVERLAY_MIN_INTERVAL`, 5 min) and
**id-tracked** (`~/.tv_overlay_ids.json`) so it never flickers or wipes the user's own drawings. Live only
(skipped in `--dry` and backtest runs).

## Tests
`test_tpo.py` (session_sp, group_sp, sessions) · `test_va_store.py` · `test_va_state.py` · `test_va_reject.py`
· `test_draw_overlay.py` — all pass.
