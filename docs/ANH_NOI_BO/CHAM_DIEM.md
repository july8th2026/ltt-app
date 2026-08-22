# CHẤM ĐIỂM — H37, cổng chất lượng từng phase

Luật đầy đủ ở [`KE_HOACH_THI_HANH.md`](KE_HOACH_THI_HANH.md) §1. Bản rút gọn để
dùng hằng ngày:

**Sáu chiều:** C1 phạm vi · C2 bằng chứng · C3 đúng đắn · C4 không phá thứ đang
chạy · C5 vận hành được · C6 tài liệu.

**Qua phase khi CẢ BA cùng đúng:**

```
① trung bình có trọng số ≥ 9,0
② KHÔNG chiều nào < 8        (không cho bù trừ)
③ KHÔNG blocker nào đỏ       (blocker là nhị phân)
```

**Trần điểm cứng:** khẳng định không trích được bằng chứng → chiều đó tối đa **6** ·
số đo chỉ chạy một lần → C3 tối đa **8** · không thử bác bỏ → C3 tối đa **8** · sửa
file tay trên máy B ngoài đường deploy → C5 tối đa **4**.

**Không đạt:** sửa và chấm lại tối đa **2 lần**. Trượt lần thứ ba thì **dừng** và
báo cáo — ba lần trượt cùng một phase nghĩa là kế hoạch sai, không phải làm ẩu.

**Phần BÁC BỎ là bắt buộc.** Phase không có nó thì *chưa được chấm*, không phải
"chấm thấp". Lý do nằm ở một bài học có sẵn trên máy B
(`scripts/live_check_control_b.py`): một phép kiểm từng **báo đạt** trong khi tự in
ra bằng chứng ngược lại — *"a verdict that does not read what it printed"*.

---

## Khuôn chép cho mỗi lần chấm

```
### Phase: G_ — <tên>
Ngày:        2026-__-__            Lần chấm: 1/2/3
Bằng chứng:  <đường dẫn tệp · lệnh đã chạy · số đo>
Điểm:        C1 __ (w__%) · C2 __ · C3 __ · C4 __ · C5 __ · C6 __
             → trung bình có trọng số: __
Blocker:     [ ] <blocker 1>   [ ] <blocker 2>
BÁC BỎ:      kết luận quan trọng nhất của phase này là "___".
             Tôi đã thử bác bỏ bằng cách ___. Kết quả: ___.
Phán quyết:  QUA / KHÔNG QUA — <lý do một câu>
Việc còn nợ: <nếu QUA nhưng còn điểm nhỏ đã biết>
```

---

## G0 — Dựng khung làm việc

### Phase: G0 — Dựng khung làm việc
**Ngày:** 2026-08-21 · **Lần chấm:** 1

**Bằng chứng:**

| Việc | Tệp / lệnh | Kiểm lại bằng |
|---|---|---|
| Q102 vào sổ quyết định nền tảng | `docs/QUYET_DINH_NEN_TANG.md` dòng `\| Q102 \|` | `grep -n "^| Q102" docs/QUYET_DINH_NEN_TANG.md` |
| Tiêu đề mục 1 sửa "đến Q95" → "đến Q102" | cùng tệp, dòng 30 | đọc tiêu đề mục 1 |
| H37 + 13 phase vào kế hoạch triển khai | `docs/KE_HOACH_TRIEN_KHAI.md` cuối tệp | `tail -40` |
| Sổ quyết định kỹ thuật, 7 mục D-001…D-007 | `docs/ANH_NOI_BO/DECISIONS.md` | đọc tệp |
| Sổ chấm điểm + khuôn 6 phần | `docs/ANH_NOI_BO/CHAM_DIEM.md` | chính tệp này |
| Thư mục bằng chứng đo | `bench/README.md` | `ls bench/` |
| `.gitignore` cho ảnh và trọng số trong `bench/` | `.gitignore` | `grep -n "bench/" .gitignore` |
| Một dòng H37 trong bảng "Việc còn dở" | `CLAUDE.md` | `grep -n "H37" CLAUDE.md` |
| Gate nhanh xanh sau khi sửa tài liệu | `python tools\gate.py --quick` | **PASS 12/12** (lần đầu FAIL 1/12) |
| Gate đầy đủ | `python tools\gate.py` | *(đang chạy — xem "Phán quyết")* |

Mười lệnh kiểm đã chạy lại thật, không dựa vào trí nhớ:

```
Q102 có đúng 1 dòng · tiêu đề mục 1 = "đến Q102" · H37 có đúng 1 mục
DECISIONS.md có 7 mục D-00x · CHAM_DIEM.md tồn tại · bench/README.md tồn tại
.gitignore có 7 dòng bench/ · CLAUDE.md nhắc H37 2 chỗ
bảng quyết định còn 87 dòng "| Q" · cấu trúc bảng không bị chèn dòng trống
```

**Điểm:**

| Chiều | Trọng số | Điểm | Căn cứ |
|---|---|---|---|
| C1 phạm vi | 30 % | **10** | 5/5 việc của G0 trong `KE_HOACH_THI_HANH.md` §3, cộng 2 việc phát sinh (sinh lại `ho_so_he_thong.txt`, vá lỗ rubric) |
| C2 bằng chứng | 20 % | **10** | mỗi dòng bảng trên có lệnh kiểm lại **và đã chạy**, kết quả ghi ngay trên |
| C6 tài liệu | 50 % | **9** | Q102 + H37 + hai sổ + `CLAUDE.md` + `bench/README.md`. Trừ 1: chưa cập nhật `docs/NHAT_KY.md` và `docs/_luutru/PROJECT_MEMORY.md` — sẽ làm ở cuối phiên theo quy tắc 3 tầng |
| C3 đúng đắn | — | **không áp dụng** | G0 không sinh mã, không có số đo |
| C4 không phá | — | **không áp dụng** | không chạm runtime máy A, không chạm máy B |
| C5 vận hành | — | **không áp dụng** | G0 không tạo ra thứ gì phải chạy |

**Trung bình có trọng số: 9,5** *(trên ba chiều áp dụng được)*

