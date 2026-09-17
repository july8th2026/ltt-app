# Cửa sổ bảo trì đo máy B — runbook (soạn 17/09/2026, pha 1: chỉ chuẩn bị)

Tệp trong thư mục này (bản chép trên máy B: `E:\AI\ltt_dual\bench_hang_cho\`):

| tệp | việc |
|---|---|
| `do_b.py` | lô đo m1/m3_35/m5/m6/m3_38/m2, chạy TRÊN máy B, server thử cổng 8290/8292/8294 |
| `khoi_dong_b.ps1` | đăng ký + chạy Scheduled Task SYSTEM + pythonw; `-XemTrangThai`; `-Go` |
| `cua_so_b.ps1` | `kiem` · `nha35` · `nha38` · `dung_comfy` · `don_dep` · `khoi_phuc` |
| `do4_do_dai_dau_ra.py` | phép 4 (chỉ đọc, không cần tạm dừng) · kết quả `do4_log_20260917.json` |

⚠️ Tham số server thử chép từ `/running` **đang chạy**, không từ kho: production có
`--no-cache-idle-slots` mà `llm_gateway/deploy/llama-swap.yaml` trên `main` không có.

## A. Tạm dừng (máy A → máy B)

Không có công tắc "drain một bước" cho mọi đường. Ghép hai công tắc, cả hai không cần restart:

0. **Chờ eval H13.6 xong** (`chay.py` trong scratchpad `h136`, gọi thẳng `192.168.2.66:8299`,
   không công tắc nào của nền tảng chặn được). Kiểm: không còn tiến trình `chay.py`/`lay_mau.py`
   trên máy A; `gateway_err.log` máy B hết dòng `POST /v1/chat/completions` mới.
1. **Kill switch API** — `/admin/api-kill-switch` → `engage`, `scope=tool`, subject `text.chat`,
   lặp lại cho `image.ltt`; lý do ≥ 8 ký tự (khách thấy nguyên văn, 503):
   *"Bảo trì máy GPU để đo hiệu năng, dự kiến xong HH:MM"*; `minutes=180` (tự hết hạn).
   Chặn lượt API MỚI (`/api/v1`, cả job). Lượt đang chạy và job đã xếp hàng vẫn chạy tiếp.
2. **Chờ hàng đợi về 0** (job đã nhận chạy hết, không bị huỷ):
   ```sql
   SELECT job_type,status,count(*) FROM jobs WHERE status IN ('queued','running')
     AND job_type IN ('ltt_llm.chat','anhnoibo.generate','chatltt.nghien_cuu','chatltt.trich_tep') GROUP BY 1,2;
   SELECT resource,count(*) FROM llm_waiters WHERE finished_at IS NULL GROUP BY 1;
   SELECT resource,count(*) FROM execution_leases WHERE heartbeat_at >= now()-interval '20 minutes' GROUP BY 1;
   SELECT nhom,trang_thai FROM gpu_residency;   -- phải là 'llm'
   ```
3. **Tắt khoá provider** — `/admin/apikeys` → "Tắt" các dòng provider `ltt_llm` và `ltt_image`.
   Chặn ChatLTT web + mọi tính năng nội bộ (`runtime_noi_bo`, dịch prompt, prompt_canh…) mà
   bước 1 không với tới. ⚠️ Làm SAU bước 2: job còn xếp hàng gặp khoá tắt sẽ **fail + hoàn
   tiền**, và người dùng web chỉ thấy lỗi chung (không có chữ "bảo trì").
4. **Xác minh đã cạn** (máy B, qua SSH):
   `powershell -NoProfile -ExecutionPolicy Bypass -File E:\AI\ltt_dual\bench_hang_cho\cua_so_b.ps1 -Buoc kiem`
   → cột `slot_ban` trống cả hai model, `util` ≈ 0 ở cả hai card, 2 phút không có `POST` mới trong
   `H:\LTT_LLM\logs\gateway_err.log`. (Ảnh chụp trạng thái bình thường đã ghi 17/09 15:2x vào
   `truoc_cua_so.json`: 4 dịch vụ Running, cả hai model ready.)

Không tạm dừng được bằng công tắc: tiến trình gọi thẳng `:8299`/`:8199` từ máy A (eval, `tools/soi_troi_may_b.py`,
`tools/do_sau_suat.py`). Voice **không** dùng máy B (sidecar 127.0.0.1:8120 máy A).
`LTT_PUBLIC_API_READ_ONLY` / manifest `lifecycle="maintenance"` cũng dùng được nhưng cần
`setup\nap_lai_env.ps1` (restart 4 dịch vụ) hoặc deploy — không dùng cho cửa sổ này.

## B. Chạy lô đo (thứ tự: 5060 Ti trước, 3090 sau)

Chép lên máy B (nếu sửa): `scp -i ~/.ssh/nexus_b do_b.py khoi_dong_b.ps1 cua_so_b.ps1 lengo@192.168.2.66:E:/AI/ltt_dual/bench_hang_cho/`
`SSH=ssh -i ~/.ssh/nexus_b -o BatchMode=yes lengo@192.168.2.66`, `PS=powershell -NoProfile -ExecutionPolicy Bypass -File E:\AI\ltt_dual\bench_hang_cho\`

| bước | lệnh (trên máy B) | thời lượng ước |
|---|---|---|
| 1 | `cua_so_b.ps1 -Buoc nha35` | 1 phút |
| 2 | `khoi_dong_b.ps1 -Do m1,m3_35,m5,m6 -HanPhut 80` rồi `-XemTrangThai` | m1 ~28 · m3_35 ~14 · m5 ~5 · m6 ~8 = **~55 phút** (trần 80) |
| 3 | `cua_so_b.ps1 -Buoc nha38` + `-Buoc dung_comfy` | 1 phút |
| 4 | `khoi_dong_b.ps1 -Do m3_38,m2 -HanPhut 55` | m3_38 ~18 · m2 ~25 = **~43 phút** (trần 55; m2 tự bỏ qua cấu hình tràn/trượt cổng 60 tok/s) |
| 5 | `cua_so_b.ps1 -Buoc khoi_phuc` rồi `khoi_dong_b.ps1 -Go` | 5 phút |

**Tổng ≈ 1 giờ 45 (không tính chờ cạn hàng); trần cứng 2 giờ 30.** Bỏ m2 ⇒ ~1 giờ 20.

Kết quả: `E:\AI\ltt_dual\bench_hang_cho\ket_qua\<phép>.jsonl` (ghi từng dòng), log từng server
`<phép>_<nhãn>.log`, nhịp tim `trang_thai.json`, `nhat_ky.txt`.

**Preflight — HUỶ cả lô nếu** (kiểm trước MỖI cấu hình, đã thử nhánh huỷ trên máy B 17/09):
llama-swap không đọc được · model nào đang nạp có `/slots` `is_processing` hoặc `/metrics`
`requests_processing`/`requests_deferred` > 0 · util trung bình (10 mẫu/5 s) của BẤT KỲ card
nào > 10 % · VRAM card đích > 1500 MiB (5060 Ti) / 1200 MiB (3090) tức model production chưa nhả.
Dòng `HUY_LO_PREFLIGHT` trong jsonl ghi lý do; task kết thúc mã 2.

**Ngân sách**: `-HanPhut` là trần cả lô, mỗi phép có trần riêng (`HAN_PHEP`); luồng gác giết server
thử và thoát ở trần + 2 phút; Task Scheduler cắt ở trần + 10 phút. Dọn dẹp chỉ giết `llama-server`
có `--port 8290|8292|8294` — không chạm 8281/8282, không sửa cấu hình, không restart dịch vụ.
Dừng khẩn: `Stop-ScheduledTask LTT_BenchHangCho` + `cua_so_b.ps1 -Buoc don_dep`.

## C. Khôi phục

1. Máy B: `cua_so_b.ps1 -Buoc khoi_phuc` — nạp 3.8 khi ComfyUI còn tắt, nạp 3.5, in dedicated/shared
   từng model (shared ~674 MiB ở 3.5 là mức nền đo 17/09, không phải tràn), bật lại LTTComfyUI,
   một lượt chat thật mỗi model qua 8280 (`content_rong=False`), so VRAM với ảnh chụp.
2. Máy A: `/admin/apikeys` → "Bật" `ltt_llm`, `ltt_image`.
3. `/admin/api-kill-switch` → `release` hai công tắc `text.chat`, `image.ltt`.
4. Xác minh: một lượt `text.chat` (LTT-3.5 và LTT-3.8) và một job `image.ltt` bằng tài khoản thử
   (`tools/tai_khoan_thu.py`); `/ops/jobs-metrics`; `gpu_residency.trang_thai='llm'`;
   `gateway_err.log` máy B có `POST` mới trả 200.

## D. Phép 4 — độ dài đầu ra thật (log máy B, 12→17/09, non-stream)

| model | n | token_ra p50 / p95 / p99 / max | tỷ lệ `length` | token_vào p50 / p95 / p99 | stream không có số |
|---|---|---|---|---|---|
| qwen35-api | 3472 | 1137 / 6815 / 13502 / 32768 | 2,8 % | 2947 / 20057 / 44635 | 859 |
| qwen38-api | 2705 | 1488 / 6000 / 11605 / 19267 | 2,9 % | 3115 / 6411 / 52408 | 1684 |

Giới hạn: `token_ra` = suy nghĩ + nội dung gộp (không nơi nào tách); log không có `max_tokens`
(tỷ lệ chạm trần = `ket_thuc=length`); lượt stream không có token; log gồm cả eval/bench nội bộ
(15/09 đột biến). Đo theo `max_tokens` thật: `do4_do_dai_dau_ra.py --nguon csdl` (bảng `jobs`, cần
quyền đọc `C:\LTTPlatform\secrets` — phiên này bị chặn, chưa chạy).
