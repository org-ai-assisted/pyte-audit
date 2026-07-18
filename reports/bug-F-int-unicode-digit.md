# Bug F: Unicode "digit" in a CSI parameter crashes with `ValueError`

**Class:** DoS (unhandled exception on untrusted input)
**Affected:** upstream master `0.8.3.dev`, Debian `0.8.0-3`
**Upstream:** already reported - open [#209] crash 2
(`ValueError: invalid literal for int() with base 10: '<U+00B3>' (superscript three)`).
Found by upstream's fuzzing; corroborated here.

## Repro
```python
import pyte
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[\u00b3A")   # superscript three as a CSI param
```
`ValueError: invalid literal for int() with base 10: '<U+00B3>' (superscript three)`

## Root cause
The parser accumulates a parameter with `elif char.isdigit(): current += char`,
then `int(current)`. Python's `str.isdigit()` returns `True` for many non-ASCII
"digit" characters (superscripts, other scripts) that `int()` cannot parse, so
`int(current)` raises `ValueError`.

## Expected vs actual
- Expected: only ASCII `0-9` accepted as CSI digits; anything else ends/aborts
  the parameter without crashing.
- Actual: `ValueError` escapes `feed()`.

## Proposed fix
Gate on ASCII digits, e.g. `elif char in "0123456789":` (or `char.isascii() and
char.isdigit()`) instead of `char.isdigit()`.

[#209]: https://github.com/selectel/pyte/issues/209
