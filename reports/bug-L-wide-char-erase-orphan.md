# Bug L: erasing or deleting a wide-character head orphans the stub -- crash on released builds, short row on the git tip

**Class:** DoS on released builds / rendering correctness on the git tip (a `display`
row no longer represents exactly `columns` on-screen cells).
**Affected (version-dependent, both verified by runtime repro):**
- Released builds -- Debian `python3-pyte` `0.8.0-3` and PyPI `0.8.2`: `render()`
  computes `wcwidth(char[0])`, which **indexes into the cell string first**; on the
  empty-data orphan stub (`char == ""`) that raises `IndexError: string index out of
  range`, escaping `Screen.display` -- a crash (DoS), not a silent no-op.
- Upstream git tip `0718fa8` and the org-ai-assisted/pyte fork (based on it):
  `render()` was rewritten to `wcswidth(char)` (no indexing), so the empty stub
  contributes 0 width instead of crashing and the rendered row is silently **shorter
  than `columns`**. The fork does not modify `erase_characters()` /
  `delete_characters()`.
**Upstream fix:** none. [PR #210](https://github.com/selectel/pyte/pull/210) fixes
only the parser-crash class and touches neither the erase/delete handlers nor
`render()`. (The tip's `render()` change to `wcswidth` is incidental -- it converts
the crash into a short row, it does not fix the orphaned stub.)
**Fork fix:** none -- tracked as a strict-xfail regression test in
org-ai-assisted/dist-ai (`pyte-tests`, which runs only against the 0.8.3+ API where
the manifestation is the short row); the pyte source is kept pristine.
**Upstream:** no issue or PR describes it -- **likely novel**.

## Repro
`\u30b3` is KATAKANA LETTER KO (U+30B3), a width-2 CJK character occupying two cells.
```python
import pyte
# via CSI X (erase character):
s = pyte.Screen(5, 2)
st = pyte.Stream(s)
st.feed("a\u30b3b")          # 'a' + wide char (2 cells) + 'b'
st.feed("\x1b[1;2H")         # cursor onto the wide char's head cell (0-based x=1)
st.feed("\x1b[X")            # erase 1 char -- erases only the head
print(repr(s.display[0]), len(s.display[0]))
# released 0.8.0-3 / 0.8.2 : IndexError: string index out of range
# git tip 0718fa8 / fork   : 'a b ' 4   -- one column short of columns == 5

# via CSI P (delete character), same root cause:
s = pyte.Screen(5, 2)
s.draw('a'); s.draw('\u30b3'); s.draw('b')
s.cursor_position(1, 2)      # at the wide char's head
s.delete_characters(1)
print(repr(s.display[0]), len(s.display[0]))
# released : IndexError ; git tip/fork : 'ab  ' 4  -- one column short
```

## Expected vs actual
- Expected: after erasing/deleting one half of a wide character the row still
  represents `columns` on-screen cells (`len(display[row]) == columns`, no crash); a
  real terminal shows a blank where the pair used to be.
- Actual: released builds raise `IndexError` out of `Screen.display`; the git tip and
  fork return a row one character short of `columns`.

## Root cause
`erase_characters()` and `delete_characters()` operate cell-by-cell and do not check
whether a touched cell is the head or the stub (`data == ""`) of a paired wide
character. Erasing/shifting only the head leaves a lone `data == ""` orphan stub with
no width-2 head before it. `render()` then trips over that empty string:
- Released (`pyte/screens.py`, `render()`): `char = line[x].data; assert
  sum(map(wcwidth, char[1:])) == 0; is_wide_char = wcwidth(char[0]) == 2` -- `char[0]`
  on `""` raises `IndexError`.
- Git tip: `char_width = wcswidth(char)` -- `wcswidth("")` is `0`, so no crash, but the
  stub yields the empty string and the joined row is shorter than `columns`.

## Proposed fix
When erase/delete touches a wide-char head or its stub, normalize the pair: replace an
orphaned stub with a blank (`data == " "`) cell so it occupies its one on-screen column.
The row then keeps exactly `columns` cells and no empty-data cell ever reaches
`render()` -- fixing both the crash and the short-row manifestations at the source.

## Related upstream
Read-only survey of `selectel/pyte`; nothing was filed (no upstream contact).
Related but distinct: [#55](https://github.com/selectel/pyte/issues/55) /
[#9](https://github.com/selectel/pyte/issues/9) concern wide-char cursor/line-end
placement, not erase/delete orphaning a stub. [PR #210] is the parser-crash class only
and does not touch the erase/delete handlers or `render()`.
