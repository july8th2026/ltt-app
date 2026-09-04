# CHATLTT V3 (H44) — STATE

> SSOT bàn giao giữa các phase. Chỉ chứa **sự thật hiện tại**.
> Bằng chứng ở các tệp `00_*.md`/`01_*.md`/`02_*.md`. Kế hoạch ở `00_KE_HOACH_V3.md`.
> Máy đọc: `state.json`.

## Định danh chương trình

| Mục | Giá trị |
|---|---|
| Gói prompt | `G:\My Drive\AI\A LTT AII\LTTCHAT_V3_AGENTIC_MULTIMODAL_PROMPT_PACK` (P00→P12) |
| Mã chương trình | **H44** · quyết định **Q121+** |
| Cây | `D:\LTTSTUDIOSAPP\.claude\worktrees\chatltt-v3-agentic` |
| Nhánh | `claude/chatltt-v3-agentic` |
| **BASE_SHA** | `72a484c5f281f4d909e72927648df7dd62e5e196` (`admin-mvp-v3` = `origin/admin-mvp-v3`, 0/0) |
| FINAL_SHA | *(chưa)* |
| Dải test | **800–899** |
| Pha hiện tại | P00 ✅ · P01 ✅ · P02 ✅ · **P03 95 %** → còn **một lượt gate đầy đủ** |
| Deploy | ⛔ chương trình này **chưa deploy**. Làn A phát hành sau cờ `LTT_CHATLTT_V3_TOOLS` |

🔑 **Cờ `LTT_CHATLTT_V3_TOOLS` và `LTT_CHATLTT_V3_PAID_TOOLS` đều đang TẮT, và
độc lập với nhau.** Không một dòng nào đã viết chạm tới một người dùng thật.

## Quyết định của chủ dự án (2026-09-04)

| # | Câu | Quyết định | Hệ quả |
|---|---|---|---|
| 1 | Reset máy B để A/B KV? | 🟢 **ĐƯỢC — chưa có khách thật** | hồ sơ tạm `qwen38-tooltest` không rủi ro khách |
| 2 | Ngân sách P01 | 🟢 **Claude tự định** ⇒ trần 3.500 credit + ~11 h GPU | **dùng hết 0 credit · 40 phút GPU** |
| 3 | q4_0 hỏng tool-call thì sao? | 🟢 **GIỮ 200K NGỮ CẢNH** | q4_0 khoá theo hệ quả; A/B thành **phép chẩn đoán**, sau đó **hạ ưu tiên** |

## Ranh giới với phiên khác (đo 05/09)

| Phiên | Vùng giữ | Trạng thái |
|---|---|---|
| `ltt-llm-api-http-guide-*` | LTT VIDEO AI V3 — `platform_core/video_gen/`, `tests/test_70x_*`, `tools/video_cloud.py`, `docs/VIDEO_AI/` | sống. Không dùng máy B (GPU đi cloud) ⇒ không tranh GPU; **có** tranh lõi CPU khi chạy gate |
| ASV (`auto-scan-video-v4-mvp`) | `apps/auto_scan_video/`, `apps/asv_*`, `tests/test_4xx_asv_*` | có ghi |
| Phiên điều phối | `tools/cua_so_yen.py`, `tools/gate.py`, **`platform_core/llm/thanh_toan.py`** | giữ khoá. Sẽ báo **"HÀNG ĐỢI TRỐNG"** khi tôi được một lượt gate |
| **H44 (phiên này)** | `apps/chatltt/`, `frontend/chatltt/`, `docs/CHATLTT_V3/`, `tests/test_8xx` | — |

⚠️ `platform_core/public_api/governance.py` đã sửa (thêm 3 hàng khai hạng giữ dữ
liệu). Ngoài vùng giữ danh nghĩa, nhưng là **sổ đăng ký bắt buộc** — mọi bảng
mới của mọi app đều phải khai ở đó, `test_211` cưỡng chế.

## Tiến độ — đo bằng NGÀY CÔNG, không bằng số pha

