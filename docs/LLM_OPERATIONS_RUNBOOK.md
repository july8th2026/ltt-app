# LLM_OPERATIONS_RUNBOOK — trực LTT LLM

Viết 2026-09-09 (chương trình MASTER UPGRADE). Dành cho người **đang có sự cố**,
nên mỗi mục bắt đầu bằng *câu lệnh*, không bằng lời giải thích.

> ⛔ Đừng gõ lại một con số nào từ đây vào tài liệu khác. Số sống ở
> `apps/ltt_llm/ngan_sach.py` và ở `GET /health` của máy B.

```
MÁY A  192.168.2.17   nền tảng, cổng 8100
MÁY B  192.168.2.66   cổng VLM 8299 -> llama-swap 8280 -> llama-server 8281
```

---

## 0. Ba câu hỏi đầu tiên, theo đúng thứ tự

```bash
curl -s -m 8 http://192.168.2.66:8299/live
```

| Trả lời | Nghĩa |
|---|---|
| `{"ok":true,...}` | tiến trình còn thở → sang câu 2 |
| không nối được | máy B/dịch vụ chết → §3 |
| treo | mạng hoặc máy B quá tải → §3 |

**Câu 2** — `/health` (cần bearer). Đọc theo thứ tự này, **đừng đọc từ trên
xuống**: bốn trường dưới đây trả lời bốn câu hỏi khác nhau.

| Trường | Trả lời câu |
|---|---|
| `duoi_dich_vu` | *"tiến trình này có NÊN đang chạy không"* — chốt duy nhất nhìn ra **health xanh giả** (mồ côi sau khi vỏ NSSM chết) |
| `gpu.tren_gpu` | *"model có THẬT nằm trên card không"* — chốt duy nhất nhìn ra sự cố CUDA 23/08, mọi trường khác vẫn xanh khi model bò trên CPU |
| `gioi_han.giu_lau_nhat_giay` | *"có suất nào bị treo không"* — sự cố 31/08 |
| `dem.theo_nhom` | *"đã từ chối bao nhiêu lượt, vì cái gì"* — lịch sử, không phải trạng thái |

**Câu 3** — máy B đang chạy bản nào:
`/health` → `thuong_nguon.phien_ban.swap.version`.
`null` ⇒ llama-swap quá cũ hoặc chưa lên; so với `llm_gateway/deploy/phien_ban_ghim.json`.

---

## 1. Khởi động / dừng (trên máy B)

```powershell
Start-Service LTTLlamaSwap ; Start-Service LTTLlmGateway     # BAT: swap truoc
Stop-Service  LTTLlmGateway ; Stop-Service  LTTLlamaSwap     # DUNG: gateway truoc
```

⛔ **Thứ tự không hoán vị được.** Gateway gọi xuống llama-swap. Quên dừng swap
thì `.exe` bị khoá và mọi lần chép đè thất bại với *"being used by another
process"*.

### Cổng không khởi động lại được

Đọc log. Ba thông điệp, ba nguyên nhân **khác hẳn nhau**:

| Log | Nghĩa | Xử lý |
|---|---|---|
| `CONG 8299 DA CO NGUOI GIU (pid N)` | tiến trình **mồ côi** sống sót sau khi vỏ NSSM chết. `/health` của nó **vẫn xanh** — đừng tin | `Stop-Process -Id N -Force` rồi `Start-Service` |
| `TU CHOI KHOI DONG: LTT_LLM_HOST=... nhung LTT_LLM_TOKEN rong` | fail-closed đang làm đúng việc | đặt token (xem dưới) |
| `LTT_LLM_MODELS rong -> KHONG mo model nao` | fail-closed Q92, **không phải lỗi** | đặt `LTT_LLM_MODELS=qwen38-api,qwen38-vision` |

### 🔴 Sửa `gateway.env` rồi `Restart-Service` là KHÔNG ĐỦ

`nssm` **nướng cứng** biến môi trường vào cấu hình dịch vụ lúc **CÀI**. Đã dính
thật ba lần.

```powershell
setup\nap_lai_env.ps1
```

---

## 2. Máy B không với tới được

```bash
ping 192.168.2.66
curl -s -m 8 http://192.168.2.66:8299/live
```

⚠️ **`NODE_OFFLINE` ≠ máy tắt.** Ping trước khi kết luận. Windows Update có thể
tự khởi động lại máy B sau 01:00.

