#!/usr/bin/env python3
"""Test suite for the trading tooling — scalp_fast (hard floor + skip logging) and analyze_logs.
Pure stdlib, no pytest. Run:  python3 test_trading.py   (exit 0 = all pass, 1 = a failure).

Covers: the pre-hold R:R hard-floor predicate, the auto-skip dedup logic + log writing, and every
analyze_logs helper (stats math, grade/number/time parsing, result classification, reason bucketing,
and a full analyze() smoke test on synthetic rows)."""
import os, sys, csv, glob, json, math, tempfile, datetime as dt

sys.path.insert(0, os.path.expanduser("~/tradingview-mcp"))
import scalp_fast as sf
import analyze_logs as al

_results = []
def check(name, cond):
    _results.append((name, bool(cond)))

def approx(a, b, tol=1e-6):
    return a is not None and b is not None and abs(a - b) <= tol


# ─────────────────────────────────────────────────────────────────────────────
# 1) hard_floor_skip — the pre-hold floor predicate (the behavior-defining function)
# ─────────────────────────────────────────────────────────────────────────────
def test_hard_floor():
    VS = 1.0
    # (name, side, regime, rsi, rr1, room, chop_er, expect_skip)
    cases = [
        # MUST SKIP — structurally un-tradeable (neg R:R), any direction
        ("live CRT +8p/18p",          "LONG",  "UP",   37.6, 8/18, 18, 0.52, True),
        ("with-trend 4p room",        "LONG",  "UP",   55.0, 6/15, 4,  0.40, True),
        ("no-room long 3p",           "LONG",  "UP",   50.0, 6/18, 3,  0.34, True),
        ("counter+oversold no-room",  "SHORT", "UP",   26.7, 6/18, 5,  0.37, True),
        ("thin-room dead-chop+counter","SHORT","UP",   33.6, 1.1,  6,  0.05, True),  # secondary clause
        # MUST NOT SKIP — genuine positive-R:R setups with room
        ("the +77 winner",            "LONG",  "UP",   45.0, 1.3,  84, 0.45, False),
        ("clean with-trend rr1.0",    "LONG",  "UP",   55.0, 1.0,  40, 0.40, False),
        ("counter but rr1.4+room",    "SHORT", "UP",   50.0, 1.4,  60, 0.45, False),
        ("mean-revert long@support",  "LONG",  "DOWN", 28.0, 1.2,  40, 0.40, False),
        ("rr exactly at floor 0.8",   "LONG",  "UP",   50.0, 0.8,  40, 0.40, False),  # >= floor passes
        ("room unknown (no wall)",    "LONG",  "UP",   50.0, 1.0,  None,0.40, False),  # above chop ER floor
        ("rr None (no risk)",         "LONG",  "UP",   50.0, None, 40, 0.40, False),
    ]
    for name, side, regime, rsi, rr1, room, er, expect in cases:
        skip, reasons = sf.hard_floor_skip(side, regime, rsi, rr1, room, er, VS)
        check(f"floor: {name}", skip == expect)
        if expect:
            check(f"floor: {name} gives a reason", len(reasons) >= 1)

    # reason content: neg R:R is reported
    _, r1 = sf.hard_floor_skip("LONG", "UP", 50, 0.4, 5, 0.5, 1.0)
    check("floor: neg-R:R reason text", any("neg R:R" in x for x in r1))
    # VS scales the room threshold: 11p room is "thin" when VS=2 (threshold 20p)
    skip_hi, _ = sf.hard_floor_skip("SHORT", "UP", 50, 1.5, 11, 0.05, 2.0)  # neg? no (rr1.5) but thin+chop+VS2
    check("floor: VS scales room threshold", skip_hi is True)


