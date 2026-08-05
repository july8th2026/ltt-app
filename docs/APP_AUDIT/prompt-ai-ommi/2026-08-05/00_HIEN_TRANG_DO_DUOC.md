# 00 — Hiện trạng đo được: nguồn vs app hiện tại

**Mã:** LTT-AQA `AUDIT DEEP -- app: prompt-ai-ommi`
**Ngày snapshot:** 2026-08-05
**Môi trường:** fixture cô lập `127.0.0.1:8119`, tài khoản `agent-a@example.com`.
Không chạm production, không dùng dữ liệu người dùng thật.
**Nguồn đối chiếu:** `D:\BOT GEMINI\app\modules\seedance` — **CHỈ ĐỌC**.

## 1. Vì sao phải audit lại

Chủ sản phẩm báo bản codex triển khai "sai hoàn toàn". Audit này không nhận định
theo cảm tính mà đo cả hai bên rồi so.

## 2. Quy mô hai bên (E1 — đếm trực tiếp)

| | Module nguồn | App hiện tại | Tỉ lệ |
|---|---:|---:|---:|
| File Python | 112 | 8 | 7% |
| Dòng code | **29.541** | **1.428** | **4,8%** |
| Router / endpoint | 22 router · 261 endpoint | 1 router · ~20 endpoint | 8% |
| Bảng dữ liệu | **49** | **0 bảng riêng** | 0% |
| Service nghiệp vụ | 33 manager · 16.818 dòng | 1 composer · 86 dòng | 0,5% |
| Adapter provider | 7 · 1.454 dòng | 1 · 114 dòng | 8% |

App hiện tại **không có bảng dữ liệu riêng nào**. Toàn bộ trạng thái nhét trong
một `AppProject` dạng JSON blob.

## 3. App hiện tại thực sự là gì (E3 — browser thật)

Một wizard 5 bước trong **một trang duy nhất**, nền sáng:
`01 Brief → 02 Assets → 03 Director → 04 Board → 05 Export`.

Control Registry đầy đủ (đếm trên DOM, 1366×900):

| Bước | Control có thật | Verdict |
|---|---|---|
| 01 Brief | tên, câu chuyện, mục tiêu, đối tượng, thời lượng, tỉ lệ, ngôn ngữ, 5 preset phong cách, mô tả phong cách riêng | `LIVE` |
| 02 Assets | **đúng 1 nút** `＋ Tài nguyên mô tả` — chỉ thêm được text | `PARTIAL` |
| 03 Director | chọn `Prompt package/Storyboard`, chọn model, `Kiểm tra & xem prompt`, `Báo giá`, `✦ Chạy AI Director` | `LIVE` |
| 04 Board | `Lưới/Danh sách`, cỡ lưới 2x2→4x3, `Tạo frame còn thiếu` | `LIVE` |
| 05 Export | `Tải .md`, `.json`, `.zip` | `LIVE` |
| Dự án | tìm, tạo, nhân bản, lưu trữ, chụp phiên bản, lưu | `LIVE` |

Chất lượng kỹ thuật của phần đã làm là **tốt**: console 0 error/0 warning, không
request nào hỏng, quote/credit đi qua đúng nền tảng. Vấn đề không phải code dở —
vấn đề là **phạm vi**.

## 4. Cái bị thiếu so với cấu trúc vận hành của module

Đây là danh sách năng lực nguồn **không tồn tại dưới bất kỳ hình thức nào** trong
app hiện tại:

| Năng lực nguồn | Quy mô nguồn | App hiện tại |
|---|---:|---|
| Kho tài nguyên (asset group/variant/tag/collection) | 777+381+305+187+178 dòng | `MISSING` — chỉ có text |
| Upload ảnh tài nguyên + thumbnail | 381 + 225 dòng | `MISSING` |
| Prompt Library (snippet/version/ref/sample) | 490 route + service | `MISSING` |
| Meta Director (meta prompt riêng) | 533 dòng | `MISSING` |
| Phong cách (style preset CRUD) | 404 + 205 dòng | `MISSING` — 5 preset cứng |
| Storyboard workspace (scene/anchor/frame/version) | 1.268 route + 407 framework | `PARTIAL` — chỉ là output |
| Tạo ảnh trong app | 1.896 route + 1.373 manager | `MISSING` |
| Chi phí AI | 295 + 321 dòng | `MISSING` |
| Iterations / lịch sử tinh chỉnh | 227 dòng | `MISSING` |
| Collections, tags, trash, folders | ~700 dòng | `MISSING` |
| Dashboard tổng quan | 140 + 77 dòng | `MISSING` |

