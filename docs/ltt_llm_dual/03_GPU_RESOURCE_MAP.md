# 03 — Bản đồ tài nguyên GPU máy B: mã giả định gì, máy thật ra sao

> Audit tĩnh trên `9e73bf1f` (= nền nhánh Multi-Job), 2026-09-11. Đường dẫn tương đối gốc kho.
> Trạng thái máy thật: `00_CURRENT_BASELINE.md` §3–5. `[INFERRED]` = suy luận, không đọc thẳng.
> ⚠️ Trunk `admin-mvp-v3` đi trước nền này 450 commit — kiểm lại từng dòng trên trunk trước khi sửa.

## 1. Giả định danh tính GPU

Hôm nay dòng 0 của `nvidia-smi` = index 0 = PCI `02:00.0` = 3090. Mọi phép đọc "dòng 0" trúng 3090
**nhờ thứ tự PCI**, không nhờ thiết kế.

| # | Chỗ | Đo gì | Trên máy 2 GPU đọc card nào | Hệ quả | Mức |
|---|---|---|---|---|---|
| a | `llm_gateway/deploy/llama-swap.yaml` (mọi hồ sơ) | `-ngl 999`, không `-dev`/`-sm`/`-mg`/`CUDA_VISIBLE_DEVICES` | llama.cpp thấy CUDA0+CUDA1 | Mặc định chia lớp Qwen qua cả hai card. Đã vá ở Multi-Job T1 (chưa deploy) | HIGH |
| b | `render_gateway/busy.py:146-186` `vram_dung_mb_qua_smi` | `memory.used` **max** mọi dòng | Card bận nhất = 3090 khi Qwen thường trú | Nuôi `xin_card` (`render_gateway/api.py:304-305`); ngưỡng 6.000 MB (`nhuong_card.py:56`) ⇒ **mọi job ảnh đi đường đuổi Qwen** kể cả khi ComfyUI chạy trên 5060 Ti | HIGH |
| c | `render_gateway/busy.py:189-234,434-435` `vram_ngoai_nhan_mb` | smi max − ComfyUI `/system_stats devices[0]` | Trộn hai card | VRAM Qwen tính là "người ngoài"; `VRAM_CAN_TOI_THIEU_MB = 20_500` (`busy.py:60`) > 16.311 ⇒ 5060 Ti **không bao giờ** qua được | HIGH |
| d | `render_gateway/busy.py:125-143` `tai_gpu_phan_tram` | `utilization.gpu` `dong[0]` | 3090 | Qwen decode ⇒ "có người đang tính" ⇒ job ảnh cho 5060 Ti chờ 45 s rồi 429 | HIGH |
| e | `llm_gateway/trong_tai.py:89-102` `_tai_gpu_mac_dinh` (+ nhánh `:261-285`) | util `dong[0]` + ComfyUI `queue_running` | 3090 | ComfyUI render trên 5060 Ti sẽ khiến Qwen bị 429 vô cớ | HIGH |
| f | `render_gateway/busy.py:63-106` `so_python_tinh_tren_gpu` (+ `trong_tai.py:118-131`) | `--query-compute-apps` không lọc GPU | Cả hai | ComfyUI + sidecar trên 5060 Ti ≥ 2 (`TRAN_PYTHON_GPU = 2`) ⇒ LLM 429 (`trong_tai.py:219-222`) | MED-HIGH |
| g | `llm_gateway/don_dep.py:47-70` `doc_vram_dung_mb` | `memory.used` `dong[0]` | 3090 (tình cờ) | Đảo thứ tự ⇒ đọc 5060 Ti (ComfyUI+màn hình) > 2.500 ⇒ 429 mọi lần nạp lạnh | MED (tiềm ẩn HIGH) |
| h | `llm_gateway/tren_gpu.py:63-83` qua `api.py:309-322` | VRAM dòng 0 vs 5.000 MB khi "có model nào chạy" | 3090 | Chỉ LTT-3.5 nạp ⇒ `/health` báo nhầm `dang_lo` | MED |
| i | `llm_gateway/deploy/nghiem_thu.py:71-78` (`splitlines()[0]`), bước 8 `:254-271` | VRAM 3090 sau render | 3090 | ComfyUI sang 5060 Ti ⇒ bước "ComfyUI CÓ giữ VRAM" hỏng/vô nghĩa | MED |
| j | `llm_gateway/deploy/chay_nghiem_thu.cmd:8-9,53-54` | `taskkill /f /im llama-server.exe` | Mọi instance | Giết cả llama-server của LTT-3.5 | MED |
| k | `render_gateway/diagnostics/gpu_check.py:47-50,101,112,144` | smi dòng 0, `gpus[0]`, `device="cuda"` | 3090 | Chẩn đoán sai card | LOW-MED |
| l | `tools/bench_llm_hieu_nang.py:57-60` | `split(",")` trên đầu ra nhiều dòng | Hỏng parse | Số bench mất nguồn gốc | LOW |
| m | `render_gateway/deploy/cai_dat_dich_vu.ps1:101`, `start_comfy_h37.ps1:65-66` | ComfyUI không `--cuda-device`/`CUDA_VISIBLE_DEVICES` | cuda:0 = 3090 (xác nhận log 09-11 08:58) | ComfyUI nằm trên card LLM | HIGH (với đích) |
| n | `platform_core/gpu.py`, `gpu_lease.py`, `gpu_claims.py:54-58` | có UUID, claim theo index | Máy A | Không deploy sang B | LOW |

