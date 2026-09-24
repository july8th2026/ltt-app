# Brief chung cho mọi làn ASV final

Đọc tệp này TRƯỚC khi làm. Brief riêng của làn chỉ nói *việc gì*; đây là *cách làm*.

## Luật (một nguồn mỗi luật — đọc, đừng chép)

- Quy tắc agent + máy: `C:\Users\Thang Tuong\.claude\ltt\QUY_TAC_AGENT_VA_TOKEN.md` mục B + C.
  Máy A là **production**. Lệnh nặng đi qua
  `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- <lệnh>`.
  ⛔ **Lệnh nào là nặng, và trần `-n` bao nhiêu**: `docs/QUY_TAC_CHAY_LENH_NANG.md`
  §1 và §4 (`gate.TRAN_N_GO_TAY`) — đừng gõ lại con số ở đây.
- Luật chết người của kho: `CLAUDE.md` + `AGENTS.md` ở gốc cây của bạn (CRLF/LF không lật,
  không BOM, `.ps1` thuần ASCII, không Python inline qua PowerShell).
- ⛔ Không deploy. Không sửa `C:\LTTPlatform\app\`. Không đụng `D:\LTTSTUDIOSAPP` (cây chính)
  hay cây của làn khác. Chỉ kill tiến trình bạn khởi động. Không `stash/reset/checkout --`.
- Test mới đặt số trong DẢI của làn (brief riêng ghi). Test nhắm: `python -m pytest <tệp> -q`.
  ⛔ Không chạy `tools/gate.py` (L1/L2/L3) — điều phối lo gate.
- Commit trên nhánh làn của bạn, `git add` TƯỜNG MINH từng tệp. Kết thúc commit message bằng
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## Bẫy công cụ đã trả giá (memory dự án)

- Tool Bash **nuốt backslash** trong heredoc ⇒ script sửa tệp viết bằng Write rồi chạy.
- `Path.write_text` đổi CRLF ⇒ đọc/ghi bytes, giữ kiểu xuống dòng của tệp gốc.
- Tệp tiếng Việt: in ra console cần `PYTHONIOENCODING=utf-8`.

## Hợp đồng sản phẩm đã khoá (chủ dự án 22/09)

- Nguồn `{zh, en, vi}` → đích `{vi, en}` (`apps/auto_scan_video/ngon_ngu.py` — một chỗ).
- MỘT giọng thuyết minh / lần chạy (`AUTO_MATCH` | `USER_SELECTED`). Không đa giọng, không phân vai.
- Phụ đề: dùng lại năng lực `apps/autosubvideo` (mở rộng nó nếu thiếu), không viết engine mới.
- Không public API. Chỉ cổng workflow NỘI BỘ.
- Tính năng đổi điểm ảnh chỉ ở preset `smart_localize`; `localize_preserve_picture` sao chép luồng hình.

## Bộ đo (luật §2–§6, §18–§22 của đề bài)

- **Loại A** (sự thật tất định: ffprobe, loudnorm, blackdetect, hình học, timestamp) ⇒ GIỮ.
- **Loại B** (điểm/heuristic/trọng số/công thức tự nghĩ) ⇒ thay bằng OSS đã thành danh, có benchmark,
  rồi XOÁ bản cũ (mọi import/call/test/docs). Không để `old_score` + `new_score` song song.
- Trước khi cài/tải model: kiểm **license code VÀ license weights riêng**, từ nguồn gốc (model card,
  LICENSE). NC / research-only / chưa xác minh ⇒ **DO NOT SHIP**. Kết quả nghiên cứu đã có:
  `docs/auto_scan_video_final/OPEN_SOURCE_METRIC_AUDIT.md` (điều phối viết).
- Model thiếu ⇒ đánh dấu QC `khong_kha_dung`; ⛔ không lùi im lặng về heuristic tự chế.
- Model tải về: có phiên bản, checksum, tài liệu, lặp lại được; nằm ở thư mục model chuẩn
  (`C:\LTTPlatform\hf-cache` qua `HF_HOME`), KHÔNG rải trong `apps/auto_scan_video/`.
- Mỗi model mới: đo CPU/RAM/GPU/VRAM/độ trễ; không chiếm GPU làm nghẽn Voice/VLM.

## Báo cáo cuối (≤ 250 từ)

SHA commit cuối, đạt/đỏ (tệp test + số), số đo chính, việc còn lại, và mọi quyết định bạn tự chốt
mà điều phối cần biết. Chi tiết dài ghi vào tệp `docs/auto_scan_video_final/<LÀN>.md` trong cây của bạn.
