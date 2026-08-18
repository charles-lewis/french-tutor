# -*- coding: utf-8 -*-
"""Session flow tests: drill loop and inline commands (§6, §11)."""

import contextlib
import io
import unittest
from unittest import mock

import trainer.main as main

from tests._fixtures import ALLER_PC, ALLER_PC_FEM, ALLER_PRESENT, make_verb


def _session(verbs):
    return main.Session({"tense": "all"}, verbs)


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.aller = make_verb("aller", present=ALLER_PRESENT,
                               pc_masc=ALLER_PC, pc_fem=ALLER_PC_FEM)
        self.patches = [
            mock.patch.object(main.progress, "load_progress", return_value={}),
            mock.patch.object(main.progress, "save_progress", return_value=None),
            mock.patch.object(main, "save_config", return_value=None),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(self._stop_patches)

    def _stop_patches(self):
        for p in reversed(self.patches):
            p.stop()

    def _run_drill(self, session, verb, answers):
        out = io.StringIO()
        with mock.patch.object(main.consoleio, "input_line", side_effect=answers), \
                contextlib.redirect_stdout(out):
            outcome = session.drill(verb, "present")
        return outcome, out.getvalue()

    def test_units_cover_all_verbs_and_tenses(self):
        session = _session([self.aller])
        self.assertEqual(len(session.units), 6)

    def test_full_correct_drill(self):
        session = _session([self.aller])
        answers = ["vais", "vas", "va", "allons", "allez", "vont"]
        outcome, out = self._run_drill(session, self.aller, answers)
        self.assertEqual(outcome, "continue")
        self.assertIn("Full correct 6/6", out)

    def test_wrong_answer_repeats_prompt_and_no_full_correct(self):
        session = _session([self.aller])
        # je answered wrong, then correctly on the re-prompt; rest all correct
        answers = ["x", "vais", "vas", "va", "allons", "allez", "vont"]
        outcome, out = self._run_drill(session, self.aller, answers)
        self.assertEqual(outcome, "continue")
        self.assertIn("expected: vais", out)
        self.assertNotIn("Full correct", out)

    def test_repeat_restarts_drill_from_first_person(self):
        session = _session([self.aller])
        # answer p0 correctly, then :repeat at p1 -> restart, then all correct
        answers = ["vais", ":repeat", "vais", "vas", "va", "allons", "allez", "vont"]
        persons = []
        real_prompt = main.modes.prompt

        def spy_prompt(verb, tkey, person, gender):
            persons.append(person)
            return real_prompt(verb, tkey, person, gender)

        out = io.StringIO()
        with mock.patch.object(main.consoleio, "input_line", side_effect=answers), \
                mock.patch.object(main.modes, "prompt", side_effect=spy_prompt), \
                contextlib.redirect_stdout(out):
            outcome = session.drill(self.aller, "present")
        self.assertEqual(outcome, "continue")
        self.assertGreaterEqual(persons.count(0), 2, "person 0 must be prompted again after :repeat")
        self.assertIn("Full correct 6/6", out.getvalue(), "second pass must be all correct")

    def test_repeat_clears_previous_results(self):
        session = _session([self.aller])
        # p0 wrong, :repeat at p1, then one wrong answer -> no Full correct
        answers = ["bad", ":repeat", "bad", ":quit"]
        out = io.StringIO()
        with mock.patch.object(main.consoleio, "input_line", side_effect=answers), \
                contextlib.redirect_stdout(out):
            outcome = session.drill(self.aller, "present")
        self.assertEqual(outcome, "quit")
        self.assertNotIn("Full correct", out.getvalue())

    def test_skip_counts_as_incorrect(self):
        session = _session([self.aller])
        outcome, correct = session.command(self.aller, "present", 0, ":skip", "vais")
        self.assertEqual((outcome, correct), ("next", False))
        st = main.engine.get_state(session.states, "aller", "present", 0)
        self.assertEqual(st.failure_count, 1)

    def test_reveal_counts_as_incorrect(self):
        session = _session([self.aller])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            outcome, correct = session.command(self.aller, "present", 0, ":reveal", "vais")
        self.assertEqual((outcome, correct), ("next", False))
        self.assertIn("expected: vais", out.getvalue())

    def test_tenses_command_rebuilds_scope(self):
        session = _session([self.aller])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            outcome, correct = session.command(self.aller, "present", 0, ":tenses present", "x")
        self.assertEqual((outcome, correct), ("repeat", None))
        self.assertEqual(session.cfg["tense"], "present")
        self.assertTrue(all(tkey == "present" for _, tkey in session.units))

    def test_help_lists_commands(self):
        session = _session([self.aller])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            outcome, correct = session.command(self.aller, "present", 0, ":help", "x")
        self.assertEqual((outcome, correct), ("repeat", None))
        for cmd in (":help", ":quit", ":new", ":tenses", ":skip", ":reveal", ":repeat", ":stats"):
            self.assertIn(cmd, out.getvalue())

    def test_quit_returns_quit(self):
        session = _session([self.aller])
        self.assertEqual(session.command(self.aller, "present", 0, ":quit", "x"), ("quit", None))

    def test_unknown_command(self):
        session = _session([self.aller])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            outcome, correct = session.command(self.aller, "present", 0, ":bogus", "x")
        self.assertEqual((outcome, correct), ("repeat", None))
        self.assertIn("unknown command", out.getvalue())


if __name__ == "__main__":
    unittest.main()
