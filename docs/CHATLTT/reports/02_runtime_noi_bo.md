# Phase 02 — Khoảng trống runtime nội bộ: chứng minh, phân loại, và cài facade

## Source
- worktree: `D:\LTTSTUDIOSAPP\.claude\worktrees\lttchat-autonomous-build-plan-1cf29d`
- branch: `claude/lttchat-autonomous-build-plan-1cf29d`
- base SHA: `dac2406` (admin-mvp-v3) · end SHA: (commit đóng phase)
- canonical rules read: `CLAUDE.md`, `AGENTS.md` §8/§10, `docs/DEVELOPMENT_WORKFLOW.md`, `docs/QUYET_DINH_NEN_TANG.md` Q92/Q106/Q107/Q112/Q114/Q117–Q119, `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` §3–§6

## Evidence — năm đồ thị gọi đã truy vết (file:line trong báo cáo tác nhân, 02/09)

| Đường | Chuỗi cửa đã đo | Kết luận |
|---|---|---|
| TEXT sync `/api/v1/chat/completions` | `require_tool` → `for_tool` → `validate` → `estimate_input`/`sync_output_cap` → `admission.acquire(mode="sync")` → `giu_cho_luot` → **commit** → `executor.run` → `quyet_toan_hoac_hoan`; `BanError` ⇒ hoàn + 503 | mọi mảnh **không** cần Principal trừ 3 cổng Q92 + rate/policy/sandbox |
| TEXT stream `/messages` `/responses` | `_cua` (`streaming.py:516`): alias → `admission.acquire(mode="stream")` → ước vào/kẹp ra → `giu_cho_luot` → **commit** → `luong_vlm.mo` → `_phat` (đếm `DemToken`, quyết toán ở `finally`, phiên CSDL mới) | **lắp ráp chỉ ở HTTP handler** — đây là khoảng trống 1 |
| TEXT job `/quotes` + `/jobs` | `validate_public_input` → `price` (`registry.credit_for`) → `quotes.issue` … `invocation.submit` → `job_submit.submit_with_credit` → worker `hold_persisted` → handler → `credit_cost` trong result | `submit_with_credit` là cửa nộp nội bộ thật; **không truyền `max_attempts`** |
| IMAGE `image.ltt` | `anhnoibo/jobs.handle` → `features.chuan_hoa` (chủ sở hữu theo khoá) → `DieuPhoi.chay` (dịch prompt, presigned GET/PUT, poll 3 s, trần 900 s) → bill theo **ảnh thật** | `cong_render.BanError` bị bọc thành `LoiTaoAnh` ⇒ worker `retry` (tiêu lượt thử) thay vì `resource_wait`; app **không khai admission** |
| VOICE `speech.ltt` | `ltt_voice/jobs.handle` → `giai_giong` (sở hữu, cùng câu cho "không có" và "không phải của bạn") → từ điển → chia lượt 1.500 → sidecar → ffprobe đo → `credit_cost` theo giây sinh | `DangBanTam` không nằm trong `_provider_failure_kind` ⇒ cũng tiêu lượt thử; `SO_LAN_THU_JOB=5` chỉ truyền ở 4 route web |

Sáu câu hỏi của gói:

1. Có resolver tool nội bộ generic? **Có** — `registry.discover()` + `ToolSpec.name`; `public_api/executor.for_tool_name` (không import app).
2. `sync_executor` đủ generic? **Đủ** cho text (`aliases/model_id/validate/estimate_input/context_output_cap/mac_dinh_cho/run`). Stream không cần executor thứ hai vì `luong_vlm.mo` đã là đường chung.
3. Có submit/quote generic cho app? **Có submit** (`job_submit.submit_with_credit`), **giá** (`credit_for` + `agent/tools.validate_tool_params`); **quote ký** chỉ có ở Public API và không cần cho client cùng phiên đăng nhập.
4. Stream có giao thức nội bộ? **Không** — chỉ HTTP route với `Principal`.
5. Metadata/availability truy vấn được ngoài Public API? **Một phần** — `project_tool(manifest, tool)` không cần Principal; `build_catalog/require_tool` thì cần `config` + `Principal`.
6. Thiếu gì cho một client nội bộ? (a) cửa stream gọi được; (b) phép chiếu catalog theo allowlist sản phẩm; (c) hai siêu dữ liệu manifest: số lần thử job và tuỳ chọn động theo người dùng.

