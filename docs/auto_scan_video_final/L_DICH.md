# L_DICH — QE dịch không tham chiếu (làn `dich`, ASV final, 22/09/2026)

Năng lực: `apps/asv_gpu/do_luong/metricx.py::do_dich(cap, ngon_ngu_nguon, ngon_ngu_dich, gpu_uuid, is_cancelled) -> {ma: điểm}`.
Làn `giong` gọi nó ở chặng đo GPU; làn này KHÔNG nối vào pipeline.

## 1. Quyết định

**Chọn MetricX-24-Hybrid-Large (bf16), chế độ QE.** Loại `wmt20-comet-qe-da`.

- Điểm = lỗi MQM dự đoán, `[0, 25]`, **THẤP LÀ TỐT**.
- Ngưỡng TẠM theo hướng (`metricx.NGUONG_DO`): zh→vi **6**, zh→en **6**, en→vi **6**, vi→en **9**.
  Điểm > ngưỡng ⇒ cờ "dịch hỏng". Thang lệch theo hướng (bản tốt vi→en trung bình 4,8; zh→vi 2,4)
  nên một ngưỡng chung (tốt nhất 6,8 → acc 0,78) kém hơn ngưỡng theo hướng.
- **Nói thẳng:** MetricX bắt chắc **bỏ sót** và **không dịch**; **KHÔNG** bắt tin cậy **lật nghĩa**
  (AUC zh→vi 0,61) và **sai thực thể** (0,72–0,79). Với zh→vi, ở ngưỡng 6 nó lọt 12/24 bản hỏng
  (5 lật nghĩa, 6 sai thực thể, 1 không dịch). ⇒ Lớp phán xét ngữ nghĩa LLM (`qc_ai`, X1 trong
  audit) **phải giữ**; MetricX là chỉ số số bổ sung, không thay nó.
- Ngưỡng chọn trên CHÍNH bộ đo (24 bản tốt/hướng, mục tiêu báo nhầm ≤ 2/24) ⇒ lạc quan; cần một
  bộ kiểm tách riêng (bản dịch LTT LLM thật + người chấm) trước khi dùng làm cổng chặn cứng.

## 2. Bộ cặp có nhãn

`docs/auto_scan_video_final/l_dich/bo_cap_co_nhan.json` — 24 câu nguồn zh thật (faster-whisper
large-v3, beam 5, VAD, trên 4 clip `Desktop\TEST VIDEO`, giữ nguyên lỗi ASR), mỗi câu có bản en/vi
tốt và một bản hỏng. Loại hỏng xoay vòng, 6 câu mỗi loại: `lat_nghia`, `bo_sot`, `sai_thuc_the`,
`khong_dich` (chép nguyên câu NGUỒN của hướng đó). Bốn hướng × 48 cặp = 192 cặp.
en→vi và vi→en dùng bản en/vi tốt làm nguồn.

Bản dịch viết tay: LTT LLM không gọi được từ làn này — cửa duy nhất (`/api/v1/messages`) cần khoá API,
và gọi thẳng llama-swap máy B sẽ vượt phòng chờ của máy A. Không gõ bí mật ⇒ viết tay.

Tái lập: `python tools/asv_danh_gia_qe_dich.py metricx <ra.json> cuda 16` rồi
`python tools/asv_danh_gia_qe_dich.py bao-cao <ra.json> metricx 1 [nguong]`.

## 3. Kết quả (RTX 5060 Ti, 192 cặp)

AUC = P(bản hỏng bị chấm xấu hơn bản tốt), gộp theo hướng. "Cặp đôi" = cùng câu nguồn, bản hỏng
xấu hơn bản tốt của nó.

| Hướng | MetricX AUC | COMET-QE AUC | MetricX cặp đôi | COMET cặp đôi | MetricX acc (ngưỡng riêng tốt nhất) |
|---|---|---|---|---|---|
| zh→vi | **0,844** | 0,583 | 23/24 | 17/24 | 0,833 @ 3,55 |
| zh→en | **0,852** | 0,587 | 23/24 | 15/24 | 0,792 @ 4,73 |
| en→vi | **0,865** | 0,595 | 23/24 | 16/24 | 0,812 @ 5,84 |
| vi→en | **0,877** | 0,602 | 22/24 | 15/24 | 0,875 @ 8,69 |

