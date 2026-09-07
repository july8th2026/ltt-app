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
| Pha hiện tại | Làn A ✅ · **P06 ✅** · B1–B3 ✅ · **B4 ✅ 6/6** · **B5 ✅ 6/6** · **P09 5/6** → còn **B6 · P10–P12** |
| Deploy | ✅ **07/09 02:21** — commit `5434a4b8baee` trên production. 543 tệp `.py` đối chiếu băm: 0 lệch/0 thiếu · `alembic f2c48b71e903` · 5/5 dịch vụ Running · không gián đoạn |

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

## B5 — dự án (đóng 06/09)

Kế hoạch + §0: `12_KE_HOACH_B5_DU_AN.md`. **44 phép kiểm** (`test_836` 19 ·
`test_837` 13 · `BangDuAn.test.tsx` 12).

⭐ **B5 là LẮP, không phải XÂY.** `platform_core/app_projects.py` đã có đủ vòng
đời và ba app đang dùng; ChatLTT chỉ thêm một cột `project_id` **nullable** và
một tệp service mỏng. Và `ix_app_projects_owner_app_updated` **chính là** chỉ số
mà `lastConversationAt` phi chuẩn hoá của LibreChat sinh ra để phục vụ — nên ta
mượn phép sắp xếp mà **không** mượn bộ đếm.

🔴 Ba ràng buộc đã trả giá:

1. **Xoá dự án KHÔNG xoá hội thoại.** `project_id` về `NULL`, hội thoại ở lại.
   Người dùng nghĩ mình đang dọn một cái *nhãn*; nếu thao tác ấy đốt luôn nội
   dung thì không lấy lại được, và họ chỉ phát hiện **sau khi đã bấm**. Đó cũng
   là lý do không có khoá ngoại `ON DELETE CASCADE`.
2. **Dự án KHÔNG có trường chỉ dẫn riêng** — `chatltt_ghi_nho.pham_vi = "du_an"`
   đã có từ B4. Hai cơ chế cùng tiêm chữ vào system prompt là hai cơ chế sẽ lệch
   nhau, rồi người dùng sửa nhầm chỗ. (LibreChat cũng không có trường ấy.)
3. **Hover không phải một cử chỉ ai cũng có.** Cảnh báo *"N cuộc trò chuyện sẽ ở
   lại"* ban đầu gắn vào `onMouseEnter` — 12 phép kiểm jsdom xanh sạch, và trình
   duyệt thật cho thấy người dùng cảm ứng không bao giờ thấy nó. Đổi sang **hai
   nhịp bấm**.

---

---

## Deploy 07/09 — H44 đã lên production

```
commit        5434a4b8baee   (= dung commit gate PASS, khong phai mot cay khac)
asset_ver     bb5a645f -> ae960b57
alembic       f2c48b71e903   (chatltt_ghi_nho + project_id da co)
bam .py       543 tep / 6 goi -> 0 lech, 0 thieu
/health/ready 200 tren URL cong khai
```

⭐ **Cloudflare phục vụ đúng bundle mới**, không dính bẫy `CLAUDE.md` 5b: tải
`main-r0NDDjvS.js` qua `https://app.lttstudios.com` cho `cf: HIT`, và **sha256
khớp tệp trên đĩa máy chủ**. Bundle chứa đủ `ltc-tool`, `ltc-duan`,
*"Không chạy được"*.

### 🔴 Đi tới đây mất BỐN vòng, và lý do đáng ghi

Deploy đi qua `merge --ff-only` từ cây chính, nên nhánh phải **chứa** trunk. Một
vòng là *merge → gate đầy đủ (~12 phút) → ff → deploy*, và phiên
`admin-mvp-v3` vẫn commit bình thường trong lúc gate chạy:

| vòng | gate PASS trên | quay ra trunk đã ở |
|---|---|---|
| 1 | `ca31a534` | `b0f47939` (+8) |
| 2 | `67810150` | `a2a6a018` (+1) |
| 3 | `8110ca76` | `0260ac07` (+1) |
| 4 | `5434a4b8` | **đứng yên** ⇒ ff được |

⛔ Không có đường tắt, và **không nên có**: rào `--ff-only` tồn tại để trunk chứa
**đúng cây đã qua cổng**. Merge nhánh vào trunk sẽ tạo một cây chưa ai gate — mất
đúng thứ đã bắt được `ruff`, `mypy`, ký tự điều khiển và một lượt `bo test` đỏ
trong cùng buổi.

⇒ Bài học vận hành: **khi hai phiên cùng đẩy lên một trunk, phía muốn deploy cần
  trunk đứng yên một lần bằng đúng thời lượng gate.** Đó là phối hợp, không phải
  kỹ thuật — và tôi đã nhắn phiên kia xin giữ tay.

### P09 bước 6 — ĐÃ XONG 07/09, và nó tìm ra một lỗi

Đăng nhập thật bằng trình duyệt, mở một hội thoại gieo sẵn đủ **năm** dạng khối
`tool_call`. Đo trên DOM, không đọc ảnh chụp:

| khối | nhãn khả truy cập | thân |
|---|---|---|
| `cho_duyet` | `Tính toán — Đang chờ bạn duyệt` | mở, `Phép tính 8123*4471` |
| `dang_chay` | `Vẽ ảnh — Đang chạy` | — |
| `xong` | `Tìm trong tài liệu của bạn — Xong` | gấp lại |
| `loi` | `Tính toán — Không chạy được` | mở, câu lỗi màu đỏ |
| khối CŨ (không `trang_thai`) | `Xem ngày giờ — Xong` | gấp lại |

⭐ `aria-label` rời rạc đúng như P09 bước 4 đã sửa: `Tính toán — Đang chờ bạn
duyệt`, không phải chuỗi dính `Tính toánĐang chờ bạn duyệt`.

### 🔴 Lỗi tìm ra bằng MẮT: một phiếu duyệt VẼ RA RỖNG

Khối `dang_chay` của `image.ltt` ở bảng trên có thân **trống**, và DOM nói vì
sao:

```html
<div class="ltc-tool" data-trang-thai="dang_chay">
  <button aria-label="Vẽ ảnh — Đang chạy" disabled>…</button>
</div>
```

