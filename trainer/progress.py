# -*- coding: utf-8 -*-
"""Progress persistence (spec §10) with atomic writes."""

import json
import os

from .engine import ItemState


def load_progress(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (IOError, OSError, ValueError):
        return {}
    states = {}
    for k, v in data.items():
        states[k] = ItemState.from_dict(v)
    return states


def save_progress(path, states):
    payload = {k: v.to_dict() for k, v in states.items()}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