## 5. Điểm mấu chốt: nguồn KHÔNG hề đa người dùng

`service/scoping.py:32`:

```python
def personal_where(user: User, alias: str = "") -> tuple[str, tuple]:
    """Single-tenant: mọi user lọc theo namespace dùng chung (shared owner)."""
    col = f"{alias}.owner_user_id" if alias else "owner_user_id"
    return f"{col} = ?", (get_master_user_id(),)
```

Hàm này nhận `user` rồi **bỏ qua nó**, luôn trả về namespace của một
`master_user_id` chung. Tầng "PERSONAL" ghi trong docstring là giả. Chỉ
`asset_groups` có ownership thật (mô hình hybrid DD1).

**Hệ quả cho kế hoạch:** yêu cầu "mỗi người kho tài nguyên riêng, prompt meta
riêng" của chủ sản phẩm **không phải là port một tính năng có sẵn** — nó là thứ
nguồn chưa từng có. Đây là phần phải thiết kế mới, và là rủi ro lớn nhất của cả
dự án. Chép nguyên nguồn = bê nguyên lỗ hổng rò rỉ dữ liệu giữa khách hàng.

## 6. Kế hoạch H19 đang nói gì

`H19.3`, `H19.4`, `H19.7` đã tick `[x]`. Đối chiếu với đo đạc ở trên thì các
mục đó chỉ đúng ở **lát cắt dọc hẹp**, không phải năng lực đầy đủ như tên gọi
gợi ý. Cụ thể `H19.6 P4 private library + published Admin catalog` vẫn `[ ]` —
và đó chính là phần chứa toàn bộ Kho tài nguyên / Prompt Library / Meta Director.

Nói cách khác: app hiện tại **đúng với những gì H19.3–H19.4 mô tả**, nhưng đó mới
là khoảng 5% khối lượng. Không có ai "làm sai quy trình" ở đây — cái sai là
**kỳ vọng đã chạy trước tiến độ**, và mục còn lại chưa được làm.

## 7. Bằng chứng

| ID | Cấp | Nội dung |
|---|---|---|
| E1-1 | E1 | Đếm file/dòng/bảng hai bên bằng `wc -l`, `grep -c "CREATE TABLE"` |
| E1-2 | E1 | `service/scoping.py:32-35` — shared namespace |
| E3-1 | E3 | Browser 1366×900: rail 5 bước, Control Registry mục 3, console 0 lỗi |
| E3-2 | E3 | Ảnh `.playwright-cli/ommi-current.png`, `ommi-assets.png` |
| E0-1 | E0 | Ảnh giao diện tham chiếu do chủ sản phẩm cung cấp (chưa có backend chứng minh) |

## 8. Kết luận Gate

| Gate | Verdict |
|---|---|
| G0 Scope | **FAIL** — tên app hứa "studio đầy đủ", thực tế là wizard 5 bước |
| G1 Core Outcome | PASS — brief → prompt package chạy thật, có kết quả |
| G2 Security | PASS ở phạm vi hiện có (owner-scoped AppProject) |
| G3 Credit | PASS — quote/hold/settle dùng nền tảng |
| G4 Honest UI | PASS — không có nút chết |
| G5–G8 | Chưa đủ phạm vi để chấm |

`Q 34 · M 28 · E 82 · BLOCKED bởi G0 Scope`

Điểm thấp **không phải vì chất lượng thi công** mà vì độ phủ năng lực. Phần đã
làm nếu chấm riêng thì khá.
