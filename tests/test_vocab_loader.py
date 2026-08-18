# -*- coding: utf-8 -*-
"""Vocabulary loader tests (spec §4)."""

import json
import os
import tempfile
import unittest

from tests._fixtures import make_verb

from vocab import loader


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)


class LoaderTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.verbs_path = os.path.join(self.dir, "verbs.json")
        self.vocab_path = os.path.join(self.dir, "vocab.json")

    def _verbs(self):
        return {"verbs": [
            make_verb(infinitive="faire", translation="to do / to make",
                      group="re_irregular", auxiliary="avoir",
                      present=["fais", "fais", "fait", "faisons", "faites", "font"]),
            make_verb(infinitive="venir", translation="to come",
                      group="ir_irregular", auxiliary="\u00eatre",
                      present=["viens", "viens", "vient", "venons", "venez", "viennent"],
                      pc_masc=["suis venu", "es venu", "est venu",
                               "sommes venus", "\u00eates venus", "sont venus"],
                      pc_fem=["suis venue", "es venue", "est venue",
                              "sommes venues", "\u00eates venues", "sont venues"]),
        ]}

    def test_verbs_only_import(self):
        _write(self.verbs_path, self._verbs())
        entries = loader.load_entries(verbs=self.verbs_path, vocab=None)
        by_id = {e["id"]: e for e in entries}
        self.assertEqual(by_id["faire"]["en"], ["to do", "to make"])
        self.assertEqual(by_id["faire"]["pos"], "verb")
        self.assertEqual(by_id["venir"]["en"], ["to come"])

    def test_vocab_overrides_verb_entry(self):
        _write(self.verbs_path, self._verbs())
        _write(self.vocab_path, {"entries": [
            {"id": "faire", "fr": "faire", "en": ["to do", "to make"],
             "pos": "verb", "notes": "extremely irregular"},
        ]})
        entries = loader.load_entries(verbs=self.verbs_path, vocab=self.vocab_path)
        by_id = {e["id"]: e for e in entries}
        self.assertEqual(by_id["faire"]["notes"], "extremely irregular")
        self.assertNotIn("notes", by_id["venir"])

    def test_verb_notes_propagate_to_entry(self):
        _write(self.verbs_path, {"verbs": [
            make_verb(infinitive="faire", translation="to do / to make",
                      group="re_irregular", auxiliary="avoir",
                      present=["fais", "fais", "fait", "faisons", "faites", "font"],
                      notes="very irregular stem"),
        ]})
        entries = loader.load_entries(verbs=self.verbs_path, vocab=None)
        by_id = {e["id"]: e for e in entries}
        self.assertEqual(by_id["faire"]["notes"], "very irregular stem")

    def test_verb_entries_tagged_with_source(self):
        _write(self.verbs_path, self._verbs())
        entries = loader.load_entries(verbs=self.verbs_path, vocab=None)
        by_id = {e["id"]: e for e in entries}
        self.assertEqual(by_id["faire"]["source"], "verbs.json")

    def test_vocab_entries_tagged_with_source(self):
        _write(self.vocab_path, {"entries": [
            {"id": "le_loyer", "fr": "le loyer", "en": ["the rent"], "pos": "noun"},
        ]})
        entries = loader.load_entries(verbs=None, vocab=self.vocab_path)
        self.assertEqual(entries[0]["source"], "vocab.json")

    def test_duplicate_vocab_id_rejected(self):
        _write(self.vocab_path, {"entries": [
            {"id": "le_chat", "fr": "le chat", "en": ["the cat"], "pos": "noun"},
            {"id": "le_chat", "fr": "le chat", "en": ["the cat"], "pos": "noun"},
        ]})
        with self.assertRaises(loader.ValidationError):
            loader.load_entries(verbs=None, vocab=self.vocab_path)

    def test_empty_english_rejected(self):
        _write(self.vocab_path, {"entries": [
            {"id": "x", "fr": "x", "en": [], "pos": "noun"},
        ]})
        with self.assertRaises(loader.ValidationError):
            loader.load_entries(verbs=None, vocab=self.vocab_path)

    def test_invalid_pos_rejected(self):
        _write(self.vocab_path, {"entries": [
            {"id": "x", "fr": "x", "en": ["x"], "pos": "conjunction"},
        ]})
        with self.assertRaises(loader.ValidationError):
            loader.load_entries(verbs=None, vocab=self.vocab_path)

    def test_missing_source_yields_empty(self):
        self.assertEqual(loader.load_entries(verbs=None, vocab=None), [])

    def test_multiple_vocab_files_override_in_order(self):
        _write(self.vocab_path, {"entries": [
            {"id": "le_loyer", "fr": "le loyer", "en": ["the rent"], "pos": "noun"},
            {"id": "la_cave", "fr": "la cave", "en": ["the cellar"], "pos": "noun"},
        ]})
        extra_path = os.path.join(self.dir, "vocab_extra.json")
        _write(extra_path, {"entries": [
            {"id": "le_loyer", "fr": "le loyer", "en": ["the rent"], "pos": "noun",
             "notes": "masculine noun"},
            {"id": "le_bail", "fr": "le bail", "en": ["the lease"], "pos": "noun"},
        ]})
        entries = loader.load_entries(verbs=None, vocab=[self.vocab_path, extra_path])
        by_id = {e["id"]: e for e in entries}
        self.assertEqual(by_id["le_loyer"]["notes"], "masculine noun")
        self.assertEqual(by_id["la_cave"]["en"], ["the cellar"])
        self.assertEqual(by_id["le_bail"]["en"], ["the lease"])

    def test_corrupt_verbs_file_raises(self):
        with open(self.verbs_path, "w", encoding="utf-8") as fh:
            fh.write("not json {{")
        with self.assertRaises(loader.ValidationError):
            loader.load_entries(verbs=self.verbs_path, vocab=None)


if __name__ == "__main__":
    unittest.main()
