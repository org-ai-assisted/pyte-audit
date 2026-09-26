# Bug K: resize() to fewer columns leaves stale tab stops; tab() parks the cursor off-screen and the next draw is lost

**Class:** data integrity (silent loss of drawn text)
**Affected:** upstream master `0.8.3.dev` (`0718fa8`) and the org-ai-assisted/pyte
fork tip (verified by runtime repro on the upstream mirror; the fork does not
modify `resize()` or `tab()`).
**Upstream fix:** none. [PR #210](https://github.com/selectel/pyte/pull/210) fixes
only the parser-crash class and does not touch `resize()` or `tab()`.
**Fork fix:** none -- tracked as a strict-xfail regression test in
org-ai-assisted/dist-ai (`pyte-tests`); the pyte source is kept pristine.
**Upstream:** no issue or PR describes it -- **likely novel** (not crash-shaped).

## Repro
```python
import pyte
s = pyte.Screen(80, 24)
s.resize(lines=24, columns=20)   # tabstops still {8, 16, 24, 32, ...} from the 80-col reset
s.cursor_position(1, 19)         # 0-based x = 18
s.tab()
print(s.cursor.x)                # 24 -- but columns == 20
s.draw('Z')
print(repr(s.display[0]))        # 20 spaces -- 'Z' is gone
```

## Expected vs actual
- Expected: after a column-shrinking `resize()` a tab must not move the cursor
  past the last column; `tab()` should clamp to `columns - 1`, so the following
  `draw('Z')` is visible.
- Actual: `cursor.x` reaches `24` on a 20-column screen and the drawn `'Z'` never
  appears in `display` (a real terminal renders `Z` in the last column).

## Root cause
`self.tabstops` is computed only in `reset()` for the INITIAL column count
(`set(range(8, self.columns, 8))`). `resize()` never prunes or recomputes it, so
after a column shrink the set still holds stops beyond the new width. `tab()`
selects the first stop greater than `cursor.x` with no clamp to `self.columns - 1`,
so the cursor can land at `x == self.columns` (or beyond). The next `draw()` writes
`line[x]` for `x >= self.columns`, which `display` never iterates
(`range(self.columns)`), so the character silently disappears.

## Proposed fix
On a column-shrinking `resize()`, drop tab stops `>= self.columns` (or recompute
`self.tabstops` for the new width), AND clamp `tab()`'s result to
`self.columns - 1` so a stale stop can never park the cursor off-screen.

## Related upstream
Read-only survey of `selectel/pyte`; nothing was filed (no upstream contact). No
issue or PR describes stale tab stops after resize. [PR #210] is the parser-crash
class only and does not touch `resize()` or `tab()`.
