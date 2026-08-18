#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate verbs.json against the v2 spec loader rules (§4.4, §5.3)."""

import json
import sys
from pathlib import Path

GROUPS = {"er_regular", "re_regular", "ir_regular", "re_irregular", "ir_irregular", "irregular"}
REQUIRED_TENSES = {
    "present": "simple", "imparfait": "simple", "futur_simple": "simple",
    "futur_proche": "periphrastic", "conditionnel": "simple", "passé_composé": "compound",
}
ETRE_AUX = ["suis", "es", "est", "sommes", "êtes", "sont"]
AVOIR_AUX = ["ai", "as", "a", "avons", "avez", "ont"]
ALLER_AUX = ["vais", "vas", "va", "allons", "allez", "vont"]

errors = []
verb_count = 0


def err(msg):
    errors.append(msg)
    print(f"ERROR: {msg}", file=sys.stderr)


data = json.loads((Path(__file__).parent / "data" / "verbs.json").read_text(encoding="utf-8"))
infinitives = set()
for verb in data["verbs"]:
    verb_count += 1
    inf = verb["infinitive"]
    if inf in infinitives:
        err(f"duplicate infinitive: {inf}")
    infinitives.add(inf)

    if verb.get("auxiliary") not in ("être", "avoir"):
        err(f"{inf}: auxiliary must be être|avoir")
    if verb.get("group") not in GROUPS:
        err(f"{inf}: bad group {verb.get('group')!r}")

    notes = verb.get("notes")
    if notes is not None and not isinstance(notes, str):
        err(f"{inf}: notes must be a string")

    tenses = verb.get("tenses", {})
    for key, expected_type in REQUIRED_TENSES.items():
        if key not in tenses:
            err(f"{inf}: missing required tense {key}")
            continue
        tense = tenses[key]
        forms = tense.get("forms")
        if not isinstance(forms, list) or len(forms) != 6:
            err(f"{inf}/{key}: forms must be exactly 6 entries")
            continue
        if tense.get("type") != expected_type:
            err(f"{inf}/{key}: type {tense.get('type')!r} != {expected_type!r}")
        for form in forms:
            if not isinstance(form, str) or not form.strip():
                err(f"{inf}/{key}: empty form {form!r}")

        if key == "passé_composé":
            aux_set = ETRE_AUX if verb["auxiliary"] == "être" else AVOIR_AUX
            for i, form in enumerate(forms):
                first = form.split(" ")[0]
                if first not in aux_set:
                    err(f"{inf}/passé_composé person {i}: {first!r} not in {aux_set}")
        elif key == "futur_proche":
            for i, form in enumerate(forms):
                first = form.split(" ")[0]
                if first not in ALLER_AUX:
                    err(f"{inf}/futur_proche person {i}: {first!r} not in {ALLER_AUX}")

        fem = tense.get("feminine")
        if key == "passé_composé":
            if verb["auxiliary"] == "être":
                if not isinstance(fem, list) or len(fem) != 6:
                    err(f"{inf}/passé_composé: être-verb must provide feminine (6 entries)")
                else:
                    for i, form in enumerate(fem):
                        if not isinstance(form, str) or not form.strip():
                            err(f"{inf}/passé_composé feminine person {i}: empty form")
                        elif form.split(" ")[0] not in ETRE_AUX:
                            err(f"{inf}/passé_composé feminine person {i}: {form.split(' ')[0]!r} not in {ETRE_AUX}")
            elif fem is not None:
                err(f"{inf}/passé_composé: avoir-verb must NOT have feminine")
        elif fem is not None:
            err(f"{inf}/{key}: feminine forbidden on {tense.get('type')} tense")

# extra tenses beyond the required set are not allowed
for verb in data["verbs"]:
    for key in verb.get("tenses", {}):
        if key not in REQUIRED_TENSES:
            err(f"{verb['infinitive']}: unexpected tense key {key!r}")

print(f"verbs: {verb_count}, unique infinitives: {len(infinitives)}")
if errors:
    print(f"FAILED with {len(errors)} error(s)")
    sys.exit(1)
print("PASS")