## 2. Trọng tài ComfyUI ↔ LLM (đang sống)

**Phía LLM** (`llm_gateway/api.py:396-434`): ngân sách (413) → slot (429) → `TrongTai.phan_xu` (429,
Retry-After 30) → `DonDepGpu.bao_dam_sach` (bỏ qua nếu model mình đang chạy). `bao_dam_sach`
(`don_dep.py:157-199`): VRAM dòng 0 ≤ `LTT_LLM_VRAM_SACH_MB` (2.500) ⇒ sạch; không thì ComfyUI đang
chạy ⇒ không sạch; không thì `POST /free {unload_models, free_memory}` rồi thăm 6×3 s; vẫn bẩn ⇒ 429
Retry-After 60.

**Phía render** (`render_gateway/nhuong_card.py:158-292`): `xin_card` **đuổi** các "hộ" trong
`LTT_HO_DUNG_CARD` (máy B: `llm=http://127.0.0.1:8280/unload`) khi VRAM > 6.000 MB, chờ ≤ 45 s,
không đuổi khi có người đang tính, chống lật 300 s; hỏng ⇒ 429. `TraCard` (`:324-368`, bật vì
`LTT_TRA_CARD_GIAY=60`) gọi ComfyUI `/free` sau 60 s rảnh.

**Không có khoá/lease chung.** Phối hợp hoàn toàn qua trạng thái quan sát (nvidia-smi, `/queue`,
`/running`, `/unload`). `llm_gateway` import helper từ `render_gateway.busy` (`trong_tai.py:86,112`).

**Lỗi thời / sai khi 3090 chỉ cho LLM và ComfyUI sang 5060 Ti:** toàn bộ đường `don_dep` `/free`;
nhánh ComfyUI-queue + util của `trong_tai`; `xin_card` đuổi Qwen; heuristic VRAM/python của `busy.py`;
`TraCard`; chú thích `nhuong_card.py:4-14` ("một card 24.576"). Hoặc đo theo UUID, hoặc gỡ.
Và một trọng tài **mới** sẽ cần ở 5060 Ti (LTT-3.5 ↔ ComfyUI) — cùng hình dạng bài toán, khác card.

## 3. `llm_gateway` và hai model

Không phục vụ được hai model trên hai GPU cùng lúc nếu không sửa:
- llama-swap chạy **một model một lúc** (không `groups`) ⇒ nạp 3.5 sẽ gỡ 3.8.
- **Một** bộ đếm slot cho mọi model (`api.py:86-87`, `gioi_han.py`); `deploy.ps1:278-285` ép
  `LTT_LLM_MAX_DONG_THOI` về 1 mỗi lần deploy.
- Catalog hard-code `qwen38-api`/`qwen38-vision` (`catalog.py:93-106`); `max_input`/`max_output` một
  bộ (`config.py:124-125`); "có model nào đang chạy" một-model (`api.py:115-141`);
  `_ho_so_dang_nap` chỉ nhớ model đầu tiên (`api.py:181-185`) ⇒ `/tokenize` sai khi hai model chạy.
- Một `LTT_LLM_UPSTREAM_URL` thì **không** phải vấn đề (llama-swap định tuyến theo trường `model`).
- Hủy: `LuongUpstream.close` (`upstream.py:101-170`) + BackgroundTask. `X-Conversation-Id`: không có.

## 4. Công cụ deploy máy B

`deploy.ps1`: scp `llama-swap.yaml` nguyên văn (không template), **không** restart llama-swap, chụp
`gateway\` vào `releases/auto-<ts>` trước khi đè (lùi = xcopy ngược tay), `gateway.env` sửa tại chỗ
không sao lưu. `cai_dat_dich_vu.ps1`: một `LTTLlamaSwap` :8280, nhánh gỡ-cài-lại xoá env dịch vụ.
`nang_llamacpp.ps1`: sao lưu `bin\llamacpp.b<cũ>`, lùi `-Ban <cũ>` tường minh.
`phien_ban_ghim.json` **chỉ có trên trunk** (không có ở `9e73`) — thêm một dấu hiệu nền cũ.
