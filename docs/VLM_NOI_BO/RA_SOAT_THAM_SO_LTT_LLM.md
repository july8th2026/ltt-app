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
| — | `tests/test_334_ngan_sach_ltt_llm.py` — **18 phép kiểm tự đối chiếu** | ✅ |

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

---

## 7. ĐÃ GIẢI — nguồn thứ ba của `LTT_LLM_MAX_INPUT_TOKENS` (30/08)

**Nó là `C:\ProgramData\LTTLlm\gateway.env` trên máy B**, và theo **thiết kế có
chủ ý** tệp này **thắng tất cả**: `llm_gateway/main.py::nap_env()` đọc nó rồi ghi
đè thẳng `os.environ`, với chú thích ngay tại chỗ:

> *"**TỆP THẮNG.** Nó là nơi người vận hành sửa; giá trị `nssm` mang theo chỉ là
> ảnh chụp cũ của chính tệp này."*

### Vì sao mất lâu đến thế mới tìm ra

Tôi đã lần lượt loại trừ — mỗi lần đều tốn một vòng đo:

| Nghi can | Kết quả |
|---|---|
| Tiến trình cũ chưa restart | ✗ PID mới, rồi cả một lần **reboot** máy B |
| Tiến trình con mồ côi giữ cổng | ✗ diệt rồi, vẫn thế |
| `AppEnvironmentExtra` của NSSM | ✗ hỏi chính `nssm.exe`: **90000** |
| `AppEnvironment` (thay thế toàn bộ) | ✗ rỗng |
| Env cấp máy / người dùng | ✗ trống, rồi tôi đặt 96256 vẫn không ăn |
| `min(cfg, catalog.max_context)` | ✗ catalog khai 131.072 |
| Bản mã thứ hai (site-packages, ổ E:) | ✗ không có |
| `__pycache__` cũ (deploy giữ timestamp) | ✗ xoá sạch, vẫn thế |
| **`gateway.env` ngoài `H:\`** | ✅ **thủ phạm** |

⭐ **Bài học đắt nhất:** tôi tìm tệp `.env` bằng `Get-ChildItem H:\LTT_LLM -Recurse`
   — nhưng tệp thật nằm ở `C:\ProgramData\`, **ngoài cây thư mục của ứng dụng**.
   Một nguồn cấu hình đặt ngoài thư mục dự án là nguồn khó tìm nhất, và ở đây nó
   còn là nguồn **có quyền cao nhất**.

### Sau khi sửa

```
LTT_LLM_MAX_INPUT_TOKENS: 65000 -> 96256      (bản sao lưu: gateway.env.truoc-96256)
/health tran.input_tokens: 96256              ✅ khớp ngan_sach.TOKEN_VAO_TRAN
tests/test_312: 21/21 PASS, 0 skip            ✅ ba tầng đồng ý
```

**+48% ngữ cảnh dùng được**, và quan trọng hơn: `TestDoiChieuMayB` nay chạy thật
chứ không bỏ qua, nên lệch kiểu này **không thể ẩn được nữa**.

⚠️ **Ghi cho phiên sau:** sửa trần token trên máy B thì sửa ở
`C:\ProgramData\LTTLlm\gateway.env` rồi `Restart-Service LTTLlmGateway`. Sửa
NSSM env hay env máy đều **vô tác dụng** — tệp ghi đè lên chúng.

---

## 8. DỌN TẦNG VẬN HÀNH — cả hai máy (30/08)

Sau khi dọn tầng **mã**, tầng **vận hành** vẫn còn chồng chéo: cùng một biến khai
ở nhiều nơi, và chỉ một nơi có tác dụng.

### 8.1 Máy B — `gateway.env` là NGUỒN DUY NHẤT

| Nơi khai `LTT_LLM_*` | Có tác dụng? |
|---|---|
| `C:\ProgramData\LTTLlm\gateway.env` | ✅ **thắng tất cả** — `main.py::nap_env()` ghi đè `os.environ` |
| NSSM `AppEnvironmentExtra` (12 biến) | ❌ bản sao câm; vẫn ghi 90000 mà không ai đọc |
| Env cấp máy | ❌ bị tệp ghi đè |

⚠️ **`gateway.env` do `deploy.ps1` SINH RA** (dòng đầu tệp ghi rõ *"KHÔNG sửa
tay"*). Sửa tay mà không sửa nguồn sinh thì **lần deploy sau mất trắng** — chính
xác cái bẫy đã suýt dính: bản vá 65000 → 96256 nằm trong tệp, còn `deploy.ps1`
vẫn ghi 65000 ở **ba** chỗ. Đã sửa cả ba (`c0c9c0f`).

**Còn phải làm (cần một lệnh trên máy B):** rút NSSM env xuống còn đúng hai mục
— `PYTHONPATH` (yêu cầu chạy, không phải cấu hình) và `LTT_LLM_ENV_FILE` (con
trỏ). Bản sao lưu 12 biến cũ đã có ở
`C:\ProgramData\LTTLlm\nssm-env.truoc-don-<thời-điểm>.txt`.

### 8.2 Máy A — mặc định trong mã là nguồn duy nhất

`LTT_PUBLIC_API_MAX_BODY_BYTES` cấp máy **đã gỡ**. Trần body nay chỉ đến từ
`DEFAULT_MAX_BODY_BYTES = 1 MiB` trong mã, và `test_312` buộc nó ≥
`ngan_sach.BODY_BYTES_TOI_THIEU`.

⛔ **Một hồi quy tự gây ra, và bài học từ nó:** gỡ biến môi trường **trước khi**
   deploy mã mới làm production tụt về 256 KB trong vài phút — biến đó đang *bù*
   cho mã cũ. Thứ tự đúng là **deploy mã trước, gỡ biến bù sau**.

### 8.3 Trạng thái sau khi dọn — đo trên hệ đang chạy

```
than 600 KB -> 413  limit_name=input_tokens  limit_value=96256
```
Trước đây cùng request này bị chặn ở tầng **byte** với thông điệp không nói tầng
nào; nay nó qua tầng byte và dừng ở đúng tầng **token**, có xưng tên.

```
tests/test_312: 21/21 PASS, 0 skip   (chay voi may B that)
```

### 8.4 Luật cho phiên sau

| Muốn đổi | Sửa ở đâu | Đừng sửa ở đâu |
|---|---|---|
| Trần token của B | `llm_gateway/deploy/deploy.ps1` **rồi deploy** | NSSM env, env máy, sửa tay `gateway.env` |
| Cửa sổ model / trần vào-ra | `apps/ltt_llm/ngan_sach.py` (3 số gõ tay) | bất kỳ nơi nào khác — chúng là bí danh |
| Trần body của nền tảng | `DEFAULT_MAX_BODY_BYTES` | biến môi trường (chỉ dùng khi cần đè tạm) |
| Token ra mặc định | `TOKEN_RA_MAC_DINH` theo **tên cửa** | đừng thêm một "mặc định chung" nào nữa |

⭐ Và sau mỗi lần đổi: `pytest tests/test_334_ngan_sach_ltt_llm.py` **có
`LTT_LLM_TOKEN`** — nó là thứ duy nhất bắt được ba tầng nói ba số khác nhau.

---

## 9. NÂNG llama.cpp + NHÓM 3 (30/08)

### 9.1 llama.cpp `b10580` → `b10689`

| | |
|---|---|
| Trước | `0.2.0-dev (build 10580, commit 54ee5ee64)` — tải 22/08 |
| Sau | `0.3.0-dev (build 10689, commit 57291f264)` — 30/08, **cách 109 bản** |
| Gói | `llama-b10689-bin-win-cuda-13.3-x64.zip` (140 MB), khớp CUDA 13.3 của B |
| Đường lùi | `H:\LTT_LLM\bin\llamacpp.b10580` (bản sao đầy đủ) |

**Cách làm — chép ĐÈ, không xoá rồi chép.** Thư mục `llamacpp` còn giữ các DLL
cudart nạp từ gói riêng; xoá cả thư mục là mất chúng và llama-server không khởi
động được. Chép đè giữ lại mọi tệp gói mới không có.

**Thứ tự bắt buộc:** dừng `LTTLlmGateway` **rồi** `LTTLlamaSwap` → chép đè →
kiểm `--version` **trước khi** bật lại → bật `LTTLlamaSwap` rồi `LTTLlmGateway`.

⚠️ `llama-server.exe --version` in ra **stderr**, nên PowerShell báo `exit=1` dù
   chạy đúng. Đừng đọc mã thoát đó thành hỏng.

### 9.2 Nhóm 3 — tự thử lại một lần khi parser tool-call vỡ

Bug thượng nguồn **vẫn còn mở** (#27733, #20260, #18353): parser `peg-native` vỡ
khi phân tích lượt có tool call, **vứt toàn bộ kết quả đã sinh**. Nâng bản là để
giảm xác suất, không phải để chắc chắn hết.

`luong_vlm.mo()` nay thử lại **đúng một lần** khi thân lỗi 5xx khớp một trong ba
dấu hiệu **lấy từ thông điệp thật của máy B**:

```
"failed to parse tool call"  |  "peg-native"  |  "failed to parse input at pos"
```

⛔ **Bộ nhận diện phải hẹp.** Thử lại một sự cố hạ tầng thật (hết VRAM, model
   chết, cấu hình sai) chỉ đốt thêm một lượt GPU rồi hỏng y hệt, **và giấu mất
   triệu chứng**. Test chốt cả hai chiều: bắt đúng 3 dạng, không bắt nhầm 5 lỗi thật.

⛔ **Đúng một lần.** `_da_thu_lai` chặn vòng lặp; lần hai vẫn vỡ thì ghi nhật ký
   và trả lỗi như cũ, để **tần suất thật không bị giấu**.

---

## 10. `gpt-5.6-luna` — ta chưa từng khai tên đó (30/08)

### 10.1 Triệu chứng và cái bẫy chẩn đoán

Nền tảng trả **400** cho những lượt mang `model='gpt-5.6-luna'`. Tên đó **không
tồn tại ở chỗ ta**, không có trong `aliases()`, không có trong
`TUYEN_TUONG_THICH`, không có trong cấu hình nào của khách.

⛔ **Cái bẫy:** đọc "Codex gửi sai tên" rồi kết luận "thì nhận thêm tên đó cho
xong". Đó là chữa triệu chứng, và chữa sai hướng — xem §10.3.

Hình dạng request (nhật ký `_bao_400`) nói ngay đây **không phải lượt chat**:

```
stream=True  model='gpt-5.6-luna'  tc='auto'  input=list(len=5)  tools=0
keys=[client_metadata, include, input, model, parallel_tool_calls,
      prompt_cache_key, reasoning, store, stream, text, tool_choice]