Đường vào máy B là **Nexus**, không phải SSH (SSH đang `DISABLED` có chủ ý, chỉ
là kênh cứu hộ). Xem `Ket_noi.md` trên Desktop máy A.

---

## 3. Máy A báo lỗi — đọc đúng mã, đừng gộp

Đây là bảng quan trọng nhất của cả runbook, vì **gộp hai mã ở đây đã từng làm
tắt model nhà**.

| Cổng trả | Nghĩa | `api_pool` có phạt khoá? | Việc phải làm |
|---|---|---|---|
| **429** `cong dang day` | hết suất của chính cổng | **không** | xem `giu_lau_nhat_giay` — nghi suất treo |
| **429** `may B dang ban` | việc ảnh/video đang giữ card | **không** | chờ; đây là bình thường |
| **429** `card chua san sang` | ComfyUI không nhả VRAM | **không** | §5 |
| **413** | vượt trần token/ảnh | **không** | client phải nén hội thoại |
| **404** | model chưa mở | có | kiểm `LTT_LLM_MODELS` |
| **504** | thượng nguồn **không trả lời kịp** | **không** | §6 |
| **502** | thượng nguồn **hỏng thật** | **có** | §3 |

🔴 **Vì sao 504 phải tách khỏi 502.** Trước 09/09 cả hai đi chung cửa 502. Máy A
đọc 502 → `danh_dau_loi` → sau **5** lần `key.status = APIKEY_ERROR`, và
`APIKEY_ERROR` **không tự hồi**. Tức năm lần hết giờ là model nhà tắt và **ở lại
tắt**. Mà prefill 200K mất hàng phút là công việc hằng ngày của hệ này.

### Khoá đã bị đẩy vào `APIKEY_ERROR`

Triệu chứng: mọi lượt LLM nội bộ trả *"khong co API key kha dung"*, GPU rảnh.
`_ung_vien` bỏ mọi khoá `status != ACTIVE`, và **chỉ `COOLDOWN` mới tự hồi**.
⇒ Phải đưa khoá về `ACTIVE` bằng tay (trang admin khoá API).

---

## 4. GPU bận / ComfyUI giữ card

```bash
curl -s http://192.168.2.66:8299/health   # -> trong_tai.ly_do, gpu.vram_dung_mb
```

* `trong_tai.ban = true` → có việc khác đang chạy. **Chờ là đúng.**
* 429 `card chua san sang` → ComfyUI giữ VRAM và không nhả sau khi render xong.

🔴 **Vì sao phải dọn**: đo 22/08 — card bẩn (ComfyUI giữ 6.211 MiB) → **18,2
tok/s**; card sạch → **63,3 tok/s**. Chênh 3,5 lần, và llama.cpp **không báo
lỗi** — nó tràn trọng số sang RAM chủ qua PCIe, `/health` vẫn xanh.

⇒ Nếu tốc độ tụt mà không có lỗi nào: nghi **tràn sang RAM chủ** trước, đừng
nghi model.

---

## 5. Chậm bất thường

Thứ tự chẩn đoán, rẻ trước:

1. `/health` → `gpu.tren_gpu`. `false` ⇒ model **không** trên card → §4.
2. `/health` → `dem.ttft.trung_binh_giay` và `cao_nhat_giay`.
3. `/health` → `phien_ban` — có ai vừa nâng llama.cpp không?
4. llama-swap `/metrics` (loopback máy B) — prefill/decode tok/s, KV cache, và
   `llamacpp:spec_decode_num_accepted_tokens_per_pos_total` (tỉ lệ chấp nhận
   suy đoán).

⚠️ Máy B là **một máy để bàn đang dùng**: đo 31/08 có **23 tiến trình** trên
card. Trước khi gọi một con số là hồi quy, xem có ai đang cuộn trình duyệt không.

### So với baseline

```bash
python tools/bench_llm_hieu_nang.py --url http://192.168.2.66:8299 --ra moi.json
python tools/so_sanh_bench_llm.py --nen baseline.json --moi moi.json
```

⛔ Benchmark chiếm **suất đồng thời duy nhất** vài phút và **đá văng** hồ sơ
đang thường trú. Đừng chạy lúc có người đang dùng.

---

## 6. Lỗi ngữ cảnh / token

