# -*- coding: utf-8 -*-
"""Load and validate vocab entry sources: verbs.json import + vocab.json (spec §4)."""

import json
import os

from trainer import loader as verb_loader

POS_CATALOG = frozenset({"verb", "noun", "adjective", "adverb", "phrase"})

TRANSLATION_SEP = " / "


class ValidationError(Exception):
    pass


def _validate_entry(entry, errors, source):
    eid = entry.get("id")
    if not isinstance(eid, str) or not eid.strip():
        errors.append("[%s] id must be a non-empty string" % source)
        eid = "<unknown>"

    fr = entry.get("fr")
    if not isinstance(fr, str) or not fr.strip():
        errors.append("[%s/%s] fr must be a non-empty string" % (source, eid))

    en = entry.get("en")
    if not isinstance(en, list) or not en or not all(isinstance(x, str) and x.strip() for x in en):
        errors.append("[%s/%s] en must be a non-empty array of non-empty strings" % (source, eid))

    pos = entry.get("pos")
    if pos not in POS_CATALOG:
        errors.append("[%s/%s] invalid pos %r" % (source, eid, pos))

    notes = entry.get("notes")
    if notes is not None and not isinstance(notes, str):
        errors.append("[%s/%s] notes must be a string" % (source, eid))


def _verb_entry(verb):
    translation = verb.get("translation") or ""
    meanings = [m.strip() for m in translation.split(TRANSLATION_SEP)] if translation else []
    if not meanings:
        meanings = [translation]
    entry = {
        "id": verb["infinitive"],
        "fr": verb["infinitive"],
        "en": [m for m in meanings if m],
        "pos": "verb",
        "group": verb.get("group"),
        "source": "verbs.json",
    }
    if verb.get("notes"):
        entry["notes"] = verb["notes"]
    return entry


def _load_vocab(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (IOError, OSError, ValueError) as exc:
        raise ValidationError("could not load %s: %s" % (path, exc))
    if not isinstance(data, dict) or "entries" not in data:
        raise ValidationError("top-level 'entries' array missing in %s" % path)
    entries = data["entries"]
    if not isinstance(entries, list):
        raise ValidationError("'entries' must be an array in %s" % path)
    return entries


def load_entries(verbs, vocab):
    """Merge verbs.json-derived entries with vocab.json entries.

    'verbs' is a file path (or None). 'vocab' is a single file path, a list
    of file paths, or None. Entries from later vocab files override earlier
    ones with the same id; vocab entries override verbs-derived entries.
    """
    by_id = {}

    if verbs is not None and os.path.isfile(verbs):
        try:
            verb_list = verb_loader.load_verbs(verbs)
        except (IOError, OSError, ValueError) as exc:
            raise ValidationError("could not load %s: %s" % (verbs, exc))
        for verb in verb_list:
            entry = _verb_entry(verb)
            by_id[entry["id"]] = entry

    if isinstance(vocab, str):
        vocab = [vocab]
    for vpath in vocab or []:
        if not os.path.isfile(vpath):
            continue
        raw = _load_vocab(vpath)
        errors = []
        seen = set()
        for entry in raw:
            if not isinstance(entry, dict):
                errors.append("[%s] entry must be an object" % vpath)
                continue
            _validate_entry(entry, errors, vpath)
            eid = entry.get("id")
            if isinstance(eid, str) and eid in seen:
                errors.append("duplicate entry id: %s" % eid)
            seen.add(eid)
        if errors:
            raise ValidationError("\n".join(errors))
        source = os.path.basename(vpath)
        for entry in raw:
            tagged = dict(entry)
            tagged["source"] = source
            by_id[entry["id"]] = tagged

    return list(by_id.values())
