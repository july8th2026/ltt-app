# 07 — Roadmap sau Decision Gate

## Phase 0 — Security blocker

- Map mọi route Socialbot và áp operator authorization nhất quán.
- Test customer/anonymous/admin cho GET+POST; CSRF vẫn giữ.
- Khóa token/worker/monitor global chỉ operator; redaction log.
- **PASS:** G2, G4; không đổi token file và route OAuth.

## Phase 1 — Recovery/observability maintenance

- Correlation ID, actor/action audit, backup/restore rehearsal token store.
- Hard-fail production nếu encryption unavailable.
- **PASS:** G5/G8, operator canary Facebook/TikTok không publish thật.

## Phase 2 — UX operator tối thiểu

- Gắn nhãn “Nội bộ”, confirmation thao tác phá hủy, keyboard/focus/mobile.
- Không thêm approval/calendar/analytics.
- **PASS:** G6 baseline cho operator core journey.

## Phase 3–5

DEFER theo Q10. Chỉ chạy provider canary/production release khi người vận hành
cho phép dữ liệu/kênh test. Rollback: tắt route flag, hoàn commit authorization;
không rollback bằng cách phục hồi token mù.

