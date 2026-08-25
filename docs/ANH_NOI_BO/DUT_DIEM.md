# `ltt_image` — kế hoạch dứt điểm

**2026-08-25.** Nối tiếp `TIEP_QUAN_H37.md` §4, không thay nó. Tài liệu kia ghi
bốn đợt A–D; tài liệu này chốt **cái gì còn lại thật** sau khi đường ảnh đã chạy
lần đầu từ một máy khách.

---

## 0. "Dứt điểm" nghĩa là gì với `ltt_image`

`TIEP_QUAN_H37.md` viết: *"Đường găng còn lại: chỉ còn nghiệm thu G10 — một job
ảnh đi thật từ ngoài vào qua `/api/v1`."*

> **Việc đó đã xong từ 24/08.** Phần còn lại không phải "làm cho nó chạy" mà là
> **làm cho một người lạ dùng được nó mà không cần hỏi ai** — và 25/08 chứng minh
> hai việc đó khác nhau thật.

---

## 1. C4 — đã đóng **24/08**; 25/08 thêm một phép thử khác hẳn

⚠️ **ĐÍNH CHÍNH.** Bản đầu của tài liệu này viết "C4 đóng hôm nay". Sai:
`APP_API_COVERAGE_FINAL.md` §4 ghi rõ `image.ltt` đã nghiệm thu **bằng tiền thật
ngày 24/08** qua `tools/nghiem_thu_anh_e2e.py` — ba lượt, 120 giây, credit 3/3.
`TIEP_QUAN_H37.md` để dòng C4 ở trạng thái chưa xong, và tôi đọc dòng đó rồi
tưởng mình vừa đóng nó.

⭐ Vậy 25/08 thêm được gì? Một phép thử **khác loại**, và chính cái khác đó tìm ra
lỗi: `nghiem_thu_anh_e2e.py` do **ta** viết, chạy trên **máy A**, và biết trước
hình dạng phản hồi. Phép thử hôm nay chạy trên **máy khác**, qua Cloudflare, bằng
thư viện chuẩn, và **chỉ biết những gì tài liệu nói** — nên nó vấp đúng chỗ khách
sẽ vấp.

Chạy trên **VM 192.168.2.136** (máy Windows sạch, ngoài máy chủ), qua
**Cloudflare**, bằng **thư viện chuẩn** — không SDK của ta, không import gì từ
`platform_core`. Kịch bản: `tools/khach_gia_lap_anh.py`.

| Bước | Kết quả |
|---|---|
| `GET /me` · `/credits/balance` · `/tools` | `200` · số dư 1218 · thấy `image.ltt` |
| `POST /quotes` | `200`, báo giá **3 credit** |
| `POST /jobs` | `201`, job `fbefed09-…` |
| `GET /jobs/{id}` | `succeeded` sau **138 giây** |
| `GET /artifacts/{id}` → tải | **5.583.155 byte** PNG |

Đối soát sổ credit bằng tay:

```
14:33:13   -3  hold     giu cho job fbefed09
14:35:28    0  settle   quyet toan job fbefed09: giu 3, thu 3, provider 3, variance 0
số dư: 1218 → 1215
```

Báo giá nói 3, giữ 3, thu 3, sai lệch 0. **Khớp tuyệt đối.**

⭐ Và nó chứng minh đúng điều `TIEP_QUAN_H37.md` nói là test không thay được:
`TestClient` và loopback bỏ qua Cloudflare, bỏ qua DNS, và bỏ qua việc khách chỉ
có đúng hai thứ — một khoá và trang tài liệu.

---

## 2. 🔴 P0 — LỖI ĐANG SỐNG, tìm ra ở đúng lượt gọi thật đầu tiên

### P0-1. Tài liệu nói sai chỗ lấy ảnh

Trang tham chiếu công bố `output_schema`:

```
image_keys   artifact[]   "Trường kiểu artifact trả về một id;
                           đổi id lấy đường tải ngắn hạn ở /api/v1/artifacts"
```

Phản hồi **thật** của job:

```json
"outputs": [{"id": "fbefed09-….image_keys.0", "field": "image_keys", "index": 0}],
"result":  {"prompt": "A calico cat sleeping on a windowsill…"}
```

⛔ Khách đọc tài liệu sẽ tìm `result.image_keys`, **không thấy**, và dừng lại —
sau khi job đã chạy xong và tiền đã bị thu. Kịch bản của tôi vấp đúng chỗ này và
thoát với mã 1. Job thành công, tiền mất, ảnh có — mà mã của khách không lấy được.