# ─────────────────────────────────────────────────────────────────────────────
# 2) auto-skip dedup — pure predicate + real log write/dedup via a temp HOME
# ─────────────────────────────────────────────────────────────────────────────
def test_skip_key_and_dedup():
    k = sf.floor_skip_key("LONG", 4462.95, "zone-bounce rejection")
    check("skip key: rounds price", k == "LONG|4463|zone-bounce rejection")
    check("skip key: side+price+why differ", sf.floor_skip_key("SHORT", 4463, "x") != k)

    now = 1_000_000.0
    prev = {"key": k, "t": now - 100}
    check("dedup: same key within window", sf.is_dup_skip(prev, k, now, 600) is True)
    check("dedup: same key past window",   sf.is_dup_skip(prev, k, now + 700, 600) is False)
    check("dedup: different key",          sf.is_dup_skip(prev, "OTHER", now, 600) is False)
    check("dedup: no prev state",          sf.is_dup_skip(None, k, now, 600) is False)


def test_log_floor_skip_writes_and_dedups():
    """Integration: log_floor_skip writes an 'auto-skip' row and de-dups the same thesis (temp HOME)."""
    real_home, real_sym, real_time = os.environ.get("HOME"), sf.SYMBOL, sf.time.time
    _clock = [1_000_000.0]
    def _tick():                       # monotonic fake clock: guarantees distinct ids (no same-second
        _clock[0] += 1; return _clock[0]   # collision) while staying inside the 600s dedup window
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HOME"] = tmp
        sf.SYMBOL = "TESTSYM"
        sf.time.time = _tick
        try:
            # same thesis twice -> 1 row; different thesis -> 2 rows total
            sf.log_floor_skip("SHORT", "break-and-retest", 4470.0, "C-into-zone", 47, 20, "x14 zone", 0.40, ["neg R:R 0.40 (TP1 < 0.8×SL)"])
            sf.log_floor_skip("SHORT", "break-and-retest", 4470.2, "C-into-zone", 47, 20, "x14 zone", 0.40, ["neg R:R 0.40 (TP1 < 0.8×SL)"])  # dup (rounds to 4470)
            sf.log_floor_skip("LONG",  "momentum impulse", 4480.0, "A+",          50, 30, "open",     0.38, ["neg R:R 0.38 (TP1 < 0.8×SL)"])
            # INTERLEAVED re-fire of the FIRST thesis after a different one — must still dedup (the old
            # single-prev store failed this, logging it again because 'momentum' overwrote the prev key).
            sf.log_floor_skip("SHORT", "break-and-retest", 4470.1, "C-into-zone", 47, 20, "x14 zone", 0.40, ["neg R:R 0.40 (TP1 < 0.8×SL)"])
            paths = glob.glob(os.path.join(tmp, "tradingview-mcp", "logs", "testsym", "*.csv"))
            check("log: csv created", len(paths) == 1)
            rows = list(csv.DictReader(open(paths[0]))) if paths else []
            skips = [r for r in rows if r.get("result") == "auto-skip"]
            check("log: deduped to 2 distinct theses (incl. interleaved re-fire)", len(skips) == 2)
            check("log: reason stored in pips", any("neg R:R" in r.get("pips", "") for r in skips))
            check("log: R:R stored in exit", any(r.get("exit") not in ("", None) for r in skips))
        finally:
            sf.SYMBOL = real_sym
            sf.time.time = real_time
            if real_home is not None: os.environ["HOME"] = real_home


# ─────────────────────────────────────────────────────────────────────────────
# 3) analyze_logs helpers
# ─────────────────────────────────────────────────────────────────────────────
def test_stats():
    s = al.stats([])
    check("stats: empty n=0", s["n"] == 0 and s["net"] == 0.0 and s["pf"] == 0.0)

    s = al.stats([10.0, -5.0, 0.0])
    check("stats: counts W/L/scratch", s["wins"] == 1 and s["losses"] == 1 and s["scratch"] == 1)
    check("stats: net",      approx(s["net"], 5.0))
    check("stats: win rate", approx(s["wr"], 100/3))
    check("stats: PF",       approx(s["pf"], 2.0))
    check("stats: avg win",  approx(s["avg_win"], 10.0))
    check("stats: avg loss", approx(s["avg_loss"], 5.0))
    check("stats: expectancy", approx(s["exp"], 5/3))

    s = al.stats([10.0, 20.0])   # no losses -> infinite PF
    check("stats: PF infinite when no losses", s["pf"] == float("inf"))


