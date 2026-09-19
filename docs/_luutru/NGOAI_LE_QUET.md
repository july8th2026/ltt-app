# Ngoại lệ máy quét tài liệu

Dòng `CHET`/`THAY` của `tools/quet_tai_lieu.py` đã được KIỂM TAY và cố ý giữ nguyên
(tệp · dòng · lý do). Mỗi làn một mục; số dòng theo SHA lúc ghi.

## L-A — `docs/` gốc, CLAUDE.md, AGENTS.md (nhánh `phien/don-tl-la`, 19/09)

Quét: `python tools/quet_tai_lieu.py $(ls docs/*.md) CLAUDE.md AGENTS.md` — 137 dòng, cả 137 thuộc bảng dưới.

| tệp | dòng | lý do |
|---|---|---|
| `CLAUDE.md` | 95, 96 | tệp runtime gitignored có chủ đích (câu cấm commit) — không phải tham chiếu vỡ |
| `docs/00_LTT_OPERATING_CONTRACT.md` | 60, 382 | dòng 60: ví dụ đường dẫn trong repo `ggml-org/llama.cpp`; dòng 382: `.claude/pha_dang_chay.json` là tệp runtime do `tools/hook_khong_dung_giua_pha.py` đọc |
| `docs/01_COPY_LEN_SERVER.md` | 22, 97 | `data/config.json` là tệp runtime gitignored trên máy chủ |
| `docs/BAY_TRONG_CONG_CHAT_LUONG.md` | 1866, 1905, 2072, 2088, 2103, 2762, 2764 | chuyện kể sự cố: `admin-mvp-v3` là nhánh lúc xảy ra; `tools/co_san.py` là tệp giả trong ví dụ test; `tools/video_cloud.py` là cột đo 'không có' |
| `docs/DOI_CHIEU_THUMBNAIL.md` | 18 | đường dẫn trong kho `D:\BOT GEMINI` (dòng 'Gốc (BOT GEMINI)') |
| `docs/HO_SO_HE_THONG.md` | 3, 13, 50, 51 | câu tự nói bộ sinh/test đã bị gỡ (dòng 3) — đúng sự thật |
| `docs/KE_HOACH_NOI_TIEP_2026-08-29.md` | 23, 318, 349 | ảnh chụp trạng thái 29/08 (mục CẦN XEM, đề xuất lưu trữ) — không viết lại lịch sử |
| `docs/KE_HOACH_TRIEN_KHAI.md` | 13 dòng (409…4028) | tracker: mục [x] đã xong/đã xoá có chủ đích (tách routes, gỡ build_system_profile, xoá nap-anh-xa-tinh.ps1), bản ghi `test-results/gates/` runtime, `data/config.json` runtime, đường dẫn `D:\BOT GEMINI` |
| `docs/KHAO_SAT_BOT_GEMINI.md` | 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56 | đường dẫn trong kho `D:\BOT GEMINI` (kiểm 19/09: tồn tại ở đó) |
| `docs/KIEM_KE_VA_LO_TRINH_AGENT.md` | 13 dòng (71…91) | đường dẫn trong kho `D:\BOT GEMINI` (tương đối từ `app/`; kiểm 19/09: tồn tại) |
| `docs/LTT_CLI_COMPAT_DECISIONS.md` | 103, 133 | bằng chứng `tmp/` lúc chạy, không theo dõi git |
| `docs/NHAT_KY.md` | 67 dòng (33…19222) | nhật ký sống, giữ nguyên (Logic bổ sung 1): đường dẫn/nhánh là sự thật lúc ghi; `test-results/`, `tmp/`, `secrets/` là tệp runtime |
| `docs/QUYET_DINH_NEN_TANG.md` | 135, 237, 272, 445, 457 | Q108 kể tệp đã xoá; `src/vieneu/...` là mã trong repo engine ngoài; Q123 kể nguồn gốc nhánh `main` từ `admin-mvp-v3` — đúng sự thật |
| `docs/VAN_HANH_THAT.md` | 64 | `tools/soi_lease_tien.py`/`dem_lease.py` chưa từng vào git (`git log --all` rỗng) và không có trên đĩa 19/09 — chưa rõ thay bằng gì, không đoán; hỏi chủ LLM (L-B `BO_DO_CHUAN.md` cũng trỏ) |
