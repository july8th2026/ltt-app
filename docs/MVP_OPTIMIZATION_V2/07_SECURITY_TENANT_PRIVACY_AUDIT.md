# 07 — BẢO MẬT / CÔ LẬP NGƯỜI THUÊ / RIÊNG TƯ / BÍ MẬT

**Ngày:** 2026-08-26 · **Cây:** `3d804ee`

---

## 1. Bề mặt HTTP — 313 route, đã kiểm từng chốt

| Chốt (`Depends`) | Route |
|---|---:|
| `require_login, get_db` | 126 |
| `require_login` | 81 |
| *(không có `Depends`)* | **40** |
| `require_account, get_db` | 31 |
| `_cong_co, require_login, get_db` | 11 |
| `_bat_buoc_web_broker, require_login` | 8 |
| `require_operator` (+`get_db`) | 9 |
| `require_scope(...)` | 4 |
| còn lại | 3 |

### 40 route "không `Depends`" — đã soi từng cái, **không route nào hở**

| Nhóm | Chốt thật |
|---|---|
| 10 route `server/nexus/routes.py` | **HMAC thiết bị** `_xac_thuc(device_id, timestamp, signature)` — có chống phát lại bằng dấu thời gian |
| `relay_check` | `hmac.compare_digest` trên khoá relay, **fail-closed**: biến rỗng ⇒ endpoint tắt |
| 3 route `/watch/*` (`upscalevideo`) | Dòng **đầu tiên** của cả ba gọi `_watch_user_id(request)` ⇒ bearer, 401. Docstring: *"no browser cookie is accepted"* |
| `/webhooks/payment/payos` | `xac_thuc_webhook(headers, raw)` trên **thân thô** ⇒ 400 `invalid signature` |
| `/api/v1` | 23 `require_scope` + 2 `require_principal` |
| `/login` `/register` `/forgot-password` `/live` `/ready` `/version` `/` `/tai-xuong` `/huong-dan` favicon | công khai **có chủ ý** |

⭐ **`relay_check` fail-closed đáng nêu riêng**: biến môi trường rỗng làm endpoint
**tắt**, không phải **mở toang**. Đó là mặc định đúng, và nó là mặc định hiếm.

---

## 2. Cô lập người thuê

**65 tệp test** chạm phép kiểm cô lập chủ sở hữu — đây **không** phải khoảng
trống, và nói ngược lại sẽ là nói sai. Bằng chứng ở mức **E2**.

Mẫu điển hình trong route: `require_login` + truy vấn lọc theo `user_id` +
`get_owned(db, id, user_id, lock=True)`.

**Còn nợ (P2):** một ma trận **có hệ thống** phủ *mọi* route trả artifact/job/
project theo đúng Golden Journey — hiện là phủ theo app, không theo hành trình.

---

## 3. Bí mật

| Kiểm | Kết quả |
|---|---|
| `tools/scan_source_secrets.py` | **0 finding** |
| Bí mật trong git | `secrets/`, `data/config.json`, `cloudflare/*` đều gitignore |
| 42 biến production | không biến nào mã không đọc; **0 cấu hình chết** |
| Sao lưu bí mật **tách** khỏi sao lưu dữ liệu | ✅ thiết kế đúng (H35.9) — ⛔ nhưng **chưa từng chạy**, xem O-01 |

⭐ Lý do tách hai bản sao được viết ra trong `backup.ps1` và nó đúng: `app.env`
giữ `LTT_TOKEN_ENCRYPTION_KEY` + `LTT_API_KEY_PEPPER`, còn dump giữ bản mã của
token và hash khoá API. Gộp chung một zip nghĩa là **một bản sao bị lấy cắp là đủ**
để đọc token và tấn công khoá API ngoại tuyến.

🔴 **Nhưng thiết kế đúng mà chưa chạy lần nào thì bảo vệ được số không.** Xem
`10_...md` O-01.

---

## 4. Một lỗ **đã đóng** trong đợt này, đáng ghi vì cách nó ẩn

`tools/build_release.py` có đường chặn: phát hiện bí mật trong gói phát hành ⇒
`SystemExit`. Phép kiểm của nó là
`test_secret_abort_path_reports_location_and_exits`.

Phép kiểm đó **đỏ từ trước đợt xoá** — nhưng **không phải vì đường chặn hỏng**.
Chốt "bundle cũ" bắn **trước** và nuốt mất `SystemExit` mà phép kiểm định bắt.

⇒ Một gốc (bundle lệch hash), hai triệu chứng, và triệu chứng thứ hai là **phép
kiểm chặn rò rỉ bí mật không được chạy** — im lặng theo cách tệ nhất: trông như
một lỗi build tầm thường.

Đã đóng ở `a5274bf` (35/35 passed). ⭐ Bài học chung: **một phép kiểm bảo mật đỏ
vì lý do khác vẫn là một phép kiểm bảo mật không chạy.**

---

## 5. Riêng tư

| Mục | Trạng thái |
|---|---|
| Retention có nơi khai | ✅ `docs/DATA_RETENTION_POLICY.md` + `public_api/governance.py` |
| Purge thật sự chạy | ✅ `_don_du_lieu_het_han` — 8 quy tắc, mỗi cái session+commit riêng |
| Nội dung job hết hạn (prompt, tệp, payload) | ✅ `_don_noi_dung_job` — hàng `jobs` ở lại làm bằng chứng |
| Log không lưu payload nhạy cảm | ✅ mẫu quan sát được: log cắt id còn 8 ký tự |

⚠️ **Một mục retention KHÔNG có ai chạy:** giữ chỗ treo. Sổ credit append-only nên
không purge được (đúng) — nhưng trước 26/08 cũng không **báo cáo** được. Đã đóng.

---

## 6. Phát hiện

| ID | Mức | Nội dung |
|---|---|---|
| **S-01** | P2 | Chưa có ma trận âm tính chủ-A/chủ-B **theo Golden Journey** (phủ theo app thì đã có, 65 tệp) |
| **S-02** | P2 | 4 chốt không-`Depends` (HMAC / bearer / chữ ký webhook / fail-closed) chưa có test **âm tính chuyên biệt**: phát lại, lệch giờ, cookie trình duyệt bị từ chối, thân sửa đổi |
| ~~S-03~~ | — | ✅ đóng `a5274bf` — phép kiểm chặn rò rỉ bí mật đã chạy lại |

**Đã đủ cho MVP:** xác thực phiên, CSRF, giới hạn nhịp, cô lập chủ, quét bí mật,
fail-closed ở ba cổng `/api/v1`. Không đề xuất framework bảo mật mới.

```text
NO_RUNTIME_CHANGE: NO
```