def test_norm_grade():
    cases = {"B (open space)": "B", "A+": "A+", "C-into-zone": "C-into-zone",
             "A": "A", "": "?", "(reconstructed)": "?"}
    for raw, exp in cases.items():
        check(f"grade: {raw!r}->{exp}", al._norm_grade(raw) == exp)
    check("grade: None->?", al._norm_grade(None) == "?")


def test_num():
    check("num: int str", approx(al._num("100"), 100.0))
    check("num: comma",   approx(al._num("1,234.5"), 1234.5))
    check("num: negative", approx(al._num("-35"), -35.0))
    check("num: reason text -> None", al._num("neg R:R 0.4 reason") is None)
    check("num: empty -> None", al._num("") is None)


def test_parse_time():
    check("time: HH:MM",    al._parse_time("2026-06-05 01:49") == dt.datetime(2026, 6, 5, 1, 49))
    check("time: HH:MM:SS", al._parse_time("2026-06-05 01:49:24") == dt.datetime(2026, 6, 5, 1, 49, 24))
    check("time: garbage -> None", al._parse_time("not a date") is None)
    check("time: empty -> None",   al._parse_time("") is None)


def _row(result, pips, pattern="momentum impulse", grade="A+", side="LONG", sym="XAUUSD",
         time="2026-06-05 13:00"):
    return {"result": result, "pips": pips, "pattern": pattern, "grade": grade,
            "side": side, "sym": sym, "time": time, "entry": "4460", "rng10": "50", "body_p": "20"}


def test_analyze_end_to_end():
    rows = [
        _row("TP2", "100"),                                   # executed win
        _row("SL", "-35"),                                    # executed loss
        _row("BE", "0"),                                      # executed scratch
        _row("rejected", "counter-trend dead chop neg R:R"),  # rejected (pips = reason text)
        _row("auto-skip", "neg R:R 0.40 (TP1 < 0.8×SL)"),     # floor skip
        _row("PENDING", ""),                                  # open
    ]
    out = al.analyze(rows)
    check("analyze: 3 executed",     "3 executed" in out)
    check("analyze: 1 rejected",     "1 rejected" in out)
    check("analyze: 1 auto-skipped", "1 auto-skipped" in out)
    check("analyze: 1 open",         "1 open" in out)
    check("analyze: net +65",        "+65" in out)
    check("analyze: auto-skip section present", "Hard-floor auto-skips" in out)
    check("analyze: auto-skip cause shown",     "neg R:R" in out)
    # auto-skip / rejected / pending rows must NOT be counted as executed trades
    executed = [r for r in rows if r.get("result") in al.EXECUTED and al._num(r.get("pips")) is not None]
    check("analyze: classification excludes non-trades", len(executed) == 3)


def test_group_stats():
    rows = [_row("TP2", "100", side="LONG"), _row("SL", "-35", side="SHORT"),
            _row("rejected", "reason text", side="SHORT")]   # rejected has no numeric pips -> dropped
    g = al.group_stats([r for r in rows if r["result"] in al.EXECUTED], lambda r: r["side"])
    check("group_stats: LONG net", "LONG" in g and approx(g["LONG"]["net"], 100.0))
    check("group_stats: SHORT net", "SHORT" in g and approx(g["SHORT"]["net"], -35.0))


