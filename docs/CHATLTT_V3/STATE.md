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
| Pha hiện tại | P00–P04 ✅ (P04 trừ **R2b**) · **P05 85 %** → Làn A còn ~1 ngày công |
| Deploy | ⛔ chương trình này **chưa deploy**. Làn A phát hành sau cờ `LTT_CHATLTT_V3_TOOLS` |

🔑 **Cờ `LTT_CHATLTT_V3_TOOLS` và `LTT_CHATLTT_V3_PAID_TOOLS` đều đang TẮT, và
độc lập với nhau.** Không một dòng nào đã viết chạm tới một người dùng thật.

## 🔒 Điều kiện để BẬT `LTT_CHATLTT_V3_TOOLS` — món nợ tự đòi

⛔ **Đọc mục này trước khi bật cờ, kể cả bật để thử.**

| # | Điều kiện | Trạng thái |
|---|---|---|
| 1 | Gate đầy đủ PASS trên cây này | ✅ `20260905T052942Z-17052.json` |
| 2 | **Mở trình duyệt thật, xem bốn nhãn trạng thái V3 hiện đúng** | ✅ **05/09** — xem §dưới |
| 3 | Kiểm trên URL công khai, không chỉ loopback (`CLAUDE.md` 5b) | ❌ chưa |
| 4 | R2b được chủ dự án chốt | ❌ đang chạy theo giả định (b) |

### Điều kiện 2 — ĐÃ GỠ, và nó bắt được một lỗi trước khi trình duyệt kịp mở

**Đã kiểm 05/09** trên tiến trình riêng (cổng **8199**, CSDL vứt đi, cờ V3 BẬT)
— không đụng bản production đang chạy ở 8100. Kết quả:

| mã | nhãn người dùng thật sự đọc |
|---|---|
| `tran_vong` | Đã dừng sau số vòng tối đa — hãy hỏi tiếp nếu còn thiếu |
| `tran_tool` | Đã dừng vì gọi công cụ quá nhiều lần trong một lượt |
| `tran_trung` | Đã dừng vì công cụ được gọi lặp lại với cùng tham số |
| `huy` | Đã dừng theo yêu cầu |

**Không mã thô nào rơi ra màn hình.** 0 lỗi console, mọi API 200, và bundle được
phục vụ là `main-Db3wVmJH.js` — đúng mã băm build sau khi thêm nhãn, nên đây là
mã của tôi chứ không phải bản cũ trong cache.

### 🔴 Và nó bắt được một lỗi mà 250 phép kiểm không thấy

Khi **gieo dữ liệu** để xem, `hoi_thoai.kiem_khoi()` **từ chối** khối `tool_call`:

```
ThamSoSai: khoi khong hop le: {'type': 'tool_call', ...}
```

`LOAI_KHOI` không khai `tool_call`. V3 vẫn **ghi được** vì `luot_v3._them_khoi`
gán thẳng `tra_loi.blocks`, **vòng qua** `kiem_khoi()`. Nên lỗi không nổ ở đường
V3 — nó nằm chờ ở `hoi_thoai.cap_nhat_khoi()`, tức luồng **sửa / tạo lại** sẽ từ
chối đúng tin nhắn mà V3 vừa tạo.

⭐ Không phép kiểm nào trong 250 cái bắt được, vì **tất cả đều đi đường V3** —
đường duy nhất không kiểm. Đã khai `tool_call` ở **cả hai phía** (`tables.LOAI_KHOI`
và `kieu.ts LoaiKhoi`) và ghim bằng `test_807` mục 8.

⛔ Điều này **không** mâu thuẫn với A5: A5 nói về loại khối **chưa ai định
nghĩa**; đây là loại ta **chủ động sinh ra**. Một loại mình tự ghi mà không khai
là một loại sẽ bị chính mình từ chối.

### Còn lại của điều kiện 2

