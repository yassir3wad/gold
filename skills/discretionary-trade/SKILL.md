---
name: discretionary-trade
description: Trade XAUUSD/forex discretionarily as the AI decision-maker (no coded strategy). Top-down multi-TF read (SMC indicator + 30m TPO prior-day value areas + VWAP + EMAs + Auto-Trendlines + structure), classify the day type, find a signal at a meaningful level, score confluence, approve/reject, then execute and manage with real stops. Use for replay study, forward blind tests, and live discretionary calls.
---

# Discretionary AI Trading — XAUUSD / Forex

**You are the trader.** No python detects the signal for you; you read the chart top-down, recognise the
setup, score it, decide, execute, and manage. This skill is the rulebook distilled from the XAUUSD/Forex
Signal Execution Manual (100 signals), the value-area + VWAP frameworks, and the day-type/transition lessons
from the replay studies. Not financial advice; for systematic analysis and disciplined review.

Convention: **1.00 in XAUUSD = 10 pips** (e.g. 4578→4566 = 12.0 = 120 pips). Minimum R:R **1:2**.

---

## THE LOOP (every decision)
1. **CONTEXT** — build the multi-TF picture and the level map (once at session start; refresh ~hourly or on a regime shift).
2. **DAY TYPE** — classify the regime; it sets which playbook is allowed.
3. **LOCATION** — is price AT a meaningful level? If mid-range/no-man's-land → **WAIT**.
4. **SIGNAL** — does a recognised setup trigger at that level, in the allowed direction?
5. **SCORE** — confluence + R:R. Approve / Wait / Reject.
6. **EXECUTE & MANAGE** — entry, stop, targets, then breakeven / trail / stand-aside.

Re-check on a fixed cadence (e.g. every 15m of price) AND when price reaches a mapped level.

---

## STEP 1 — CONTEXT (top-down, build the level map)

Read **4H → 1H → 15m** for bias and structure; **5m** is execution only.

Gather and mark these levels (the "map") — **read them off the indicators; never compute them yourself:**
- **SMC = the Smart Money Concepts (LuxAlgo) indicator, read on the HIGHER timeframes 15m / 1h / 4h.** SMC is
  HTF *context*, not a 5m execution tool. On each of 15m, 1h, 4h read: order blocks (supply/demand boxes),
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
5m EMA pack. Once repeated tests of the session extreme **fail to expand** and price slips back through the EMA
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

**Hard rejects (any one):** R:R < 1:2 · no clear invalidation/stop · entry into a strong opposite level ·
level already accepted through · chopping around VWAP · setup old/over-tested/unclear · mid-value no-edge.

**Level validity (acceptance kills a level):** a prev VAH/VAL/range edge is INVALID once ≥2 of: two closes
beyond it · a retest holds beyond it · >30 min spent beyond it · POC migrates beyond it · new value builds
beyond it. Invalid → don't trade the first touch, drop it from the map.

---

## STEP 6 — EXECUTE & MANAGE

- **Entry:** on the trigger (break of the rejection candle / BOS retest) — at the level, not chasing mid-move.
- **Stop:** beyond the invalidation (other side of the OB/zone/wick + buffer). Define it before entry.
- **Targets:** T1 = nearest liquidity (VWAP / POC / VAH-VAL / PDH-PDL / 2R); T2 = next structure. R:R ≥ 1:2.
- **Manage:** move to **breakeven** once price approaches T1 and stalls (this turns rejected-at-resistance trades
  into scratches, not losses). Trail behind structure on trend days. **Stand aside** after 2 failed trades or in
  confirmed chop — over-trading a chop day is how small losses become big ones.

**Output each decision in this form:**
```
Bias: Bullish/Bearish/Neutral | Day type: Trend/Range/Dead/Reversal
Nearest valid level (and state: Untested/Rejected/Accepted/Flipped):
VWAP position:  | Open vs prev value:
Signal: <name> | Direction: LONG/SHORT/WAIT
Entry / Stop / T1 / T2 / R:R / Confluence score:
Reason:
```

---

## DISCIPLINE / LESSONS (from the forward tests — do not skip)
- **Day type is everything and you cannot know it at the open.** A clean-looking pullback can chop all day
  (May 13: 2 reasonable longs → scratch + −100p). When in doubt, smaller or no trade.
- **Track fills with DATA, not eyeballing** — TP/SL hit between checks; a later snapshot can misrepresent a
  closed trade (May 20: I misread a +320p winner as stopped). Pull bars-up-to-now to know exact fills.
- **No-hindsight only** — decide on bars up to NOW; never use future bars. Then forward-verify.
- **Use ALL the tools consistently** — VWAP and volume confirmation especially (a low-volume support bounce is a
  trap). The May-13 loss bought support without volume confirmation.
- **Sample, not anecdote** — one good day (+320) doesn't prove edge; one bad day (−100) doesn't disprove it.
  Judge across many days, net of ~3p/trade cost.

## Reading the indicators (practical — both are READ, not computed)
- **SMC = Smart Money Concepts indicator, read on 15m / 1h / 4h** (HTF context). Visible on chart; boxes/labels
  via `data_get_pine_*` with `study_filter="Smart Money"`. Switch TF 15m→1h→4h, read each, then restore 5m.
- **VA = TPO indicator, read on 30m, ONE call** → `data_get_pine_lines` verbose `study_filter="TPO"`: yellow POC,
  lime VAH/VAL pairs for all visible prior sessions. Restore the 5m execution TF after.
- Execution is **5m**. SMC/VA are HTF context layered onto the 5m read; you do NOT trade off SMC/TPO on 5m.
- All chart screenshots must be **full-region** (price + time axes visible).
