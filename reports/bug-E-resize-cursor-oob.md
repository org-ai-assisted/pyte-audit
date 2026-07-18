# Bug E: `resize()` to a smaller screen leaves the cursor out of bounds (data loss)

**Class:** data integrity (silent loss), broken invariant
**Affected:** upstream master `0.8.3.dev`, Debian `0.8.0-3`
**Upstream:** no matching report found - **likely novel** (distinct from the
resize-resets-cursor issues [#95]/[#17]/[#18], which are the opposite complaint).

## Repro
```python
import pyte
s = pyte.Screen(1, 10)
s.cursor_position(9, 1)          # y = 8
s.resize(lines=1, columns=1)
print(s.cursor.y, s.lines)       # 8 1  -> cursor below the screen
s.draw("X")
print(s.display)                 # [' ']  -> 'X' written off-screen and lost
print(8 in s.buffer)             # True  -> leaked onto hidden row 8
```
The column axis fails identically (`resize(columns=...)` does not clamp `cursor.x`).

## Expected vs actual
- Expected: after resize the cursor is clamped into the new bounds; later output
  is visible.
- Actual: the cursor keeps its old coordinates; subsequent `draw()` lands on an
  off-screen buffer cell and never appears in `display`.

## Root cause
In `resize()`, `restore_cursor()` runs `ensure_vbounds()` / `ensure_hbounds()`
while `self.lines` / `self.columns` still hold the OLD geometry; the new values
are assigned afterward, and the column-shrink path never re-clamps at all.

## Proposed fix
Clamp after applying the new geometry:
```python
self.lines, self.columns = lines, columns
self.ensure_hbounds()
self.ensure_vbounds()
self.set_margins()
```

[#95]: https://github.com/selectel/pyte/issues/95
[#17]: https://github.com/selectel/pyte/pull/17
[#18]: https://github.com/selectel/pyte/pull/18
