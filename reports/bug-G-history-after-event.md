# Bug G: `HistoryScreen.after_event` mutates a line dict while iterating it

**Class:** DoS (unhandled exception), broken invariant
**Affected:** upstream master `0.8.3.dev`, PR #210 head `98bd878`, Debian `0.8.0-3`
**Upstream fix:** none -- found by deeper fuzzing after PR #210; not addressed by any open upstream PR.
**Found by:** the direct-method fuzzer in this repo (paging a `HistoryScreen` after a column shrink).

## Repro
```python
import pyte
screen = pyte.HistoryScreen(10, 3, history=20)
stream = pyte.Stream(screen)
for _ in range(8):
    stream.feed("ABCDEFGHIJ\r\n")   # 10-wide lines scroll into history.top
screen.resize(lines=3, columns=4)    # shrink; captured history lines stay 10-wide
screen.prev_page()                   # page a wide line back in
```
`RuntimeError: dictionary changed size during iteration`

## Expected vs actual
- Expected: paging trims the over-width cells and continues; no crash.
- Actual: `RuntimeError` escapes `prev_page()` / `next_page()`.

## Root cause
`screens.py`, `HistoryScreen.after_event`:
```python
if event in ["prev_page", "next_page"]:
    for line in self.buffer.values():
        for x in line:              # iterating the dict...
            if x > self.columns:
                line.pop(x)          # ...while mutating it -> RuntimeError
```
`Screen.resize()` trims the *current* buffer but not the lines already captured
in `history.top` / `history.bottom`; when one of those wider lines is paged
back in, `after_event` tries to trim it and pops during iteration.

## Proposed fix
Iterate over a snapshot of the keys:
```python
for x in list(line):
    if x > self.columns:
        line.pop(x)
```

## Regression test
`tests/test_history_after_event.py` (org-ai-assisted/pyte fork,
branch `fix/history-after-event-mutation`).
