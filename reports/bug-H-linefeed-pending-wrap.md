# Bug H: a bare line feed after a width-filling line leaves a blank row (deferred wrap not cleared)

**Class:** rendering correctness / data integrity (spurious blank rows)
**Affected:** upstream master `0.8.3.dev`, Debian `0.8.0-3` (verified on both)
**Upstream fix:** none. Open [PR #210](https://github.com/selectel/pyte/pull/210)
addresses only the parser-crash class and does not touch `DECAWM` wrapping.
**Fork fix:** [org-ai-assisted/pyte#7](https://github.com/org-ai-assisted/pyte/pull/7) --
`Screen.linefeed` clears the deferred wrap, with a native regression test
(`tests/test_screen.py`; 2 fail pre-fix, 121 pass / 0 fail / 0 skip / 1 xfail post-fix).
**Upstream:** no matching report found -- **likely novel**.

## Repro
```python
import pyte
s = pyte.Screen(3, 3)             # DECAWM on, LNM off (pyte defaults)
pyte.Stream(s).feed("abc\ndef")   # a width-filling line, a bare LF, the next line
print(s.display)                  # ['abc', '   ', 'def']  -> blank row 1
```
Expected `['abc', 'def', '   ']`. Any screen-width run of printable glyphs
followed by a bare `\n` and more text reproduces it; wider screens show
`row, blank, row, blank ...` for a full-viewport board fed as raw bytes.

## Expected vs actual
- Expected: the second line lands directly below the first, as a real terminal
  (xterm) renders it -- a line feed clears the last-column flag.
- Actual: a blank row is inserted between the two lines; every full-width line
  is followed by an empty one.

## Root cause
pyte models autowrap's deferred wrap ("last column flag", LCF) implicitly, by
parking the cursor one past the end: after a character is drawn into the final
column with `DECAWM` set, `cursor.x == columns` and the wrap is performed only
when the *next* printable character arrives (`Screen.draw`: `if self.cursor.x
== self.columns: ... carriage_return(); linefeed()`).

`Screen.linefeed` (and `Screen.index`) never clear that state. So a bare `\n`
between two width-filling lines advances the cursor twice: once for the line
feed itself, and again for the deferred wrap that fires on the first character
of the next line -- landing it two rows down and leaving a blank row.

A real terminal resets the LCF on a line feed, so the next character lands at
column 0 of the new line. In normal PTY use `ONLCR` turns `\n` into `\r\n`, and
the `\r` (carriage return) resets `cursor.x` to 0 before the line feed, so the
double advance never happens -- which is why this only bites *bare* `\n` output,
e.g. a raw-fed full-viewport board or a program writing `\n` without `\r`.

## Proposed fix
Clear the deferred wrap at the start of `linefeed`, guarded on `DECAWM`:
```python
def linefeed(self) -> None:
    if mo.DECAWM in self.mode and self.cursor.x >= self.columns:
        self.cursor.x = 0
    self.index()
    if mo.LNM in self.mode:
        self.carriage_return()
```
The `DECAWM` guard matters: with autowrap off pyte parks the cursor at the last
column to *overwrite* the next character there, so forcing column 0 would be
wrong. This is the same fix the `secure-terminal` terminal emulator carries as a
`HistoryScreen` subclass workaround.
