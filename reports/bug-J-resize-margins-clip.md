# Bug J: resize() smaller keeps the WRONG rows when a scrolling region is active

**Class:** data integrity (silent loss of the rows that should have been kept)
**Affected:** upstream master `0.8.3.dev` (`0718fa8`) and the org-ai-assisted/pyte
fork tip (verified by runtime repro on the upstream mirror; the fork does not
modify `resize()`, `delete_lines()` or `set_margins()`).
**Upstream fix:** none. [PR #210](https://github.com/selectel/pyte/pull/210) fixes
only the parser-crash class and does not touch `resize()`.
**Fork fix:** none -- tracked as a strict-xfail regression test in
org-ai-assisted/dist-ai (`pyte-tests`); the pyte source is kept pristine.
**Upstream:** no issue or PR describes it -- **likely novel** (not crash-shaped, so
the crash-oriented fuzzers and PR #210 never reach it).

## Repro
```python
import pyte
s = pyte.Screen(80, 24)
st = pyte.Stream(s)
for i in range(24):
    st.feed('row%02d\r\n' % i)   # rows row00..row23
st.feed('\x1b[5;20r')            # DECSTBM: a scrolling region with top > 0
s.resize(lines=10)
print(s.display[0].strip())      # 'row01'  -- the EARLIEST rows survived
```
Control (same feed, no `DECSTBM` line): `s.display[0]` is `'row15'` -- the latest
rows survive, matching the documented contract. Merely having an active scrolling
region flips which half of the buffer is kept on shrink.

## Expected vs actual
- Expected: `resize()`'s own docstring promises "if the requested screen size has
  less lines than the existing screen, lines will be clipped at the top" -- i.e.
  the most-recent rows are kept (`row15..row23`), exactly as the no-margin control
  shows.
- Actual with an active `top > 0` region: the earliest rows (`row01..`) are kept
  and the recent rows are lost.

## Root cause
`resize()` implements the top-clip by moving the cursor to `(0, 0)` and calling
`delete_lines(old_lines - new_lines)`:
```python
if lines < self.lines:
    self.save_cursor()
    self.cursor_position(0, 0)
    self.delete_lines(self.lines - lines)  # Drop from the top.
    self.restore_cursor()
...
self.lines, self.columns = lines, columns
self.set_margins()                         # margins reset only AFTER the delete
```
But `delete_lines()` is guarded by `if top <= self.cursor.y <= bottom` against the
CURRENT (pre-resize) margins. With a `DECSTBM` region whose `top > 0`, cursor
`y = 0` falls outside `[top, bottom]`, so `delete_lines()` is a silent no-op -- the
top rows are never dropped. `set_margins()` (which would reset the region for the
new geometry) runs only afterwards, too late. On re-render the buffer is truncated
to its earliest rows instead of its latest.

## Proposed fix
Clear the scrolling region before the top-clip in `resize()` (the region is about
to be reset for the new geometry anyway), so `delete_lines()` operates on the full
screen regardless of an active `DECSTBM`. Equivalently, drop the top rows without
routing through the margin-guarded `delete_lines()`.

## Related upstream
Read-only survey of `selectel/pyte`; nothing was filed (no upstream contact). No
issue or PR describes a resize/scroll-region interaction. [PR #210] is the
parser-crash class only and does not touch `resize()`.
