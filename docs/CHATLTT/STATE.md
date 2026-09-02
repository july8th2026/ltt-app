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
- Phase hiện tại: **00 ✅ · 01 ✅ · 02 ✅ → tiếp 03** (04/05 có thể song song)

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
| **00** Bootstrap + nguồn chân lý | PASS — một cây/một gốc SHA, không rủi ro đè mã mới; runtime map + quyết định đã khảo sát | `b8f2845` |
| **01** LibreChat tham chiếu | PASS — `reports/01_librechat_tham_chieu.md`: 12 hệ con có trích mã/test @ `9e74cc0`; 18 tiêu chí AC-01..AC-18 | (commit phase 02) |
| **02** Gap runtime nội bộ | PASS — `platform_core/runtime_noi_bo/` (facade mỏng), 2 trường manifest, `streaming.py` gọi facade; 40 + 500 test xanh | (commit phase 02) |

## Hợp đồng đã cài ở Phase 02 (các phase sau DÙNG, không dựng lại)
| Hàm | Ký |
|---|---|
| `runtime_noi_bo.luong.mo_luong(db, *, user_id, tool_name, params, correlation_id="", holder_id="")` | `Iterator[dict]` sự kiện `response.started/delta/completed/failed`, `reasoning.delta`, `tool_call.delta`, `usage.updated`, `billing.updated`; ném `ThamSoSai/DangBan/ThieuCredit/KhongCoNangLuc` **trước** byte đầu; `.close()` = dừng (vẫn quyết toán) |
| `runtime_noi_bo.luong.mo_luong_tho(db, *, user_id, tool_name, than, duong, ...)` | `LuotLuong` byte thô — cho `/api/v1` |
| `runtime_noi_bo.danh_muc.danh_muc(db, *, user_id, cho_phep)` | `list[NangLuc]` (ten, phuong_thuc, che_do, nhan, hop_dong, models, tuy_chon, gia, duong_dan_app, san_sang) |
| `runtime_noi_bo.job.bao_gia(tool_name, params, *, db=None, user_id="")` → `BaoGia` · `nop_job(db, *, user_id, bao_gia, correlation_id="", idempotency_key="")` → `Job` | giữ đúng số đã báo, ép `owner_id`, `so_lan_thu` từ manifest |
| `AppManifest.so_lan_thu: dict` + `so_lan_thu_for(job_type)`; `ToolSpec.tuy_chon_dong: dict` (`param -> "module:callable(db, user_id)"`); `registry.tai_tham_chieu(ref)` | |

## Giao cho phase sau (từ Phase 02)
| Mục | Phase | Việc |
|---|---|---|
| `DangBanTam` (voice) / `LoiTaoAnh`←`BanError` (ảnh) rơi vào `retry`, tiêu lượt thử | 04 / 05 | vào bảng `_provider_failure_kind` hoặc chuẩn hoá `DangBan` nền tảng + test worker |
| `anhnoibo` chưa khai admission/VRAM | 04 | khai theo Q114 nếu có bằng chứng tranh chấp |
| `DemToken` không đọc `timings.cache_n` ⇒ stream không giảm giá cache | 03 | đo rồi quyết |
| `danh_muc.san_sang` mới chỉ đọc `manifest.enabled` | 06 | thêm hook sức khoẻ (sidecar `trang_thai()` ba trạng thái, cổng render) qua manifest |

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