`prompt` không có trong `NHAN_DOI_SO`, mà khoá không nhãn thì **ẩn**. Bình
thường đó là lựa chọn đúng — nhưng `image.ltt` và `speech.ltt` là **hai tool
duy nhất tiêu tiền của khách**, thuộc lớp `PAID`, nên đường đi bình thường của
chúng là mở một **phiếu duyệt**. Nghĩa là người dùng được hỏi *"duyệt không?"*
trên một cái khung không nói mình sắp duyệt cái gì.

⛔ `test_835` cố ý không đòi nhãn cho tool ngoài, lý lẽ: *"hợp đồng nằm ở app
   khác và có thể đổi mà không ai ở đây biết"*. Lý lẽ ấy đúng về **quyền sở
   hữu** và sai về **kết quả**.

⭐ Và `tables.py` đã tự hứa điều ngược lại từ trước: chú thích của
  `ChatlttApproval.doi_so` là *"đối số người dùng **nhìn thấy** khi bấm"*.

**Sửa, hai tầng:**

1. `NHAN_DOI_SO` thêm nhãn cho đối số của hai tool trả tiền: `prompt`
   (*Mô tả*), `count`, `negative_prompt`, `text` (*Văn bản*), `voice_id`,
   `preset`. Núm kỹ thuật (`mode`, `model`, `image_key`) vẫn ẩn.
2. `KhoiTool` **fail-closed**: `cho_duyet` mà không hiện được đối số nào thì in
   *"Không hiển thị được chi tiết của yêu cầu này — đừng duyệt."* Cả ứng dụng
   này fail-closed (`lop_chinh_sach` trả `DESTRUCTIVE` khi không khai); một
   phiếu duyệt trắng là fail-**open** ở giao diện — nó trông vô hại, nên người
   ta bấm.

**Bánh cóc `test_840`** chốt: mọi tool trong `CHO_MODEL_GOI` phải có nhãn cho ít
nhất một đối số **bắt buộc**. Mệnh đề hẹp đúng chỗ — nó bất biến với việc app kia
thêm núm mới, nhưng đỏ ngay nếu họ đổi tên `prompt`. Đối chứng đã đo: tiêm bản
cũ ⇒ **2 đỏ** (Python) và **3 đỏ** (frontend).

Đo lại sau khi sửa, trên trình duyệt thật:

```
Vẽ ảnh — Đang chờ bạn duyệt      | Mô tả: mot con meo…  · Số ảnh: 2
Đọc thành tiếng — Đang chờ…      | Văn bản: Xin chao…   · Giọng: vn_nu_1
Vẽ ảnh — Đang chờ bạn duyệt      | "…— đừng duyệt."   (ca khoá không nhãn)
```

0 lỗi console · mọi request 200 · bundle `main-Cz21CDvu.js`.

### ⚠️ Còn thiếu, và KHÔNG sửa ở đây: GIÁ

`ChatlttApproval` mang `bao_gia_credit` — *"số credit **đã hiện ra**"* — nhưng
khối `tool_call` không mang trường ấy, nên màn hình không nói giá. Không vá vội
ở P09: giao diện **duyệt** (nút bấm) chưa tồn tại ở frontend, nên đây không phải
một hồi quy mà là một hạng mục của việc dựng giao diện duyệt. Ghi ra để nó không
rơi.

### ~~Còn lại của P09 bước 6~~ — ✅ ĐÃ XONG 07/09

> *Giữ nguyên chữ gốc bên dưới làm bản ghi. Nó đã hết đúng — xem mục
> **P09 bước 6** ở trên.*

~~Đã chứng minh: mã trên máy, bundle đúng, Cloudflare không phục vụ bản cũ.
**Chưa chứng minh:** khối `tool_call` vẽ ra trông thế nào trong một phiên **đã
đăng nhập** trên URL công khai.~~

✅ **Đã đăng nhập được**, và chặn không phải cái tôi tưởng: cookie phiên mang cờ
`Secure` (production đặt `https_only`), nên `http.cookiejar` **từ chối gửi** nó
qua `http://` loopback ⇒ session rỗng ⇒ CSRF trượt ⇒ 400 *"phiên đã hết hạn"*.
Không liên quan gì tới mật khẩu của chủ dự án. Xem
[[cookie-secure-chan-loopback-http]].

⭐ Và lần nhìn bằng mắt ấy tìm ra một lỗi thật: khối `cho_duyet` của tool **trả
  tiền** vẽ ra **rỗng hoàn toàn**. Xem mục P09 bước 6.

## B6 — vòng nghiên cứu: 6/6 XONG 07/09

| # | Việc | Trạng thái |
|---|---|---|
| 1 | `services/nguon.py` | ✅ |
| 2 | `services/nghien_cuu.py` | ✅ |
| 3 | `gia_nghien_cuu.py` + job `chatltt.nghien_cuu` | ✅ |
| 4 | route + cờ `LTT_CHATLTT_V3_RESEARCH` | ✅ |
| 5 | giao diện: báo giá → chạy → báo cáo có trích dẫn | ✅ |
| 6 | nói rõ PHẠM VI ở giao diện | ✅ |

Dải test dùng: **838, 839, 841, 842** *(kế hoạch ghi 838–840; **840** đã bị P09
bước 6 lấy trong cùng buổi — xem mục P09 ở trên. Bảng cấp phát 800–899 của
CHATLTT còn rộng, nên dịch một số rẻ hơn đổi tên một tệp đã commit.)*

### 🔴 D3 của kế hoạch phải SỬA, không phải thi hành

*"Quyết toán theo số lượt thật sự chạy"* — làm đúng chữ ấy ở tầng job là **thu
hai lần**. Đo được: `runtime_noi_bo/luong.py` giữ credit theo trần token cho
**mỗi** lời gọi model rồi hoàn về token thật (`billing.updated`). Vòng nghiên
cứu không tốn gì ngoài những lượt ấy — nó đọc `chatltt_doan` của chính người
hỏi rồi ghép chữ.

⇒ `credit_cost = 0`, và số 0 ấy là một **khẳng định** có bánh cóc giữ hai đầu
  (`test_841`): giá lúc nộp là 0, **và** kết quả job không mang khoá
  `credit_cost`. Một số dương ở bất kỳ đầu nào là tầng thu thứ hai.

