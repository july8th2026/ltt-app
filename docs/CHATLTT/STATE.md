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
- Phase hiện tại: **00–11 ✅ → tiếp 12** (torture)
  (03/04/05 PASS ở mức deterministic; bằng chứng LIVE với máy B/GPU hoãn tới Phase 12)

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
| **02** Gap runtime nội bộ | PASS — `platform_core/runtime_noi_bo/` (facade mỏng), 2 trường manifest, `streaming.py` gọi facade; 40 + 500 test xanh; gate `20260902T175553Z-19724` | `bdddeae` |
| **03** Text nội bộ | PASS (deterministic) — chuẩn hoá chunk→sự kiện, `DemToken` đọc `timings.cache_n`, SLO, **Q120**; LIVE hoãn Phase 12 (`reports/03_text_noi_bo.md`) | (commit phase 03–06) |
| **06** Catalog chính sách | PASS — `apps/chatltt/services/chinh_sach.py` allowlist fail-closed, `AppManifest.suc_khoe` + `danh_muc.suc_khoe_cua`, alias mới chỉ bằng registry (`test_613/614`) | (commit phase 03–07) |
| **07** Dữ liệu + sự kiện | PASS — `chatltt_*` dạng cây (D4=C), migration `7d2c1e9f4a03`, `hoi_thoai`/`su_kien`, reload từ CSDL (`test_616–618`) | (commit phase 03–08a) |
| **04** Ảnh nội bộ | PASS (deterministic) — `platform_core/jobs.DangBan` + `_provider_failure_kind` ⇒ bận là `resource_wait` không tiêu lượt thử; `LoiYeuCauAnh` cho lỗi người gọi; hỏi `health()` trước khi dịch prompt (`test_606–608`) | (commit phase 03–08a) |
| **05** Tiếng nội bộ | PASS (deterministic) — `DangBanTam(DangBan)`; giọng người khác ≡ không tồn tại; trần 1.500 không nới; tiền theo giây `ffprobe`; `so_lan_thu_for=5` (`test_609–612`) | (commit phase 03–08a) |
| **08a** Text (máy chủ) | PASS — `apps/chatltt/routes/*`, `services/{luot,dang_chay}`, SSE + Dừng + nối lại; hai lỗi thật đã sửa (múi giờ SQLite, `parent_id: null`) (`test_623`) | `b77fe83` |
| **08b** Text (giao diện) | PASS — `frontend/chatltt` (30 test), build 4 bundle, **kiểm trình duyệt thật**: stream, tạo lại, chuyển nhánh, nhánh sống qua reload, 390 px không tràn; sửa 302 của mỗi lệnh GET (`reports/08b_text_giao_dien.md`) | `1abeffc` |
| **09** Ảnh + tiếng | PASS — báo giá→xác nhận→nộp, tiến độ, khối ảnh/âm, cửa tài sản có kiểm sở hữu; hai lỗi thật đã sửa (**path traversal**, ô soạn đè chân trang) (`test_624/625`) | `f2b58a5` |
| **10** UX | PASS — trả ba nợ (Đọc to · số dư tự cập nhật · `anhnoibo.suc_khoe`), ba phím tắt, focus/tên đọc được, **reduced-motion**, ma trận 390–1920 px, không lộ ID thô (`App.test.tsx`, `reports/10_ux.md`) | (commit 10+11) |
| **11** Mở rộng | PASS — ba fixture (alias thứ ba · không khả dụng · phương thức lạ) + hai phép kiểm tĩnh + `11_THEM_MODEL_MOI.md` có test canh (`test_626`, `reports/11_mo_rong.md`) | (commit 10+11) |

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
| D12 | **ĐÃ ĐÓNG (Q120, 03/09)**: trần vào là số dẫn xuất `ngan_sach.TOKEN_VAO_TRAN`/`CONG_BO_CHO_CLIENT`; Q116 (65000) đã thay phần con số; `test_604` chốt |

## Chặn ngoài đang mở
| Chặn | Ảnh hưởng | Khi nào thử lại |
|---|---|---|
| Deploy + kiểm URL công khai = việc chủ sản phẩm | Phase 13 có thể `NOT READY (chặn ngoài)` | sau khi chủ sản phẩm deploy |
| Bằng chứng LIVE với máy B / GPU | Phase 03/04/05/12 | khi máy rảnh; deterministic trước |

## Next phase
- **12 — Torture**: đồng thời (đa tab, nối lại, đua dừng/xong, nộp trùng) · tiền
  (hỏng trước/sau giữ chỗ, kết quả một phần, thử lại, idempotency) · bảo mật
  (IDOR hội thoại/message/job/artifact, giọng người khác, XSS, body quá cỡ, rò
  alias/bí mật) · dữ liệu (xoá khi đang chạy, artifact mồ côi, retention,
  migration lên/xuống) · hiệu năng (thread dài, stream dài, mã lớn).
- Thử lại LIVE với máy B nếu máy rảnh.
- Nợ đã biết: chưa có test **axe** (a11y tự động) — Phase 12 nhận.

## Giao cho phase sau (từ 04/05/08a)
| Mục | Phase | Việc |
|---|---|---|
| `anhnoibo` chưa khai `admission_resource`/`gpu_vram_mb` — chưa đo thấy tranh chấp | 12 | đo tỉ lệ 429 rồi thêm một dòng `ToolSpec` nếu cần |
| Pre-check sở hữu giọng cho ChatLTT (UI chỉ mời từ `tuy_chon_dong`; không dùng danh sách để từ chối server-side vì bỏ sót kho chung) | 09 | cân hook `ToolSpec.kiem_truoc` nếu đo thấy đáng |
| Mục "## 2. 23/23 ToolSpec" trong `APP_API_COVERAGE_FINAL.md` đếm sai (thật: 13) — trôi từ Q108/Q109, không thuộc H43 | — | sửa khi ai đó chạm mục đó |
| Retention purge cho `deleted_at` của `chatltt_*` (Q75) | 12 | vòng bảo trì |
