# P00 — MA TRẬN KHOẢNG TRỐNG

Cột: **HIỆN CÓ** / **BẰNG CHỨNG** / **THAM CHIẾU** / **THIẾU GÌ** /
**GIỮ·MỞ·XÂY·HOÃN** / **RỦI RO** / **PHỤ THUỘC**.

`GIỮ` = không đụng · `MỞ` = mở rộng thứ đã có · `XÂY` = mới · `HOÃN` = ghi là
DEFERRED, **không** tính PASS (`04_ACCEPTANCE_SCORECARD.md`).

---

## A. Hội thoại lõi — phần lớn **GIỮ**

| # | Hạng mục | Hiện có | Bằng chứng | Thiếu | Phân loại | Rủi ro | Phụ thuộc |
|---|---|---|---|---|---|---|---|
| A1 | Cây hội thoại, sửa/tạo-lại/nhánh/lá đang xem | ✅ đủ | `tables.py` `parent_id`+`current_leaf_id`; `test_617` | — | **GIỮ** | 🟢 | — |
| A2 | Khối typed (text/reasoning/image/audio/file/status/error) | ✅ đủ | `tables.py:LOAI_KHOI` | 4 loại mới: `tool_call`, `tool_result`, `approval`, `artifact` | **MỞ** (thêm phần tử vào mảng cũ) | 🟢 bộ hiển thị cũ bỏ qua loại lạ | A5 |
| A3 | Stream text + reasoning + Dừng + nối lại | ✅ đủ | `luot.py:196`; `_p_luot.py:128`; `test_623` | — | **GIỮ** | 🟢 | — |
| A4 | Reload dựng lại sự thật từ CSDL | ✅ đủ | `su_kien.nen_ghi` (1 s/200 ký tự); `snapshot()`; `test_618` | nhịp ghi cho `run` nhiều bước | **MỞ** | 🟡 | B2 |
| A5 | Bộ hiển thị bỏ qua loại khối lạ | ⚠️ **chưa kiểm** | `ThongDiepView.tsx` | phép kiểm chốt "khối lạ ⇒ không vỡ" | **XÂY** (test) | 🔴 **điều kiện để hội thoại cũ không vỡ** | — |

## B. Điều phối tool — **XÂY**, đây là trọng tâm V3

| # | Hạng mục | Hiện có | Bằng chứng | Thiếu | Phân loại | Rủi ro | Phụ thuộc |
|---|---|---|---|---|---|---|---|
| B1 | `text.chat` nhận `tools`, trả `tool_calls` | ✅ **đã có** | `ltt_llm/manifest.py:208,213` | — | **GIỮ** | 🟢 | — |
| B2 | Runtime chuẩn hoá `tool_call.delta` | ✅ **đã có** | `luong.py:475-477` | gộp mảnh (aggregate) | **MỞ** ở phía ChatLTT | 🟡 | P01 kịch bản 15 |
| B3 | Ước token **có tính** khối `tools` | ✅ **đã có** | `luong.py:123-125` | — | **GIỮ** | 🟢 | — |
| B4 | ChatLTT **gửi** `tools` | ❌ | `luot.py:223` chỉ 3 khoá | phép chiếu registry→schema + gửi | **XÂY** | 🟡 | B5 |
| B5 | Phép chiếu tool động từ registry đã duyệt | ⚠️ một nửa | `chinh_sach.CONG_CU_CHO_PHEP` là allowlist **hiển thị**, không phải schema | dùng lại `catalog.project_tool` + lớp chính sách | **MỞ** | 🟡 chiếu thừa = lộ năng lực nội bộ | B4 |
| B6 | Giữ `tool_call.delta` | ❌ | `su_kien.py:72` `pass` | ghi vào `chatltt_step` | **XÂY** | 🔴 | C1 |
| B7 | Thi hành tool phía máy chủ + kết quả có cấu trúc | ❌ | — | executor + chuẩn hoá kết quả | **XÂY** | 🔴 | B5, D1 |
| B8 | **Trả kết quả về model, vòng nhiều lượt** | ❌ | `luot.chay()` gọi `mo_luong` **đúng một lần** | vòng lặp + máy trạng thái | **XÂY** | 🔴 **hạng mục lõi** | R1, B7 |
| B9 | Trần bước / chặn trùng / chặn lặp | ❌ | — | 8 vòng · 12 lời gọi · băm `(tên, đối số chuẩn hoá)` · trần credit/lượt | **XÂY** | 🔴 không có = vòng lặp đốt tiền | B8 |
| B10 | `parallel_tool_calls` | ❌ | **tắt mặc định** ở llama.cpp ([U] `function-calling.md:24`) | gửi cờ trong thân | **XÂY** | 🟡 P01 không gửi cờ ⇒ đo nhầm | P01 |
| B11 | Đối số/kết quả tool là **dữ liệu không tin được** | ❌ | — | validate schema trước thi hành; injection trong kết quả không đổi được chính sách | **XÂY** | 🔴 bảo mật | P02 §ranh giới tin cậy |

