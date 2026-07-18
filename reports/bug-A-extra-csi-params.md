# Bug A: extra CSI parameters crash `Stream.feed()` with `TypeError`

**Class:** DoS (unhandled exception on untrusted input)
**Affected:** upstream master `0.8.3.dev`, Debian `0.8.0-3`
**Upstream fix:** open [PR #210](https://github.com/selectel/pyte/pull/210) fixes this (verified against the PR head).
**Upstream:** already reported - open issue [#209] crash 3 (`cursor_down() takes from 1 to 2 positional arguments but 3 were given`).

## Repro
```python
import pyte
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[1;2A")     # cursor_up(1, 2)
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[1;2;3H")   # cursor_position(1, 2, 3)
```
`TypeError: Screen.cursor_up() takes from 1 to 2 positional arguments but 3 were given`

## Expected vs actual
- Expected: surplus CSI parameters are ignored; no exception reaches the caller.
- Actual: `TypeError` propagates out of `feed()`, crashing the application.

## Root cause
`streams.py` `_parser_fsm()` dispatches `csi_dispatch[char](*params)` with every
collected parameter; single-argument handlers (`cursor_up`, `insert_characters`,
...) then get too many positional args. Affects essentially every one-arg CSI
final (`@ A B C D G L M P X d e ...`).

## Proposed fix
Wrap the CSI dispatch and route an argument mismatch to the existing `debug`
sink (the catch-all for unrecognised sequences):
```python
handler = csi_dispatch[char]
try:
    handler(*params, private=True) if private else handler(*params)
except TypeError:
    debug(*params, private=private)
```
(Alternative: give the one-arg CSI handlers `*args` signatures.)

[#209]: https://github.com/selectel/pyte/issues/209
