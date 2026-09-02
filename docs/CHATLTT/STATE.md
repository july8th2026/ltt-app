# CHATLTT (H43) — STATE

> SSOT bàn giao giữa các phase của chương trình `LTTCHAT_AUTONOMOUS_DEEP_BUILD_V2`.
> Chỉ chứa **sự thật hiện tại**. Bằng chứng chi tiết ở `reports/`. Kế hoạch ở
> `00_PHUONG_AN_VA_LO_TRINH.md`. Máy đọc: `state.json`.

## Program identity
- Gói: `G:\My Drive\AI\A LTT AII\LTTCHAT_AUTONOMOUS_DEEP_BUILD_V2` (14 prompt 00→13)
- Cây: `D:\LTTSTUDIOSAPP\.claude\worktrees\lttchat-autonomous-build-plan-1cf29d`
- Nhánh: `claude/lttchat-autonomous-build-plan-1cf29d`
- Gốc: `admin-mvp-v3` @ `dac2406` (= `origin/admin-mvp-v3`). ⚠️ Cây này lúc tạo
  đứng ở `master` (`dc7f255`, thua 497 commit) — đã `merge --ff-only`, không reset.
- Dải số test: **600–699**
- Production: `89eb46c` (14:15 02/09) + voice (21:11 02/09), 5 tool bán thật.
  ⛔ Chương trình này **không deploy**.
- Phase hiện tại: **00 ✅ → tiếp 01**

## Ranh giới với phiên khác (02/09)
| Phiên | Trạng thái | Vùng giữ |
|---|---|---|
| `ltt-voice-autonomous-supervisor` | xong, cây sạch | — (đã rời `apps/ltt_voice`, `voice.js`, `ltt.css`) |
| `lttstudiosapp-7d` (Purification V1) | đóng, đã push | — |
| `lttstudiosapp-dc` (Auto Scan Video, `phien/asv`) | **đã dừng** | `apps/auto_scan_video/`, `apps/asv_*`, `tests/test_4xx_asv_*`, `docs/auto_scan_video/` |

Ràng buộc nhận: giữ chữ ký `platform_core/llm/dieu_phoi.goi(...)`; khai `bang_gia`
trong manifest; không `pytest -n auto` tay; `git add` tường minh.

## Phase đã đóng
| Phase | Kết quả | Commit |
|---|---|---|
| **00** Bootstrap + nguồn chân lý | PASS — một cây/một gốc SHA, không rủi ro đè mã mới; runtime map + quyết định đã khảo sát | (commit kế hoạch) |

## Quyết định đã chốt (D1–D12 trong §4 kế hoạch)
| ID | Tóm tắt |
|---|---|
| D1 | app mới `apps/chatltt/`, không sửa `chataistudio` |
| D3 | cửa nội bộ = facade mỏng `platform_core/runtime_noi_bo/`; `server/api/streaming.py` gọi lại nó |
| D4 | bảng riêng `chatltt_*` dạng cây (chấm lại ở Phase 07) |
| D5 | React island `frontend/chatltt` |
| D7 | `response.started` + heartbeat ngay sau admission |
| D8 | allowlist `{text.chat, image.ltt, speech.ltt}` fail-closed |
| D12 | đóng mâu thuẫn Q116↔`ngan_sach.py` ở Phase 03 bằng số đo |

## Chặn ngoài đang mở
| Chặn | Ảnh hưởng | Khi nào thử lại |
|---|---|---|
| Deploy + kiểm URL công khai = việc chủ sản phẩm | Phase 13 có thể `NOT READY (chặn ngoài)` | sau khi chủ sản phẩm deploy |
| Bằng chứng LIVE với máy B / GPU | Phase 03/04/05/12 | khi máy rảnh; deterministic trước |

## Next phase
- Prompt: **01 — LibreChat deep reference** (pin `v0.8.7` @ `9e74cc0e57b395926122bd4062c1fcedc48ed465`, MIT)
- Bằng chứng cần: ma trận 12 hệ con với trích mã/test upstream; verdict từng hệ con; tiêu chí nghiệm thu kế thừa.
- Có thể chạy **song song** với Phase 02 (vùng khác nhau).