⚠️ **Nhưng con số này không có nhiều ý nghĩa** — theo đúng luật vừa bổ sung ở §1.4:
G0 có **ba chiều không áp dụng**, nên nó là **bước chuẩn bị, không phải một phase
thật**. Phase đầu tiên mà điểm nói lên điều gì đó là G1.

**Blocker:** không có blocker riêng cho G0.

**BÁC BỎ:** kết luận quan trọng nhất của G0 là *"khung ghi chép đã sẵn sàng trước
khi sinh ra dữ liệu"*. Cách bác bỏ: **dùng thật** khuôn chấm điểm để chấm chính G0
— nếu khuôn không đủ cho phase đơn giản nhất thì nó cũng sẽ không đủ cho G4.

**Kết quả: bắt được hai thứ thật.**

1. **Bộ chấm điểm có lỗ.** Nó ngầm giả định cả sáu chiều luôn áp dụng. G0 có ba
   chiều không áp dụng, và nếu cứ thế lấy trung bình thì mẫu số nhỏ đi **im lặng**
   — một phase càng làm ít càng dễ điểm cao. Đã vá: `KE_HOACH_THI_HANH.md` §1.4 nay
   bắt phải ghi "không áp dụng" kèm lý do, chia lại trọng số, và **nói thẳng khi
   điểm không có ý nghĩa**.
2. **Phép kiểm độc lập chứng minh là độc lập thật.** `gate.py` bắt được thứ tôi
   không hề nghĩ tới: sửa `CLAUDE.md` làm `ho_so_he_thong.txt` lỗi thời →
   `FAIL 1/12`. Nếu tôi tự chấm mà không chạy gate, G0 đã "qua" với một tệp hồ sơ
   sai. Đây đúng là loại lỗi mà §1.1 nói tới.

**Phán quyết:** **QUA** — với hai điều kiện đã thoả (gate nhanh PASS 12/12, mười
lệnh kiểm bằng chứng đều đúng) và một điều kiện **đang chờ**: gate đầy đủ. Nếu gate
đầy đủ đỏ thì phán quyết này bị rút lại và G0 chấm lại lần 2.

**Việc còn nợ:** `docs/NHAT_KY.md` + `docs/_luutru/PROJECT_MEMORY.md` (cuối phiên).

---

## G2 — Xác minh giấy phép ⛔

### Phase: G2 — Xác minh giấy phép
**Ngày:** 2026-08-21 · **Lần chấm:** 1

**Kết quả một câu:** **Klein 9B bị loại** — FLUX Non-Commercial License v2.1.
Bộ model đích đổi sang **Qwen-Image 20B + Qwen-Image-Edit-2509 + Klein 4B**, cả ba
Apache 2.0.

**Bằng chứng:** [`LICENSE_NOTES.md`](LICENSE_NOTES.md) — 8 nguồn, mỗi kết luận kèm
trích dẫn nguyên văn và đường dẫn, đọc ngày 2026-08-21.

| Kết luận | Xác minh bằng |
|---|---|
| Klein 4B = Apache 2.0, cho commercial use | model card chính thức của nhà phát hành |
| Klein 9B = FLUX Non-Commercial v2.1 | model card chính thức + bảng biến thể |
| NC cấm *"revenue-generating activity"* | điều khoản giấy phép |
| Có mâu thuẫn 2(d) vs 4(a) trong chính giấy phép | thảo luận công khai trên model card 9B |
| Không có phản hồi chính thức nào gỡ mâu thuẫn | thảo luận đó + issue #32 kho mã chính thức |
| FAQ nhà phát hành: bán ảnh cần giấy phép thương mại | trích trong thảo luận |
| 4 bậc giấy phép thương mại, **không công bố giá** | trang licensing chính thức |
| Qwen-Image = Apache 2.0 **nguyên bản** | đọc thẳng tệp `LICENSE`, không chỉ nhãn |
| Qwen-Image-Edit-2509 = apache-2.0 + phủ 3 chế độ | model card chính thức |

**Điểm:**

| Chiều | Trọng số | Điểm | Căn cứ |
|---|---|---|---|
| C2 bằng chứng | 50 % | **10** | mỗi kết luận có trích dẫn + nguồn + ngày. Với Qwen đã đọc **tận tệp `LICENSE`** chứ không tin nhãn model card — vì nhiều model Qwen khác dùng giấy phép riêng |
| C3 đúng đắn | 30 % | **10** | đối chiếu chéo 3 nguồn độc lập cho kết luận chính; **đi tìm cách đọc ngược lại** trước khi kết luận (xem BÁC BỎ), không dừng ở kết quả tìm kiếm đầu tiên |
| C6 tài liệu | 20 % | **10** | `LICENSE_NOTES.md` mới · D-008 thay D-003 (D-003 gắn dấu ⛔, không xoá) · sửa `KE_HOACH_H37.md` §5 · sửa `KE_HOACH_THI_HANH.md` §5 |
| C1 · C4 · C5 | — | **không áp dụng** | G2 không sinh mã, không chạm máy nào, không tạo ra thứ phải chạy |

**Trung bình có trọng số: 10,0** *(trên ba chiều áp dụng được)*

Theo luật §1.4: ba chiều không áp dụng ⇒ đây vẫn là **phase điều tra, không phải
phase thi hành**. Nhưng khác G0, kết quả của nó **đổi hướng cả hạng mục** — nên
điểm ở đây có trọng lượng thật, dù thang đo hẹp.

**Blocker — cả hai đều đã kiểm:**

- [x] *"Không tìm được văn bản giấy phép chính thức → coi như không được bán"* —
  **tìm được**, từ model card của chính nhà phát hành.
- [x] *"Điều khoản mơ hồ về quyền với ảnh đầu ra → dùng phương án dự phòng"* —
  **có mơ hồ thật** (mục 2(d) vs 4(a)), và blocker này **đã kích hoạt đúng như thiết
  kế**: chuyển sang phương án dự phòng thay vì tự diễn giải giấy phép của người khác.

**BÁC BỎ:** câu hỏi tự đặt ra ở kế hoạch là *"nếu luật sư của bên phát hành đọc kết
luận này, họ phản đối ở đâu?"*

