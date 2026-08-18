# -*- coding: utf-8 -*-
"""Load and validate verbs.json (spec §4.4, §5.3, §5.5)."""

import json

GROUPS = frozenset({
    "er_regular", "re_regular", "ir_regular",
    "re_irregular", "ir_irregular", "irregular",
})

REQUIRED_TENSES = {
    "present": "simple",
    "imparfait": "simple",
    "futur_simple": "simple",
    "futur_proche": "periphrastic",
    "conditionnel": "simple",
    "pass\u00e9_compos\u00e9": "compound",
}

ETRE_AUX = ["suis", "es", "est", "sommes", "\u00eates", "sont"]
AVOIR_AUX = ["ai", "as", "a", "avons", "avez", "ont"]
ALLER_AUX = ["vais", "vas", "va", "allons", "allez", "vont"]


class ValidationError(Exception):
    pass


def _validate_verb(verb, errors):
    inf = verb.get("infinitive")
    if not isinstance(inf, str) or not inf.strip():
        errors.append("infinitive must be a non-empty string")
        inf = "<unknown>"

    auxiliary = verb.get("auxiliary")
    if auxiliary not in ("\u00eatre", "avoir"):
        errors.append("%s: auxiliary must be 'être' or 'avoir'" % inf)

    group = verb.get("group")
    if group not in GROUPS:
        errors.append("%s: invalid group %r" % (inf, group))

    notes = verb.get("notes")
    if notes is not None and not isinstance(notes, str):
        errors.append("%s: notes must be a string" % inf)

    tenses = verb.get("tenses")
    if not isinstance(tenses, dict):
        errors.append("%s: 'tenses' must be an object" % inf)
        return

    for key, expected_type in REQUIRED_TENSES.items():
        if key not in tenses:
            errors.append("%s: missing required tense %s" % (inf, key))
            continue
        tense = tenses[key]
        if not isinstance(tense, dict):
            errors.append("%s/%s: tense must be an object" % (inf, key))
            continue
        forms = tense.get("forms")
        if not isinstance(forms, list) or len(forms) != 6:
            errors.append("%s/%s: forms must be exactly 6 entries" % (inf, key))
            continue
        if tense.get("type") != expected_type:
            errors.append("%s/%s: type %r != %r" % (inf, key, tense.get("type"), expected_type))
        for form in forms:
            if not isinstance(form, str) or not form.strip():
                errors.append("%s/%s: empty or invalid form %r" % (inf, key, form))
        if not all(isinstance(f, str) and f.strip() for f in forms):
            continue

        if key == "pass\u00e9_compos\u00e9":
            aux_set = ETRE_AUX if auxiliary == "\u00eatre" else AVOIR_AUX
            for i, form in enumerate(forms):
                first = form.split(" ")[0]
                if first not in aux_set:
                    errors.append("%s/passé_composé person %d: %r not in %r" % (inf, i, first, aux_set))
            fem = tense.get("feminine")
            if auxiliary == "\u00eatre":
                if not isinstance(fem, list) or len(fem) != 6:
                    errors.append("%s/passé_composé: être-verb must provide feminine (6 entries)" % inf)
                else:
                    for i, form in enumerate(fem):
                        if not isinstance(form, str) or not form.strip():
                            errors.append("%s/passé_composé feminine person %d: empty form" % (inf, i))
                        elif form.split(" ")[0] not in ETRE_AUX:
                            errors.append("%s/passé_composé feminine person %d: %r not in %r"
                                          % (inf, i, form.split(" ")[0], ETRE_AUX))
            elif fem is not None:
                errors.append("%s/passé_composé: avoir-verb must NOT have feminine" % inf)
        elif key == "futur_proche":
            for i, form in enumerate(forms):
                first = form.split(" ")[0]
                if first not in ALLER_AUX:
                    errors.append("%s/futur_proche person %d: %r not in %r" % (inf, i, first, ALLER_AUX))
        elif tense.get("feminine") is not None:
            errors.append("%s/%s: feminine forbidden on %s tense" % (inf, key, tense.get("type")))

    for key in tenses:
        if key not in REQUIRED_TENSES:
            errors.append("%s: unexpected tense key %r" % (inf, key))


def load_verbs(path):
    """Load verbs.json and return the verb list, raising ValidationError on failure."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "verbs" not in data:
        raise ValidationError("top-level 'verbs' array missing")
    verbs = data["verbs"]
    if not isinstance(verbs, list):
        raise ValidationError("'verbs' must be an array")

    errors = []
    seen = set()
    for verb in verbs:
        if not isinstance(verb, dict):
            errors.append("verb entries must be objects")
            continue
        _validate_verb(verb, errors)
        inf = verb.get("infinitive")
        if isinstance(inf, str):
            if inf in seen:
                errors.append("duplicate infinitive: %s" % inf)
            seen.add(inf)

    if errors:
        raise ValidationError("\n".join(errors))
    return verbs
