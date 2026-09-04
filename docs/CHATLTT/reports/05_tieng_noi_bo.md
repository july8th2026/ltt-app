# Phase 05 — Tiếng nội bộ (`speech.ltt`): truy vết, sở hữu giọng, trần 1.500, ba trạng thái cổng, bận ≠ hỏng, tiền theo giây

## Source
- worktree: `D:\LTTSTUDIOSAPP\.claude\worktrees\lttchat-autonomous-build-plan-1cf29d`
- branch: `claude/lttchat-autonomous-build-plan-1cf29d`
- base SHA: `bdddeae` (HEAD lúc bắt đầu phase; gốc chương trình `dac2406` admin-mvp-v3)
- end SHA: (chưa commit — phiên này **không commit**)
- canonical rules read: như Phase 04, thêm `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` dòng H43.5 + D10, `apps/ltt_voice/tham_so_cong_khai.py` (Q119, `SO_LAN_THU_JOB`), `apps/ltt_voice/manifest.py` (chỉ đọc — vừa được Phase 02 sửa), `docs/KHUON_BAN_MODEL_NHA.md` (khuôn 3.4/3.5 qua docstring `gia.py`)

## Evidence

### Truy vết đường `speech.ltt` (file:line ở cây này)

| Bước | Ở đâu | Ghi nhận |
|---|---|---|
| Báo giá + nộp (client nội bộ) | `runtime_noi_bo/job.py:45` `bao_gia(tool, params, db=, user_id=)`: `validate_tool_params` (`agent/tools.py:96`) kiểm **hình dạng**: `text` string ≤ `max_length=1500` (`manifest.py:200-201`), `voice_id` ≤ 40, `preset` ≤ 64; `tuy_chon_dong` chỉ **thêm `options/values`** cho giao diện (`agent/tools.py:65-72`), **không** dùng để từ chối (`:129-152` không so `values` cho `string`). `nop_job` (`:77`): `max_attempts = MANIFEST.so_lan_thu_for("ltt_voice.synthesize") = 5`, `admission_resource="vieneu_gpu"`, `admission_slots=1` | `bao_gia` **không kiểm sở hữu, không giữ tiền** — đúng vai (nền tảng không biết giá trị nào của ai, `registry.py:171-178`) |
| Worker | `_chay_mot_job`: `hold_persisted(vieneu_gpu,1)` → `_vram_can=2000` ⇒ `_giu_gpu` (máy chạy worker làn `voice`) → `_chay_handler` | test giả `_vram_can=0` để không giành GPU thật trên máy production |
| Handler | `apps/ltt_voice/jobs.py:78` `handle` phân nhánh theo `ctx.job_type`; `:84` `_tao_tieng`: `chuan_hoa` (`features.py:96`: text rỗng/preset lạ/vừa voice vừa preset ⇒ `LoiGiongNoi`) → **`:95` `san_sang()`** (thiếu token ⇒ `LoiGiongNoi` "chưa được thiết lập") → `:100` `giai_giong(db, yc)` (**sở hữu**, `features.py:221`: cùng câu cho "không tồn tại"/"không phải của bạn", kho chung `dung_chung` đọc được) → từ điển riêng `:123` → `chuan_bi_van_ban` chia lượt `TRAN_MOI_LUOT_SINH=1500` → **`:152` trần sau chuẩn hoá `3×thô+200` ⇒ `LoiGiongNoi`** → `goi_cong/goi_cong_dai` (`features.py:250` `_goi_va_dich_loi`: `SidecarBan⇒DangBanTam`, 413⇒`LoiGiongNoi`, `LoiSidecar⇒LoiHaTang`) → `:175` `_do_thoi_luong` (ffprobe = nguồn tiền) → tốc độ hậu kỳ **sau** đo → kho `voice/out/{owner}/{job_id}/tieng.wav` → `KetQua.as_result()` `credit_cost = gia.tinh(giay)` (0 nếu không đo được) | |
| Phân loại lỗi | `LoiGiongNoi(LoiNguoiGoi)` ⇒ không thử lại; `LoiHaTang(RuntimeError)` ⇒ retry có đếm (5 lượt ≈ 150 s > nạp model 73 s); `DangBanTam` — **trước phase này là `RuntimeError` thường ⇒ `retry`** | F1 |
| Cổng | `sidecar_client.py:229` `trang_thai()` **ba** giá trị: `chua_bat` / `khong_tra_loi` / `san_sang`; `san_sang()` `:47` chỉ hỏi *có token không*; `song()` `:196` GET `/health` đệm 5 s, timeout 1,5 s | |

### Phát hiện