```

`tools=0` và 5 mẩu đầu vào ⇒ một **lượt phụ** Codex bắn lúc mở phiên. Lượt chat
chính ngay sau đó **vẫn chạy tốt**. Nên triệu chứng khách thấy không phải "chat
hỏng" mà là những thứ vụn: phiên không được đặt tên, và nén hội thoại trượt.

### 10.2 Gốc — Codex không có metadata cho `ltt_llm`

Codex in cảnh báo `Model metadata for ltt_llm not found`, rồi đường
`compact_model_fallback` của nó **mượn tên một model OpenAI** cho lượt phụ.

**Bằng chứng đo được**, không phải suy luận — cùng một phiên, chỉ khác việc có
khai catalog hay không:

| | cảnh báo metadata | `model_context_window` của phiên |
|---|---|---|
| trước (không catalog) | **có** | 84.127 |
| sau (có catalog) | **không** | **79.699** |

79.699 = `88.555 × 90 %` — đúng hai con số **ta** khai trong catalog
(`context_window` và `effective_context_window_percent`). Tức Codex đã đọc tệp
của ta và thôi phải đoán. Từ lúc khai: **0 lượt 400** (trước đó 29/08 23:30 và
30/08 11:57).

### 10.3 Vì sao KHÔNG thêm tuyến tương thích cho tên đó

Đây là câu hỏi đã đặt ra, và câu trả lời là **không**, có lý do:

`TUYEN_TUONG_THICH` hiện có đúng một mục — `ltt-llm-claude-compat` — và đó là
tên **ta tự đặt**. Chú thích của chính nó ghi: *"ta qua được cổng mà **không**
mượn tên sản phẩm của hãng khác"*.

Ánh xạ `gpt-5.6-luna → ltt_llm` làm **đúng điều ngược lại**: nhận một tên sản
phẩm thật của OpenAI rồi lặng lẽ phục vụ Qwen. Ba hệ quả:

1. **Mượn tên hãng khác** — chính thứ khuôn hiện tại cố ý tránh.
2. **Giấu cấu hình sai.** Máy khách thiếu catalog sẽ chạy "êm" mãi mãi, và ta
   không bao giờ biết máy nào đang thiếu.
3. **Không bao giờ đóng lại được.** Danh sách tên hãng cần nhận sẽ dài ra theo
   mỗi bản Codex, vì ta đang đuổi theo một giá trị nội bộ của họ.

⇒ Ta **vẫn từ chối**, nhưng lời từ chối nay **chỉ đúng chỗ sửa**:
`_goi_y_ten_la()` nhận ra tên bắt đầu bằng `gpt-`/`claude-`/`gemini-`/… và thêm
câu chỉ dẫn khai `model_catalog_json`. Có **bánh cóc** chốt rằng không mục nào
của `TUYEN_TUONG_THICH` được bắt đầu bằng tên hãng.

### 10.4 Cách làm đúng — `model_catalog_json`

Khoá cấu hình **chính thức** của Codex để khai model ngoài. `tools/cam_cli.py`
nay ghi `~/.codex/ltt_model_catalog.json` và khai đường dẫn tới nó.

⚠️ **Ba thứ Codex TỪ CHỐI**, tìm ra bằng cách lặp thật chứ không có trong tài liệu:

| Sai | Đúng |
|---|---|
| `"web_search_tool_type": null` | **bỏ hẳn trường đó** — nó không nhận `null` |
| `"effective_context_window_percent": 0.9` | `90` — trường đòi **i64** |
| khai đường dẫn tới tệp **chưa tồn tại** | phải **ghi tệp** — nếu không Codex `failed to parse model_catalog_json` rồi **từ chối khởi động** |

Mục cuối là thứ nguy hiểm nhất: nó biến một **cảnh báo vô hại** thành một **lỗi
chặn đường**. Nên `cam` ghi tệp, và `go` dọn nó theo đúng luật *"xoá đúng thứ ta
đã thêm"* — xoá nếu ta tạo, trả về bản sao lưu nếu khách đã có sẵn.

### 10.5 Dọn theo — test từng ghi ra ngoài thư mục tạm

`TEP_CATALOG` và `TEP_NHAT_KY` được tính từ `NHA` **lúc nạp module**, mà fixture
chỉ tro lại `NHA`. Hệ quả: test ghi vào `~/.codex` và `%LOCALAPPDATA%` **thật**
của người đang chạy test — và **không test nào đỏ**. Xanh vì lý do sai.

Đã tro lại cả hai, và thêm bánh cóc
`test_KHONG_hang_duong_dan_nao_con_tro_ra_NGOAI_thu_muc_tam` để lần sau có hằng
mới thì nó đỏ ngay.

⚠️ Bánh cóc đó **không** kiểm "có nằm trong thư mục nhà không" — trên Windows
`tmp_path` chính nó nằm dưới thư mục nhà, nên phép kiểm đó luôn đỏ.

---

## 11. Claude Code cũng đoán sai cửa sổ — và đó là lỗi tiền (30/08)

### 11.1 Đo được, không phải suy luận

Chạy thật `claude.exe -p` qua model của ta (cấu hình **cách ly**, không chạm
phiên nào đang sống):

```
"ltt_llm" is not a model this version of Claude Code recognizes, so auto-compact
will keep this session within 200k tokens (the context window it assumes).
```

Trần vào thật của ta là **96.256**. Với giả định **200.000**, auto-compact
**không bao giờ nén kịp**: hội thoại đã vượt trần của ta từ lâu mà client vẫn
tưởng còn nửa đường. Khách ăn **413 giữa chừng** — đúng triệu chứng *"hỏi dài
thì im lặng"* đã mất nhiều giờ truy ở phía Codex.

⇒ Đây **không phải tinh chỉnh**. Nó là cùng một lỗi tiền, ở client thứ hai.

### 11.2 Cách sửa, đã A/B

| | cảnh báo cửa sổ |
|---|---|
| không đặt `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | **có** |
| đặt `= 88555` | **hết** |

