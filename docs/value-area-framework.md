# Previous Value Area (VAH/VAL/POC) Trading Framework

**Canonical decision rules for using value areas in the engine grading AND the AI review.** The value-area
levels themselves (POC/VAH/VAL per prior session) are computed TPO-faithfully (time-at-price + 70%-from-POC)
and stored as data — see [[prior-day-value-areas]] and `docs/zones-and-confluence.md`. This file is the
*how to act on them* layer: when a level matters, what confirms a trade there, and when a level is dead.
The AI (and the grade logic) should consult these rules when a signal sits at a value-area level.

## Definitions
- **VAH** — upper boundary of the previous session's value area.
- **VAL** — lower boundary of the previous session's value area.
- **POC** — price level with the highest traded volume / TPO count.
- **Acceptance** — market AGREES with prices beyond a level. Signalled by ANY of: multiple candle closes
  beyond the level · TPOs build beyond it · volume builds beyond it · retests hold beyond it · new value
  develops beyond it.
- **Rejection** — market DISAGREES beyond a level. Signalled by: price quickly returns through the level ·
  excess tails · strong delta imbalance · footprint absorption · failure to build TPOs beyond it.

## Priority order (most important first)
1. Current-session VAH/VAL
2. Previous-day VAH/VAL
3. Untested VAH/VAL from older sessions
4. Weekly profile levels
5. Monthly profile levels

Older levels lose importance after repeated testing (see Rule 7).

## Rule 1 — Trend up, looking for longs
If structure is **bullish**, search prior sessions for: VAL below price · POC below price · VAH that was
broken AND accepted. **Valid long locations:** previous VAH as support · previous POC as support ·
previous VAL after a strong rejection. **Confirmation:** rejection candle · footprint absorption ·
positive delta · upward BOS. **Invalidation:** acceptance below the level · new value developing below it.

## Rule 2 — Trend down, looking for shorts
If structure is **bearish**, search prior sessions for: VAH above price · POC above price · VAL that was
broken AND accepted. **Valid short locations:** previous VAL as resistance · previous POC as resistance ·
previous VAH after a strong rejection. **Confirmation:** rejection candle · negative delta · footprint
absorption · downward BOS. **Invalidation:** acceptance above the level · new value developing above it.

## Rule 3 — Open ABOVE previous value (Open > prev VAH)
Market is attempting price discovery higher.
- **Bullish path:** pullback into VAH → rejection from VAH → acceptance above VAH → **long**.
  Target hierarchy: current-session POC → single prints → poor high → weekly VAH.
- **Failure:** acceptance back inside value → rotation toward previous POC → **avoid longs, expect balance.**

## Rule 4 — Open BELOW previous value (Open < prev VAL)
Market is attempting price discovery lower.
- **Bearish path:** pullback into VAL → rejection from VAL → acceptance below VAL → **short**.
  Target hierarchy: current-session POC → single prints → poor low → weekly VAL.
- **Failure:** acceptance back inside value → rotation toward previous POC → **avoid shorts, expect balance.**

## Rule 5 — Inside-value open (VAL < Open < VAH)
Balanced market. Expect rotation between VAH and VAL with attraction toward POC.
**Strategy:** fade the extremes — long near VAL, short near VAH. Do NOT chase moves from the center.

## Rule 6 — When a previous VA level becomes INVALID
A previous VAH or VAL is invalid when **ANY TWO** of these occur:
1. Two or more candle closes beyond the level.
2. A retest succeeds beyond the level.
3. A new session develops value beyond the level.
4. POC migrates beyond the level.
5. Market spends more than 30% of a session beyond the level.

Once invalid: do not use as S/R · do not trade the first touch · remove from active levels.

## Rule 7 — Multi-day selection
When price sits between several historical profiles: find the nearest **active** level above (→ resistance)
and the nearest **active** level below (→ support). **Skip** levels that have: already been accepted
through · been tested more than 3 times · lost their associated POC · been completely traded through by a
later profile. Always prefer the most recent valid level.

---

## How this maps onto the engine / AI review (implementation notes)
- **Levels:** POC/VAH/VAL per prior session are **read from the TPO indicator** (`tpo.py`, by line color)
  and stored as data in the zone file — we use the indicator, not a reimplementation. Reliable live;
  best-effort in backtest (the indicator's lines don't track the replay cursor — to revisit).
- **Structure (Rules 1–2):** bullish/bearish bias = the engine's existing regime / EMA-stack trend.
- **Open vs value (Rules 3–5):** compare the session open to the *previous-day* VAH/VAL to pick the regime
  (discovery-up / discovery-down / balanced) before grading a setup.
- **Acceptance/Rejection:** approximate with what we can read — closes beyond the level (acceptance),
  rejection wicks / quick return (rejection); delta/footprint cues are aspirational (not in our data yet).
- **Invalidation (Rule 6) & selection (Rule 7):** track per-level test count + closes-beyond so a dead VA
  level stops adding confluence and isn't traded on first touch. Mirrors our zone freshness/decay model.
- **Confluence "+":** a signal at a *valid* VAH/VAL/POC in the right context (per Rules 1–5) is a grade
  bump, like SMC/zone confluence; a signal at an *invalid* level (Rule 6) gets no credit.