Họ sẽ chỉ vào **mục 2(d)**, chỗ nói đầu ra **có thể** dùng *"for commercial
purposes"*, và lập luận rằng ảnh sinh từ Klein 9B **bán được**. Đó là một phản bác
nghiêm túc, không phải nguỵ biện — nên tôi đã đi tìm nó thay vì kết luận sớm từ kết
quả tìm kiếm đầu tiên.

Ba lý do nó vẫn không cứu được Klein 9B:

1. **FAQ của chính nhà phát hành khép cửa đó lại:** *"If you're generating images for
   products you charge for … you need a commercial license."*
2. **Ngay cả theo cách đọc dung hoà, ta vẫn vi phạm** — ta không chỉ bán ảnh, ta
   **tự vận hành model trong một dịch vụ có thu tiền**, đúng vế mà cách đọc đó cấm.
3. **Không ai từ nhà phát hành trả lời để gỡ mâu thuẫn**, cả trên model card lẫn
   trên issue của kho mã chính thức.

Và một lý do kinh doanh độc lập với pháp lý: xây sản phẩm có thu tiền trên một mâu
thuẫn chưa được giải trong giấy phép của người khác là **rủi ro không có mặt lợi**,
khi đã có hai phương án Apache 2.0 tốt ngang hoặc hơn.

**Phán quyết:** **QUA — 10/10.**

**Ba điều đáng ghi lại:**

1. **Thứ tự phase đã cứu một khoản công thật.** G2 nằm **trước** việc tải ~45 GB là
   một quyết định có chủ ý khi lập kế hoạch. Nếu đi theo thứ tự của bộ build pack
   (bước 13 nằm gần cuối), ta đã tải model, đo đạc, dựng workflow, viết cổng render
   — rồi mới phát hiện không được phép bán.
2. **Phương án dự phòng hoá ra phủ yêu cầu tốt hơn phương án gốc.**
   Qwen-Image-Edit-2509 khớp gần một-một với ba chế độ đã chốt: ghép nhiều ảnh
   *person + person / person + product / person + scene* với giữ nhân dạng khuôn mặt
   (`subject`), ControlNet gốc depth/edge/keypoint (`structure`), sửa nội dung và
   font/màu/chất liệu chữ (`edit`).
3. **Nguyên tắc model-agnostic đã được thử thật và đứng vững.** Đổi model đích giữa
   chừng mà **kiến trúc không đổi một dòng nào** — chỉ đổi bảng model và các file
   workflow chưa viết.

**Việc còn nợ:** không có. G2 đóng.

---

## G6 — Cổng render (máy A, không cần GPU)

### Phase: G6 — Cổng render
**Ngày:** 2026-08-21 · **Lần chấm:** 1

**Kết quả một câu:** `render_gateway/` đã viết xong và có **53 test xanh chạy trên
máy A, không cần ComfyUI, không cần GPU** — đúng yêu cầu để G6 không bị chặn bởi
việc máy B đang dọn dẹp.

**Bằng chứng:**

| Việc | Tệp | Kiểm lại bằng |
|---|---|---|
| Client ComfyUI | `render_gateway/comfy.py` | mọi endpoint chú thích kèm số dòng mã nguồn gốc |
| Dò bận + ETA | `render_gateway/busy.py` | test ETA học từ thời lượng thật |
| Sổ job + idempotency | `render_gateway/jobs.py` | test cùng `job_id` không vẽ lần hai |
| Template + thẻ | `render_gateway/workflows.py` | test prompt chứa `@` không bị thay nhầm |
| Danh mục model | `render_gateway/catalog.py` + `workflows/catalog.json` | test `max_refs=2`, bucket 4 MP |
| Vòng thi hành | `render_gateway/runner.py` | test OOM · hết giờ · lỗi ref · lịch sử-lỗi |
| Hợp đồng HTTP | `render_gateway/api.py` | test 429-khi-bận, token, huỷ, độc chiếm |
| Vận chuyển thật | `render_gateway/http.py` | tách riêng để test không cần mạng |
| Điểm khởi động | `render_gateway/main.py` | từ chối chạy nếu nghe LAN mà không có token |
| Test | `tests/test_245_render_gateway.py` | `python -m pytest tests/test_245_render_gateway.py -q` → **53 passed** |
| Gate nhanh | — | `python tools\gate.py --quick` → **PASS 12/12** |
| Gate đầy đủ | — | *(đang chạy)* |

**Bảy sự thật lấy từ mã nguồn ComfyUI, mỗi cái có một test chốt:**

| Sự thật | Nguồn | Test |
|---|---|---|
| Client **được tự đặt `prompt_id`** | `script_examples/websockets_api_example.py` | `test_prompt_id_on_dinh_theo_job_id` |
| `progress`/`executing` gửi **chỉ tới client đã gửi prompt** | `main.py:450`, `execution.py:436/496` | (quyết định D-012 — bỏ websocket) |
| `/interrupt` nhận `prompt_id` để huỷ **đúng một** lượt | `server.py:1160` | `test_interrupt_bat_buoc_co_prompt_id` |
| `/history` có mục **cả khi hỏng**, kèm `status_str` | `execution.py:1282` | `test_co_muc_lich_su_KHONG_co_nghia_la_thanh_cong` |
| Mục hàng đợi là **mảng vị trí**, `prompt_id` ở chỉ số 1 | `server.py:1064` | `test_queue_prompt_ids_doc_dung_vi_tri_1_cua_mang` |
| Ảnh xem trước mang `type: "temp"` | `/history` outputs | `test_images_of_bo_qua_anh_xem_truoc_temp` |
| Model huấn luyện ~4 MP, dưới đó **giảm chất lượng rõ** | mô tả node `EmptyHiDreamO1LatentImage` | `test_catalog_mac_dinh_la_bucket_4mp_khong_phai_1920` |

**Điểm:**

