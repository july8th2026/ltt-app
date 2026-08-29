# Rà soát tham số `ltt_llm` — và cách dẹp bỏ chồng chéo

**Đo ngày 2026-08-30**, sau một phiên truy bug mà **một triệu chứng duy nhất**
(*"trả lời dài thì im lặng"*) bắt đi qua **bốn tầng tham số ở bốn nơi khác nhau**.
Tài liệu này ghi lại *vì sao khó truy*, không chỉ *sửa gì*.

---

## 1. Chuỗi tệp của một lượt `ltt_llm`

```
HTTP        server/api/streaming.py      (/v1/responses, /v1/messages — cửa STREAM)
            server/api/chat.py           (cửa ĐỒNG BỘ, trả một cục)
              │
hợp đồng    apps/ltt_llm/manifest.py     khai tool, model alias, cửa sổ ngữ cảnh
            apps/ltt_llm/features.py     ước token, ngân sách cửa đồng bộ
            apps/ltt_llm/executor.py     gói lại cho tầng trên gọi
              │
nền tảng    platform_core/llm/luong_vlm.py    mở luồng tới B, dịch lỗi
            platform_core/llm/dieu_phoi.py    chọn khoá/provider
            platform_core/llm/gia_token.py    giá, quy đổi credit
            platform_core/llm/thanh_toan.py   giữ chỗ → quyết toán → hoàn
            platform_core/llm/admission.py    nhịp tim, nhận việc
            platform_core/public_api/config.py trần body, rpm, concurrency
              │  ── mạng LAN ──
máy B       llm_gateway/config.py        đọc 12 biến LTT_LLM_*
            llm_gateway/ngan_sach.py     trần token vào/ra, ước token
            llm_gateway/gioi_han.py      đồng thời + rpm
            llm_gateway/trong_tai.py     trọng tài GPU (bận ≠ hỏng)
            llm_gateway/upstream.py      chuyển tiếp llama-server
              │
            llama-server (-c 131072, --parallel 1, spec draft-mtp)
```

**Bảy tệp có quyền từ chối một request**, mỗi tệp có trần riêng. Đó là gốc của
việc "không biết cái nào chặn".

---

## 2. Danh mục tham số — và các chỗ chồng chéo THẬT

### ⛔ A. Cùng một hằng số, khai ở hai kho

| Hằng | Nơi 1 | Nơi 2 |
|---|---|---|
| `KY_TU_MOI_TOKEN = 2.5` | `apps/ltt_llm/features.py:49` | `llm_gateway/ngan_sach.py:42` |

Hai bản sao của **cùng một phép ước token**. Lệch nhau là tiền giữ trước lệch với
tiền B tính — và **không có gì báo**.

### ⛔ B. "Token ra mặc định" — ba giá trị, ba nơi

| Giá trị | Nơi | Phục vụ cửa nào |
|---|---|---|
| `MAX_TOKENS_MAC_DINH = 4096` | `manifest.py:46` | (tài liệu nói: stream + job) |
| `SYNC_MAX_TOKENS_MAC_DINH = 1024` | `features.py:53` | cửa đồng bộ |
| `MAC_DINH_TOKEN_RA_STREAM = 8192` | `streaming.py:116` | cửa stream *(thêm 30/08)* |

🔴 **Đây là bug đã xảy ra**: `_max_tokens()` lấy `executor.default_max_tokens`
(= 1024 của cửa đồng bộ) cho **cả cửa stream**, trong khi chú thích ngay tại
`features.py:49` viết *"Cửa stream và cửa job vẫn dùng mặc định 4.096"*. Tài
liệu hứa một đằng, mã làm một nẻo, và triệu chứng là câu trả lời **cụt ở đúng
1024 token** — không lỗi, không cảnh báo.

### ⛔ C. Cửa sổ ngữ cảnh — bốn con số, không ai đồng bộ ai

| Con số | Nơi | Ý nghĩa |
|---|---|---|
| `131_072` | `manifest.py:51` `CUA_SO_NGU_CANH` | ta *tin* model có bấy nhiêu |
| `65_000` (mặc định mã) / `90_000` (registry B) | `llm_gateway/config.py:118` | B **thực sự** chặn đầu vào |
| `60_000` | `server/api/tools.py` | ta **công bố** cho Codex |
| `60_000` | `~/.codex/config.toml` | Codex dùng để nén hội thoại |

Nền tảng tính chỗ-còn-lại bằng `131072 − vào − 2048` mà **không hề biết** B chặn
ở 65.000. Ba nơi, ba số, không nơi nào dẫn xuất từ nơi nào.

