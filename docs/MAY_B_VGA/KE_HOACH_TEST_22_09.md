# Mod card máy B — kế hoạch test (22/09/2026)

Chủ dự án cấp quyền: tự cài HWiNFO, tự điều khiển máy B (SSH/Nexus), tự vận hành. Phạm vi: CHỈ card
(3090 + 5060 Ti). Không sửa mã/cấu hình LTTSTUDIOSAPP (llama-swap.yaml, gateway giữ nguyên).
Mốc lỗi: log System/Application đã sao lưu + xoá lúc 2026-09-22T18:08:22 (`H:\LTT_MOD_CARD\evtx_truoc_mod\`).
Thư mục làm việc trên B: `H:\LTT_MOD_CARD\` (kết quả, CSV HWiNFO, bản sao cfg Afterburner).

## Nguyên tắc an toàn
- Một thay đổi mỗi lần; đo trước/sau; đường lùi có sẵn trước khi áp.
- Không đụng điện áp, không OC xung nhân. Chỉ: power limit, offset xung BỘ NHỚ, (tuỳ đo) tắt ép P2 cho CUDA.
- Bậc nhỏ: 3090 +250 MHz/bậc (trần +1000), 5060 Ti +500/bậc (trần +2000 hoặc trần Afterburner).
- Không lưu vào "Startup" của Afterburner cho tới khi soak đạt ⇒ khởi động lại máy = về mặc định.

## Điều kiện DỪNG + LÙI ngay (về bậc trước)
1. Bất kỳ sự kiện mới: nvlddmkm 13/14/153, Display 4101, WHEA-Logger (mọi Id), Kernel-Power 41, bugcheck.
2. 3090 Memory Junction ≥ 96 °C, hoặc GPU hot spot ≥ 95 °C (HWiNFO). 5060 Ti memory ≥ 90 °C.
3. Output greedy khác hash mốc (kiểm chất lượng từng byte).
4. Tốc độ decode KHÔNG tăng hoặc giảm so với bậc trước (GDDR6X EDR gửi lại ⇒ OC quá tay) ⇒ lùi 1 bậc.
5. llama-server chết / lỗi CUDA trong log llama-swap.

## Phép đo (qua đường production: llama-swap 127.0.0.1:8280, cấu hình thật, không đổi cờ)
- T1 decode: prompt ~1K, greedy (temp 0), max 512 token ra, 5 lượt → trung vị `timings.predicted_per_second`
  + draft acceptance; hash nội dung ra.
- T2 prefill: prompt ~16K, `cache_prompt:false`, 16 token ra, 3 lượt → trung vị `prompt_per_second`.
- T3 (mốc + bậc chốt): decode ở ngữ cảnh ~64K, 1 lượt.
- Trước mỗi lượt: kiểm /slots không có slot khách đang chạy; có khách ⇒ đánh dấu lượt nhiễu, đo lại.
- Ghi song song: nvidia-smi 1 s (xung, điện, nhiệt, P-state, lý do giới hạn), HWiNFO CSV 2 s.

## Trình tự
0. Chuẩn bị: cài HWiNFO portable (nguồn chính thức), bật log CSV; sao lưu cfg Afterburner; kiểm cơ chế áp
   profile Afterburner bằng thay đổi vô hại (PL 99 %) trước khi dùng cho OC.
1. Mốc cả hai card (T1, T2, T3) ở mặc định + kiểm greedy lặp 3 lần có trùng hash không (tất định).
2. 3090 — power limit 370 → 300 W (nvidia-smi -pl): đo T1/T2; giữ nếu decode mất < 2 %.
3. 3090 — kiểm P-state khi chạy CUDA (P2 hạ xung nhớ?). Nếu có: đánh giá thêm.
4. 3090 — offset nhớ +250/+500/+750/+1000: mỗi bậc T1 + T2 + hash + nhiệt + sự kiện.
   Chọn bậc tốt nhất rồi lùi 1 bậc (biên an toàn).
5. 5060 Ti — offset nhớ +500 …: như bước 4.
6. Soak ở cấu hình chốt: 30 phút tải liên tục cả hai card (T1+T2 xen kẽ), theo dõi điều kiện dừng.
7. Chốt: lưu profile Afterburner + áp lúc khởi động; power limit bền qua khởi động lại (tác vụ lúc khởi động
   nếu nvidia-smi -pl không bền); ghi KET_QUA.md; báo chủ dự án.

## Đường lùi
- Afterburner: áp profile mặc định (offset 0, PL 100 %) / bản cfg `MSIAfterburner.cfg.truoc_claude` + bản sao
  hôm nay ở `H:\LTT_MOD_CARD\afterburner_goc\`.
- `nvidia-smi -i 0 -pl 370`. Khởi động lại máy = về mặc định (khi chưa lưu Startup).

## Trạng thái
(cập nhật trong lúc chạy — xem KET_QUA.md)