| # | Finding | Source/runtime/test | Result |
|---|---|---|---|
| F1 | **Bận tiêu lượt thử**: `DangBanTam(RuntimeError)` không nằm trong `_provider_failure_kind` ⇒ `retry`; năm lần 429 liên tiếp = job `error` + hoàn tiền cho việc chưa chạy. Chính `tham_so_cong_khai.py:82` *tin* rằng `DangBanTam` "đã đi đường `defer_resource`" — chú thích đúng ý, mã chưa làm | Phase 02; `test_611::test_ban_la_DangBan_cua_nen_tang…` | **ĐÃ SỬA** — `DangBanTam(DangBan, RuntimeError)`; worker thật: 6 lần bận > 5 lượt vẫn `queued/attempts=0`, tiền giữ nguyên |
| F2 | `jobs.py:95` dùng `san_sang()` — **là chốt cấu hình, không phải bằng chứng sống**: có token mà cổng chết ⇒ lượt gọi thật ném `LoiSidecar` ⇒ `LoiHaTang` ⇒ retry có đếm. Đường job **không** dựa vào chip; chip xanh giả là chuyện của trang web (Phase 02 đã giao Phase 06 hook `trang_thai()`) | `test_611::test_job_cong_chet_la_LoiHaTang…`, `test_san_sang_chi_la_cau_hoi_cau_hinh…` | **Đúng như hiện tại — không sửa**. Không đổi `san_sang()` thành `song()` ở job: cổng chết lúc deploy phải là `LoiHaTang` (thử lại qua 5 lượt), còn "chưa bật" là lỗi cấu hình không thử lại — hai câu, hai hành vi, đang đúng |
| F3 | Giọng người khác ≡ giọng không tồn tại: **cùng một chuỗi** `"Không tìm thấy giọng này trong tài khoản của bạn."`; cả hai là `LoiNguoiGoi` | `test_609::test_giong_nguoi_khac_va_khong_ton_tai_CUNG_mot_thong_diep` | PASS |
| F4 | Cửa nội bộ: `bao_gia(voice_id của người khác)` **không ném, không giữ tiền, không tạo job** (đúng vai); sở hữu chỉ kiểm lúc thi hành; worker: job `error` sau **1** lượt (không phải 5), hoàn đủ, cổng không bị gọi | `test_609` §3, §4 | PASS — nhưng khách vẫn "giữ tiền → hàng đợi → hoàn" cho một câu trả lời cửa vào biết được; xem D-05.2 |
| F5 | Trần 1.500 ở schema: 1.501 ⇒ `ThamSoSai` tại `bao_gia`; `chuan_hoa` không cắt, không gõ số; 413 ⇒ `LoiGiongNoi` | `test_610` | PASS, **không nới** (`TRAN_KY_TU_CONG_KHAI <= 1500` chốt) |
| F6 | Từ điển nở > `3×thô+200` ⇒ `LoiGiongNoi` **trước** khi gọi cổng; từ điển thường qua | `test_610` §4 | PASS |
| F7 | Tiền = `gia.tinh(giây ffprobe)`; không đo được ⇒ 0; tốc độ 1,5× không làm rẻ đi; worker thu 1, hoàn 1 trong 2 đã giữ | `test_612` | PASS |
| F8 | `so_lan_thu` chảy từ manifest: `so_lan_thu_for("ltt_voice.synthesize") == 5`, `nop_job` ghi `max_attempts=5` | `test_609` §5 | PASS — D10 GENERIC_GAP đã đóng ở Phase 02, phase này chỉ chứng minh |

## Decisions made autonomously

