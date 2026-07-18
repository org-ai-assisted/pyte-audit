# Bug C: `erase_in_line` / `erase_in_display` crash on an unhandled `how`

**Class:** DoS (unhandled exception on untrusted input)
**Affected:** upstream master `0.8.3.dev`, Debian `0.8.0-3`
**Upstream:** partly - PR [#108] added `*args` to `erase_in_display` for a related
case; the `UnboundLocalError` remains for out-of-range `how`. **CodeQL**
independently flags it (`screens.py:792`, `:825`, "Potentially uninitialized
local variable 'interval'").

## Repro
```python
import pyte
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[3K")   # erase_in_line(3)
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[4J")   # erase_in_display(4)
```
`UnboundLocalError: cannot access local variable 'interval' where it is not associated with a value`

## Expected vs actual
- Expected: an unsupported erase mode is a no-op (as terminals ignore `CSI 3 K`).
- Actual: `UnboundLocalError` escapes `feed()`.

## Root cause
Both methods bind `interval` only for the `how` values they handle; any other
value leaves it unbound before `for x in interval` / `self.dirty.update(interval)`.

## Proposed fix
Add an `else: return` (no-op) branch to each method after the recognised `how`
values.

[#108]: https://github.com/selectel/pyte/pull/108
