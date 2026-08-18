# -*- coding: utf-8 -*-
"""Unicode-safe Windows console line input.

``input()`` on some Windows console/terminal setups reads in the active code
page, so backspacing over an accented character can leave a stray half-coded
byte and the answer then fails to match.  ``ReadConsoleW`` always reads UTF-16
and lets the console edit whole characters, so ``pr\xe9f\xe9r\xe9``-style input
survives backspacing.  Falls back to plain ``input()`` when stdin is not a
console (piped/redirected) or ctypes is unavailable.
"""

import os
import sys

if os.name != "nt":
    # CPython only uses GNU readline's UTF-8-aware line editing once the module
    # is imported; without it, input() falls back to byte-based editing and
    # backspacing over a multi-byte character (é) corrupts the line.
    try:
        import readline  # noqa: F401
    except ImportError:
        pass

ctypes = None
if os.name == "nt":
    try:
        import ctypes
        from ctypes import wintypes
    except (ImportError, ValueError):
        ctypes = None

_ERROR_OPERATION_ABORTED = 0x3E3  # Ctrl+C while reading


def _read_console_line():
    """Return ('line', text) / ('abort',) on Ctrl+C / ('eof',) on EOF, or None
    if stdin is not a Windows console."""
    if os.name != "nt" or ctypes is None:
        return None
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
    mode = wintypes.DWORD()
    if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        return None
    buf = ctypes.create_unicode_buffer(4096)
    nread = wintypes.DWORD(0)
    if not kernel32.ReadConsoleW(handle, buf, 4095, ctypes.byref(nread), None):
        if kernel32.GetLastError() == _ERROR_OPERATION_ABORTED:
            return "abort"
        return "eof"
    n = nread.value
    if n == 0:
        return "eof"
    line = buf[:n].rstrip("\r\n")
    return "line", line


def input_line(prompt=""):
    """Like input(), but Unicode-safe on the Windows console."""
    if os.name == "nt" and sys.stdin.isatty():
        sys.stdout.write(prompt)
        sys.stdout.flush()
        result = _read_console_line()
        if result is None:
            return input()
        status = result[0]
        if status == "abort":
            raise KeyboardInterrupt
        if status == "eof":
            raise EOFError
        return result[1]
    return input(prompt)
