#!/usr/bin/env python3
"""Reproduce every pyte-audit finding against whatever `pyte` is importable.

Usage:
    PYTHONPATH=/path/to/pyte/checkout python3 reproduce_all.py

Prints one line per finding: CRASH (bug present) or ok. Bug E is checked by
state, not exception. Exit code is the number of findings still present.
"""
import sys
import pyte


def feed(data):
    pyte.Stream(pyte.Screen(10, 5)).feed(data)


CASES = [
    ("A extra CSI params      ESC[1;2A",   lambda: feed("\x1b[1;2A")),
    ("A extra CSI params      ESC[1;2;3H", lambda: feed("\x1b[1;2;3H")),
    ("B private kwarg         ESC[?0A",    lambda: feed("\x1b[?0A")),
    ("C erase_in_line how=3   ESC[3K",     lambda: feed("\x1b[3K")),
    ("C erase_in_display how=4 ESC[4J",    lambda: feed("\x1b[4J")),
    ("D VPA under DECOM       ESC[?6h;5d", lambda: feed("\x1b[?6h\x1b[5d")),
    ("D DSR under DECOM       ESC[?6h;6n", lambda: feed("\x1b[?6h\x1b[6n")),
    ("F unicode digit         ESC[<U+00B3>A", lambda: feed("\x1b[\u00b3A")),
]


def check_bug_e():
    s = pyte.Screen(1, 10)
    s.cursor_position(9, 1)
    s.resize(lines=1, columns=1)
    oob = not (0 <= s.cursor.y < s.lines)
    s.draw("X")
    lost = "X" not in "".join(s.display)
    return oob or lost


def main():
    print("pyte:", getattr(pyte, "__version__", "n/a"),
          "at", pyte.__file__)
    present = 0
    for label, fn in CASES:
        try:
            fn()
            print(f"  ok    {label}")
        except Exception as exc:  # noqa: BLE001 - repro harness
            present += 1
            print(f"  CRASH {label}  -> {type(exc).__name__}: {str(exc)[:40]}")
    if check_bug_e():
        present += 1
        print("  CRASH E resize cursor OOB   resize(1,1) leaves cursor off-screen, draw lost")
    else:
        print("  ok    E resize cursor OOB")
    print(f"findings still present: {present}")
    return present


if __name__ == "__main__":
    sys.exit(main())
