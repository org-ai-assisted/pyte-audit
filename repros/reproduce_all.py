#!/usr/bin/python3 -Bsu
"""Reproduce every pyte-audit finding against whatever `pyte` is importable.

Usage:
    PYTHONPATH=/path/to/pyte/checkout python3 reproduce_all.py

Prints one line per finding: CRASH (bug present) or ok. Bugs E, G, H, I, J and K are
checked by state; L by state or exception (version-dependent). Exit code is the number of findings still
present.
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


def check_bug_g():
    s = pyte.HistoryScreen(10, 3, history=20)
    stream = pyte.Stream(s)
    for _ in range(8):
        stream.feed("ABCDEFGHIJ\r\n")
    s.resize(lines=3, columns=4)
    try:
        s.prev_page()
        return False
    except Exception:
        return True


def check_bug_h():
    s = pyte.Screen(3, 3)                # DECAWM on, LNM off by default
    pyte.Stream(s).feed("abc\nX")        # full-width line, bare LF, one more char
    # xterm: last-column flag cleared, column kept -> ["abc", "  X", "   "].
    # Bug present: the deferred wrap survives the LF -> blank row, X at (2, 0).
    return s.display != ["abc", "  X", "   "]


def check_bug_i():
    # Bug present unless BOTH SU (CSI S) and SD (CSI T) scroll correctly. Judge by BEHAVIOUR,
    # not by whether the S/T mappings exist: a partial or wrong implementation (only one byte
    # mapped, a missing Screen handler, or an incorrect scroll) must still read as the bug.
    def _scrolled(seq):
        s = pyte.Screen(5, 4)
        st = pyte.Stream(s)
        st.feed("AAAAA\r\nBBBBB\r\nCCCCC\r\nDDDDD")
        st.feed(seq)
        return s.display
    blank = " " * 5
    sd_ok = _scrolled("\x1b[T") == [blank, "AAAAA", "BBBBB", "CCCCC"]   # SD 1: down, blank at top
    su_ok = _scrolled("\x1b[S") == ["BBBBB", "CCCCC", "DDDDD", blank]   # SU 1: up, blank at bottom
    return not (sd_ok and su_ok)


def check_bug_j():
    # resize() smaller keeps the WRONG rows when a scroll region with top > 0 is
    # active: the documented top-clip keeps the latest rows; the bug keeps the
    # earliest. Judged by state.
    s = pyte.Screen(80, 24)
    st = pyte.Stream(s)
    for i in range(24):
        st.feed("row%02d\r\n" % i)
    st.feed("\x1b[5;20r")                # DECSTBM: top > 0
    s.resize(lines=10)
    return not s.display[0].startswith("row15")   # latest rows should survive


def check_bug_k():
    # resize() to fewer columns leaves stale tab stops; tab() parks the cursor
    # at/after self.columns and the next draw is lost off-screen. Judged by state.
    s = pyte.Screen(80, 24)
    s.resize(lines=24, columns=20)
    s.cursor_position(1, 19)             # x = 18
    s.tab()
    return s.cursor.x >= s.columns


def check_bug_l():
    # Erasing/deleting a wide-char head orphans the empty-data stub. On released
    # builds (0.8.0-3, 0.8.2) render() indexes char[0] and RAISES IndexError; on
    # the git tip (render uses wcswidth(char)) it instead yields a row shorter than
    # columns. Either manifestation is the bug -- judged by state OR exception.
    def _broken(build):
        try:
            s = build()
            return len(s.display[0]) != s.columns
        except Exception:
            return True                      # crash form (released render char[0])
    def _erase():
        s = pyte.Screen(5, 2)
        st = pyte.Stream(s)
        st.feed("a\u30b3b")             # width-2 CJK char (U+30B3)
        st.feed("\x1b[1;2H")
        st.feed("\x1b[X")
        return s
    def _delete():
        s = pyte.Screen(5, 2)
        s.draw("a"); s.draw("\u30b3"); s.draw("b")
        s.cursor_position(1, 2)
        s.delete_characters(1)
        return s
    return _broken(_erase) or _broken(_delete)


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
    if check_bug_g():
        present += 1
        print("  CRASH G HistoryScreen.after_event   resize+prev_page dict-mutation-in-loop")
    else:
        print("  ok    G HistoryScreen.after_event")
    if check_bug_h():
        present += 1
        print("  CRASH H linefeed blank row   bare LF after a full-width line inserts a blank row")
    else:
        print("  ok    H linefeed blank row")
    if check_bug_i():
        present += 1
        print("  CRASH I no SU/SD            CSI S/T scroll-region scroll is a silent no-op")
    else:
        print("  ok    I no SU/SD")
    if check_bug_j():
        present += 1
        print("  CRASH J resize wrong rows   shrink under an active scroll region keeps earliest rows")
    else:
        print("  ok    J resize wrong rows")
    if check_bug_k():
        present += 1
        print("  CRASH K stale tabstops      column shrink leaves tab() parking the cursor off-screen")
    else:
        print("  ok    K stale tabstops")
    if check_bug_l():
        present += 1
        print("  CRASH L wide-char orphan    erase/delete of a wide-char head: crash (released) or short row (tip)")
    else:
        print("  ok    L wide-char orphan")
    print(f"findings still present: {present}")
    return present


if __name__ == "__main__":
    sys.exit(main())