⛔ Đếm pha là cách đếm gian: P00 mất nửa ngày, P03 mất năm ngày, cả hai đều là
"một pha". Bảng dưới quy về ngày công theo ước lượng trong `00_KE_HOACH_V3.md`.

| Làn | Pha | Ước (ngày) | Xong | Còn |
|---|---|---|---|---|
| **A** | P00 nguồn chân lý | 0,5 | **0,5** ✅ | — |
| **A** | P01 qualification Qwen | 2,5 | **2,5** ✅ | — |
| **A** | P02 ADR điều phối | 1,0 | **1,0** ✅ | — |
| **A** | P03 kernel điều phối | 5,0 | **4,3** (95 %) | 0,7 |
| **A** | P04 duyệt bền + tiền | 4,5 | 0 | 4,5 |
| **A** | P05 ảnh/tiếng thành tool | 3,5 | 0 | 3,5 |
| | **Làn A** | **17,0** | **8,3** | **8,7** |
| **B** | P06 · P07 · P08 | 20,0 | 0 | 20,0 |
| **C** | P09 · P10 · P11 · P12 | 14,0 | 0 | 14,0 |
| | **TOÀN CHƯƠNG TRÌNH** | **51,0** | **8,3** | **42,7** |

### Con số

| | |
|---|---|
| **Toàn chương trình (P00→P12)** | **≈ 16 %** |
| **Làn A** (phần phát hành được một mình) | **≈ 49 %** |
| Mã sản phẩm đã sửa | 9 tệp · 8 tệp test · 1 migration |
| Phép kiểm mới | **136** (backend 800–808: 127 · frontend A5: 9) |

## Pha đã đóng

| Pha | Kết quả | Sản phẩm |
|---|---|---|
| **P00** nguồn chân lý + ma trận khoảng trống | **PASS** — trunk xác định bằng đo; call graph đủ hai đường có `tệp:dòng`; 43 hạng mục phân loại (GIỮ 7 · MỞ 12 · XÂY 21 · HOÃN 3) | `00_SOURCE_TRUTH.md` · `00_CALL_GRAPH.md` · `00_REFERENCE_MATRIX.md` · `00_GAP_MATRIX.md` · `00_DO_NOT_REWRITE.md` |
| **P01** qualification Qwen3.8 | **PASS** — 581 lượt gọi · **0 hỏng** · **0 credit** · 40 phút GPU. Bốn cổng: Cổng 0 20/20 · lô chính 9/9 chỉ số · ngữ cảnh sâu 22/22 tới 128K · đường ống LTT 7/7 | `01_M1_*.md` · `01_NGUONG_VA_MA_TRAN.md` · `01_*_KET_QUA.md` · `01_PHAN_QUYET.md` |
| **P02** ADR điều phối | **PASS** — phương án **A** (ChatLTT tự sở hữu bộ điều phối) 47 điểm, trên B 37 · LangGraph 32 · LibreChat 22 | `02_ADR_ORCHESTRATION.md` · `02_ADR_R1_MOT_SUAT.md` · `02_HOP_DONG.md` |

## P03 — bóc chi tiết 95 %

| Hạng mục | Phép kiểm | Trạng thái |
|---|---|---|
| `gop_manh.py` — gộp mảnh `tool_call.delta` | test_801 (15) | ✅ |
| `chieu_tool.py` — **cổng thứ tư** `CHO_MODEL_GOI` | test_802 (14) | ✅ |
| Bất biến tiền C2 (số học thuần, 100.000 dãy) | test_803 (10) | ✅ |
| `thi_hanh.py` — lỗi là kết quả, không phải ngoại lệ | test_804 (14) | ✅ |
| `dieu_phoi.py` — máy trạng thái 12 trạng thái + 3 trần | test_805 (18) | ✅ |
| Ba bảng + migration `4b8e21c6d907` (chỉ thêm) | test_616 | ✅ |
| `co_v3.py` + nối vào `luot.py` | test_806 (19) | ✅ |
| `luu_run.py` — run/step xuống CSDL | test_807 (20) | ✅ |
| `tool_noi_bo.py` — `noi_bo.thoi_gian` · `noi_bo.tinh` | test_808 (46) | ✅ |
| **A5** — bộ hiển thị bỏ qua khối lạ | `KhoiLa.test.tsx` (9) | ✅ |
| Ba bảng khai hạng giữ dữ liệu | test_211 | ✅ |
| **Một lượt gate đầy đủ để chốt** | — | ⏳ chờ **"HÀNG ĐỢI TRỐNG"** |