Khối `tool_call` hiện **chưa được vẽ gì cả** — người dùng thấy phần chữ và nhãn
trạng thái, không thấy dấu vết lời gọi công cụ. Đó **đúng A5** (bỏ qua khối chưa
có bộ vẽ, không vỡ), nhưng nghĩa là **P09 vẫn phải dựng bộ hiển thị tool_call**.

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
| **A** | P03 kernel điều phối | 5,0 | **5,0** ✅ | — |
| **A** | P04 duyệt bền + tiền | 4,5 | **4,0** (trừ R2b) | 0,5 |
| **A** | P05 ảnh/tiếng thành tool | 3,5 | **3,0** (85 %) | 0,5 |
| | **Làn A** | **17,0** | **15,9** | **1,1** |
| **B** | P06 · P07 · P08 | 20,0 | 0 | 20,0 |
| **C** | P09 · P10 · P11 · P12 | 14,0 | 0 | 14,0 |
| | **TOÀN CHƯƠNG TRÌNH** | **51,0** | **15,9** | **35,1** |

### Con số

| | |
|---|---|
| **Toàn chương trình (P00→P12)** | **≈ 31 %** |
| **Làn A** (phần phát hành được một mình) | **≈ 94 %** |
| Mã sản phẩm đã sửa | 14 tệp · 16 tệp test · 1 migration |
| Phép kiểm mới | **250** (backend 800–816: 241 · frontend A5: 9) |

## Pha đã đóng

| Pha | Kết quả | Sản phẩm |
|---|---|---|
| **P00** nguồn chân lý + ma trận khoảng trống | **PASS** — trunk xác định bằng đo; call graph đủ hai đường có `tệp:dòng`; 43 hạng mục phân loại (GIỮ 7 · MỞ 12 · XÂY 21 · HOÃN 3) | `00_SOURCE_TRUTH.md` · `00_CALL_GRAPH.md` · `00_REFERENCE_MATRIX.md` · `00_GAP_MATRIX.md` · `00_DO_NOT_REWRITE.md` |
| **P01** qualification Qwen3.8 | **PASS** — 581 lượt gọi · **0 hỏng** · **0 credit** · 40 phút GPU. Bốn cổng: Cổng 0 20/20 · lô chính 9/9 chỉ số · ngữ cảnh sâu 22/22 tới 128K · đường ống LTT 7/7 | `01_M1_*.md` · `01_NGUONG_VA_MA_TRAN.md` · `01_*_KET_QUA.md` · `01_PHAN_QUYET.md` |
| **P02** ADR điều phối | **PASS** — phương án **A** (ChatLTT tự sở hữu bộ điều phối) 47 điểm, trên B 37 · LangGraph 32 · LibreChat 22 | `02_ADR_ORCHESTRATION.md` · `02_ADR_R1_MOT_SUAT.md` · `02_HOP_DONG.md` |

## P03 · P04 · P05 — đã xây gì

