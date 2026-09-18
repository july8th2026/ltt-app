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

| model | tài nguyên | suất | pool KV (A đặt chỗ) |
|---|---|---|---|
| `ltt-3.8` | `ltt_38_3090` | 3 | 212.992 |
| `ltt-3.5` | `ltt_35_5060` | 3 | 253.952 |

⚠️ **Đừng gõ lại các con số này ở nơi khác.** Nguồn là **hồ sơ theo model**
`apps/ltt_llm/ngan_sach.HO_SO[id]` (phương án C, 17/09/2026) → `manifest.py`
(`_khai_admission`) → `platform_core.registry.AdmissionModel`. Hỏi bằng
`tool.admission_cho(model)`. Pool = `-c` − `BIEN_POOL_TOKEN` (8.192, chủ dự án
chốt 17/09: draft MTP + sai số ước chiếm KV mà phép đặt chỗ không đếm).

Mỗi `AdmissionModel` mang đủ số của model — `slots`, `token_pool`,
`nguong_whale` (số chủ dự án chọn 17/09, L-23: 3.8 **8.192**, 3.5 **16.384** —
`ngan_sach.NGUONG_WHALE`; ước đường cong ở 9 s 10.752/18.944 chỉ là ghi chú),
`dem_uoc`, `token_giu_moi_anh`. ⛔ Không còn env
`LTT_LLM_NGUONG_WHALE` / `LTT_LLM_DEM_DAT_TRUOC` / `LTT_LLM_TOKEN_MOI_ANH`; env
thời gian (chờ, backfill, lão hoá, xếp lại) chỉ ở `tham_so_da_luot.doc()`.

**Máy A là người quyết định duy nhất; máy B là rào vật lý** (`seq ≤ -np`,
`Σ đặt chỗ ≤ -c`). A ⊆ B: pool A nhỏ hơn `-c` của B, và A gửi CÙNG số đặt chỗ
lên B (`X-LTT-Token-Dat`) ở mọi cửa.

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
     │                               (phòng đầy = SỐ người/whale, KHÔNG token — L-12b;
     │                                "có vừa pool KV" chỉ hỏi ở luat_nhan luật 2)
     │                               ⭐ MỌI lỗi ở đây là MÃ HTTP THẬT (trước 200)
     └─ luong_co_cho()               ← thân phản hồi, là generator ĐỒNG BỘ
        ├─ vao_va_cho()
        │  └─ phong_cho.cho_nhan()   xếp hàng, nhả nhịp SSE `: ltt-cho ...`
        │     └─ admission.xet_va_giu()   ← **suất sinh ra ở đây**
        ├─ thanh_toan.giu_cho_luot()  giữ tiền SAU khi được nhận
        ├─ mo_co_xep_lai()            ⭐ B 429 ⇒ nhả suất, XẾP LẠI dòng chờ
        │  │                          (giữ created_at), chờ lại trong hạn,
        │  │                          ≤ so_lan_xep_lai_toi_da (3) — GIỮ tiền
        │  └─ mo_thuong_nguon()
        │     └─ luong_vlm.mo()       mở httpx tới máy B (read timeout 75 s ở cửa
        │        │                    /api/v1; header X-LTT-Token-Dat)
        │        └─ máy B `llm_gateway/api.py`   RÀO VẬT LÝ (phương án C, bước 3):
        │           ├─ 413  vào > `-c − max_out − DEM_UOC` của ĐÚNG model
        │           └─ 429  chuỗi đang chạy = `-np`, hoặc Σ đặt chỗ + lượt này > `-c`
        │              (`llm_gateway/vat_ly.py` đọc `-c`/`-np` từ `llama-swap.yaml`)
        └─ _phat()                    `with keep_alive(...)` rồi `yield` từng khối
