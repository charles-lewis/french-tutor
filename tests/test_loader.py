# -*- coding: utf-8 -*-
"""Loader validation tests (spec §4.4, §5.3, §5.5)."""

import copy
import json
import os
import tempfile
import unittest

from trainer import loader

from tests._fixtures import VALID_AVOIR_VERB, VALID_ETRE_VERB


def _write_verbs(verbs):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"verbs": verbs}, fh, ensure_ascii=False)
    return path


class LoaderTest(unittest.TestCase):
    def test_loads_valid_verbs(self):
        path = _write_verbs([VALID_AVOIR_VERB, VALID_ETRE_VERB])
        try:
            verbs = loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertEqual([v["infinitive"] for v in verbs], ["finir", "aller"])

    def test_missing_tenses_key(self):
        path = _write_verbs([{"not": "a verb"}])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("tenses", str(ctx.exception))

    def test_missing_required_tense(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        del verb["tenses"]["imparfait"]
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("missing required tense imparfait", str(ctx.exception))

    def test_wrong_tense_type(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["tenses"]["futur_proche"]["type"] = "simple"
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("type 'simple' != 'periphrastic'", str(ctx.exception))

    def test_forms_must_have_six_entries(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["tenses"]["present"]["forms"] = ["a", "b"]
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("exactly 6 entries", str(ctx.exception))

    def test_empty_form_rejected(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["tenses"]["present"]["forms"][0] = "   "
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("empty or invalid form", str(ctx.exception))

    def test_bad_group_rejected(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["group"] = "nope"
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("invalid group", str(ctx.exception))

    def test_bad_auxiliary_rejected(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["auxiliary"] = "aller"
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("auxiliary must be", str(ctx.exception))

    def test_string_notes_accepted(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["notes"] = "takes avoir"
        path = _write_verbs([verb])
        try:
            verbs = loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertEqual(verbs[0]["notes"], "takes avoir")

    def test_non_string_notes_rejected(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["notes"] = 42
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("notes must be a string", str(ctx.exception))

    def test_avoir_verb_must_not_have_feminine(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["tenses"]["pass\u00e9_compos\u00e9"]["feminine"] = ["x"] * 6
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("must NOT have feminine", str(ctx.exception))

    def test_etre_verb_requires_feminine(self):
        verb = copy.deepcopy(VALID_ETRE_VERB)
        del verb["tenses"]["pass\u00e9_compos\u00e9"]["feminine"]
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("must provide feminine", str(ctx.exception))

    def test_compound_first_word_must_be_aux(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["tenses"]["pass\u00e9_compos\u00e9"]["forms"][0] = "suis fini"
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("not in", str(ctx.exception))

    def test_periphrastic_first_word_must_be_aller(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["tenses"]["futur_proche"]["forms"][0] = "irai finir"
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("futur_proche", str(ctx.exception))

    def test_feminine_forbidden_on_simple_tense(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["tenses"]["present"]["feminine"] = ["x"] * 6
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("feminine forbidden", str(ctx.exception))

    def test_duplicate_infinitive_rejected(self):
        path = _write_verbs([VALID_AVOIR_VERB, copy.deepcopy(VALID_AVOIR_VERB)])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("duplicate infinitive", str(ctx.exception))

    def test_unexpected_tense_key_rejected(self):
        verb = copy.deepcopy(VALID_AVOIR_VERB)
        verb["tenses"]["plus_que_parfait"] = {"label": "x", "type": "simple", "forms": ["x"] * 6}
        path = _write_verbs([verb])
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("unexpected tense key", str(ctx.exception))

    def test_top_level_missing_verbs(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"foo": []}, fh)
        try:
            with self.assertRaises(loader.ValidationError) as ctx:
                loader.load_verbs(path)
        finally:
            os.remove(path)
        self.assertIn("top-level", str(ctx.exception))


class RealDatasetTest(unittest.TestCase):
    def test_real_dataset_passes_validation(self):
        import trainer.main as main
        if not os.path.exists(str(main.VERBS_PATH)):
            self.skipTest("data/verbs.json not present")
        verbs = loader.load_verbs(str(main.VERBS_PATH))
        self.assertEqual(len(verbs), 54)


if __name__ == "__main__":
    unittest.main()
