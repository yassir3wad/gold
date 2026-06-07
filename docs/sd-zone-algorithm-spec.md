# Support/Resistance + Supply/Demand Zone Algorithm — Reference Spec

> Reference specification for the classic zone system. **What is implemented today** lives in `zones_sd.py`
> (+ `build_classic_zones`, the shared drawn==traded builder) and is wired into `scalp_fast` grading — see
> `docs/zones-and-confluence.md` §3.5. **Implemented:** zone geometry, Key Levels (BOS + impulse + never
> wicked through), touch decay, broken/flip, position-based buy/sell, 4h-covers-1h dedup, the confluence
> merge + KL top-tier grade boost. **Not yet (gaps to revisit):** the full `NEW/UNTESTED/TESTED_ONCE/
> MITIGATED/BROKEN/FLIPPED` state machine, the additive 0–100 score rubric (§15 below), and a hard
> *rejection-confirmation* entry gate (we currently confirm via the existing pattern/trigger families).

---

## Purpose

Detect high-probability buy and sell zones using: 4H/1H candle bodies, big high-volume candles, swing
highs/lows, demand/supply zones, break-and-retest behavior, rejection confirmation. For XAUUSD, gold
futures, and liquid FX (EURUSD, GBPUSD, USDJPY).

## 1. Core Concept
A strong zone forms when price shows an institutional reaction from a specific area. Valid when: (1) price
reacts strongly, (2) the reaction creates displacement, (3) the move breaks structure or rejects strongly,
(4) price later returns to the zone, (5) the zone still holds. **Not every S/R is tradable** — a zone
becomes tradable only when price returns and confirms rejection.

## 2. Timeframe Priority
Higher timeframe first: Daily → 4H → 1H → 15M (entry refinement) → 5M (trigger).
- Intraday: bias = 4H + 1H, entry = 15M/5M.  Scalping: bias = 1H, entry = 5M/1M.

## 3. Big Candle Detection
- **Bullish big**: close > open; body ≥ 1.5× avg body (20); volume ≥ 1.3× avg volume (20); closes near high.
- **Bearish big**: close < open; body ≥ 1.5× avg body; volume ≥ 1.3× avg volume; closes near low.
- Forex/CFD without real volume → use tick volume.

## 4. Support Zone from Big Bullish Candle
`Support Zone High = bullish candle open`, `Low = bullish candle low` (conservative: high = body midpoint).
Area below the body/open of a big bullish candle is possible demand/support.

## 5. Resistance Zone from Big Bearish Candle
`Resistance Zone High = bearish candle high`, `Low = bearish candle open` (conservative: low = body midpoint).

## 6. Demand Zone from Swing Low
Swing low: low < lows of N before AND N after (N=2 scalping, 3–5 for 1H/4H). Valid only if price left with
strong bullish candles causing bullish BOS / displacement, zone not fully broken. Boundaries = the **last
bearish candle before the bullish move** (high/low); else the swing-low candle open→low.

## 7. Supply Zone from Swing High
Mirror of §6: last **bullish** candle before the bearish move; else swing-high candle high→open.

## 8. Break of Structure
Bullish BOS = close above previous swing high; bearish BOS = close below previous swing low. Scoring: caused
BOS → strong; only bounce → medium; no displacement → ignore.

## 9. Zone States
`NEW` (just created) · `UNTESTED` (strongest — price hasn't returned) · `TESTED_ONCE` (returned + rejected,
still valid) · `MITIGATED` (returned ≥2×, weaker) · `BROKEN` (closed fully beyond — don't trade original
direction) · `FLIPPED` (broken support→resistance / resistance→support).

## 10. Invalidation
- Demand/support invalid: close below zone low (same TF) / two closes below / accept-below then retest as
  resistance.
- Supply/resistance invalid: close above zone high / two closes above / accept-above then retest as support.

## 11. Buy Setup (demand/support)
Long only when: price returns to a valid zone (NEW/UNTESTED/TESTED_ONCE) + rejects + bullish confirmation +
R:R ≥ 1:2. Bullish rejection = engulfing / long lower wick / close back above zone high / minor bullish BOS
(LTF) / double bottom in zone / sweep-below-then-reclaim. Stop below zone low (+buffer: XAUUSD 0.5–2.0,
majors 2–5 pips). Targets: nearest resistance → prev swing high → prev VAH/POC/VWAP/session high.

## 12. Sell Setup (supply/resistance)
Mirror of §11 (bearish rejection, stop above zone high, targets to support/swing low/VAL/POC/session low).

## 13. Support→Resistance flip
Close below support, retest from below, rejects → `SUPPORT_FLIP_SHORT` (stop above flipped zone, target next
demand/swing low).

## 14. Resistance→Support flip
Close above resistance, retest from above, holds → `RESISTANCE_FLIP_LONG` (stop below flipped zone, target
next supply/swing high).

## 15. Zone Strength Score (0–100)
`+25` HTF (4H/Daily) · `+20` caused BOS · `+20` strong displacement · `+15` high-volume impulse · `+15`
untested · `+10` VAH/VAL/POC confluence · `+10` VWAP/band confluence · `+10` PDH/PDL/session confluence ·
`+10` clean rejection on retest.
Subtract: `-20` tested >1× · `-25` mid-value · `-30` opposite strong zone too close · `-50` broken · `-30`
R:R < 1:2.
Approval: 80–100 high probability · 65–79 tradable with confirmation · 50–64 wait · <50 reject.

## 16. Detection (pseudocode)
Swings, big candles, big-candle zones, swing-low demand / swing-high supply, zone touch, bullish/bearish
rejection-from-zone, signal generation — see the original spec body (mirrors `zones_sd.py` functions:
`is_swing_*`, `big_candle`, `demand_zone`/`supply_zone`, `find_*_zones`, `touches`, `caused_bos`,
`mark_key_levels`, `sr_levels`).

## 17. AI Review Rules
Approve only if: zone from 1H/4H/Daily · not broken · untested or tested once · clear rejection · no strong
opposite zone before T1 · R:R ≥ 1:2 · agrees with HTF bias or clear reversal structure · not chopping VWAP ·
near a meaningful level. Reject if: zone too wide · tested many times · closed fully through · mid-value ·
stop too large · opposite zone too close · no confirmation candle · no BOS/structure.

## 18. Output contract (Python → AI)
`{signal, symbol, timeframe, higher_timeframe_zone, zone_type, zone_source, zone_high, zone_low, zone_state,
current_price, entry, stop_loss, target_1, target_2, risk_reward, bos_confirmed, rejection_confirmed,
volume_condition, vwap_position, nearest_opposite_zone_distance, python_confidence}` →
AI returns `{decision(APPROVE|REJECT|WAIT), direction, entry, stop_loss, target_1, target_2, reason, risk_warning}`.

## 19. By market
- **Gold/XAUUSD**: 4H big-candle zones, 1H swing S/D, liquidity sweep into S/D, NY retests, VWAP confluence.
  Spikes through zones before reversing → require **sweep + reclaim + BOS**.
- **EURUSD**: cleaner 1H/4H S/R, clean retests, channel S/R, London reactions (slower).
- **GBPUSD**: liquidity sweeps, S/D retests, London fakeouts, PDH/PDL sweeps — require reclaim confirmation.
- **USDJPY**: trend pullbacks, S/R flips, 4H continuation, VWAP pullbacks — don't fight strong-trend zones.

## 20. Final rule
A zone is not a trade. A zone becomes a trade only when: price returns + zone still valid + rejection
appears + structure confirms + R:R acceptable. Any part missing → **NO TRADE**.
