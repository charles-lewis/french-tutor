# -*- coding: utf-8 -*-
"""Vocabulary engine tests: keys, states, weighted selection (spec §7)."""

import unittest
from datetime import datetime
from unittest import mock

from trainer import engine as tren

from vocab import engine


class KeyTest(unittest.TestCase):
    def test_key(self):
        self.assertEqual(engine.key("faire", "fr2en"), "faire|fr2en")
        self.assertEqual(engine.key("faire", "en2fr"), "faire|en2fr")

    def test_get_state_defaults_to_unseen(self):
        states = {engine.key("faire", "fr2en"): tren.ItemState(success_count=5)}
        st = engine.get_state(states, "faire", "fr2en")
        self.assertEqual(st.success_count, 5)
        self.assertIsInstance(engine.get_state(states, "faire", "en2fr"), tren.ItemState)


class SelectionTest(unittest.TestCase):
    def _entries(self):
        return [
            {"id": "faire", "fr": "faire", "en": ["to do", "to make"], "pos": "verb"},
            {"id": "venir", "fr": "venir", "en": ["to come"], "pos": "verb"},
        ]

    def test_empty_returns_none(self):
        self.assertIsNone(engine.select_item([], ["fr2en"], {}, datetime.now()))

    def test_returns_member_of_scope(self):
        entries = self._entries()
        with mock.patch("trainer.engine.random.uniform", return_value=0.0):
            picked = engine.select_item(entries, ["fr2en", "en2fr"], {}, datetime.now())
        self.assertIn(picked, [(e, d) for e in entries for d in ("fr2en", "en2fr")])

    def test_higher_weight_item_chosen_first(self):
        entries = self._entries()
        states = {engine.key("venir", "fr2en"): tren.ItemState(
            failure_count=50, last_seen=datetime.now().isoformat(),
            last_result="incorrect")}
        # uniform() calls: faire noise, venir noise, then selection draw r.
        # faire weight=10, venir weight=306, r=100 lands in venir's range.
        with mock.patch("trainer.engine.random.uniform", side_effect=[1.0, 1.0, 100.0]):
            picked = engine.select_item(entries, ["fr2en"], states, datetime.now())
        self.assertEqual(picked, (entries[1], "fr2en"))

    def test_all_unseen_selection_uses_first(self):
        entries = self._entries()
        with mock.patch("trainer.engine.random.uniform", return_value=1e-12):
            picked = engine.select_item(entries, ["fr2en"], {}, datetime.now())
        self.assertEqual(picked, (entries[0], "fr2en"))


if __name__ == "__main__":
    unittest.main()