# ─────────────────────────────────────────────────────────────────────────────
# 4) reversal_rsi_extreme — #3 gate: skip a reversal taken at a WRONG-WAY RSI extreme
#    (selling the bottom / buying the top), while leaving reset-RSI bounces alone.
# ─────────────────────────────────────────────────────────────────────────────
def test_reversal_rsi_extreme():
    # SHORT reversals into deep oversold = selling the bottom -> skip
    check("rsi-gate: SHORT VWAP @22 (sell bottom)",  sf.reversal_rsi_extreme("SHORT", "VWAP rejection", 22.0) is True)
    check("rsi-gate: SHORT zone-bounce @25 boundary", sf.reversal_rsi_extreme("SHORT", "zone-bounce rejection", 25.0) is True)
    check("rsi-gate: SHORT CRT @20",                  sf.reversal_rsi_extreme("SHORT", "CRT sweep+reclaim", 20.0) is True)
    check("rsi-gate: SHORT zone-bounce @26 NOT extreme", sf.reversal_rsi_extreme("SHORT", "zone-bounce rejection", 26.0) is False)

    # LONG reversals into overbought = buying the top -> skip
    check("rsi-gate: LONG VWAP @78 (buy top)",        sf.reversal_rsi_extreme("LONG", "VWAP bounce", 78.0) is True)
    check("rsi-gate: LONG zone-bounce @75 boundary",  sf.reversal_rsi_extreme("LONG", "zone-bounce rejection", 75.0) is True)

    # the WINNERS must be safe — reset RSI, not extreme
    check("rsi-gate: +28p winner LONG @40 SAFE",      sf.reversal_rsi_extreme("LONG", "zone-bounce rejection", 40.0) is False)
    check("rsi-gate: +77 winner LONG @45 SAFE",       sf.reversal_rsi_extreme("LONG", "zone-bounce rejection", 45.0) is False)

    # only REVERSAL setups are gated; continuation setups are not (handled elsewhere)
    check("rsi-gate: momentum impulse not gated",     sf.reversal_rsi_extreme("LONG", "momentum impulse", 20.0) is False)
    check("rsi-gate: trendline break not gated",      sf.reversal_rsi_extreme("SHORT", "support-trendline break", 22.0) is False)

    # missing RSI -> never gate
    check("rsi-gate: None rsi safe",                  sf.reversal_rsi_extreme("SHORT", "VWAP rejection", None) is False)


# ─────────────────────────────────────────────────────────────────────────────
# 4b) reversal context quality floor — stacked confluence OR valid prior VA
# ─────────────────────────────────────────────────────────────────────────────
class _FakeVAState:
    def __init__(self, state, confidence="strong"):
        self.state = state
        self.confidence = confidence

    def level_state(self, lvl, bars, role, poc=None, bar_minutes=5):
        return {"state": self.state, "evidence": {"confidence": self.confidence}}


def test_reversal_context_floor():
    prior = [{"vah": 4500.0, "poc": 4475.0, "val": 4450.0}]
    prior_multi = [
        {"vah": 4510.0, "poc": 4485.0, "val": 4460.0},
        {"vah": 4500.0, "poc": 4475.0, "val": 4450.0},
    ]
    bars = [_bar(4501, 4490)]
    check("prior VA: rejected strong valid",
          sf.valid_prior_va_near(4500.4, prior, bars, 1.0, 5, state_mod=_FakeVAState("Rejected")) is True)
    check("prior VA: flipped strong valid",
          sf.valid_prior_va_near(4450.2, prior, bars, 1.0, 5, state_mod=_FakeVAState("Flipped")) is True)
    check("prior VA: scans older days too",
          sf.valid_prior_va_near(4450.2, prior_multi, bars, 1.0, 5, state_mod=_FakeVAState("Rejected")) is True)
    check("prior VA: accepted invalid",
          sf.valid_prior_va_near(4500.0, prior, bars, 1.0, 5, state_mod=_FakeVAState("Accepted")) is False)
    check("prior VA: weak rejected invalid",
          sf.valid_prior_va_near(4500.0, prior, bars, 1.0, 5, state_mod=_FakeVAState("Rejected", "weak")) is False)
    check("prior VA: too far invalid",
          sf.valid_prior_va_near(4510.0, prior, bars, 1.0, 5, state_mod=_FakeVAState("Rejected")) is False)

    check("reversal context: stacked confluence passes",
          sf.reversal_context_ok("LONG", 4400.0, conf_s=2, conf_r=0, prior_vas=[], bars=bars,
                                 dyn_tolp=1.0, bar_minutes=5, state_mod=_FakeVAState("Accepted")) is True)
    check("reversal context: valid prior VA passes below conf floor",
          sf.reversal_context_ok("SHORT", 4500.0, conf_s=0, conf_r=1, prior_vas=prior, bars=bars,
                                 dyn_tolp=1.0, bar_minutes=5, state_mod=_FakeVAState("Rejected")) is True)
    check("reversal context: no confluence and invalid VA fails",
          sf.reversal_context_ok("SHORT", 4500.0, conf_s=0, conf_r=1, prior_vas=prior, bars=bars,
                                 dyn_tolp=1.0, bar_minutes=5, state_mod=_FakeVAState("Accepted")) is False)


