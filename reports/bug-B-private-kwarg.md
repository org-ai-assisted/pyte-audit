# Bug B: private `?` CSI crashes with `TypeError: unexpected keyword argument 'private'`

**Class:** DoS (unhandled exception on untrusted input)
**Affected:** upstream master `0.8.3.dev`, Debian `0.8.0-3`
**Upstream fix:** open [PR #210](https://github.com/selectel/pyte/pull/210) fixes this (verified against the PR head).
**Upstream:** already reported - open [#209] crash 1 (`insert_lines() ... 'private'`), open [#126] (w3m, since 2019), closed [#67] (`set_margins ... 'private'`, still unfixed for that handler).

## Repro
```python
import pyte
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[?0A")   # cursor_up(0, private=True)
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[?0@")   # insert_characters(0, private=True)
```
`TypeError: Screen.cursor_up() got an unexpected keyword argument 'private'`

## Expected vs actual
- Expected: a private marker on a command with no private form is ignored.
- Actual: `TypeError` escapes `feed()`.

## Root cause
When a `?` is seen the parser calls `csi_dispatch[char](*params, private=True)`
for the final byte regardless of whether that handler accepts `private`. Only a
few (`set_mode`, `reset_mode`, `select_graphic_rendition`,
`report_device_attributes`) do. Upstream fixed the SGR case ([#202]) but not the
general one.

## Proposed fix
Same `try/except TypeError -> debug(...)` guard as Bug A covers this too (the
`private=True` mismatch raises `TypeError`).

[#209]: https://github.com/selectel/pyte/issues/209
[#126]: https://github.com/selectel/pyte/issues/126
[#67]: https://github.com/selectel/pyte/issues/67
[#202]: https://github.com/selectel/pyte/issues/202