```

**Một chỗ tính đặt chỗ + gắn cờ whale cho MỌI cửa:**
`tham_so_da_luot.luat_cho(AdmissionModel, …)`:
`đặt chỗ = vào_ước + max_tokens + dem_uoc + ảnh × token_giu_moi_anh`,
`whale ⇔ token_prefill_mới ≥ nguong_whale` (stream dùng `uoc_moi`; đồng bộ/job/
planner dùng `vào_ước`). Đặt chỗ > pool ⇒ **ném** `DatChoVuotPool` (cửa trả 413 /
job hỏng không thử lại) — không còn kẹp im lặng. Kẹp `max_tokens` theo ngữ cảnh
(`tran_theo_ngu_canh`) tính trên **pool**, nên mọi lượt qua trần vào đều vừa pool.

**Cửa đồng bộ** (`chat.py`, nhánh một-cục `streaming.py`): `cho_suat_dong_bo` →
giữ tiền → `goi_dong_bo_co_xep_lai` (B 429 ⇒ xếp lại trong ngân sách thời gian
cửa; mỗi lần gọi bọc `dieu_phoi.mang_dat_cho`) → nhả suất ĐANG giữ
(`giu_suat_dong_bo` / `_release_ticket` đọc `suat.lease_id` lúc nhả).
**Cửa job**: `job_runner` bọc handler trong `dieu_phoi.mang_dat_cho(lease)`;
B 429 ⇒ `BanError` ⇒ `defer_resource` (job về hàng, giữ tiền — như trước).

### 3b. Máy B = rào vật lý, KHÔNG phải bộ nhận thứ hai

⭐ **Máy A là người quyết định nhận DUY NHẤT** (`docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md`
§3). Cổng máy B không có luật công bằng, nhịp hay hạn mức riêng — khoá whale
(O-01), RPM (O-03), trần vào chung cho hai model (O-02) và env
`LTT_LLM_MAX_DONG_THOI`/`LTT_LLM_TOKEN_POOL`/`LTT_LLM_MAX_INPUT_TOKENS`/`LTT_LLM_RPM`
**đã gỡ**. Nó chỉ chặn điều engine không tự chặn được:

| chốt ở B | số lấy từ đâu | vượt thì |
|---|---|---|
| chuỗi đang chạy ≤ `-np` | `llama-swap.yaml`, từng hồ sơ | 429 |
| Σ token đặt chỗ ≤ `-c` (`-kvu`: một bể) | `llama-swap.yaml`; đặt chỗ = header `X-LTT-Token-Dat` của A | 429 |
| token vào ≤ `-c − max_out − DEM_UOC` | yaml + `gateway.env` (ghi từ `apps/ltt_llm/ngan_sach.py` lúc deploy) | 413 |

🔑 **B 429 ⇒ A XẾP HÀNG LẠI**, không trả lỗi cho khách (`mo_co_xep_lai` /
`goi_dong_bo_co_xep_lai` ở trên, O-04): 429 của B chỉ còn nghĩa là tràn vật lý thật
trong khe nhả suất A/B. Hợp đồng hai phía có phép kiểm:
`tests/test_1223_phuong_an_c_rao_vat_ly_b.py` (B) và `tests/test_1229_phuong_an_c_hop_dong.py` (A).

⚠️ **Sau khi đã trả 200 thì không còn mã HTTP.** Mọi kết cục xấu từ đó là một
khối lỗi SSE đúng khuôn. Đi tìm "vì sao khách nhận 500" mà lượt đã stream rồi
là đi nhầm tầng.

## 4. Suất được nhả thế nào — **ba lớp**, đọc kỹ trước khi thêm lớp thứ tư

| lớp | cơ chế | ở đâu | chặn trên |
|---|---|---|---|
| **1 chính** | `khi_dut` → `_nha_suat` | `streaming.py`, gọi từ `finally` của `bat_dong_bo_hoa` | ~0,05 s |
| **2 lưới** | nhịp tim chỉ đập khi **có byte đi qua**; im quá trần thì luồng nhịp tự nhả | `admission.keep_alive(con_song=...)` | `TRAN_IM_LANG_S` |
| **3 chặn cuối** | `reclaim_expired` | `admission.py`, chạy khi có ai `acquire` | 20 phút |

⚠️ **Máy B có sổ suất riêng** (`llm_gateway/gioi_han.py`), nhả khi luồng đóng ở
B — có thể **sau** khi A đã nhả lease. Trong khe đó một lượt A vừa nhận có thể
ăn 429 của B; đường đúng là A **xếp lượt ấy lại hàng chờ** (O-04), không phải
thêm một lớp nhả thứ tư. B còn một lưới thu hồi suất treo riêng
(`gioi_han.HAN_IM_LANG_MAC_DINH_S` — từ 18/09 tính theo IM LẶNG: mỗi chunk/nhịp tim gia hạn suất, không thu lượt dài đang chạy).

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
   từng được đọc** (khách ngắt trước byte đầu). Có suất + tiền mà luồng **chưa
   từng mở** (khách đi trong lúc xếp lại) ⇒ `BackgroundTask` hoàn (`hoan`,
   idempotent).

💰 **Tiền theo LƯỢT, không theo lần thử** (phương án C bước 1): xếp lại sau 429
của B **không** hoàn rồi giữ lại — `credit.hoan` kết sổ vĩnh viễn theo mã lượt, nên
giữ lại cùng `request_id` là một khoản giữ không bao giờ kết sổ. Một lượt = một
`hold` + một `settle` **hoặc** một `refund`, ở mọi đường ra. Đây là ngoại lệ có
tên duy nhất của INV-MJ-1 ("đang chờ thì không giữ tiền"): lượt ĐÃ được nhận
một lần rồi mới quay lại hàng.

⛔ Đường 2 **cộng thêm**, không thay thế. Bỏ đường 1 để "gọn" là đổi hai đường
độc lập lấy một — và đường còn lại chính là đường có lịch sử bị huỷ.

## 6. Sửa ở đây thì đọc gì

| muốn biết | nguồn chân lý |
|---|---|
| suất · pool · ngưỡng whale · đệm ước · token/ảnh (theo model) | `apps/ltt_llm/ngan_sach.py::HO_SO` → `manifest.py` → `AdmissionModel` |
| phép tính đặt chỗ + cờ whale (MỘT chỗ, mọi cửa) | `platform_core/llm/tham_so_da_luot.py::luat_cho` |
| luật nhận ai trước (ngân sách KV · backfill có chặn · whale) | `platform_core/llm/luat_nhan.py` |
| núm sức chứa theo tài nguyên (số suất, pool — chỉ hạ) | `platform_core/registry.py::ap_cau_hinh_admission` |
| trần chờ, trần hàng, cửa sổ backfill, lão hoá, xếp lại sau 429 (env) | `platform_core/llm/tham_so_da_luot.py::doc` |
| B 429 ⇒ xếp lại (stream / đồng bộ) | `runtime_noi_bo/luong.py::mo_co_xep_lai`, `goi_dong_bo_co_xep_lai` |
| `X-LTT-Token-Dat` (stream / đồng bộ, job) | `llm/luong_vlm.py::mo` / `llm/dieu_phoi.py::mang_dat_cho` |
| hàng đợi + sổ từng lượt | `platform_core/llm/phong_cho.py` (`llm_waiters`) |
| cấp/nhả suất | `platform_core/llm/admission.py` |
| cư trú model trên card | `platform_core/llm/residency.py` |
| rào vật lý máy B (`-c`, `-np`, trần vào theo model, giữ chỗ) | `llm_gateway/vat_ly.py` ← `llama-swap.yaml` |
| thứ tự deploy khi đổi sức chứa (tăng ⇒ B trước, giảm ⇒ A trước) | `docs/ltt_llm_dual/RUNBOOK.md` §2.1 |
| tiền | `platform_core/llm/thanh_toan.py` |
| suy nghĩ: gỡ ghi đè budget/bật-tắt + thẻ `<\|think_*\|>`, chuẩn hoá effort theo model (MỘT hàm, mọi cửa; L-26) | `runtime_noi_bo/luong.py::chuan_hoa_suy_nghi` ← gọi từ `tien_kiem`, `chuan_bi`, `streaming._cua` (một cục), `apps/ltt_llm/features.kiem_tham_so` (đồng bộ/job) |
| mức suy nghĩ từng model (catalog `/api/v1/models`, catalog Codex, LTTCODE) | `platform_core/public_api/examples.py` (`CODEX_MODEL_REASONING*`, `muc_suy_nghi`) |
| budget suy nghĩ | chỉ `--reasoning-budget` trong `llama-swap.yaml`; sàn `max_tokens` 3.5 = budget + 512 (`ngan_sach.BUDGET_SUY_NGHI_35`, `test_1430` đối chiếu yaml) |
| sổ lỗi đã đóng/còn mở | `docs/ltt_llm_dual/SO_LOI_DO_TAI.md` |

## 7. Ba cái bẫy đã cắn thật — đừng dẫm lại

1. **Vá nhầm cửa.** Hỏi *"lượt thật đi đường nào"* **trước** khi đọc mã. Cách
   hỏi rẻ nhất: `tool.admission_cho(model)` — có khai ⇒ đi phòng chờ.
   ⛔ Và đừng thêm luật nhận vào cổng máy B: hai bộ nhận chồng nhau chính là
   nguồn 429/413 **sau 200** mà phương án C dẹp (§3b).
2. **Bản giả tự mở trói.** Bộ kiểm cũ của L-08 xanh suốt vì nguồn giả tự tỉnh
   dậy khi bị đóng; máy B không làm thế. Bản giả phải khác vật thật ở **mọi**
   chiều **trừ** chiều đang đo.
3. **Phép kiểm chốt vị trí dòng.** `ham.body[0] is Try` đỏ ngay khi thêm một
   docstring. Chốt **bất biến**, đừng chốt **hình dạng văn bản**.
