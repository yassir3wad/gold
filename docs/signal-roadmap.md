# Signal Roadmap & Reference (XAUUSD / Forex)
Version: 1.1 — repurposed as a ROADMAP, not a build list.

**How to use this file.** This is a 100-signal *taxonomy* and a prioritized *roadmap* — NOT a to-do list. Our
bottleneck is **edge**, not signal coverage (the 1m backtest showed gross/trade < spread), so we add new
detectors **rarely and only after validating what we have**. Its real value: (1) the **AI approval checklist**
(now merged into the live review — see `scalp_fast` `--review` output), (2) a **shared vocabulary**, and (3) a
**menu** to cherry-pick from after the 5m backtest. The full signal list below is the reference appendix.

## Crosswalk — what we ALREADY have (don't rebuild)
Most of the "highest quality" signals map onto our existing 13 strategies + SMC/VA/trendline layers:

| Roadmap signal(s) | Our implementation |
|---|---|
| 16/17 VAH/VAL Rejection · 18/19 VAH/VAL Flip | `va_reject` (entry #13) + `va_state` Level State (Rejected/Flipped/Accepted) |
| 6 Liquidity Sweep · 14 Stop Hunt | `liquidity_sweep` |
| 9/10 PDH/PDL Sweep · 11/12 Session Sweep · 61–63 London sweeps | `session_sweep` (time-gated pools) |
| 59 Asian Range Breakout · 60 Asian Fakeout | `session_breakout` + `session_sweep` |
| 29–32 VWAP Reclaim/Reject/Pullback | `vwap` strategy (+ bands) |
| 35 VWAP Chop Filter · 66 NY Lunch | `range_filter` (Kaufman ER) + session filter |
| 39/40 Double Top/Bottom | `double_top_bottom` |
| 72/75/76 Failed/False Break | `crt` (Candle Range Theory) |
| 1 KLZ Retest · 71/77 Break-and-retest | `break_retest` + `zone_bounce` |
| 5 FVG · 2 Order Block · 89/91–100 BOS/CHoCH/MSS | **SMC confluence** (LuxAlgo boxes/structure, read live) |
| 57 Channel Breakout · 45/46 Flags · fib | `patterns.py` (4h+daily HTF context) |
| multi-TF trend context | **Auto-Trendlines** confluence (4h/1h/15m) |
| Universal AI Approval Checklist · Python Confidence | merged into `--review` output + `confidence.py` (0–10) |

**Partial / candidate to ADD after validation** (suit gold + our data): 18/19 VAH/VAL Flip as a *first-class*
trigger (half-there via `va_reject` flipped states) · 100 Market Structure Shift · 20/21 Failed Auction.

**Skip for now — data we don't reliably have:** 26 Single Prints (harvest disabled) · 27/28 LVN/HVN ·
25 Poor High/Low · 36/37 Anchored/Weekly VWAP · anything needing footprint/delta/DOM.

## Companion: detailed execution reference
[`signal-roadmap-detailed.md`](signal-roadmap-detailed.md) — per-signal setup/trigger/execution/invalidation +
Python detection hints for all 100, plus the **Confluence Score Guide** and the **AI Review JSON** schema.

**Adopted from it:**
- **AI approval checklist** — live in `scalp_fast --review` output (every held trade).
- **APPROVE / REJECT / WAIT** decision vocabulary — the review now asks the AI for one of the three + a
  one-line reason citing the checklist & confidence (WAIT = let it expire if a cleaner entry is one candle away).
- **AI Review JSON** (canonical decision schema): `{decision, direction, bias, entry, stop_loss, target_1,
  target_2, risk_reward, confidence, reason}`.

**TODO (pending 5m backtest) — Confluence Score Guide penalties into `confidence.py`:** today `confidence.py`
only *adds*; the guide also *subtracts* (−30 mid-value · −25 accepted-through · −20 over-tested · −20 into
opposing level · −20 VWAP chop). Most are already hard filters, but folding them as score deductions would let
confidence reflect near-misses that pass the filters. Hold the reweight until the backtest justifies it.

---

> Original spec below (reference appendix).

Purpose: Python detects mechanical signals, then an AI review layer approves, rejects, or waits. This file is designed for Gold/XAUUSD first, but includes guidance for major forex pairs such as EURUSD, GBPUSD, and USDJPY.

Important: This is a technical strategy specification for research and automation. It is not financial advice. Always forward-test and back-test before live use.

## Global Architecture
```text
Python = signal detection engine
AI = context review and trade approval engine
Broker/execution module = only acts after AI approval
```

## Required Core Data
- OHLC candles for selected timeframes.
- Previous day high/low/close.
- Session high/low: Asian, London, New York.
- VWAP and VWAP bands if available.
- Market Profile levels if available: VAH, VAL, POC.
- Swing highs/lows for BOS and CHOCH detection.
- ATR for volatility and stop sizing.

## Universal AI Approval Checklist
Approve only when all are true:
1. Signal is near a meaningful level: KLZ, VAH, VAL, POC, VWAP, PDH, PDL, session high/low, FVG, or channel/range boundary.
2. Structure is aligned or has shifted: BOS, CHOCH, HH/HL, LL/LH.
3. Risk/reward is at least 1:2.
4. Stop loss is logical and not too wide.
5. Price is not in the middle of value/chop.
6. There is no strong opposing level directly before target 1.
7. Session is appropriate: London and New York are preferred for Gold and forex majors.
8. Signal is fresh: avoid old zones tested many times.

[//]: # (## Universal Execution Template)

[//]: # (```json)

[//]: # ({)

[//]: # (  "signal_name": "",)

[//]: # (  "symbol": "XAUUSD",)

[//]: # (  "timeframe": "M5/M15",)

[//]: # (  "direction": "LONG/SHORT",)

[//]: # (  "entry_type": "market_after_confirmation | limit_retest | stop_breakout",)

[//]: # (  "entry_price": 0,)

[//]: # (  "stop_loss": 0,)

[//]: # (  "target_1": 0,)

[//]: # (  "target_2": 0,)

[//]: # (  "risk_reward": 0,)

[//]: # (  "confidence": 0,)

[//]: # (  "context": {)

[//]: # (    "structure": "bullish/bearish/neutral",)

[//]: # (    "vwap_position": "above/below/at",)

[//]: # (    "value_area_position": "inside/above/below",)

[//]: # (    "nearest_level": "",)

[//]: # (    "session": "asian/london/ny")

[//]: # (  })

[//]: # (})

[//]: # (```)

## Recommended Implementation Phases
Phase 1 - Highest quality: 1 Key Level Zone Retest, 6 Liquidity Sweep, 9 Previous Day High Sweep, 10 Previous Day Low Sweep, 16 Previous VAH Rejection, 17 Previous VAL Rejection, 20 Failed Auction Above VAH, 21 Failed Auction Below VAL, 29 VWAP Reclaim Long, 30 VWAP Rejection Short, 5 Fair Value Gap Fill, 45 Bull Flag, 46 Bear Flag, 57 Channel Breakout, 39 Double Top, 40 Double Bottom.

Phase 2 - Session edge: 59 Asian Range Breakout, 60 Asian Range Fakeout, 61 London Open Sweep, 62 London High Sweep in NY, 63 London Low Sweep in NY, 64 NY Open Manipulation, 65 NY AM Continuation, 68 Daily Open Retest, 70 Killzone Liquidity Sweep.

Phase 3 - Classic patterns: 54 Rectangle Breakout, 55 Rectangle Reversal, 52 Rising Wedge, 53 Falling Wedge, 43 Head and Shoulders, 44 Inverse Head and Shoulders, 49 Ascending Triangle, 50 Descending Triangle, 41 Triple Top, 42 Triple Bottom.

## Full Signal List

### Institutional/SMC

| # | Signal | Category | Description | Gold/XAUUSD | Forex Majors | Best Use | Execution Details |
|---|---|---|---|---|---|---|---|
| 1 | Key Level Zone Retest | Institutional/SMC | Retest a zone that created displacement and BOS. | Excellent | Excellent | Intraday | Trade from the zone after rejection and minor BOS. Entry on break of rejection candle or retest. Stop beyond zone. Targets next liquidity/POC/VAH/VAL. |
| 2 | Order Block Retest | Institutional/SMC | Last opposite candle before strong displacement and BOS. | Excellent | Excellent | Intraday/Swing | Enter after price returns to OB and rejects. Stop beyond OB. Target previous swing high/low, POC, or liquidity. |
| 3 | Breaker Block Retest | Institutional/SMC | Failed order block that flips direction after structure breaks through it. | Excellent | Very Good | Intraday | Trade retest of failed block from opposite side. Stop beyond breaker. Target next structure/liquidity. |
| 4 | Mitigation Block Retest | Institutional/SMC | Price returns to the origin of displacement to fill remaining institutional orders. | Very Good | Very Good | Intraday | Enter only after reaction. Stop beyond zone. Target origin high/low and next liquidity. |
| 5 | Fair Value Gap Fill | Institutional/SMC | Three-candle imbalance where price left inefficiently and later returns. | Excellent | Excellent | Scalping/Intraday | Enter after partial/50% fill plus rejection. Stop beyond gap. Target FVG origin, opposing liquidity, or VWAP. |
| 6 | Liquidity Sweep | Institutional/SMC | Price takes a visible high/low and quickly reclaims it. | Excellent | Excellent | Scalping | Enter after reclaim + BOS. Stop beyond sweep wick. Target range midpoint, POC, or opposite liquidity. |
| 7 | Equal Highs Sweep | Institutional/SMC | Sweep above equal highs then reject. | Excellent | Excellent | Scalping | Short after close back below equal highs and bearish BOS. Stop above sweep wick. Target nearest support/VAL/POC. |
| 8 | Equal Lows Sweep | Institutional/SMC | Sweep below equal lows then reject. | Excellent | Excellent | Scalping | Long after close back above equal lows and bullish BOS. Stop below sweep wick. Target nearest resistance/VAH/POC. |
| 9 | Previous Day High Sweep | Institutional/SMC | Sweep PDH then reverse lower. | Excellent | Very Good | Intraday | Short after close back below PDH and bearish BOS. Stop above sweep. Target POC/VAL/PDL. |
| 10 | Previous Day Low Sweep | Institutional/SMC | Sweep PDL then reverse higher. | Excellent | Very Good | Intraday | Long after close back above PDL and bullish BOS. Stop below sweep. Target POC/VAH/PDH. |
| 11 | Session High Sweep | Institutional/SMC | Sweep current session high and reject. | Excellent | Very Good | Scalping | Short after reclaim below session high and minor BOS. Stop above sweep. Target VWAP/session midpoint. |
| 12 | Session Low Sweep | Institutional/SMC | Sweep current session low and reject. | Excellent | Very Good | Scalping | Long after reclaim above session low and minor BOS. Stop below sweep. Target VWAP/session midpoint. |
| 13 | Trendline Liquidity Sweep | Institutional/SMC | Price breaks obvious retail trendline then reverses. | Very Good | Very Good | Scalping | Enter after false break and BOS back inside structure. Stop beyond sweep. Target opposite side of channel/range. |
| 14 | Stop Hunt Reversal | Institutional/SMC | Fast spike through a level then strong reclaim. | Excellent | Very Good | Scalping | Enter only after reclaim and structure shift. Stop beyond spike. Target VWAP or next liquidity. |
| 15 | Displacement Continuation | Institutional/SMC | Strong impulse, small pullback, continuation. | Excellent | Excellent | Intraday | Trade shallow pullback to FVG/OB/VWAP with BOS continuation. Stop below pullback. Target measured move. |

### Market Profile

| # | Signal | Category | Description | Gold/XAUUSD | Forex Majors | Best Use | Execution Details |
|---|---|---|---|---|---|---|---|
| 16 | Previous VAH Rejection | Market Profile | Price rejects from previous Value Area High. | Excellent | Good | Intraday | Short after wick above VAH, close below, then minor bearish BOS. Stop above rejection. Target POC then VAL. |
| 17 | Previous VAL Rejection | Market Profile | Price rejects from previous Value Area Low. | Excellent | Good | Intraday | Long after wick below VAL, close above, then minor bullish BOS. Stop below rejection. Target POC then VAH. |
| 18 | VAH Flip Support | Market Profile | Price breaks VAH, accepts above, then retests as support. | Excellent | Good | Intraday | Long after 2 closes above VAH, retest, and bullish rejection. Stop below VAH/zone. Target session high/PDH. |
| 19 | VAL Flip Resistance | Market Profile | Price breaks VAL, accepts below, then retests as resistance. | Excellent | Good | Intraday | Short after 2 closes below VAL, retest, and bearish rejection. Stop above VAL/zone. Target session low/PDL. |
| 20 | Failed Auction Above VAH | Market Profile | Break above VAH fails and returns inside value. | Excellent | Good | Intraday | Short after close back inside VAH and bearish BOS. Target POC then VAL. Stop above failed auction high. |
| 21 | Failed Auction Below VAL | Market Profile | Break below VAL fails and returns inside value. | Excellent | Good | Intraday | Long after close back inside VAL and bullish BOS. Target POC then VAH. Stop below failed auction low. |
| 22 | POC Magnet Rotation | Market Profile | Price rotates toward previous POC in balanced market. | Very Good | Good | Range Day | Enter from VA edge after rejection; target POC first. Avoid if trend day or price accepts outside value. |
| 23 | Inside Value Rotation | Market Profile | Trade VAL to POC to VAH or reverse when open is inside value. | Good | Good | Range Day | Buy VAL rejection or sell VAH rejection. Stop outside VA. Target POC then opposite VA edge. |
| 24 | Outside Value Acceptance | Market Profile | Price accepts outside value and trends. | Excellent | Good | Trend Day | Trade retest of VAH/VAL after acceptance. Stop back inside value. Target next liquidity/weekly level. |
| 25 | Poor High / Poor Low Repair | Market Profile | Market returns to repair weak auction high/low. | Very Good | Medium | Intraday | Trade toward poor high/low only with trend alignment. Stop behind last swing. Target poor level. |
| 26 | Single Prints Fill | Market Profile | Price returns to fill single prints/imbalance. | Very Good | Medium | Intraday | Trade fill only with acceptance toward single prints. Stop beyond entry structure. Target end of single-print zone. |
| 27 | LVN Rejection | Market Profile | Low Volume Node rejects price. | Very Good | Medium | Intraday | Fade LVN when price rejects quickly. Stop beyond LVN. Target adjacent HVN/POC. |
| 28 | HVN Magnet | Market Profile | High Volume Node attracts price in balance. | Good | Medium | Range Day | Trade toward HVN after reclaim. Avoid entering at HVN; it is usually target, not entry. |

### VWAP

| # | Signal | Category | Description | Gold/XAUUSD | Forex Majors | Best Use | Execution Details |
|---|---|---|---|---|---|---|---|
| 29 | VWAP Reclaim Long | VWAP | Price moves from below VWAP to above and retests. | Excellent | Very Good | Intraday | Long after 2 closes above VWAP and retest holds. Stop below VWAP/retest low. Target upper band/VAH/PDH. |
| 30 | VWAP Rejection Short | VWAP | Price loses VWAP and retests from below. | Excellent | Very Good | Intraday | Short after 2 closes below VWAP and retest rejects. Stop above VWAP/retest high. Target lower band/VAL/PDL. |
| 31 | VWAP Pullback Long | VWAP | Trend above VWAP, pullback holds VWAP. | Excellent | Very Good | Scalping | Long on bullish rejection at VWAP in bullish structure. Stop below VWAP. Target band 1/band 2. |
| 32 | VWAP Pullback Short | VWAP | Trend below VWAP, pullback rejects VWAP. | Excellent | Very Good | Scalping | Short on bearish rejection at VWAP in bearish structure. Stop above VWAP. Target lower band 1/band 2. |
| 33 | VWAP Band 2 Reversal | VWAP | Price reaches extreme band and rejects. | Very Good | Good | Scalping | Fade band 2 only with exhaustion, sweep, or KLZ confluence. Stop beyond extreme wick. Target VWAP. |
| 34 | VWAP Band Trend Ride | VWAP | Price walks upper/lower band in strong trend. | Excellent | Good | Trend Day | Enter pullbacks to band 1/VWAP in trend direction. Do not fade band 2 without reversal signal. |
| 35 | VWAP Chop Filter | VWAP | Repeated crossing of VWAP means balance/chop. | Excellent | Excellent | Filter | Block trend trades when price crosses VWAP 3+ times in short window and range is compressed. |
| 36 | Anchored VWAP Retest | VWAP | Retest VWAP anchored from major swing/news/session open. | Excellent | Excellent | Intraday/Swing | Enter on AVWAP reaction with structure alignment. Stop beyond AVWAP and swing. Target next liquidity. |
| 37 | Weekly VWAP Confluence | VWAP | Price reacts from weekly VWAP. | Very Good | Very Good | Swing | Use as confluence for intraday entries. Do not trade weekly VWAP alone. |
| 38 | VWAP + VAH/VAL Confluence | VWAP | VWAP or band aligns with value area boundary. | Excellent | Good | Intraday | Approve signals at this confluence if rejection + BOS exists. Stop beyond combined zone. Target POC/opposite VA. |

### Classic Pattern

| # | Signal | Category | Description | Gold/XAUUSD | Forex Majors | Best Use | Execution Details |
|---|---|---|---|---|---|---|---|
| 39 | Double Top | Classic Pattern | Two highs near same resistance, neckline break. | Very Good | Excellent | Intraday/Swing | Short neckline break or retest. Stop above second top. Target measured move or next support. |
| 40 | Double Bottom | Classic Pattern | Two lows near same support, neckline break. | Very Good | Excellent | Intraday/Swing | Long neckline break or retest. Stop below second bottom. Target measured move or next resistance. |
| 41 | Triple Top | Classic Pattern | Three failed highs at resistance. | Good | Good | Swing | Short after neckline break. Stop above third top. Best at VAH/PDH/resistance. |
| 42 | Triple Bottom | Classic Pattern | Three failed lows at support. | Good | Good | Swing | Long after neckline break. Stop below third bottom. Best at VAL/PDL/support. |
| 43 | Head and Shoulders | Classic Pattern | Reversal pattern after uptrend. | Good | Very Good | Intraday/Swing | Short after neckline break/retest. Stop above right shoulder/head. Target measured move. |
| 44 | Inverse Head and Shoulders | Classic Pattern | Bullish reversal pattern after downtrend. | Good | Very Good | Intraday/Swing | Long after neckline break/retest. Stop below right shoulder/head. Target measured move. |
| 45 | Bull Flag | Classic Pattern | Bullish impulse then shallow pullback/channel. | Excellent | Excellent | Scalping/Intraday | Long breakout or retest of flag. Stop below flag. Target pole projection or next resistance. |
| 46 | Bear Flag | Classic Pattern | Bearish impulse then shallow pullback/channel. | Excellent | Excellent | Scalping/Intraday | Short breakdown or retest of flag. Stop above flag. Target pole projection or next support. |
| 47 | Bullish Pennant | Classic Pattern | Bullish impulse then triangle compression. | Very Good | Very Good | Intraday | Long break of pennant high. Prefer retest. Stop below pennant. Target pole projection. |
| 48 | Bearish Pennant | Classic Pattern | Bearish impulse then triangle compression. | Very Good | Very Good | Intraday | Short break of pennant low. Prefer retest. Stop above pennant. Target pole projection. |
| 49 | Ascending Triangle | Classic Pattern | Flat resistance with higher lows. | Good | Very Good | Intraday | Long breakout + retest, unless breaking into VAH/PDH. Stop below last HL. Target measured height. |
| 50 | Descending Triangle | Classic Pattern | Flat support with lower highs. | Good | Very Good | Intraday | Short breakdown + retest, unless breaking into VAL/PDL. Stop above last LH. Target measured height. |
| 51 | Symmetrical Triangle | Classic Pattern | Compression with lower highs and higher lows. | Medium | Good | Intraday | Trade confirmed breakout with retest. Stop opposite side. Avoid if breakout candle is exhausted. |
| 52 | Rising Wedge | Classic Pattern | Weak rising compression, bearish break. | Very Good | Very Good | Intraday | Short close below wedge support, ideally near resistance. Stop above last high. Target wedge origin. |
| 53 | Falling Wedge | Classic Pattern | Weak falling compression, bullish break. | Very Good | Very Good | Intraday | Long close above wedge resistance, ideally near support. Stop below last low. Target wedge origin. |
| 54 | Rectangle Breakout | Classic Pattern | Range breakout and retest. | Very Good | Excellent | Intraday | Enter retest of range high/low. Stop back inside range. Target range height projection. |
| 55 | Rectangle Reversal | Classic Pattern | Buy range low or sell range high. | Good | Excellent | Range Day | Trade range edge rejection only in balanced market. Stop outside range. Target midpoint then opposite edge. |
| 56 | Channel Bounce | Classic Pattern | Trade lower/upper boundary of channel. | Good | Excellent | Intraday | Enter bounce in trend direction. Stop outside channel. Target channel midline/opposite boundary. |
| 57 | Channel Breakout | Classic Pattern | Break channel, retest, continue. | Very Good | Excellent | Intraday | Enter retest after close outside channel. Stop back inside. Target next structure/VA level. |
| 58 | Parabolic Exhaustion | Classic Pattern | Fast accelerating move becomes unstable and reverses. | Excellent | Good | Scalping | Fade only at strong level with rejection + BOS. Stop beyond parabolic extreme. Target VWAP/mean. |

### Session

| # | Signal | Category | Description | Gold/XAUUSD | Forex Majors | Best Use | Execution Details |
|---|---|---|---|---|---|---|---|
| 59 | Asian Range Breakout | Session | Break Asian session high/low. | Very Good | Excellent | London/NY | Trade breakout retest in direction of clean acceptance. Stop inside range. Target measured range. |
| 60 | Asian Range Fakeout | Session | Sweep Asian range then reverse. | Excellent | Excellent | London/NY | Enter after sweep and close back inside range + BOS. Stop beyond sweep. Target opposite range side. |
| 61 | London Open Sweep | Session | Liquidity grab near London open. | Very Good | Excellent | Scalping | Trade after sweep of Asian high/low and structure shift. Stop beyond sweep. Target next session liquidity. |
| 62 | London High Sweep in NY | Session | NY sweeps London high then reverses. | Excellent | Very Good | NY Session | Short after reclaim below London high + BOS. Stop above sweep. Target VWAP/London low. |
| 63 | London Low Sweep in NY | Session | NY sweeps London low then reverses. | Excellent | Very Good | NY Session | Long after reclaim above London low + BOS. Stop below sweep. Target VWAP/London high. |
| 64 | NY Open Manipulation | Session | First move after NY open fails. | Excellent | Very Good | Scalping | Trade opposite after initial sweep/reclaim and BOS. Stop beyond NY manipulation wick. Target VWAP/session liquidity. |
| 65 | NY AM Continuation | Session | After manipulation, trend continues in NY morning. | Excellent | Very Good | Intraday | Enter pullback after NY directional BOS. Stop below/above pullback. Target next liquidity/VA level. |
| 66 | NY Lunch Chop Filter | Session | Avoid low-quality middle session. | Excellent | Excellent | Filter | Block new trades during lunch chop unless major news or clear breakout acceptance exists. |
| 67 | London Close Reversal | Session | Reversal near London close. | Good | Very Good | Intraday | Trade only if extended into key level and reversal BOS occurs. Stop beyond extreme. Target VWAP/POC. |
| 68 | Daily Open Retest | Session | Price retests daily open and reacts. | Very Good | Very Good | Intraday | Use daily open as bias line. Enter retest with rejection. Stop beyond daily open zone. Target session high/low. |
| 69 | Weekly Open Retest | Session | Price reacts from weekly open. | Very Good | Very Good | Swing | Use as confluence with structure. Stop beyond weekly open swing. Target weekly range extremes. |
| 70 | Killzone Liquidity Sweep | Session | Sweep during London/NY high-volume window. | Excellent | Excellent | Scalping | Approve sweeps in killzone more aggressively if confluence exists. Stop beyond sweep. Target intraday liquidity. |

### Breakout/Fakeout

| # | Signal | Category | Description | Gold/XAUUSD | Forex Majors | Best Use | Execution Details |
|---|---|---|---|---|---|---|---|
| 71 | Clean Breakout Retest | Breakout/Fakeout | Break level, retest, continue. | Very Good | Excellent | Intraday | Enter retest after acceptance. Stop back inside level. Target next structure. Reject if no retest and RR poor. |
| 72 | Failed Breakout | Breakout/Fakeout | Break level, fail, reverse. | Excellent | Very Good | Scalping | Enter after close back inside and BOS opposite. Stop beyond failed breakout. Target range midpoint/opposite side. |
| 73 | Breakout Without Retest | Breakout/Fakeout | Momentum breakout without pullback. | Medium | Medium | Trend Day | Only approve with strong trend and wide target. Stop below breakout candle midpoint/level. Usually wait for pullback. |
| 74 | Compression Breakout | Breakout/Fakeout | Tight range then expansion. | Excellent | Excellent | Intraday | Trade after ATR/volume expansion beyond compression. Stop inside range. Target measured compression height. |
| 75 | False Break Above Range | Breakout/Fakeout | Break high, close back inside. | Excellent | Excellent | Scalping | Short after bearish confirmation. Stop above false break high. Target range midpoint/low. |
| 76 | False Break Below Range | Breakout/Fakeout | Break low, close back inside. | Excellent | Excellent | Scalping | Long after bullish confirmation. Stop below false break low. Target range midpoint/high. |
| 77 | Break and Retest of KLZ | Breakout/Fakeout | Structural zone flips after breakout. | Excellent | Excellent | Intraday | Enter retest after acceptance on other side. Stop through KLZ. Target next KLZ/liquidity. |
| 78 | Failed Retest | Breakout/Fakeout | Retest fails and reverses hard. | Very Good | Very Good | Scalping | Trade opposite when retest cannot hold and BOS occurs. Stop beyond failed retest. Target origin of breakout. |
| 79 | Volatility Expansion Breakout | Breakout/Fakeout | ATR expands after compression. | Excellent | Very Good | Intraday | Enter with acceptance or first pullback. Stop inside compression. Target measured move or next liquidity. |
| 80 | News Breakout Continuation | Breakout/Fakeout | Strong news move continues after pullback. | Good | Medium | News Only | Wait for first pullback after news spike. Stop behind pullback. Target continuation. Avoid first seconds/minutes. |

### Candle Confirmation

| # | Signal | Category | Description | Gold/XAUUSD | Forex Majors | Best Use | Execution Details |
|---|---|---|---|---|---|---|---|
| 81 | Bullish Pin Bar | Candle Confirmation | Long lower wick at support. | Good | Very Good | Confirmation | Entry above pin high after support confluence. Stop below wick. Target next resistance. |
| 82 | Bearish Pin Bar | Candle Confirmation | Long upper wick at resistance. | Good | Very Good | Confirmation | Entry below pin low after resistance confluence. Stop above wick. Target next support. |
| 83 | Bullish Engulfing | Candle Confirmation | Bullish candle engulfs prior bearish body. | Very Good | Very Good | Confirmation | Long above engulfing high at support. Stop below engulfing low. Target next level. |
| 84 | Bearish Engulfing | Candle Confirmation | Bearish candle engulfs prior bullish body. | Very Good | Very Good | Confirmation | Short below engulfing low at resistance. Stop above engulfing high. Target next level. |
| 85 | Inside Bar Breakout | Candle Confirmation | Small candle inside previous candle range, then breakout. | Good | Very Good | Intraday | Trade break of mother candle in trend direction. Stop opposite side. Target measured mother candle range. |
| 86 | Outside Bar Reversal | Candle Confirmation | Large candle sweeps both sides and closes directional. | Excellent | Very Good | Scalping | Enter on break of outside bar in closing direction if at key level. Stop opposite extreme. Target VWAP/next level. |
| 87 | Marubozu Continuation | Candle Confirmation | Strong full-body candle after breakout. | Very Good | Good | Momentum | Use as confirmation, not late chase. Enter pullback to candle midpoint/level. Stop behind candle. |
| 88 | Doji at Level | Candle Confirmation | Indecision at key level. | Medium | Medium | Warning | No trade alone. Wait for next candle break + structure confirmation. |
| 89 | Rejection Wick + BOS | Candle Confirmation | Wick at level followed by structure break. | Excellent | Excellent | Entry Trigger | Enter after BOS or retest. Stop beyond wick. Target next liquidity/VA level. |
| 90 | Three Candle Reversal | Candle Confirmation | Exhaustion candle + reversal candle + confirmation candle. | Very Good | Very Good | Entry Trigger | Enter on confirmation close/break. Stop beyond exhaustion extreme. Target mean/next level. |

### Trend/Structure

| # | Signal | Category | Description | Gold/XAUUSD | Forex Majors | Best Use | Execution Details |
|---|---|---|---|---|---|---|---|
| 91 | Bullish BOS | Trend/Structure | Break previous swing high. | Excellent | Excellent | Structure | Use as confirmation for longs. Entry after pullback/retest. Stop below HL. Target next swing high/liquidity. |
| 92 | Bearish BOS | Trend/Structure | Break previous swing low. | Excellent | Excellent | Structure | Use as confirmation for shorts. Entry after pullback/retest. Stop above LH. Target next swing low/liquidity. |
| 93 | Bullish CHOCH | Trend/Structure | First bullish shift after bearish trend. | Excellent | Excellent | Reversal | Use after sweep/support reaction. Enter pullback after CHOCH. Stop below reversal low. Target next resistance. |
| 94 | Bearish CHOCH | Trend/Structure | First bearish shift after bullish trend. | Excellent | Excellent | Reversal | Use after sweep/resistance reaction. Enter pullback after CHOCH. Stop above reversal high. Target next support. |
| 95 | Higher High / Higher Low Trend | Trend/Structure | Confirmed bullish trend sequence. | Very Good | Excellent | Intraday | Prefer longs on pullbacks to HL, VWAP, KLZ. Stop below HL. Target HH/extension. |
| 96 | Lower Low / Lower High Trend | Trend/Structure | Confirmed bearish trend sequence. | Very Good | Excellent | Intraday | Prefer shorts on pullbacks to LH, VWAP, KLZ. Stop above LH. Target LL/extension. |
| 97 | Pullback to Higher Low | Trend/Structure | Buy HL in bullish trend. | Very Good | Excellent | Intraday | Long after HL rejection + minor BOS. Stop below HL. Target prior high and extension. |
| 98 | Pullback to Lower High | Trend/Structure | Sell LH in bearish trend. | Very Good | Excellent | Intraday | Short after LH rejection + minor BOS. Stop above LH. Target prior low and extension. |
| 99 | Trend Exhaustion | Trend/Structure | New high/low with weak follow-through. | Excellent | Very Good | Reversal | Counter-trend only after key level + sweep + CHOCH. Stop beyond extreme. Target VWAP/POC. |
| 100 | Market Structure Shift | Trend/Structure | CHOCH plus displacement confirms regime change. | Excellent | Excellent | Reversal | Enter first pullback after MSS. Stop beyond origin. Target next major liquidity/VA level. |

## Best Signals by Market
### Gold / XAUUSD
Use first: KLZ Retest, Liquidity Sweep, PDH/PDL Sweep, FVG Fill, VWAP Reclaim/Rejection, VAH/VAL Rejection, Failed Auction, NY Open Manipulation, London High/Low Sweep, Bull/Bear Flag, Parabolic Exhaustion, Outside Bar Reversal, Rejection Wick + BOS, Compression Breakout. Gold is fast and aggressive; it prefers sweeps, fakeouts, displacement, VWAP reactions, and NY session moves.

### EURUSD
Use first: London Open Sweep, Asian Range Breakout/Fakeout, Clean Breakout Retest, Double Top/Bottom, Channel Bounce, Rectangle Breakout, VWAP Pullback, FVG Fill, Trend Pullback. EURUSD is smoother and often respects ranges/channels.

### GBPUSD
Use first: Liquidity Sweep, London Open Sweep, Asian Range Fakeout, PDH/PDL Sweep, Breakout Retest, Stop Hunt Reversal, Double Top/Bottom, Bull/Bear Flag, VWAP Reclaim, Market Structure Shift. GBPUSD is volatile and likes London traps.

### USDJPY
Use first: Trend Continuation, Pullback to HL/LH, VWAP Pullback, Channel Bounce, Breakout Retest, FVG Fill, Daily/Weekly Open Retest, Rectangle Breakout, Asian Session Range. USDJPY trends well; reversal trades need stronger confirmation.

## AI Review Prompt
```text
Review this trading signal for XAUUSD / Forex.

Signal: {signal_name}
Direction: {direction}
Current Price: {price}
Timeframe: {timeframe}
Market Structure: {structure}
Previous VAH: {prev_vah}
Previous VAL: {prev_val}
Previous POC: {prev_poc}
VWAP: {vwap}
VWAP Bands: {vwap_bands}
Previous Day High: {pdh}
Previous Day Low: {pdl}
Nearest Key Level Zone: {klz}
Entry: {entry}
Stop Loss: {stop_loss}
Targets: {targets}
Risk Reward: {risk_reward}
Python Confidence: {confidence}

Tasks:
1. Decide APPROVE, REJECT, or WAIT.
2. Reject if price is in the middle of value or chopping around VWAP.
3. Reject if risk/reward is below 1:2.
4. Reject if the nearest VAH/VAL was already accepted through.
5. Reject if the KLZ is mitigated or invalidated.
6. Approve only if structure, level, session, and VWAP context agree.


```
