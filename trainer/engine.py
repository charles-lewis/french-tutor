# -*- coding: utf-8 -*-
"""Item state, weighted spaced-repetition scheduling (spec §8)."""

import random
from datetime import datetime

PERSONS = (0, 1, 2, 3, 4, 5)

_UNSEEN_WEIGHT = 10.0
_ISO_FMTS = ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S")
MAX_RECENT = 10


class ItemState(object):
    def __init__(self, success_count=0, failure_count=0, streak=0, longest_streak=0,
                 last_seen=None, last_result=None, avg_response_time=None,
                 recent_results=None, recent_times=None, expected=None):
        self.success_count = success_count
        self.failure_count = failure_count
        self.streak = streak
        self.longest_streak = longest_streak
        self.last_seen = last_seen
        self.last_result = last_result
        self.avg_response_time = avg_response_time
        self.recent_results = recent_results if recent_results is not None else []
        self.recent_times = recent_times if recent_times is not None else []
        self.expected = expected

    def to_dict(self):
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "streak": self.streak,
            "longest_streak": self.longest_streak,
            "last_seen": self.last_seen,
            "last_result": self.last_result,
            "avg_response_time": self.avg_response_time,
            "recent_results": self.recent_results,
            "recent_times": self.recent_times,
            "expected": self.expected,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            streak=data.get("streak", 0),
            longest_streak=data.get("longest_streak", 0),
            last_seen=data.get("last_seen"),
            last_result=data.get("last_result"),
            avg_response_time=data.get("avg_response_time"),
            recent_results=data.get("recent_results", []),
            recent_times=data.get("recent_times", []),
            expected=data.get("expected"),
        )


def key(infinitive, tense_key, person_index):
    return "%s|%s|%d" % (infinitive, tense_key, person_index)


def get_state(states, infinitive, tense_key, person_index):
    return states.get(key(infinitive, tense_key, person_index), ItemState())


def _parse_iso(text):
    for fmt in _ISO_FMTS:
        try:
            return datetime.strptime(text, fmt)
        except (ValueError, TypeError):
            continue
    return None


def weight(state, now):
    """§8.2 weight function. Unseen items default to 10 * noise."""
    if not state.last_seen:
        return _UNSEEN_WEIGHT * random.uniform(0.5, 1.5)
    last = _parse_iso(state.last_seen)
    if last is None:
        return _UNSEEN_WEIGHT * random.uniform(0.5, 1.5)
    age_hours = max(0.0, (now - last).total_seconds()) / 3600.0
    freshness = 1.0 + (age_hours / 24.0) ** 0.6
    recency_boost = 6.0 if state.last_result == "incorrect" else 1.0
    noise = random.uniform(0.5, 1.5)
    return (state.failure_count + 1) * freshness * recency_boost * noise / (state.streak + 1)


def select_unit(units, states, now):
    """Weighted-random selection of a (verb, tense) unit (§8.3)."""
    if not units:
        return None
    weights = []
    for verb, tense_key in units:
        w = sum(weight(get_state(states, verb["infinitive"], tense_key, p), now) for p in PERSONS)
        weights.append(max(w, 1e-9))
    total = sum(weights)
    r = random.uniform(0.0, total)
    acc = 0.0
    for index, ((verb, tense_key), w) in enumerate(zip(units, weights)):
        acc += w
        if r <= acc:
            return verb, tense_key
    return units[-1]


def record_answer(state, correct, seconds, now, expected=None):
    if correct:
        state.success_count += 1
        state.streak += 1
        if expected is not None:
            state.expected = expected
    else:
        state.failure_count += 1
        state.streak = 0
    state.longest_streak = max(state.longest_streak, state.streak)
    state.last_result = "correct" if correct else "incorrect"
    state.last_seen = now.isoformat()
    state.recent_results.append(correct)
    if len(state.recent_results) > MAX_RECENT:
        del state.recent_results[0]
    if seconds is not None:
        state.recent_times.append(seconds)
        if len(state.recent_times) > MAX_RECENT:
            del state.recent_times[0]
        n = state.success_count + state.failure_count
        if state.avg_response_time is None:
            state.avg_response_time = seconds
        else:
            state.avg_response_time = (state.avg_response_time * (n - 1) + seconds) / n


def windowed_accuracy(state):
    """Accuracy (%) over the last MAX_RECENT results, or None if none recorded."""
    if not state.recent_results:
        return None
    return 100.0 * sum(state.recent_results) / len(state.recent_results)


def windowed_avg_time(state):
    """Mean response time (s) over the last MAX_RECENT responses, or None."""
    if not state.recent_times:
        return None
    return sum(state.recent_times) / len(state.recent_times)


def perfect_verb_names(units, states):
    """Set of infinitive names whose every item in scope was last answered
    correctly (all items tested, all last results correct)."""
    groups = {}
    for verb, tense_key in units:
        groups.setdefault(verb["infinitive"], []).append((tense_key, verb))
    perfect = set()
    for name, tense_items in groups.items():
        tested = False
        ok = True
        for tense_key, verb in tense_items:
            tense_type = verb["tenses"][tense_key]["type"]
            # Compound tenses record only under person 0
            persons_to_check = [0] if tense_type == "compound" else PERSONS
            for p in persons_to_check:
                st = get_state(states, name, tense_key, p)
                if st.last_seen is None:
                    ok = False
                else:
                    tested = True
                    if st.last_result != "correct":
                        ok = False
        if tested and ok:
            perfect.add(name)
    return perfect
