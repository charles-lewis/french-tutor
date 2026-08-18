#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launcher: run the vocabulary tutor from any working directory."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from vocab.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
