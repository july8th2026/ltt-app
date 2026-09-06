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
| Pha hiện tại | Làn A ✅ · **P06 ✅ 6/6** · B1–B3 ✅ · **B4 5/6** · **P09 5/6 (06/09)** → còn **B4 bước 6 · B5 · B6 · P10–P12** |
| Deploy | ⛔ chương trình này **chưa deploy**. Làn A phát hành sau cờ `LTT_CHATLTT_V3_TOOLS` |

🔑 **Cờ `LTT_CHATLTT_V3_TOOLS` và `LTT_CHATLTT_V3_PAID_TOOLS` đều đang TẮT, và
độc lập với nhau.** Không một dòng nào đã viết chạm tới một người dùng thật.

## P06 — tệp/tri thức/tìm kiếm (đóng 06/09)

| # | Bước | Kết quả |
|---|---|---|
| 1 | `unaccent` | migration `c7d41e8a2b93`; đo trên Postgres thật |
| 2 | `chatltt_tep` — bảng LIÊN KẾT, **không giữ byte** | `a3f92c5d7e14` |
| 3 | Trích văn bản → `chatltt_doan`, job `chatltt.trich_tep` | `e5b2d9c4a71f` |
| 4 | Chỉ số FTS (`f_unaccent` IMMUTABLE + GIN) | `b8c31f6e9d24` |
| 5 | Trích dẫn `(tep_id, doan_id, trang)` dính liền chữ | `tim_doan.cho_tool` |
| 6 | Mở `noi_bo.tim_tai_lieu` cho model | `CHO_MODEL_GOI`, lớp `READ_ONLY` |

**101 phép kiểm mới** (`test_821`→`test_828`), 4.034 dòng.

⛔ **"Mở cho model" nghĩa là SẴN SÀNG, không phải ĐANG CHẠY.** Vẫn chưa có route
để khách đính tệp, và `LTT_CHATLTT_V3_TOOLS` vẫn TẮT trên production. Người dùng
chưa thấy một thay đổi nào.

🔴 Ba ràng buộc đã trả giá trong P06, ghi lại vì chúng sẽ quay lại:

1. **`unaccent` là STABLE, không IMMUTABLE** ⇒ không index trực tiếp được. Và
   phương án "bỏ dấu ở Python" bị loại vì **hành vi**: Postgres ánh xạ `đ → d`,
   `NFD` thì không — `"đầu tư"`, `"đồng"`, `"điện thoại"` đều lệch.
2. **Thân hàm bọc phải chỉ đích danh schema cho CẢ hàm lẫn từ điển**
   (`public.unaccent('public.unaccent'::regdictionary, $1)`) — Postgres chạy
   biểu thức chỉ số với `search_path` hạn chế. Ba biến thể, chỉ một cái chạy.
3. **Phạm vi hội thoại không được là tham số của model.** `thi_hanh()` nay mang
   `boi_canh` do người gọi đặt, không đi qua schema.

---

## B4 — ghi nhớ (bước 1–5 đóng 06/09, commit `8c368ed7`)

| # | Bước | Kết quả |
|---|---|---|
| 1 | `chatltt_ghi_nho` | migration `d1a7f4c9b620` |
| 2 | `services/ghi_nho.py` — 4 phép, `user_id` là **điều kiện** | `test_830` (25) |
| 3 | tiêm vào `luot.dung_ngu_canh()` sau cờ | `test_831` (11) |
| 4 | 4 route `/api/ghi-nho` + `cong_ghi_nho` | `test_832` (11) |
| 5 | tool `noi_bo.ghi_nho` (`FREE`) — **cửa 4 CÒN ĐÓNG** | `test_833` (15) |
| 6 | `BangGhiNho.tsx` — xem/sửa/xoá, kể cả mẩu **model ghi** | ✅ `BangGhiNho.test.tsx` (12) |

**74 phép kiểm mới** (62 Python + 12 frontend). Kế hoạch + §0 đối chiếu cộng đồng:
`10_KE_HOACH_B4_GHI_NHO.md`.

🔴 Ba ràng buộc đã trả giá trong B4:

1. **`muc_tieu_id` là `""`, không `NULL`.** Trong SQL `NULL != NULL` nên một
   `UNIQUE` chứa cột `NULL` **không chặn trùng** — triệu chứng là kho tự nhân
   đôi, không phải một lỗi ràng buộc. `NULLS NOT DISTINCT` chỉ có ở PostgreSQL
   15+, **không có ở SQLite** tức đường chạy test.
