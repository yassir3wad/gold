# Gold Trading AI Strategy — Without Footprint / Bookmap

**This is the canonical strategy the AI review applies to gold value-area signals.** It supersedes the
generic framework (`value-area-framework.md`) for *execution* because it uses **only data we actually have**
(no footprint/delta/DOM) and gives concrete setups + a required output format. The engine emits the inputs
(prev VAH/VAL/POC + single prints from `va_store`, VWAP+bands, structure, session/prev H/L); the AI applies
the rules below and returns the structured output.

## Available data (use ONLY these)
Price action · market structure · **previous-day VAH / VAL / POC** · current-session **VWAP** + bands ·
previous high/low · session high/low.
**Do NOT use:** footprint · delta · absorption · icebergs · DOM · Bookmap liquidity. (We have none of these —
acceptance/rejection is judged purely from candles/closes/wicks.)

## Main rule
VAH/VAL are **not** automatic S/R. They are valid **only if price reacts clearly from them** (rejection).

## VWAP bias
- Price **above** VWAP → **bullish** bias, prefer longs.
- Price **below** VWAP → **bearish** bias, prefer shorts.
- Price **crossing VWAP repeatedly** → **neutral**, avoid trend trades.

## Previous value-area logic (by where the session opened vs prev value)
- **Open above prev VAH** (bullish discovery): long valid only if price pulls back to prev VAH, VAH **holds
  as support**, a **bullish rejection candle** forms, and price **breaks minor structure up**. If price
  **accepts back inside** value → VAH invalid → expect rotation to prev POC → **do not long**.
- **Open below prev VAL** (bearish discovery): short valid only if price pulls back to prev VAL, VAL **holds
  as resistance**, **bearish rejection candle**, **breaks minor structure down**. Accept back inside → VAL
  invalid → rotation to POC → **do not short**.
- **Open inside prev value** (balanced): buy near VAL only after **bullish rejection**; sell near VAH only
  after **bearish rejection**; **avoid POC and the middle of value**.

## Acceptance rule (level becomes INVALID — "accepted")
A prev VAH/VAL is invalid when **≥ 2** occur: (1) two candles close beyond it · (2) price retests from the
other side and holds · (3) price spends **>30 min** beyond it · (4) price moves from the level toward POC
**without rejection** · (5) the current session builds value on the other side.
If invalid → **don't trade first touch**, don't use as S/R, mark **Accepted**.

## Rejection rule (level is VALID)
- **Bullish:** wick **below** the level · candle **closes back above** · next candle **breaks the rejection
  candle's high**.
- **Bearish:** wick **above** the level · candle **closes back below** · next candle **breaks the rejection
  candle's low**.

## Long setup (ALL required)
1. Above VWAP, or reclaiming VWAP · 2. At prev **VAL**, prev **POC**, or a **flipped VAH** · 3. Bullish
rejection · 4. Bullish **BOS** · 5. R:R ≥ **1:2**.
**Targets:** T1 VWAP → T2 prev POC → T3 prev VAH / session high. **Stop:** below the rejection wick (or below
an invalidated VAL).

## Short setup (ALL required)
1. Below VWAP, or rejecting VWAP · 2. At prev **VAH**, prev **POC**, or a **flipped VAL** · 3. Bearish
rejection · 4. Bearish **BOS** · 5. R:R ≥ **1:2**.
**Targets:** T1 VWAP → T2 prev POC → T3 prev VAL / session low. **Stop:** above the rejection wick (or above
an invalidated VAH).

## Skip conditions (NO TRADE)
Middle of value · chopping around VWAP · no BOS after rejection · level already accepted through · stop too
large · R:R < 1:2 · price between VWAP and POC with no clear direction.

## Required AI output format
```
Bias: Bullish / Bearish / Neutral
Previous VAH:
Previous VAL:
Previous POC:
VWAP Position:
Current Structure:
Nearest Valid Level:
Level State: Untested / Rejected / Accepted / Flipped
Trade Decision: LONG / SHORT / NO TRADE
Entry:
Stop Loss:
Target 1:
Target 2:
Reason:
```

## How the engine supports this (what's emitted vs judged)
- **Emitted by the engine** (so the AI judges, not recomputes): prev VAH/VAL/POC + single prints (`va_store`),
  VWAP + bands, EMAs/structure, session/prev H/L, the open-vs-value regime, and the **Level State**
  (Untested/Rejected/Accepted/Flipped — the acceptance/rejection logic, Rules 6/7, coded in `va_state.py`).
- **Judged by the AI:** the final LONG/SHORT/NO-TRADE decision, BOS confirmation quality, and the structured
  output above.
