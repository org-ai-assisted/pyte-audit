# pyte-audit

Independent fuzz/test audit of the [`pyte`][pyte] VTXXX terminal-emulator
library. Not affiliated with upstream. Holds concise defect reports and
runnable repros; the test + fuzz suite that found these lives in
[org-ai-assisted/dist-ai][distai] (`pyte-tests`).

[pyte]: https://github.com/selectel/pyte
[distai]: https://github.com/org-ai-assisted/dist-ai

## Method

A full public-API pytest suite + Hypothesis property tests + an in-process
Stream/ByteStream/Screen fuzzer were run against **both** upstream master
(`0.8.3.dev`, commit `0718fa8`) and Debian `python3-pyte` `0.8.0-3`, plus a
CodeQL `python-security-and-quality` pass. Every finding below reproduces on
both builds unless noted.

## Findings

| ID | Defect | Class | Upstream fix status |
|----|--------|-------|---------------------|
| [A](reports/bug-A-extra-csi-params.md) | Extra CSI params -> `TypeError` out of `feed()` | DoS | **Fix open: [PR #210]** (verified) |
| [B](reports/bug-B-private-kwarg.md) | Private `?` CSI -> `TypeError: ... 'private'` | DoS | **Fix open: [PR #210]** (verified) |
| [C](reports/bug-C-erase-unboundlocal.md) | `erase_in_line`/`erase_in_display` bad `how` -> `UnboundLocalError` | DoS | **Fix open: [PR #210]** (verified; identical `else: return`). Fork fix: [pyte#7] |
| [D](reports/bug-D-decom-no-margins.md) | VPA/DSR under DECOM w/o margins -> `AssertionError` | DoS | **No fix** ([PR #210] does NOT address it, verified) |
| [E](reports/bug-E-resize-cursor-oob.md) | `resize()` smaller than cursor -> off-screen write, data loss | data integrity | **No fix** (not a parser crash; untouched by [PR #210]) |
| [F](reports/bug-F-int-unicode-digit.md) | `int('superscript-digit')` in CSI param -> `ValueError` | DoS | **Fix open: [PR #210]** (verified) |
| [G](reports/bug-G-history-after-event.md) | `HistoryScreen.after_event` mutates a line dict mid-iteration -> `RuntimeError` | DoS | **No fix** (new; found after #210, verified) |

### Dedup against upstream (verified against the PR #210 head, commit `98bd878`)

Open **[PR #210] "Don't crash when consuming arbitrary random data"** (by
jonathanslenders, targeting issue [#209]) fixes the parser-crash class. Running
`repros/reproduce_all.py` against the PR #210 tree confirms it **resolves A, B,
C, and F** and **leaves D and E crashing**. So:

* **A, B, C, F** already have an open upstream fix -- do not duplicate.
* **D, E, and G** are not addressed by any open upstream PR and are the
  genuinely new findings here. **G** was found by fuzzing *against the PR #210
  tree* (parser crashes fixed), which let the fuzzer reach it; a 120k-round
  adversarial sweep with A-G filtered surfaced nothing further.

[PR #210]: https://github.com/selectel/pyte/pull/210
[pyte#7]: https://github.com/org-ai-assisted/pyte/pull/7
[#209]: https://github.com/selectel/pyte/issues/209
[#126]: https://github.com/selectel/pyte/issues/126
[#67]: https://github.com/selectel/pyte/issues/67
[#108]: https://github.com/selectel/pyte/pull/108

## Security assessment

pyte is a pure in-memory parser with no injection/eval/exec/path/deserialization
sinks and no native code, so there is **no RCE or info-leak surface**. The
relevant class is **denial of service**: A-D and F are unhandled exceptions that
escape `Stream.feed()` and crash the hosting application on untrusted terminal
output (`cat` any binary file, as [#209] notes). **E** is a data-integrity bug
(silent loss of drawn text). CodeQL independently flagged the C uninitialised
variable; its other findings (a `TYPE_CHECKING`-only "cyclic import", an
intentional empty `except`, an `__init__`-calls-overridden-`reset` smell) were
reviewed and are not defects.

## Novelty

A, B, C, F are fixed by open upstream [PR #210] (verified). **D and E are new**
-- no open upstream PR addresses them. Upstream has **no AI contribution
policy** and is semi-active (last code commit 2025-09).

## Status

Draft. **No upstream communication has been made.** Proposed fixes are drafted
as branches on the `org-ai-assisted/pyte` fork (D and E as draft PRs); the
parser-crash fix is superseded by upstream [PR #210] and is not for upstream
submission.
