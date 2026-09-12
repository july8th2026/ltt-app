# LLM_FINAL_ARCHITECTURE — LTT LLM sau chương trình MASTER UPGRADE

2026-09-09. Mô tả **trạng thái sau khi thi hành**, đối chiếu với
`LLM_UPGRADE_BASELINE.md` (trạng thái trước).

> ⛔ Không con số ngân sách nào được gõ lại ở đây. Nguồn:
> `apps/ltt_llm/ngan_sach.py`, hoặc `GET /health` của máy B.

---

## 1. Hình dạng — **không đổi**, và đó là kết quả

```
MÁY A  192.168.2.17
  apps/ltt_llm/            manifest · features · executor · jobs · ngan_sach
  platform_core/llm/       dieu_phoi · cong_vlm · luong_vlm · thanh_toan
                           gia_token · admission · dem_token_luong
  platform_core/runtime_noi_bo/luong.py    cửa stream nội bộ (tiền ở đây)
        |
        |   LAN riêng · bearer · tường lửa chỉ mở cho 192.168.2.17
        v
MÁY B  192.168.2.66
  [3] llm_gateway   :8299   nghe LAN
  [2] llama-swap    :8280   loopback · v250
  [1] llama-server  :8281   loopback · KHÔNG xác thực
        v
  Qwen3.8-27B-UD-Q4_K_M.gguf        RTX 3090 24 GB
```

⭐ **Chương trình này không dời một ranh giới nào.** Không thêm dịch vụ, không
thêm phụ thuộc, không thêm tầng vào đường request. Chín thay đổi đều nằm **bên
trong** các hộp đã có. Đó không phải sự dè dặt — đó là kết luận của đợt nghiên
cứu: bốn trong năm khoảng trống lớn nhất được lấp bằng cách **dùng thứ đã có**.

---

## 2. Cái đã đổi

### 2.1 Cổng nói được nó là ai (W10 · W2)

`/health` → `thuong_nguon.phien_ban`:

```json
{"swap": {"version": "...", "commit": "...", "build_date": "..."},
 "engine": {"ho_so": "...", "build_info": "..."}, "ly_do": ""}
```

* `swap` từ `GET /api/version` của llama-swap — rẻ, không chạm model.
* `engine` từ `build_info` trong `/props`, **chỉ khi hồ sơ đã nạp sẵn**. Hỏi vô
  điều kiện sẽ khiến một lượt `/health` đánh thức GPU ~2,5 phút.
* Hai ô nhớ **riêng**, vì `swap` bất biến còn `engine` phụ thuộc VRAM. Gộp
  chúng đóng băng `engine=None` vĩnh viễn khi lượt `/health` đầu tiên rơi vào
  lúc chưa nạp model — tức ngay sau mỗi lần khởi động lại.

`llm_gateway/deploy/phien_ban_ghim.json` giữ bản **được chúc phúc**.
`llama_cpp.build` để `null`: **không đoán** khi chưa đo được.

### 2.2 Ranh giới bảo mật là cơ chế, không còn là giao ước (W7)

```
host ∉ {127.0.0.1, ::1, localhost}  ∧  token rỗng   ->  SystemExit(3)
```

`0.0.0.0` và `::` **cố ý không** thuộc tập loopback: chúng bind mọi giao diện.
Đường dev (loopback + không token) giữ nguyên — một chốt phá mất đường thử sẽ
bị tắt, rồi cả chốt biến mất cùng nó.

### 2.3 Phân loại lỗi: bốn nghĩa, bốn mã (W5 · W6)

| Tình huống | Cổng | Máy A | Phạt khoá? |
|---|---|---|---|
| ba loại bận | **429** | `BanError` / `DangBan` | không |
| vượt trần | **413** | `VuotNganSachError` / `qua_dai` | không, không cascade |
| model chưa mở | **404** | `CongVlmError` | có |
| **hết giờ** | **504** | `AmbiguousProviderError` / `het_gio` | **không** |
| hỏng thật | **502** | `CongVlmError` | có |

`upstream.py` tách `MA_HET_GIO`(598) khỏi `MA_KHONG_VOI_TOI`(599), và
`TimeoutException` phải bắt **trước** `HTTPError` vì nó là lớp con.

🔴 Trước đợt này, hết giờ và hỏng đi chung cửa 502 ⇒ `danh_dau_loi` ⇒ sau 5 lần
`APIKEY_ERROR`, thứ **không tự hồi**. Đã bịt ở **cả hai** client (`cong_vlm` cho
cửa đồng bộ, `luong_vlm` cho cửa streaming — cửa hay hết giờ nhất).

### 2.4 Quan trắc: đọc thứ đã đếm sẵn, đếm thứ chỉ mình thấy (W2)

```
llama.cpp  /metrics       BẬT bằng `--metrics` trong macro CHUNG
llama-swap /api/*         đã có sẵn ở v250, không phải thêm gì
cổng       /health -> dem tám nhóm kết cục + tỉ lệ từ chối + TTFT
```

Cờ `--metrics` **không** bật việc đếm — việc đếm chạy vô điều kiện trong vòng
lặp suy luận; cờ chỉ gác **cửa đọc**. Nên bật nó tốn **0** trên đường nóng.

