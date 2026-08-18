# -*- coding: utf-8 -*-
"""Vocabulary prompt/evaluation tests (spec §6)."""

import unittest

from vocab import modes


class ModesTest(unittest.TestCase):
    def _entry(self, en=("to do", "to make"), notes=None):
        return {"id": "faire", "fr": "faire", "en": list(en),
                "pos": "verb", "notes": notes}

    def test_prompt_fr2en(self):
        line, expected = modes.prompt(self._entry(), "fr2en")
        self.assertIn("faire", line)
        self.assertEqual(expected, ["to do", "to make"])

    def test_prompt_en2fr(self):
        line, expected = modes.prompt(self._entry(), "en2fr")
        self.assertIn("to do / to make", line)
        self.assertEqual(expected, ["faire"])

    def test_fr2en_any_meaning_accepted(self):
        e = self._entry()
        self.assertTrue(modes.is_correct(e, "fr2en", "to do"))
        self.assertTrue(modes.is_correct(e, "fr2en", "To Make"))
        self.assertFalse(modes.is_correct(e, "fr2en", "to make it"))

    def test_fr2en_accent_strict(self):
        e = self._entry(("pr\u00e9f\u00e9rer",))
        self.assertTrue(modes.is_correct(e, "fr2en", "pr\u00e9f\u00e9rer"))
        self.assertFalse(modes.is_correct(e, "fr2en", "preferer"))

    def test_en2fr_accent_strict(self):
        e = self._entry(("to come",))
        e["fr"] = "venir"
        self.assertTrue(modes.is_correct(e, "en2fr", "venir"))
        self.assertFalse(modes.is_correct(e, "en2fr", "veni"))

    def test_success_feedback_lists_all_meanings(self):
        e = self._entry()
        out = modes.success_feedback(e, "fr2en")
        self.assertEqual(out, "faire -> to do / to make")

    def test_success_feedback_single_meaning_is_none(self):
        e = self._entry(("to make",))
        self.assertIsNone(modes.success_feedback(e, "fr2en"))

    def test_success_feedback_shows_notes_for_en2fr(self):
        e = self._entry(notes="extremely irregular")
        out = modes.success_feedback(e, "en2fr")
        self.assertIn("extremely irregular", out)

    def test_success_feedback_no_notes(self):
        e = self._entry()
        self.assertIsNone(modes.success_feedback(e, "en2fr"))

    def test_success_feedback_notes_shown_for_fr2en(self):
        e = self._entry(notes="extremely irregular")
        out = modes.success_feedback(e, "fr2en")
        self.assertEqual(out, "faire -> to do / to make   (extremely irregular)")

    def test_success_feedback_notes_only_for_single_meaning(self):
        e = self._entry(("to make",), notes="extremely irregular")
        out = modes.success_feedback(e, "fr2en")
        self.assertEqual(out, "(extremely irregular)")


if __name__ == "__main__":
    unittest.main()
