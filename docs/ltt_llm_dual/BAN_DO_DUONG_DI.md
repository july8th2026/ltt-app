# BẢN ĐỒ ĐƯỜNG ĐI — LLM nội bộ (hai card, sáu suất)

> **Đọc tệp này TRƯỚC khi sửa bất cứ gì trong đường LLM.** Nó trả lời đúng một
> câu: *"một lượt thật đi qua những đâu, và mỗi chặng ai gác?"*
>
> ⛔ Ngày 13/09/2026 ba bản vá liên tiếp của L-08 đều gắn vào một cánh cửa
> **không lượt nào đi qua**. Không ai sai về kỹ thuật; cái thiếu là tờ bản đồ
> này. Nó sinh ra từ đúng ba lần mất công ấy.

---

## 1. Hình dạng hệ, một hình

```
             máy A (nền tảng)                        máy B (GPU)
  khách ──► /api/v1/messages ──► phòng chờ ──► suất ──► llama-server
                                   │                      ├── ltt_38_3090  3 suất
                                   │                      └── ltt_35_5060  3 suất
                              người thứ 7
                               xếp hàng
```

**6 suất tổng** (3 mỗi model, hai khoá advisory độc lập). Người thứ bảy **xếp
hàng**, không bị từ chối — trừ khi phòng chờ chạm trần thì mới 429.

| model | tài nguyên | suất | pool KV |
|---|---|---|---|
| `ltt-3.8` | `ltt_38_3090` | 3 | 221.184 |
| `ltt-3.5` | `ltt_35_5060` | 3 | 262.144 |

⚠️ **Đừng gõ lại bốn con số này ở nơi khác.** Nguồn là
`apps/ltt_llm/manifest.py` (`admission_theo_model`) lấy từ
`apps/ltt_llm/ngan_sach.py`. Hỏi bằng `tool.admission_cho(model)`.

⚠️ **Tài liệu viết TRƯỚC 11/09/2026 khai `DONG_THOI_MAY_B = 1` / `--parallel 1`.**
Con số ấy **đúng tại thời điểm đó** — máy B khi ấy thật sự một suất. Rà 13/09
thấy ~40 tệp còn mang nó; phần lớn là **bản ghi có ngày** (báo cáo sự cố, audit,
nhật ký benchmark) nên **cố ý giữ nguyên**: sửa một bản ghi là làm giả bằng
chứng. Gặp chúng thì đọc như lịch sử, và hỏi `ngan_sach.py` cho con số hôm nay.

⛔ Lý lẽ đi kèm con số ấy — *"speculative decoding chỉ tối ưu một luồng"* — đã
   **đo lại và bị bác** (multijob M-1, 11/09; `llama-swap.yaml:151`). Nếu thấy
   nó ở một tài liệu **đang sống** (không phải bản ghi có ngày), đó là tệp cần
   sửa, không phải tệp cần tin.

## 2. Bốn cửa vào — và **chỉ một** cửa stream thật

| cửa | tệp | dùng khi |
|---|---|---|
| **stream** | `server/api/streaming.py` | `/api/v1/messages`, `/api/v1/responses` |
| đồng bộ | `server/api/chat.py` | `/api/v1/chat/completions` (từ chối `stream:true`) |
| job | `server/api/jobs.py` | `/api/v1/jobs` — hàng đợi bền |
| nội bộ | `runtime_noi_bo/luong.py:mo_luong` | ChatLTT, prompt_canh — **không** qua HTTP công khai |

Trong `streaming.py` có đúng **hai** `return StreamingResponse`:

1. **sandbox** (`_luong_thu`) — khoá thử, không chạm GPU, không chạm sổ tiền.
   Được miễn mọi lớp bảo vệ vì nó không có suất nào để nhả.
2. **cửa thật** — mọi lượt còn lại.

🔴 `tests/test_1248_mot_cua_stream_duy_nhat.py` **cưỡng chế** con số này. Thêm
cửa thứ ba mà quên bảo vệ ⇒ gate đỏ. Đó là chủ ý: thêm cửa là việc lớn.

## 3. Một lượt thật đi qua đâu

