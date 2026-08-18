# -*- coding: utf-8 -*-
"""Vocabulary item selection: weighted sampling over (entry, direction) (spec §7)."""

import random
from datetime import datetime

from trainer import engine as trainer_engine

DIRECTIONS = ("fr2en", "en2fr")


def key(entry_id, direction):
    return "%s|%s" % (entry_id, direction)


def get_state(states, entry_id, direction):
    return states.get(key(entry_id, direction), trainer_engine.ItemState())


def item_weight(entry, direction, states, now):
    """Reuse the verb trainer's weight formula for one (entry, direction) item."""
    state = get_state(states, entry["id"], direction)
    return trainer_engine.weight(state, now)


def select_item(entries, directions, states, now):
    """Weighted-random selection of (entry, direction) across the active scope."""
    weights = []
    for entry in entries:
        for direction in directions:
            w = item_weight(entry, direction, states, now)
            weights.append((entry, direction, max(w, 1e-9)))
    if not weights:
        return None
    total = sum(w for _, _, w in weights)
    r = random.uniform(0.0, total)
    acc = 0.0
    for entry, direction, w in weights:
        acc += w
        if r <= acc:
            return entry, direction
    return weights[-1][0], weights[-1][1]