2. **Model không được nêu ĐỊA CHỈ, chỉ được đề nghị ĐỘ BỀN.** `ghi_boi_model()`
   không nhận `user_id`/`conv_id`/`pham_vi`; `cho_phep_lau_dai` của bên gọi là
   **trần** cho cờ `lau_dai` model xin, và bị hạ trần thì hàm **nói ra** qua
   `pham_vi` thật.
3. **`quen`/`thay` không mở cho model được** — khối ghi nhớ tiêm vào ngữ cảnh
   chỉ mang chữ, **không mang `id`** (cố ý: `id` tốn token ở mọi lượt). Kế hoạch
   đã khai `noi_bo.quen` trước khi có cơ chế cho nó; hai phép ấy ở lại phía
   người dùng.

---

## P09 — UX V3 (bước 1–5 đóng 06/09, commit `d2175f7c`)

Kế hoạch + §0: `11_KE_HOACH_P09_UX.md`. Bước 6 (kiểm URL công khai) **còn chặn**
vì cờ V3 chưa bật trên production.

🔴 **P09 lộ ra một lỗ ở BACKEND trước khi chạm tới giao diện.** Khối `tool_call`
mang ba cờ rời và bỏ hẳn `cho_job`, nên một bước **đang chờ job** tuần tự hoá y
hệt một bước **đã xong** — hai ca chỉ khác nhau một chuỗi `tom_tat` rỗng. Chưa
ai thấy vì chưa ai vẽ nó. Nay khối mang một trường `trang_thai` **một chiều**;
`ok`/`cho_duyet` giữ lại **chỉ để đọc ngược** khối cũ.

⭐ Và trình duyệt bắt được thứ bốn phép kiểm đơn vị không thấy: tên khả truy cập
của nút là *"Tính toánĐang chờ bạn duyệt"* — dính liền, vì `gap` của flexbox
tách hai chữ trên **màn hình** chứ không tách trong **chuỗi**.

---

## 🔒 Điều kiện để BẬT các cờ V3 — món nợ tự đòi

⚠️ **BỐN cờ** (cập nhật 06/09). Kế hoạch tổng ghi *"làn B — mỗi nhóm một cờ"*;
cờ nhóm P06 bị bỏ sót suốt P06 lẫn B1/B2, cờ B4 thì khai ngay từ bước 3:

| Cờ | Gác cái gì | Mặc định |
|---|---|---|
| `LTT_CHATLTT_V3_TOOLS` | vòng lặp tool | TẮT |
| `LTT_CHATLTT_V3_PAID_TOOLS` | model **tự** gọi tool có phí | TẮT |
| `LTT_CHATLTT_V3_FILES` | đính tài liệu (P06/B1) — **tốn credit** | TẮT |
| `LTT_CHATLTT_V3_MEMORY` | kho ghi nhớ (B4) — đổi **ngữ cảnh mọi lượt** | TẮT |

⛔ Bốn cờ **độc lập**. Bật cờ tool không kéo theo cờ tệp: đính một tài liệu
tốn tiền ngay cả khi vòng lặp tool tắt.

🔴 Và cờ thứ tư khác ba cờ kia về **bề rộng**: ba cờ đầu gác một **cửa** (tắt thì
một route 404, phần còn lại y nguyên). `_MEMORY` gác **ngữ cảnh của mọi lượt**,
kể cả lượt không đính tệp và không gọi tool. Bật nhầm nó là đổi hành vi toàn sản
phẩm. `test_831` chốt rằng cờ tắt ⇒ `messages` **không đổi một byte**, chứ không
phải "tiêm một khối rỗng".

### Ba điều kiện riêng để bật `LTT_CHATLTT_V3_MEMORY`

| # | Điều kiện | Vì sao |
|---|---|---|
| M1 | ~~P09 vẽ được khối `tool_call`~~ | ✅ **XONG 06/09** (`d2175f7c`) — bốn trạng thái, kiểm trên trình duyệt thật |
| M2 | ~~Giao diện quản lý (bước 6)~~ | ✅ **XONG 06/09** — CRUD kiểm đầu-cuối trên trình duyệt thật |
| M3 | **Đo lại trần 2.000 ký tự/phạm vi** trên 20–50 người dùng thật | hằng số hiện tại là một **neo tự suy** (4 × trần một mẩu), không phải phép đo — và nó tự khai như vậy trong mã |

⛔ Thêm `noi_bo.ghi_nho` vào `chieu_tool.CHO_MODEL_GOI` là một bước **riêng**,
sau cả M1–M3. `test_833::test_CHUA_mo_cua_thu_tu` chốt sự vắng mặt ấy.