```
streaming.py
  └─ tien_kiem()                     alias · đầu vào · trần 413 · số dư 402 · phòng đầy 429
     │                               ⭐ MỌI lỗi ở đây là MÃ HTTP THẬT (trước 200)
     └─ luong_co_cho()               ← thân phản hồi, là generator ĐỒNG BỘ
        ├─ vao_va_cho()
        │  └─ phong_cho.cho_nhan()   xếp hàng, nhả nhịp SSE `: ltt-cho ...`
        │     └─ admission.xet_va_giu()   ← **suất sinh ra ở đây**
        ├─ thanh_toan.giu_cho_luot()  giữ tiền SAU khi được nhận
        ├─ mo_thuong_nguon()
        │  └─ luong_vlm.mo()          mở httpx tới máy B (read timeout 900 s)
        └─ _phat()                    `with keep_alive(...)` rồi `yield` từng khối
```

⚠️ **Sau khi đã trả 200 thì không còn mã HTTP.** Mọi kết cục xấu từ đó là một
khối lỗi SSE đúng khuôn. Đi tìm "vì sao khách nhận 500" mà lượt đã stream rồi
là đi nhầm tầng.

## 4. Suất được nhả thế nào — **ba lớp**, đọc kỹ trước khi thêm lớp thứ tư

| lớp | cơ chế | ở đâu | chặn trên |
|---|---|---|---|
| **1 chính** | `khi_dut` → `_nha_suat` | `streaming.py`, gọi từ `finally` của `bat_dong_bo_hoa` | ~0,05 s |
| **2 lưới** | nhịp tim chỉ đập khi **có byte đi qua**; im quá trần thì luồng nhịp tự nhả | `admission.keep_alive(con_song=...)` | `TRAN_IM_LANG_S` |
| **3 chặn cuối** | `reclaim_expired` | `admission.py`, chạy khi có ai `acquire` | 20 phút |

🔑 **Vì sao cần cả ba** — và đây là bài học đắt nhất của hạng mục này:

- `starlette/responses.py:250` chỉ `async for`, **không bao giờ `aclose()`** thân
  phản hồi ⇒ `finally` của generator **không được bảo đảm chạy đúng lúc**.
- `starlette/background.py` **không** bọc `CancelScope(shield=True)` ⇒
  `BackgroundTask` có thể bị huỷ trước khi chạy (`Kludex/starlette#1438`, chỉ xảy
  ra khi có `BaseHTTPMiddleware` — ta có **bốn** tầng).
- Trước 13/09, nhịp tim đập **vô điều kiện** ⇒ nó chứng minh *luồng còn sống*
  chứ không chứng minh *công việc còn tiến triển* ⇒ lớp 3 **không bao giờ khai
  hoả**, và suất bị giữ **vĩnh viễn** chứ không phải chỉ lâu.

## 5. Tiền được kết thế nào

Hai đường **độc lập**, `da_quyet_toan` bảo đảm chỉ một đường thật sự thu:

1. `finally` của `_phat` — đường thường.
2. `dam_bao_quyet_toan(luot)` trong `BackgroundTask` — chạy cả khi thân **chưa
   từng được đọc** (khách ngắt trước byte đầu).

⛔ Đường 2 **cộng thêm**, không thay thế. Bỏ đường 1 để "gọn" là đổi hai đường
độc lập lấy một — và đường còn lại chính là đường có lịch sử bị huỷ.

## 6. Sửa ở đây thì đọc gì

| muốn biết | nguồn chân lý |
|---|---|
| suất · pool · tài nguyên | `apps/ltt_llm/ngan_sach.py` → `manifest.py` |
| luật nhận ai trước | `platform_core/llm/luat_nhan.py` |
| hàng đợi + sổ từng lượt | `platform_core/llm/phong_cho.py` (`llm_waiters`) |
| cấp/nhả suất | `platform_core/llm/admission.py` |
| cư trú model trên card | `platform_core/llm/residency.py` |
| tiền | `platform_core/llm/thanh_toan.py` |
| sổ lỗi đã đóng/còn mở | `docs/ltt_llm_dual/SO_LOI_DO_TAI.md` |

## 7. Ba cái bẫy đã cắn thật — đừng dẫm lại

1. **Vá nhầm cửa.** Hỏi *"lượt thật đi đường nào"* **trước** khi đọc mã. Cách
   hỏi rẻ nhất: `tool.admission_cho(model)` — có khai ⇒ đi phòng chờ.
2. **Bản giả tự mở trói.** Bộ kiểm cũ của L-08 xanh suốt vì nguồn giả tự tỉnh
   dậy khi bị đóng; máy B không làm thế. Bản giả phải khác vật thật ở **mọi**
   chiều **trừ** chiều đang đo.
3. **Phép kiểm chốt vị trí dòng.** `ham.body[0] is Try` đỏ ngay khi thêm một
   docstring. Chốt **bất biến**, đừng chốt **hình dạng văn bản**.
