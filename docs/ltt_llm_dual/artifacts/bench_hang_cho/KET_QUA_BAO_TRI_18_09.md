# Kết quả cửa sổ bảo trì máy B — 18/09/2026

**Một dòng:** giữ `--cache-ram 12288` + `--ctx-checkpoints 8` (cả hai model), `-b 512 -ub 512`
(chỉ 3.8), `-watch-config` cho `LTTLlamaSwap`. **24576 đề nghị ở `KET_QUA_CACHE_18_09` §7
đã được bật rồi hạ** — nó làm máy B ngừng bán ~10 phút (§2). `-c`/`-np` không đổi ⇒ máy A
không cần đổi gì. Quyết định: `DECISION_LOG.md` L-24; vận hành: `RUNBOOK.md` §2.3b.

## 0. Điều kiện

| mục | giá trị |
|---|---|
| Giờ | 06:20–07:55 (UTC+7). Trước khi bắt đầu: `/running` rỗng (cả hai model đã tự nhả theo `ttl`), không `POST` nào trong `gateway_err.log`, GPU rảnh |
| Engine | `b10883-91f6a6cf3`, llama-swap v250 |
| Đường đo | production `https://app.lttstudios.com/api/v1/messages` SSE, khoá thử `secrets/keyltt_thu_nghiem.txt` (không in) — `usage.cache_read_input_tokens` là số của chính llama.cpp |
| Đối chứng | `H:\LTT_LLM\logs\llamaswap.log`: `prompt eval time`, `making room`, `do_reset`, `prompt state size` |
| Prompt cache | tài liệu cố định 9,8–10,0K token, lượt sau = cùng tiền tố + 1 cặp (assistant cố định) |
| Điểm lùi | `H:\LTT_LLM\gateway\llama-swap.yaml.baotri-20260918-062109` (SHA-256 `ef6c5c47…a2dd`) + `releases/auto-*` của `deploy.ps1` |
| Script đo | chỉ ở scratchpad phiên (không commit): `do_baotri.py`, `m_a_restart.py`, `m_b_nhieu_hoi_thoai.py`, `m_cd_tocdo.py`, `m_d_prefill.py`, `log_b.py` |

Trước cửa sổ, yaml trên B **lệch kho chỉ ở chú thích** (thiếu khối Phương án C/O-19; cờ trùng
khít). `deploy.ps1` bước 1c đã dừng đúng; chạy lại bằng `-GhiDeYamlLech` sau khi so cờ.

## 1. Bảng trước / sau

| phép | trước (mặc định) | sau (chốt) |
|---|---|---|
| (a) hội thoại qua **restart dịch vụ** | — | **0 % trúng** (cả hai). Nạp lại tiền tố ~9,9K: 3.5 **4,93 s** engine / TTFT 6,00 s; 3.8 **8,71 s** / TTFT 9,92 s. Lượt kế tiếp trúng lại 99,64 %. Hai model sẵn sàng sau restart **35,8 s** |
| (b) số hội thoại ~10K token còn trong cache | ~9 (8192 MiB; log 8× `making room`, entry 886 MiB; 3 lần `prompt state size 10,6–18,2 GB exceeds ... skipping` = hội thoại dài **không bao giờ** được cache) | 3.5: **14/14** trúng 99,69 %, 0 đuổi (12288); 3.8: **12/12**, 0 đuổi. ~0,82 GB/hội thoại |
| (c) 3.5 decode 1 luồng / tổng 3 luồng | 76,2 (L-16) | 82,1 / 154,1 (51,5·52,1·50,6) — `-b` 3.5 không đổi |
| (c) 3.8 decode 1 luồng / tổng 3 luồng | 62,0 / **125,3** (43,7·40,5·41,1) | 64,9 / **105,0** (31,5·32,5·41,1) |
| (d) 3.5 lượt đang sinh khi prefill 32K chèn vào (-b 2048) | 17/09: 2,1 tok/s, lặng 1,22 s | 2,6 tok/s (77,7 trước), lặng 1,15 s, prefill 17,35 s — không đổi `-b` |
| (d) 3.8 lượt đang sinh khi prefill 32K chèn vào | 17/09: 1,5; hôm nay -b 2048: **1,4 tok/s**, lặng **2,08 s**, prefill **31,13 s** | -b 512: **4,4 tok/s**, lặng **0,75 s**, prefill **35,02 s (+12,5 %)** |
| TTFT ngắn 3.8 (1 luồng) | 2,58–3,84 s | 2,68 s |

(d) đo cửa sổ **prefill thật** = [token đầu job 2 − `prompt eval time` của engine, token đầu job 2].
Lần chạy đầu dùng cả TTFT phía khách làm mẫu số và cho 38 tok/s — **sai**: TTFT khách gồm
~30 s chờ nền tảng trước khi engine bắt đầu. Đã bỏ số đó. Mỗi ô (d) = trung vị 2 lần.