# ─────────────────────────────────────────────────────────────────────────────
# 5) core setup detectors — characterization tests pinning current behavior
# ─────────────────────────────────────────────────────────────────────────────
def _bar(h, l, o=None, c=None, v=1):
    o = h if o is None else o; c = l if c is None else c
    return {"high": float(h), "low": float(l), "open": float(o), "close": float(c), "volume": v, "time": 0}

def test_pivots():
    H = [10]*11; H[5] = 20      # one clear swing high at index 5
    Lo = [9]*11; Lo[4] = 2      # one clear swing low at index 4
    bars = [_bar(H[i], Lo[i]) for i in range(11)]
    sh, sl = sf.pivots(bars, 3, 3)
    check("pivots: detects swing high", (5, 20.0) in sh)
    check("pivots: detects swing low",  (4, 2.0) in sl)
    check("pivots: no spurious highs",  len(sh) == 1)

def test_chop_15m():
    up = [_bar(i+1, i, c=i) for i in range(75)]                 # monotonic climb -> efficient trend
    is_chop, er = sf.chop_15m(up)
    check("chop_15m: trend not chop", is_chop is False and er >= 0.9)
    osc = [_bar(101, 100, c=(100 + (10 if (i % 2) else 0))) for i in range(75)]   # oscillation -> chop
    is_chop2, er2 = sf.chop_15m(osc)
    check("chop_15m: oscillation = chop", is_chop2 is True and er2 < 0.3)

def test_rsi_series():
    up = sf.rsi_series([float(i) for i in range(30)])     # strictly rising closes
    check("rsi: warmup is None", up[0] is None and up[13] is None)
    check("rsi: rising -> ~100", up[20] is not None and up[20] > 95)
    dn = sf.rsi_series([float(30 - i) for i in range(30)])
    check("rsi: falling -> ~0", dn[20] is not None and dn[20] < 5)

def test_line_and_proj():
    line = sf.line_through((0, 0), (2, 4))
    check("line_through: slope/intercept", approx(line[0], 2.0) and approx(line[1], 0.0))
    check("proj: projects along line", approx(sf.proj(line, 3), 6.0))
    check("line_through: vertical -> None", sf.line_through((1, 0), (1, 5)) is None)

def test_near_htf():
    levels = [(10, 20, "R zone")]
    check("near_htf: inside band+tol", sf.near_htf(15, levels, 4) == (10, 20, "R zone"))
    check("near_htf: edge within tol",  sf.near_htf(23, levels, 4) == (10, 20, "R zone"))
    check("near_htf: outside -> None",   sf.near_htf(30, levels, 4) is None)

def test_calc_vp():
    bars = [_bar(100.5, 100.0, v=100) for _ in range(12)] + [_bar(110.5, 110.0, v=1) for _ in range(8)]
    vpoc, vah, val = sf._calc_vp(bars)
    check("vp: POC at the heavy cluster", vpoc is not None and 99 < vpoc < 102)
    check("vp: value area ordered", val is not None and vah is not None and val <= vpoc <= vah)
    check("vp: too few bars -> None", sf._calc_vp([_bar(1, 0)]) == (None, None, None))

