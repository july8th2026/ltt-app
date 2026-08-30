# Phase 08 — Bằng chứng phát hành

**Đo 2026-08-30.** Chỉ ghi `PASS` cho phần **thật sự có bằng chứng**; phần chưa
đo ghi đúng nhãn của gói, không làm tròn lên.

---

## 1. Baseline / regression

```
python tools\gate.py   ->  RESULT: PASS   (25/25 buoc)
```

Phân loại lỗi trong đợt: **không có lỗi nào thuộc `CAUSED_BY_API_EXPANSION`.**

⚠️ Bảy bước từng đỏ trong đợt là của **app LTT VOICE** ở một phiên khác
(`PREEXISTING` với đợt này) — đã báo phiên đó và họ đóng hết.

---

## 2. Bất biến TIỀN

### 2.1 Job bất đồng bộ có báo giá

| Bất biến | Bằng chứng |
|---|---|
| Kiểm tham số **trước** giữ chỗ | `test_339::test_kiem_chay_TRUOC_price` đọc thứ tự thật trong `server/api/jobs.py` |
| Tổ hợp sai theo model bị chặn trước tiền | `test_336::test_to_hop_SAI_theo_model_bi_tu_choi` |
| Quote = giá job thật | `apps/taovideo/cost.py` là nguồn duy nhất; không bảng giá thứ hai ở tầng API |
| Giữ chỗ → quyết toán **đúng một lần** | `test_193::test_the_full_chain_runs_and_settles_exactly_once` |
| Sập giữa hold và hàng đợi | `test_193::test_a_crash_between_hold_and_queue_leaves_the_ledger_clean` |
| Worker chết giữa job | `test_193::test_a_worker_crash_mid_job_is_reclaimed_and_never_double_settles` |
| Provider hết giờ → hoàn | `test_193::test_a_provider_timeout_refunds_and_reconciles` |
| Gửi trùng đồng thời | `test_193::test_concurrent_duplicate_retries_create_one_job_and_one_hold` |
| Giữ chỗ **niêm phong** | `platform_core/credit.py::_giu_cho_da_niem_phong`, chốt ở `test_326` |

### 2.2 🔴 Chỗ tiền của việc nối chuỗi — và nó suýt vỡ im lặng

`video.upscale` khai `duration_s: {"measured_from": "video_key"}`: máy chủ **đo**
thời lượng lúc báo giá (H35.10a, đóng Q84 — giá không bao giờ được tính từ con số
người gọi khai).

Nối chuỗi đưa vào đó một **artifact**, không phải upload. Nếu
`apply_server_measurements` không đọc được `ThamChieuArtifact` thì Recipe A chết
**ở đúng bước tính tiền**, bằng một 400 khó hiểu.

⇒ `test_339::test_do_thoi_luong_CHAY_DUOC_tren_artifact_noi_chuoi` — **PASS**.

### 2.3 Stream / sync-billed

| Bất biến | Trạng thái |
|---|---|
| Bận là **503**, không phải 429; không thu tiền | `luong_vlm` không `danh_dau_loi` khi 429 (D-005) |
| Khách ngắt ≠ hỏng thượng nguồn | `LuongMo.xong()` / `.hong()` tách hai đường |
| Không bịa token để thu tiền | `chataistudio/cost.py` nói rõ giá phẳng vì upstream không đưa chi phí token |

---

## 3. Bảo mật

| Bất biến | Bằng chứng |
|---|---|
| Fail-closed | Đo trực tiếp: `LTT_PUBLIC_API_TOOLS` rỗng → **0** tool; bật riêng `video.generate` → đúng 1 |
| Id nhà cung cấp không ra bề mặt khách | `test_212::test_no_vendor_model_id_reaches_a_customer_surface` (5 đường) + `test_336::test_KHONG_ro_id_nha_cung_cap_hay_dia_chi_ha_tang` |
| Artifact **chỉ chủ sở hữu** dùng được | `test_339::test_ba_cong_bao_mat_o_duong_giai_artifact` |
| Danh sách trắng hợp đồng đầu ra | như trên — và **thiếu ToolSpec thì TỪ CHỐI**, không đi tiếp |
| Lỗi không lộ sự tồn tại | `test_339::test_moi_loi_tra_CUNG_MOT_thong_diep` |
| Khoá API không vào tệp cấu hình | `cam_cli` để khoá ở biến môi trường; `test_283` chốt |

