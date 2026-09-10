# 00_STATUS — bảng điều phối chương trình 4 bot → 4 App

> ⛔ **Đây là bảng điều phối, không phải nguồn chân lý.** Nguồn chân lý là mã
> nguồn và `docs/00_LTT_OPERATING_CONTRACT.md`. Một bảng chép tay không có cách
> nào tự biết nó đã cũ — cơ chế đó đã nói sai năm lần trong kho này.

Cập nhật lần cuối: **2026-09-10 05:30**.
Nguồn: `docs/migration/workflow_apps/01_SOURCE_MANIFEST.md`.

| Phase | Trạng thái | Bằng chứng | Chặn | Kế |
|---|---|---|---|---|
| 00 FAST BUILD governance | **XONG** | hợp đồng §4.10 · `tools/ho_so_cay.py` · `gate.py --tu` · `tests/test_1100` · `FAST_BUILD_WORKTREE_DESIGN.md` · `WORKTREE_ADOPTION_MATRIX.md` · `FAST_BUILD_OPERATOR_GUIDE.md` | — | — |
| 01 LTT runtime baseline | **XONG** | `02_LTT_RUNTIME_BASELINE.md` · vá R1 `foreach.py` + `tests/test_1101` | — | — |
| 02 Audit Transcript | **XONG** | `03_AUDIT_BOT_TRANSCRIPT.md` | S11·S12 | — |
| 03 Audit Pause | **XONG** | `04_AUDIT_BOT_PAUSE.md` | S11·S13 | — |
| 04 Audit GEM | **XONG** | `05_AUDIT_BOT_GEM.md` + `09_QUYET_DINH_GEM_BO_TRINH_DUYET.md` | — | — |
| 05 Audit Video Assembly | **XONG** | `06_AUDIT_BOT_DUNGVIDEO.md` | S10·S11·S14 | — |
| 06 Cross-bot synthesis | **XONG** | `07_CROSS_BOT_SYNTHESIS.md` | — | — |
| 07 App contracts + Workflow UX | **XONG** | `23_APP_BOUNDARIES.md` · `24_NODE_CONTRACTS.md` · `26_WORKFLOW_UX.md` | — | 08 |
| 08 Build Transcript | **XONG** | `apps/transcript` · `platform_core/stt` · `test_1102`+`test_1103` | — | 12 |
| 09 Build Pause | **XONG** | `apps/audio_pause` · `test_1104` | — | — |
| 10 Build GEM | **XONG** | `apps/prompt_canh` (đổi slug) · `test_1105` | — | — |
| 11 Build Video Assembly | **XONG** | `apps/video_assembly` · `test_1106` | — | — |
| 12 Legacy workflow rebuild | **MỘT PHẦN** | `32_PHASE12_...md` · `tests/test_1111` — 4 App chạy được như node, dữ liệu chảy giữa 2 node | Canvas/V2 **không có bộ thi hành**; Drive/Sheets connector chưa audit | 13 |
| 13 Workflow hardening | CHƯA | | | |
| 14 Agent re-evaluation | CHƯA | | | |
| 15 Final cutover | CHƯA | | | |

## Bốn quyết định của chủ dự án — 2026-09-09

| | Quyết định |
|---|---|
| S2 | `gem` **bỏ hẳn lái trình duyệt**, chỉ gọi qua `runtime_noi_bo` — `09_...` |
| S1 | nhánh nguồn chân lý của `bot_gem` là **`master`** |
| S9 | giữ **thứ tự của pack**: `transcript` trước |
| S8 | cấu hình thật đọc từ `D:\FULL AUTO VIDEO` (chỉ-đọc) — `08_...` |

⚠️ S2 thay provider giữa lúc migrate. Tôi đã nêu, chủ dự án đã quyết. Hệ quả ghi
ở `09` §1: `gem` **không còn đo được parity** — chuẩn nghiệm thu của nó là **hợp
đồng đầu ra**, không phải so với legacy.

## Bốn App đã dựng — 2026-09-10

| App | slug | job_type | engine chuyển |
|---|---|---|---|
| Phiên âm | `transcript` | `transcript.run` | 17 tệp / 3.936 dòng |
| Chèn khoảng lặng | `audio_pause` | `audio_pause.run` | 4 tệp / ~1.700 dòng |
| Kịch bản → prompt | `prompt_canh` | `prompt_canh.run` | **viết lại**, 3 template |
| Dựng video | `video_assembly` | `video_assembly.run` | 29 tệp / ~6.900 dòng |

Cả bốn: `group="Workflow"` · `public=False` · `lifecycle="development"` ·
`api_exposed=False`. Mở từng cổng **sau** khi parity đóng, mỗi lần một cổng.

⭐ **Hai lần `test_60` ép ra một cái tên TỐT HƠN**, không chỉ một cái tên khác:
hồ sơ STT đổi từ tên App (`transcript`) sang tên **năng lực**
(`moc_tu_vad_ngoai`), và slug `gem` — chuỗi con của `gemini` trong
`providers.py` — đổi thành `prompt_canh`.

## Sổ nợ — `S1`–`S14` ĐÃ ĐÓNG HẾT

Mười bốn mục, đóng trong hai ngày. Bốn mục cuối (`S11`–`S14`) sinh ra từ chính
việc đọc cấu hình đang chạy, và cả bốn đều là **đo lại**, không phải xây thêm.

⛔ **Nhưng "hết nợ" không có nghĩa là "xong".** Thứ chưa có, và phải nói thẳng:

| Còn thiếu | Vì sao nó chưa làm được |
|---|---|
| **fixture parity trên dữ liệu thật** | cần audio/clip mẫu — chưa có bộ nào an toàn để dùng |
| **E2E chạy thật qua worker** | cần một lượt job đi hết hàng đợi → worker → artifact |
| **kiểm trình duyệt trên URL công khai** | bốn App đổi giao diện; hợp đồng §9 đòi chốt trên `app.lttstudios.com` |
| **đo `vram_min_mb` thật** cho `video_assembly` | con số 8000 hiện là **ước tính**, bốn model một job |

⇒ Bốn App có **hợp đồng, ranh giới và phép kiểm đơn vị**. Chúng **chưa** được so
với legacy trên một tệp thật. Đó là Phase 12–15, và nó cần dữ liệu mẫu.

## Hồ sơ vận hành của cây này

`FAST_BUILD` từ sau khi Phase 00 đóng — luật ở hợp đồng §4.10, trạng thái hỏi
bằng `python tools\ho_so_cay.py trang-thai`.

Phase 00 **tự nó** chạy theo `NORMAL`: một prompt không có quyền nới cadence
trước khi hợp đồng canonical được sửa. Đó là chi phí một lần để không tồn tại
hai nguồn luật cùng lúc.

## Chuẩn nghiệm thu đã đóng băng

- Hành vi **P0/P1: giữ 100%**, trừ khi người dùng duyệt cho khai tử một mục cụ thể.
- Parity người dùng nhìn thấy, có trọng số: **≥95%**.
- Không đòi bằng nhau từng byte cho đầu ra LLM — dùng phép đo cấu trúc/ngữ nghĩa
  được đóng băng trong chính bản audit của bot đó.
