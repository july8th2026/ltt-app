> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: docs/PUBLIC_API/. Chỉ đọc để hiểu lịch sử.

# API Expansion V2 — báo cáo cuối đợt

**2026-08-30.** Gói `LTT_API_EXPANSION_V2_PROMPT_PACK`, 9 phase. Phase 01–03,
06–09 thi hành; 04–05 kiểm định rồi dừng ở `BLOCKED_POLICY`.

---

## 1. Mục tiêu

Đưa **Seedance** ra Public API, **bọc Codex Auth** sau khoá LTT, dựng
**Developer API Center**, và chứng minh API **ghép thành dây chuyền**.

---

## 2. Kiến trúc hiện tại

```
khach --LTT API key--> /api/v1 --+--> /quotes -> /jobs -> worker -> artifact
                                 |      (ASYNC_JOB: image.*, video.*)
                                 +--> /chat/completions   (SYNC_BILLED)
                                 +--> /messages | /responses  (STREAM)
```

Một hàng đợi, một sổ tiền, một kho. Không đường nào thêm trong đợt này.

---

## 3. Quyết định và phương án đã cân

| Quyết định | Chọn | Vì sao không chọn cái kia |
|---|---|---|
| Ràng buộc theo model của Seedance | `PublicModel.constraints` **đã có sẵn** | schema hợp nhất khiến khách không thấy ràng buộc trước khi gọi, và sinh nguồn chân lý thứ hai |
| `provider_model_id` | **khai**, để danh sách trắng lọc | giấu đi thì phép kiểm rò **mất mục tiêu để săn** |
| Nối chuỗi | artifact **tham chiếu**, không dời | dời artifact là lấy mất kết quả job trước |
| Hình dạng Codex | ToolSpec `STREAM` qua `require_tool` | bridge thẳng làm mất ba cổng fail-closed |
| Trang tài liệu | giữ nguyên chốt của chủ sản phẩm | **khuyến nghị ban đầu của tôi sai** — xem §16 |

---

## 4. Tệp đã đổi

| Tệp | Việc |
|---|---|
| `apps/taovideo/manifest.py` | hợp đồng công khai **sinh từ** `models.py` |
| `platform_core/public_api/invocation.py` | `_check_model_constraints` · `ThamChieuArtifact` |
| `server/api/uploads.py` | giải artifact id, hai cổng bảo mật |
| `platform_core/public_api/examples.py` | `BA_CUA`, số cửa sổ từ một nguồn |
| `apps/ltt_llm/manifest.py` | mô tả model sinh từ `ngan_sach.py` |
| `tools/do_current_truth.py` | bảng trạng thái **sinh từ registry** |
| `tools/check_xuong_dong.py` · `don_tien_trinh_mo_coi.py` | hai bánh cóc mới |
| `tests/test_336` · `test_339` | 19 phép kiểm mới |

---

## 5. Thay đổi hợp đồng

| | Loại |
|---|---|
| `video.generate` vào danh mục đóng băng + 3 model kèm `constraints` | ADDED |
| Tham số media nhận **artifact id** | ADDED |
| `text.chat` mô tả model: `131K` → `89K` | FIXED *(không phá vỡ tương thích)* |
| Tài liệu: `"No streaming yet"` → ba cửa | FIXED |

`check_api_compat`: **0 phá vỡ tương thích** ở mọi lượt.

---

## 6. Seedance

**`TECHNICALLY_READY`**, operator **chưa bật**, canary **`BLOCKED_EXTERNAL`**.

Rào cản cũ (*"tập tuỳ chọn đổi theo model"*) đóng bằng cách **giải**: mỗi model
công bố tập của riêng nó; tổ hợp sai bị chặn **trước** `price()`. Bốn đường
tham chiếu **hoãn có ghi** vì chưa chứng minh được ownership.

**Chủ sản phẩm quyết: xử lý canary sau.**

---

## 7. Codex Auth bridge

**Kỹ thuật: `DEFERRED_NOT_MVP`** — kiểm định xong, **không viết mã**, có chủ ý.
**Thương mại: `BLOCKED_POLICY`.**

Rẻ hơn hồ sơ nói: hợp đồng `STREAM` đã có, cô lập thread đã có mầm, giá đã đúng
khuôn. Bảy việc đều làm được — nhưng chỉ có giá trị nếu câu hỏi ở
`05_CODEX_AUTH_BRIDGE.md` §6 được trả lời "có".

---

## 8. Developer API Center

**Phần lớn đã xong**, và khuyến nghị lớn nhất của tôi ở Phase 01 **sai** — xem §16.

Việc thật đã làm: dẹp 6 chỗ gõ tay nói ba giá trị mâu thuẫn; đưa bảng **ba cửa**
ra trang công khai; thêm mục **Gỡ ra** (trước đó không tồn tại).

---

## 9. Công thức chuỗi

