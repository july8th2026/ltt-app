# LTT-CMC literal cleanup ledger

Chụp ngày 12/09/2026 sau khi `main` PASS L3 và trở thành remote default.
Ledger này **chưa cho phép xóa**. Mọi dòng `YES_AFTER_APPROVAL` chỉ là đề nghị;
phải đo lại HEAD/status ngay trước thao tác. Không dùng xóa thư mục trực tiếp,
không `git gc`, không `git prune`.

## Chứng nhận cho phép đi tới checkpoint cleanup

- Canonical local/remote: `main` =
  `f14b3056f6dcc0a4f8c05c8dad755816cde9b44c`.
- L3: PASS 33/33, report `test-results/gates/20260912T155432Z-20964.json`,
  `cay_da_doi_giua_chung=false`.
- Remote default/`origin/HEAD`: `main`.
- Protection/rulesets: `NOT_AVAILABLE` trên gói private hiện tại; GitHub API
  trả thông điệp yêu cầu Pro hoặc public.
- Production: CMC không deploy và không phụ thuộc đường dẫn worktree nguồn;
  deploy Voice/LLM trước đó dùng quy trình release riêng được ghi trong handoff.

## Worktrees

| Đường dẫn tuyệt đối | Branch | HEAD | Status | Quan hệ với main | Xóa |
|---|---|---|---:|---|---|
| `D:/LTTSTUDIOSAPP` | `main` | `f14b3056` | sạch | canonical | **NO — KEEP** |
| `D:/LTTSTUDIOSAPP/.claude/worktrees/auto-scan-video-analysis-plan-752af9` | detached | `34b4626e` | sạch | ancestor | YES_AFTER_APPROVAL |
| `D:/LTTSTUDIOSAPP/.claude/worktrees/ltt-4bot-workflow-app-550cab` | detached | `81c6a03b` | sạch | Voice functional baseline + 3 docs ported | YES_AFTER_APPROVAL |
| `D:/LTTSTUDIOSAPP/.claude/worktrees/ltt-llm-api-http-guide-a3e123` | `claude/ltt-llm-multijob-audit-43efd3` | `b3b11dbc` | **dirty 5** | Source B supersedes từng tệp, patch-id `2d985f9c…` | YES_AFTER_APPROVAL, **chấp nhận mất WIP** |
| `D:/LTTSTUDIOSAPP/.claude/worktrees/ltt-video-architecture-recovery-746b24` | `cmc/llm-dual-reconcile` | `dd26ec44` | sạch | ancestor qua merge `c556c411` | YES_AFTER_APPROVAL |
| `D:/LTTSTUDIOSAPP/.claude/worktrees/ltt-voice-rc1-gate` | detached | `031ac4c` | sạch | ancestor, gate tree cũ | YES_AFTER_APPROVAL |
| `D:/LTTSTUDIOSAPP-aiclean` | `phien/aiclean` | `5d0df95e` | sạch | ancestor | YES_AFTER_APPROVAL |
| `D:/LTTSTUDIOSAPP-scheduler-v1` | `architecture/scheduler-priority-v1` | `34b4626e` | sạch | ancestor | YES_AFTER_APPROVAL |
| `D:/LTTSTUDIOSAPP-vps-v4` | `codex/vps-v4-infrastructure-profiles` | `3b5adcb7` | **dirty 31** | uncommitted VPS V4, ngoài CMC | **NO — HOLD_NEED_RECONCILIATION** |
| `D:/LTTSTUDIOSAPP-wf2` | `phien/wf2` | `0d1ffe5a` | sạch | ancestor | YES_AFTER_APPROVAL |
| `D:/LTTSTUDIOSAPP_RELEASE_H42` | `h42-release-clean` | `b4adf873` | sạch | patch-equivalent (0 plus/2 minus) | YES_AFTER_APPROVAL |

Dirty Source A gồm đúng:
`platform_core/job_runner.py`, `platform_core/llm/tham_so_da_luot.py`,
`platform_core/runtime_noi_bo/luong.py`, `server/api/chat.py`,
`server/api/streaming.py`. Dirty VPS V4 gồm 15 tracked và 16 untracked mục;
chi tiết phải được chụp lại trước cleanup, không ghi đè bằng stash/reset.

## Local branches

Mọi dòng dưới đây có đích xóa `YES_AFTER_APPROVAL`, trừ `main` và VPS V4 HOLD.
Phân loại semantic chi tiết nằm trong `RECONCILIATION.md`, `reconciliation.json`,
Voice `SO_CAI.json` và LLM `CMC_SOURCE_STATE.md`.

