# Realtime TPO Profile [Kioseff Trading] — how it computes POC/VAH/VAL (reference)

Source: © KioseffTrading (MPL-2.0). Full Pine v5 source pasted by the user; key logic distilled here so we
can READ or REPLICATE the value areas. The indicator is on the PEPPERSTONE:XAUUSD charts (OANDA has no real
volume). See [[supply-demand-zones]] / zones-and-confluence for how this fits the value-area layer.

## Color inputs (what each character/line color MEANS)
- `col`  = **gray**  (default) — main TPO letters, OUTSIDE the value area → IGNORE
- `col1` = **red**   — Single Print (SP) letters/levels → IGNORE for VA
- `col2` = **yellow**— **POC** row (price level hit by the most TPO periods) + POC line (width 2)
- `col3` = **blue**  — Initial Balance letters + the `●` current-open dot
- `col4` = **lime**  — the **value-area boundary LINES** (`val[]`) and the "VAH"/"VAL" text labels
- `col5` = **white** — letters INSIDE the value area → VAH = highest white, VAL = lowest white

Observed ARGB textColors (little-endian 0xAABBGGRR): white `4294967295`, yellow `4282117119`
(#FFEB3B), gray `4287003512` (#787B86), red `4283585279` (#FF5252), blue-dot `4294926889` (#2962FF).

## POC + value-area algorithm
1. Slice the session into price rows ("ticks"), step = `tickz * mintick`. `tickz` = Custom ticks value, or
   Auto = `atr*30/40/50` depending on TF. Chart config seen: `Regular / Auto / 50 / Small / D / 1300-1700`.
2. For each row, count how many TPO periods touched it → `che[x]`. **POC** = the row with the max count
   (`len`); its letters are recolored `col2` (yellow) and a POC line (width 2) is drawn from `first`.
3. **Value Area = 70%**: expand outward from the POC row, alternately adding the next row above/below,
   accumulating counts until `sum_above + sum_below >= array.sum(che) * 0.7`. The two outermost included rows
   become the VA boundary lines (`val[0]`, `val[1]`); the higher one is labeled **VAH**, the lower **VAL**.
   Letters within [VAL, VAH] (except the POC row) are recolored `col5` (white).

## What persists for PREVIOUS sessions (showPre = true, default on)
On each session close it COPIES forward: the VA lines (`valCopy`, lime), the POC line (`pocCopy`, yellow),
the SP lines (`SPCopy`, red), and the letter labels (`tpoLabelsCopy`). These lines extend right each bar
**until price moves more than `distCalc2`/`distCalc3` % away (default 5%)**, at which point they're hidden
(x2 reset to x1). So only prior sessions whose VA/POC sit within ~5% of current price stay drawn/readable.
NOTE: the "VAH"/"VAL"/"POC" TEXT labels are only created for the most-recent session, NOT copied to all
previous sessions — so for prior days, read the LINES (by color), not text labels.

## How to READ it programmatically (preferred over letter-parsing)
- `data_get_pine_lines` on the TPO study, VERBOSE (need color + y). Group by color:
  - lime (`col4`) lines → VA boundaries (VAH = higher of a pair, VAL = lower), one pair per visible session
  - yellow (`col2`) line → POC
  - red (`col1`) → SP levels (ignore for VA)
- Fallback (letter method, per user): group letter labels by DAY (map label `x`→time→calendar day), then
  VAH = max price of white letters, VAL = min price of white letters, POC = the yellow row. Validated, but
  noisier than reading the lines.
- Indicator must be VISIBLE to read; its study id ROTATES per call (resolve fresh each time); inputs are
  protected (names come back null). Reading a LIVE indicator is NOT date-faithful in replay — for the
  backtest, REPLICATE this 70%-from-POC algorithm in Python on the replay bars instead.
