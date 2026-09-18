# Kiểm cô lập chéo phiên — 18/09/2026 (Task 10 Step 1–2, llama.cpp #27148)

**Kết luận: 0 rò / 432 lượt chấm (216 mỗi model), 0 lượt không đo được.** Cấu hình production đo được
**không** tái hiện #27148 trong phạm vi phép đo dưới đây. Không đổi cờ, không khởi động lại, không gỡ model trên B.

Chỉ dữ liệu tổng hợp (marker ngẫu nhiên `QX/QY/ZT/KP/QN/QD` + 8 chữ số). Không có dữ liệu khách.
Thô: `kiem_co_lap_18_09/qwen38-api.jsonl`, `kiem_co_lap_18_09/qwen35-api.jsonl`, `kiem_co_lap_18_09/dieu_phoi.txt`.

## Cấu hình được đo (đọc từ `llama-swap /running` lúc chạy, không phải từ kho)

| | LTT-3.8 `qwen38-api` (3090) | LTT-3.5 `qwen35-api` (5060 Ti) |
|---|---|---|
| `-np` / `-kvu` | 3 / **có** (kv_unified = true) | 3 / **có** |
| `--cache-ram` | **24576** | **24576** |
| `--cache-idle-slots` | mặc định (bật) | mặc định (bật) |
| MTP | `draft-mtp`, n-max 2 | `draft-mtp`, n-max 2 |
| KV | q4_0 | q8_0 |

Đường vào: `ssh -L 18280:127.0.0.1:8280` → llama-swap trên B (gọi thẳng engine, không qua cổng 8299, không tốn credit).
Lúc bắt đầu (09:53) `/running` rỗng (TTL 1800 s đã nhả cả hai model ⇒ không có lưu lượng LLM ≥ 30 phút), ComfyUI
dừng, VRAM 66/415 MiB. Lượt đầu nạp model theo đúng đường theo nhu cầu như một request khách.

## Nguồn đã đọc (GitHub MCP)

- **#27148** (mở; PR sửa #27624 còn mở): `server_prompt_cache::load()` trả `true` khi không khớp ⇒ slot bị LRU
  chọn không được `prompt_clear()`. Tái hiện gốc: nạp pool bằng nhiều hội thoại ~4,5K token **khác nhau** (system dài
  + user + assistant `tool_calls` + `tool`), rồi bắn **cặp đồng thời** hội thoại mới; `cached_tokens` = 0 ở mọi lượt
  hỏng (không có tín hiệu phía client).
- Bình luận 2 của #27148: tái hiện **tuần tự, không đồng thời**, với **kv_unified = true** + MTP — A = "tìm lỗi script
  bash" (~285 token, sinh 2000), B = tài liệu ~4,9K token không liên quan ⇒ 3/3 hỏng ở mặc định. Với kv_unified =
  true chỉ còn đường pool RAM mở (một cờ `--cache-ram 0` hoặc `--no-cache-idle-slots` là đủ); kv_unified = false cần cả hai.
  **Cấu hình của ta là kv_unified = true ⇒ công thức tuần tự này là công thức sát nhất.**
- **#28286** (MTP + `--parallel > 1` trộn nội dung giữa các request đồng thời, cần prompt đủ entropy) và **#26425**
  (MTP giữ trạng thái giữa request) — cùng lớp rủi ro vì ta chạy `draft-mtp` + np 3.

## Kịch bản và số lượt chấm (mỗi model)

