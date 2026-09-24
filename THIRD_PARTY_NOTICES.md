# Third-Party Notices — LTT Nexus

LTT Nexus distributes and operates third-party software. This file lists that
software, its license, and where to obtain its Corresponding Source, as required
by those licenses.

> Decision context: **Q100 supersedes Q97 — Rổ 2**. The RustDesk **client** will
> be a **modified fork** (LTT branding, embedded config, custom session
> indicator, LTT login flow). Under AGPL-3.0 §13 this triggers the duty to
> publish the modified fork's Corresponding Source to users who interact with it
> over a network. The **server** (hbbs/hbbr) stays **unmodified**, so §13 does
> not apply to it. See the two components below.
>
> **Status:** the fork is not built yet (`docs/nexus/N3_2_FORK.md`). Before any
> client is distributed, the "RustDesk client" entry below MUST be updated to
> point at LTT's public fork repository and carry a written offer of source.

---

## RustDesk (remote-control engine)

- **Component:** `rustdesk/rustdesk` — the client/engine that captures the
  screen, receives input, negotiates NAT traversal, and transports the session.
- **License:** GNU Affero General Public License v3.0 (AGPL-3.0).
- **Version / commit:** `1.4.9` (2026-07-06), commit
  `6c578292e8ebbbec708b76986ba8c4bc7c509747`.
- **Source:** https://github.com/rustdesk/rustdesk (pinned at the commit above).
- **Modifications by LTT:** **planned (Rổ 2, Q100).** LTT will publish a modified
  fork of the client (branding, embedded server config, custom session
  indicator, LTT login flow). The fork's Corresponding Source will be public and
  linked here before any client binary is distributed. Until then no modified
  client is shipped. Every change is tracked as a separate commit on the public
  fork (OSS_BOUNDARY rule 6). The proprietary **LTT Nexus Agent** is a separate
  process communicating only over a local IPC/command-line contract and is not a
  derivative of RustDesk.

## RustDesk Server — hbbs / hbbr (rendezvous + relay)

- **Component:** `rustdesk/rustdesk-server` — the self-hosted rendezvous (hbbs)
  and relay (hbbr) that LTT runs on its own infrastructure.
- **License:** AGPL-3.0.
- **Version / commit:** `1.1.16` (2026-07-20), commit
  `73523b31cfd25d77dee862e6fc9f5e1fb5e485ef`.
- **Source:** https://github.com/rustdesk/rustdesk-server (pinned at the commit
  above).
- **Modifications by LTT:** **none.** Run unmodified; §13 is therefore not
  triggered for the server either.

---

## Full license text

The complete AGPL-3.0 license text applies to both components above and is
available at:

- https://www.gnu.org/licenses/agpl-3.0.txt
- and in the `LICENCE` file inside each RustDesk repository at the pinned commit.

## Obtaining the source

For each component, the Corresponding Source is the upstream repository at the
exact commit listed above. Because LTT distributes these components **unmodified**,
the Corresponding Source is the upstream source itself — no LTT-specific patches
exist to publish. Anyone who receives an LTT Nexus binary that includes these
components may obtain the source from the URLs above.

## Not covered here

- **Transitive dependencies** of RustDesk (Rust crates, Flutter libraries) are
  **not yet inventoried** (`docs/nexus/03_OSS_LICENSE.md` §2, §6 item 4). Some
  may carry other licenses. This must be completed before commercial release;
  it is recorded as *not done*, not as *no issue*.
- The **LTT Nexus Agent** and control plane are LTT's own proprietary software,
  are not derived from RustDesk, run in a separate process communicating only
  over a local IPC contract, and are not covered by this notice.

---

# Measurement / build-time dependencies (NOT distributed)

These are used by LTT's **quality gates and benchmarks** (`tools/do_luong.py`).
They run on LTT's own machines and are **not shipped to users**, so no
distribution obligation attaches. They are listed because the project rule of
2026-09-24 — *measurement tools must be researched, downloaded and reused, never
hand-written* — makes them load-bearing for published numbers.

## pyannote.metrics (speech segmentation / detection metrics)

- **Component:** `pyannote.metrics` — boundary-tolerance segmentation metrics
  (`SegmentationPrecision` / `SegmentationRecall`, `tolerance=` in seconds) and
  speech-detection metrics with a `collar`. Used for the B1 segmentation gate
  (*boundary accuracy +/-0,3 s*) in place of LTT's hand-written metric.