⭐ Nửa đầu của D3 giữ nguyên và **quan trọng hơn trước**: vì job không giữ chỗ,
  cửa số dư chuyển thành **điều kiện trước khi nộp** ở route. Một điều kiện,
  không phải một giá.

Bản sửa đã ghi vào chính `13_KE_HOACH_B6_NGHIEN_CUU.md`, theo giao thức đổi
quyết định.

### Phạm vi — bốn chốt, không phải một dòng chữ

§1: nền tảng này **không có khả năng tìm web**. Câu phạm vi vì thế là hợp đồng
với khách, và nó bị chốt ở bốn chỗ:

1. **Đến từ máy chủ**, không phải hằng số trong bundle — một bản sao sẽ trôi về
   phía **nguy hiểm**: bundle cũ nói *"không tìm Internet"* trong khi máy chủ đã
   mở `web.tim`.
2. **Ra ở cả ba đường** (báo giá · nộp · xem). Chỉ hiện ở màn báo giá là một câu
   khách đọc một lần rồi không thấy lại — trong khi báo cáo cuối mới là chỗ họ
   dễ tin nhầm nhất.
3. **Đứng trước ô nhập** trên màn hình. Một cảnh báo đọc *sau* khi đã tin là một
   cảnh báo không còn tác dụng.
4. **Dịch theo request** (`N_` + `_t()`), không `_()` lúc import. `_()` đóng
   băng ngôn ngữ của tiến trình vào câu này, và đây đúng là câu không được phép
   không đọc được.

### Kiểm bằng MẮT trên trình duyệt thật (cổng 8198, CSDL vứt đi)

Job chạy qua **đúng** `jobs.handle` → `nghien_cuu.chay` → `kiem_trich_dan`; chỉ
`goi_model` bị tiêm, vì cây thử nghiệm không có worker và không có model.

```
pham vi (khung vien)  Doc tai lieu ban da dinh vao hoi thoai nay. Khong tim tren Internet.
gia                   Uoc khoang 13 credit cho toi da 3 vong. So du: 100 credit.
bao cao               "Dung o gioi han so vong … · 3 vong · da bo 1 cau khong chi duoc nguon"
                      1. Thoi han thanh toan la 30 ngay …   tep_78b2 · trang 2
                      2. Cham thanh toan bi phat 0,05% …    tep_78b2 · trang 3
console               0 loi
/en/…/bao-gia         "Reads the documents you attached … Does not search the Internet."
```

⭐ Trạng thái *"0 credit"* cũng đã nhìn thấy trước khi nạp: nút **vô hiệu** và
  màn hình nói *"Chưa đủ để chạy."* — chứ không phải một nút bấm được rồi mới
  báo 402.

### ⚠️ Bốn cổng vẫn ĐÓNG

`customer_visible=False`, `api_exposed=False`, không trong
`chinh_sach.CONG_CU_CHO_PHEP`, không trong `chieu_tool.CHO_MODEL_GOI`. Model
**không** tự gọi được vòng nghiên cứu; nó là một nút người dùng bấm.

---

## P09 — nghiệm thu pha, đo 07/09

Tiêu chí `00_KE_HOACH_V3.md`: *"ma trận **390 / 768 / 1280 / 1440 / 1920** px
trên trình duyệt thật + URL công khai · 0 lỗi console · axe không có vi phạm
nghiêm trọng · bàn phím/focus/`prefers-reduced-motion` đúng · **CLS không tệ
hơn 0,079**"*.

| Tiêu chí | Kết quả |
|---|---|
| Ma trận 5 mốc | ✅ 0 tràn ngang ở cả năm — **và tìm ra một lỗi thật ở 390 px** |
| 0 lỗi console | ✅ |
| axe (nghiêm trọng) | ✅ 0 vi phạm · **9 rule** chạy trên `KhoiTool`, **13** trên `TheDuyet` |
| Tương phản màu | ✅ thấp nhất **4,79** (thẻ duyệt) và **5,25** (khối tool), chuẩn AA là 4,5 |
| Bàn phím / focus | ✅ `focus-visible` ra viền `2px solid` kèm offset, Tab tới đủ ba nút |
| `prefers-reduced-motion` | ✅ 3 quy tắc |
| **CLS** | ✅ **0,0003** trên Chrome thật (mốc 0,079 — dư biên **263 lần**), ba lượt giống hệt |
| Ma trận trên **URL công khai** | ⛔ **chưa đo được, và lý do không phải cái tôi tưởng** — xem dưới |

### 🔴 Lỗi thật mà ma trận tìm ra, ở 390 px

`.ltc-dinh` là `flex-wrap: nowrap`. Bốn phần tử (65+77+56+100 = 298 px + 3 gap)
bị ép trong 366 px khả dụng:

```
chip "Model chua san sang"   56 px RONG  x  72 px CAO   <- chu gay BON dong
o chon du an                 co lai con "— k"
```

Sau khi đổi sang `flex-wrap: wrap` + `flex: 0 0 auto` cho chip:

```
chip  134 x 24     o chon du an hien du "— khong thuoc du an nao —"
```

⛔ Không sửa bằng `overflow-x: auto`: một thanh cuộn ngang ở hàng đỉnh là một
   hàng đỉnh người dùng không thấy hết, và trên điện thoại họ không biết là còn
   thứ để cuộn tới.

### CLS — và vì sao lượt đo ĐẦU TIÊN phải bị vứt

Lượt đầu (khung trình duyệt nhúng) ra `CLS = 0` với **0 dịch chuyển ghi được**.
Đó là đúng cái số 0 không có đối chứng. Ba lần ép dịch chuyển có chủ đích:

```
chen div 200px vao dau <body>          -> 0 muc
chen div 260px vao dau .page           -> 0 muc
doi chieu cao mot .ltc-tool DANG HIEN  -> 0 muc
```

`supportedEntryTypes` **có** `layout-shift`, nhưng khung nhúng không phát mục
nào kể cả khi bị ép. ⇒ Số 0 ấy **vô nghĩa**, và tôi không báo nó là "đạt".

