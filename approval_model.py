#!/usr/bin/env python3
"""Outcome-calibrated approval — a transparent, stdlib-only win-rate table that learns which
signals actually resolve TP1-first and scores new ones accordingly. Drops in at the ai_decide
step to replace hand-coded vetoes that the backtest showed were anti-predictive.

Design (deliberately simple + inspectable):
  - featurize(signal) -> {family, align, rsi-bucket, session}
  - Model.train(rows) tallies wins/losses at three tiers: the full cell, the setup-family
    marginal, and the global prior.
  - Model.score(signal) walks cell -> family -> global, using the most specific tier that has
    at least `min_support` samples, with Laplace smoothing. This is graceful degradation:
    an unseen cell never invents an edge, it backs off to what it does know.
  - Model.decide(signal, threshold) keeps the ONE veto the data supported (off-session is a
    hard reject) and otherwise approves on calibrated confidence.

Empirical motivation (06-01/02/04 backtest, 152 resolved signals): the live discipline approved
at 33% win / net-negative while its rejects ran 42% / net-positive — it was sorting backwards.
The dominant real signal is setup family (momentum impulse 30%/-160p vs CRT +137p); RSI is
U-shaped (extremes win, mid-zone loses); counter-trend is not a disqualifier. This table learns
exactly that instead of vetoing it.
"""
import json

RSI_BUCKETS = ((30, "<30"), (45, "30-45"), (55, "45-55"), (70, "55-70"))   # upper-exclusive; else ">70"


def _fnum(x, d=0.0):
    try: return float(x)
    except (TypeError, ValueError): return d


def _rsi_bucket(rsi):
    for hi, label in RSI_BUCKETS:
        if rsi < hi:
            return label
    return ">70"


def _align(side, regime):
    reg = (regime or "").upper()
    if reg == "UP":
        return "with" if side == "LONG" else "counter"
    if reg == "DOWN":
        return "with" if side == "SHORT" else "counter"
    return "flat"


def featurize(signal):
    """Map a raw signal dict to its calibration features."""
    why = signal.get("why") or "?"
    return {
        "family": why.split()[0] if why.split() else "?",
        "align": _align(signal.get("side"), signal.get("regime")),
        "rsi": _rsi_bucket(_fnum(signal.get("rsi"), 50.0)),
        "session": str(signal.get("session", "?")),
    }


def _cell_key(f):
    return f"{f['family']}|{f['align']}|{f['rsi']}|{f['session']}"


class Model:
    """Hierarchical smoothed win-rate table over signal features."""

    def __init__(self, alpha=1.0, min_support=5):
        self.alpha = float(alpha)
        self.min_support = int(min_support)
        self.cells = {}       # cell_key -> [wins, losses]
        self.families = {}    # family   -> [wins, losses]
        self.glob = [0, 0]    # [wins, losses]

    # ---- training -------------------------------------------------------
    @staticmethod
    def _bump(d, key, won):
        wl = d.setdefault(key, [0, 0])
        wl[0 if won else 1] += 1

    def train(self, rows):
        for r in rows:
            f = featurize(r)
            won = bool(r.get("won"))
            self._bump(self.cells, _cell_key(f), won)
            self._bump(self.families, f["family"], won)
            self.glob[0 if won else 1] += 1
        return self

    # ---- scoring --------------------------------------------------------
    def _smoothed(self, wl):
        w, l = wl
        return (w + self.alpha) / (w + l + 2 * self.alpha)

    def score(self, signal):
        """Return {score, tier, n}: calibrated P(win) from the most specific supported tier."""
        f = featurize(signal)
        cell = self.cells.get(_cell_key(f))
        if cell and sum(cell) >= self.min_support:
            return {"score": self._smoothed(cell), "tier": "cell", "n": sum(cell)}
        fam = self.families.get(f["family"])
        if fam and sum(fam) >= self.min_support:
            return {"score": self._smoothed(fam), "tier": "family", "n": sum(fam)}
        return {"score": self._smoothed(self.glob), "tier": "global", "n": sum(self.glob)}

    # ---- decision -------------------------------------------------------
    def decide(self, signal, threshold=0.5):
        """Approve/reject. Off-session is a hard veto (the only one the data supported);
        otherwise approve on calibrated confidence >= threshold."""
        if str(signal.get("session", "?")) != "ON":
            return {"approve": False, "score": 0.0, "tier": "veto",
                    "reasons": ["off-session: hard veto"]}
        s = self.score(signal)
        ok = s["score"] >= threshold
        reason = (f"calibrated score {s['score']:.2f} {'>=' if ok else '<'} {threshold:.2f} "
                  f"(tier={s['tier']}, n={s['n']})")
        return {"approve": ok, "score": s["score"], "tier": s["tier"], "reasons": [reason]}

    # ---- persistence ----------------------------------------------------
    def save(self, path):
        json.dump({"alpha": self.alpha, "min_support": self.min_support,
                   "cells": self.cells, "families": self.families, "glob": self.glob},
                  open(path, "w"), indent=1)

    @classmethod
    def load(cls, path):
        d = json.load(open(path))
        m = cls(alpha=d.get("alpha", 1.0), min_support=d.get("min_support", 5))
        m.cells = {k: list(v) for k, v in d.get("cells", {}).items()}
        m.families = {k: list(v) for k, v in d.get("families", {}).items()}
        m.glob = list(d.get("glob", [0, 0]))
        return m