| Hạng mục | Phép kiểm | Pha |
|---|---|---|
| `gop_manh.py` — gộp mảnh `tool_call.delta` | test_801 (15) | P03 ✅ |
| `chieu_tool.py` — **cổng thứ tư** `CHO_MODEL_GOI` | test_802 (14) | P03 ✅ |
| Bất biến tiền C2 (số học thuần, 100.000 dãy) | test_803 (10) | P03 ✅ |
| `thi_hanh.py` — lỗi là kết quả, không phải ngoại lệ | test_804 (15) | P03 ✅ |
| `dieu_phoi.py` — máy trạng thái + 3 trần | test_805 (18) | P03 ✅ |
| Ba bảng + migration `4b8e21c6d907` (chỉ thêm) | test_616 · test_211 | P03 ✅ |
| `co_v3.py` + nối vào `luot.py` | test_806 (19) | P03 ✅ |
| `luu_run.py` — run/step xuống CSDL | test_807 (20) | P03 ✅ |
| `tool_noi_bo.py` — đồng hồ + máy tính (AST whitelist) | test_808 (47) | P03 ✅ |
| **A5** — bộ hiển thị bỏ qua khối lạ | `KhoiLa.test.tsx` (9) | P03 ✅ |
| `duyet.py` — phiếu duyệt **bền** | test_809 (30) | P04 ✅ |
| `dieu_phoi.CanDuyet` + `tiep_tuc()` | test_810 (16) | P04 ✅ |
| Hai cửa HTTP `/api/duyet/*` | test_811 (29) | P04 ✅ |
| `bo_chay_tool.py` — `chay_tool` hai kết cục | test_812 (17) | P04 ✅ |
| `luot_v3.py` — vòng lặp agentic **chạy thật** | test_813 (8) | P04 ✅ |
| `luu_run.dung_lai()` — dựng lại `Run` từ CSDL | test_814 (16) | P04 ✅ |
| `dieu_phoi.ChoJob` — chờ job nền | test_815 (27) | P05 ✅ |
| Nộp job sau duyệt + `tao_media.tao(tin_nhan=…)` | test_816 (10) | P05 ✅ |
| `CHO_MODEL_GOI` mở `image.ltt` · `speech.ltt` | test_802 | P05 ✅ |
| **R2b** — một `request_id` cho cả run | — | P04 ⏸ **chờ `thanh_toan.py`** |
| Đường **ĐẨY** khi job xong (móc `job_runner`) | — | P05 ⏸ ngoài ranh giới app |
| UI duyệt ở frontend | — | P09 |

### Năm phát hiện mà kế hoạch không có

**1. Một mã thô suýt rơi ra màn hình người dùng.** `ThongDiepView.tsx` dựng nhãn
bằng `NHAN_TRANG_THAI[ma] ?? ma`, và bốn lý do kết của V3 đều **chưa có nhãn** —
người dùng sẽ đọc thấy đúng chuỗi `tran_vong` giữa câu trả lời. Không ném, không
đỏ, nên không cảnh báo nào kêu. Đã thêm bốn câu, **kiểm bằng đột biến**.

**2. `chatltt_run` không thể là `OPERATIONAL`.** Bảng ấy chỉ có số đếm nên xếp
`OPERATIONAL` nghe hợp lý — và sai: nó **tự già đi theo hạn riêng**, nên một ngày
các `run` bị dọn trong khi hội thoại vẫn còn, và người dùng mở lại lượt cũ thấy
các bước biến mất khỏi một tin nhắn nguyên vẹn.

**3. Sổ handler tool nội bộ phụ thuộc THỨ TỰ IMPORT.** Chỉ `chieu()` nhập
`tool_noi_bo`, nên mọi đường **không** đi qua nó — chạy tiếp sau duyệt, job nền,
lệnh CLI — thấy `LOI_CHUA_CAI` cho một tool bình thường. `test_812` đỏ ba phép
kiểm vì đúng chuyện này; chạy riêng thì xanh hay đỏ tuỳ **tệp nào chạy trước**.
Chốt bằng một phép kiểm chạy **tiến trình mới** — cách duy nhất tái hiện được.

**4. `_dem_bam` là một dict trong RAM.** Không dựng lại thì mỗi lần chờ duyệt là
một lần **xoá sạch** bộ đếm trùng, và một model kẹt vòng lặp chỉ cần xin duyệt
**một** lần là thoát trần, mãi mãi.

**5. `dong_bo` THAY TOÀN BỘ `tin.blocks` khi job xong.** Đúng cho đường nút bấm
(mỗi lần tạo là một tin nhắn riêng). Với V3 thì tin nhắn ấy đang mang khối
`tool_call` của cả lượt và phần chữ model đã nói — thay toàn bộ là **xoá sạch**
chúng, và người dùng thấy một bức ảnh xuất hiện thay chỗ câu trả lời vừa đọc.

### Hai lần phải viết lại phép kiểm của chính mình

`test_802` đổi **hai lần**, và lần nào cũng vì tập hợp thật sự rộng ra:

| Ghim ban đầu | Vì sao không còn đúng |
|---|---|
| P03: *"mặc định rỗng"* | P03 mở hai tool nội bộ miễn phí |
| P04: *"mọi thứ model gọi được đều KHÔNG cần duyệt"* | P05 mở `image.ltt`/`speech.ltt` — **có** cần duyệt |

🔑 Nên mệnh đề giữ lại phải **không đổi theo tập hợp**, và đó là mệnh đề về tiền:
với **mọi** tên trong `CHO_MODEL_GOI`, hoặc nó không cần duyệt, hoặc gọi qua
`thi_hanh` mà không có phép rõ ràng thì **bị từ chối**. Thêm một tool `PAID` mà
quên đường duyệt ⇒ phép kiểm đỏ.

### E2 — trả lời bằng một lệnh `grep`

`image.edit` **không tồn tại**: không `manifest.py` nào khai nó
(`05_E2_ANH_TIENG_THANH_TOOL.md` §1). ⇒ **HOÃN**, đúng luật của
`00_GAP_MATRIX.md`. P01 đo 98,8 % chọn đúng tool *trong số được mời*, nên mời một
tool nền tảng không làm được là **bảo đảm** model sẽ gọi nó.

## Phát hiện của P00 mà gói prompt KHÔNG có

| ID | Phát hiện | Bằng chứng | Trạng thái |
|---|---|---|---|
| **R1** | Cả nền tảng chỉ **một suất LLM đồng thời** ⇒ vòng N bước = N lần giành/nhả | `apps/ltt_llm/manifest.py:197` + yaml `--parallel 1` | ✅ P02 chọn **C** (giành lại mỗi vòng, `WAITING_SLOT`) |
| **R2** | Tiền tính theo **một lần gọi model**, không theo **một lượt** | `chatltt_execution` 3 cột vô hướng | ✅ P02: tổng hợp theo `run_id`, **không** dựng sổ thứ hai |
| **R2b** | 🔴 **Làm tròn C1** thu gấp 2–6 lần giá niêm yết trên lượt agentic **và** trên chat ngắn | `platform_core/llm/thanh_toan.py` | ✅ **đã nghiên cứu, đo, cài xong** — `04_ADR_R2B_TINH_TIEN_LUOT.md`. **OPT-IN** (`LTT_TINH_TIEN_TICH_LUY=1`), mặc định vẫn C1 vì nó đổi **điều khoản công bố** ⇒ chủ dự án chốt |
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

**Gate đầy đủ: `RESULT: PASS`** — `test-results/gates/20260905T052942Z-17052.json`
(05/09). Chạy sau khi P05 đóng, trên đúng cây này.

⭐ **`frontend chatltt` đã CHẠY** (7,6 s, PASS) — 87 phép kiểm vitest, kể cả 9
phép kiểm A5 mới. Trước phiên này nó bị `[BOQUA]` ở **mọi cây**, tức 87 phép kiểm
giao diện chưa bao giờ chạy ở đâu cả.

🔴 **Bốn bước gate TỰ KHAI là bỏ qua — không phải bằng chứng:**

| Bước | Vì sao | Ai gỡ được |
|---|---|---|
| `bat bien da tien trinh` | thiếu `LTT_TEST_DATABASE_URL` (Postgres) | đặt biến môi trường; **chưa chạy ⇒ đừng tính là đã chứng minh** |
| `frontend agent-canvas` | thiếu `node_modules` ở cây riêng | `npm ci` |
| `frontend autosub-studio` | 〃 | 〃 |
| `frontend prompt-ai-ommi` | 〃 | 〃 |

### Một cái bẫy đã trả giá trong phiên này

Thêm một mục `N_()` mới (ba hàng `Store` trong `governance.py`) làm `test_306`
**đỏ**: chuỗi chưa có bản dịch EN. Cách đúng là **THÊM TAY** vào
`locale/en/LC_MESSAGES/messages.po` (msgid + msgstr) rồi `i18n.py bien-dich`.

⛔ **Đừng chạy `i18n.py trich`** — `msgmerge` sẽ **đoán** bản dịch cho chúng, và
một bản dịch đoán là một bản dịch sai mà không ai kiểm. Hạ mốc bằng **DỊCH**,
không bằng **TRÍCH LẠI**.