### ⛔ D. Trần body — không liên quan gì tới trần token, nhưng chặn trước

`DEFAULT_MAX_BODY_BYTES = 256 KB` (`public_api/config.py:66`). Một hội thoại
agentic 90.000 token ở dạng JSON ≈ **360 KB** ⇒ bị chặn **trước khi** ai kịp đếm
token. 256 KB ÷ ~4 byte/token ≈ **64.000 token** — trùng hợp gần bằng 65.000 nên
suốt buổi ta tưởng đang chạm trần của B.

### ⛔ E. Nhịp và đồng thời — hai tầng, không phối hợp

| Bên ta | Máy B |
|---|---|
| `LTT_PUBLIC_API_RPM = 120` | `LTT_LLM_RPM = 120` |
| `LTT_PUBLIC_API_CREATE_RPM = 20` | — |
| `MAX_ACTIVE_JOBS = 5` | `LTT_LLM_MAX_DONG_THOI = 1` |

Ta cho **5 việc chạy song song**, B phục vụ **1** ⇒ bốn việc kia chắc chắn ăn
429/503. Không phải lỗi của bên nào, là **hai trần không biết nhau**.

### ⛔ F. Thời gian chờ — ba tầng, tầng chặt nhất nằm ở giữa

`MO_LUONG_GIAY = 75s` (ta) · `LTT_LLM_UPSTREAM_TIMEOUT_S = 600s`,
`STREAM_TIMEOUT_S = 900s` (B) · Cloudflare **100s** (ngoài cùng).
Ta bỏ cuộc ở 75s trong khi B còn chờ tới 600s.

### ⛔ G. Một biến, ba nguồn sự thật

`LTT_LLM_MAX_INPUT_TOKENS` cùng lúc tồn tại ở: **mặc định trong mã** (90.000 trên
B) · **registry dịch vụ** (90.000) · **tiến trình đang chạy** (65.000). Ba nguồn
bất đồng, và **chưa có phép kiểm nào phát hiện**. Tính tới 30/08 nguồn thứ ba
vẫn chưa truy ra.

---

## 3. Phương án: bốn nguyên tắc

### Nguyên tắc 1 — MỘT nguồn chân lý, phần còn lại là DẪN XUẤT

Gom vào `apps/ltt_llm/ngan_sach.py` (mới):

```python
CUA_SO_MODEL   = 131_072          # ĐO từ `-c` của llama-server, không đoán
TOKEN_RA_TRAN  =  32_768
LE             =   2_048

# ─ dẫn xuất, KHÔNG gõ tay ────────────────────────────────
TOKEN_VAO_TRAN   = CUA_SO_MODEL - TOKEN_RA_TRAN - LE      # 96_256
BODY_BYTES_TRAN  = TOKEN_VAO_TRAN * BYTE_MOI_TOKEN_JSON   # đủ chỗ cho ngần ấy token
CONG_BO_CHO_CLIENT = int(TOKEN_VAO_TRAN * 0.92)           # lệ cho lệch tokenizer

TOKEN_RA_MAC_DINH = {"stream": 8_192, "sync": 1_024, "job": 8_192}
```

Sửa `CUA_SO_MODEL` là bốn con số dưới **tự đúng theo**. Không còn chỗ để lệch.

### Nguyên tắc 2 — mặc định phải MANG TÊN CỬA

Bỏ `executor.default_max_tokens` (chung chung). Thay bằng `mac_dinh_cho("stream")`.
Lỗi 1024 **không xảy ra được** nếu tên bắt buộc nêu cửa.

### Nguyên tắc 3 — trần nào từ chối thì trần đó XƯNG TÊN

Mọi 413/429 trả kèm `limit_name`, `limit_value`, `observed`. Hôm nay thông điệp
chỉ nói *"vượt giới hạn"* nên mất nhiều lượt mới biết là body-bytes hay token.

### Nguyên tắc 4 — một phép kiểm TỰ ĐỐI CHIẾU

Một test đọc số của ta, gọi `GET /health` của máy B, và **so**:

```
ta.TOKEN_VAO_TRAN     ==  B.tran.input_tokens
ta.TOKEN_RA_TRAN      ==  B.tran.output_tokens
ta.KY_TU_MOI_TOKEN    ==  B.KY_TU_MOI_TOKEN
ta.MAX_ACTIVE_JOBS    <=  B.gioi_han.max_dong_thoi   (hoặc nêu rõ vì sao khác)
```

Lệch là **đỏ**. Có nó từ đầu thì mâu thuẫn 90k-vs-65k đã lộ ngay, không cần truy
nửa đêm.

---

## 4. Thứ tự thi hành đề xuất

