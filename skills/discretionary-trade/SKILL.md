---
name: discretionary-trade
description: Trade XAUUSD/forex discretionarily as the AI decision-maker (no coded strategy). Top-down multi-TF read (SMC indicator + 30m TPO prior-day value areas + VWAP + EMAs + Auto-Trendlines + structure), classify the day type, find a signal at a meaningful level, score confluence, approve/reject, then execute and manage with real stops. Use for replay study, forward blind tests, and live discretionary calls.
---

# Discretionary AI Trading — XAUUSD / Forex

> ⚠ **DEPRECATED (2026-06).** Superseded by **`skills/scalp-suite`** — the consolidated 4-strategy indicator suite
> (Order Flow VWAP Deviation · native Volume Profile · Peak Activity Range + Liquidity Delta Profiler · Swing Breakout
> Sequence) with per-instrument target scaling and a regime selector. Use `scalp-suite` for new work. This SMC/CRT/TPO
> discretionary rulebook is kept for reference only.

**You are the trader.** No python detects the signal for you; you read the chart top-down, recognise the
setup, score it, decide, execute, and manage. This skill is the rulebook; the **canonical detailed reference is
`xauusd_forex_ai_signal_execution_manual_refined.md`** (the Claude-Optimized manual — 102 signals, each with
Description / Claude Analytical Focus / Setup / Trigger / Execution / Invalidation, plus the approval rules,
confluence scoring, and the structured output schema below). This file is the scannable distillation +
day-type/transition lessons from the replay studies; open the refined manual for the per-signal depth.
Not financial advice; for systematic analysis and disciplined review.

Convention: **1.00 in XAUUSD = 10 pips** (e.g. 4578→4566 = 12.0 = 120 pips). Minimum R:R **1:2**.

**Your analytical focus (read every chart through these lenses, in this order):** **Market Structure** (BOS /
CHoCH → trend & reversal) · **Liquidity** (pools at swing H/L, PDH/PDL, session extremes → sweeps) ·
**Institutional footprints** (KLZ, OB, breaker, mitigation, FVG) · **Volume Profile** (VAH/VAL/POC, HVN/LVN →
acceptance vs rejection) · **Session dynamics** (Asian/London/NY + lunch behaviours) · **Volatility** (ATR,
compression→expansion) · **Risk management** (R:R ≥ 1:2, clear invalidation). Pattern-spotting is secondary to
this contextual read.

---

## ⛔ HARD GATE — DO THE HTF READ *FIRST*, AND KEEP REFRESHING IT (failed this 2× — non-negotiable)
**BEFORE the FIRST `replay_step` / any execution on a day, you MUST have done the top-down HTF read THIS session:
switch to 4H → 1H → 15m, read structure/EMA/VWAP/SMC on each, set the bias + level map.** Do NOT start stepping
the execution TF off 3m/SBS alone — that is the exact mistake. THEN, while walking, **refresh on cadence: 15m every
15m of price, 1h every hour, 4h every 4h** (restore 3m + verify replay after each), AND always refresh the 15m
before acting on a setup. If you catch yourself executing without a current HTF read → STOP and do it.

## THE LOOP (every decision)
1. **CONTEXT** — build the multi-TF picture + level map **FIRST** (top-down 4H→1H→15m; see the HARD GATE above). Refresh on cadence.
2. **DAY TYPE** — classify the regime; it sets which playbook is allowed.
3. **LOCATION** — is price AT a meaningful level? If mid-range/no-man's-land → **WAIT**.
4. **SIGNAL** — does a recognised setup trigger at that level, in the allowed direction?
5. **SCORE** — confluence + R:R. Approve / Wait / Reject.
6. **EXECUTE & MANAGE** — entry, stop, targets, then breakeven / trail / stand-aside.

Re-check on the cadence (15m/15m, 1h/hr, 4h/4h) AND when price reaches a mapped level.

---

## STEP 1 — CONTEXT (top-down, build the level map)

Read **4H → 1H → 15m** for bias and structure; **3m** is execution only (**execution TF = 3m, changed from 5m on
2026-06**; HTF context unchanged. Everywhere this skill says "execution chart / execution TF / restore execution", it means **3m**).

**REFRESH CADENCE — re-read each TF at its own bar-close rhythm (frequency-matched; not all every 15m):**
- **15m TF → every 15m** (each execution checkpoint) — 1 TF switch, read SMC structure/OBs on 15m.
- **1h TF → every hour** (on the hour) — re-read 1h SMC + structure.
- **4h TF → every 4h** (new 4h bar: 00/04/08/12/16/20 UTC) — re-read 4h SMC + structure.
- **Daily → once per session** (and at each new day).
- **TPO 30m VAs → once at session start** (prior-day value areas don't change intraday; re-read only at a new
  day boundary). 3m = continuous execution.
This keeps the map current while minimising TF switches (most checkpoints = one 15m switch), which protects
replay stability. After each TF read, restore 3m and **verify the replay is still started + on the right date**.