| kịch bản | trigger được bao | lượt chấm | rò | ghi chú |
|---|---|---:|---:|---|
| `tuan_tu_khong_lien_quan` | bình luận 2 #27148 (A script bash → B ~6K token không liên quan) | 18 | 0 | prompt B tb ~5,96K token, `cache_n` 0 |
| `xoay_vuot_slot` | 5 phiên > 3 slot rồi B không liên quan (LRU + pool) | 18 | 0 | |
| `dong_thoi` | 3 phiên đồng thời, mã riêng (#28286 dạng ngắn) | 54 | 0 | 3.8: 54/54 trả đúng mã mình; 3.5: 51/54 (2 rỗng do `length`, 1 không nêu mã — không chứa marker lạ) |
| `sentinel_tien_to_chung` | tiền tố hệ thống chung ~3K token, hỏi lại có mã nào không | 18 | 0 | `cache_n` > 0 (tiền tố chung, đúng kỳ vọng) |
| `dong_thoi_lru_27148` / nạp | công thức gốc #27148: 4 hội thoại (> np) ~3,5K token có `tool_calls`/`tool` | 72 | 0 | 72/72 trả đúng mã mình |
| `dong_thoi_lru_27148` / đồng thời | cặp hội thoại mới bắn cùng lúc (rào `Barrier`) ngay sau pha nạp | 36 | 0 | 36/36 đúng mã mình, `cache_n` 0 |
| **tổng** | | **216** | **0** | 0 không đo được (mọi lượt HTTP 200) |

Tiêu chí rò: **bất kỳ** marker nào của **cả lượt chạy** (mọi kịch bản, mọi vòng) trừ marker của chính phiên đó xuất
hiện trong `content` hoặc `reasoning_content`. `cache_n` được ghi nhưng không là tiêu chí (issue: tín hiệu này = 0 cả
khi hỏng). Chạy 18 vòng mỗi model, 6 khúc × 3 vòng, hai model song song trên hai card, 09:58–10:57.

## Bảo vệ khách

Trước mỗi khúc: đếm kết nối Established vào cổng khách B `8299` từ ngoài loopback; > 0 ⇒ chờ (bước 30 s, trần 15 phút).
Bốn lần gặp 1 kết nối (10:06, 10:17, 10:32, 10:37) — đều hết trong ≤ 1 phút, khúc chạy sau đó. `song_song` = 2 (để một
slot trống); `dong_thoi` dùng 3 lượt ngắn (~80 token). Log A `ltt-server.jsonl` không ghi dòng nào trong 10 phút trước
khi chạy (dòng cuối 09:06, máy A vừa khởi động lại 09:24).

## Công cụ — thay đổi so với 0bb171ca

1. Thêm `dong_thoi_lru_27148` (công thức gốc) + `--n-nap`, `--song-song`.
2. Sổ marker toàn cục (`SoMarker`): trước chỉ so với marker cùng kịch bản/cùng vòng.
3. Dừng ngay khi thấy rò (mặc định), ghi `marker_ro`, `trich_ro` (±200 ký tự), `marker_minh`, `dung_ma`.
4. **Dương tính giả đã sửa trước lượt chính:** lượt khói đầu (09:54) báo "rò" ở `dong_thoi` cả hai model. Nguyên nhân là
   bước 2: `dong_thoi` không khai marker của chính phiên nên câu trả lời ĐÚNG (content 10 ký tự = đúng một marker) bị
   tính là rò. Sửa + test hồi quy (`test_engine_sach_tra_dung_ma_cua_chinh_minh_khong_bi_tinh_la_ro`); lượt chính
   ghi `dung_ma` = true cho các lượt đó. Lượt khói bị loại khỏi số liệu.

Test: `tests/test_1407_kiem_co_lap_llm.py` (9) + `tests/test_1409_cong_b_khong_lo_slots.py` (1) → PASS.

## Giới hạn của phép đo (đọc trước khi dùng kết luận)

- **0/216 không chứng minh an toàn**: issue báo 20/20 vòng hỏng ở cấu hình np 2/kv_unified false, và 3/3 ở cấu hình
  kv_unified true — với tỉ lệ như vậy 216 lượt đủ để thấy; với tỉ lệ ~1/ngày (lưu lượng thật của người báo) thì không.
- Không có bằng chứng phía server rằng nhánh `prompt_load()` không-khớp **đã thực sự chạy** (không đọc log
  llama-server, không đọc `/slots`). Suy ra từ thiết kế: slot bận/idle > np, prompt không chung tiền tố ⇒ LRU + pool.
- Build B là `91f6a6cf3`; không kiểm mã nguồn build này có chứa đường lỗi giống hệt `adb55e514` trong issue hay không.
- Prompt ~3,5–6K token; người báo thấy tỉ lệ tăng ở ~12K token (bình luận 1). Chưa đo cỡ đó.
- Chạy lúc vắng, B vừa nạp lại model (pool RAM bắt đầu rỗng, chỉ chứa hội thoại tổng hợp).

Giảm thiểu nếu sau này thấy rò: `--cache-ram 0` (đủ với kv_unified = true theo bình luận 2/3 của #27148) — thay đổi
production, chủ dự án quyết.
