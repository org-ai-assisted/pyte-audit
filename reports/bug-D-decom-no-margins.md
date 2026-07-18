# Bug D: VPA / DSR under DECOM without margins crash (`AssertionError`)

**Class:** DoS (unhandled exception on untrusted input)
**Affected:** upstream master `0.8.3.dev` (`AssertionError`), Debian `0.8.0-3` (`AttributeError`)
**Upstream fix:** none -- open [PR #210](https://github.com/selectel/pyte/pull/210) does NOT address this (verified against the PR head).
**Upstream:** no matching report found - **likely novel** (may fall under [#209]'s
"there were others").

## Repro
```python
import pyte
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[?6h\x1b[5d")   # DECOM on, then VPA
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[?6h\x1b[6n")   # DECOM on, then DSR
```
`AssertionError` (upstream); `AttributeError: 'NoneType' object has no attribute 'top'` (Debian, and upstream under `python -O`).

## Expected vs actual
- Expected: with no scrolling region set, DECOM is relative to the whole screen
  (`margins.top == 0`); no crash. This is exactly what `cursor_position()` does.
- Actual: `cursor_to_line()` (VPA) and `report_device_status(6)` (DSR) do
  `assert self.margins is not None` then read `self.margins.top`, which fails
  when DECOM is set but no `DECSTBM` was received.

## Root cause
Inconsistent guarding: `cursor_position()` uses
`if self.margins is not None and mo.DECOM in self.mode`, but these two methods
assume margins exist under DECOM.

## Proposed fix
Guard both on `self.margins`, mirroring `cursor_position()`:
`if mo.DECOM in self.mode and self.margins is not None:`

[#209]: https://github.com/selectel/pyte/issues/209
