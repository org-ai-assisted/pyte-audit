# Bug I: no SU / SD (`CSI S` / `CSI T`) -- scroll-region scrolls are silently dropped

**Class:** rendering correctness (stale rows; a program's scroll is a no-op)
**Affected:** Debian `python3-pyte` `0.8.0-3` (verified); upstream master (S/T are
absent from `Stream.csi` and `Screen` has no `scroll_up`/`scroll_down`, and
[PR #210](https://github.com/selectel/pyte/pull/210) touches only the parser-crash class).
**Upstream fix:** none. Neither SU nor SD is implemented.
**Fork fix:** carried in the `secure-terminal` emulator (a `HistoryScreen` subclass adds
`scroll_up`/`scroll_down` and a `CSI S`/`CSI T` dispatch) rather than in the pyte fork,
because a complete fix is blocked by the parser limitation in [Root cause](#root-cause).
**Reference terminal:** ECMA-48 SU/SD, as implemented by **xterm** -- see
[Reference behaviour](#reference-behaviour).
**Upstream:** no issue or PR implements SU/SD -- **likely novel** (feature gap, not a crash,
so the crash-oriented fuzzers and PR #210 never reach it). See [Related upstream](#related-upstream).

## Repro
```python
import pyte
print("S" in pyte.Stream.csi, "T" in pyte.Stream.csi)                 # False False
print(hasattr(pyte.Screen, "scroll_up"), hasattr(pyte.Screen, "scroll_down"))  # False False

s = pyte.Screen(5, 4)
st = pyte.Stream(s)
st.feed("AAAAA\r\nBBBBB\r\nCCCCC\r\nDDDDD")
st.feed("\x1b[T")            # SD 1: scroll the screen DOWN one line
print(s.display)             # ['AAAAA', 'BBBBB', 'CCCCC', 'DDDDD']  -- UNCHANGED (no-op)
```
`CSI S` (SU) is dropped identically. A `DECSTBM` scroll region does not help -- pyte still
has no handler for the final bytes `S`/`T`, so the sequence is an undispatched no-op.

## Reference behaviour
xterm (and every ECMA-48 terminal) implements:
- **SU** -- `CSI Ps S` -- scroll the scroll region UP `Ps` lines; the top `Ps` lines are
  lost, `Ps` blank lines appear at the bottom. Cursor position unchanged.
- **SD** -- `CSI Ps T` -- scroll the scroll region DOWN `Ps` lines; the bottom `Ps` lines
  are lost, `Ps` blank lines appear at the top. Cursor position unchanged.

Feeding the repro above to xterm and probing with `ESC[6n` shows the grid scrolled and the
cursor unmoved; pyte leaves the grid untouched.

## Expected vs actual
- Expected (xterm): after `CSI T` the display is `['     ', 'AAAAA', 'BBBBB', 'CCCCC']`.
- Actual (pyte): `['AAAAA', 'BBBBB', 'CCCCC', 'DDDDD']` -- the scroll never happened.

## Impact
A full-screen program that opens space by setting a `DECSTBM` region and issuing `SD` (an
editor's paste/insert redraw does exactly this) has the scroll silently dropped: it then
writes the inserted lines over the un-scrolled old content, leaving stale characters and
losing the row that should have moved off. In the `secure-terminal` emulator this surfaced
as GNU nano corrupting the buffer on a multi-line paste (stale line tails; a lost trailing
line), and as a doubled-line appearance in an Ink-based full-screen TUI. It is a rendering
defect, not a crash and not a security issue (pyte is a pure in-memory model with no
injection/exec sink; moving already-modelled rows introduces no new sink -- consistent with
the audit's overall Security assessment).

## Root cause
Two layers:

1. **No handler.** `Stream.csi` has no entry for `S` or `T`, and `Screen` defines neither
   `scroll_up` nor `scroll_down`, so the final byte is undispatched (a silent no-op).

2. **The parser discards the disambiguating intermediates**, so even a downstream that
   *adds* an `S`/`T` -> `scroll_up`/`scroll_down` mapping cannot dispatch correctly. Several
   distinct sequences share the `S`/`T` final byte and are told apart only by a private (`?`)
   marker or an intermediate byte (`>` or SP):
   - `CSI ? Pi;Pa;Pv S` -- **XTSMGRAPHICS** (sixel/ReGIS graphics query) -- must NOT scroll.
   - `CSI f;x;y;r;c T` (5 params) -- **XTHIMOUSE** (initiate highlight mouse tracking) -- must NOT scroll.
   - `CSI > Ps T` -- **XTRMTITLE** (reset title modes) -- must NOT scroll.
   - `CSI Ps SP T` -- **DECSWBV** (set warning bell volume) -- must NOT scroll.

   The parser tracks `private` (so `?`-forms can be rejected) and the parameter list (so the
   5-parameter XTHIMOUSE can be rejected), but it **drops `>` and SP entirely**:
   ```python
   # pyte/streams.py, Stream._parser_fsm, CSI branch
   elif char in SP_OR_GT:      # SP_OR_GT = ctrl.SP + ">"
       pass                    # "Secondary DA is not supported atm."
   ```
   So `CSI > 0 T` (XTRMTITLE) and `CSI 1 SP T` (DECSWBV) arrive at the handler
   indistinguishable from a plain single-parameter `CSI 0 T` / `CSI 1 T` (SD). A correct
   SU/SD therefore cannot be implemented purely at the `Screen`/`csi`-mapping layer; the
   parser must surface the intermediate.

## Proposed fix
1. Add margin-aware, cursor-independent `scroll_up` / `scroll_down` to `Screen` (SD is
   `insert_lines`-shaped anchored at the region top; SU is `delete_lines`-shaped -- both
   without the cursor move / carriage return those perform), and map them in `Stream.csi`:
   `esc.SU = "S"`, `esc.SD = "T"`.
2. Record the CSI intermediate in the parser instead of discarding it (`elif char in
   SP_OR_GT: intermediate = char` rather than `pass`) and pass it to the dispatch, so `S`/`T`
   dispatch only for the plain (non-private, no-intermediate, <=1-parameter) form and the
   XTSMGRAPHICS / XTHIMOUSE / XTRMTITLE / DECSWBV collisions fall through untouched.

The `secure-terminal` fork implements step 1 in its `HistoryScreen` subclass and guards the
private + multi-parameter collisions at the handler; the `> `/SP single-parameter residual
is the part that needs step 2 in pyte's own parser.

## Related upstream
Read-only survey of `selectel/pyte`; nothing was filed (no upstream contact).
- [PR #210](https://github.com/selectel/pyte/pull/210) / [#209](https://github.com/selectel/pyte/issues/209)
  fix the parser-crash class only; they neither add SU/SD nor change intermediate handling.
- The `SP_OR_GT: pass` line is long-standing ("Secondary DA is not supported atm."); no issue
  tracks its side effect on other intermediate-bearing CSIs.