Gather and mark these levels (the "map") — **read them off the indicators; never compute them yourself:**
- **SMC = the Smart Money Concepts (LuxAlgo) indicator, read on the HIGHER timeframes 15m / 1h / 4h.** SMC is
  HTF *context*, not a 3m execution tool. On each of 15m, 1h, 4h read: order blocks (supply/demand boxes),
  BOS/CHoCH structure, liquidity (EQH/EQL), swing highs/lows, and **premium/discount** (above equilibrium =
  premium → favour shorts; below = discount → favour longs). Read visually AND via `data_get_pine_boxes` /
  `data_get_pine_labels` with `study_filter="Smart Money"` (switch TF to 15m→1h→4h, read each). A 4h demand OB
  aligned with a 1h bullish CHoCH is far stronger than either alone.
- **VA = the TPO indicator, read on the 30m timeframe, ONE call.** Switch to 30m and read the TPO once — it
  shows ALL visible prior sessions. `data_get_pine_lines` verbose on `study_filter="TPO"`: **yellow = POC**,
  **lime pair = VAH (higher) / VAL (lower)** per session, red = single prints (ignore). Mark prev-day VAH/POC/VAL
  (and 2–3 days back). Do NOT recompute value areas — the TPO indicator is the source of truth.
- **VWAP** (session) + bands — the intraday mean. Above = bullish lean, below = bearish, repeated crosses = chop.
- **EMAs 50/100/200** — trend direction (stack/slope) and a dynamic S/R cluster.
- **Auto-Trendlines** — diagonal channel/trendline levels (read each projected to now).
- **Structure** — swing highs/lows, **PDH/PDL** (prev day high/low), session highs/lows (Asian/London/NY), daily/weekly open.

Then state: **Bias (Bullish/Bearish/Neutral)** · nearest valid level **above** (resistance) and **below** (support) ·
VWAP position · open-vs-prev-value.

---

## STEP 2 — DAY TYPE (the master filter; decides the playbook)

Classify from the open behaviour + structure + range/ER + position in the HTF map:
- **TREND day** (directional, expanding, lower-highs or higher-lows persist) → **with-trend continuation only.**
  Buy pullbacks to support (uptrend) / sell rallies to resistance (downtrend). Suppress counter-trend fades.
- **RANGE day** (rotating between two levels, close ≈ open, balanced) → **fade the extremes.** Long the range
  low / short the range high after rejection. Suppress mid-range breakouts. (Market-Profile inside-value rotation.)
- **DEAD day** (thin/holiday, sub-~40p expected range, no expansion) → **STAND ASIDE.** Most "setups" are traps.
- **REVERSAL / two-leg day** (a decisive reclaim of the morning base/structure flips bias) → trade continuation
  *within the current leg*; on a confirmed CHoCH/MSS at a level, switch sides.

**Open vs previous value (Market Profile):**
- Open **above** prev VAH → bullish discovery: long only on a VAH pullback that **holds + reclaims**; if it
  accepts back inside value → rotate to POC, **don't long**.
- Open **below** prev VAL → bearish discovery: mirror (short the VAL retest that holds).
- Open **inside** value → balanced → **fade VAH/VAL, avoid the middle/POC.**

**The transition rule (codex):** allow the first continuation trade while price still respects the reclaimed
3m EMA pack. Once repeated tests of the session extreme **fail to expand** and price slips back through the EMA
cluster, **downgrade that direction and switch** to failed-high / failed-bounce trades the other way.

---

## STEP 3 — LOCATION

A trade needs a **meaningful level**: SMC OB/KLZ/breaker · prev VAH/VAL/POC · PDH/PDL or session high/low ·
VWAP or a VWAP band · a clean swing / trendline / round number. **No level = no trade.** Mid-value, VWAP chop,
and "middle of nowhere" pins are auto-rejects.

---

## STEP 4 — SIGNAL (recognise the setup at the level)

Take only setups that fit the day type and bias. The high-value families (from the manual):

**SMC / Institutional** — KLZ retest · Order-Block retest · Breaker retest · FVG fill · **Liquidity sweep**
(take a high/low, close back inside, BOS opposite) · Equal-highs/lows sweep · **PDH/PDL sweep** · session
high/low sweep · **Stop-hunt reversal** · Displacement continuation.

**Market Profile** — prev **VAH/VAL rejection** · VAH-flip-support / VAL-flip-resistance · **failed auction**
above VAH / below VAL · POC magnet (range) · inside-value rotation (range) · outside-value acceptance (trend).

**VWAP** — VWAP reclaim long / rejection short · **VWAP pullback** continuation (trend) · band-2 reversal ·
band-walk ride (trend) · **VWAP chop filter (no-trade)** · VWAP+VAH/VAL confluence.

