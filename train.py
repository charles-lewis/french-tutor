#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launcher: run the trainer from any working directory."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from trainer.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