| Chiều | Trọng số | Điểm | Căn cứ |
|---|---|---|---|
| C3 đúng đắn | 35 % | **10** | 53 test, phủ cả đường hỏng: OOM + thử lại một lần · hết giờ + huỷ đúng id · vấp mạng ≠ máy chết · "thành công nhưng không có ảnh" · file `.txt` đội lốt `.png` |
| C1 phạm vi | 20 % | **9** | 5 endpoint + độc chiếm + template + danh mục. Trừ 1: mới có chế độ `t2i`; `edit`/`subject`/`structure` chờ G5 vì cần chạy thật mới biết đồ hình node đúng |
| C5 vận hành | 25 % | **9** | mã lỗi ổn định · 429 ≠ 5xx · `main.py` **từ chối khởi động** nếu nghe LAN mà không token. Trừ 1: chưa chạy thật trên máy B (đó là G7) |
| C2 bằng chứng | 10 % | **10** | mỗi hợp đồng chú thích kèm **số dòng** mã nguồn ComfyUI, không phải "theo tài liệu" |
| C6 tài liệu | 10 % | **10** | D-011, D-012 · `workflows/README.md` ghi rõ template còn là **DRAFT** và bốn chỗ nghi ngờ nhất |
| C4 không phá | — | **không áp dụng** | không chạm runtime máy A, không chạm máy B |

**Trung bình có trọng số: 9,55**

**Blocker:**

- [x] `gate.py` xanh — quick **PASS 12/12**; gate đầy đủ *(đang chạy)*
- [x] Không có bí mật nào của nền tảng lọt vào `render_gateway/` — module không
  import `platform_core`, không đọc `app.env`, không biết CSDL. Khoá R2 không xuất
  hiện: ảnh vào/ra chỉ qua URL presigned do máy A cấp.

**BÁC BỎ:** kết luận quan trọng nhất của G6 là *"cổng này nói chuyện đúng với
ComfyUI"*. Tôi thử bác bỏ bằng cách **cho ComfyUI giả trả những thứ ác ý**: 200 kèm
thân rỗng · `node_errors` trong phản hồi thành công · mục lịch sử tồn tại nhưng
`status_str = error` · ảnh `type: temp` trộn lẫn ảnh thật · mạng lỗi 2 lần liên
tiếp rồi hồi phục · job kéo 6 phút.

**Kết quả: bắt được một lỗi thiết kế thật, trước khi viết mã.**

Kế hoạch cũ (`CHIA_GPU_VOI_VIDEO.md` §3–4) định **ước tính ETA của việc video bằng
cách nghe websocket ComfyUI**. Đọc mã mới thấy `progress` và `executing` gửi kèm
`server.client_id` — **chỉ tới client đã gửi prompt đó**. Cổng render sẽ **không
bao giờ** nhận được tiến độ của lượt video. Thiết kế đó bất khả thi, không phải khó.

Nếu tôi viết theo kế hoạch cũ, lỗi này chỉ lộ ra ở **G7 trên máy thật**, sau khi đã
viết xong lớp websocket và cả cơ chế kết nối lại. Đã thay bằng: học **trung vị thời
lượng** của việc lạ, và **không bao giờ ước lượng lạc quan** (chưa có lịch sử ⇒ trả
`None` = "không biết" = coi như lâu). Ghi ở **D-012**.

Đây là bằng chứng cụ thể cho chỉ đạo của chủ dự án: *"nên check tài liệu chia sẻ để
xây dựng thay vì tự suy"*.

**Phán quyết:** **QUA — 9,55** với điều kiện gate đầy đủ xanh. Nếu gate đỏ vì mã
mới thì rút lại và chấm lần 2.

**Việc còn nợ:**
1. `workflows/hidream_o1_t2i.json` là **DRAFT chưa chạy thật lần nào** — dựng từ đọc
   mã, vì gói `comfyui_workflow_templates` trên máy B có **0 file JSON**. G3 phải
   xác minh và sửa; bốn chỗ nghi ngờ nhất đã liệt kê ở `workflows/README.md`.
2. Chế độ `edit`/`subject`/`structure` chưa có template — chờ G5.
3. `render_gateway/http.py` chưa chạy với mạng thật — chờ G7.

---

## G7-chuẩn bị — bộ deploy (viết ở máy A, chưa chạy lên máy B)

**Ngày:** 2026-08-21 · **Không phải một phase** — đây là phần máy-A của G7. Phase
G7 chỉ đóng được khi đã chạy thật lên máy B và khởi động lại máy đó.

**Sản phẩm:**

| Tệp | Chạy ở đâu | Việc |
|---|---|---|
| `render_gateway/deploy/deploy.ps1` | **máy A** | chép mã sang B qua SSH · **so hash hai bên** · dựng venv riêng · sinh token |
| `render_gateway/deploy/cai_dat_dich_vu.ps1` | **máy B, Administrator** | hai dịch vụ NSSM · tường lửa chỉ cho .17 · **chặn nếu có quy tắc nào mở 8188** |
| `render_gateway/deploy/kiem_tra.ps1` | **máy B** | 7 nhóm câu hỏi, mỗi câu **có thể trả lời KHÔNG** |

**Bốn quyết định đáng ghi:**

1. **Token sinh TRÊN máy B, không sinh ở máy A.** Sinh tại chỗ rồi truyền sang sẽ
   để lại dấu vết trong log và lịch sử lệnh của máy A. Sinh ở B thì nó chỉ đi một
   chiều, qua SSH, khi máy A chủ động đọc.
2. **`deploy.ps1` KHÔNG cài dịch vụ và KHÔNG động tường lửa.** Hai việc đó cần
   quyền Administrator trên máy B; script chuẩn bị hết rồi in ra lệnh để chủ dự án
   chạy bằng cửa sổ nâng quyền — đúng cách đã làm với production máy A.
3. **`cai_dat_dich_vu.ps1` tự chặn chính nó** nếu phát hiện một quy tắc tường lửa
   nào đang mở cổng 8188 ra ngoài. ComfyUI không có xác thực; một quy tắc như vậy
   là cửa mở để chạy mã tuỳ ý trên máy B.
4. **`kiem_tra.ps1` nói thẳng câu nó KHÔNG tự trả lời được:** phải gọi thử từ một
   máy thứ ba trong LAN để chứng minh tường lửa chặn thật. *Đọc lại cấu hình tường
   lửa không phải là một phép kiểm.*

**BÁC BỎ:** kết luận cần bác bỏ là *"ba script này đúng"*. Tôi tự soi byte và đọc
lại từng dòng thay vì tin là mình viết đúng. **Bắt được ba lỗi thật:**

