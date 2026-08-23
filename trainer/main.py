# -*- coding: utf-8 -*-
"""CLI entry point, session loop, and reports (spec §6, §9, §11, §12)."""

import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from . import consoleio, engine, loader, modes, progress

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "data"
VERBS_PATH = DATA_DIR / "verbs.json"
PROGRESS_PATH = DATA_DIR / "progress.json"
CONFIG_PATH = DATA_DIR / "config.json"

TENSE_ORDER = ["present", "imparfait", "futur_simple", "futur_proche",
               "conditionnel", "pass\u00e9_compos\u00e9"]
TENSE_LABELS = {
    "present": "pr\u00e9sent",
    "imparfait": "imparfait",
    "futur_simple": "futur simple",
    "futur_proche": "futur proche",
    "conditionnel": "conditionnel",
    "pass\u00e9_compos\u00e9": "pass\u00e9 compos\u00e9",
}

DEFAULT_CONFIG = {"tense": "all"}


def load_config():
    try:
        with open(str(CONFIG_PATH), encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (IOError, OSError, ValueError):
        cfg = {}
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    return merged


def save_config(cfg):
    with open(str(CONFIG_PATH), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


# --- session setup ---------------------------------------------------------

def choose_tense_scope(cfg):
    print("Tense scope:")
    for i, key in enumerate(TENSE_ORDER, 1):
        print("  [%d] %s" % (i, TENSE_LABELS[key]))
    default = cfg.get("tense", "all")
    line = consoleio.input_line("Choose (numbers or keys, comma-separated) [%s]: " % default).strip()
    if not line:
        return default
    if line.lower() == "all":
        return "all"
    keys = []
    for token in line.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token)
            if 1 <= idx <= len(TENSE_ORDER):
                keys.append(TENSE_ORDER[idx - 1])
                continue
        if token in TENSE_LABELS:
            keys.append(token)
        else:
            print("  unknown tense: %s" % token)
    if not keys:
        return default
    if len(keys) == len(TENSE_ORDER):
        return "all"
    return ",".join(keys)


def resolve_tense_keys(scope):
    if scope == "all":
        return list(TENSE_ORDER)
    return [t for t in scope.split(",") if t in TENSE_LABELS]


def build_units(verbs, tense_keys):
    units = []
    for verb in verbs:
        for tkey in tense_keys:
            if tkey in verb["tenses"]:
                units.append((verb, tkey))
    return units


# --- session ---------------------------------------------------------------

class Session(object):
    def __init__(self, cfg, verbs):
        self.cfg = cfg
        self.verbs = verbs
        self.states = progress.load_progress(str(PROGRESS_PATH))
        self.stats = {
            "prompts": 0,
            "correct": 0,
            "incorrect": 0,
            "start": time.monotonic(),
            "by_tense": {},
            "by_verb": {},
        }
        self.rebuild()

    def rebuild(self):
        tense_keys = resolve_tense_keys(self.cfg["tense"])
        self.units = build_units(self.verbs, tense_keys)

    # -- flow --

    def run(self):
        while True:
            unit = engine.select_unit(self.units, self.states, datetime.now())
            if unit is None:
                print("\nNo items in scope. Use :new to change tense.")
                return "new"
            verb, tkey = unit
            outcome = self.drill(verb, tkey)
            if outcome != "continue":
                return outcome

    def drill(self, verb, tkey):
        print("\n" + modes.bold(modes.drill_header(verb, tkey)))
        if verb["tenses"][tkey]["type"] == "compound":
            return self._drill_compound(verb, tkey)
        results = {}
        person = 0
        while person in engine.PERSONS:
            outcome, correct = self.ask(verb, tkey, person)
            if outcome == "quit":
                return "quit"
            if outcome == "new":
                return "new"
            if outcome == "restart":
                results = {}
                person = 0
                print("\n" + modes.bold(modes.drill_header(verb, tkey)))
                continue
            results[person] = correct
            person += 1
        if all(results.get(p) for p in engine.PERSONS):
            print("  " + modes.green("[OK] Full correct 6/6 - %s" % modes.drill_header(verb, tkey)))
        return "continue"

    def _drill_compound(self, verb, tkey):
        person = random.choice(list(engine.PERSONS))
        tense = verb["tenses"][tkey]
        gender = "both"
        if "feminine" in tense:
            gender = "f" if random.random() < 0.5 else "m"
        while True:
            line, expected = modes.prompt(verb, tkey, person, gender)
            print(line)
            t0 = time.monotonic()
            try:
                raw = consoleio.input_line("> ").strip()
            except EOFError:
                return "quit"
            seconds = time.monotonic() - t0
            if raw.startswith(":"):
                if raw == ":quit":
                    return "quit"
                if raw == ":new":
                    return "new"
                if raw in (":skip", ":reveal"):
                    self.record(verb, tkey, 0, False, None)
                    print("  " + modes.red("[X] expected: %s" % expected))
                    return "continue"
                print("  unknown command: %s" % raw)
                continue
            correct = modes.normalize(raw).casefold() == modes.normalize(expected).casefold()
            self.record(verb, tkey, 0, correct, seconds)
            if correct:
                print("  " + modes.green("[OK]"))
                return "continue"
            print("  " + modes.red("[X] expected: %s" % expected))
            print("  Try again.")

    def ask(self, verb, tkey, person):
        first_try = True
        while True:
            line, expected = modes.prompt(verb, tkey, person, "both")
            print(line)
            t0 = time.monotonic()
            try:
                raw = consoleio.input_line("> ").strip()
            except EOFError:
                return "quit", None
            seconds = time.monotonic() - t0
            if raw.startswith(":"):
                result, correct = self.command(verb, tkey, person, raw, expected)
                if result == "repeat":
                    continue
                return result, correct
            correct = modes.normalize(raw).casefold() == modes.normalize(expected).casefold()
            self.record(verb, tkey, person, correct, seconds)
            if correct:
                print("  " + modes.green("[OK]"))
                return "continue", first_try
            print("  " + modes.red("[X] expected: %s" % expected))
            print("  Try again.")
            first_try = False

    # -- commands --

    def show_help(self):
        print("\nCommands:")
        print("  :help        Show this help.")
        print("  :quit        Show session report, save progress, exit.")
        print("  :new         Return to session setup (change tense scope).")
        print("  :tenses <k>  Change tense scope (present,imparfait,... | all).")
        print("  :skip        Skip this prompt (counted as incorrect).")
        print("  :reveal      Show the answer (counted as incorrect).")
        print("  :repeat      Restart this verb drill from the first person.")
        print("  :stats       Show session + per-item stats.\n")

    def command(self, verb, tkey, person, raw, expected):
        parts = raw.split(None, 1)
        name = parts[0]
        arg = parts[1] if len(parts) > 1 else ""
        if name == ":help":
            self.show_help()
            return "repeat", None
        if name == ":quit":
            return "quit", None
        if name == ":new":
            return "new", None
        if name == ":skip":
            self.record(verb, tkey, person, False, None)
            print("  " + modes.red("[X] skipped - expected: %s" % expected))
            return "next", False
        if name == ":reveal":
            self.record(verb, tkey, person, False, None)
            print("  " + modes.red("[X] expected: %s" % expected))
            return "next", False
        if name == ":repeat":
            return "restart", None
        if name == ":tenses":
            if arg:
                if arg == "all":
                    self.cfg["tense"] = "all"
                else:
                    self.cfg["tense"] = arg
                self.rebuild()
                save_config(self.cfg)
                print("  tense scope: %s" % self.cfg["tense"])
            else:
                print("  usage: :tenses <keys|all>")
            return "repeat", None
        if name == ":stats":
            self.show_stats()
            return "repeat", None
        print("  unknown command: %s" % raw)
        return "repeat", None

    # -- recording --

    def record(self, verb, tkey, person, correct, seconds):
        st = engine.get_state(self.states, verb["infinitive"], tkey, person)
        engine.record_answer(st, correct, seconds, datetime.now())
        self.states[engine.key(verb["infinitive"], tkey, person)] = st
        self.stats["prompts"] += 1
        if correct:
            self.stats["correct"] += 1
        else:
            self.stats["incorrect"] += 1
        self.stats["by_tense"][tkey] = self.stats["by_tense"].get(tkey, 0) + 1
        self.stats["by_verb"][verb["infinitive"]] = self.stats["by_verb"].get(verb["infinitive"], 0) + 1
        progress.save_progress(str(PROGRESS_PATH), self.states)

    # -- reporting --

    def show_stats(self):
        s = self.stats
        prompts = s["prompts"]
        acc = (100.0 * s["correct"] / prompts) if prompts else 0.0
        elapsed = time.monotonic() - s["start"]
        print("\n--- Session ---")
        print("prompts: %d   correct: %d   incorrect: %d   accuracy: %.1f%%"
              % (prompts, s["correct"], s["incorrect"], acc))
        print("time: %d:%02d" % (elapsed // 60, elapsed % 60))
        if s["by_tense"]:
            print("by tense: %s" % ", ".join("%s %d" % (k, v) for k, v in sorted(s["by_tense"].items())))
        if s["by_verb"]:
            print("by verb: %s" % ", ".join("%s %d" % (k, v) for k, v in sorted(s["by_verb"].items())))

        rows = []
        for verb, tkey in self.units:
            for p in engine.PERSONS:
                st = engine.get_state(self.states, verb["infinitive"], tkey, p)
                acc = engine.windowed_accuracy(st)
                if acc is None:
                    continue
                n_correct = sum(st.recent_results)
                n_total = len(st.recent_results)
                rows.append((verb["infinitive"], tkey, p,
                             n_total, n_correct, engine.windowed_avg_time(st),
                             st.streak, st.longest_streak, acc))
        rows.sort(key=lambda r: (r[8], r[0], r[1], r[2]))
        print("\n--- Items with recent attempts (%d) ---" % len(rows))
        for r in rows[:20]:
            avg = "%.1fs" % r[5] if r[5] is not None else "-"
            print("  %-12s %-14s p%d  n=%-3d correct=%-3d acc=%5.1f%%  streak=%d/%d  avg=%s"
                  % (r[0], r[1], r[2], r[3], r[4], r[8], r[6], r[7], avg))

    def report(self):
        self.show_stats()

        session_verbs = set(self.stats["by_verb"].keys())
        perfect = engine.perfect_verb_names(self.units, self.states)
        tested_perfect = perfect & session_verbs
        print("\n--- Perfect verbs (this session) ---")
        print("  %d of %d verbs tested answered perfectly the last time tested"
              % (len(tested_perfect), len(session_verbs)))


# --- entry -----------------------------------------------------------------

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        verbs = loader.load_verbs(str(VERBS_PATH))
    except loader.ValidationError as exc:
        print("verbs.json failed validation:\n%s" % exc)
        return 1
    except (IOError, OSError, ValueError) as exc:
        print("could not load %s: %s" % (VERBS_PATH, exc))
        return 1

    print("French Verb Trainer\n")
    cfg = load_config()
    try:
        while True:
            cfg["tense"] = choose_tense_scope(cfg)
            save_config(cfg)
            session = Session(cfg, verbs)
            outcome = session.run()
            if outcome == "quit":
                progress.save_progress(str(PROGRESS_PATH), session.states)
                session.report()
                print("\nGoodbye.")
                return 0
            # outcome == "new": back to setup
    except KeyboardInterrupt:
        print("\nInterrupted - progress saved.")
        progress.save_progress(str(PROGRESS_PATH), session.states)
        return 130
    except EOFError:
        print("\nGoodbye.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