`cam_claude` nay đặt thêm hai biến:

```
CLAUDE_CODE_MAX_CONTEXT_TOKENS = 88555      (= ngan_sach.CONG_BO_CHO_CLIENT)
CLAUDE_CODE_MAX_OUTPUT_TOKENS  = 32768      (= ngan_sach.TOKEN_RA_TRAN)
```

⚠️ **Không dùng `modelOverrides`.** Đọc mô tả trong chính binary: nó là *ánh xạ
từ model ID của Anthropic sang model ID của nhà cung cấp* — dùng để đổi tên, và
cửa sổ vẫn lấy theo model ID của Anthropic. Nó **không** giải bài này.

### 11.3 Hai client, một nguồn chân lý

`test_334::TestCamCliKhopNganSach` chốt cả hai đường cùng nói một con số:

| client | khoá | nói cửa sổ ở đâu |
|---|---|---|
| Codex | `model_catalog_json` | `context_window` trong tệp catalog |
| Claude Code | biến môi trường | `CLAUDE_CODE_MAX_CONTEXT_TOKENS` |

Bỏ sót một bên là để **đúng một client** rơi lại vào lỗi vừa sửa cho client kia.

### 11.4 Thử Claude Code an toàn — không cần VM

`claude.exe` đọc `CLAUDE_CONFIG_DIR`, nên cách ly được hoàn toàn:

