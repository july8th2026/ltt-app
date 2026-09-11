# Scheduler V1 — phối hợp các worktree đang tạm dừng

Chụp lúc 2026-09-10. Các phiên khác phải rebase/đối chiếu commit scheduler trước
khi làm tiếp; không chép từng hunk bằng tay nếu file nền đã đổi.

| Worktree/campaign | File đang giữ | Scheduler có chạm? | Việc cần làm khi tiếp tục |
|---|---|---:|---|
| `ltt-voice-api-audit` | `platform_core/public_api/invocation.py`, `registry.py`, Voice API template/manifest | Không | Rebase; không cần thêm priority vào `invocation.py`. `/api/v1` đã được đóng EXTERNAL tại middleware và route. |
| `ltt-voice-inference-hardening` | `apps/ltt_voice/routes/_p_tao.py` | Không | Rebase; web job tự nhận INTERNAL từ trusted request scope, không thêm tham số tại route. |
| `my-voices-enrollment-prod` | `_p_giong.py`, tables/lifecycle | Không | Rebase; không cần vá scheduler ở route. |
| `projects-longform-slice` | `_p_du_an.py`, `du_an.py` | Không | Rebase; không cần vá scheduler ở route. |
| `ltt-voice-gui-mvp` | nhiều route/template Voice | Không | Rebase; giữ nguyên submit call. Middleware phân loại web. |
| `studio-voice-picker-ui` | `server/static/ltt.css`, `voice.js` | Không | Rebase bình thường; scheduler không đổi asset. |
| `ltt-voice-qa-ci-gate` | `tools/gate.py`, browser/e2e tools | Không | Rà lại `tools/gate.py` khi rebase vì scheduler dựa gate canonical nhưng không sửa file này. |
| `asv-v6` và kế hoạch ASV | `apps/auto_scan_video/*` | Không | Rebase; job con sinh trong handler tự nhận INTERNAL từ worker scope. Bằng chứng ASV hiện có 7 assertion đỏ độc lập, cần chiến dịch ASV làm mới. |
| `wf2` | workflow/agent code | `platform_core/agent/runs.py` có thể giao nhau sau rebase | Giữ cặp `origin="agent", priority_class="internal"` ở `submit_child`; chạy lại test Agent. |
| `aiclean` | nhánh làm sạch nền tảng | Có khả năng giao `server/app.py`/core | Rebase sớm, giữ `JobIngressMiddleware` và hai field Job; không phục hồi queue/engine cũ. |

Trạng thái rà lại 2026-09-11:

- Trunk `3100c317` đã nhận bản sửa ký tự VT của Voice qua `9fba9fb1`.
- Bảy assertion E2E ASV đã có bản cập nhật trên nhánh `phien/asv-v6`
  (`710aa7c1`) nhưng chưa vào trunk; Scheduler không cherry-pick thay chủ.
- Test hook thiếu `sh` trên PATH vẫn chưa được sửa trên trunk.

Hai blocker còn lại **không nằm trong changeset Scheduler V1**. Phiên sở hữu
cần rà lại trên commit Scheduler hiện hành sau khi hợp nhất. Asset
`yolov8n.pt` chỉ được copy vào worktree để chạy gate; nó vẫn gitignored và
không nằm trong commit.

Rà lại sau khi phiên Auto Scan kết thúc: nhánh sạch tại `694b8a4b`, nhưng
trạng thái canonical vẫn ghi nhiều pha CHƯA/MỘT PHẦN và nhánh lệch trunk
42/56 commit. Hai commit tái sinh bằng chứng `28f6a8bf`/`710aa7c1` phụ thuộc
engine/QC trên chính nhánh ASV; không được chép riêng JSON sang Scheduler.
Đóng cửa sổ làm việc không phải là phán quyết sẵn sàng hợp nhất.