| Chuỗi | Trạng thái |
|---|---|
| Recipe A `video.generate → video.upscale` | **VERIFIED_LOCAL** — đo thời lượng trên artifact đã chốt |
| Recipe B/C/D | **IMPLEMENTED**, chưa chạy đầu-tới-cuối |
| Chuỗi thật trên môi trường production | **BLOCKED_EXTERNAL** |

---

## 10–11. Bất biến tiền và bảo mật

Đầy đủ ở `09_RELEASE_EVIDENCE.md` §2–§3. Hai điểm đáng nhắc lại:

* **Đo thời lượng khi nối chuỗi** — nếu `apply_server_measurements` không đọc
  được artifact thì Recipe A chết ở **đúng bước tính tiền**. Có test.
* 🔴 **Một cổng suýt bị tôi để hở**: `storage_key_for(..., tool=None)` bỏ qua
  danh sách trắng. Bản đầu của tôi đi tiếp khi không tra được ToolSpec — tức mọi
  tệp trung gian trong `result` thành đầu vào gọi được. Nay **từ chối**.

---

## 12. Test / gate

```
python tools\gate.py   ->  RESULT: PASS   (25/25)
```

Bánh cóc mới: kiểu xuống dòng · thu hồi tiến trình mồ côi · ba tệp test thôi ghi
vào tệp thật · không số ngữ cảnh gõ tay · không test nào ghi vào SDK/baseline/`.po`.

---

## 13–14. Bằng chứng production và chặn ngoài

| | |
|---|---|
| Bốn tool đang phục vụ khách | đo bằng `GET /api/v1/tools` |
| Ba cửa streaming | đo qua Cloudflare: 66 và 63 khối SSE |
| Canary Seedance | **BLOCKED_EXTERNAL** — chủ sản phẩm hoãn |
| Kiểm giao diện trên bản deploy | **BLOCKED_EXTERNAL** — cần deploy |
| Codex thương mại | **BLOCKED_POLICY** |

---

## 15. Rollback

Đo trực tiếp: cờ rỗng → **0** tool; app web `taovideo` vẫn nạp sạch. Hai công
tắc **độc lập** là thứ làm rollback rẻ.

---

## 16. 🔴 Một khuyến nghị của tôi đã bị rút

Phase 01 tôi đề xuất mở một trang danh mục **công khai**, viện dẫn tiền lệ
`/vps`. Quan sát đúng, **kết luận sai**: chủ sản phẩm đã chốt **hai nhịp** rằng
toàn bộ `/developers/*` đứng sau đăng nhập, và mã còn dựng bánh cóc hai chiều
quanh chốt đó.

⭐ Bài học, vì nó lặp lại được: **một tiền lệ không phải một luật.** `/vps` trả
lời *"có đáng mua không"*; `/developers/*` trả lời *"tôi đang dùng cái gì"* — và
nó **đọc dữ liệu tài khoản**, đó là điểm của nó. Trước khi áp một tiền lệ, kiểm
xem trường hợp này đã có quyết định riêng chưa.

Giữ lại thay vì xoá: lý do rút có giá trị hơn khuyến nghị ban đầu.

---

## 17. Hoãn, và đề nghị tiếp theo

| Hoãn | Vì sao |
|---|---|
| 4 tham chiếu media của Seedance | chưa chứng minh ownership qua `upload_sessions` |
| Codex bridge | chờ một quyết định, không chờ code |
| `video.short_clips` | thiếu trần đồng thời GPU (H35.10c) |

**Đề nghị năng lực tiếp theo:** mở dần bốn tham chiếu media. Nó là thứ biến
Recipe B/D từ *"gọi được"* thành *"dùng được"*, và mỗi bậc mở là một phép chứng
minh ownership độc lập — rủi ro chia nhỏ được.

---

## 18. Bảng cuối

| Hạng mục | Trạng thái |
|---|---|
| `video.generate` hợp đồng công khai | **IMPLEMENTED · VERIFIED_LOCAL** |
| Ràng buộc theo model + chặn trước tiền | **IMPLEMENTED · VERIFIED_LOCAL** |
| Nối chuỗi artifact → job | **IMPLEMENTED · VERIFIED_LOCAL** |
| Đo thời lượng khi nối chuỗi | **VERIFIED_LOCAL** |
| Số công bố từ một nguồn chân lý | **IMPLEMENTED · VERIFIED_LOCAL** |
| Ba cửa ra trang công khai | **IMPLEMENTED · VERIFIED_PRODUCTION** |
| Bốn tool đang phục vụ | **VERIFIED_PRODUCTION** |
| Rollback | **VERIFIED_LOCAL** |
| Cổng chất lượng đầy đủ | **PASS** |
| Canary Seedance | **BLOCKED_EXTERNAL** |
| Recipe A đầu-tới-cuối thật | **BLOCKED_EXTERNAL** |
| Codex bridge — kỹ thuật | **DEFERRED** |
| Codex bridge — thương mại | **BLOCKED_POLICY** |
| 4 tham chiếu media Seedance | **DEFERRED** |