⛔ **Đọc mục này trước khi bật cờ, kể cả bật để thử.**

| # | Điều kiện | Trạng thái |
|---|---|---|
| 1 | Gate đầy đủ PASS trên cây này | ✅ `20260905T181119Z-12404.json` — 26 bước · 0 FAIL · `cay_da_doi_giua_chung=False` · sha `4a55620f` |
| 2 | **Mở trình duyệt thật, xem bốn nhãn trạng thái V3 hiện đúng** | ✅ **05/09** — xem §dưới |
| 3 | Kiểm trên URL công khai, không chỉ loopback (`CLAUDE.md` 5b) | ❌ chưa |
| 4 | R2b được chủ dự án chốt | ✅ **06/09 — chốt C3**, đã deploy (`334004d4`), đang thu thật |
| 5 | **Giá trích tài liệu** được chủ dự án chốt | 🟡 **06/09 — đang chạy giá TẠM** `20` mcredit/1.000 ký tự (`apps/chatltt/gia_trich.py`). Cơ chế chạy đầu-cuối; `CHU_DU_AN_DA_CHOT = False` cho tới khi có người chốt. |

⛔ **Và một sự thật không nằm trong bảng trên: hai cờ VẪN TẮT trên
production.** Đo 06/09 sau deploy `334004d4`:

```
grep -c LTT_CHATLTT_V3  C:/LTTPlatform/secrets/app.env   ->  0
```

⇒ Mã Làn A **đã lên production và đã qua gate**, nhưng `LTT_CHATLTT_V3_TOOLS`
mặc định TẮT nên **vòng lặp agentic chưa chạm một người dùng nào**. "100 % mã"
và "0 % tới khách" là hai con số **cùng đúng**, và trộn chúng lại là cách một
báo cáo tiến độ nói dối mà không có câu nào sai.

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

### ⚠️ Ba bước `BOQUA` của cây này là thuộc tính CÂY, không phải của kho

Lượt gate chốt bỏ qua `frontend agent-canvas`, `autosub-studio`,
`prompt-ai-ommi`. **Không** phải vì chúng không áp dụng — mà vì **cây này thiếu
`node_modules`** cho ba app đó. Đối chiếu 06/09 ở **cây chính**: cả ba đều
**PASS** (14,8s / 4,1s / 4,5s). `npm ci` ba thư mục là gỡ hẳn.

🔴 **Và một bước bỏ qua ỔN ĐỊNH nguy hiểm hơn một bước bỏ qua thất thường.**
Nguyên nhân bỏ qua ở đây **không liên quan gì** tới nội dung H44 sửa, nên ba
lượt gate liên tiếp cùng bỏ đúng ba bước ấy — và **ổn định là thứ người ta ngừng
đọc**. Ngày ai đó dùng cây này để chạm vào `agent-canvas`, bước phủ nó sẽ **vẫn**
bỏ qua, im lặng, đúng lúc nó cần nói nhất.

⭐ So với ca ngược lại (phiên Mobile V1): họ bỏ **đúng** bước phủ phần vừa sửa —
77 phép kiểm không chạy — nên nó **đập vào mặt** và bị bắt ngay. Cái không đập
vào mặt thì sống lâu hơn.

⇒ `frontend chatltt` — bước phủ đúng phần H44 đổi — **PASS 8,2s**. Nên lượt này
đứng vững; cảnh báo trên là cho **phiên sau dùng cây này**, không phải cho H44.

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
| **A** | P05 ảnh/tiếng thành tool | 3,5 | **3,5** ✅ | — |
| | **Làn A** | **17,0** | **17,0** ✅ | — (R2b đã chốt 06/09) |
| **B** | P06 · P07 · P08 | 20,0 | 0 | 20,0 |
| **C** | P09 · P10 · P11 · P12 | 14,0 | 0 | 14,0 |
| | **TOÀN CHƯƠNG TRÌNH** | **51,0** | **17,0** | **34,0** |

### Con số

| | |
|---|---|
| **Toàn chương trình (P00→P12)** | **≈ 33 %** (17,0 / 51,0 ngày công) |
| **Làn A** (phần phát hành được một mình) | **100 % MÃ** — nhưng ⛔ **chưa tới người dùng nào**: hai cờ vẫn TẮT, xem bảng điều kiện |
| Mã sản phẩm đã sửa | 16 tệp · 19 tệp test · 1 migration |
| Phép kiểm mới | **383** (backend 800–819: **374** đếm bằng `--collect-only` · frontend A5: 9) |