### Còn phải làm (hạ tầng, không thuộc H44)

1. `npm ci` trong `frontend/chatltt` ở **cây chính** — ở đó vẫn thiếu.
2. Thêm `frontend/*/node_modules` vào luật 1b của `QUY_TRINH_WORKTREE.md`
   (luật đó hiện **chỉ nói** `apps/*/vendor`).

## 💰 R2b — cách tính tiền một lượt (05/09, đã đo và đã cài)

Chủ dự án giao: *"nghiên cứu sâu sắc, tính theo token input/output, tự đề xuất
con số tối ưu"*. Kết luận:

> 🔑 **Bảng giá 50 / 10 / 400 credit/1M là ĐÚNG — đừng đổi.** Neo thị trường đo
> lại hôm nay: `qwen/qwen3.8-27b` = **110,5 / 789**, ta ở **45 % / 51 %**. Thứ
> hỏng là **ranh giới làm tròn**, ở một tầng khác.

| Kịch bản | ta thu | chi phí theo bảng giá | mua lẻ ngoài |
|---|---|---|---|
| hội thoại 20 lượt ngắn | 🔴 **20** | 3,13 | 17,18 |
| chat rất ngắn | 1 | 0,10 | 0,21 (**ta đắt 4,84×**) |
| lượt agentic 4 vòng | 4 | 0,92 | — |

**Đã cài `C3`** (tích luỹ phần lẻ theo người dùng) + migration chỉ-thêm + 20
phép kiểm. **Để OPT-IN** vì nó đổi `toi_thieu_moi_luot_credit` — một **điều
khoản công bố**. Bật bằng `LTT_TINH_TIEN_TICH_LUY=1`.

⚠️ Mọi con số trên đến từ **mô hình**, không phải lượt chạy thật (artefact P01
ghi độ trễ, **không ghi token**). Trước khi bật thu tiền thật: ghi `usage` của
20–50 lượt thật rồi chạy lại. Chi tiết: `04_ADR_R2B_TINH_TIEN_LUOT.md`.

## Chặn ngoài đang mở

| Chặn | Ảnh hưởng | Ai gỡ |
|---|---|---|
| ~~Một lượt gate đầy đủ~~ | ~~P03~~ | ✅ **đã chạy 05/09, PASS** |
| **R2b: quyết định vĩnh viễn** | cách tính tiền một lượt agentic | 🔴 **chủ dự án** — đang chạy theo giả định **(b) C2-trong-run** |
| `platform_core/llm/thanh_toan.py` bị phiên khác giữ | phần R2b còn lại của P04 | phiên điều phối (đã mở theo điều kiện Đ1–Đ4) |
| Ngưỡng credit tự chạy (§6b-5) · `image.generate` mây (§6b-6) · Làn B có chạy hết không (§6b-7) | P05 · Làn B | **chủ dự án** |
| Deploy + kiểm URL công khai (bấm UAC) | P12 | **chủ dự án** |

### ⚠️ Một giới hạn đã biết, không phải một thiếu sót bị bỏ quên

`_danh_thuc_run` (đánh thức run khi job xong) là đường **KÉO**, không phải đường
**ĐẨY**: `tao_media.dong_bo` chỉ chạy khi **client hỏi** (nhịp 2 giây). Không ai
mở hội thoại thì run nằm im ở `WAITING_BACKGROUND`.

⭐ **Không mất dữ liệu:** job đã xong, tiền đã quyết toán, kết quả đã nằm trong
`blocks`. Thứ chưa xảy ra chỉ là **vòng model nói về** bức ảnh đó.

⛔ Đường ĐẨY thật phải là một chỗ móc trong `job_runner` — `platform_core`, ngoài
ranh giới của app này. Ghi ở đây để phiên sau **không tưởng nó đã được giải
quyết**, và cũng không tưởng đó là một lỗi bị bỏ sót.
