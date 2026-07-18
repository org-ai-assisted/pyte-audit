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

| ID | Defect | Class | Upstream status |
|----|--------|-------|-----------------|
| [A](reports/bug-A-extra-csi-params.md) | Extra CSI params -> `TypeError` out of `feed()` | DoS | **Reported** (open [#209] crash 3) |
| [B](reports/bug-B-private-kwarg.md) | Private `?` CSI -> `TypeError: ... 'private'` | DoS | **Reported** (open [#209] crash 1, [#126], [#67]) |
| [C](reports/bug-C-erase-unboundlocal.md) | `erase_in_line`/`erase_in_display` bad `how` -> `UnboundLocalError` | DoS | Partly ([#108] fixed `erase_in_display` args; CodeQL confirms) |
| [D](reports/bug-D-decom-no-margins.md) | VPA/DSR under DECOM w/o margins -> `AssertionError` | DoS | **Not found reported** (likely novel) |
| [E](reports/bug-E-resize-cursor-oob.md) | `resize()` smaller than cursor -> off-screen write, data loss | data integrity | **Not found reported** (likely novel) |
| [F](reports/bug-F-int-unicode-digit.md) | `int('superscript-digit')` in CSI param -> `ValueError` | DoS | **Reported** (open [#209] crash 2) |

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

A, B, F are already covered by open upstream issue [#209] ("Various parser
crashes on random input", whose reporter explicitly asked for a parser fuzzer).
C is partly addressed. **D and E appear to be new.** Upstream has **no AI
contribution policy** and is semi-active (last code commit 2025-09).

## Status

Draft. **No upstream communication has been made.** Proposed fixes are drafted
as branches on the `org-ai-assisted/pyte` fork.