⭐ Nếu tôi dừng ở đó, tôi đã báo *"CLS = 0, đạt"* — một câu sai, và sai về phía
  **an toàn giả**.

### ✅ Đo lại trên Chrome THẬT (Playwright, chủ dự án cấp quyền 07/09)

**Đối chứng TRƯỚC:** ép một dịch chuyển ⇒ `CLS 0,2043` qua **2 mục**. Bộ đo
chạy thật; khung nhúng mới là thứ hỏng. Không có dòng này thì mọi số dưới đây
lại là một số 0 không đối chứng nữa.

**Rồi đo sạch, ba lượt tải lại:**

```
luot 1   CLS 0,0003   1 dich chuyen   nguon: .ltc-chip--tat
luot 2   CLS 0,0003   1 dich chuyen   nguon: .ltc-chip--tat
luot 3   CLS 0,0003   1 dich chuyen   nguon: .ltc-chip--tat
```

Mốc là **0,079** ⇒ dư biên **263 lần**. Dịch chuyển duy nhất là chip *"Model
chưa sẵn sàng"* xuất hiện khi `/api/danh-muc` trả về — một nhịp, rất nhỏ.

Ma trận 5 mốc cũng chạy lại trên Chrome thật: **0 tràn ngang, 0 phần tử vượt
phải, chip 24 px ở cả năm** (390 / 768 / 1280 / 1440 / 1920).

### ⛔ Vế "URL CÔNG KHAI" — chưa đo được, và lý do KHÔNG phải Cloudflare

Tôi suýt ghi vào đây rằng *"Cloudflare chặn bot nên không đo được"*. Đó là một
**triệu chứng tôi gặp**, không phải **nguyên nhân**. Đo tiếp thì ra nguyên nhân
thật:

```
grep "ltc-duyet" C:/LTTPlatform/app/server/static/chatltt/assets/main-DkFV4b4_.js   -> 0
grep "ltc-duyet" C:/LTTPlatform/app/server/static/chatltt/assets/main-DHF47eDa.css  -> 0
git branch -a --contains HEAD   -> chi `claude/chatltt-v3-agentic`, chua hop nhat
production /health/version      -> commit 252f24fa6e2f
```

⇒ **Giao diện V3 chưa có trên production.** Không có gì để đo ở URL công khai.
  Vế này không "trượt" — nó **chưa tới lượt**, và nó tới ở **P12 (phát hành)**.

⭐ Bài học: một lời giải thích **khớp vừa vặn** (`kiem-gui-noi-vao-chrome-that`
  đúng là có nói Cloudflare chặn Chrome do Playwright mở) thì kết thúc điều tra
  sớm. Nó khớp, nó có sẵn trong trí nhớ, và nó **sai**. Bẫy
  `gia-thuyet-khop-qua-vua-ket-thuc-dieu-tra`.

### Hai sự thật RỜI NHAU, đừng gộp

**1. Cloudflare CÓ chặn.** `https://app.lttstudios.com/login` trả *"Just a
moment…"*. Tôi **không giải CAPTCHA**. Đây là việc thật phải xử ở P12 — nối vào
Chrome của chủ dự án cần bật `chrome://inspect/#remote-debugging` bằng tay.

**2. Nhưng Cloudflare KHÔNG làm hỏng byte.** Đo 07/09 trên static đang phục vụ
thật:

```
GET https://app.lttstudios.com/static/ltt.css
  HTTP 200 · 290.440 byte · cf-cache-status: HIT
  sha256 165ed3b1904fd5b4f1228200745625e7db154f9dcbf9e2954290f8b51e2208db

C:/LTTPlatform/app/server/static/ltt.css
  290.440 byte
  sha256 165ed3b1904fd5b4f1228200745625e7db154f9dcbf9e2954290f8b51e2208db
```

**Khớp tuyệt đối** — CF không minify, không đổi một byte nào của tệp này.

⚠️ Nhưng đây là **`ltt.css`, không phải bundle V3**. Nó chỉ chứng minh *cơ chế*
   phục vụ nguyên byte; nó **không** chứng minh bố cục V3 đúng trên URL công
   khai. Đó là một phép đo **thứ hai**, và nó phải chạy sau P12.

⛔ Vì đúng cái bẫy `CLAUDE.md` mục **5b** ghi lại đã xảy ra thật: sau khi sửa
   `ltt.css`, CF phục vụ bản **cũ** (TTL 4h) → chip hiện thành radio thô dù
   origin đã đúng. `Cache-Control: max-age=14400` ở trên chính là 4 giờ ấy. Vấn
   đề khi đó là **bản nào**, không phải **byte có nguyên không** — nên phép đo
   byte ở trên **không** trả lời được nó.

### axe chạy ở vitest, không tiêm vào trang — và vì sao

CSP của nền tảng là `script-src 'self' 'unsafe-inline' <hai host Cloudflare>`.
`cdnjs` không nằm trong đó nên tiêm `axe.min.js` bị chặn — **và đó là đúng**.
Nới CSP để đo một lần a11y là đổi một biện phòng thủ thật lấy một phép đo.

`axe-core` 4.13.0 — **0 dependency**, MPL-2.0, chỉ chạy lúc test. Đúng ngưỡng
§0 mức thấp mà chính kế hoạch đặt cho test-time tooling.

⚠️ `jsdom` không vẽ nên `color-contrast` **không chạy được** ở đó — axe tự xếp
   nó vào `incomplete`, không phải `pass`. Tương phản vì thế được đo **riêng**
   trên trình duyệt thật, và số ở bảng trên là từ lượt đo ấy.

---

## P10 — tra tấn: ba lỗ thật, cả ba ở chỗ KHÔNG ai đang chạy

Kế hoạch P10 liệt kê *"đua credit · POST/duyệt trùng · **huỷ ở từng biên trạng
thái**"*. Đo 07/09 tìm ra **ba** lỗ, và chúng cùng một hình dạng: mọi đường
phòng thủ đều canh lúc có **một luồng đang chạy**, còn lúc lượt **đứng chờ** thì
không ai canh.