## 2. 🔴 Sự cố giữa cửa sổ: `--cache-ram 24576` làm cổng B từ chối mọi lượt

| thời điểm | RAM trống máy B (191,9 GiB tổng) | llama-server 3.8 / 3.5 |
|---|---|---|
| hai model vừa nạp, cache rỗng | **85,0 GB** | 15,7 / 7,5 GB |
| sau (b) 28 hội thoại, `--cache-ram 24576` | **44,2 GB** | 37,3 / 26,5 GB |

`gateway.env`: `LTT_LLM_RAM_TRONG_GB=48`. `/health` cổng B: `trong_tai.ban=true`,
`"RAM trong 44.4 GB duoi nguong 48 GB"`, `dem.ban_trong_tai=36`; khách nhận
`overloaded_error` trên **cả hai** model trong khi `/slots` cả 6 slot rảnh và
`execution_leases` rỗng. Chữa: `Restart-Service LTTLlamaSwap` (xả cache) ⇒ 85 GB, mở lại
ngay; rồi hạ `--cache-ram` trong kho.

Ngân sách: (85 − 48) = 37 GB cho cả hai cache; trừ biên ~13 GB (ComfyUI, RDP, việc AI khác)
⇒ **12 GiB/model**, xấu nhất còn ≥ 61 GB trống. Đo sau khi hạ: 73,5 GB trống sau 14 hội thoại.

Bài học: `KET_QUA_CACHE_18_09` xếp `--cache-ram` "rủi ro thấp — chỉ RAM, không VRAM". Đúng về
VRAM, sai về hệ thống: RAM máy B có một sàn cứng do chính cổng đọc, ở tệp khác.

## 3. `-watch-config` và nhả từng model

- Dòng lệnh dịch vụ: `llama-swap.exe --config ...\llama-swap.yaml --listen 127.0.0.1:8280 -watch-config`
  (qua `cai_dat_dich_vu.ps1` trên B, SSH đã là admin). Log: `watching configuration for changes (poll-based, 2s interval)`.
- Lưu yaml ⇒ `reloading configuration` → `configuration reloaded`, PID llama-swap **không đổi** (5784).
- ⚠️ **Nhưng v250 nạp lại CẢ HAI model ở mọi lần lưu** — kể cả chỉ sửa chú thích: PID
  llama-server 20860/12176 → 5544/16036, cache RAM mất. Tiết kiệm restart dịch vụ và
  restart cổng; **không** cho phép "chỉnh một model, model kia không bị đụng".
- `POST /api/models/unload/qwen35-api` → 200; `/running` chỉ còn `qwen38-api`, PID 3.8 giữ
  nguyên 5544 và trả lời đúng. 3.5 nạp lại theo yêu cầu trong 15,9 s. ⇒ nhả **từng model**
  làm được — đó là đường cho L-17 (`LTT_HO_DUNG_CARD` vẫn đang trỏ `GET /unload`, chưa đổi).

## 4. Trạng thái cuối máy B (07:55)

`/running` hai model `ready`; yaml B SHA-256 `a9fb6387…f8dc` = kho nhánh `phien/bao-tri-may-b`;
`/health`: `trong_tai.ban=false`, RAM trống 83,6 GB, `models_la=[]`, `vat_ly` 3.5 (262144, 3) /
3.8 (221184, 3); VRAM 3090 24058, 5060 Ti 15778 MiB; đúng hai `llama-server`, không mồ côi.
LTTLlmGateway đã restart theo (phụ thuộc LTTLlamaSwap) — `-c`/`-np` không đổi nên không cần gì ở máy A.

## 5. Còn nợ / ngoài phạm vi

- Tổng 3 luồng 3.8 giảm 16 % với `-b 512` — một lần đo, số ra mỗi luồng lệch nhau (122–226 token); đo lại có lặp.
- `--ctx-checkpoints 8` không chứng minh được entry nhỏ đi (0,82 vs 0,87 GB).
- Mỗi lượt stream bị huỷ để lại dòng `llm_waiters` `trang_thai='nhan'` không bao giờ đóng
  (`don_het_han` chỉ đóng `cho`, chạy 6 giờ/lần). Vô hại cho admission (lọc nhịp 10 s) nhưng làm sai truy vấn RUNBOOK §4.
- Máy B còn hai tệp mồ côi đã xoá khỏi kho: `llm_gateway/don_dep.py`, `render_gateway/nhuong_card.py` (`scp` không xoá; bước 2b không bắt tệp thừa).
- Tài liệu 17/09 (`KET_QUA_DO_17_09.md`, `RUNBOOK_CUA_SO_DO.md`) chỉ nằm trên nhánh `phien/bench-may-b`, chưa vào `main`.
