# -*- coding: utf-8 -*-
"""Vocabulary session flow tests (spec §6, §8)."""

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from vocab import main
from vocab.main import Session


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.progress_path = os.path.join(self.dir, "vocab_progress.json")
        self.faire = {"id": "faire", "fr": "faire",
                      "en": ["to do", "to make"], "pos": "verb",
                      "notes": "extremely irregular"}
        self.venir = {"id": "venir", "fr": "venir",
                      "en": ["to come"], "pos": "verb", "notes": None}
        self.patches = [
            mock.patch.object(main.tprogress, "load_progress", return_value={}),
            mock.patch.object(main.tprogress, "save_progress", return_value=None),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(self._stop)

    def _stop(self):
        for p in reversed(self.patches):
            p.stop()

    def _run_quiz(self, entry, direction, answers):
        s = Session({"direction": direction, "pos_scope": "all"},
                    [entry], self.progress_path)
        out = io.StringIO()
        with mock.patch.object(main.consoleio, "input_line", side_effect=answers), \
                contextlib.redirect_stdout(out):
            outcome = s.quiz(entry, direction)
        return outcome, out.getvalue()

    def test_fr2en_retry_until_correct(self):
        # "to read" wrong at first, then "to do" correct; lists all meanings and notes
        outcome, out = self._run_quiz(self.faire, "fr2en", ["to read", "to do"])
        self.assertEqual(outcome, "continue")
        self.assertIn("expected: to do / to make", out)
        self.assertIn("faire -> to do / to make   (extremely irregular)", out)

    def test_fr2en_wrong_then_correct_records_failure(self):
        s = Session({"direction": "fr2en", "pos_scope": "all"},
                    [self.faire], self.progress_path)
        with mock.patch.object(main.consoleio, "input_line", side_effect=["to read", "to do"]), \
                contextlib.redirect_stdout(io.StringIO()):
            s.quiz(self.faire, "fr2en")
        from vocab import engine as veng
        st = veng.get_state(s.states, "faire", "fr2en")
        self.assertEqual(st.failure_count, 1)
        self.assertEqual(st.success_count, 1)

    def test_en2fr_success_shows_notes(self):
        outcome, out = self._run_quiz(self.faire, "en2fr", ["faire"])
        self.assertEqual(outcome, "continue")
        self.assertIn("extremely irregular", out)

    def test_en2fr_no_notes_no_feedback(self):
        outcome, out = self._run_quiz(self.venir, "en2fr", ["venir"])
        self.assertEqual(outcome, "continue")
        self.assertNotIn("venir -> to come", out)

    def test_skip_counts_incorrect(self):
        outcome, out = self._run_quiz(self.faire, "fr2en", [":skip", "to do"])
        self.assertEqual(outcome, "continue")
        self.assertIn("skipped - expected: to do / to make", out)

    def test_reveal_counts_incorrect(self):
        outcome, out = self._run_quiz(self.faire, "fr2en", [":reveal", "to do"])
        self.assertEqual(outcome, "continue")
        self.assertIn("expected: to do / to make", out)

    def test_quit_command(self):
        outcome, _ = self._run_quiz(self.faire, "fr2en", [":quit"])
        self.assertEqual(outcome, "quit")

    def test_unknown_command(self):
        outcome, out = self._run_quiz(self.faire, "fr2en", [":bogus", "to do"])
        self.assertEqual(outcome, "continue")
        self.assertIn("unknown command", out)

    def test_run_returns_quit(self):
        s = Session({"direction": "fr2en", "pos_scope": "all"},
                    [self.faire], self.progress_path)
        out = io.StringIO()
        with mock.patch.object(main.consoleio, "input_line", side_effect=["to do", ":quit"]), \
                contextlib.redirect_stdout(out):
            outcome = s.run()
        self.assertEqual(outcome, "quit")

    def test_empty_scope_returns_new(self):
        s = Session({"direction": "fr2en", "pos_scope": "noun"},
                    [self.faire], self.progress_path)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            outcome = s.run()
        self.assertEqual(outcome, "new")

    def test_source_scope_filters_entries(self):
        faire = dict(self.faire, source="vocab.json")
        venir = dict(self.venir, source="verbs.json")
        s = Session({"direction": "fr2en", "pos_scope": "all", "sources": ["verbs.json"]},
                    [faire, venir], self.progress_path)
        self.assertEqual(s._scope_entries(), [venir])

    def test_default_sources_is_all(self):
        faire = dict(self.faire, source="vocab.json")
        venir = dict(self.venir, source="verbs.json")
        s = Session({"direction": "fr2en", "pos_scope": "all"},
                    [faire, venir], self.progress_path)
        self.assertEqual(sorted(e["id"] for e in s._scope_entries()), ["faire", "venir"])


if __name__ == "__main__":
    unittest.main()