| # | Lỗ | Hậu quả | Phép kiểm |
|---|---|---|---|
| **1** | Bấm Dừng lúc lượt đang **chờ** là no-op im lặng | duyệt xong lượt **vẫn chạy tiếp**, tiêu thêm tiền sau khi người dùng bảo dừng | `test_849` |
| **2** | Hai nguồn cùng chạy tiếp **một** run | **hai lượt model cho một lần duyệt** ⇒ tiền đi hai lần, hội thoại hai nhánh | `test_817` |
| **3** | Huỷ rồi mà **thẻ duyệt vẫn hiện** | người dùng bấm "Duyệt", **không có gì xảy ra**, không lời giải thích | `test_849` |

### Lỗ 1 — nút Dừng trượt cả hai việc của nó

```
ex.status in ("streaming", "queued")  ->  vong da xong, KHONG lat
dang_chay.yeu_cau_dung(ex.id)         ->  luong da thoat, KHONG tim thay
```

Luồng nền gọi `dang_chay.ket_thuc()` ở `finally`, nên sổ `_SO` không còn khoá.
Và lần chạy tiếp gọi `dang_chay.bat_dau()` — hàm này **ghi đè** một
`LuotDangChay` mới, tức một `Event` **mới, đã xoá**. Cờ đặt trước đó biến mất
cùng đối tượng cũ.

⭐ Bản vá không thêm cột nào: `dieu_phoi.CHUYEN_HOP_LE` **đã khai**
  `AWAITING_APPROVAL -> CANCELLED` và `WAITING_BACKGROUND -> CANCELLED`. Chỗ ghi
  nhận có sẵn, chỉ là không ai ghi vào. Dùng đúng ô ấy thì `nen_chay_tiep` tự
  đúng theo, vì `CANCELLED` không thuộc `CHO_DUOC`.

⛔ Và bản vá **chỉ** chạm biên chờ. `TOOL_RUNNING -> CANCELLED` cũng hợp lệ,
   nhưng ở đó có một luồng đang sống với đường dừng riêng; lật trạng thái từ
   ngoài vào là ghi đè lên thứ luồng ấy sắp ghi. `test_849` chốt cả hai chiều.

### Lỗ 2 — đọc-rồi-ghi, đúng cái bẫy cổng duyệt đã học

Có **hai** nguồn gọi chạy tiếp, không phải một:

```
routes/_p_duyet.py     nguoi bam Duyet
services/tao_media.py  _danh_thuc_run() khi job xong (dong_bo goi)
```

Cả hai theo cùng khuôn: hỏi `nen_chay_tiep()` **rồi mới** `chay_tiep_nen()`.

⭐ Và `duyet._quyet` đã học đúng bài này rồi, ghi ngay trong mã của nó: *"Điều
  kiện nằm TRONG `WHERE`. Đọc-rồi-ghi có một khe giữa hai câu lệnh, và hai yêu
  cầu song song lọt vừa vào khe ấy."* Cổng duyệt có người canh; đường chạy tiếp
  thì chưa — **cùng một kho, cùng một tuần**.

⚠️ Bản vá **không** lật một cột trạng thái để giữ chỗ, dù cách ấy ngắn hơn: một
   sự cố giữa chừng sẽ để run **kẹt vĩnh viễn** ngoài `CHO_DUOC`, trong khi
   trước bản vá cùng sự cố ấy chỉ làm lượt đứng lại và **thử lại được**.

⇒ Chữa một cuộc đua mà tạo ra một cách kẹt mới là đổi một lỗi hiếm lấy một lỗi
  hiếm khác, không phải một bản sửa. Dùng `platform_core.leases`: UNIQUE quyết
  người thắng, `heartbeat_at` khiến tiến trình chết thì chỗ **tự nhả**. Đập nhịp
  đi nhờ callback `ghi=` có sẵn của `DP.tiep_tuc`, nên TTL 10 phút chỉ là trần
  cho ca tiến trình chết, không phải trần cho một lượt chậm.

### Lỗ 3 — trạng thái đúng mà giao diện sai vẫn là sản phẩm hỏng

Bản vá lỗ 1 làm `ChatlttRun.trang_thai` thành `CANCELLED` — đúng. Nhưng
`ChatlttApproval.quyet_dinh` vẫn là `CHO`, và `dang_cho()` chỉ lọc theo
`quyet_dinh` + hạn, **không** biết run đã huỷ.

⇒ Thẻ duyệt vẫn hiện. Người dùng bấm "Duyệt", `_quyet` chạy trót lọt, rồi
  `nen_chay_tiep` trả `False` và **không có gì xảy ra** — không kết quả, không
  lời giải thích. Một cái nút không làm gì mà cũng không nói gì.

⭐ Vá ở phía **ĐỌC**, không phía ghi — theo đúng lý lẽ đã viết trong bản vá lỗ 1:
  nếu đi cập nhật từng hàng phiếu mỗi lần huỷ, thì **mọi** đường huỷ tương lai
  phải nhớ làm thêm bước ấy, và sẽ có đường quên.

⚠️ `outerjoin` chứ không `join`: một phiếu mà `run_id` không trỏ tới hàng nào vẫn
   phải hiện. `join` trong sẽ **im lặng nuốt** nó, biến một dữ liệu hỏng thành
   một phiếu vô hình thay vì một phiếu đáng ngờ.

⛔ Và **chỉ** lọc `CANCELLED`. `FAILED` cũng có vẻ đáng lọc, nhưng đường ấy chưa
   được đo — nới một bộ lọc theo suy đoán là cách một bộ lọc bắt đầu giấu thứ nó
   không nên giấu. Ghi lại cho P11 ở `15_BAN_GIAO_P11_RED_TEAM.md` §2.4.

### 🔴 Cả ba phép kiểm đều đã được TIÊM BẢN CŨ để xem có đỏ không

Màu xanh không phải bằng chứng; đối chứng mới là.

```
Lo 1:  ban cu chay trong cung bo phep kiem  ->  4/10 DO
Lo 2:  go lease ra, chay lai                ->  returncode 1 (DO)
       roi tra lai nguyen trang, sha256 khop
```

⭐ Lỗ 2 còn có một đối chứng **ngược**:
  `test_nha_cho_xong_thi_nguoi_sau_van_vao_duoc`. Một bản vá chặn người thứ hai
  bằng cách chặn **luôn mọi người** cũng làm phép kiểm chính xanh — phép kiểm
  ngược là thứ phân biệt *giữ chỗ* với *khoá chết*.

