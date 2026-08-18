# -*- coding: utf-8 -*-
"""Engine tests: item state, weight, selection (spec §8)."""

import unittest
from datetime import datetime
from unittest import mock

from trainer import engine


class ItemStateTest(unittest.TestCase):
    def test_defaults(self):
        s = engine.ItemState()
        self.assertEqual(s.success_count, 0)
        self.assertEqual(s.failure_count, 0)
        self.assertEqual(s.streak, 0)
        self.assertEqual(s.longest_streak, 0)
        self.assertIsNone(s.last_seen)
        self.assertIsNone(s.last_result)
        self.assertIsNone(s.avg_response_time)

    def test_dict_roundtrip(self):
        s = engine.ItemState(success_count=3, failure_count=1, streak=2, longest_streak=4,
                             last_seen="2026-08-09T12:00:00.123456",
                             last_result="correct", avg_response_time=1.4,
                             recent_results=[True, False, True], recent_times=[2.0, 1.0])
        t = engine.ItemState.from_dict(s.to_dict())
        self.assertEqual(t.to_dict(), s.to_dict())

    def test_record_answer_correct(self):
        now = datetime(2026, 8, 9, 12, 0, 0)
        s = engine.ItemState()
        engine.record_answer(s, True, 2.0, now)
        self.assertEqual(s.success_count, 1)
        self.assertEqual(s.streak, 1)
        self.assertEqual(s.longest_streak, 1)
        self.assertEqual(s.last_result, "correct")
        self.assertEqual(s.last_seen, now.isoformat())
        self.assertEqual(s.avg_response_time, 2.0)

    def test_record_answer_wrong_resets_streak(self):
        now = datetime(2026, 8, 9, 12, 0, 0)
        s = engine.ItemState(success_count=2, streak=2, longest_streak=2)
        engine.record_answer(s, False, None, now)
        self.assertEqual(s.failure_count, 1)
        self.assertEqual(s.streak, 0)
        self.assertEqual(s.longest_streak, 2)
        self.assertEqual(s.last_result, "incorrect")
        self.assertIsNone(s.avg_response_time)

    def test_average_response_time(self):
        now = datetime(2026, 8, 9, 12, 0, 0)
        s = engine.ItemState()
        engine.record_answer(s, True, 2.0, now)
        engine.record_answer(s, True, 4.0, now)
        self.assertEqual(s.avg_response_time, 3.0)
        self.assertEqual(s.recent_times, [2.0, 4.0])

    def test_recent_window_caps_at_ten(self):
        now = datetime(2026, 8, 9, 12, 0, 0)
        s = engine.ItemState()
        for i in range(13):
            engine.record_answer(s, i % 2 == 0, 1.0, now)
        self.assertEqual(len(s.recent_results), 10)
        self.assertEqual(len(s.recent_times), 10)
        self.assertEqual(s.recent_results[-1], 12 % 2 == 0)
        self.assertEqual(s.recent_times[-1], 1.0)

    def test_windowed_metrics(self):
        now = datetime(2026, 8, 9, 12, 0, 0)
        s = engine.ItemState()
        self.assertIsNone(engine.windowed_accuracy(s))
        self.assertIsNone(engine.windowed_avg_time(s))
        engine.record_answer(s, True, 2.0, now)
        engine.record_answer(s, False, 4.0, now)
        engine.record_answer(s, True, 6.0, now)
        self.assertAlmostEqual(engine.windowed_accuracy(s), 2.0 / 3.0 * 100)
        self.assertEqual(engine.windowed_avg_time(s), 4.0)

    def test_key_and_get_state(self):
        self.assertEqual(engine.key("aller", "present", 2), "aller|present|2")
        states = {engine.key("aller", "present", 2): engine.ItemState(success_count=5)}
        st = engine.get_state(states, "aller", "present", 2)
        self.assertEqual(st.success_count, 5)
        self.assertIsInstance(engine.get_state(states, "aller", "present", 0), engine.ItemState)


class WeightTest(unittest.TestCase):
    def _state(self, **kw):
        defaults = dict(success_count=0, failure_count=0, streak=0, longest_streak=0,
                        last_seen=None, last_result=None, avg_response_time=None)
        defaults.update(kw)
        return engine.ItemState(**defaults)

    def test_unseen_weight(self):
        now = datetime(2026, 8, 9, 12, 0, 0)
        with mock.patch("trainer.engine.random.uniform", return_value=1.0):
            self.assertEqual(engine.weight(engine.ItemState(), now), 10.0)

    def test_unseen_weight_noise(self):
        now = datetime(2026, 8, 9, 12, 0, 0)
        with mock.patch("trainer.engine.random.uniform", return_value=2.0):
            self.assertAlmostEqual(engine.weight(engine.ItemState(), now), 20.0)

    def test_correct_recent_state(self):
        now = datetime(2026, 8, 9, 12, 0, 0)
        st = self._state(failure_count=2, streak=3, last_seen=now.isoformat(),
                         last_result="correct")
        with mock.patch("trainer.engine.random.uniform", return_value=1.0):
            # (fail+1) * freshness(age 0 -> 1.0) * boost(correct -> 1) / (streak+1)
            self.assertAlmostEqual(engine.weight(st, now), 3.0 / 4.0)

    def test_incorrect_recency_boost(self):
        now = datetime(2026, 8, 9, 12, 0, 0)
        st = self._state(failure_count=2, streak=3, last_seen=now.isoformat(),
                         last_result="incorrect")
        with mock.patch("trainer.engine.random.uniform", return_value=1.0):
            self.assertAlmostEqual(engine.weight(st, now), (3.0 * 6.0) / 4.0)

    def test_older_items_get_more_weight(self):
        now = datetime(2026, 8, 9, 12, 0, 0)
        old = self._state(last_seen=datetime(2026, 8, 1, 12, 0, 0).isoformat(),
                          last_result="correct")
        fresh = self._state(last_seen=now.isoformat(), last_result="correct")
        with mock.patch("trainer.engine.random.uniform", return_value=1.0):
            self.assertGreater(engine.weight(old, now), engine.weight(fresh, now))