## Decisions made autonomously

| Đề xuất | Phân loại | Chọn | Vì sao | Đảo được |
|---|---|---|---|---|
| `runtime_noi_bo.luong.mo_luong` / `mo_luong_tho` | **THIN_FACADE** | cài | mọi mảnh có sẵn và có 15 tệp test ghim; chỉ hạ phần lắp ráp khỏi HTTP handler; `server/api/streaming.py` gọi lại | có |
| `runtime_noi_bo.danh_muc` | **THIN_FACADE** | cài | mượn `catalog.project_tool` (đã bỏ id nội bộ, test_212), thêm allowlist + tuỳ chọn động + `bang_gia` | có |
| `runtime_noi_bo.job.bao_gia` | **THIN_FACADE** | cài | gói `validate_tool_params` + `lane_for` + `credit_for` thành `BaoGia` | có |
| `runtime_noi_bo.job.nop_job` | **EXISTS_USE_IT** | bọc mỏng | `submit_with_credit` đã nhận đủ tham số; chỉ ép `owner_id`, lane, `so_lan_thu`, admission từ manifest | có |
| `ToolSpec.stream_executor` | **NOT_NEEDED** | bác | `luong_vlm.mo` là đường stream chung, alias→id đã do executor lo | — |
| `AppManifest.so_lan_thu` | **GENERIC_GAP** | cài | hằng `SO_LAN_THU_JOB=5` không import chéo được; API chạy 3 lượt trong khi web 5 (bất đối xứng đo được) | có |
| `ToolSpec.tuy_chon_dong` | **GENERIC_GAP** | cài | ba cơ chế enum động không biết `user_id`; `voice_id` là ô chữ tự do trên palette | có |
| `Principal` nội bộ trong `public_api` | **NOT_NEEDED** | bác | Principal mang key_id/mode/allowlist khoá — khái niệm chỉ có vì khoá API bán ra ngoài | — |
| Đường ChatLTT dùng cho stream | `/v1/chat/completions` + `stream_options.include_usage` | chọn | hình dạng OpenAI chunk đơn giản nhất để chuẩn hoá; llama-server chỉ đính `usage` khi được xin | có |

## Changes

- **Mới** `platform_core/runtime_noi_bo/` — `__init__.py` (lý do tồn tại), `tim.py` (`tim_tool`, tra qua `registry.discover()` không bind tên), `luong.py` (`chuan_bi` → `mo_thuong_nguon` → `LuotLuong.luong` byte thô có quyết toán ở `finally`; `mo_luong` sinh sự kiện canonical §5.3; `response.started` **trước** khi mở luồng — D7), `danh_muc.py` (`NangLuc`, `danh_muc(db, user_id, cho_phep)`), `job.py` (`BaoGia`, `bao_gia`, `nop_job`).
- `platform_core/registry.py`: `ToolSpec.tuy_chon_dong` (+ kiểm lúc nạp: tham số có thật, kiểu `string`, tham chiếu `module:attribute`, **không import lúc nạp**), `AppManifest.so_lan_thu` + `so_lan_thu_for()` (+ kiểm job_type thuộc app, số nguyên ≥ 1), `tai_tham_chieu()`.
- `platform_core/agent/tools.py`: `resolve_params_schema/validate_tool_params(..., db=None, user_id="")` resolve tuỳ chọn động; tra `registry.discover()` qua thuộc tính module.
- `platform_core/public_api/invocation.py`: `submit()` truyền `max_attempts=_so_lan_thu(tool, lane)`.
- `server/api/streaming.py`: `_cua` gọi `cua_luong.chuan_bi` + `mo_thuong_nguon`; bốn lỗi trước-byte-đầu dịch sang 400/409/429-503/413; `_phat/_quyet_toan/_hoan/_tin_nhan` uỷ quyền; `_max_tokens` lấy mặc định cửa stream từ executor. **27 route đóng băng không đổi** (test_178/192 xanh). Ba cạnh `apps.ltt_llm` còn lại (`_tran_vao_cua_model`, `ngan_sach`) giữ nguyên — nợ có tên trong `test_147`.
- `apps/ltt_voice/manifest.py`: `so_lan_thu={synthesize:5, enroll:5}`, `tuy_chon_dong={"voice_id": "apps.ltt_voice.tham_chieu:tuy_chon_voice_id"}`; `tham_chieu.tuy_chon_voice_id(db, user_id)` (giọng `active` của chính người dùng).
- `tests/test_360_ban_co_ly_do.py`: đếm dòng log nhánh bận ở cả facade (nhánh đã dời chỗ, không mất).