| Decision | Options | Chosen | Why | Reversible |
|---|---|---|---|---|
| **D-05.1** `DangBanTam` nhận tín hiệu nền tảng bằng cách nào | (a) dịch trong `jobs.py` (`except DangBanTam ⇒ raise DangBan`) · (b) `DangBanTam` kế thừa `platform_core.jobs.DangBan` (giữ cả `RuntimeError`) | **(b)** | một chỗ (`features.py`), cả hai cửa `goi_cong/goi_cong_dai` và nhánh ghi danh (`jobs.py:278`) cùng được; giữ `retry_after_s`, không kế thừa `LoiNguoiGoi`/`LoiHaTang` (test_340/353/501 chốt) | Có |
| **D-05.2** ChatLTT có nên hỏi sở hữu giọng **trước** khi giữ tiền, và bằng cách nào không import app | (a) import `apps.ltt_voice.features.giai_giong` · (b) kiểm "voice_id ∈ `options` của `tuy_chon_dong`" phía client · (c) hook nền tảng mới `ToolSpec.kiem_truoc: "module:callable(db,user_id,params)"` · (d) không hỏi trước, để worker trả lời | **Khuyến nghị (b) cho UI + (d) là thẩm quyền; (c) chỉ nếu Phase 09/12 đo thấy tỉ lệ job hỏng-vì-giọng đáng kể** | (a) bị `test_147/308` cấm, đúng. (b) rẻ và không import app: UI **chỉ mời** giọng từ `danh_muc(...).tuy_chon`/`resolve_params_schema(db,user_id)` + preset — không có ô chữ tự do thì không có `voice_id` lạ để nộp. ⚠️ (b) **không** được dùng để *từ chối* server-side: `tuy_chon_voice_id` cố ý bỏ **kho chung** (`dung_chung`) mà `giai_giong` cho phép — chặn theo danh sách là chặn nhầm giọng hợp lệ. (c) là GENERIC_GAP thật (route web đang gọi `giai_giong` tại cửa, `_p_tao.py:282`, và Public API không có) nhưng chưa có số đo về mức thiệt hại (đã có D10 cho `so_lan_thu` là vì đo được 31 s chờ; ở đây worker hỏng ngay lượt 1 sau `LoiNguoiGoi` — chi phí là một vòng hàng đợi, không phải 3–5 lượt) | Có |
| **D-05.3** `jobs.py:95` `san_sang()` | (a) đổi sang `trang_thai()=="san_sang"` · (b) giữ | **(b)** | xem F2: cổng chết phải là `LoiHaTang` (retry), không phải một lỗi "chưa sẵn sàng" cố định; `song()` lại đệm 5 s và có timeout 1,5 s — không đủ tin để quyết một job | — |
| **D-05.4** Không đổi trần, giá, manifest | — | giữ | Q119/V10; manifest vừa được Phase 02 sửa và ngoài ranh giới | — |

## Changes

- `apps/ltt_voice/features.py:23` import `DangBan`; `:69` `class DangBanTam(DangBan, RuntimeError)` — `DangBan.__init__(self, "May tao tieng dang ban", retry_after_s=…)`; docstring ghi hồi quy và hai chốt không-kế-thừa.
- `apps/ltt_voice/jobs.py` — **không đổi** (đã để `DangBanTam` bay lên nguyên vẹn; `san_sang()` giữ theo D-05.3).
- Dùng chung với Phase 04: `platform_core/jobs.py:86` `DangBan`, `platform_core/job_runner.py:588/600`.
- Test mới: `tests/test_609_tieng_noi_bo_giong.py` (9), `tests/test_610_tieng_noi_bo_tran_van_ban.py` (7), `tests/test_611_tieng_noi_bo_san_sang_va_ban.py` (6), `tests/test_612_tieng_noi_bo_tien_theo_giay.py` (4).

## Tests

| Command / journey | Result |
|---|---|
| `python -m pytest tests/test_609_*.py tests/test_610_*.py tests/test_611_*.py tests/test_612_*.py -q -n 0 -p no:cacheprovider` | **26 passed** (lượt 606–612 chung: **58 passed** in 12.62s) |
| Preset ⇒ `(None, preset)` không chạm CSDL; giọng của mình ⇒ `(ref_b64, None)`; kho chung đọc được; vừa `voice_id` vừa `preset` ⇒ từ chối trước CSDL | PASS |
| Giọng người khác vs không tồn tại: `str(e1) == str(e2)`, cả hai `LoiNguoiGoi` | PASS |
| `bao_gia(voice_id người khác, db=, user_id=)`: trả `BaoGia`, số dư 100 nguyên, 0 job; `resolve_params_schema(db,user_id)["voice_id"]["values"] == [giọng active của mình]` (không giọng tắt, không giọng người khác) | PASS |
| Worker: `nop_job` (`max_attempts=5`) với giọng người khác → `_chay_mot_job` → `error`, `attempts=1`, `failed` không `retry_scheduled`, hoàn đủ, `sidecar.noi/noi_dai` không bị gọi | PASS |
| 1.501 ⇒ `ThamSoSai("text")`, 1.500 qua; `chuan_hoa` giữ nguyên 1.501 ký tự; nguồn `chuan_hoa` không chứa `1500`; 413 ⇒ `LoiGiongNoi` | PASS |
| Từ điển `{"a": "x"×160}` trên 199 ký tự thô ⇒ `LoiGiongNoi` "từ điển" trước khi gọi cổng; `{"LTT": "e lờ tê tê"}` qua, độ dài ≤ 3×+200 | PASS |
| `trang_thai()` ∈ {`chua_bat`,`khong_tra_loi`,`san_sang`} theo token/`song()`; không token ⇒ job `LoiGiongNoi` không gọi mạng; token + cổng chết ⇒ `LoiHaTang` ⇒ `retry`; `SidecarBan(7.5)` ⇒ `DangBanTam` là `DangBan` ⇒ `("resource_wait", 7)` | PASS |
| Worker: `SidecarBan(3)` **6 lần** (> `max_attempts=5`) ⇒ `queued`, `attempts=0`, `provider_state=rejected`, 6 sự kiện `resource_wait`, không `failed/credit_settled`, `so_da_giu` nguyên, số dư `100−held` | PASS |
| Handler: giây giả 6,0 ⇒ `credit_cost == gia.tinh(6.0)`, `audio_key == voice/out/{owner}/job612/tieng.wav` tồn tại trong kho; giây 0 ⇒ 0; tốc độ 1,5× vẫn `gia.tinh(6.0)`, `duration_played_s≈4`; worker: giữ 2, thu 1, số dư 99, sự kiện `credit_settled` | PASS |
| Hồi quy tệp ghim: `test_501 test_353 test_340 test_338` (+ `test_253/276/313/302`) `-n 0` | **185 passed** (chung lượt Phase 04) |
| `check_silent_except` / `check_i18n` / `lint_app_contract` | 62/62 PASS · 774/774 không tăng · 16 app, 0 ERROR 0 WARN |
| Hồi quy đầy đủ theo thành phần | **2 failed, 1184 passed, 7 skipped** in 463 s (`-n 0`, 74 tệp). Hai tệp đỏ **không thuộc phase này**: `test_211::test_every_table_has_a_retention_class` (bảng `chatltt_conversation/_execution/_message` chưa vào `governance.STORES`) và `test_212::test_the_document_classifies_every_app` (`undecided: ['chatltt']`) — cả hai do phiên Phase 07 (`apps/chatltt/`, migration `20260903_1000_chatltt_cay_hoi_thoai.py`) đang mở trên cùng cây; đã báo cho phiên điều phối, không sửa ở đây (ngoài ranh giới tệp). Mọi tệp `core:job`/`app:anhnoibo`/`app:ltt_voice`/`test_256/60/308/147` xanh |