**Sessions** — Asian-range breakout/**fakeout** · London-open sweep · **London high/low sweep in NY** ·
**NY-open manipulation → AM continuation** · NY-lunch chop filter (no-trade) · daily/weekly-open retest · killzone sweep.

**Breakout/Fakeout** — clean breakout-retest · **failed breakout** · compression breakout · false-break above/below
range · break-and-retest of KLZ · failed retest.

**Patterns** — double top/bottom · H&S · **bull/bear flag** · wedges · triangles · rectangle · channel · parabolic exhaustion.

**Trigger candle (always required):** rejection wick + **BOS/CHoCH**, engulfing, pin bar, outside bar, or 3-candle
reversal — **prefer a candle CLOSE confirmation over a wick.** A level without a trigger is a watch, not a trade.

---

## STEP 5 — SCORE (confluence + R:R → decision)

Start 0. **Add:** +25 SMC OB/KLZ/breaker · +20 at VAH/VAL/POC · +20 PDH/PDL or session high/low **sweep** ·
+15 VWAP or band · +15 BOS/CHoCH confirmation · +10 London/NY active session · +10 fresh/untested level.
**Subtract:** −30 middle of value · −25 level already accepted-through · −20 tested >2× · −20 trading directly
into a strong opposite level · −20 VWAP chop.

**Decision:** **80–100 = strong (take it)** · **65–79 = wait for one more confirmation** · **<65 = reject.**

**MUST REJECT (any one true → no trade):** R:R < 1:2 · entry in the middle of a balanced value area (no edge) ·
trades directly into a strong unmitigated opposite level · no clear/logical invalidation · the level is already
**accepted through** (closed + retested beyond) · **VWAP chop** (non-directional around VWAP) · **stale** setup
(old / unclear / over-tested) · abnormal spread/slippage · a high-impact news spike that makes execution unsafe ·
NY-lunch / dead-time chop.

**MAY APPROVE only when ALL hold:** the setup is at a **meaningful level** (KLZ/OB/VAH-VAL/PDH-PDL/VWAP) ·
**market structure (BOS/CHoCH) confirms the direction** · entry/stop/targets are **precisely defined** · R:R ≥ 1:2 ·
session/volatility/narrative **context fits** the premise. Missing any → WAIT, don't force it.

**News:** never trade the FIRST news spike (whipsaws both ways). If a scheduled high-impact print has a clear
direction, trade the **pullback continuation** after it (38–50% hold + continuation BOS), not the impulse.

**Zone/level lifecycle — track each level's STATE; trade only live ones:**
- **new → untested** (best, +confluence) → **tested once** (still valid) → **tested >2×** (−20, weakening) →
  **mitigated** (price entered and partially filled the OB/zone) → **invalidated/accepted-through** (DEAD — drop it).
- A prev VAH/VAL/range edge / OB is **INVALID** once ≥2 of: two closes beyond it · a retest holds beyond it ·
  >30 min spent beyond it · POC migrates beyond it · new value builds beyond it. Invalid → don't trade first touch, drop from the map.

---

## STEP 6 — EXECUTE & MANAGE

**ORDER BLOCKS ARE PRECISE — enter FROM the OB, stop BEYOND it (do not eyeball the level).** When an SMC order
block / KLZ / supply-demand box is at your level, read its exact bounds (`data boxes` on the Smart Money study)
and:
- **Entry:** wait for price to TAP INTO the OB and reject — short from the OB's body, long from the OB's body —
  NOT below/above it chasing a break. (My May-26 error: shorted 4535 *below* a 4542–4550 supply OB, so price
  ran UP into the OB to fill it — the real rejection point — and stopped me, then faded as planned.)
- **Stop:** beyond the FAR edge of the OB + buffer (above a supply OB / below a demand OB). NEVER inside the OB —
  a stop inside the OB is guaranteed to be taken by the OB-fill stop-run before the move resolves.
- In a tight coil/range at a level, the stop must clear the WHOLE coil (and any OB) + buffer, not just the last cap.

- **Entry (general):** on the trigger (break of the rejection candle / BOS retest) — at the level, **prefer a LIMIT
  at the level over market-on-rejection** (better fill + tighter stop). Not chasing mid-move.
- **Stop:** beyond the invalidation (far side of the OB/zone/**whole swing** / SBS swing extreme + buffer), **size
  DOWN for a wider stop** rather than tightening it into the noise. Define it before entry. (See RECALIBRATION.)
- **Targets (two only, no T3 on scalps):** **T1 = nearest REAL liquidity** (VWAP/POC/VAH-VAL/PDH-PDL/SBS-CRT level) →
  take a **partial**; **T2/runner = next structure**. **R:R ≥ ~1.5 to T1 WITH a runner** (don't demand 2R-to-T1).
  Mode: MICRO_SCALP (small level-based TP) vs SCALP_TO_RUNNER (TP1 ≈100 pips as space-filter + structure TP2).
- **Manage:** **breakeven at ~+1R or once a minor structure is cleared — NOT a fixed +40 pips** (a too-tight BE
  scratches you on gold's noise). Partial at T1 → BE → **trail behind 3m structure / VWAP / EMA** to T2 on trend
  days. Close the runner if price closes back through VWAP against you, breaks 3m structure against you, or rejects a
  strong opposing HTF level. **Stand aside** in confirmed chop — but day-type decides: don't quit a good trend day
  after one stop; do stop forcing scalps into a range. (See RECALIBRATION + DAY-TYPE.)

**Output each decision in this structured form** (the refined manual's Claude output schema — always include the
`reasoning_chain_of_thought` narrative and a `confidence` read; `entry` carries an order `type`):
```json
{
  "decision": "APPROVE | REJECT | WAIT",
  "trade_mode": "MICRO_SCALP | SCALP_TO_RUNNER | INTRADAY | NO_TRADE",
  "market": "XAUUSD",
  "signal_name": "<e.g. Order Block Retest / SBS / CRT>",
  "direction": "LONG | SHORT | NEUTRAL",
  "bias": "BULLISH | BEARISH | NEUTRAL",
  "day_type": "TREND | RANGE | DEAD | REVERSAL",
  "entry": { "price": 0.0, "type": "MARKET | LIMIT | STOP" },
  "stop_loss": 0.0, "target_1": 0.0, "target_2": 0.0, "risk_reward_to_t1": 0.0,
  "breakeven_trigger": "+1R or cleared minor structure (NOT fixed +40p)",
  "confidence": "HIGH | MEDIUM | LOW",
  "level_state": "Untested | Tested | Rejected | Accepted | Flipped | Mitigated",
  "vwap_position": "above | below | chopping", "open_vs_prev_value": "above VAH | inside | below VAL",
  "reasoning_chain_of_thought": "<narrative: HTF structure → day-type → level → trigger → R:R/stop/target, and why the MUST-REJECT gates are clear and the MAY-APPROVE conditions all hold. Not a bullet list — a reasoned story.>",
  "confluence_score_details": { "<each + / − line that applied>": 0, "final_score": 0 }
}
```
`confidence`: HIGH ≈ score ≥ 80 with blind-agent agreement and no veto; MEDIUM ≈ 65–79 / one soft concern;
LOW ≈ borderline — pair LOW with WAIT, never APPROVE. A one-line plain-text summary is fine for quick logs, but
the committee and any forward-test log get the full JSON.

---

## MULTI-AGENT REVIEW COMMITTEE (sign-off before any trade fires)
When a candidate signal forms, convene a panel of role-specialized reviewer agents IN PARALLEL (one Agent call
each). **Give every agent the full evidence: screenshots of ALL timeframes (4h/1h/15m/3m, SMC shown) + the data
(level map, prior-day VAs, SMC OBs, bars-up-to-now) + the proposed signal (side/entry/SL/T1/T2/thesis) + this skill.**
Each judges the chart independently and returns the **structured verdict schema above** (decision +
`reasoning_chain_of_thought` + `confidence` + `confluence_score_details`) so verdicts are directly comparable.

| # | Agent | Gets | Validates | Veto |
|---|-------|------|-----------|------|
| 1 | **Blind Independent Trader** | charts + data **only, NO thesis** | independently calls LONG/SHORT/NO-TRADE + its own entry/SL/T1/T2 (breaks anchoring) | — |
| 2 | **Context & Regime** | full set + thesis | HTF structure (4h/1h SMC, BOS/CHoCH, premium/discount) + day-type + session — is it WITH the regime? | — |
| 3 | **Level & Trigger** | full set + thesis | entry at a real/FRESH level (OB/VAH-VAL-POC/VWAP/PDH-PDL, not accepted-through) + trigger-candle quality + confluence | — |
| 4 | **Risk & Numbers** | full set + thesis | stop BEYOND the OB/invalidation (not inside) · R:R ≥ 1:2 · target at ACTUAL nearest liquidity · **verifies the price/OB/R:R math** | **HARD** |
| 5 | **Adversary** | full set + thesis | argue AGAINST — find the trap (stop-hunt, low-vol bounce, into opposite level, over-tested). Default refute. | **HARD** |

**Why this beats a flat panel:** Agent 1 is **blind** (no thesis) → real independence, not five agents grading my plan; merged Context removes overlap; the two hard-veto agents (Numbers, Adversary) catch the exact errors I've made (OB-stop-inside, eyeballed levels, chasing).

**Decision rule:** take the trade ONLY if **Agent-1 (blind) independently agrees on direction + zone, AND ≥3/4 of Agents 2–5 APPROVE, AND neither hard-veto agent rejects.** Else WAIT / no-trade. Log every verdict.
Optional upgrades: run 1–2 agents on a **different model** (true diversity, not just role-prompting); the human/main loop is the final synthesizer.

## SIGNAL REFERENCE (the 102-signal manual, condensed — full detail in `xauusd_forex_ai_signal_execution_manual_refined.md`)
Every signal: needs a meaningful level + a trigger, **prefer candle CLOSE over wick**, **R:R ≥ 1:2**, target the
**nearest liquidity** (VWAP/POC/VAH-VAL/PDH-PDL or 2R). `★` = Excellent for XAUUSD (prioritise). **Track each
zone's state** (new→untested→tested→mitigated→invalidated); trade only live ones.

**SMC / Institutional** — *enter FROM the zone on rejection, stop BEYOND its far edge.*
- ★KLZ retest · ★Order-Block retest (tap last opposite candle before displacement, reject, LTF BOS) · Breaker
  retest (broken OB flips polarity) · Mitigation-block retest · ★FVG fill (fill 50–100%, reject) · ★Liquidity
  sweep / ★Equal-high/low sweep / ★PDH-PDL sweep / Session-high/low sweep (take the level, close back inside,
  BOS opposite) · ★Stop-hunt reversal (big wick pierces + closes back, next candle confirms) · ★Displacement
  continuation (impulse+BOS → shallow 38–62% / OB / FVG pullback → continuation).

**Market Profile** — ★VAH/VAL rejection (wick beyond, close back, BOS → POC then opposite) · ★VAH-flip-support /
VAL-flip-resistance (close+hold beyond, retest) · ★Failed auction above VAH / below VAL (break out, close back
inside → POC) · POC magnet / Inside-value rotation (RANGE: fade edges to POC) · ★Outside-value acceptance
(TREND: 2 closes out + retest) · Poor-high/low repair · Single-prints fill · LVN rejection · HVN magnet (target).

**VWAP** — ★Reclaim long (below→2 closes above, retest, BOS) · ★Rejection short (mirror) · ★Pullback long/short
(trend; pullback to VWAP rejects) · Band-2 reversal (extreme + CHoCH, not first touch) · ★Band-walk ride (trend;
enter pullbacks to band1/VWAP) · ★VWAP chop filter = **NO TRADE** · ★Anchored-VWAP retest · VWAP+VA confluence.

**Patterns** — Double/Triple top-bottom · H&S / inverse · ★Bull/Bear flag (pole+flag, break+retest, pole-projection
target) · Pennants · Triangles (asc/desc/sym) · Wedges (rising=bearish break / falling=bullish) · Rectangle
breakout / reversal · Channel bounce / breakout · ★Parabolic exhaustion (fade only after CHoCH).

**Sessions** — Asian-range breakout · ★Asian-range fakeout (sweep + reclaim + BOS) · London-open sweep · ★London
high/low sweep in NY (NY takes London extreme, reclaims, BOS = fade) · ★NY-open manipulation (first 15–45m sweep+
fail+BOS) → ★NY-AM continuation (pullback to VWAP/KLZ/FVG) · ★NY-lunch chop = **NO TRADE** · London-close reversal ·
Daily/Weekly-open retest · ★Killzone liquidity sweep (sweep+reclaim+BOS in London/NY killzone).

**Breakout / Fakeout** — Clean breakout-retest · ★Failed breakout (break, close back inside, BOS = fade) ·
Breakout-without-retest (trend-day only) · ★Compression breakout (low-ATR → expansion) · ★False break above/below
range (sweep range extreme, close inside, BOS) · Break-&-retest of KLZ · Failed retest (retest fails fast, snaps back).

**Liquidity models (#101–102 — on-chart indicators are DETECTORS only; always validate liquidity+structure+R:R manually):**
- ★**SBS — Swing Breakout Sequence** (the LuxAlgo "Swing Breakout Sequence" indicator on our chart). **READ it off
  the indicator, don't reconstruct it:** the indicator auto-marks the points **1→5** + **"Swing High"/"Swing Low"**
  labels + the **shaded liquidity boxes** directly on the chart at whatever TF you're on (visually, and try
  `data_get_pine_boxes` / `data_get_pine_labels` study_filter="Swing Breakout"). My job is to validate the
  liquidity/structure/R:R narrative on top — same "read, never compute" rule as SMC/TPO. **TF: SBS is fractal — it
  forms and is tradable directly on 3m AND 5m/15m** (1H for larger swings); run the whole sequence + post-P5 entry on 3m
  (scalp), or read the sequence on 5m/15m and drop to 3m for the post-P5 trigger/entry. 6-point
  liquidity-trap model: **P0** swing → **P1** impulse → **P2** key-liquidity pullback (holds beyond P0) → **P3**
  new/failed extreme that traps breakout traders → **P4** sweeps P2 liquidity *without accepting beyond* → **P5**
  reversal point (EQ-high/low, double-top/bottom, reject) → **CHoCH/BOS after P5 = the trigger.** Enter the post-P5
  break or its FVG/OB retest; target next liquidity / Point-3 / ≥2R. **NOT the first breakout.** Reject if the 6
  points are forced/over-tuned, P4 *accepts* beyond P2 (real reversal, not a raid), P5 makes no structure shift, or
  the breakout already ran to target.
  - **STOP = beyond the SBS Swing High/Low (point 3 extreme), NOT an arbitrary tight buffer.** The model's
    invalidation IS the swing extreme it drew — put the stop past it + ATR buffer, and size down. (May-15 proof: I
    shorted a lower-high with a tight +4-pt stop at 4567; the whipsaw wicked to **4572.64 — which was the SBS Swing
    High** — stopped me, then price fell to 4511 exactly as the bearish SBS projected. A stop above the SBS swing
    would have survived and caught the ~500-pip move.)
  - **CONSULT THE SBS INDICATOR AT EVERY CHECKPOINT** (read its labels/boxes each scan — it's why we added it). When
    a sequence completes (P5 + breakout) at a level, that IS a primary trigger; don't trade your own eyeballed
    rejections while ignoring it. (May-15: the bearish SBS completed ~4561 and called the 4561→4511 drop; I missed it
    because I read SBS once at the open then traded off price/EMA the rest of the day. Don't.)
- ★**CRT — Candle Range Theory** (CandelaCharts CRT; ICT-derived). **TF (our default): anchor on the 1H candle →
  confirm+enter on 3m** (faster scalp: 15m/30m anchor → 3m). HTF candle = a range: **CRT-High / CRT-Low /
  CRT-Mean(50%)**. Raid one side → **close back inside** (failed acceptance) → drop to LTF for **MSS/CHoCH/CISD** →
  enter the LTF displacement/FVG/OB/CISD retest. *Bullish:* HTF at support/discount, sweep < CRT-Low, close back
  above, LTF bull shift. *Bearish:* mirror at resistance/premium. **T1 = CRT-Mean, T2 = opposite side, T3 = external
  liquidity;** stop beyond the raid extreme + ATR buffer; ≥2R to T2. Fractal pairs: scalp 15m/30m/1H→1–5m · intraday
  1H/4H→5–15m · swing D/W→1H/4H. Reject if no LTF confirm, real acceptance outside the range, mid-value/VWAP-chop,
  or a late chase after the range is already delivered. (NB: this is the engine's busiest family — most live "CRT
  sweep+reclaim" fires auto-skip on sub-2R; the discretionary edge is selectivity + the LTF-confirmation gate.)

**Candle triggers (use AT a level, never standalone)** — Pin bar (wick ≥2× body) · Engulfing · Inside-bar break ·
★Outside-bar reversal (sweeps both sides, strong close) · Marubozu continuation · Doji = warning only ·
★**Rejection wick + BOS** (the core trigger) · Three-candle reversal.

**Trend / Structure** — BOS (continuation; enter the pullback after) · ★CHoCH (first reversal: break of last
LH/HL; enter retest/FVG/OB) · HH-HL / LL-LH trend · ★**Pullback to Higher-Low / Lower-High** (the core
trend-continuation: buy HL in uptrend / sell LH in downtrend on break of the pullback extreme) · Trend exhaustion
(fade after CHoCH) · ★Market-Structure-Shift (CHoCH + displacement → pullback to FVG/OB).

**DATA I track each scan:** candle anatomy (dir/body/wick) · swing H/L · BOS/CHoCH/MSS · ATR + volatility
**compression→expansion** · sessions (Asian/London/NY + **killzones** + NY-lunch) · daily/weekly open · PDH/PDL ·
prev-day VAH/VAL/POC + single prints/LVN/HVN (TPO) · VWAP + bands 1&2 · each zone's lifecycle state.

---

## DISCIPLINE / LESSONS (from the forward tests — do not skip; add new lessons here every time)

### ★ RECALIBRATION (2026-06 — the big correction; READ FIRST). This is a TRADE machine, not a REJECT machine.
- **0 trades = the method failing, not discipline.** Across May 11/12/15 forward walks I took 0–2 trades and
  rejected everything else on perfectionist grounds. **Take good-not-perfect WITH-trend setups:** level + trigger +
  with the regime + R:R ≥ ~1.5 to T1 **with a runner**. R:R and "clean A+" are **sizing/management tools, not reject
  buttons** — wide stop? size DOWN, don't reject. Scale: partial at T1, BE, runner to structure. **A losing trade on
  a valid setup is fine; standing aside all day is the error.**
- **LET THE COMMITTEE VOTE — don't pre-reject.** For scalps use the **relaxed committee**: Risk no-hard-veto +
  Adversary finds no hard-invalidation + main confirms (level+trigger+path+R:R). Full 5-agent panel only for
  large/unclear trades. (I failed by never once convening it — I killed every trade myself first.)
- **HARD-REJECT only the genuinely bad:** counter-trend with no reversal · no level · no trigger · R:R <1.5 even with
  a runner · dead VWAP-chop · mid-balanced-value · first news spike · NY-lunch/dead-time.
- **DAY-TYPE is the master filter — size to it.** Clean **trend-WITH-pullback days = participate / size up** (that's
  where the edge is). **Chop/range days BLEED** — either 0 trades or whipsaw losses (May 15: −240p shorting a
  4511–4588 chop). On chop: fewer/smaller or stand aside WITHOUT guilt; don't force scalps into chop.
- **Stops too tight get wicked on gold — clear the WHOLE swing + ATR buffer, size DOWN.** (May 15: two shorts
  stopped by 8–10pt wicks past +4–5pt stops, then price went my way.) Prefer the **structure/SBS swing extreme** as
  the stop reference, never an arbitrary few-point buffer inside the noise.
- **Breakeven at ~+1R or a cleared minor structure — NOT a fixed +40 pips.** (May 15: a +40-pip BE would have
  scratched both trades at BE on normal noise wicks; BE-at-~1R correctly kept me in.) **And place BE a touch BELOW
  entry / the breakout-or-structure level, NOT exactly at entry** — an exact-entry BE gets nicked by noise wicks.
  (May 18: TP1 long won +120p, but the runner's BE at the 4565 entry was wicked at 4563.71 — 2p — then price bounced
  to 4576; a BE at ~4560, below the breakout level, would have kept the runner alive.)
- **Prefer a LIMIT at the level over market-on-rejection** — better fill, tighter stop, and the moves that just-go
  without you aren't dragged into at a bad price.
- **Pip convention (don't conflate units):** **1.00 price = 10 pips = $1; 100 pips = $10 = 10.0 price points.**
  Gold's normal intraday moves are 250–700+ pips, so a 100-pip ($10) target is MODEST — "not enough room to T1" is
  rarely the blocker on gold; **stop width and chop are.**
- **Two execution modes (UNDER FORWARD-TEST — formalize after results):** **MICRO_SCALP** (1/3m exec, 15m context,
  score 65+, small TP at the nearest level) vs **SCALP_TO_RUNNER** (3/5m exec, 1H/4H context, score 75+, TP1 ≈100
  pips, structure-based TP2, **no T3**). R:R checked to TP1 *with a runner*. **TP1 = the nearest REAL liquidity level;
  use 100 pips as the space/viability filter, NOT a blind fixed exit** (keeps the "T1 at the actual level" lesson).

### ★ BOUNCE-HANDLING after a sharp drop (3 losses paid for this — May 15 ×2, May 18 ×1)
- **DON'T short the FIRST rejection of a sharp-drop/capitulation bounce.** After a hard drop (RSI ≲20, price far
  below VWAP), the bounce **frequently V-reverses the WHOLE way back to VWAP/EMAs (and beyond)** — it is NOT a
  lower-high before continuation. Shorting the first rejection = repeatedly stopped by the V (May 15: 4638→bounce
  stopped me twice; May 18: 4480 capitulation → bounce +550p to VWAP, stopped my 4500 short at 4521, −210p).
- **To short the resumption, REQUIRE:** the bounce **fully resolves** AND rejects a **MAJOR level** (VWAP / EMA
  cluster / broken structure / SBS swing high) AND prints a **confirmed lower-high + a CHoCH *down*** on the exec TF.
  The first stall of a sharp-drop bounce is not enough — wait for the structure break.
- **Better play on a capitulation (RSI <~20): trade the BOUNCE *LONG*** off the low on a reclaim trigger, targeting
  VWAP/the mean — that V-bounce IS the move (it's what actually happened all 3 times). This is the recurring
  "capitulation-low reclaim long" edge (cf. the May-27/28 reviews). Counter to the day-trend, but high-probability
  to the mean; scalp it (partial at VWAP), don't hold for a full reversal unless structure confirms.
- Net: after a sharp drop → either **buy the V-bounce to VWAP**, or **wait for VWAP/EMA rejection + LH + CHoCH** to
  short. Never short the first bounce-rejection.

### Earlier lessons —
- **Order blocks are precise — enter FROM the OB, stop BEYOND it.** (May 26: shorted 4535 below a 4542–4550
  supply OB with stop 4543 *inside* it → price ran up into the OB to fill it, stopped me, then faded as planned.
  −80p on a directionally-correct trade.) Read the OB bounds; enter on the tap+reject; stop past the far edge.
- **Coil/range stops must clear the WHOLE coil + any OB + buffer**, not just the last cap. Tight coils stop-run
  the recent high/low before resolving. A stop one tick past the recent cap is a donation.
- **Set T1 AT the actual nearest-liquidity LEVEL, not a round number beyond it.** (May 26: T1 4520 vs the real
  VA level 4524 — price hit 4521.6 repeatedly and reverted; a 4-pip-greedy target turned a clean win into a
  grind. Put T1 a touch INSIDE the level so you actually get filled.)
- **Day type is everything and you cannot know it at the open.** A clean-looking pullback can chop all day
  (May 13: 2 reasonable longs → scratch + −100p). When in doubt, smaller or no trade.
- **Track fills with DATA, not eyeballing** — TP/SL hit between checks; a later snapshot can misrepresent a
  closed trade (May 20: I misread a +320p winner as stopped). Pull bars-up-to-cursor to know exact fills.
- **No-hindsight only** — decide on bars up to NOW; never use future bars. Then forward-verify.
- **Use ALL the tools consistently** — VWAP and volume confirmation especially (a low-volume support bounce is a
  trap; May-13 loss bought support without volume). Don't skip the order-block / SMC read when one is at the level.
- **Sample, not anecdote** — one good day (+320) doesn't prove edge; one bad day (−100/−80) doesn't disprove it.
  Judge across many days, net of ~3p/trade cost.

## OPERATIONAL NOTES — replay/chart stability (LEARNED THE HARD WAY — follow exactly)
- **Repeated timeframe switching DESTABILISES the replay** — it silently STOPS and the chart reverts to LIVE
  data (wrong date/prices). So use the **frequency-matched refresh cadence** (STEP 1): 15m every 15m, 1h every
  hour, 4h every 4h, TPO 30m once at session start. Otherwise **stay on 3m**. Don't refresh all HTFs every 15m.
- **After ANY TF switch or replay action, VERIFY before trusting data:** check `replay status` shows
  `is_replay_started: true` with a `current_date` on the right day, and that `ohlcv` bars are the expected date
  + 3-min spacing. If you see live/wrong-date prices → the replay died → `replay stop` then `replay start --date`
  again and step back to your point.
- **"Continue your last replay?" modal → dismiss with `ui_keyboard Escape`, NOT the "Continue" button.** After
  `replay start --date`, a modal pops up; clicking **Continue RELOADS the OLD saved session** (wrong date). Escape
  keeps your new start. (If it already reverted: `replay stop` → `replay start --date` → Escape.)
- **`data_get_study_values` + SMC/SBS pine data can FREEZE stale** on the prior frame for a whole replay session
  (e.g. VWAP/RSI not matching price). **OHLCV + screenshots stay reliable** — cross-check; if frozen, read
  EMA/VWAP/RSI VISUALLY off a full-region screenshot. (Stepping once sometimes unfreezes it; sometimes not.)
- **Symbol switching needs the app FOREGROUNDED** and is unreliable from rapid back-to-back scripts; drive switches
  one at a time and verify the symbol before trusting a read. `scalp_fast.py` has **no symbol guard** — it will
  silently read the wrong instrument if the chart didn't switch (refresh_zones.py aborts correctly; scalp doesn't).
- **`indicator toggle --visible false` does NOT reliably repaint** (the study often stays visible). To actually
  remove a heavy indicator from the 3m chart, **`indicator remove <id>`** it. BUT — **do NOT remove COMMUNITY
  indicators you'll need next session** (SMC, TPO): they CANNOT be re-added via the API (only the user's manual
  favorites). KEEP TPO/SMC on the chart; just don't switch to their TF except on the refresh cadence. (Removing
  TPO once cost a re-add the user had to do by hand.)
- **Foreground the app** (`osascript -e 'tell application "TradingView" to activate'`) before TF switches/HTF
  screenshots — backgrounded windows don't repaint, giving stale captures.
- **HTF screenshots lag the TF switch (stale frame = shows the PREVIOUS TF).** Fix = **double-capture**: switch
  TF, sleep ~6s, take a FIRST throwaway screenshot (triggers the repaint), sleep ~3s, take the SECOND = the fresh
  one. Verify with md5 that consecutive-TF shots DIFFER. (3m renders fine via replay-step; only TF *switches* lag.)
- **Screenshots: `--region full` only** (price + time axes visible), incl. your own review shots.
- **Manage open trades with data, not images** — pull `ohlcv` up to the cursor each checkpoint to know exact
  TP/SL fills (intra-checkpoint fills are invisible to a periodic screenshot).

## Reading the indicators (practical — both are READ, not computed)
- **SMC = Smart Money Concepts indicator, read on 15m / 1h / 4h** (HTF context). Visible on chart; boxes/labels
  via `data_get_pine_*` with `study_filter="Smart Money"`. Switch TF 15m→1h→4h, read each, then restore 3m.
- **VA = TPO indicator, read on 30m, ONE call** → `data_get_pine_lines` verbose `study_filter="TPO"`: yellow POC,
  lime VAH/VAL pairs for all visible prior sessions. Restore the 3m execution TF after.
- Execution is **3m** (changed from 5m, 2026-06). SMC/VA are HTF context layered onto the 3m read; you do NOT trade off SMC/TPO on 3m.
- **PERFORMANCE: hide SMC + TPO on the 3m execution chart** (they're heavy and irrelevant to 3m) — keep only
  VWAP/EMA/Auto-Trendlines/Volume/RSI for fast 3m screenshots. **Show SMC when reading 15m/1h/4h, show TPO when
  reading 30m, then hide both again and restore 3m.** Toggle via `indicator toggle <id> --visible true/false`
  (study ids rotate — resolve fresh from `state` each time).
- All chart screenshots must be **full-region** (price + time axes visible).
