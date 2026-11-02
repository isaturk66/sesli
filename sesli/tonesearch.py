"""Tune-by-ear search logic (no UI). Finds the voice character a listener prefers from blind choices.

Space: three character axes in [-1, 1] (clarity, warmth, air); each maps to a few EQ moves.
Phase 1 "explore": 2 rounds of 4 clearly different options (one is always the current point, hidden),
         so the listener first picks a direction. If they can't tell, the next round is bolder.
Phase 2 "refine": blind pairs along one axis at a time with a shrinking step. "Can't tell" at a big
         step -> try bolder once; at a small step -> that axis is settled. Stops early when all settle.
Phase 3 "check": tuned vs original, asked twice with sides re-randomised (guards against drift:
         after many small steps ears adapt, and the end point may not beat the start).
Hard caps keep it short: <= 2 explore rounds, <= MAX_PAIRS pairs, 2 checks.
"""
import random
import numpy as np

AXES = {
    'clarity': [('peak', 300, -3.0, 1.0), ('peak', 3500, 3.0, 0.8)],     # less mud, more presence
    'warmth':  [('lowshelf', 180, 4.0, 0.7), ('peak', 2800, -1.5, 1.0)],  # fuller chest, softer bite
    'air':     [('highshelf', 10000, 4.0, 0.7)],                          # crisp top end
}
NAMES = list(AXES)
PRESETS = [  # phase-1 round-1 characters (besides "unchanged")
    {'clarity': 0.8, 'warmth': -0.3, 'air': 0.4},   # clear
    {'clarity': -0.2, 'warmth': 0.9, 'air': -0.3},  # warm / deep
    {'clarity': 0.3, 'warmth': -0.1, 'air': 0.9},   # bright / crisp
]
MAX_EXPLORE = 2
MAX_PAIRS = 10
STEP0 = 0.35          # first refine step
STEP_MIN = 0.12       # below this an axis counts as settled
BOLDER = 1.6          # "can't tell" at a big step -> try this much bigger, once per axis
ROUND2_RADIUS = 0.5
SAME_SIDE_STREAK = 5  # this many identical letters in a row looks like habit, not preference


def character_eq(pos):
    eq = []
    for ax, amt in pos.items():
        for kind, f, g, q in AXES[ax]:
            if abs(amt) > 1e-3:
                eq.append([kind, float(f), float(g * amt), float(q)])
    return eq


def clip(pos):
    return {k: float(np.clip(v, -1, 1)) for k, v in pos.items()}


ZERO = {a: 0.0 for a in NAMES}