| Branch | HEAD | Disposition | Xóa |
|---|---|---|---|
| `main` | `f14b3056` | CANONICAL | **NO** |
| `codex/vps-v4-infrastructure-profiles` | `3b5adcb7` | HOLD_NEED_RECONCILIATION (dirty worktree) | **NO** |
| `cmc/llm-dual-reconcile` | `dd26ec44` | MERGED | YES_AFTER_APPROVAL |
| `phien/ltt-llm-dual` | `003f5dd6` | MERGED_SOURCE | YES_AFTER_APPROVAL |
| `claude/ltt-llm-multijob-audit-43efd3` | `b3b11dbc` | SUPERSEDED_DIRTY_SOURCE | YES_AFTER_APPROVAL, explicit dirty loss |
| `claude/ltt-llm-recovery-multimodel-110f65` | `d47d9fad` | PATCH_EQUIVALENT | YES_AFTER_APPROVAL |
| `claude/ltt-llm-master-upgrade-ddcfc9` | `2b3251ca` | SEMANTICALLY_INTEGRATED/SUPERSEDED | YES_AFTER_APPROVAL |
| `claude/ltt-video-architecture-recovery-746b24` | `7a654bb6` | VIDEO/WANGP HISTORY SUPERSEDED | YES_AFTER_APPROVAL |
| `claude/ltt-voice-reconciliation-165a40` | `81c6a03b` | FUNCTIONAL_BASELINE + DOCS_PORTED | YES_AFTER_APPROVAL |
| `admin-mvp-v3` | `34b4626e` | SUPERSEDED_TRUNK | YES_AFTER_APPROVAL |
| `master` | `9e73bf1f` | SUPERSEDED_TRUNK | YES_AFTER_APPROVAL |
| `architecture/scheduler-priority-v1` | `34b4626e` | ANCESTOR | YES_AFTER_APPROVAL |
| `claude/auto-scan-video-analysis-plan-752af9` | `9e73bf1f` | ANCESTOR | YES_AFTER_APPROVAL |
| `claude/chatltt-v3-agentic` | `139cb1d1` | ANCESTOR | YES_AFTER_APPROVAL |
| `claude/cool-pike-8be595` | `34b4626e` | ANCESTOR | YES_AFTER_APPROVAL |
| `claude/history-audio-storage-auth-4cffe3` | `dca96e84` | VOICE SEMANTICALLY_INTEGRATED | YES_AFTER_APPROVAL |
| `claude/ltt-4bot-workflow-app-550cab` | `b0e488a7` | VOICE SEMANTICALLY_INTEGRATED | YES_AFTER_APPROVAL |
| `claude/ltt-video-ai-v3-p00-3f5713` | `989353c2` | SUPERSEDED BY V2.1 | YES_AFTER_APPROVAL |
| `claude/ltt-voice-98-upgrade-9b586f` | `9d711828` | ANCESTOR | YES_AFTER_APPROVAL |
| `claude/ltt-voice-api-audit-7c8fee` | `9fba9fb1` | ANCESTOR | YES_AFTER_APPROVAL |
| `claude/ltt-voice-gui-mvp-ed62d6` | `65e099af` | VOICE SEMANTICALLY_INTEGRATED | YES_AFTER_APPROVAL |
| `claude/ltt-voice-inference-hardening-b1db43` | `99f199d4` | ANCESTOR | YES_AFTER_APPROVAL |
| `claude/ltt-voice-qa-ci-gate-1c85fb` | `a3a2a46e` | VOICE SEMANTICALLY_INTEGRATED | YES_AFTER_APPROVAL |
| `claude/ltt-vps-v2-deployment-plan-2cfc36` | `78ba1d50` | ANCESTOR | YES_AFTER_APPROVAL |
| `claude/my-voices-enrollment-prod-379a22` | `29ac2300` | VOICE SEMANTICALLY_INTEGRATED | YES_AFTER_APPROVAL |
| `claude/projects-longform-slice-ab2e77` | `ca6a00ce` | VOICE SEMANTICALLY_INTEGRATED | YES_AFTER_APPROVAL |
| `claude/studio-voice-picker-ui-6782bb` | `3634412a` | VOICE SEMANTICALLY_INTEGRATED | YES_AFTER_APPROVAL |
| `claude/voice-language-compatibility-440bfd` | `3100c317` | ANCESTOR | YES_AFTER_APPROVAL |
| `h42-release-clean` | `b4adf873` | PATCH_EQUIVALENT | YES_AFTER_APPROVAL |
| `phien/aiclean` | `5d0df95e` | ANCESTOR | YES_AFTER_APPROVAL |
| `phien/asv` | `706faca5` | ANCESTOR | YES_AFTER_APPROVAL |
| `phien/asv-v4` | `9d363fa9` | ANCESTOR | YES_AFTER_APPROVAL |
| `phien/asv-v6` | `694b8a4b` | ANCESTOR | YES_AFTER_APPROVAL |
| `phien/asv-v6-pha27` | `710aa7c1` | ANCESTOR | YES_AFTER_APPROVAL |
| `phien/mobile-v1` | `c43d7880` | ANCESTOR | YES_AFTER_APPROVAL |
| `phien/video-v2-wangp` | `f19b072d` | SUPERSEDED/UNSAFE GALLERY OPEN | YES_AFTER_APPROVAL |
| `phien/wf2` | `0d1ffe5a` | ANCESTOR | YES_AFTER_APPROVAL |