- **Version:** `4.1` (installed 2026-09-24).
- **License:** **MIT** - Copyright (c) 2014 CNRS (Herve Bredin). Verified from
  the LICENSE file shipped inside the installed wheel
  (`pyannote_metrics-4.1.dist-info/licenses/LICENSE`), which matches the
  repository LICENSE:
  https://github.com/pyannote/pyannote-metrics/blob/main/LICENSE
- **Metadata gap, recorded as a gap, not as "no issue":** the PyPI package
  carries **no** `License` field and **no** license classifier. The MIT
  determination therefore rests on the LICENSE file (wheel + repo), not on
  package metadata.
- **Code license is not model license.** This is the **metrics** package: it
  ships no model weights and loads none. The non-commercial / gated concerns in
  the pyannote ecosystem attach to `pyannote.audio` **model weights** on Hugging
  Face, which LTT does **not** install or use here.
- **Transitive dependencies pulled in:** `pandas` 3.0.6, `pyannote-core` 6.0.1,
  `pyannote-database` 6.1.1 (both MIT). `numpy`, `scikit-learn`, `scipy` were
  already present. **No `torch`, no `pyannote.audio`** - confirmed from
  `install_requires` and from the install log. (`torch` exists on this machine
  from unrelated work; `pyannote.metrics` did not pull it.) `sympy`,
  `matplotlib`, `docopt`, `tabulate` are **extras only** (`[cli]`, `[plot]`,
  `[doc]`) and are not installed.
- **Modifications by LTT:** none. Used unmodified as a library.

### Definition borrowed, not just the runtime

`sed_eval` (MIT, https://github.com/TUT-ARG/sed_eval/blob/master/LICENSE.txt)
defines the onset/offset tolerance rule LTT falls back on when a timeline has
silence gaps. LTT does **not install** `sed_eval` - it drags in `dcase_util`,
`librosa`, `matplotlib`, `soundfile` and more. Only the **definition** is
borrowed and re-implemented over `scipy`. Borrowing a spec is cheap; borrowing a
runtime is not.

## WhisperX — sentence-splitting rule (Auto Scan Video)

* **Component:** `apps/auto_scan_video/cat_doan.py` (`KET_CAU`, `DAU_DONG`,
  `CHU_SO`, `_ket_cau()`)
* **Upstream:** https://github.com/m-bain/whisperX — **PR #1466**
  *"Split Chinese and Japanese into sentences during alignment"*, which adds
  `CJKSentenceSplitter` to `whisperx/utils.py`. PR #1466 closes **issue #1310**.
* **License:** **BSD-2-Clause** (`whisperx-3.8.6.dist-info/METADATA`,
  `License: BSD-2-Clause`; author Max Bain)
* **What LTT uses:** the *rule* — the CJK sentence-terminator set, the closing
  bracket set, and the three qualifications in `_ends_sentence` (half-width `.`
  only ends a sentence before whitespace; full-width `．` is not a terminator
  between digits; `!`/`?` are not terminators after an ASCII alphanumeric).
  Re-expressed in LTT's own code; **not** a vendored copy of the module.
* **Why not the shipped module:** whisperx 3.8.6 already ships
  `whisperx/SubtitlesProcessor.py`, but when a run of text exceeds
  `max_line_length` it splits at the **midpoint**
  (`midpoint = normal_round((last_split_point + i) / 2)`) — a mid-sentence cut,
  which is forbidden for the dubbing product. See `docs/auto_scan_video_final/
  B1_CHEP_LOI.md` §7.4.

> ⚠️ PR #1466 was **open** upstream when this was written (24/09/2026). If it
> merges, re-check whether `whisperx.utils.CJKSentenceSplitter` can be imported
> directly instead — **reuse beats re-expressing**.

### `initial_prompt` for Chinese/Japanese

`apps/autosubvideo/whisperx_runner.py` and `apps/autosubvideo/transcription.py`
set `initial_prompt` for `zh`/`ja`. Source: whisperX **issue #645**
*"No punctuation for Chinese"*, comment by `leexinxu` (2024-08-17). This is a
usage pattern, not copied code.

### Subtitle timing constants

The thresholds in `cat_doan.py` (`KHE_TOI_DA_S`, `KHE_TOI_THIEU_S`,
`KY_TU_MOI_DONG`, `KY_TU_MOI_GIAY`) are quoted from the **Netflix Timed Text
Style Guide**, a published specification, with the article number recorded next
to each constant in the source:

| constant | article |
|---|---|
| max 7 s / min 5⁄6 s per subtitle event | *General Requirements*, **215758617** |
| 16 characters per line, max 2 lines, 9 characters/second | *Chinese (Simplified)*, **215986007** |

⚠️ Article **215346638** is the *Russian* guide (42 chars/line, 17 cps) — verify
the page title before quoting.