### Hai phát hiện của P03 mà kế hoạch không có

**1. Một mã thô suýt rơi ra màn hình người dùng.** `ThongDiepView.tsx` dựng
nhãn trạng thái bằng `NHAN_TRANG_THAI[ma] ?? ma`. Bốn lý do kết của V3
(`tran_vong` · `tran_tool` · `tran_trung` · `huy`) đều **chưa có nhãn**, nên
người dùng sẽ đọc thấy đúng chuỗi `tran_vong` giữa câu trả lời. Không ném,
không đỏ, nên không cảnh báo nào kêu — nó chỉ làm sản phẩm trông như bản chưa
làm xong. Đã thêm bốn câu, và **kiểm bằng đột biến**: gỡ một nhãn ra thì phép
kiểm đỏ.

**2. `chatltt_run` không thể là `OPERATIONAL`.** Bảng ấy không chứa chữ của ai —
chỉ số đếm và ba cột tiền — nên xếp `OPERATIONAL` nghe hợp lý. Và sai:
`OPERATIONAL` **tự già đi theo hạn riêng**, nghĩa là một ngày các `run` bị dọn
trong khi hội thoại chứa chúng vẫn còn, và người dùng mở lại một lượt cũ thấy
các bước biến mất khỏi một tin nhắn vẫn nguyên vẹn. Một hội thoại phải có **một**
lời hứa giữ dữ liệu, không phải hai lời hứa lệch nhau bên trong nó.

## Phát hiện của P00 mà gói prompt KHÔNG có

| ID | Phát hiện | Bằng chứng | Trạng thái |
|---|---|---|---|
| **R1** | Cả nền tảng chỉ **một suất LLM đồng thời** ⇒ vòng N bước = N lần giành/nhả | `apps/ltt_llm/manifest.py:197` + yaml `--parallel 1` | ✅ P02 chọn **C** (giành lại mỗi vòng, `WAITING_SLOT`) |
| **R2** | Tiền tính theo **một lần gọi model**, không theo **một lượt** | `chatltt_execution` 3 cột vô hướng | ✅ P02: tổng hợp theo `run_id`, **không** dựng sổ thứ hai |
| **R2b** | 🔴 **Làm tròn C1** biến lượt 8 vòng từ 2,3 credit thật thành **8 credit thu** | `platform_core/llm/thanh_toan.py` §C1 | ⚠️ chạy theo giả định **(b) C2-trong-run**; quyết định vĩnh viễn **chờ chủ dự án**. Đường đi được là **một `request_id` cho cả run** ⇒ **P04** |
| **U-1** | llama.cpp gọi đích danh `-ctk q4_0` *"substantially degrade"* tool calling | `docs/function-calling.md:332-333` | ✅ đo 22/22 tới 128K ⇒ **không tái hiện**; A/B hạ ưu tiên |
| **U-2** | `parallel_tool_calls` **tắt mặc định** ở llama.cpp | `function-calling.md:24` | ✅ đã gửi cờ; test_806 chốt |
| **M-1** | Handler tool-call là Native hay Generic | `chat.cpp:3597-3601` | ✅ **NATIVE** (Qwen3-Coder PEG) — chứng minh bằng mã **và** bằng đo |
| **M-4** | `tool_call_format=json` có phải bẫy im lặng | đo 3/3 vẫn phân tích được | ✅ **bác bỏ, đã đính chính**. Mắt xích thiếu: văn phạm GBNF (`chat.cpp:1201`) thắng prompt. Hạ từ luật *an toàn* xuống luật *vệ sinh* |
| **M-5** | Model tin **DỮ LIỆU** của tool, nhưng không nghe **MỆNH LỆNH** của tool | G0-4 (5/5 lặp lại số sai) vs N10 (30/30 từ chối lệnh tiêm) | 🔴 **mở** — bề mặt lớn hơn không phải lệnh tiêm mà là **dữ liệu sai**. Kernel phải kiểm tính đúng ở chỗ kiểm được ⇒ P06 |
| **M-6** | Khi có `tools`, llama.cpp **cưỡng chế sinh** bằng GBNF (lazy) | `chat.cpp:1201, 1332-1337` | ✅ mạnh hơn giả định ban đầu — nhưng prompt và văn phạm có thể mâu thuẫn mà không ai thấy |