⚠️ Và `test_849` suýt xanh rỗng: `nen_chay_tiep` trả `False` vì **bốn** lý do
   khác nhau. Nên mỗi ca huỷ có một ca **không huỷ** chạy trên cùng dữ liệu và
   phải ra `True` — không có nó thì màu xanh không nói lên gì (Bẫy 31 hình
   thái 3).

### Còn nợ của P10

| Món | Trạng thái |
|---|---|
| Đua credit · POST/duyệt trùng | ✅ CAS ở `_quyet` + lease ở chạy tiếp; `test_627` phủ đường V2 |
| Huỷ ở từng biên trạng thái | ✅ `test_849`, 10 phép kiểm, 4 biên |
| **Hồi quy TTFT** | 🟡 **hai trong ba thành phần đã đo**, phần prefill treo sang P12 |

### Hồi quy TTFT — đo cái GÂY RA nó, thay vì bấm giờ

Tiêu chí viết *"TTFT lượt không-tool không xấu hơn baseline quá 10 %"*. Nghe như
một phép bấm giờ, nhưng bấm giờ ở đây trả lời sai câu hỏi:

- **Không có baseline nào được ghi.** Nó phải được dựng trước, và chỉ có nghĩa
  khi đo cùng máy, cùng model, **xen kẽ** để triệt trôi.
- **Phương sai của model nuốt tín hiệu.** Lượt thật dao động hàng trăm ms; phụ
  phí V3 là vài ms cộng phần prefill dài thêm.
- **Máy dùng chung.** Một cây khác chạy nặng đẩy số về phía *"chậm"* ⇒ báo động
  giả. Sai số **có chiều** thì không hiệu chỉnh được
  (`phep-do-lech-chieu-phai-bo-khong-phai-sua`).

⭐ Nên tách TTFT thành ba thành phần và đo **tất định** hai cái đầu —
`tools/do_phu_phi_v3.py`, đo 07/09 lúc máy yên:

| Thành phần | Cờ TẮT | Cờ BẬT | Kết luận |
|---|---|---|---|
| Ký tự thêm vào prompt | **0** | **1.213** (3 tool) | cờ tắt ⇒ **không đổi một byte** |
| CPU trước lời gọi (trung vị) | 0,00 ms | **3,33 ms** | không đáng kể |
| Prefill của 1.213 ký tự | — | **chưa đo** | cần model thật + máy yên ⇒ **P12** |

### 🔴 Và phép đo đầu tiên của chính tôi đã nói dối, theo hướng nguy hiểm

Bản đầu của công cụ báo **204 ms**. Xem phân bố mới thấy:

```
tung luot (ms): 986.97  2.73  2.46  3.98  2.72  2.51  2.51  2.58  2.56  2.81  2.77
```

Lượt một là **987 ms** (nạp module), sau đó ổn định **2,7 ms**. Trung bình 204 ms
là một con số **không mô tả lượt nào cả** — và nó lệch về phía *"chậm"*, tức về
phía tôi sẽ báo một hồi quy không có thật.

⛔ Một dãy có mẫu khác biệt **bậc độ lớn** thì trung bình là thống kê **sai**,
   không phải thống kê thô. Công cụ nay báo **trung vị**, và in riêng lượt đầu
   kèm chú thích *"một lần mỗi tiến trình"*.

⭐ Cái bắt được nó không phải trực giác mà là **nhìn phân bố thay vì nhìn tóm
  tắt** — cùng họ với `doc-thu-dai-dien-thay-vi-doc-thu-that`.

⚠️ **Giới hạn phải nói ra:** phép đo chạy trên một SQLite **rỗng** với một
   `user_id` bịa, nên `chieu_tool.chieu()` chỉ dựng **3 tool**. Một tài khoản
   thật bật nhiều tool hơn sẽ ra nhiều ký tự hơn.

⇒ **1.213 là một cái SÀN, không phải trần.** Đo lại trên tài khoản thật ở P12.

---

## 🔒 Điều kiện để BẬT các cờ V3 — món nợ tự đòi

⚠️ **SÁU cờ** (cập nhật 07/09). Kế hoạch tổng ghi *"làn B — mỗi nhóm một cờ"*;
cờ nhóm P06 bị bỏ sót suốt P06 lẫn B1/B2, cờ B4 thì khai ngay từ bước 3:

| Cờ | Gác cái gì | Mặc định |
|---|---|---|
| `LTT_CHATLTT_V3_TOOLS` | vòng lặp tool | TẮT |
| `LTT_CHATLTT_V3_PAID_TOOLS` | model **tự** gọi tool có phí | TẮT |
| `LTT_CHATLTT_V3_FILES` | đính tài liệu (P06/B1) — **tốn credit** | TẮT |
| `LTT_CHATLTT_V3_MEMORY` | kho ghi nhớ (B4) — đổi **ngữ cảnh mọi lượt** | TẮT |
| `LTT_CHATLTT_V3_PROJECTS` | dự án gom hội thoại (B5) | TẮT |
| `LTT_CHATLTT_V3_RESEARCH` | vòng nghiên cứu (B6) — **N lượt model chạy nền** | TẮT |

⛔ **SÁU** cờ, tất cả **độc lập**. Bật cờ tool không kéo theo cờ tệp: đính một tài liệu
tốn tiền ngay cả khi vòng lặp tool tắt.

⭐ Và `_RESEARCH` **không** ăn theo `_FILES` dù đọc cùng kho `chatltt_doan`. Đính
  một tài liệu là một việc khách làm **một lần** và thấy kết quả ngay; một vòng
  nghiên cứu là **N lượt model chạy nền**, và nó tốn tiền theo N chứ không theo
  một. Hai mức rủi ro khác nhau ⇒ hai cái van khác nhau.

🔴 `test_831::test_trang_thai_khai_du_MOI_co` chốt **tập hợp** sáu tên, không
   phải số lượng và không nới thành `>=`. Nó đã đỏ đúng lúc **hai lần** — cờ thứ
   năm (B5) và cờ thứ sáu (B6) — và cả hai lần đều bắt người viết quay lại khai.

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