## C. Trạng thái bền + duyệt (HITL) — **XÂY**

| # | Hạng mục | Hiện có | Bằng chứng | Thiếu | Phân loại | Rủi ro | Phụ thuộc |
|---|---|---|---|---|---|---|---|
| C1 | Mô hình `run` / `step` | ❌ | `chatltt_execution` = **một lần gọi model** | `chatltt_run` + `chatltt_step` (+ `run_id` trên execution) | **XÂY** | 🔴 | P02 |
| C2 | Duyệt **bền** qua F5/đóng tab/tiến trình khác/**restart dịch vụ** | ❌ | xác nhận nằm giữa hai POST ở trình duyệt (`TaoMedia.tsx`) | `chatltt_approval` + unique index trên `step_id` | **XÂY** | 🔴 **cửa tiền** | C1 |
| C3 | Chính sách người dùng: luôn hỏi / tự chạy dưới X credit / không bao giờ | ❌ | — | bảng + cưỡng chế phía máy chủ | **XÂY** | 🟡 | C2, §6b-5 |
| C4 | Chống duyệt-2-lần · thi-hành-2-lần · thu-2-lần · tiếp-tục-2-lần | ⚠️ một phần | `job_submit` có `dedupe_key`; `credit.quyet_toan` idempotent | unique index + idempotency cho **duyệt** và **vòng model** | **MỞ** | 🔴 | C1, C2 |
| C5 | Model **không thể** tự cho phép tiêu tiền | ✅ theo cấu trúc hiện tại | model chưa hề được gọi tool | phải **giữ** bất biến này khi mở vòng lặp | **GIỮ** (thành phép kiểm) | 🔴 | C2 |

## D. Tiền — **MỞ**, và có một bất ngờ

| # | Hạng mục | Hiện có | Bằng chứng | Thiếu | Phân loại | Rủi ro | Phụ thuộc |
|---|---|---|---|---|---|---|---|
| D1 | Báo giá theo bảng giá chính tắc, báo giá **lại** khi chốt | ✅ đủ | `tao_media.py:135`; `runtime_noi_bo/job.bao_gia` | mở cho tool do **model** gọi | **MỞ** | 🟡 | C2 |
| D2 | Giữ chỗ → quyết toán → hoàn, không thu quá phần giữ | ✅ đủ | `thanh_toan`; `credit.quyet_toan` (Q84) | — | **GIỮ** | 🟢 | — |
| D3 | Tiền của **một lượt** (N gọi model + M job) | ❌ | 3 cột vô hướng trên `chatltt_execution` | tổng hợp theo `run_id` | **XÂY** | 🔴 giao diện nói sai chi phí | C1 |
| D4 | 🔴 **Làm tròn C1 trên lượt agentic** | ⚠️ **đúng luật nhưng sai dạng tải** | `thanh_toan.py` §C1: làm tròn LÊN mỗi lượt gọi, **tối thiểu 1 credit** | 8 vòng × 0,285 cr thật = 2,3 cr, **thu 8 cr** — gấp 3,5 lần | **quyết định P02** (§6b-4) | 🔴 khách trả cho 8 khi hỏi 1 | — |
| D5 | Bận ≠ hỏng, không thu tiền | ✅ đủ | `DangBan`; `hoan_luot`; `PROVIDER_REJECTED` | áp cho tool step | **MỞ** | 🟢 | — |

⭐ **D4 là phát hiện của P00 mà gói prompt không có.** `thanh_toan.py` tự ghi
cái giá của C1 — *"lượt gọi nhỏ trả nhiều hơn giá niêm yết, tới ~3,3 lần"* —
lúc "lượt gọi nhỏ" còn là ngoại lệ. V3 biến nó thành **thường lệ**. Và cùng tệp
đó để ngỏ C2 kèm câu *"chỉ đụng module này, không đụng `gia_token.py`"* — ranh
giới ấy được vẽ sẵn cho đúng hôm nay.

## E. Đa phương thức trong hội thoại — **MỞ**

| # | Hạng mục | Hiện có | Bằng chứng | Thiếu | Phân loại | Rủi ro | Phụ thuộc |
|---|---|---|---|---|---|---|---|
| E1 | Sinh ảnh qua `image.ltt` | ✅ (người dùng bấm) | `tao_media.py` | thành **tool model gọi được**; kết quả **trả về model** | **MỞ** | 🟡 | B8, C2 |
| E2 | Sửa ảnh (`image.edit`) | ❓ **chưa biết backend có không** | — | kiểm năng lực THẬT trước khi khai | **XÂY hoặc HOÃN** | 🔴 hứa tính năng không có | P05 |
| E3 | Vision: ảnh vào, nhiều ảnh, sở hữu | ✅ đủ | `anh_vao.py`; `dung_ngu_canh(doc_anh=…)`; `test_633` | tham chiếu **ảnh model vừa tạo** bằng id artifact | **MỞ** | 🟡 ngữ cảnh vision 131K chạm trần sớm trong vòng nhiều bước | E1 |
| E4 | Đọc to + sinh giọng qua `speech.ltt` | ✅ đủ | `chon_giong.py`; `tao_media` | thành tool | **MỞ** | 🟢 | B8 |
| E5 | Nói-sang-nói thời gian thực | ❌ | backend không có | — | **HOÃN** | — | — |
| E6 | Tham chiếu artifact ổn định (id, không đoán tên tệp) | ❌ | khoá kho là chuỗi đường dẫn | id artifact + phiên bản | **XÂY** | 🟡 | P08 |

## F. Làn B — khung, chi tiết viết sau khi làn A đóng

| # | Hạng mục | Phân loại | Ràng buộc LTT đã biết |
|---|---|---|---|
| F1 | Tệp: PDF/DOCX/TXT/MD/CSV/XLSX/PPTX/code | **XÂY** | Cloudflare **100 MB**/request; parse dài ⇒ job |
| F2 | Tri thức/RAG + trích dẫn, 3 phạm vi (lượt/hội thoại/project), **không trộn với memory** | **XÂY** | — |
| F3 | Tìm kiếm web + fetch + trích dẫn | **XÂY** | 🔴 injection từ web là kịch bản kiểm bắt buộc; SSRF |
| F4 | Calculator tất định | **XÂY** | dễ nhất — làm đầu tiên ở P03 làm tool thật |
| F5 | Sandbox code | **XÂY nếu chứng minh được sandbox** | 🔴 không chứng minh được ⇒ **HOÃN**, không làm nửa vời |
| F6 | MCP (adapter về hợp đồng tool LTT) | **XÂY** | ⛔ MCP **không** được vòng qua chính sách/tiền/sở hữu của LTT |
| F7 | OpenAPI Actions | **XÂY nếu tái dùng được đúng đường chuẩn hoá của F6** | — |
| F8 | Memory 3 tầng, người dùng thấy và sửa được | **XÂY** | ⛔ không âm thầm lưu mọi thứ |
| F9 | Projects · Custom Agents · Skills | **XÂY** | mỗi thứ là một bề mặt quyền mới ⇒ test ACL + cách ly + thứ tự ưu tiên chỉ dẫn |
| F10 | Deep Research (workflow bền) · Artifacts có phiên bản · việc nền | **XÂY** | dùng `job_runner`+`leases`, **không** hàng đợi thứ hai |
| F11 | Tool video · browser/computer use · hành động tự trị theo lịch | **HOÃN** | ghi là DEFERRED, không tính PASS |