## Remote branches

Giữ `origin/main`. Các nhánh remote còn lại đều là đích
`YES_AFTER_APPROVAL`; không force-push, chỉ dùng tên literal với
`git push origin --delete` sau khi duyệt.

| Remote branch | HEAD | Disposition |
|---|---|---|
| `origin/main` | `f14b3056` | KEEP_CANONICAL |
| `origin/admin-mvp-v3` | `3100c317` | SUPERSEDED |
| `origin/master` | `9e73bf1f` | SUPERSEDED |
| `origin/claude/auto-scan-video-v4-mvp-7173d9` | `dc7f2553` | ANCESTOR |
| `origin/claude/ltt-llm-api-http-guide-a3e123` | `dac24060` | ANCESTOR |
| `origin/claude/ltt-llm-master-upgrade-ddcfc9` | `2b3251ca` | SEMANTICALLY_INTEGRATED/SUPERSEDED |
| `origin/claude/ltt-llm-multijob-audit-43efd3` | `b3b11dbc` | SUPERSEDED SOURCE |
| `origin/claude/ltt-llm-recovery-multimodel-110f65` | `d47d9fad` | PATCH_EQUIVALENT |
| `origin/claude/ltt-video-ai-v3-p00-3f5713` | `989353c2` | SUPERSEDED |
| `origin/claude/ltt-video-architecture-recovery-746b24` | `7a654bb6` | SUPERSEDED VIDEO/WANGP HISTORY |
| `origin/claude/ltt-voice-98-upgrade-9b586f` | `9d711828` | ANCESTOR |
| `origin/claude/ltt-voice-api-audit-7c8fee` | `9fba9fb1` | ANCESTOR |
| `origin/claude/ltt-voice-gui-mvp-ed62d6` | `65e099af` | VOICE SEMANTICALLY_INTEGRATED |
| `origin/claude/ltt-voice-inference-hardening-b1db43` | `4bd26f52` | ANCESTOR |
| `origin/claude/ltt-voice-reconciliation-165a40` | `81c6a03b` | FUNCTIONAL_BASELINE + DOCS_PORTED |
| `origin/h42-release-clean` | `b4adf873` | PATCH_EQUIVALENT |
| `origin/phien/aiclean` | `63768385` | ANCESTOR |
| `origin/phien/asv-v4` | `9d363fa9` | ANCESTOR |
| `origin/phien/asv-v6` | `694b8a4b` | ANCESTOR |
| `origin/phien/asv-v6-pha27` | `710aa7c1` | ANCESTOR |
| `origin/phien/ltt-llm-dual` | `c6503bb3` | ANCESTOR |
| `origin/phien/video-v2-wangp` | `f19b072d` | SUPERSEDED |

## Refs, backups, archives và session state

| Target | Verified/purpose | Xóa |
|---|---|---|
| tag `cmc-base-20260911` = `09b219a3` | temporary CMC barrier ref; canonical history now contains it | YES_AFTER_APPROVAL |
| `refs/cmc-rescue/*` | không tồn tại (0) | N/A |
| Git stash | rỗng (0) | N/A |
| `%TEMP%/ltt-cmc-final-20260912212918.{json,md}` | inventory tạm ngoài repo | YES_AFTER_APPROVAL |
| `%TEMP%/ltt-cmc-final-20260912213557.{json,md}` | inventory tạm ngoài repo | YES_AFTER_APPROVAL |
| `%TEMP%/ltt-cmc-final-authority-20260912225938.{json,md}` | inventory fresh sau chuyển remote authority | YES_AFTER_APPROVAL |
| `docs/ltt_llm_dual/artifacts/wip_task9_multijob.patch` | đã xóa trước certification theo quyết định không giữ bản sao | ALREADY_REMOVED |
| Claude chat sessions | người dùng xác nhận không còn phiên vận hành; không có official session-delete API trong phiên này | **NO BROAD FILESYSTEM DELETE** |

## Phán quyết dừng

Không thể đạt “chỉ một worktree” trong lượt cleanup hiện tại nếu chưa xử lý VPS
V4: xóa nó sẽ làm mất 31 mục WIP chưa đối soát. Khi người dùng duyệt ledger,
cleanup chỉ được xóa các dòng `YES_AFTER_APPROVAL`; dòng VPS V4 tiếp tục HOLD.
Sau khi VPS V4 được bàn giao/đối soát, phải tạo ledger mới cho chính nó.

**CHECKPOINT: STOP_BEFORE_DELETION.**