AUC theo loại hỏng (MetricX / COMET-QE):

| Hướng | lật nghĩa | bỏ sót | sai thực thể | không dịch |
|---|---|---|---|---|
| zh→vi | 0,61 / 0,73 | 1,00 / 0,97 | 0,79 / 0,58 | 0,98 / **0,06** |
| zh→en | 0,69 / 0,76 | 1,00 / 0,97 | 0,72 / 0,61 | 0,99 / **0,01** |
| en→vi | 0,68 / 0,79 | 1,00 / 0,92 | 0,79 / 0,63 | 1,00 / **0,04** |
| vi→en | 0,75 / 0,84 | 1,00 / 0,94 | 0,75 / 0,63 | 1,00 / **0,00** |

COMET-QE (wmt20) **thưởng** bản không dịch (chép nguồn được điểm cao hơn bản dịch đúng) — lỗi
đã biết của QE thế hệ đó, và là lỗi chết người cho sản phẩm lồng tiếng. Nó nhỉnh hơn ở lật nghĩa
nhưng thua mọi chỗ khác ⇒ loại.

Ngưỡng cố định của MetricX (báo nhầm trên 24 bản tốt / lọt trên 24 bản hỏng):

| Hướng | 5 | 6 | 7 | 9 |
|---|---|---|---|---|
| zh→vi | 3 / 9 | **2 / 12** | 0 / 13 | 0 / 17 |
| zh→en | 2 / 9 | **1 / 10** | 0 / 11 | 0 / 15 |
| en→vi | 6 / 6 | **2 / 8** | 1 / 9 | 1 / 12 |
| vi→en | 11 / 3 | 7 / 5 | 5 / 5 | **0 / 8** |

## 4. Tài nguyên

| | MetricX-24-Large bf16 (GPU) | MetricX fp32 (CPU, 6 luồng) | COMET-QE wmt20 (GPU, fp32) |
|---|---|---|---|
| VRAM đỉnh (torch, lô 16) | 2.435 MB | — | 2.264 MB |
| Nạp model | 32,6 s (lần đầu, đĩa lạnh) | 26,3 s | 18,9 s |
| Chấm | 192 cặp trong 17,8 s ⇒ **93 ms/cặp** (lô 16) | 32 cặp trong 4,4 s ⇒ **139 ms/cặp** (lô 8) | 192 cặp trong 19,9 s ⇒ 104 ms/cặp |

Đo khi GPU đang chạy việc khác (máy production dùng chung) ⇒ độ trễ là cận trên. Đĩa: 2,46 GB
checkpoint + 4,3 MB tokenizer.

**Chạy được trên CPU** (`thiet_bi="cpu"`, fp32, `OMP_NUM_THREADS=6`): chỉ chậm hơn ~1,5 lần trên
đoạn phụ đề ngắn (RSS không đo; trọng số fp32 ~4,9 GB), và điểm khớp bản GPU bf16 (lệch trung bình 0,064; tối đa 0,17 trên 32
cặp chung) ⇒ ngưỡng dùng chung cho cả hai đường. Đây là lối lùi khi card bận, không phải mặc định.

## 5. Cài đặt, lặp lại được

- Mã: `apps/asv_gpu/do_luong/_metricx/` — `mt5_regression.py` (chép tối thiểu `MT5ForRegression` từ
  upstream, Apache-2.0, có `LICENSE` nguyên văn + `NOTICE` ghi thay đổi), `chay.py` (runner trong
  qc-venv), `ban_ghim.py` + `phien_ban.json` (revision + sha256), `tai.py` (tải lần đầu).
- Tải: `set HF_HOME=C:\LTTPlatform\hf-cache` rồi
  `C:\LTTPlatform\qc-venv\Scripts\python.exe apps\asv_gpu\do_luong\_metricx\tai.py`.
  Runner KHÔNG tự tải: thiếu tệp hoặc sai sha256 ⇒ in `KHONG_KHA_DUNG`, `venv.chay` ném `KhongKhaDung`.
  Đã tải sẵn vào `C:\LTTPlatform\hf-cache` trên máy A (22/09).
