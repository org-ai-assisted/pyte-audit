# Bug H: a bare line feed after a width-filling line leaves a blank row (last-column flag not cleared)

**Class:** rendering correctness (spurious blank rows)
**Affected:** upstream master `0.8.3.dev`, Debian `0.8.0-3` (verified on both)
**Upstream fix:** none. Open [PR #210](https://github.com/selectel/pyte/pull/210)
addresses only the parser-crash class and does not touch `DECAWM` wrapping.
**Fork fix:** [org-ai-assisted/pyte#7](https://github.com/org-ai-assisted/pyte/pull/7) --
the cursor-move primitives reset the last-column flag, with native regression
tests (`tests/test_screen.py`; pre-fix fail, 124 pass / 0 fail / 0 skip /
1 xfail post-fix).
**Reference terminal:** behaviour below was verified against **xterm** with a
`ESC[6n` (DSR) cursor-position probe -- see [Reference behaviour](#reference-behaviour).
**Upstream:** no matching report found -- **likely novel**.

## Repro
```python
import pyte
s = pyte.Screen(3, 3)             # DECAWM on, LNM off (pyte defaults)
pyte.Stream(s).feed("abc\nX")     # a width-filling line, a bare LF, one more char
print(s.display)                  # ['abc', '   ', 'X  ']  -> blank row 1, X two rows down
```
Any screen-width run of printable glyphs followed by a bare `\n` and more text
reproduces it; wider screens show `row, blank, row, blank ...` for a full-viewport
board fed as raw bytes. `IND` (`ESC D`) is affected identically.

## Reference behaviour
xterm (10 columns), `ESC[6n` after each step, cursor reported 1-based:

| after            | DSR reply   | meaning                                    |
|------------------|-------------|--------------------------------------------|
| `0123456789`     | `1;10`      | row 1, last column, last-column flag set   |
| bare `\n`        | `2;10`      | moved down one row, **column unchanged**   |
| `X`              | `2;10`      | `X` written into the **last column**       |

So a real terminal clears the last-column flag on a line feed (no blank row)
**and keeps the column** -- the next character lands at the last column of the
new line (a staircase), it does **not** return to column 0.

## Expected vs actual
- Expected (xterm, above): `['abc', '  X', '   ']` -- the second line lands
  directly below, `X` at the last column.
- Actual: `['abc', '   ', 'X  ']` -- a blank row is inserted and `X` drops to
  column 0 two rows down.

## Root cause
pyte models autowrap's deferred wrap (the "last column flag", LCF) implicitly by
parking the cursor one past the end: after a character is drawn into the final
column with `DECAWM` set, `cursor.x == columns` and the wrap is performed only
when the *next* printable character arrives (`Screen.draw`: `if self.cursor.x ==
self.columns: ... carriage_return(); linefeed()`).

Only `Screen.cursor_back` cleared that state (`if self.cursor.x == self.columns:
self.cursor.x -= 1`). `Screen.index` (line feed, `IND`, `NEL`), `reverse_index`,
`cursor_up`, `cursor_down` and `cursor_to_line` (`VPA`) did not. So a bare `\n`
between two width-filling lines advances the cursor twice: once for the line
feed itself, and again for the deferred wrap that fires on the first character
of the next line -- landing it two rows down and leaving a blank row. `IND`,
`cursor-down` and `VPA` from the parked state show the same doubling, verified
against xterm by DSR (down/absolute move, column kept at the last cell).

A line feed resets the last-column flag while keeping the column, so the next
character lands at the last column of the new line. In normal PTY use `ONLCR`
turns `\n` into `\r\n`, and the `\r` resets `cursor.x` to 0 before the line feed,
so the double advance never happens -- which is why this only bites *bare* `\n`
output, e.g. a raw-fed full-viewport board or a program writing `\n` without `\r`.

## Proposed fix
Consolidate the reset `cursor_back` already did into one helper and call it from
every cursor-move primitive, keeping the column:
```python
def _clear_last_column_flag(self) -> None:
    if self.cursor.x == self.columns:
        self.cursor.x -= 1

def index(self) -> None:
    self._clear_last_column_flag()
    ...

# likewise reverse_index, cursor_up, cursor_down, cursor_to_line, and
# cursor_back (which had the inline version already).
```
The reset is unconditional, matching `cursor_back`: the last-column park exists
with autowrap off too (the cursor sits at the last column so `draw()` overwrites
there), and a move resolves it the same way. The `secure-terminal` terminal
emulator carries a `HistoryScreen` subclass workaround for the line-feed case
(it pins the distribution `pyte`, which lacks this fix).
