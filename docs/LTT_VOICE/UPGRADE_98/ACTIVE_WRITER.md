# ACTIVE_WRITER — ai đang ghi vào cây này

Một tệp, một chủ. Phiên nào định sửa `apps/ltt_voice/` hay `voice_sidecar/`
phải đọc tệp này TRƯỚC.

## Phiên đang giữ

| trường | giá trị |
|---|---|
| chương trình | LTT VOICE 98+ — AUTONOMOUS DEEP UPGRADE |
| cây làm việc | `D:\LTTSTUDIOSAPP\.claude\worktrees\auto-scan-video-v4-mvp-7173d9` |
| nhánh | `claude/ltt-voice-98-upgrade-9b586f` |
| SHA lúc bắt đầu | `990179106f7e80a554f28c41c4745488fb17bbd8` |
| nhánh đích hợp nhất | `admin-mvp-v3` (cùng SHA lúc bắt đầu) |
| bắt đầu | 2026-09-09 13:37 +0700 |
| trạng thái | WAVE A đã ghi mã — P1..P7 + B-06, gate đầy đủ đã chạy 09/09 21:27Z |

## Phạm vi WRITE mà phiên này nhận

```
apps/ltt_voice/**
voice_sidecar/**
tests/test_5xx_*voice*  tests/test_3xx_*voice*
tools/*voice*  tools/*giong*
docs/LTT_VOICE/UPGRADE_98/**
server/static/voice.js
```

## Phạm vi phiên này KHÔNG đụng

`platform_core/**` và `server/**` — trừ khi một hạng mục chứng minh được
buộc phải sửa nền tảng, và khi đó phải dừng lại nói rõ vì sao (CLAUDE.md luật 20).

## Cây khác đang sống lúc bắt đầu

Đo bằng `git worktree list` lúc 13:36 +0700 ngày 09/09/2026:

| cây | nhánh | SHA |
|---|---|---|
| `D:\LTTSTUDIOSAPP` | `admin-mvp-v3` | `99017910` |
| `.claude/worktrees/chatltt-v3-agentic` | `claude/chatltt-v3-agentic` | `139cb1d1` |
| `.claude/worktrees/ltt-llm-api-http-guide-a3e123` | `claude/ltt-llm-master-upgrade-ddcfc9` | `99017910` |
| `.claude/worktrees/video-v2-wangp` | `phien/video-v2-wangp` | `f19b072d` |
| `D:\LTTSTUDIOSAPP-aiclean` | `phien/aiclean` | `3bcd580f` |
| `D:\LTTSTUDIOSAPP-wf2` | `phien/wf2` | `0d1ffe5a` |
| `D:\LTTSTUDIOSAPP_RELEASE_H42` | `h42-release-clean` | `b4adf873` |

⚠️ Bảy cây dùng CHUNG một `.git`. Commit vào nhánh dùng chung là **đã xuất bản**.
Không `--amend`, không `reset --hard`, không `stash` trần.

⚠️ Danh sách trên là **ảnh chụp lúc hỏi**. Nó chứng minh có cây tồn tại; nó
KHÔNG chứng minh cây nào đang có phiên sống. Trước lệnh nặng vẫn phải chạy
`python tools\cua_so_yen.py trang-thai` và nhìn cây tiến trình.