## Failures found and repaired
- `test_612` lượt đầu: giữ = thu = 2 ⇒ đổi giây giả 6 → 3 để "hoàn phần dư" đo được thật.
- Không có hồi quy: `test_501::test_cong_BAN_thi_xep_lai…` (retry_after 7.5, không `LoiNguoiGoi`, không `LoiHaTang`), `test_340/353` (không `LoiNguoiGoi`) đều xanh với `DangBanTam(DangBan, RuntimeError)`.

## External unknown/blocker
- **LIVE bị chặn ở phiên này** (không chạm máy B/GPU/sidecar thật): **TTFA** (time-to-first-audio) và **RTF** (thời gian sinh ÷ thời lượng), giây GPU/giây tiếng để đối chiếu giá vốn (`gia.py` ghi *"chưa đối chiếu được với giá vốn vì chưa có RTF đo thật"*), độ trễ nạp model sau deploy (đã có số 39,9–73,1 s), chất lượng bản ghép ở 3.000/5.000 ký tự (V10). Công cụ có sẵn: `tools/chay_thu_ltt_voice.py` (+ `setup/chay_thu_ltt_voice.ps1`) — đi đúng đường khách: `submit_with_credit` → worker production → cổng → ffprobe → quyết toán, in số dư trước/sau (**tiêu credit thật có chủ đích**); `tools/cong_chat_luong_voice.py` (+ `setup/cong_chat_luong_voice.ps1 [-Ghim]`) — cổng V10 so baseline ghim theo phiên bản (CER, tương đồng người nói, trôi giọng); `voice_sidecar/do_chat_luong.py`, `tools/do_troi_tong.py` cho số đo thành phần. TTFA/RTF suy từ `job_events` (`execution_started` → `execution_completed.duration_ms`) ÷ `result.duration_s`.
- D-05.2(c) `ToolSpec.kiem_truoc` — chỉ mở nếu Phase 09/12 đo thấy đáng.

## Verdict
**PASS** — 26/26 test deterministic xanh; bận ⇒ `resource_wait` chứng minh trên worker thật với 6 lần bận > 5 lượt; preset/giọng sở hữu/giọng người khác/không tồn tại đúng hợp đồng (cùng câu, không giữ tiền ở cửa báo giá, hỏng ngay lượt 1 ở worker); trần 1.500 không nới; ba trạng thái cổng đúng và đường job không lấy `san_sang()` làm bằng chứng sống; tiền theo giây đo được. LIVE = chặn ngoài.

## Next
Autocontinue to phase: **06** (catalog/chính sách) — hook `san_sang` đọc `sidecar_client.trang_thai()` và `cong_render.dang_ban()` qua manifest (đã giao từ Phase 02); Phase 09: khối "Đọc to/Tạo giọng" chỉ mời giọng từ `tuy_chon` + preset (D-05.2b), hiện `resource_wait.delay_seconds`; Phase 12: đo tỉ lệ job hỏng-vì-giọng để quyết D-05.2(c).