```powershell
$env:CLAUDE_CONFIG_DIR = "$env:TEMP\claude_thu_ltt"   # cau hinh RIENG
$env:ANTHROPIC_BASE_URL = "https://app.lttstudios.com/api"
$env:ANTHROPIC_MODEL    = "ltt_llm"
$env:ANTHROPIC_AUTH_TOKEN = "<khoa LTT>"
$env:CLAUDE_CODE_MAX_CONTEXT_TOKENS = "88555"
& $claude -p "cau hoi" --output-format text
```

Ba điều đã kiểm, không phải phỏng đoán:

1. **Claude Desktop không bị chạm.** Đường của Desktop là chính sách registry
   `HK*\SOFTWARE\Policies\Claude`; đọc máy 30/08 thì **cả HKCU lẫn HKLM đều
   không có khoá đó**. Desktop không đọc `settings.json`, không đọc
   `ANTHROPIC_BASE_URL`.
2. **Phiên đang chạy không bị ngắt.** Env cấp User đã trỏ về LTT từ 27/08 mà
   phiên đang chạy vẫn `ANTHROPIC_BASE_URL=https://api.anthropic.com`. `setx`
   ghi registry, **không** đổi môi trường tiến trình đang sống; `settings.json`
   đọc **lúc khởi động**. ⇒ chỉ ảnh hưởng phiên mở **sau**.