class SelectUnitTest(unittest.TestCase):
    def test_empty(self):
        self.assertIsNone(engine.select_unit([], {}, datetime.now()))

    def test_single_unit(self):
        verb = {"infinitive": "aller"}
        unit = engine.select_unit([(verb, "present")], {}, datetime.now())
        self.assertEqual(unit, (verb, "present"))

    def test_returns_member_of_units(self):
        verbs = [{"infinitive": "a"}, {"infinitive": "b"}]
        units = [(verbs[0], "present"), (verbs[1], "present")]
        with mock.patch("trainer.engine.random.uniform", return_value=0.0):
            verb, tkey = engine.select_unit(units, {}, datetime.now())
        self.assertIn((verb, tkey), units)

    def test_all_unseen_selection_uses_first(self):
        # deterministic: r near 0 always selects the first unit
        verbs = [{"infinitive": "a"}, {"infinitive": "b"}]
        units = [(verbs[0], "present"), (verbs[1], "present")]
        with mock.patch("trainer.engine.random.uniform", return_value=1e-12):
            verb, tkey = engine.select_unit(units, {}, datetime.now())
        self.assertEqual(verb["infinitive"], "a")


class PerfectVerbNamesTest(unittest.TestCase):
    NOW = "2026-08-09T12:00:00"

    def _correct(self):
        return engine.ItemState(last_seen=self.NOW, last_result="correct")

    def _wrong(self):
        return engine.ItemState(last_seen=self.NOW, last_result="incorrect")

    def _verb(self, name, tenses=None):
        if tenses is None:
            tenses = {"present": {"label": "présent", "type": "simple"}}
        return {"infinitive": name, "tenses": tenses}

    def test_empty(self):
        self.assertEqual(engine.perfect_verb_names([], {}), set())

    def test_all_correct(self):
        v1 = self._verb("aller")
        v2 = self._verb("finir")
        units = [(v1, "present"), (v2, "present")]
        states = {}
        for v in (v1, v2):
            for p in engine.PERSONS:
                states[engine.key(v["infinitive"], "present", p)] = self._correct()
        self.assertEqual(engine.perfect_verb_names(units, states), {"aller", "finir"})

    def test_untested_excluded(self):
        verb = self._verb("aller")
        units = [(verb, "present")]
        self.assertEqual(engine.perfect_verb_names(units, {}), set())

    def test_any_wrong_excludes_verb(self):
        verb = self._verb("aller")
        units = [(verb, "present")]
        states = {}
        for p in engine.PERSONS:
            states[engine.key("aller", "present", p)] = self._correct()
        states[engine.key("aller", "present", 3)] = self._wrong()
        self.assertEqual(engine.perfect_verb_names(units, states), set())

    def test_missing_tense_in_scope_excludes(self):
        tenses = {"present": {"label": "présent", "type": "simple"},
                  "imparfait": {"label": "imparfait", "type": "simple"}}
        verb = self._verb("aller", tenses)
        units = [(verb, "present"), (verb, "imparfait")]
        states = {}
        for p in engine.PERSONS:
            states[engine.key("aller", "present", p)] = self._correct()
        self.assertEqual(engine.perfect_verb_names(units, states), set())

    def test_perfect_only_in_own_scope(self):
        verb = self._verb("aller")
        units = [(verb, "present")]
        states = {engine.key("aller", "imparfait", 0): self._wrong()}
        self.assertEqual(engine.perfect_verb_names(units, states), set())

    def test_compound_only_checks_person_zero(self):
        tense = {"passé_composé": {"label": "passé composé", "type": "compound"}}
        verb = self._verb("venir", tense)
        units = [(verb, "passé_composé")]
        states = {engine.key("venir", "passé_composé", 0): self._correct()}
        self.assertEqual(engine.perfect_verb_names(units, states), {"venir"})

    def test_compound_wrong_at_zero_excludes(self):
        tense = {"passé_composé": {"label": "passé composé", "type": "compound"}}
        verb = self._verb("venir", tense)
        units = [(verb, "passé_composé")]
        states = {engine.key("venir", "passé_composé", 0): self._wrong()}
        self.assertEqual(engine.perfect_verb_names(units, states), set())


if __name__ == "__main__":
    unittest.main()
