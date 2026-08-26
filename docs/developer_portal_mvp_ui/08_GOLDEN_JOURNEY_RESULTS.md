# 08 — Kết quả bốn Hành trình Vàng

Chạy trên **Chromium thật**, trên một bản `/developers` có dữ liệu
(`tools/dev_portal_harness.py`, CSDL tạm).

Bộ chạy: `tools/qa/dev_portal_golden.js`
Kết quả: **39 PASS · 0 FAIL**

⛔ **Không tiêu một credit nào.** Đường gọi duy nhất chạm `/api/v1` dùng một
khóa **chế độ test** (`ltt_tk_…`) và tuyến `GET /tools` — không nhà cung cấp nào
được gọi, không bút toán nào được ghi. Đó là lý do bước "gọi thật" nằm được
trong một phép kiểm tự động thay vì phải làm tay.

---

## GJ-A — Tích hợp đầu tiên · 9/9

```
PASS  trang dau chi duong toi khoa
PASS  trang dau chi duong toi "cam vao cong cu"
PASS  tao duoc project
PASS  bi mat hien MOT LAN, trong .dev-mat        — ltt_tk_5314b52…
PASS  khoi bi mat mang role=alert
PASS  trang cam noi base URL
PASS  moi khoi ma co nut chep                    — 9 nut
PASS  KHONG vi du nao chua khoa that
PASS  lot goi API dau tien tra 200               — HTTP 200
```

Chuỗi thật đi được đầu tới cuối: **đăng nhập → `/developers` → tạo project →
tạo khóa → chép chuỗi bí mật → `/developers/cli` → gọi `GET /api/v1/tools` → 200.**

## GJ-B — Hiểu về API và báo giá · 5/5

```
PASS  danh muc liet ke cong cu                   — 3 the
PASS  danh muc noi che do chay
PASS  trang gia dua ra mot con so
PASS  trang gia noi RO day la mo phong / khong tru credit
PASS  bao gia KHONG lam doi so du                — 4.820 -> 4.820
```

Số dư đọc **trước và sau** khi mô phỏng giá, so từng chữ số.

## GJ-C — Vòng đời một khóa · 12/12

```
PASS  tai lai trang thi bi mat BIEN MAT
PASS  nua cong khai cua khoa van con
PASS  tim thay nut doi bi mat cua dung khoa do
PASS  bam duoc nut doi bi mat
PASS  doi bi mat cho ra chuoi MOI
PASS  chuoi CU bi tu choi sau khi doi            — HTTP 401
PASS  chuoi MOI dung duoc                        — HTTP 200
PASS  doi bi mat cung doi luon ma khoa cong khai — 5314b52c68… -> dc47a47fab…
PASS  ma khoa MOI hien ngay tren trang
PASS  tim thay nut thu hoi cua dung khoa do
PASS  bam duoc nut thu hoi
PASS  khoa da thu hoi bi tu choi                 — HTTP 401
PASS  bang noi khoa da thu hoi, bang CHU          — revoked | dev-tt loi
```

⭐ Hàng thứ tám là thứ hành trình này **tìm ra chứ không đi kiểm**: đổi bí mật
đổi **luôn cả `key_id` công khai**. Xem tài liệu 07 §2 và 09 "Rủi ro đã biết".

⚠️ Chốt cuối cố ý đọc **chữ**, không đọc màu: một trạng thái chỉ mã hoá bằng màu
là một trạng thái vô nghĩa với người không phân biệt được màu.

## GJ-D — Gỡ lỗi một tích hợp · 13/13

```
PASS  nhat ky co dong                            — 10 dong
PASS  trang thai la mot nhan co mau ngu nghia
PASS  2xx va 4xx/5xx KHAC lop mau                — ok, canh, loi
PASS  ma loi hien ra khi co
PASS  moi dong mo duoc chi tiet theo request_id
PASS  KHONG lo noi dung request/response
PASS  loc theo request_id thu hep duoc           — 10 dong -> 1 dong
PASS  trang chi tiet co trang thai
PASS  trang chi tiet co do tre
PASS  trang chi tiet KHONG lo body
PASS  trang thai rong dung khuon .dev-trong
PASS  trang thai rong co BUOC TIEP
```

Một dòng nhật ký thật, đọc từ trình duyệt:

```
08-26 13:51:34 │ POST /api/v1/jobs │ 200 │ text.chat │ 812 ms │ 12 │ req_009f4c2a
```

Đủ bảy thứ để trả lời "chuyện gì đã xảy ra": lúc nào · gọi gì · kết quả · mã lỗi
· công cụ · độ trễ · credit · request_id.

Đường một người dẫn từ ticket hỗ trợ đi được: dán `request_id` vào bộ lọc →
10 dòng còn 1 → mở chi tiết.

---

## Ba chốt phủ định — thứ hành trình phải KHÔNG thấy

| | KQ |
|---|---|
| không ví dụ nào chứa khóa thật | ✅ 0 kết quả |
| không trang nhật ký nào lộ body request/response | ✅ bảng và trang chi tiết |
| báo giá không đổi số dư | ✅ 4.820 → 4.820 |

## Hai cái bẫy của chính bộ kiểm, ghi lại để lần sau khỏi mất giờ

1. **`playwright-cli` giữ cookie giữa các lượt chạy.** `/login` chuyển hướng đi
   ngay, ô nhập không bao giờ xuất hiện, và `page.fill` treo 30 giây rồi báo
   "không tìm thấy ô nhập" — một triệu chứng không liên quan gì tới nguyên nhân.
   ⇒ Kiểm `page.$('input[name=username]')` trước, đừng đoán.

2. **`page.on('dialog')` cộng dồn.** Lượt chạy thứ ba thì ba trình xử lý cùng
   tranh một hộp thoại và hai cái sau ném *"Cannot accept dialog which is
   already handled"*, làm cả trang kẹt ở trạng thái modal.
   ⇒ `page.removeAllListeners('dialog')` trước khi gắn.

   Cùng loại: `form.submit()` bên trong `page.evaluate` gây điều hướng, và điều
   hướng **huỷ ngữ cảnh của chính lời gọi đang chạy** — Playwright ném
   *"Execution context was destroyed"*. Bấm nút thật rồi `waitForLoadState`.