Cổng chỉ đếm thứ engine không bao giờ thấy: **mọi lượt bị từ chối** đều không
chạm tới engine.

TTFT đo **như khách thấy** (gồm chờ suất, dọn card, nạp model), và lớp đo phải
nằm **trong** `nhip_tim` — bọc ngoài thì mọi lượt dài đều ra đúng chu kỳ nhịp
tim, một con số ổn định và vô nghĩa.

### 2.5 Tiền: hai đường độc lập (W9)

```
đường 1   `finally` của `_phat`                        — khi luồng có chảy
đường 2   `dam_bao_quyet_toan()` từ `BackgroundTask`   — kể cả khi thân chưa đọc
```

`luot.da_quyet_toan` bảo đảm chỉ một đường thật sự thu.

🔴 Trước đợt này chỉ có đường 1, và một `finally` **không chạy nếu generator
chưa khởi động**. Khách ngắt trước byte đầu ⇒ hold không được kết sổ ngay.

⚠️ **Không phải "vĩnh viễn"** — `credit.tu_hoan_treo` (H41.3) quét nó sau
`TU_HOAN_SAU = 24 giờ`. Hại thật là tiền khách bị giữ **tới một ngày** cho một
lượt không chạy, không phải mất tiền. Lưới mới biến 24 giờ thành **tức thì**.

---

## 3. Bất biến — cái giữ nguyên, và vì sao

| Bất biến | Vì sao không đụng |
|---|---|
| Máy A giữ toàn bộ business logic | máy B là node suy luận, không phải app server thứ hai |
| Cổng **không** có đường fallback | D-010: đổi model sau lưng khách là bán sai hàng |
| Cascade chỉ ở `dieu_phoi`, bên gọi **tự khai** thứ tự | khai ra thì không phải là lén |
| `AmbiguousProviderError` **không** cascade | lượt đầu có thể đã tạo tác dụng phụ |
| Một hồ sơ text công khai | hai hồ sơ = llama-swap giết lượt đang chạy, `ConnectionReset` ngẫu nhiên |
| `llama-server` vĩnh viễn loopback | nó không có xác thực |
| Không bắt prompt/response | llama-swap **có sẵn** `/api/captures/*`; ta cố ý không dùng |
| Ngân sách token dẫn xuất một nguồn | 7 mắt xích đã khoá bằng `test_334` |

---

## 4. Thứ đã CÂN NHẮC rồi TỪ CHỐI

| | Vì sao từ chối |
|---|---|
| **LiteLLM** vào đường request | dựng `LTT → LiteLLM → cổng → llama-swap → llama.cpp`: thêm tầng, thêm điểm hỏng, và **thay một lớp phân loại lỗi đã đúng bằng một lớp đa dụng** |
| **Prometheus / Grafana / Langfuse** thường trú | ba tiến trình nữa **trên chính máy đang tranh GPU** với ComfyUI và việc video |
| **GuideLLM / Promptfoo** làm phụ thuộc | mượn *phương pháp* và *hình dạng kết xuất*, không mượn công cụ |
| Nâng binary llama.cpp trong đợt này | "mới hơn" ≠ "tốt hơn"; đổi engine phải đi qua đo |
| Mã lỗi **504** ra tới khách | đòi mã mới trong hợp đồng Public API + golden API + compat, để đổi lấy một sắc thái ngữ nghĩa |
| Đối chiếu ngược "test X phải nhắc lại A.py" | **đo trước khi từ chối**: nó báo động nhầm `features.py → test_212`, một viện dẫn đúng |
| Cho `APIKEY_ERROR` tự hồi | đổi hành vi **toàn nền tảng**, chạm mã sát tiền — quyết định riêng |

---

## 5. Bề mặt HTTP của cổng — sau đợt này

| Đường | Auth | Đổi gì |
|---|---|---|
| `GET /live` | không | — |
| `GET /health` | có | **+`thuong_nguon.phien_ban`**, **+`dem`** |
| `GET /v1/models` | có | — |
| `POST /v1/{chat/completions,responses,messages}` | có | **+504** tách khỏi 502 |
| `GET /metrics` | — | **404, có chủ ý** — không phơi ra LAN |

---

## 6. Giới hạn còn lại — nói thẳng

1. **`llama_cpp.build` = `null`.** Không chứng minh được từ máy A; bốn đường đều
   không trả lời. Điền khi chạy `nghiem_thu.py` trên máy B.
2. **Chưa có baseline hiệu năng đo thật.** Công cụ so sánh đã có
   (`tools/so_sanh_bench_llm.py`), số thì chưa — chạy benchmark chiếm suất đồng
   thời duy nhất và đá văng hồ sơ đang thường trú, nên nó cần một lượt được
   đồng ý. ⇒ **W3 không được chấm 98.**
3. **Khách vẫn nhận 503 cho lượt hết giờ**, không phải 504. Ranh giới cố ý.
4. **`APIKEY_ERROR` không tự hồi.** Nguồn sinh ra nó từ phía LLM đã bị cắt;
   bản thân cơ chế thì nằm ngoài phạm vi.
5. **22 số hiệu test trùng trên toàn kho.** Nguyên nhân gốc của một chú thích
   sai; sửa là đổi tên tệp của phiên khác.