`413` = đầu vào vượt trần **của máy B**. Ba con số, ba tầng, đừng nhầm:

```
cửa sổ engine  >  trần vào  >  công bố cho client
```

Đọc số hôm nay ở `apps/ltt_llm/ngan_sach.py`, hoặc `/health` →
`tran.input_tokens`. **Đừng gõ lại chúng vào bất kỳ tài liệu nào** — đúng chỗ
này đã trôi hai lần (xem `apps/ltt_llm/manifest.py`).

⚠️ Hai trần **không liên quan** nhau mà cái nhỏ hơn luôn thắng: trần **byte**
của thân request từng chặn hội thoại ở ~64.000 token trong khi ai cũng tưởng
đang chạm trần **token**. Lỗi nay có `limit_name` — đọc nó.

---

## 7. Sự cố tính tiền

Nguyên tắc: **không đo được thì không thu.** `usage` thiếu ⇒ hoàn đủ + ghi cảnh
báo. Nếu cảnh báo đó xuất hiện thường xuyên thì có thứ **khác** đang hỏng.

Ba cửa, ba chỗ quyết toán — cả ba theo số **đo được**, không theo trần:

```
stream   runtime_noi_bo/luong.py  `finally` cua `_phat`  +  dam_bao_quyet_toan()
đồng bộ  thanh_toan.quyet_toan_hoac_hoan
job      features.gia_that_credit();  do_duoc=False -> 0
```

🔴 **Hold mồ côi.** Nếu thấy một dòng `hold` không có `settle`/`hoan` đi kèm:
cửa stream có **hai** đường quyết toán độc lập từ 09/09 (`finally` + lưới an
toàn chạy từ `BackgroundTask`), nên một hold mồ côi **sau ngày đó** là một
khuyết tật mới — đừng vá bằng tay trước khi tìm ra đường nào đã im lặng.

---

## 8. Deploy và hoàn nguyên

```powershell
llm_gateway\deploy\deploy.ps1          # chep ma nguon + llama-swap.yaml
llm_gateway\deploy\nang_llamacpp.ps1   # mac dinh = ban GHIM
llm_gateway\deploy\nang_llamacpp.ps1 -HoanNguyen
```

* `deploy.ps1` chụp `releases/auto-<thời điểm>` **trước** mỗi lượt.
* Chép `llama-swap.yaml` **không** tự khởi động lại `LTTLlamaSwap`. Cấu hình mới
  chỉ có hiệu lực sau `Restart-Service LTTLlamaSwap` — và việc đó **unload
  model**. Script có cảnh báo; đừng bỏ qua nó.
* `nang_llamacpp.ps1` mặc định lấy **bản ghim**, không phải bản mới nhất.
  `-Ban latest` phải gõ ra.

⛔ **Đừng xoá `bin\llamacpp` rồi giải nén bản mới.** Thư mục đó giữ các DLL
`cudart` nạp từ **một gói riêng**; gói `llama-*-bin-win-cuda-*.zip` không chứa
chúng. Chép đè, đừng xoá.

⛔ **Đừng sửa file trực tiếp trên máy B.** Lần cập nhật sau là mất trắng, **âm
thầm**.

---

## 9. Đọc log và số đo

```
H:/LTT_LLM/logs/gateway.log      gateway_err.log
H:/LTT_LLM/logs/llamaswap.log    llamaswap_err.log
```

llama-swap (loopback máy B): `/logs` · `/api/metrics/activity` (bền qua khởi
động lại) · `/api/hardware` · `/metrics`.

⛔ **Cổng 8299 không phơi `/metrics` ra LAN**, có chủ ý. Nó chỉ phơi số của
**riêng nó** ở `/health` → `dem`, vì đó là thứ llama-server không bao giờ nhìn
thấy: mọi lượt bị **từ chối** đều không chạm tới engine.

⛔ **Không bắt prompt/response.** llama-swap có sẵn `/api/captures/*`; ta cố ý
không dùng. Một con số không rò rỉ được gì; một prompt thì rò rỉ tất cả.

---

## 10. Sau một lần máy treo

```
C:\Users\Thang Tuong\Desktop\HOP DEN\KHAM.bat
```

⚠️ Hộp đen ghi giờ **UTC**; máy ở **UTC+7**. `09:51Z` = **16:51 giờ máy**.