1. **Cả ba tệp `.ps1` có ký tự ngoài ASCII** (⛔, ⭐) — vi phạm quy tắc 2. `test_61`
   chỉ canh `setup/*.ps1` nên `render_gateway/deploy/` lọt lưới hoàn toàn.
2. **`kiem_tra.ps1` đọc token bằng `Substring(18)`** trong khi `"LTT_RENDER_TOKEN="`
   dài **17** ký tự ⇒ token mất ký tự đầu. Lỗi này sẽ lộ ra thành *"401 sai token"*
   ở **máy A**, rất lâu sau, ở một chỗ khác hẳn nơi gây ra nó.
3. **`cai_dat_dich_vu.ps1` in sai địa chỉ nghiệm thu** — bảo gọi
   `https://<máy A>:8199` trong khi phải là `http://<máy B>:8199`.

Đã thêm **7 test chốt** vào `test_245` cho đúng lớp lỗi này (ASCII · không BOM ·
không dùng `Out-File -Encoding utf8` · ComfyUI phải ở `127.0.0.1` · tường lửa phải
giới hạn theo địa chỉ · token phải đọc bằng `Split`).

Và một chi tiết đáng nhớ: **test đó báo đỏ ngay lần chạy đầu — vì chính dòng chú
thích đang cảnh báo về lỗi.** Đã sửa để bỏ dòng chú thích trước khi soi. Một phép
kiểm bắt oan sẽ bị người ta học cách bỏ qua, và khi đó nó tệ hơn không có.

**Trạng thái:** `python -m pytest tests/test_245 tests/test_247 -q` → **85 passed,
1 skipped**. Gate đầy đủ đang chạy.

---

## G1 — Đo nốt phần cứng máy B

### Phase: G1 — Đo phần cứng
**Ngày:** 2026-08-21 · **Lần chấm:** 1

**Bằng chứng:** [`bench/G1_phan_cung.json`](../../bench/G1_phan_cung.json) — mọi số
kèm điều kiện đo. Máy B lúc đo: GPU nghỉ (602 MiB / 5 % / 36 °C), ComfyUI
`queue_remaining = 0`, RAM trống 108,9 GB.

| Đo gì | Kết quả | Lặp lại |
|---|---|---|
| **PCIe** | **Gen 3 × 16**, **11,93 GB/s** đo trong lúc tải | lần 2: 11,94 GB/s (lệch 0,08 %) |
| Đĩa E: (kho model) | Samsung 860 EVO **SATA** — ghi 373, **đọc 476 MB/s** | — |
| Đĩa H: (849 GB trống) | Samsung 970 EVO Plus **NVMe** — ghi **1.070 MB/s** | — |
| `gpu_check.py` | exit 0 · torch 2.13.0+cu130 · CC **8.6** · 82 SM · bf16 ✅ | — |
| **fp8 tensor core** | **KHÔNG** (CC 8.6 < 8.9) — D-004 nay là **số đo**, không còn là suy luận | — |
| Phép tính bf16 thật | matmul 2048² chạy, lệch 0,877 so với CPU, hữu hạn | — |
| Trần công suất | **370 W** (không phải 250 W — hai task power-limit đang Disabled) | — |

**Điểm:**

| Chiều | Trọng số | Điểm | Căn cứ |
|---|---|---|---|
| C2 bằng chứng | 40 % | **10** | mỗi số kèm điều kiện đo; PCIe đo **hai lần**; ba nguồn VRAM đối chiếu chéo |
| C3 đúng đắn | 40 % | **10** | phép bác bỏ **tìm ra một lỗi thật** và lỗi đó đã sửa + xác minh lại (xem dưới) |
| C1 phạm vi | 20 % | **10** | 5/5 việc của G1, cộng phần "nhiệt và trần công suất" mới thêm ở bản 2 |
| C4 · C5 · C6 | — | không áp dụng | G1 chỉ đọc; không chạm runtime, không tạo dịch vụ |

**Trung bình có trọng số: 10,0**

**Blocker — cả hai đã kiểm:**

- [x] *"PCIe x4 hoặc thấp hơn → dừng"* — **Gen 3 × 16**, trường hợp tốt nhất. Đổi
  model bf16 16,4 GB chỉ mất **~1,4 giây**; fp8 **~0,7 giây**. Lo ngại "đổi model
  tốn kém khi chia card với video" **tan hẳn**.
- [x] *"Phép tensor thật không chạy → dừng"* — chạy, kết quả hữu hạn, lệch 0,877.

**BÁC BỎ:** *"chạy `gpu_check.py` hai lần, một lần khi có tiến trình khác giữ VRAM —
số VRAM có phản ánh đúng không, hay đọc ra số cũ?"*

**Kết quả: báo ĐỎ, và hoá ra là một lỗi thật trong mã tôi vừa viết ở G6.**

Cho một tiến trình torch khác giữ 8 GB rồi hỏi ba nguồn *"còn trống bao nhiêu"*:

```
nvidia-smi              15.308 MiB   <- ĐÚNG
ComfyUI /system_stats   23.165 MiB   <- MÙ
torch mem_get_info      23.217 MiB   <- MÙ
```

Trên Windows/WDDM hai nguồn sau **chỉ thấy tiến trình của chính mình**.

`render_gateway/busy.py` bản đầu đọc `/system_stats` cho chốt *"VRAM đang bị giữ
bởi tiến trình khác"* ⇒ **chốt đó không bao giờ bắn**. Nó là lưới duy nhất bắt được
một lượt torch chạy **ngoài** ComfyUI — mà máy B có sẵn nhiều script như vậy. Hậu
quả nếu để nguyên: cổng nhận job trong khi card đã đầy ⇒ **OOM giữa job của khách**.

Đáng chú ý về **cách** nó lộ ra: lần chạy đầu chỉ in `=> NGHI DOC SO CU (SAI)` và
trông như `gpu_check.py` sai. Phải đi thêm hai bước nữa — kiểm tiến trình giữ có
thật sự cấp phát được không (nó có: in `DA GIU 8 GB`), rồi đối chiếu `nvidia-smi` —
mới ra thủ phạm thật. **Nếu bỏ qua vì "chắc do script test hỏng", lỗi này sống tới
tận G9 hoặc tới lúc khách gặp.**