*Đạt khi:* trang tham chiếu nói rõ artifact nằm ở `outputs[]`, kèm ví dụ lấy id;
và `tools/khach_gia_lap_anh.py` chạy trọn vòng **không sửa gì**.

### P0-2. Không ai bên ngoài biết ta bán API tạo ảnh

Đo trên `/huong-dan` (25 KB, trang công khai duy nhất nói về tích hợp):

```
ltt_llm  16 lần   ·   codex 24 lần   ·   claude 39 lần
image.ltt  0 lần   ·   uploads 0 lần   ·   quote 0 lần
```

Ta đang **bán hai thứ và chỉ giới thiệu một**. Người chưa đăng ký thấy giá ảnh ở
`/gia-api` rồi hết đường: mọi hướng dẫn dùng ảnh nằm sau đăng nhập.

⚠️ Đây **không** mâu thuẫn với chốt "`/developers/*` sau đăng nhập". Danh mục và
playground là của tài khoản; nhưng *"ta có bán tạo ảnh qua API, và đây là ba bước
gọi"* là thứ trả lời câu **"có đáng mua không"**.

*Đạt khi:* `/huong-dan` có một mục tạo ảnh, công khai, với ví dụ `quote → job →
artifact` chép chạy được và nói rõ ba chế độ + điều kiện `image_key`.

---

## 3. 🟡 P1 — nợ từ kế hoạch cũ

| # | Việc | Ghi chú |
|---|---|---|
| P1-1 | **C5**: điền một dòng vào mục 4 của `APP_API_COVERAGE_FINAL.md` | `test_212` đọc bảng đó như dữ liệu và so hai chiều với registry |
| P1-2 | Deploy thay đổi hợp đồng 25/08 (`x-ltt-only-when` + sửa câu nói sai *"ignored for t2i"*) | đã xong mã, đã chốt ảnh vàng + bản chuẩn + CHANGELOG; **chưa deploy** |
| P1-3 | Ghi **138 giây** vào tài liệu như số đo tham khảo | khách cần con số để đặt timeout và quyết định polling hay webhook |

---

## 4. ⏸️ P2 — cần chủ sản phẩm

| # | Việc | Vì sao cần người |
|---|---|---|
| P2-1 | **B2**: chạy dự án video cùng lúc, xác minh cổng render báo **bận** (`429`/`503`) chứ không báo **hỏng** | ba hộ dùng chung một card (D-037). Không đóng được bằng một lô đo của riêng ta |
| P2-2 | Một khách thật trả tiền | |

⛔ **B2 là chốt an toàn tiền, không phải chốt hiệu năng.** Nếu cổng báo hỏng thay
vì báo bận, `api_pool` sẽ cooldown rồi **`disable` sau 5 lần** — và một tối chạy
video sẽ **tự tắt vĩnh viễn model nhà** (D-005). Triệu chứng khi đó: `image.ltt`
biến mất khỏi `/tools` mà không ai đụng vào cấu hình.

---

## 5. Thứ tự thi hành

```
P0-1  sửa tài liệu outputs[]        ← lỗi đang sống, khách vấp ngay
P0-2  mục tạo ảnh trên /huong-dan   ← đang mất khách trước cả khi họ đăng ký
P1-2  deploy                         ← gộp hai việc trên vào cùng một lần
P1-1  C5                             ← rẻ, và test_212 canh nó
P1-3  ghi 138 giây
P2    khi chủ sản phẩm sắp xếp được
```

⭐ P0-1 xếp trên P0-2 dù P0-2 nghe "kinh doanh hơn": một khách **đã** trả tiền mà
không lấy được ảnh là thiệt hại đã xảy ra; một khách chưa biết ta bán thì chưa
mất gì.

---

## 6. Cái **không** làm

| Không làm | Vì sao |
|---|---|
| Rút ngắn 138 giây bằng cách hạ số bước | D-054 đã đóng: giữ 50 bước, có 60 cặp so mù đứng sau |
| Cửa đồng bộ cho ảnh | 138 giây > trần 100 giây của Cloudflare. Không phải lựa chọn thiết kế, là một bức tường |
| Cascade sang Gemini khi máy B bận | D-010: khách trả cho `image.ltt` mà nhận Gemini là **bán sai hàng** |
| Định vị model nhà là "đẹp hơn" | G6b: thua 14–4 ở phần có nghĩa. Ảnh có chữ thì trả lời Gemini, và đó là câu cuối |
| Thêm lô đấu Gemini | D-046 đã bỏ hẳn đối chứng ngoài |
