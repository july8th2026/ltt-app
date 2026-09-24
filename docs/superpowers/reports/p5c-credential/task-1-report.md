# P5c / Task 1 — Kho credential: bảng + migration + `MultiFernet`

**Nguồn.** `cryptography` `fernet.rst`, lớp `MultiFernet`: ghi luôn bằng khoá
đầu danh sách, đọc thì thử lần lượt, `rotate()` giải bằng khoá bất kỳ rồi mã
hoá lại bằng khoá đầu **giữ nguyên dấu thời gian**. Đúng ba thứ một lần xoay
khoá cần ⇒ ⛔ không tự viết vòng thử khoá. Spec §9.1.

**Đã làm.**

- `platform_core/secretbox.py` → `MultiFernet`. Khoá đời cũ đọc từ
  `LTT_TOKEN_ENCRYPTION_KEYS_CU` (hoặc `_FILE`). **Dẫn xuất khoá KHÔNG đổi**
  (`sha256(material + _SALT)`) nên mọi hàng ghi trước 24/09 đọc được y nguyên —
  một "nâng cấp" làm mất dữ liệu cũ thì không phải nâng cấp.
- `models.py`: `credential`, `credential_nhat_ky`, `oauth_state`.
- Migration `9c1e4b77a205` (`down_revision` `c4a17f9b6d20`).
  `python -m alembic heads` ⇒ **`9c1e4b77a205 (head)`** — đúng một dòng.
- `platform_core/credential.py`: **một cửa duy nhất** vào bí mật. `kiem_ref`
  (validator, không giải mã) · `liet_ke` (API, chỉ `preview` + `meta`) ·
  `lay_de_dung` (job, hàm **duy nhất** trả bản rõ, khoá hàng `FOR UPDATE`,
  commit ngắn sau khi làm mới). Thu hồi = **xoá** `bi_mat_ma_hoa`. `meta` chặn
  khoá bí mật **cơ học** (`META_CAM`), không bằng lời dặn.
- `governance.STORES`: hai bảng EVIDENCE (hàng ở lại sau thu hồi — nó là bằng
  chứng run nào dùng khoá nào), `oauth_state` OPERATIONAL 1 ngày + sweep nối
  vào `job_runner._don_du_lieu_het_han`.
- `tools/xoay_khoa_credential.py`: mặc định chỉ đếm; từ chối khi chỉ có một
  khoá đang nạp (dấu hiệu bước 1 chưa làm).

```
ĐỎ    13 failed in 72.54s
XANH  13 passed in 54.03s     tests/test_2920_credential_kho.py
      23 passed in 25.13s     tests/test_211_data_governance.py
```

**Chưa làm được.** API `/agent/api/v3/credentials` (spec §9.2) — nó sống trong
`apps/agent/routes/`, **làn p8 sở hữu**. Kho + hàm đã sẵn; chỉ thiếu bốn route
mỏng. ⛔ Không chạm.
