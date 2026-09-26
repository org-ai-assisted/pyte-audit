# Bug L: erasing or deleting the head of a wide character orphans the stub and shortens the rendered row

**Class:** rendering correctness (a `display` row no longer represents exactly
`columns` on-screen cells)
**Affected:** upstream master `0.8.3.dev` (`0718fa8`) and the org-ai-assisted/pyte
fork tip (verified by runtime repro on the upstream mirror; the fork does not
modify `erase_characters()` or `delete_characters()`).
**Upstream fix:** none. [PR #210](https://github.com/selectel/pyte/pull/210) fixes
only the parser-crash class and does not touch the erase/delete handlers.
**Fork fix:** none -- tracked as a strict-xfail regression test in
org-ai-assisted/dist-ai (`pyte-tests`); the pyte source is kept pristine.
**Upstream:** no issue or PR describes it -- **likely novel**.

## Repro
`\u30b3` is KATAKANA LETTER KO, a width-2 CJK character occupying two cells.
```python
import pyte
# via CSI X (erase character):
s = pyte.Screen(5, 2)
st = pyte.Stream(s)
st.feed("a\u30b3b")          # 'a' + wide char (2 cells) + 'b' = 4 cells used
st.feed("\x1b[1;2H")         # cursor onto the wide char's head cell (0-based x=1)
st.feed("\x1b[X")            # erase 1 char -- erases only the head
print(repr(s.display[0]), len(s.display[0]))   # 'a b ' 4  -- but columns == 5

# via CSI P (delete character), same root cause:
s = pyte.Screen(5, 2)
s.draw('a'); s.draw('\u30b3'); s.draw('b')
s.cursor_position(1, 2)      # at the wide char's head
s.delete_characters(1)
print(repr(s.display[0]), len(s.display[0]))   # 'ab  ' 4  -- but columns == 5
```

## Expected vs actual
- Expected: after erasing/deleting one half of a wide character the row still
  represents `columns` on-screen cells (`len(display[row]) == columns`); a real
  terminal shows a blank where the pair used to be.
- Actual: the joined row is one character short of `columns`, even though no
  genuine width-2 character remains in it.

## Root cause
`erase_characters()` and `delete_characters()` operate cell-by-cell and do not
check whether a touched cell is the head or the stub (`data == ""`) of a paired
wide character. Erasing/shifting only the head leaves a lone `data == ""` stub with
no width-2 head before it. In `display`, `render()` decides how many characters a
cell contributes from `wcswidth(char)` computed at render time; an orphan stub's
`data` is `""`, whose `wcswidth` is `0`, so it contributes nothing (not even a
blank). The joined row is then shorter than `self.columns`, violating the invariant
that each `display` row is exactly `columns` on-screen cells wide.

## Proposed fix
When erase/delete touches a wide-char head or its stub, normalize the pair: replace
an orphaned stub with a blank (`data == " "`) cell so it occupies its one on-screen
column, keeping the row exactly `columns` cells wide.

## Related upstream
Read-only survey of `selectel/pyte`; nothing was filed (no upstream contact).
Related but distinct: [#55](https://github.com/selectel/pyte/issues/55) /
[#9](https://github.com/selectel/pyte/issues/9) concern wide-char cursor/line-end
placement, not erase/delete orphaning a stub. [PR #210] is the parser-crash class
only and does not touch the erase/delete handlers.