## Giao cho pha sau

| Mục | Pha | Việc |
|---|---|---|
| ~~A5 — bộ hiển thị bỏ qua khối lạ~~ | ~~P03~~ | ✅ **xong** — `KhoiLa.test.tsx`, kiểm bằng đột biến |
| R2b — một `request_id` cho cả run | **P04** | đường duy nhất đi được; ba đường kia đụng `DO_NOT_REWRITE §2` hoặc ranh giới phiên khác |
| Duyệt bền (`chatltt_approval`) | **P04** | hai ràng buộc UNIQUE đã có ở CSDL; còn route + UI + idempotency |
| E2 — `image.edit` có backend thật không | P05 | kiểm năng lực THẬT trước khi khai; không có ⇒ HOÃN, không làm nửa vời |
| M-5 — kiểm tính đúng của dữ liệu tool | P06 | schema · khoảng giá trị · đối chiếu nguồn |
| 128K–170K chưa đo | *(tuỳ)* | ngoài đường ChatLTT (trần 1 lượt ~80K), **trong** đường Public API. ~10 phút nếu cần |

## Cổng chất lượng — trạng thái thật, không chỉ chữ PASS

| | |
|---|---|
| Lượt gate đầy đủ gần nhất | `test-results/gates/20260904T140608Z-10420.json` — **PASS** |
| Từ đó tới nay | thêm 6 tệp mã + 3 tệp test ⇒ **cần một lượt nữa để chốt P03** |
| Lượt `--vong-lap` gần nhất | 6.103 xanh / 5 đỏ → **cả 5 đã sửa**, xanh lại (89/89) |

⭐ **`frontend/chatltt/node_modules` đã cài ở cây này.** 87 phép kiểm vitest của
ChatLTT **thật sự chạy** — trước đó gate tự khai là `[BOQUA]` và **không cây nào**
chạy chúng. Trong 87 có 9 phép kiểm A5 mới.

🔴 **Còn hai việc thuộc hạ tầng, không thuộc H44:**

1. `npm ci` trong `frontend/chatltt` ở **cây chính** — ở đó vẫn thiếu.
2. Thêm `frontend/*/node_modules` vào luật 1b của `QUY_TRINH_WORKTREE.md`
   (luật đó hiện **chỉ nói** `apps/*/vendor`).

## Chặn ngoài đang mở

| Chặn | Ảnh hưởng | Ai gỡ |
|---|---|---|
| Một lượt gate đầy đủ | P03 không chốt được | phiên điều phối báo **"HÀNG ĐỢI TRỐNG"** |
| `platform_core/llm/thanh_toan.py` đang bị phiên khác giữ | R2b/P04 | điều phối — đã mở theo điều kiện Đ1–Đ4 |
| R2b: quyết định vĩnh viễn | P04 tính tiền lượt agentic | **chủ dự án** *(đang chạy theo giả định (b))* |
| Ngưỡng credit tự chạy (§6b-5) · `image.generate` mây (§6b-6) · Làn B có chạy hết không (§6b-7) | P05 · Làn B | **chủ dự án** |
| Deploy + kiểm URL công khai (bấm UAC) | P12 | **chủ dự án** |