- Kiểm sha256 lần đầu rồi ghi dấu vào `HF_HOME\ltt-kiem\`; băm lại khi kích thước/mtime đổi.
- Tokenizer: `T5TokenizerFast` từ `spiece.model` của `google/mt5-xl` (upstream dùng
  `AutoTokenizer("google/mt5-xl")`, cùng lớp). Đầu vào `"source: … candidate: …"`, bỏ EOS, cắt 1536.
- Test: `tests/test_2030_asv_qe_dich_metricx.py` (hợp đồng, ghim, ghi công, bộ nhãn, runner thật
  thiếu model ⇒ `KhongKhaDung`).

## 6. Mục THIRD_PARTY_METRICS.md (dán nguyên)

```
### MetricX-24-Hybrid-Large (QE dịch không tham chiếu)
- Mục đích: chấm chất lượng bản dịch (nguồn, dịch) không cần bản tham chiếu; zh→vi, zh→en, en→vi, vi→en.
  Điểm lỗi MQM dự đoán [0, 25], thấp là tốt. Dùng ở: apps/asv_gpu/do_luong/metricx.py.
- Mã nguồn: https://github.com/google-research/metricx @ fc4978eb064670f7cc33e93ea4f52d38396b8ae6
  (2024-12-12). License: Apache-2.0 (LICENSE gốc, git blob 7a4a3ea2424c09fbe48d455aed1eaa94d9124835).
  Chép tối thiểu metricx24/models.py (MT5ForRegression, rút gọn chỉ suy luận) vào
  apps/asv_gpu/do_luong/_metricx/ kèm LICENSE + NOTICE ghi thay đổi. Không pip cài repo.
- Checkpoint: google/metricx-24-hybrid-large-v2p6-bfloat16 @ febb720e29a059df2e8af3ffd71dcdc9e0a24910
  License weights: Apache-2.0 (model card HF, trường license). pytorch_model.bin
  sha256 b1f2c03ab5ec5318a55b90b42eefa22431daa7b1a8e28a97a6aef23d18a24278 (2.459.348.101 byte);
  config.json sha256 cdd5f7a2c8a9b3221ba0cb6a9c04ddcf335fcf8b110218e8c57b122dd79cb258.
- Tokenizer: google/mt5-xl @ 63fc6450d80515b48e026b69ef2fbbd426433e84, Apache-2.0; chỉ tải
  spiece.model (sha256 ef78f86560d809067d12bac6c09f19a462cb3af3f54d2b8acbba26e1433125d6),
  tokenizer_config.json, special_tokens_map.json.
- Thương mại: CÓ (Apache-2.0 cả mã lẫn weights). Phân phối lại: được, kèm LICENSE + NOTICE; ta
  KHÔNG phân phối weights (tải từ Hugging Face lúc cài vào C:\LTTPlatform\hf-cache).
- Nguồn tải: https://huggingface.co (hf_hub_download, revision ghim), qua
  apps/asv_gpu/do_luong/_metricx/tai.py; runner kiểm sha256 mỗi tệp, thiếu/sai ⇒ KHONG_KHA_DUNG.
- Tài nguyên: GPU bf16 ~2,4 GB VRAM đỉnh (lô 16); ~90 ms/cặp trên RTX 5060 Ti.
- Giới hạn đã đo: bắt chắc bỏ sót/không dịch; yếu với lật nghĩa và sai thực thể (L_DICH.md §3).
- Đã loại: Unbabel wmt20-comet-qe-da (Apache-2.0, sạch license) — thưởng bản không dịch;
  CometKiwi / XCOMET — CC BY-NC-SA 4.0, DO NOT SHIP.
```

## 7. Ứng viên 2 — ghi lại license đã kiểm

`Unbabel/wmt20-comet-qe-da` @ `2e7ffc84fb67d99cf92506611766463bb9230cfb`: model card `license: apache-2.0`,
tệp `LICENSE` Apache-2.0 trong repo HF; `checkpoints/model.ckpt` sha256
`05d892bf4a3e34b9a4de239109387d43107b2a8c55ad34b73a929ca6c1ede24e`; mã `unbabel-comet` 2.2.7 Apache-2.0.
Chỉ chạy trong venv tạm (scratchpad, chồng lên qc-venv qua `.pth`, không sửa qc-venv); không tải vào
`hf-cache`, không ship. `unbabel-comet` 2.2.7 ghim `numpy<2`, `torchmetrics<0.11`, `jsonargparse==3.13.1`
— xung đột với qc-venv, thêm một lý do không đưa vào.
