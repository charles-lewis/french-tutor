# -*- coding: utf-8 -*-
"""Progress persistence tests (§10)."""

import json
import os
import tempfile
import unittest

from trainer import progress
from trainer.engine import ItemState


class ProgressTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "progress.json")

    def tearDown(self):
        for name in (self.path, self.path + ".tmp"):
            if os.path.exists(name):
                os.remove(name)
        os.rmdir(self.dir)

    def test_save_load_roundtrip(self):
        states = {
            "aller|present|0": ItemState(success_count=3, failure_count=1, streak=2,
                                         longest_streak=3, last_seen="2026-08-09T12:00:00.000000",
                                         last_result="correct", avg_response_time=1.5),
        }
        progress.save_progress(self.path, states)
        loaded = progress.load_progress(self.path)
        self.assertEqual(loaded["aller|present|0"].to_dict(), states["aller|present|0"].to_dict())

    def test_missing_file_returns_empty(self):
        self.assertEqual(progress.load_progress(self.path), {})

    def test_corrupt_file_returns_empty(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("not json {{")
        self.assertEqual(progress.load_progress(self.path), {})

    def test_save_is_atomic_no_tmp_leftover(self):
        progress.save_progress(self.path, {})
        self.assertFalse(os.path.exists(self.path + ".tmp"))
        with open(self.path, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {})


if __name__ == "__main__":
    unittest.main()
