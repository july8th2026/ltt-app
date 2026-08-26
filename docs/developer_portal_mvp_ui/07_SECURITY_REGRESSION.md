# 07 — Hồi quy bảo mật

Không phải QA thị giác. Mỗi dòng dưới đây là một phép **chạy thật**: hoặc
`pytest`, hoặc một lượt trên trình duyệt có gọi `/api/v1` và đọc mã HTTP trả về.

Bộ chạy trên trình duyệt: `tools/qa/dev_portal_golden.js` — **39 PASS, 0 FAIL**.

## 1. Chuỗi bí mật hiện MỘT LẦN

| Chốt | Kiểm bằng | KQ |
|---|---|---|
| tạo khóa → plaintext hiện trên chính phản hồi đó | trình duyệt, `.dev-mat code` khớp `^ltt_tk_` | ✅ |
| tải lại trang → plaintext **biến mất** | trình duyệt, tìm chuỗi trong HTML sau khi tải lại | ✅ |
| nửa công khai (`key_id`) vẫn còn | trình duyệt | ✅ |
| đổi bí mật → chuỗi **mới**, khác chuỗi cũ | trình duyệt | ✅ |
| máy chủ không tái tạo được | `test_179::test_a_reloaded_key_cannot_reproduce_its_token` | ✅ |
| pepper không bao giờ vào hàng CSDL | `test_179::test_pepper_is_never_written_to_the_row` | ✅ |

⚠️ **Hình dạng markup là hợp đồng.** `test_191` tìm
`<code>(ltt_sk_[^<]+)</code>` để chứng minh plaintext chỉ sống ở phản hồi tạo.
Khối mới `.dev-mat` **giữ nguyên `<code>`** — nếu đổi thành `<span>` thì bằng
chứng đó biến mất mà test vẫn xanh trong một thời gian.

**Không** thêm: `localStorage`, `sessionStorage`, cookie, route đọc lại, tham số
URL, thuộc tính `data-*`. Kiểm bằng `grep` trên `dev_keys.html` +
`dev_webhooks.html`: 0 kết quả.

## 2. Đổi bí mật và thu hồi — chạy thật, đọc mã HTTP

```
tao khoa test        -> ltt_tk_5314b52c…      GET /api/v1/tools  200
doi bi mat           -> ltt_tk_dc47a47f…
  chuoi CU                                    GET /api/v1/tools  401  ✅
  chuoi MOI                                   GET /api/v1/tools  200  ✅
thu hoi
  chuoi MOI                                   GET /api/v1/tools  401  ✅
bang noi trang thai: "revoked", lop `dev-tt loi`               ✅
```

⭐ **Một hành vi sản phẩm thật mà việc này làm lộ ra:** `rotate` đổi **luôn cả
`key_id` công khai**, không chỉ chuỗi bí mật
(`platform_core/public_api/keys.py::rotate` — đổi tại chỗ để phạm vi, tên và
lịch sử ở nguyên một hàng). Hệ quả cho vận hành: **một ticket hỗ trợ trích mã
khóa cũ sẽ không còn khớp hàng nào**, và bộ lọc `key_id` ở trang Hoạt động cũng
đổi theo.

Trang **có** nói mã mới ra ("Mã khóa công khai: …"), nhưng **không** nói nó đã
thay thế mã cũ. Xem "Rủi ro đã biết" ở tài liệu 09.

*(Tôi đã tự chẩn đoán nhầm chỗ này một lần: bộ kiểm tìm hàng theo mã CŨ sau khi
đổi, không thấy, và tôi suýt coi đó là lỗi giao diện. Là lỗi của phép kiểm.)*

## 3. CSRF

| | |
|---|---|
| 7/7 POST gọi `verify_csrf_token` trước mọi việc khác | đọc mã, không đổi |
| mọi form trong template có `<input name="csrf_token">` | `grep`: 12 form, 12 token |
| POST không token thì **không đổi gì** | `test_191::test_a_post_without_a_csrf_token_changes_nothing` ✅ |
| ghi vẫn cần token | `test_197::test_writes_still_need_a_csrf_token` ✅ |

Không form nào bị đổi sang `fetch` mang bearer. Portal vẫn là bề mặt phiên.

## 4. Quyền sở hữu theo người thuê

`test_197::test_no_section_shows_another_account_anything` đi qua **mọi**
section: ✅
`test_179::test_one_customer_cannot_reach_another_customers_key`: ✅
`test_191` (Alice không thu hồi được khóa của Bob): ✅

Không truy vấn nào bị đổi. Việc này chỉ chạm template và CSS.

## 5. Live / Test không trộn nhau

Khóa test bắt đầu `ltt_tk_`, không chạm sổ credit, chỉ thấy job test.
`test_204_sandbox`: ✅ · lượt chạy thật ở trên dùng **khóa test** nên **không
một credit nào bị tiêu** trong toàn bộ QA.

Bảng khóa vẫn phân biệt Live/Test bằng chip riêng.

## 6. Báo giá không tiêu tiền

```
so du truoc khi mo phong gia : 4.820
so du sau                    : 4.820   ✅
```

`pricing.simulate` không đúc quote token, không ghi sổ. Trang **nói ra** điều đó
(kiểm bằng regex trên nội dung trang): ✅

## 7. Nhật ký request — chỉ giữ bộ xương

| Chốt | KQ |
|---|---|
| bảng nhật ký **không** lộ body request/response | ✅ |
| trang chi tiết **không** lộ body | ✅ |
| chính sách ghi log **không bị đổi** | ✅ — không sửa dòng Python nào |

Trang hiển thị đúng 12 trường `ApiRequestLog` đã có. Không thêm cột nào cần dữ
liệu backend chưa lưu.

## 8. Webhook

| | |
|---|---|
| ngữ nghĩa ký, cửa sổ chống phát lại, ân hạn secret cũ | **không đổi** — không sửa Python |
| secret hiện một lần, nay dùng chung `.dev-mat` | ✅ |
| trần chống lạm dụng của `resend` | không đổi |
| `test_202_webhook_console` | ✅ |

Đã **thêm** một câu ở hộp xác nhận: đổi secret **không** làm mất sự kiện, vì
secret cũ còn được ký kèm trong thời gian ân hạn. Đó là thông tin quyết định
khách có dám bấm hay không, và trước đây nó chỉ nằm ở trang tài liệu.

## 9. Không ví dụ nào chứa khóa thật

Quét `/developers/cli` bằng regex `ltt_(sk|tk)_[A-Za-z0-9_-]{10}` trên nội dung
trang: **0 kết quả** ✅. Mọi ví dụ dùng `$LTT_API_KEY`.

## 10. Credential của nhà cung cấp

`test_179::test_the_developer_key_domain_never_touches_provider_credentials`: ✅
Không tệp nào trong `server/routes/developer/` import `platform_core.api_keys`,
và không template `dev_*` nào nhắc tới nó.

## 11. Xuất dữ liệu

`test_211_data_governance`: ✅ · chuỗi bí mật **không** nằm trong tệp xuất (máy
chủ không lưu nó ở đâu, nên không có gì để xuất).

---

## Tổng

**`pytest` 15 tệp hợp đồng khu API: 299 passed, 4 skipped, 0 failed.**

```
test_179  test_191  test_197  test_199  test_200  test_201  test_202
test_203  test_207  test_211  test_299  test_300  test_301  test_302  test_303
```

**Không một dòng Python nào bị sửa trong lượt này.** Thay đổi nằm ở 20 template,
`ltt.css`, và `messages.po`. Bề mặt bảo mật không đổi vì mã thi hành nó không đổi.
