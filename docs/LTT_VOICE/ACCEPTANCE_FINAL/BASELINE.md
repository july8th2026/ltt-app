# LTT Voice — Final Acceptance Baseline

Frozen: 2026-09-13 12:02 UTC+7

## Source

| Item | Value |
|---|---|
| Branch | `claude/ltt-voice-final-acceptance-deddff` |
| HEAD SHA | `429bc0cc48c3a93bcc6e666db29256323a539d7d` |
| Base (main) | `1e4dfdb6` (fix L-06/L-07) |
| Migration head | `a3f7c214e8b9` |

## Runtime

| Item | Value |
|---|---|
| Python | 3.13.12 |
| OS | Windows 10.0.19045 |
| GPU | Không có CUDA trên máy phát triển (worktree) |
| Sidecar VieNeu | `chua_bat` (worktree, không phải máy chủ) |

## Production (app.lttstudios.com)

| Endpoint | Status |
|---|---|
| `/health/ready` | 200 |
| `/` | 200 |
| `/vps` | 200 |
| `/gia-api` | 200 |
| `/developers` | 303 (redirect to login) |

## Public API Tools (khai trong manifest)

| Tool | Job type | kiem_truoc |
|---|---|---|
| `speech.ltt` | `ltt_voice.synthesize` | `apps.ltt_voice.kiem_truoc_api:kiem` |
| `image.ltt` | `anhnoibo.generate` | — |
| `video.subtitle` | `autosubvideo.render` | — |
| `text.chat` | `ltt_llm.chat` | — |
| `text.prompt_package` | `prompt_ai_ommi.generate` | — |
| `story.storyboard` | `prompt_ai_ommi.generate` | — |
| `image.generate` | `taoanh.generate` | — |
| `video.generate` | `taovideo.generate` | — |
| `image.thumbnail` | `thumbnail.generate` | — |
| `video.upscale` | `upscalevideo.render` | — |
| `image.upscale` | `upscalevideo.render` | — |

## Voice Constants (after D01–D03)

| Constant | Value |
|---|---|
| `TRAN_KY_TU_CONG_KHAI` | 100,000 |
| `TRAN_MOI_LUOT_SINH` | 1,500 |
| `SO_LAN_THU_JOB` | 5 |
| `TOC_DO_MIN` | 0.5 |
| `TOC_DO_MAX` | 2.0 |
| `CAC_NAC` (web) | (0.75, 0.85, 1.0, 1.15, 1.25, 1.5) |
| `CREDIT_GHI_DANH` | 2 |
| `PHIEN_BAN_GIA` | `ltt-voice-2026-08-30a` |

## Voice params_schema (Public API)

```json
{
  "text":     {"type": "string",  "required": true,  "max_length": 100000},
  "voice_id": {"type": "string",  "required": false, "max_length": 40, "exclusive_with": ["preset"]},
  "preset":   {"type": "string",  "required": false, "max_length": 64},
  "speed":    {"type": "number",  "required": false, "minimum": 0.5, "maximum": 2.0},
  "language": {"type": "string",  "required": false, "enum": ["auto", "vi", "en"]}
}
```

## Regression baseline

1120 voice tests passed, 0 failed, 3 skipped (commit `429bc0cc`).