| Bước | Việc | Rủi ro |
|---|---|---|
| 1 | Dựng `ngan_sach.py` + phép kiểm tự đối chiếu (Nguyên tắc 1 + 4) | thấp — chỉ thêm |
| 2 | Chuyển các nơi đang gõ tay sang import từ đó | thấp — có test đỡ |
| 3 | Đổi tên mặc định theo cửa (Nguyên tắc 2) | thấp |
| 4 | Thêm `limit_name` vào lỗi (Nguyên tắc 3) | thấp — cộng thêm trường |
| 5 | Gộp `KY_TU_MOI_TOKEN` về một nơi hai kho cùng đọc | trung bình — hai kho |
| 6 | Chốt lại đồng thời: `MAX_ACTIVE_JOBS` theo `MAX_DONG_THOI` của B | trung bình |

---

## 5. Đã sửa trong phiên 30/08 (bối cảnh)

| Lỗi | Vá |
|---|---|
| Cửa stream mượn mặc định 1024 của cửa đồng bộ | `MAC_DINH_TOKEN_RA_STREAM = 8192` |
| Trần body 256 KB chặn hội thoại dài | `LTT_PUBLIC_API_MAX_BODY_BYTES = 2 MB` (env cấp máy) |
| 413 của B bị dịch nhầm thành 503 | trả 413 kèm hướng dẫn nén |
| Log cắt lý do thượng nguồn ở 200 ký tự | ghi 4.000 |
| `/v1/models` sai khuôn Codex đọc | thêm khối `models` |

**Còn mở:** nguồn thứ ba đặt `LTT_LLM_MAX_INPUT_TOKENS=65000` trên máy B.

---

## 6. ĐÃ THI HÀNH — 30/08

| Bước | Việc | Kết quả |
|---|---|---|
| 1 | `apps/ltt_llm/ngan_sach.py` — nguồn chân lý, **3 số gõ tay**, còn lại dẫn xuất | ✅ |
| 2 | `manifest.py` / `features.py` chuyển thành **bí danh**, không định nghĩa lại | ✅ |
| 3 | Bỏ `executor.default_max_tokens`; mọi bên gọi phải **nêu cửa** (`mac_dinh_cho`) | ✅ |
| 4 | Lỗi 413 **xưng tên trần** (`limit_name`, `limit_value`, `observed`) | ✅ |
| 5 | `KY_TU_MOI_TOKEN` một nơi; test đối chiếu hai kho | ✅ |
| 6 | `DONG_THOI_MAY_B` khai ra để trần đồng thời của ta biết trần của B | ✅ |
| — | `tests/test_312_ngan_sach_ltt_llm.py` — **18 phép kiểm tự đối chiếu** | ✅ |

### Ba lệch THẬT mà bộ kiểm mới bắt được ngay khi vừa viết xong

1. **Nền tảng cho 262.144 byte, app cần 433.152** → `DEFAULT_MAX_BODY_BYTES`
   nâng 256 KB → **1 MiB**. Đây đúng là trần đã chặn hội thoại dài ở ~64.000
   token trong khi ta tưởng đang chạm trần của máy B.
2. **`llm_gateway` mặc định 65.000, ngân sách tính 96.256** → sửa về 96.256.
   Chính con số 65.000 này là thứ máy B đang thực thi.
3. **Cửa job suýt bị đổi 4.096 → 8.192** — bộ kiểm hợp đồng vàng chặn lại. Con số
   cửa job là `default` **in trong hợp đồng công khai**, đổi nó là đổi thứ khách
   nhìn thấy; cửa job chưa từng dính lỗi nên không có lý do đổi.

### Giá trị sau khi dọn

| | Trước | Sau |
|---|---|---|
| Cửa sổ model | 131.072 (chỉ ta tin) | 131.072 (**đo**, và mọi trần dẫn xuất từ nó) |
| Trần vào | 65.000 gõ tay | **96.256** = 131.072 − 32.768 − 2.048 |
| Trần body | 256 KB, không liên quan token | **1 MiB**, đủ chứa trần vào, có test buộc |
| Token ra mặc định | 1.024 / 4.096 / 8.192 lẫn lộn | `sync 1.024` · `stream 8.192` · `job 4.096`, **gọi theo tên cửa** |
| Công bố cho client | 60.000 gõ tay | **88.555** = trần vào × 0,92 |

⚠️ **Còn lại một việc trên máy B**: nó vẫn *thực thi* 65.000 dù mã lẫn registry
đều đã đúng. Nay `TestDoiChieuMayB` sẽ **đỏ** khi chạy có `LTT_LLM_TOKEN` — tức
lệch này không còn ẩn được nữa.