class ToneSearch:
    def __init__(self, start=None, rng=None):
        self.r = rng or random.Random()
        self.pos = dict(start or ZERO)
        self.phase = 'explore'
        self.explore_round = 0
        self.explore_scale = 1.0
        self.pairs = 0
        self.axis_i = 0
        self.step = {a: STEP0 for a in NAMES}
        self.boosted = {a: False for a in NAMES}
        self.settled = {a: False for a in NAMES}
        self.tried_other_dir = {a: False for a in NAMES}
        self.dir = {a: self.r.choice([-1, 1]) for a in NAMES}
        self.checks = []
        self.letters = []
        self.history = []
        self.trial = None
        self.result = None   # 'tuned' | 'original' | 'mixed' when finished

    # ---- what to show next ----
    def next(self):
        """Returns a trial dict: {'kind', 'options': [pos, ...], 'labels': [...]} or None when done."""
        if self.phase == 'explore':
            if self.explore_round == 0:
                opts = [dict(self.pos)] + [clip({a: p[a] * self.explore_scale for a in NAMES}) for p in PRESETS]
            else:
                opts = [dict(self.pos)]
                dirs = self._spread_dirs(3)
                for d in dirs:
                    opts.append(clip({a: self.pos[a] + ROUND2_RADIUS * self.explore_scale * d[a] for a in NAMES}))
            self.r.shuffle(opts)
            self.trial = {'kind': 'multi', 'options': opts}
            return self.trial
        if self.phase == 'refine':
            ax = self._next_axis()
            if ax is None or self.pairs >= MAX_PAIRS:
                self.phase = 'check'
                return self.next()
            cand = dict(self.pos)
            cand[ax] = float(np.clip(self.pos[ax] + self.dir[ax] * self.step[ax], -1, 1))
            if abs(cand[ax] - self.pos[ax]) < 1e-6:  # at the edge: go the other way
                self.dir[ax] *= -1
                cand[ax] = float(np.clip(self.pos[ax] + self.dir[ax] * self.step[ax], -1, 1))
            opts = [dict(self.pos), cand]
            flip = self.r.random() < 0.5
            self.trial = {'kind': 'pair', 'axis': ax, 'current': dict(self.pos), 'candidate': cand,
                          'options': opts[::-1] if flip else opts}
            return self.trial
        if self.phase == 'check':
            if all(abs(v) < 1e-3 for v in self.pos.values()):
                self.result = 'original'
                self.phase = 'done'
                return None
            if len(self.checks) >= 2:
                self._finish_checks()
                return None
            opts = [dict(ZERO), dict(self.pos)]
            if self.r.random() < 0.5:
                opts.reverse()
            self.trial = {'kind': 'check', 'tuned': dict(self.pos), 'options': opts}
            return self.trial
        return None

    # ---- answers ----
    def answer(self, choice):
        """choice: index into trial['options'], or None for "can't tell"."""
        t = self.trial
        letter = None if choice is None else 'ABCD'[choice]
        self.letters.append(letter)
        habit = self.same_side_streak()
        self.history.append({'kind': t['kind'], 'choice': letter, 'habit_suspect': habit,
                             'options': t['options'], 'pos_before': dict(self.pos)})
        if t['kind'] == 'multi':
            self.explore_round += 1
            if choice is None:
                self.explore_scale = min(self.explore_scale * 1.4, 1.25)   # bolder next round
            else:
                self.pos = dict(t['options'][choice])
            if self.explore_round >= MAX_EXPLORE:
                self.phase = 'refine'
        elif t['kind'] == 'pair':
            ax = t['axis']
            self.pairs += 1
            cand_won = choice is not None and t['options'][choice] == t['candidate']
            if habit and cand_won:
                cand_won = False  # a habit streak is weak evidence: don't move on it
            if choice is None:
                if self.step[ax] >= 0.3 and not self.boosted[ax]:
                    self.step[ax] = min(self.step[ax] * BOLDER, 0.8)
                    self.boosted[ax] = True
                else:
                    self.settled[ax] = True
            elif cand_won:
                self.pos = dict(t['candidate'])
                self.tried_other_dir[ax] = False
                self.step[ax] *= 0.75
            else:
                if not self.tried_other_dir[ax]:
                    self.dir[ax] *= -1
                    self.tried_other_dir[ax] = True
                else:
                    self.step[ax] *= 0.5
                    self.tried_other_dir[ax] = False
            if self.step[ax] < STEP_MIN:
                self.settled[ax] = True
            self.axis_i += 1
        elif t['kind'] == 'check':
            tuned_won = None if (choice is None or habit) else t['options'][choice] == t['tuned']
            self.checks.append(tuned_won)

    def same_side_streak(self):
        last = self.letters[-SAME_SIDE_STREAK:]
        return len(last) == SAME_SIDE_STREAK and last[0] is not None and all(x == last[0] for x in last)

    def _finish_checks(self):
        wins = sum(1 for c in self.checks if c is True)
        losses = sum(1 for c in self.checks if c is False)
        if losses == 2:
            self.result = 'original'
        elif wins == 2 or (wins == 1 and losses == 0):
            self.result = 'tuned'
        else:
            self.result = 'mixed'
        self.phase = 'done'

    def _next_axis(self):
        live = [a for a in NAMES if not self.settled[a]]
        if not live:
            return None
        return live[self.axis_i % len(live)]

    def _spread_dirs(self, n):
        """n well-spread unit directions in the 3-axis space."""
        best = None
        for _ in range(50):
            ds = []
            for _ in range(n):
                v = np.array([self.r.gauss(0, 1) for _ in NAMES])
                ds.append(v / (np.linalg.norm(v) + 1e-9))
            spread = min(np.linalg.norm(a - b) for i, a in enumerate(ds) for b in ds[i + 1:])
            if best is None or spread > best[0]:
                best = (spread, ds)
        return [dict(zip(NAMES, d)) for d in best[1]]

    def max_trials(self):
        return MAX_EXPLORE + MAX_PAIRS + 2

    def describe(self, pos=None):
        pos = pos or self.pos
        return {a: round(v, 2) for a, v in pos.items() if abs(v) > 1e-3}
