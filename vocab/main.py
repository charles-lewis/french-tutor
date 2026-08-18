# -*- coding: utf-8 -*-
"""Vocabulary tutor CLI entry, session loop, commands, and reports (spec §5–§12)."""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from trainer import consoleio, engine as tren, modes as tmodes, progress as tprogress

from . import engine, loader, modes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_CONFIG_PATH = ROOT / "data" / "vocab_config.json"

DEFAULT_CONFIG = {
    "direction": "both",
    "pos_scope": "all",
    "sources": "all",
    "data": {
        "verbs": "data/verbs.json",
        "vocab": ["data/vocab.json"],
        "progress": "data/vocab_progress.json",
    },
}


def resolve(root, path):
    p = Path(path)
    return p if p.is_absolute() else root / p


def load_config(path):
    try:
        with open(str(path), encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (IOError, OSError, ValueError):
        cfg = {}
    merged = {"direction": DEFAULT_CONFIG["direction"], "pos_scope": DEFAULT_CONFIG["pos_scope"],
              "sources": DEFAULT_CONFIG["sources"], "data": dict(DEFAULT_CONFIG["data"])}
    if isinstance(cfg, dict):
        for key in ("direction", "pos_scope", "sources"):
            if key in cfg:
                merged[key] = cfg[key]
        if isinstance(cfg.get("data"), dict):
            merged["data"].update(cfg["data"])
    return merged


def save_config(path, cfg):
    with open(str(path), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


def choose_direction(cfg):
    print("Direction:")
    print("  [1] French -> English")
    print("  [2] English -> French")
    print("  [3] Both (random per prompt)")
    default = cfg.get("direction", "both")
    line = consoleio.input_line("Choose [%s]: " % default).strip()
    if not line:
        return default
    mapping = {"1": "fr2en", "2": "en2fr", "3": "both",
               "fr2en": "fr2en", "en2fr": "en2fr", "both": "both"}
    if line in mapping:
        return mapping[line]
    print("  unknown direction: %s" % line)
    return default


def choose_sources(cfg, entries):
    """Choose which data files to quiz on; 'all' or a list of source names."""
    available = []
    for e in entries:
        src = e.get("source")
        if src and src not in available:
            available.append(src)
    print("Quiz on file:")
    print("  [all] All files")
    for i, src in enumerate(available, 1):
        print("  [%d] %s" % (i, src))
    default = cfg.get("sources", "all")
    default_str = default if isinstance(default, str) else ", ".join(default)
    line = consoleio.input_line("Choose [%s]: " % default_str).strip()
    if not line:
        return default
    if line.lower() == "all":
        return "all"
    if line.isdigit():
        idx = int(line)
        if 1 <= idx <= len(available):
            return [available[idx - 1]]
        print("  unknown file: %s" % line)
        return default
    tokens = [t.strip() for t in line.split(",")]
    keys = [t for t in tokens if t in available]
    if not keys:
        print("  unknown file: %s" % line)
        return default
    if len(keys) == len(available):
        return "all"
    return keys


def choose_pos_scope(cfg):
    print("Part-of-speech scope:")
    print("  all, or comma-separated (verb,noun,adjective,adverb,phrase)")
    default = cfg.get("pos_scope", "all")
    line = consoleio.input_line("Choose [%s]: " % default).strip()
    if not line:
        return default
    if line.lower() == "all":
        return "all"
    keys = []
    for token in line.split(","):
        token = token.strip()
        if token in loader.POS_CATALOG:
            keys.append(token)
        else:
            print("  unknown pos: %s" % token)
    if not keys:
        return default
    if len(keys) == len(loader.POS_CATALOG):
        return "all"
    return ",".join(keys)


def resolve_directions(scope):
    if scope == "both":
        return list(engine.DIRECTIONS)
    if scope in engine.DIRECTIONS:
        return [scope]
    return []


def resolve_pos(scope):
    if scope == "all":
        return list(loader.POS_CATALOG)
    return [p for p in scope.split(",") if p in loader.POS_CATALOG]


class Session(object):
    def __init__(self, cfg, entries, progress_path):
        self.cfg = cfg
        self.entries = entries
        self.progress_path = progress_path
        self.states = tprogress.load_progress(progress_path)
        self.stats = {
            "prompts": 0,
            "correct": 0,
            "incorrect": 0,
            "start": time.monotonic(),
            "by_direction": {},
            "by_pos": {},
        }

    def _scope_entries(self):
        pos_set = set(resolve_pos(self.cfg["pos_scope"]))
        src = self.cfg.get("sources", "all")
        if src == "all":
            return [e for e in self.entries if e.get("pos") in pos_set]
        src_set = {src} if isinstance(src, str) else set(src)
        return [e for e in self.entries
                if e.get("pos") in pos_set and e.get("source") in src_set]

    def _scope_directions(self):
        return resolve_directions(self.cfg["direction"])

    def run(self):
        entries = self._scope_entries()
        directions = self._scope_directions()
        if not entries or not directions:
            print("\nNo items in scope. Use :mode or :pos to widen scope.")
            return "new"
        while True:
            picked = engine.select_item(entries, directions, self.states, datetime.now())
            if picked is None:
                print("\nNo items in scope. Use :new to change setup.")
                return "new"
            entry, direction = picked
            outcome = self.quiz(entry, direction)
            if outcome != "continue":
                return outcome
            entries = self._scope_entries()
            directions = self._scope_directions()

    def quiz(self, entry, direction):
        while True:
            line, expected_list = modes.prompt(entry, direction)
            print(line)
            t0 = time.monotonic()
            try:
                raw = consoleio.input_line("> ").strip()
            except EOFError:
                return "quit"
            seconds = time.monotonic() - t0
            if raw.startswith(":"):
                result = self.command(entry, direction, raw, expected_list)
                if result == "repeat":
                    continue
                return result
            correct = modes.is_correct(entry, direction, raw)
            self.record(entry, direction, correct, seconds)
            if correct:
                print("  " + tmodes.green("[OK]"))
                feedback = modes.success_feedback(entry, direction)
                if feedback:
                    print("  " + tmodes.bold(feedback))
                return "continue"
            print("  " + tmodes.red("[X] expected: %s" % " / ".join(expected_list)))
            print("  Try again.")

    # -- commands --

    def show_help(self):
        print("\nCommands:")
        print("  :help        Show this help.")
        print("  :quit        Show session report, save progress, exit.")
        print("  :new         Return to session setup.")
        print("  :mode <d>    Change direction (fr2en,en2fr,both).")
        print("  :pos <p>     Change POS scope (all | comma-separated).")
        print("  :skip        Skip this prompt (counted as incorrect).")
        print("  :reveal      Show the answer (counted as incorrect).")
        print("  :repeat      Restart this item's re-prompt loop.")
        print("  :stats       Show session + per-item stats.\n")

    def command(self, entry, direction, raw, expected_list):
        parts = raw.split(None, 1)
        name = parts[0]
        arg = parts[1] if len(parts) > 1 else ""
        if name == ":help":
            self.show_help()
            return "repeat"
        if name == ":quit":
            return "quit"
        if name == ":new":
            return "new"
        if name == ":skip":
            self.record(entry, direction, False, None)
            print("  " + tmodes.red("[X] skipped - expected: %s" % " / ".join(expected_list)))
            return "continue"
        if name == ":reveal":
            self.record(entry, direction, False, None)
            print("  " + tmodes.red("[X] expected: %s" % " / ".join(expected_list)))
            return "continue"
        if name == ":repeat":
            return "repeat"
        if name == ":mode":
            if arg:
                if arg in engine.DIRECTIONS or arg == "both":
                    self.cfg["direction"] = arg
                    print("  direction: %s" % arg)
                else:
                    print("  usage: :mode fr2en|en2fr|both")
            else:
                print("  usage: :mode fr2en|en2fr|both")
            return "repeat"
        if name == ":pos":
            if arg:
                scope = choose_pos_scope({"pos_scope": arg})
                self.cfg["pos_scope"] = scope
                print("  pos scope: %s" % scope)
            else:
                print("  usage: :pos all|verb,noun,...")
            return "repeat"
        if name == ":stats":
            self.show_stats()
            return "repeat"
        print("  unknown command: %s" % raw)
        return "repeat"

    # -- recording --

    def record(self, entry, direction, correct, seconds):
        st = engine.get_state(self.states, entry["id"], direction)
        tren.record_answer(st, correct, seconds, datetime.now())
        self.states[engine.key(entry["id"], direction)] = st
        self.stats["prompts"] += 1
        if correct:
            self.stats["correct"] += 1
        else:
            self.stats["incorrect"] += 1
        self.stats["by_direction"][direction] = self.stats["by_direction"].get(direction, 0) + 1
        pos = entry.get("pos", "unknown")
        self.stats["by_pos"][pos] = self.stats["by_pos"].get(pos, 0) + 1
        tprogress.save_progress(self.progress_path, self.states)

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
        if s["by_direction"]:
            print("by direction: %s" % ", ".join("%s %d" % (k, v)
                                                 for k, v in sorted(s["by_direction"].items())))
        if s["by_pos"]:
            print("by pos: %s" % ", ".join("%s %d" % (k, v) for k, v in sorted(s["by_pos"].items())))

        rows = []
        for entry in self.entries:
            for direction in engine.DIRECTIONS:
                st = engine.get_state(self.states, entry["id"], direction)
                wacc = tren.windowed_accuracy(st)
                if wacc is None:
                    continue
                rows.append((entry["id"], direction, len(st.recent_results),
                             tren.windowed_avg_time(st), st.streak,
                             st.longest_streak, wacc))
        rows.sort(key=lambda r: (r[6], r[0], r[1]))
        print("\n--- Items with recent attempts (%d) ---" % len(rows))
        for r in rows[:20]:
            avg = "%.1fs" % r[3] if r[3] is not None else "-"
            print("  %-12s %-6s  n=%-3d acc=%5.1f%%  streak=%d/%d  avg=%s"
                  % (r[0], r[1], r[2], r[6], r[4], r[5], avg))

    def report(self):
        self.show_stats()
        print("\n--- Weakest words ---")
        acc_by_id = {}
        for entry in self.entries:
            totals = []
            for direction in engine.DIRECTIONS:
                st = engine.get_state(self.states, entry["id"], direction)
                wacc = tren.windowed_accuracy(st)
                if wacc is not None:
                    totals.append((wacc, len(st.recent_results)))
            if totals:
                wsum = sum(a * n for a, n in totals)
                nsum = sum(n for _, n in totals)
                acc_by_id[entry["id"]] = (wsum / nsum if nsum else 0.0, nsum)
        for name, (acc, tot) in sorted(acc_by_id.items(), key=lambda kv: kv[1][0])[:5]:
            print("  %-12s acc=%5.1f%%  (n=%d)" % (name, acc, tot))


def main(config_path=None):
    config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = load_config(config_path)

    progress_path = str(resolve(ROOT, cfg["data"].get("progress", "data/vocab_progress.json")))

    verbs_path = cfg["data"].get("verbs")
    verbs_src = str(resolve(ROOT, verbs_path)) if verbs_path else None

    vocab_path = cfg["data"].get("vocab")
    if isinstance(vocab_path, str):
        vocab_path = [vocab_path]
    vocab_srcs = [str(resolve(ROOT, p)) for p in vocab_path or [] if p]
    try:
        entries = loader.load_entries(verbs_src, vocab_srcs)
    except loader.ValidationError as exc:
        print("vocabulary data failed validation:\n%s" % exc)
        return 1

    print("French Vocabulary Tutor\n")
    try:
        while True:
            cfg["direction"] = choose_direction(cfg)
            cfg["sources"] = choose_sources(cfg, entries)
            save_config(config_path, cfg)
            session = Session(cfg, entries, progress_path)
            outcome = session.run()
            if outcome == "quit":
                tprogress.save_progress(progress_path, session.states)
                session.report()
                print("\nGoodbye.")
                return 0
    except KeyboardInterrupt:
        print("\nInterrupted - progress saved.")
        tprogress.save_progress(progress_path, session.states)
        return 130
    except EOFError:
        print("\nGoodbye.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
