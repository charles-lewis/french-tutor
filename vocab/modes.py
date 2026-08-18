# -*- coding: utf-8 -*-
"""Vocabulary prompt display, answer evaluation, and success feedback (spec §6)."""

from trainer import modes as trainer_modes

DIRECTIONS = ("fr2en", "en2fr")

POS_LABELS = {
    "verb": "verb",
    "noun": "noun",
    "adjective": "adj",
    "adverb": "adv",
    "phrase": "phrase",
}


def normalize(text):
    return trainer_modes.normalize(text)


def is_correct(entry, direction, raw):
    text = normalize(raw).casefold()
    if direction == "fr2en":
        return any(normalize(m).casefold() == text for m in entry["en"])
    return normalize(entry["fr"]).casefold() == text


def expected(entry, direction):
    """The list of accepted strings for scoring/correction display."""
    if direction == "fr2en":
        return list(entry["en"])
    return [entry["fr"]]


def _display_text(entry, direction):
    if direction == "fr2en":
        return entry["fr"]
    return " / ".join(entry["en"])


def prompt(entry, direction):
    """Return (display_line, expected_list)."""
    pos = POS_LABELS.get(entry.get("pos"), entry.get("pos"))
    if direction == "fr2en":
        line = "%s [%s] (en?) ->" % (_display_text(entry, direction), pos)
    else:
        line = "%s [%s] (fr?) ->" % (_display_text(entry, direction), pos)
    return line, expected(entry, direction)


def success_feedback(entry, direction):
    """Informational line after a correct answer, or None (spec §6.4)."""
    notes = entry.get("notes")
    if direction == "fr2en":
        if len(entry["en"]) > 1:
            line = "%s -> %s" % (entry["fr"], " / ".join(entry["en"]))
        else:
            line = None
    else:
        if not notes:
            return None
        line = "%s -> %s" % (entry["fr"], " / ".join(entry["en"]))
    if notes:
        if line:
            return "%s   (%s)" % (line, notes)
        return "(%s)" % notes
    return line