### 3.1 🔴 Một cổng suýt bị tôi để hở, ghi lại vì nó là loại dễ lặp

`media.storage_key_for(..., tool=None)` **bỏ qua** danh sách trắng. Bản đầu của
tôi tra ToolSpec của job sinh ra artifact, và khi không tìm thấy thì **đi tiếp**.

Hệ quả nếu để nguyên: một job không tra lại được ToolSpec sẽ biến **mọi thứ**
handler để trong `result` — bản nháp, tệp trung gian, dump gỡ lỗi — thành đầu vào
gọi được, chỉ cần đoán ra id.

⇒ Nay không tìm thấy tool thì **từ chối**, và có test chốt đúng dòng đó.

---

## 4. Rollback — đo trực tiếp

| Yêu cầu §8 | Kết quả |
|---|---|
| Đóng `video.generate` bằng cờ operator | ✅ cờ rỗng → 0 tool |
| App **web** không hỏng khi tool đóng | ✅ `taovideo` nạp sạch, `enabled=True`, route `/taovideo` — web đọc `enabled`/`nav`, **không** đọc `LTT_PUBLIC_API_TOOLS` |
| Migration additive | ✅ không migration nào trong đợt này |
| Sổ credit nguyên vẹn | ✅ không đường tiền mới; bút toán append-only |

⭐ Hai công tắc **độc lập** là điều làm rollback rẻ: đóng cửa API không đụng tới
sản phẩm web, và ngược lại.

---

## 5. Bảng trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Cổng chất lượng đầy đủ | **PASS** |
| Bất biến tiền — job bất đồng bộ | **PASS** |
| Bất biến tiền — đo thời lượng khi nối chuỗi | **PASS** |
| Bảo mật — fail-closed, sở hữu, không rò id | **PASS** |
| Rollback | **PASS** |
| `video.generate` hợp đồng công khai | **PASS** *(operator chưa bật)* |
| Nối chuỗi artifact → job | **PASS** |
| Canary Seedance bằng credential thật | **BLOCKED_EXTERNAL** |
| Chuỗi Recipe A đầu-tới-cuối trên môi trường thật | **BLOCKED_EXTERNAL** |
| Codex Auth bridge — kỹ thuật | **DEFERRED_NOT_MVP** *(kiểm định xong, chưa viết mã)* |
| Codex Auth bridge — thương mại | **BLOCKED_POLICY** |
| Kiểm giao diện Developer Center trên bản đã deploy | **BLOCKED_EXTERNAL** *(cần deploy)* |

---

## 6. §7 — Cổng chính sách cho Codex

**`BLOCKED_POLICY`.**

Điều khoản của OpenAI hạn chế chia sẻ/bán lại quyền truy cập tài khoản và lách
giới hạn sử dụng. Mô hình đích là bán quyền gọi runtime của **một tài khoản
ChatGPT cá nhân** cho khách bên ngoài.

Theo nguyên văn gói: **không** tự đổi kiến trúc Auth để làm ô này xanh, **không**
thiết kế xoay tài khoản. Câu cần chủ sản phẩm trả lời ở
`05_CODEX_AUTH_BRIDGE.md` §6.

*(Ý kiến kỹ thuật, không phải tư vấn pháp lý.)*

---

## 7. Việc chủ sản phẩm đã quyết trong đợt

| Việc | Quyết định |
|---|---|
| Canary Seedance | **hoãn** — xử lý sau |
| WhisperX | **giao phiên khác** (`lttstudiosapp-9e`) |
