# -*- coding: utf-8 -*-
"""Prompt display tests: elision, gender variants, normalization (§3.2, §6.4, §7)."""

import unittest
from unittest import mock

from trainer import modes

from tests._fixtures import ALLER_PC, ALLER_PC_FEM, ALLER_PRESENT, make_verb


class NormalizeTest(unittest.TestCase):
    def test_trims_and_collapses(self):
        self.assertEqual(modes.normalize("  est   all\u00e9e  "), "est all\u00e9e")
        self.assertEqual(modes.normalize("vais"), "vais")
        self.assertEqual(modes.normalize("\t ai \t eu \n"), "ai eu")

    def test_empty(self):
        self.assertEqual(modes.normalize(""), "")


class VowelTest(unittest.TestCase):
    def test_vowel_starts(self):
        self.assertTrue(modes.starts_with_vowel("aime"))
        self.assertTrue(modes.starts_with_vowel("\u00e9cris"))
        self.assertTrue(modes.starts_with_vowel("habite"))
        self.assertFalse(modes.starts_with_vowel("vais"))
        self.assertFalse(modes.starts_with_vowel(""))
        self.assertFalse(modes.starts_with_vowel("cours"))


class PromptTest(unittest.TestCase):
    def setUp(self):
        self.aller = make_verb("aller", present=ALLER_PRESENT,
                               pc_masc=ALLER_PC, pc_fem=ALLER_PC_FEM)

    def test_elision_on_vowel_start(self):
        line, expected = modes.prompt(self.aller, "present", 0, "m")
        self.assertEqual(expected, "vais")
        self.assertIn("je ->", line)

    def test_no_elision_needed(self):
        # present[0] starts with 'v' -> 'je', not "j'"
        self.assertEqual(modes.prompt(self.aller, "present", 0, "m")[1], "vais")
        self.assertNotIn("j'", modes.prompt(self.aller, "present", 0, "m")[0])

    def test_masculine_prompt(self):
        line, expected = modes.prompt(self.aller, "pass\u00e9_compos\u00e9", 2, "m")
        self.assertEqual(expected, "il est all\u00e9")
        self.assertIn("[il]?", line)

    def test_feminine_prompt_uses_elle(self):
        line, expected = modes.prompt(self.aller, "pass\u00e9_compos\u00e9", 2, "f")
        self.assertEqual(expected, "elle est all\u00e9e")
        self.assertIn("[elle]?", line)

    def test_feminine_person_5_uses_elles(self):
        line, expected = modes.prompt(self.aller, "pass\u00e9_compos\u00e9", 5, "f")
        self.assertEqual(expected, "elles sont all\u00e9es")
        self.assertIn("[elles]?", line)

    def test_both_gender_random_draw(self):
        with mock.patch("trainer.modes.random.random", return_value=0.0):
            variant = modes.resolve_variant(self.aller["tenses"]["pass\u00e9_compos\u00e9"], "both")
        self.assertEqual(variant, "feminine")
        with mock.patch("trainer.modes.random.random", return_value=0.99):
            variant = modes.resolve_variant(self.aller["tenses"]["pass\u00e9_compos\u00e9"], "both")
        self.assertEqual(variant, "forms")

    def test_avoir_verb_both_falls_back_to_forms(self):
        finir = make_verb("finir", auxiliary="avoir", present=ALLER_PRESENT)
        with mock.patch("trainer.modes.random.random", return_value=0.0):
            variant = modes.resolve_variant(finir["tenses"]["pass\u00e9_compos\u00e9"], "both")
        self.assertEqual(variant, "forms")

    def test_drill_header_includes_translation(self):
        header = modes.drill_header(self.aller, "present")
        self.assertIn("aller (to go) - pr\u00e9sent", header)

    def test_prompt_includes_translation(self):
        line, _ = modes.prompt(self.aller, "present", 1, "m")
        self.assertIn("aller (to go)", line)

    def test_avoir_compound_shows_helper_and_participle(self):
        finir = make_verb("finir", auxiliary="avoir", present=ALLER_PRESENT,
                          pc_masc=["ai fini", "as fini", "a fini",
                                   "avons fini", "avez fini", "ont fini"])
        line, expected = modes.prompt(finir, "pass\u00e9_compos\u00e9", 2, "m")
        self.assertEqual(expected, "il a fini")
        self.assertIn("[il]?", line)

    def test_avoir_compound_elision_no_extra_space(self):
        finir = make_verb("finir", auxiliary="avoir", present=ALLER_PRESENT,
                          pc_masc=["ai fini", "as fini", "a fini",
                                   "avons fini", "avez fini", "ont fini"])
        _, expected = modes.prompt(finir, "pass\u00e9_compos\u00e9", 0, "m")
        self.assertEqual(expected, "j'ai fini")


if __name__ == "__main__":
    unittest.main()