### Điều kiện riêng để bật `LTT_CHATLTT_V3_RESEARCH`

| # | Điều kiện | Trạng thái |
|---|---|---|
| R1 | `_FILES` đang bật — không có tài liệu thì mọi lượt ra `khong_co_nguon` | ✅ **07/09** |
| R2 | Giao diện nói rõ **phạm vi** (không đọc Internet) | ✅ **07/09** — chốt ở bốn chỗ, xem mục B6 |
| R3 | **Đo lại `CREDIT_UOC_MOI_VONG`** (nay `= 1`) trên 20–50 lượt thật | 🟡 vẫn là một **neo**, không phải phép đo — nhưng nay neo vào `gia_token` bằng mã, không chép tay; xem dưới |

⛔ Thêm `chatltt.nghien_cuu` vào `chieu_tool.CHO_MODEL_GOI` là một bước **riêng**
   và hôm nay **không** làm: vòng nghiên cứu là một nút **người dùng bấm**, không
   phải một năng lực model tự gọi. `test_841` chốt sự vắng mặt ấy.

🔴 **R3 từng ghi `= 3`, và con số ấy sai 13 lần.** Nó được suy ra bằng cách lấy
   `GIA_RA_CREDIT_1M = 400` áp lên **token VÀO** — mà token vào có giá riêng,
   `GIA_VAO_MOI_CREDIT_1M = 50`. Sai một bậc độ lớn.

⛔ Và **25 phép kiểm của `test_841` đều xanh với hằng số sai**, vì chúng chỉ đòi
   `> 0` và đòi tăng đơn điệu — hai mệnh đề mà một hằng số sai 13 lần vẫn thoả.
   Đó là **Bẫy 32** (`docs/BAY_TRONG_CONG_CHAT_LUONG.md`): phép kiểm **yếu hơn**
   thứ nó phải đo.

⭐ Bản vá không phải "sửa số cho đúng" — số chép tay nào rồi cũng trôi. `test_847`
  neo `uoc_tran` vào **chính `gia_token`**, nên đổi bảng giá mà quên đổi ước tính
  thì gate đỏ.

⭐ Không có điều kiện "chốt giá" như `_FILES`, và đó **không** phải bỏ sót: tầng
  job này thu **0**, mọi credit chảy qua `runtime_noi_bo` theo giá đã chốt của
  `text.chat`. Xem `apps/chatltt/gia_nghien_cuu.py`.

### 📌 Món nợ CHÉO: vế "URL công khai" của P09 chỉ trả được SAU P12

Tiêu chí P09 đòi ma trận *"trên trình duyệt thật **+ URL công khai**"*. Vế đầu
đã đo xong trên Chrome thật. Vế sau **chưa đo được**, và không phải vì trượt:

```
grep "ltc-duyet" <bundle chatltt tren production>  -> 0
git branch -a --contains HEAD                      -> chua hop nhat vao dau
```

Giao diện V3 **chưa có trên production**, nên URL công khai không có gì để đo.

⛔ Đây là một **vòng phụ thuộc**, phải nói thẳng ra chứ đừng để nó tự giải:

```
P09 (nghiem thu)  can  URL cong khai
URL cong khai     can  P12 (phat hanh)
P12               can  P11 (red team)
P11               can  P09
```

⇒ Cách cắt vòng: P09 đóng với vế công khai **treo có địa chỉ**, và nó thành một
  hạng mục **bắt buộc trong nghiệm thu P12** — không phải một việc "nhớ thì làm".

| # | Việc | Khi nào |
|---|---|---|
| CK1 | Chạy lại ma trận 5 mốc + CLS trên `https://app.lttstudios.com/chatltt` | ngay sau deploy P12 |
| CK2 | Đối chiếu sha256 bundle CF phục vụ với tệp trên đĩa | cùng lượt |

⚠️ CK2 **không** thừa dù đã đo `ltt.css` khớp tuyệt đối hôm nay. Sự cố `CLAUDE.md`
   mục 5b ghi lại không phải "CF đổi byte" mà "CF phục vụ **bản cũ**" — TTL 4 giờ
   (`Cache-Control: max-age=14400`, đo được ngay hôm nay). Phép đo *byte có nguyên
   không* **không trả lời được** câu *bản nào*. Hai câu khác nhau, hai phép đo.


⛔ **Đọc mục này trước khi bật cờ, kể cả bật để thử.**

| # | Điều kiện | Trạng thái |
|---|---|---|
| 1 | Gate đầy đủ PASS trên cây này | ✅ `20260905T181119Z-12404.json` — 26 bước · 0 FAIL · `cay_da_doi_giua_chung=False` · sha `4a55620f` |
| 2 | **Mở trình duyệt thật, xem bốn nhãn trạng thái V3 hiện đúng** | ✅ **05/09** — xem §dưới |
| 3 | Kiểm trên URL công khai, không chỉ loopback (`CLAUDE.md` 5b) | ✅ **07/09** — `https://app.lttstudios.com/en/chatltt/api/hoi-thoai/cv_x/tep` trả **303** (cổng cờ cho qua → `require_login`); đối chứng route không tồn tại vẫn **404**; `/health/ready` 200 |
| 4 | R2b được chủ dự án chốt | ✅ **06/09 — chốt C3**, đã deploy (`334004d4`), đang thu thật |
| 5 | **Giá trích tài liệu** được chủ dự án chốt | ✅ **CHỐT 07/09/2026 — chủ dự án giữ nguyên `20`** mcredit/1.000 ký tự. Căn cứ: giá vốn đo được **1–2đ**/lượt (PDF thật 1 MB/17 trang = 0,16 s CPU); **sàn làm tròn 1 credit** ăn hết mọi tài liệu dưới 50.000 ký tự, nên hạ xuống `10` không đổi gì cho tài liệu thường. `CHU_DU_AN_DA_CHOT = True`. |

### ✅ 07/09 — `_FILES` và `_TOOLS` ĐÃ BẬT trên production

```
loopback  /en/chatltt/api/hoi-thoai/cv_x/tep   404 -> 303
cong khai https://app.lttstudios.com/...       303
doi chung /en/chatltt/api/khong-ton-tai        404   (phep do phan biet duoc)
/health/ready  ca hai duong                    200   (khong gian doan)
```