def test_scalp_num():
    check("scalp _num: comma", approx(sf._num("1,234.5"), 1234.5))
    check("scalp _num: junk -> None", sf._num("abc") is None)


# ─────────────────────────────────────────────────────────────────────────────
# 6) NEW modules (test-first): digest.build_digest + preflight status helpers
# ─────────────────────────────────────────────────────────────────────────────
def test_build_digest():
    import digest
    rows = [_row("TP2", "100"), _row("SL", "-35"), _row("BE", "0"),
            _row("auto-skip", "neg R:R 0.40 (TP1 < 0.8×SL)")]
    txt = digest.build_digest(rows, "2026-06-05")
    check("digest: shows date", "2026-06-05" in txt)
    check("digest: 3 trades", "3" in txt)
    check("digest: net +65", "+65" in txt)
    check("digest: W/L counts", "1W" in txt and "1L" in txt)
    check("digest: floor auto-skips", "auto-skip" in txt.lower())
    check("digest: empty day handled", isinstance(digest.build_digest([], "2026-06-05"), str))

def test_preflight_status():
    import preflight
    check("preflight: fresh zone ok", preflight.fresh_status(True, 100, 6*3600) == "ok")
    check("preflight: stale zone", preflight.fresh_status(True, 7*3600, 6*3600) == "stale")
    check("preflight: missing file", preflight.fresh_status(False, 0, 100) == "missing")
    check("preflight: overall READY", preflight.overall(["ok", "ok"]) == "READY")
    check("preflight: overall CHECK on stale", preflight.overall(["ok", "stale"]) == "CHECK")
    check("preflight: overall CHECK on missing", preflight.overall(["missing"]) == "CHECK")


# ─────────────────────────────────────────────────────────────────────────────
# 7) counterfactual reject analysis (test-first): simulate_outcome — which level hits first
# ─────────────────────────────────────────────────────────────────────────────
def test_simulate_outcome():
    import counterfactual as cf
    B = lambda h, l: {"high": float(h), "low": float(l), "time": 0}
    # LONG: reaches TP1 without hitting SL -> "TP1"
    check("cf: LONG hits TP1", cf.simulate_outcome("LONG", 100, 98, 103, [B(101, 99), B(104, 100)]) == "TP1")
    # LONG: dips to SL first -> "SL"
    check("cf: LONG hits SL",  cf.simulate_outcome("LONG", 100, 98, 103, [B(101, 97)]) == "SL")
    # LONG: same bar touches both -> SL wins (conservative)
    check("cf: LONG tie -> SL", cf.simulate_outcome("LONG", 100, 98, 103, [B(104, 97)]) == "SL")
    # LONG: neither over the window -> "none"
    check("cf: LONG none",     cf.simulate_outcome("LONG", 100, 98, 103, [B(101, 99), B(102, 99)]) == "none")
    # SHORT mirror
    check("cf: SHORT hits TP1", cf.simulate_outcome("SHORT", 100, 102, 97, [B(101, 99), B(100, 96)]) == "TP1")
    check("cf: SHORT hits SL",  cf.simulate_outcome("SHORT", 100, 102, 97, [B(103, 99)]) == "SL")
    check("cf: empty bars -> none", cf.simulate_outcome("LONG", 100, 98, 103, []) == "none")


def test_kl_upgrade():
    # KL = top tier: a real setup (A or B) → A+ directly; C/garbage not promoted; A+ stays A+.
    check("kl_upgrade: B(open space) -> A+", sf.kl_upgrade("B (open space)") == "A+")
    check("kl_upgrade: B+vol -> A+", sf.kl_upgrade("B+vol") == "A+")
    check("kl_upgrade: A -> A+", sf.kl_upgrade("A") == "A+")
    check("kl_upgrade: A+ stays A+", sf.kl_upgrade("A+") == "A+")
    check("kl_upgrade: C not promoted", sf.kl_upgrade("C-into-zone") == "C-into-zone")