### P05 đóng bằng cái gì

Phần 0,5 ngày còn thiếu của P05 là **phép kiểm đầu-cuối cho đường job** — và nó
không phải thủ tục: `test_819` moi ra hai lỗi, một cái làm **vỡ hẳn** lượt
(`RuntimeError: tool 'image.ltt' has no sync executor`). Chi tiết ở §"Bảy phát
hiện" và `05_E2_ANH_TIENG_THANH_TOOL.md` §5.

⛔ Hai thứ của P05 **cố ý** không tính là xong, và cả hai đã ghi rõ chứ không im:

| Hạng mục | Vì sao chưa |
|---|---|
| Đường **ĐẨY** khi job xong | Cần một móc trong `job_runner` — `platform_core`, **ngoài ranh giới app**. Đường KÉO hiện tại không mất dữ liệu; `test_819` ghim giới hạn ấy bằng một phép kiểm |
| Kiểm trên **URL công khai** | Cần deploy — một trong ba ranh giới phải có người |

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
| **Mối nối đường job** — `dong_bo` → `_danh_thuc_run` → vòng model sau | test_819 (22) | P05 ✅ |
| Đường **ĐẨY** khi job xong (móc `job_runner`) | test_819 (ghim giới hạn KÉO) | P05 ⏸ ngoài ranh giới app |
| UI duyệt ở frontend | — | P09 |

### Bảy phát hiện mà kế hoạch không có

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

**6. Vòng model SAU MỘT JOB được mở bằng `image.ltt`.** `su_kien.mo_execution()`
**ghi đè** `message.execution_id` mỗi lần nó mở một hàng mới — và `tao_media.tao`
cũng gọi nó, với `tool_name="image.ltt", mode="job"`. `tiep_sau_duyet` lại đọc
đúng trường ấy để biết mở luồng bằng năng lực nào, còn `luot.dong_su_kien`
truyền `ex.tool_name` **thẳng** vào `L.mo_luong()`.

⛔ Nên đây không phải một cái nhãn sai: lượt vỡ ngay ở `for_tool()` với
`RuntimeError: tool 'image.ltt' has no sync executor` — hỏi cỗ máy vẽ ảnh một
câu hỏi chữ. Sửa: lấy **execution đầu của run** (`_execution_dau`, thứ
`chay_tiep_nen` đã dùng cho đúng câu hỏi này) thay vì một con trỏ mà đường job
ghi đè.

**7. Model chưa bao giờ biết bức ảnh nó vừa vẽ có id gì.** `ket_qua_job` **đoán**
tên cổng ra: `kq.get("files") or kq.get("outputs") or kq.get("keys")`. Không tên
nào trong ba cái đó tồn tại — `image.ltt` khai `image_keys`, `speech.ltt` khai
`audio_key`. Nên model luôn đọc `{"tao_xong": true, "tep": []}`: một câu **tự
mâu thuẫn**, và là lý do nó không thể tham chiếu ảnh cũ ở lượt sau — đúng thứ
P05 đòi (*"bằng id artifact, không bằng đoán tên tệp"*).

⭐ Bản sửa không thêm một bảng tra thứ hai: `khoi_artifact()` (thứ dựng khối cho
**người dùng** xem) được công khai và dùng chung. Hai nguồn cho câu hỏi *"job này
đẻ ra những gì"* là hai nguồn sẽ lệch — và chỗ chúng lệch là chỗ người dùng thấy
một bức ảnh trong khi model nói nó không tạo được gì.

🔑 Cả hai đều **chỉ sống ở mối nối**: `test_815`/`test_816` kiểm khúc nộp job
nhưng **thay `tao_media.tao` bằng hàm giả**, nên hàng `chatltt_execution` của job
chưa từng tồn tại trong một phép kiểm nào — và nó chính là thứ ghi đè con trỏ.
Cùng hình dạng với lỗi `LOAI_KHOI` mà trình duyệt bắt được.

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

🟢 **CHỐT 06/09: C3 là MẶC ĐỊNH** (chủ dự án duyệt). Đường lùi về C1:
`LTT_TINH_TIEN_SAN_MOI_LUOT=1` — giữ lại vì đây là **tiền**, người trực phải
tắt được trong một phút chứ không chờ một lượt phát hành.

⚠️ **Chưa chạm khách thật:** chốt này đổi mặc định **trong mã**; bật cho người
dùng thật cần một lượt **deploy**.

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
