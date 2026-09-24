# P5c / Task 3 — OAuth2 Google qua `/hooks/*`

**Nguồn.** `authlib` **1.8.0** (cài trong lượt này, thoả `≥ 1.6.9`).
`authlib.oauth2.rfc7636.create_s256_code_challenge` (PKCE S256, RFC 7636 §4.2)
và `authlib.oauth2.client.OAuth2Client.create_authorization_url` (RFC 6749
§4.1.1). ⛔ Không tự tính challenge: base64url **không đệm** — cái đệm `=` là
chỗ người ta sai, và sai thì Google trả `invalid_grant` không nói vì sao.

🔴 **Đính chính một lựa chọn của plan.** ⛔ Không dùng
`authlib.integrations.httpx_client`: bản 1.8.0 in
`AuthlibDeprecationWarning: The httpx module is deprecated; please use httpx2
instead` (đo trong lượt này). Nối vào một lớp tích hợp đang bị khai tử là tự
hẹn một lần di trú. Lượt POST tới điểm token đi thẳng bằng `httpx` (đã là phụ
thuộc); phần phân tích phản hồi là RFC 6749 §5.1 — một JSON phẳng.

**Ba chỗ mất tiền, đã viết vào mã.**

1. `access_type=offline` + `prompt=consent` — thiếu cặp này Google chỉ phát
   `refresh_token` ở lần cấp quyền **đầu**, và lỗi chỉ lộ một giờ sau.
2. Lượt làm mới **không** trả lại `refresh_token` ⇒ `_hop_nhat` giữ cái cũ.
3. `invalid_grant` là **dứt điểm** (token bị thu hồi, hoặc app còn Testing —
   refresh token hết hạn 7 ngày) ⇒ `meta.can_ket_noi_lai` + thu hồi, ⛔ không
   thử lại im lặng.

`state` lưu **băm**, dùng **một lần**, hạn 10 phút; PKCE verifier mã hoá qua
`secretbox`. Route: `/hooks/oauth/google/bat-dau` (vẫn đòi đăng nhập) và
`/callback` (công khai — thứ bảo vệ nó là `state`, không phải cookie).

**Việc thủ công của chủ dự án:** `tools/wizard_oauth_google.sh` (skill
`wizard`, 6 chặng, `bash -n` sạch). ⛔ Claude không tự tạo tài khoản, không tự
nhập bí mật.

```
ĐỎ    13 failed in 51.53s
XANH  13 passed in 51.93s     tests/test_2922_oauth_google.py
```

**Chưa làm được.** App OAuth Google chưa tồn tại (việc của chủ dự án) ⇒ ⛔
**chưa có lượt uỷ quyền THẬT nào**; điểm token được tiêm qua `goi_token`.
`youtube.upload` là scope nhạy cảm, cần Google xác minh mới lên Production.