def test_downgrade_grade():
    # SOFT counter-trend penalty: lower the letter tier by N, floored at C, suffix dropped.
    check("downgrade: A+ −1 → A", sf.downgrade_grade("A+", 1) == "A")
    check("downgrade: A+ −2 → B", sf.downgrade_grade("A+", 2) == "B")
    check("downgrade: A −1 → B", sf.downgrade_grade("A", 1) == "B")
    check("downgrade: B(open space) −1 → C", sf.downgrade_grade("B (open space)", 1) == "C")
    check("downgrade: floors at C", sf.downgrade_grade("C-into-zone", 1) == "C" and sf.downgrade_grade("B", 5) == "C")
    check("downgrade: 0 steps unchanged tier", sf.downgrade_grade("A+", 0) == "A+")


def test_merge_classic_keeps_all():
    # drawn == traded: EVERY classic zone enters the level map (none dropped, even overlapping ones).
    htf_r = [(4400, 4410, "old R")]; htf_s = [(4300, 4310, "old S")]
    classic = {"zones": [
        {"role": "sell zone", "lo": 4402, "hi": 4408, "tf": "4H", "kl": False},   # overlaps old R — kept anyway
        {"role": "buy zone",  "lo": 4250, "hi": 4260, "tf": "1H", "kl": True},
    ], "sr": [
        {"role": "resistance", "price": 4405, "tf": "4H", "flip": False},          # overlaps old R — kept anyway
        {"role": "support",    "price": 4280, "tf": "1H", "flip": False},
    ]}
    R, S = sf.merge_classic_zones(htf_r, htf_s, classic)
    check("merge: overlapping classic zone is NOT dropped (drawn==traded)", any("sell zone" in lab for _, _, lab in R))
    check("merge: overlapping classic S/R line is NOT dropped", any("resistance (classic)" in lab for _, _, lab in R))
    check("merge: all classic zones in R/S (3R: old + sell + res-line)", len(R) == 3)
    check("merge: all classic supports in S (old + buy + sup-line)", len(S) == 3)
    check("merge: inputs untouched (returns copies)", len(htf_r) == 1 and len(htf_s) == 1)


def test_count_distinct_at():
    # an old HTF wall + a coinciding classic zone at the SAME price counts ONCE (no double-count) ...
    overlapping = [(4400, 4410, "old R"), (4402, 4408, "4H sell zone")]
    check("count: overlapping walls at price count once", sf.count_distinct_at(overlapping, 4405) == 1)
    # a far wall that doesn't bracket the price isn't counted
    far = [(4400, 4406, "wall A"), (4470, 4480, "wall B")]
    check("count: far non-bracketing wall not counted", sf.count_distinct_at(far, 4403) == 1)
    # price squeezed BETWEEN two separate walls (gap > edge) → counts as 2 distinct
    straddle = [(4395, 4401, "below"), (4409, 4415, "above")]
    check("count: price between two distinct walls counts 2", sf.count_distinct_at(straddle, 4405) == 2)
    check("count: nothing at price → 0", sf.count_distinct_at(overlapping, 4300) == 0)


def main():
    for fn in (test_hard_floor, test_skip_key_and_dedup, test_log_floor_skip_writes_and_dedups,
               test_stats, test_norm_grade, test_num, test_parse_time,
               test_analyze_end_to_end, test_group_stats, test_reversal_rsi_extreme,
               test_reversal_context_floor, test_pivots, test_chop_15m, test_rsi_series, test_line_and_proj, test_near_htf,
               test_calc_vp, test_scalp_num, test_build_digest, test_preflight_status,
               test_simulate_outcome, test_kl_upgrade, test_downgrade_grade, test_merge_classic_keeps_all, test_count_distinct_at):
        try:
            fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False)
            print(f"  !! {fn.__name__} raised: {e}")
    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)
    for name, ok in _results:
        if not ok: print(f"  [FAIL] {name}")
    print(f"\n{'✅' if passed == total else '❌'} {passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