Đã sửa (**D-013**): `busy.py` đọc VRAM bằng `nvidia-smi`, trần 8 giây, cùng trần với
`platform_core/gpu.py`. RAM vẫn lấy từ `/system_stats` vì con số RAM không bị giới
hạn theo tiến trình. `gpu_check.py` đổi tên trường thành
`vram_TIEN_TRINH_NAY_*` và thêm đối chiếu `nvidia-smi`, để nó không lừa người đọc
tiếp theo đúng như đã lừa tôi. **Xác minh lại trên máy B:** với 8 GB bị giữ, bản sửa
báo `nvidia-smi: 9.359 MB đang dùng` — thấy đúng. Thêm **6 test** chốt vào `test_245`.

**Phát hiện thứ hai — kho model đang nằm trên ổ chậm (D-014):** E: là SATA
(476 MB/s) trong khi NVMe 2TB còn trống 849 GB. Nạp một checkpoint 16,4 GB:
**~33 giây từ E:** so với **~5–7 giây từ H:**. G3 sẽ tải model về `H:\LTT_MODELS\`
và thêm base path thứ hai vào `extra_model_paths.yaml` (thay đổi thuần cộng thêm).

**Phán quyết:** **QUA — 10,0.** Đây là phase đầu tiên có đủ chiều để điểm nói lên
điều gì đó, và nó vừa chứng minh bộ chấm điểm hoạt động: **phần BÁC BỎ bắt được một
lỗi mà 74 test đơn vị không bắt được**, vì lỗi nằm ở chỗ mã nói chuyện với thế giới
thật, không nằm trong logic.

**Việc còn nợ:** không. G1 đóng.

---

## G3 — Tải model + baseline *(ĐANG DỞ — chưa chấm)*

**Ngày:** 2026-08-21 · **Trạng thái: DỞ.** Máy B có việc trên GPU, chủ dự án yêu cầu
dừng mọi thứ chạm card. **Chưa chấm điểm** vì phần đo baseline chưa chạy.

**Đã xong:**

| Việc | Bằng chứng |
|---|---|
| Tải 3 checkpoint (30,26 GB) về `H:\LTT_MODELS\` | `BANG_KE.json` trên B — sha256 đủ 3 file, tốc độ 71–108 MB/s |
| Thêm base path thứ hai vào `extra_model_paths.yaml` | **thuần cộng thêm**, có sao lưu `.truoc_h37_20260821.bak`; xác minh bằng **chính bộ nạp của ComfyUI** (`load_extra_path_config`), không bằng hàm của tôi |
| ComfyUI thấy cả 3 checkpoint | `/object_info/CheckpointLoaderSimple` liệt kê đủ |
| venv riêng cho cổng render | Python 3.13.15 + fastapi + httpx; **venv ComfyUI không bị cài thêm gì** (đã kiểm) |
| Gói `render_gateway` chạy được trên B | 19/19 tệp, import OK bằng venv riêng |
| **Template `t2i` chạy ra ảnh thật** | `bench/G3_smoke.json` — 48,4 s, 1 ảnh 4,48 MB |

**Ba việc bất ngờ phải xử lý dọc đường, mỗi việc là một lỗi thật:**

1. **`scp` nuốt tệp im lặng** (**D-015**). Chép `tai_model.py` sang B: scp trả về 0
   nhưng **không có tệp nào được tạo và cũng không có tệp lạc ở đâu**. Thủ phạm là
   `\t` trong `\tai_model.py` — shell mặc định của OpenSSH trên B là `cmd.exe`.
   Cùng lệnh đó với `gpu_check.py` chạy tốt ⇒ **lỗi ẩn theo tên tệp**. Đã sửa
   `deploy.ps1` sang gạch chéo xuôi + test chốt.
2. **Tiến trình nền bị giết khi phiên SSH đóng.** `Start-Process` tạo tiến trình con
   của `sshd`; phiên đóng là nó chết, để lại stdout/stderr **0 byte** — không cả
   traceback. Đã chuyển sang `Win32_Process.Create` (qua dịch vụ WMI, không phải con
   của sshd).
3. **Lọc tiến trình ComfyUI theo dòng lệnh là sai.** Dòng lệnh của nó không chứa chữ
   `ComfyUI` (thư mục làm việc mới chứa), nên lệnh dừng của tôi **không dừng gì cả**
   và bản cũ tiếp tục trả lời — làm tôi suýt kết luận nhầm là cấu hình mới không có
   tác dụng. Phải tìm theo **ai đang giữ cổng 8188** (`Get-NetTCPConnection`).

**Một điều phải nói rõ, không giấu:** file `extra_model_paths.yaml` gốc **có BOM**,
và lệnh ghi của tôi đã **xoá BOM đó**. Tôi định chỉ nối thêm. Bỏ BOM là an toàn hơn
và đúng quy tắc 1, nhưng đó vẫn là một thay đổi ngoài dự định trên một tệp dùng
chung với dự án video. Đã xác minh bằng **chính bộ nạp của ComfyUI** rằng cả khối cũ
lẫn khối mới đều đọc đúng, và đã sao lưu bản gốc trước khi sửa.

**Còn lại của G3:**

- [ ] Baseline 5 ca ở cấu hình đích (bf16, 2560×1440, 50 bước) — **cần GPU**
- [ ] Thí nghiệm độ phân giải: 1920×1080 sinh thẳng ↔ 2560×1440 rồi thu nhỏ ↔ 2048² cắt
- [ ] Bác bỏ: khởi động lại ComfyUI rồi chạy lại **đúng seed** — có ra đúng ảnh cũ không

**Chưa có phán quyết.** Theo luật §1.6, một phase chưa có phần BÁC BỎ thì **chưa
được chấm**, không phải "chấm tạm".

---

## G3 — Tải model + baseline

### Phase: G3 — Tải model + baseline
**Ngày:** 2026-08-21 · **Lần chấm:** 1

**Kết quả một câu:** model chạy được ở **cấu hình đích**, **tái lập được từng byte**,
và **hai lỗi thật đã bị bắt** — nhưng card **chạm tiết lưu nhiệt** ngay ở một lượt
đơn, và tôi đã để lại bốn dấu chân ngoài dự định trên máy dùng chung.

**Số đo — cấu hình đích (bf16, 2560×1440, 50 bước, CFG 5,0):**

| | |
|---|---|
| Thời gian/ảnh | **92,3 s · 93,5 s** *(lượt sạch)*; ~97 s *(theo dấu thời gian lượt 21:31)* |
| VRAM đỉnh | **16,8 GB** / 24 GB — thoải mái |
| Nhiệt đỉnh | **82–83 °C** |
| Công suất | **369,6–370,0 W** trên trần 370 W |
| Throttle | Power Cap **+ `0x20` SW Thermal Slowdown** |
| RAM trống trước/sau | 107,3 → 107,1 GB — **không rò rỉ** |
| Trần 6 phút (D-011) | **đạt thoải mái** — 1,5 phút |

Thời gian **tỉ lệ thuận với số token**: 0,0254 · 0,0262 · 0,0272 s/token ở ba độ
phân giải (D-019). Ước tính bucket mới chỉ cần nhân `(W/32)·(H/32)`.

**Điểm:**

| Chiều | Trọng số | Điểm | Căn cứ |
|---|---|---|---|
| C2 bằng chứng | 25 % | **10** | mọi số kèm điều kiện đo; số **bẩn được đánh dấu là không dùng được** thay vì lặng lẽ trộn vào |
| C3 đúng đắn | 30 % | **10** | tái lập **byte-identical** hai lượt độc lập; thời gian chéo-kiểm bằng hằng số giây/token ở ba điểm; **bác bỏ tìm ra hai lỗi thật** |
| C1 phạm vi | 20 % | **8** | baseline + tái lập + đo độ phân giải xong. Trừ 2: **kết luận chất lượng về độ phân giải phải hoãn sang G4** vì 1 prompt không đủ (luật §1.5.5 đòi ≥ 50 cặp) |
| C5 vận hành | 15 % | **9** | thêm `dung_het.ps1` — công tắc khẩn cấp chỉ dừng việc của H37, **không đụng ComfyUI** vì nó dùng chung với video |
| **C4 không phá** | 10 % | **7** | xem dưới |
| C6 tài liệu | — | không áp dụng | *(gộp vào D-016…D-019)* |

**Trung bình có trọng số: 9,25 — NHƯNG C4 = 7 < 8.**

### ⛔ PHÁN QUYẾT LẦN 1: KHÔNG QUA

Theo luật §1.4 điều ②: **không chiều nào được dưới 8, và không cho bù trừ.** Trung
bình 9,25 không cứu được C4 = 7. Đây đúng là trường hợp mà điều ② sinh ra để chặn.

**Bốn dấu chân ngoài dự định trên máy dùng chung — vì sao C4 = 7:**

1. **Lệnh tách khỏi SSH vẫn chạy tiếp khi chủ dự án NGẮT tôi.** Lượt baseline
   21:31–21:38 chạy trọn vẹn dù tool call đã bị ngắt. Chủ dự án nhìn thấy "card
   đang chạy job" **mà không có cách nào dừng**. Đây là điểm nặng nhất: nó lấy mất
   quyền kiểm soát máy của chính chủ máy.
2. **Ghi ảnh vào `output/ltt/` của dự án video** — thư mục đã có sẵn `TEST1..TEST5*.mp4`.
3. **Xoá BOM của `extra_model_paths.yaml`** khi định chỉ nối thêm.
4. **Trong lúc dọn, tôi chuyển nhầm HAI TỆP `.mp4` CỦA HỌ** ra khỏi thư mục — bộ
   lọc `smoke|G3_` khớp theo tên với `smoke_p03_l1_00001_.mp4` và
   `MG3_na10_l1_00001_.mp4`. **Một thao tác dọn dẹp gây hại nhiều hơn thứ nó dọn.**

**Đã khắc phục cả bốn** *(khắc phục trước, chấm sau — không chấm rồi hứa)*:
`dung_het.ps1` (công tắc dừng, nhận diện việc H37 theo `filename_prefix`, **không**
đụng ComfyUI) · prefix đổi sang `ltt_h37/` ở **cả** catalog lẫn `chay_baseline.py` ·
ảnh đã chuyển sang `output/ltt_h37/` · hai tệp `.mp4` **đã trả về đúng chỗ và đã
xác minh** · `extra_model_paths.yaml` có bản sao lưu và đã xác minh bằng chính bộ
nạp của ComfyUI.

**BÁC BỎ:** kết luận quan trọng nhất là *"model chạy đúng và số đo tin được"*.
Ba cách bác bỏ, **hai cách thành công**:

1. **Chạy lại đúng seed sau khi ComfyUI khởi động lại** → ảnh **giống hệt từng byte**
   (SHA-256 trùng, hai ca độc lập). Tái lập **được chứng minh**, không phải giả định.
2. **Đọc con số thay vì tin dòng `OK`** → `0,6 giây` cho 50 bước ở 2560×1440 là bất
   khả thi. Truy tiếp ra **lỗi thật**: runner coi "có bản ghi `/history`" là "job của
   ta xong", trong khi một prompt **đang CHỜ, chưa chạy** vẫn trả `status_str:
   "success"` (vì `prompt_id` sinh tất định nên lặp lại). Nó vừa trả kết quả cũ vừa
   **xếp hàng lại**, đốt thêm ~100 giây GPU mỗi ảnh. Sửa: `da_xong()` đòi **hai**
   điều kiện, và tra `/history` **trước** khi xếp hàng (**D-018**).
3. **Đối chiếu chéo thời gian** giữa ba độ phân giải → hằng số giây/token nhất quán
   trong 7 %, nên các số thời gian tự xác nhận lẫn nhau.

**Việc phải làm trước khi chấm lần 2:**

- [x] Công tắc dừng khẩn cấp (`dung_het.ps1`) — **xong**
- [x] Ảnh của H37 ra khỏi thư mục dự án video — **xong**
- [x] Trả lại hai tệp `.mp4` — **xong, đã xác minh**
- [ ] **Từ nay mọi lệnh phóng tách khỏi SSH phải in kèm lệnh dừng** — đã làm ở lượt
      baseline v2, cần thành thói quen chứ không phải một lần
- [ ] Chấm lại C4 sau khi chạy thêm ít nhất một phase mà **không phát sinh dấu chân
      mới** trên máy dùng chung

⚠️ **Một cảnh báo cho G4/G9, rút từ chính số đo của G3:** một lượt **đơn lẻ** đã
82–83 °C và bật `SW Thermal Slowdown`. G9 chạy **100 lượt liên tiếp**. Trục
**370 W ↔ 250 W** thêm ở D-016 nay không còn là "thử cho biết" — nó là đường thoát
khả dĩ duy nhất chưa cần đụng phần cứng.

---

## G4 — CHƯA CHẤM ĐƯỢC, và C4 của G3 nay TỆ HƠN chứ không khá lên

**Vì sao chưa chấm G4:** phase chưa xong. Lô s90 mới 20/30 ảnh, chưa có JSON tổng
kết, và **cuộc so mù chưa diễn ra** — mà theo D-010 thì chất lượng là tiêu chí chọn
duy nhất và người chấm là chủ dự án, không phải tôi. Chấm G4 lúc này là chấm một
phase dở.

### ⛔ Điều kiện chấm lại C4 đã có câu trả lời, và là câu trả lời xấu

G3 để lại một ô chưa tick: *"chấm lại C4 sau khi chạy thêm ít nhất một phase mà
**không phát sinh dấu chân mới** trên máy dùng chung"*.

Phase tiếp theo **làm sập máy dùng chung** (D-024). Nên ô đó không những chưa tick
được, mà **C4 phải xuống thấp hơn 7**, không phải lên.

Bốn dấu chân của G3 là *phiền*: ghi nhầm thư mục, xoá BOM, chuyển nhầm hai tệp,
lệnh không dừng được. Dấu chân lần này là **khác loại**: một cấu hình tôi chọn chạy
ở **97,5 % VRAM trên máy để bàn dùng chung**, liên tục nhiều giờ, không chừa chỗ cho
hệ điều hành lẫn dự án video — rồi tôi xếp tiếp một chuỗi **tự động, không người
canh**, mà lượt kế của nó (`subject`, hai ảnh tham chiếu 4 MP) **chưa từng được đo
VRAM lần nào**.

Ba điều làm nó nặng hơn tổng bốn cái cũ:

1. **Chủ dự án mất máy**, không chỉ mất một thư mục.
2. **Tôi có số đo cảnh báo trong tay và đọc sót một mặt của nó.** D-022 ghi 23,9 GB
   /24,6 GB và tôi viết nó ra như một sự thật kỹ thuật thú vị, không như một biên an
   toàn đã cạn. Cùng lúc đó tôi ghi "quạt sửa xong, hết thermal slowdown" như tin
   tốt thuần tuý — trong khi nó cũng có nghĩa là **card nay chạy hết tải không nghỉ**.
3. **Chuỗi tự động nhân hậu quả lên.** Không có nó thì máy sập một lần rồi thôi;
   có nó thì lượt sau sẽ sập tiếp mà không ai kịp nhìn.

**C4 = 4/10 cho G4** (và điểm này chặn G4 dù mọi chiều khác có 10, theo §1.4 ②).

**Không chấm lại C4 của G3 lúc này.** Nó phải chờ đúng thứ nó đã chờ: **một phase
chạy trọn mà không để lại dấu chân nào**. Đếm lại từ đầu.

### Việc phải xong trước khi chấm G4

- [ ] ComfyUI khởi động lại với `--reserve-vram 3`; **đo lại VRAM đỉnh thật** ở
      cấu hình đích và ghi số vào đây
- [ ] 10 ảnh s90 còn thiếu, chạy **có người canh**, không tách khỏi phiên
- [ ] Chế độ tham chiếu đo **theo bậc** (1 ảnh @ 1 MP → đo → mới lên)
- [ ] Nhật ký Windows: `Kernel-Power 41` hay `BugCheck` — **không đoán**
- [ ] Lô so mù 60 cặp, chủ dự án chấm

**Date:** 2026-08-22

---

## ⚠️ ĐÍNH CHÍNH mục G4 ở trên — C4 chấm trên một tiền đề SAI

Mục trên cho **C4 = 4/10** với lý do *"chủ dự án mất máy"*. **Tiền đề đó sai.** Nhật
ký Windows cho thấy máy B **tự khởi động lại để cài cập nhật** (sự kiện `1074`,
*Service pack (Planned)*, 01:29:31), không hề sập. Chi tiết ở **D-025**.

**Chấm lại C4 = 6/10.** Nó vẫn dưới 8, nên **G4 vẫn KHÔNG QUA** — nhưng phải vì
đúng lý do:

| Vẫn tính | Không còn tính |
|---|---|
| Chạy ở **97,5 % VRAM** trên máy để bàn dùng chung nhiều giờ — biên quá mỏng, dù lần này không gây hậu quả | ~~"chủ dự án mất máy"~~ — **không xảy ra** |
| Xếp một cấu hình **chưa ai đo** (11.412 token so với 4.096) vào chuỗi **tự động, không người canh** — nó sẽ hỏng, chỉ là chưa kịp | ~~"tôi làm sập máy dùng chung"~~ |
| Đọc số đo cảnh báo (23,9/24,6 GB) mà không nhận ra đó là biên đã cạn | |
| Không lường việc máy có thể khởi động lại giữa lô — lô dài không ghi kết quả từng ảnh, mất số đo của 20 ảnh | |

**Và thêm một khoản trừ MỚI, thuộc C3 (đúng đắn) chứ không phải C4:** tôi **viết ra
một mục quyết định (D-024) kết luận nguyên nhân trước khi có bằng chứng quyết định**,
trong khi chính tôi đang nói "tôi không đoán". **C3 cho G4 = 6/10.**

Đây đúng là thứ §1.1 nói bộ chấm điểm sinh ra để chống: không phải chống việc làm
sai, mà chống việc **tự thuyết phục mình rằng mình đã biết**.

**Date:** 2026-08-22