## G. Hạ tầng phục vụ — không phải mã ChatLTT nhưng chặn nó

| # | Hạng mục | Trạng thái | Bằng chứng | Rủi ro |
|---|---|---|---|---|
| G1 | **Một suất LLM toàn nền tảng** | `admission_slots=1` + `--parallel 1` | `manifest.py:197`; yaml | 🔴 **R1** — vòng N bước = N lần giành/nhả; mất suất giữa chừng |
| G2 | KV `q4_0` cả hai hồ sơ | yaml | [U] `function-calling.md:333` gọi đích danh `-ctk q4_0` "substantially degrade tool calling" | 🔴 **R3** — và 200K đã chốt ⇒ không đổi được |
| G3 | Handler Native hay Generic | ❓ **chưa ai biết** | [U] `function-calling.md:20`; họ Qwen chia đôi ở bảng dòng 77-83 | 🔴 nguyên nhân thứ hai, độc lập với G2 |
| G4 | Template vá cộng đồng v22.3 | đang chạy | yaml [C] | 🟡 5 lời hứa chưa ai kiểm, có "agentic stalling" |
| G5 | MTP `--spec-draft-n-max 2` | đang chạy | yaml | 🟡 A/B chẩn đoán ở P01 |
| G6 | Máy B tự khởi động lại sau 01:00 | Windows Update | ghi nhớ vận hành | 🟡 lô đo phải < 3 giờ + checkpoint |

---

## H. Tổng kết phân loại

| | Số hạng mục |
|---|---|
| **GIỮ** (không đụng) | 7 |
| **MỞ** (mở rộng thứ đã có) | 12 |
| **XÂY** (mới) | 21 |
| **HOÃN** (DEFERRED, không tính PASS) | 3 + F11 |
| **quyết định chờ chủ dự án** | 1 (D4) |
| **chưa biết, phải đo** | 3 (E2, G3, + M-2 mức độ) |

⭐ Tỉ lệ GIỮ+MỞ so với XÂY (19 : 21) là bằng chứng định lượng cho kết luận của
`01_RESEARCH_BASELINE.md`: *"execution primitives phần lớn đã có; thiếu
orchestration state machine / tool loop / persisted approval. **Không có bằng
chứng cần rewrite core**."* P00 xác nhận câu đó bằng mã, không bằng niềm tin.
