# -*- coding: utf-8 -*-
"""Prompt display: elision-aware pronouns and gender variants (spec §3.2, §6.4)."""

import os
import random
import re
import sys

PRONOUNS = {0: "je", 1: "tu", 2: "il/elle", 3: "nous", 4: "vous", 5: "ils/elles"}
FEM_PRONOUNS = {0: "je", 1: "tu", 2: "elle", 3: "nous", 4: "vous", 5: "elles"}
MASC_COMPOUND = {0: "je", 1: "tu", 2: "il", 3: "nous", 4: "vous", 5: "ils"}
FEM_COMPOUND = {0: "je", 1: "tu", 2: "elle", 3: "nous", 4: "vous", 5: "elles"}
VOWEL_START = frozenset("aeiou\u00e0\u00e2\u00e6\u00e9\u00e8\u00ea\u00eb\u00ef\u00ee\u00f4\u0153\u00f9\u00fb\u00fch")
WS_RUN = re.compile(r"\s+")

COLOR = False
if sys.stdout.isatty():
    if os.name == "nt":
        try:
            os.system("")
            COLOR = True
        except Exception:
            pass
    else:
        COLOR = os.environ.get("TERM", "") not in ("", "dumb")

GREEN = "\x1b[32m"
RED = "\x1b[31m"
BOLD = "\x1b[1m"
RESET = "\x1b[0m"


def _paint(text, code):
    return code + text + RESET if COLOR else text


def green(text):
    return _paint(text, GREEN)


def red(text):
    return _paint(text, RED)


def bold(text):
    return _paint(text, BOLD)


def normalize(text):
    """Trim leading/trailing whitespace and collapse internal runs to single spaces."""
    return WS_RUN.sub(" ", text).strip()


def starts_with_vowel(text):
    return bool(text) and text[:1].casefold() in VOWEL_START


def resolve_variant(tense, gender):
    """Return the forms key ('forms' or 'feminine') to use for the current gender scope."""
    if gender == "m":
        return "forms"
    if gender == "f":
        return "feminine" if "feminine" in tense else "forms"
    return "feminine" if "feminine" in tense and random.random() < 0.5 else "forms"


def expected_answer(verb, tense_key, person, gender):
    tense = verb["tenses"][tense_key]
    return tense[resolve_variant(tense, gender)][person]


def prompt(verb, tense_key, person, gender):
    """Return (display_line, expected_answer)."""
    tense = verb["tenses"][tense_key]
    variant = resolve_variant(tense, gender)
    expected = tense[variant][person]

    if tense["type"] == "compound":
        pronoun_table = FEM_COMPOUND if variant == "feminine" else MASC_COMPOUND
        pronoun = pronoun_table[person]
        if person == 0 and starts_with_vowel(expected):
            pronoun = "j'"
        full_expected = pronoun + (" " if not pronoun.endswith("'") else "") + expected
        prompt_pronoun = pronoun_table[person]
        # être-verbs agree with subject gender; the pronoun alone doesn't
        # reveal it for je/tu/nous/vous, so add an explicit gender hint.
        if "feminine" in tense and person in (0, 1, 3, 4):
            gender_note = " (m)" if variant == "forms" else " (f)"
            prompt_pronoun += gender_note
        line = "%s (%s) - %s - [%s]?" % (
            verb["infinitive"], verb["translation"], tense["label"],
            prompt_pronoun)
        return line, full_expected, full_expected

    pronoun = FEM_PRONOUNS[person] if variant == "feminine" else PRONOUNS[person]
    if person == 0 and starts_with_vowel(expected):
        pronoun = "j'"
    full_expected = pronoun + " " + expected
    line = "%s (%s) - %s - %s ->" % (
        verb["infinitive"], verb["translation"], tense["label"], pronoun)
    return line, expected, full_expected


def drill_header(verb, tense_key):
    tense = verb["tenses"][tense_key]
    return "%s (%s) - %s" % (verb["infinitive"], verb["translation"], tense["label"])