3. Vì (1) và (2), **không cần VM** cho việc thử này. VM chỉ cần khi muốn thử
   chính đường `cam`/`go` (setx + registry) đúng như khách sẽ chạy.

---

## 12. Dọn theo — gate thôi đỏ ngẫu nhiên (30/08)

Ba thứ làm cổng chất lượng đỏ vì **chính nó**, không vì mã:

**① `test_209` sửa thẳng `CONTRACT_BASELINE.json`.** Có `try/finally`, nhưng
`finally` không chạy khi tiến trình bị giết — và `gate.py` chạy
`check_api_compat.py` **song song** với bộ test, nên cổng đọc tệp trong khi test
đang sửa. Tệ hơn: một lượt bị ngắt để tệp lại bẩn, rồi lượt sau chụp **đúng bản
bẩn đó** làm `saved` và ghi lại ⇒ rác **tự nhân lên**.
⇒ Nay các phép kiểm đó chạy trên **bản sao** (`_ban_sao`), qua hai biến chỉ dành
cho test: `LTT_CONTRACT_BASELINE` và `LTT_CONTRACT_BASELINE_COMMITTED`. Có bánh
cóc `test_KHONG_test_nao_duoc_GHI_vao_ban_chuan_that`.

**② `check_bo_qua.py --accept` ghi CRLF**, nên mỗi lần chấp nhận một dòng lại
đổi **cả tệp** — diff 14 dòng cho một thay đổi 1 dòng. Đã `newline=""`.

**③ Số test trùng.** `test_312` bị hai phiên dùng cùng lúc; bản của đợt này đổi
thành **`test_334_ngan_sach_ltt_llm.py`**.

⚠️ Còn **một chỗ chưa đóng, và nó không thuộc đợt này**:
`test_252_vps_giao_dien.py::test_app_TAT_khong_lot_vao_trang_chu_cua_nguoi_da_dang_nhap`
đỏ **một lần** trong lượt gate ngay sau khi đổi tên tệp test (đổi tên làm đổi
thứ tự chia nhóm song song), rồi xanh ở hai lượt sau và xanh khi chạy riêng.
Dấu hiệu **trạng thái ngoài rò vào test**, không phải lỗi của mã VPS. Ghi ra đây
để lần sau không ai truy nhầm sang phía `ltt_llm`.
