# Nghiên cứu tiếp quản — trần ngữ cảnh Qwen3.8-27B trên máy B

Ngày: 2026-08-27 · mục đích: tiếp nối phiên Claude
`5a74e3b4-a8e0-4dbc-a26b-6fe9bb2ddc04`.

## Sự thật đã xác minh trên máy B

- Nexus node `f8b24d88-6e3e-4719-8143-d5e83f68ed82` đang `ONLINE`.
- GPU: NVIDIA RTX 3090, 24.576 MB; phép đo Nexus gần nhất còn khoảng 22,9 GB
  trống.
- `H:\LTT_LLM\gateway\llama-swap.yaml`: `qwen38-api` và `qwen38-vision`
  dùng `-c 65536`, KV `q8_0`; profile `qwen38-ops` dùng `-c 204800`, KV
  `q4_0` nhưng chưa được bật/đo nghiệm thu trong phiên này.
- `C:\ProgramData\LTTLlm\gateway.env` (đã loại dòng token khi đọc):
  `LTT_LLM_MAX_INPUT_TOKENS=60000`, `LTT_LLM_MAX_OUTPUT_TOKENS=32768`.

## Bằng chứng cộng đồng

1. [jonidimo/qwen38-3090-benchmark](https://github.com/jonidimo/qwen38-3090-benchmark):
   RTX 3090, Q4, KV `q4_0`, MTP-2; 131.072 token được lấp đầy và đo thật,
   khoảng 63,7 tok/s; tác giả dùng build b10217, model AD-Q4_K_M nhỏ hơn bản
   Unsloth và bật `GGML_CUDA_CUBLAS_COMPUTE_TYPE=fp32` cho Ampere.
2. [llama.cpp issue #27623](https://github.com/ggml-org/llama.cpp/issues/27623):
   Qwen3.8-27B trên CUDA/Windows và WSL2; decode từ khoảng 33 tok/s ở vị trí
   68K xuống 1,4 tok/s ở 91K, dù VRAM vẫn đủ và prompt processing vẫn nhanh.
3. [qwen38-mtp RTX-3090 sweep](https://github.com/sudoingX/qwen38-mtp/blob/master/sweeps/rtx-3090.md):
   báo 204.800 với KV Turbo3/q4 trên 24 GB, nhưng 262K không nạp được và hai
   nhánh dùng build khác nhau; đây là mốc tham khảo, không phải chứng nhận.
4. [QwenLM/Qwen3.8 README](https://github.com/QwenLM/Qwen3.8/blob/main/README.md):
   recipe vLLM/SGLang công bố 262.144 token, nhưng đó không phải phép đo cho
   llama.cpp + Q4 + RTX 3090 của cụm này.

## Kết luận vận hành

- Không nâng thẳng `LTT_LLM_MAX_INPUT_TOKENS` lên 131K/200K: con số đó có thể
  vượt đường decode thực tế hoặc làm tổng `input + output` vượt `-c`.
- Giữ client Codex ở `model_context_window=56000` như commit `c90894c`; đây là
  mức pre-compress dưới cap 60K hiện hữu và kết hợp với bản vá 413 ở `a2fc60c`.
- Với khách qua Cloudflare, profile 64K là trần hợp lý về độ trễ; không mở
  profile 200K ra đường public vì prefill có thể vượt giới hạn 100 giây.
- Nếu cần context dài cho Codex/Claude nội bộ, dùng profile `qwen38-ops`
  riêng, KV q4, chỉ qua LAN/Nexus, sau khi vượt qua ladder đo dưới đây.

## Ladder nghiệm thu trước khi đổi cấu hình

Ở mỗi mốc `C ∈ {65536, 73728, 98304, 131072}` trên đúng build/model đang chạy:

1. Nạp model với `-np 1`, ghi VRAM trước/sau và kiểm tra không có tensor CPU.
2. Đo prompt fill tại 45K, 60K, 68K, 80K và 90K (nếu mốc cho phép): prefill
   tok/s, TTFT, decode tok/s, p95 token latency, MTP acceptance.
3. Lặp tối thiểu 3 lần/mốc; ghi cả lỗi/timeout, không chỉ số pass.
4. Xác minh `input + requested_output <= C`, gateway 413 khi vượt và không
   biến thành 503/retry.
5. Giữ mốc cao nhất chỉ khi decode không rơi vào cliff, VRAM còn biên an toàn
   và workload agent thực tế không chạm timeout. Nếu không, chọn mốc thấp hơn.

Kết quả ladder phải được ghi vào quyết định/kế hoạch trước khi deploy. Rollback
là khôi phục `gateway.env`/YAML phiên bản trước và restart đúng dịch vụ; không
sửa tay một giá trị trên B rồi để source A lệch.

## Lượt đo thực tế ngày 2026-08-27

- Đã xác minh binary `H:\LTT_LLM\bin\llamacpp\llama-bench.exe` và model
  `Qwen3.8-27B-UD-Q4_K_M.gguf` trên B.
- Đã thử `-p 131072 -n 128 -r 3` và lượt rút gọn `-p 131072 -n 32 -r 1`,
  KV `q8_0`, GPU offload `-ngl 999`, flash attention bật.
- Cả hai lượt không trả về throughput/VRAM trong giới hạn proxy Nexus 120 giây;
  tiến trình nạp model kéo dài, không sinh được log benchmark có số đo. Đã dừng
  đúng PID và xác nhận không còn tiến trình benchmark/compute chiếm GPU.
- Kết luận: **chưa có phép đo đạt/không đạt 131072**. Không mở public API và
  không thay `gateway.env`/`llama-swap.yaml` dựa trên lượt chạy chưa hoàn tất.