## Tests

| Command / journey | Result |
|---|---|
| `pytest tests/test_600 tests/test_601 tests/test_602 -n 0` | **40 passed** |
| 24 tệp ghim (272, 285, 290, 291, 292, 293, 385, 360, 363, 372, 194, 178, 192, 273, 334, 147, 308, 60, 212, 259, 313, 87, 88, 271) `-n 0` | **500 passed, 3 skipped**, 1 fail ở `test_360` (đã sửa test: nhánh bận dời sang facade) |
| `python tools/gate.py --doi` (tự hạ xuống đầy đủ: 5.435 test) | **PASS** `test-results/gates/20260902T175553Z-19724.json` — 4 bước tự bỏ qua trong cây riêng (frontend `node_modules`, bất biến đa tiến trình). Hai lượt trước đỏ vì: nuốt lỗi lặng (`job.py`, sửa), i18n +6 (bọc `_t` + dịch EN), profile stale (sinh lại), `test_82` thiếu vendor (junction), `test_37` timeout 30 s dưới tải (xanh khi chạy riêng, không tái hiện ở lượt PASS) |

Sáu tính chất `test_600` chứng minh điều kiện PASS của gói: không Principal/không URL máy · giữ chỗ trước khi mở luồng, `response.started` trước prefill · sinh ít trả ít + `billing.updated` đúng số · bận ⇒ sự kiện `ban` + hoàn đủ + nhả suất · `.close()` giữa chừng vẫn quyết toán phần đã sinh · alias lạ/thiếu tiền/hết suất là ngoại lệ trước byte đầu, chưa giữ tiền · đường byte thô cho `/api/v1` **không sửa một byte**.

## Failures found and repaired
- `tim.py`/`danh_muc.py`/`agent/tools.py` bind `discover` lúc import ⇒ bộ test cắm app thử bằng `monkeypatch.setattr(registry, "discover")` không tới được (đúng cái `conftest.app_thu` cảnh báo). Sửa: tra qua thuộc tính module.
- `ThieuCredit` sau khi đã giành suất: `db.rollback()` không đủ tin (pysqlite không giữ SAVEPOINT) ⇒ thêm `release_by_id` idempotent. Nếu không, một suất mồ côi giữ GPU 20 phút.
- Số liệu test nhỏ làm giữ = thu = 1 credit ⇒ nâng `max_tokens` để "hoàn phần dư" thật sự đo được gì.

## External unknown/blocker
- Không có. Chưa cần máy B ở phase này (fake `luong_vlm.mo`).

## Phát hiện phụ — GIAO cho phase sau (không sửa ở đây)
| Phát hiện | Phase | Việc |
|---|---|---|
| `DangBanTam` (voice) và `LoiTaoAnh` bọc `BanError` (ảnh) rơi vào nhánh `retry` của `_provider_failure_kind` ⇒ **tiêu lượt thử** thay vì `resource_wait` | 04 / 05 | thêm hai lớp vào bảng (hoặc chuẩn hoá một `DangBan` nền tảng) + test hành vi worker |
| `anhnoibo` không khai `admission_resource/_slots`, không `gpu_vram_mb` | 04 | khai theo Q114 nếu bằng chứng cho thấy tranh chấp GPU máy B |
| `cong_vlm.doc_su_dung` đọc `timings.cache_n` nhưng `DemToken` không ⇒ stream không giảm giá cache (cả `/api/v1` lẫn ChatLTT) | 03 | đo có/không có prefix cache; nếu đáng kể thì `DemToken._gop` đọc thêm `timings` |
| `_mot_cuc(config)` tham số chết | — | dọn khi chạm lại tệp |

## Verdict
**PASS** — ChatLTT gọi được cả ba năng lực bằng `user_id` + tên tool + tham số, không Principal, không URL máy, không import app; một đường đếm token/quyết toán cho cả `/api/v1` và client nội bộ.

## Next
Autocontinue to phase: **03** (Text: SLO + benchmark deterministic/LIVE + đóng D12 Q116↔`ngan_sach.py`). 04 và 05 có thể song song.