⚠️ Nói cho chính xác: **`_FILES` được chứng minh** bằng hành vi route. `_TOOLS`
gác vòng lặp tool chứ không gác route nào, nên nó **không có phép đo HTTP
riêng** — nó vào cùng lượt nạp, nhưng chưa được quan sát trực tiếp.

### 🔴 Vì sao nó "đã bật" nhiều giờ mà vẫn TẮT: NSSM nướng ENV lúc CÀI

Dịch vụ chạy qua NSSM, và NSSM **nướng biến môi trường vào đăng ký dịch vụ lúc
CÀI** (`AppEnvironmentExtra`). `server\run.py` chỉ đọc `os.environ` — nó
**không tự đọc `secrets\app.env` lúc chạy**.

⇒ Sửa `app.env` rồi `Restart-Service` = *"dịch vụ lên lại với ENV CŨ, không lỗi
  nào báo"*. Cờ nằm đúng chỗ, không BOM, kết dòng đúng — và **vô tác dụng**.

⭐ Cách đúng: `setup/nap_lai_env.ps1` (đã có sẵn trong kho). Header của nó ghi
   rằng bẫy này **đã dính hai lần** trước đây — cổng VLM máy B, và
   `LTT_PUBLIC_API_TOOLS` ngày 23/08. Triệu chứng giống hệt cả ba lần: *"cấu
   hình đúng, dịch vụ chạy, tính năng không bật"*.

⛔ **Và một sự cố bảo mật trong lúc chẩn đoán, ghi lại để không lặp:** một lệnh
   `nssm get … AppEnvironmentExtra` đã in **toàn bộ bí mật production** ra bản
   ghi phiên (session secret, khoá mã hoá token, mật khẩu CSDL, Turnstile,
   Resend, Gemini, R2, ModelArk). `secrets/` là vùng cấm, nhưng **cấu hình dịch
   vụ LÀ nơi chứa bí mật** — cùng một thứ, khác một cửa. `nap_lai_env.ps1` cố ý
   không in giá trị nào (*"72 biến (không in giá trị)"*); một lệnh `get` thô thì
   in sạch. ⇒ Đã khuyến nghị xoay khoá.

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

### ~~Còn lại của điều kiện 2~~ — ✅ ĐÃ XONG (P09, 06–07/09)

> *Bản ghi của lượt gate **05/09**. Giữ nguyên chữ; câu cuối đã hết đúng.*

~~Khối `tool_call` hiện **chưa được vẽ gì cả** — người dùng thấy phần chữ và
nhãn trạng thái, không thấy dấu vết lời gọi công cụ. Đó **đúng A5** (bỏ qua khối
chưa có bộ vẽ, không vỡ), nhưng nghĩa là **P09 vẫn phải dựng bộ hiển thị
`tool_call`**.~~

✅ `frontend/chatltt/src/KhoiTool.tsx` đã dựng, và đã **nhìn bằng mắt** trên
trình duyệt thật với đủ **năm** dạng khối (bốn trạng thái + khối CŨ không có
`trang_thai`). Xem mục **P09 bước 6**.

⛔ Để nguyên câu *"P09 vẫn phải dựng"* thì người đọc sau sẽ đi dựng lại một thứ
   đã có. Đó đúng cơ chế `CLAUDE.md` mô tả: *"một bảng chép tay không có cách
   nào tự biết nó đã cũ"* — và ở đây thứ chép tay là **một câu về tương lai**
   nằm trong một bản ghi về quá khứ.

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

### 🔴 07/09: cùng bước ấy bỏ qua vì một lý do THỨ HAI, và bản sửa khác hẳn

Bảng trên ghi lý do là *"thiếu `LTT_TEST_DATABASE_URL`"*. Hôm nay nó bỏ qua vì
một chuyện khác:

```
python -c "pathlib.Path(r'C:\LTTPlatform\secrets').iterdir()"
  -> PermissionError [WinError 5] Access is denied
```

Thư mục ấy siết ACL từ 27/08 (hạng mục **W1.5**, và siết là **cố ý**).
`check_multiproc.py` cần đọc nó, nên nó cần **quyền nâng**.

⛔ Và đây là phần đáng sợ: **một phiên được nối tiếp sẽ MẤT token nâng quyền**,
   trong khi sớm hơn trong cùng phiên nó đọc được. Phiên khác báo sang đã đo
   được đúng thế (`ADMIN=True` lúc 11:12, `PermissionError` sau khi resume);
   phiên này kiểm lại và **cũng dính**.

⇒ Hai nguyên nhân khác nhau cho cùng một dòng `[BOQUA]`, và **hai bản sửa khác
  nhau**: một cái là đặt biến môi trường, cái kia là chạy có UAC. Đọc bảng trên
  rồi đặt biến môi trường sẽ **không** làm bước này chạy.

⭐ Bản sửa cho ca thứ hai: `setup/chay_multiproc_nang_quyen.ps1` (khuôn hai lớp,
  `AGENTS.md` §9.3). Nó **fail-closed** — không có quyền thì ghi `EXITCODE=126`
  kèm lý do chứ không chạy rồi báo xanh. Đo được ở phiên kia: `ADMIN=True`,
  `EXITCODE=0`, **181 giây**, log `"7 passed in 139.51s"` — vượt xa sàn
  `giay_toi_thieu=3.0`, nên là chạy thật chứ không phải một `return 0` lịch sự.

⚠️ Script ấy **chưa có trong nhánh này** (`claude/chatltt-v3-agentic` rẽ trước
   `a365fa80`). Nó sẽ tới khi nhánh này hợp nhất lên trunk, và lúc ấy vẫn cần
   **chủ dự án bấm UAC** — không phiên Claude nào tự làm được.

🔑 Nên với mọi lượt gate của nhánh này cho tới lúc đó: dòng `RESULT: PASS`
   **thiếu một bước**, và phải nói ra kèm nó. Đây đúng lớp lỗi mà
   `docs/BAY_TRONG_CONG_CHAT_LUONG.md` sinh ra để chứa: *một bước không chạy mà
   trông như đã chạy*.

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
