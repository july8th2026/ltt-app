# V5_IMPLEMENTATION_STATUS — đã làm gì, và cái gì còn lại

> ⚠️ **Ảnh chụp 08/09/2026** (tệp này) — không phải hiện trạng. Số đồng thời LLM ở đây
> (`DONG_THOI_MAY_B=1`, `parallel=1`, một suất máy B…) **đã cũ** → `apps/ltt_llm/ngan_sach.HO_SO`
> (L-23, L-28 trong `docs/ltt_llm_dual/DECISION_LOG.md`).

> Artifact thứ 6, không nằm trong năm artifact bắt buộc. Nó tồn tại vì §24 đòi
> một cổng thoát có thể chấm được, và một cổng thoát chấm bằng trí nhớ là một
> cổng thoát sẽ nói dối.
>
> Cây: `phien/asv-v4` · worktree `auto-scan-video-v4-mvp-7173d9` · 2026-09-07.

---

## 1. Trạng thái theo 24 bước của §15

| # | Bước | Trạng thái |
|---|---|---|
| 1 | Audit current ASV UI | ✅ `CURRENT_UI_AUDIT.md` |
| 2 | Audit Viral Render | ✅ `VIRAL_RENDER_FEATURE_MAP.md` |
| 3 | Feature parity matrix | ✅ `FEATURE_PARITY_MATRIX.md` |
| 4 | Capability map | ✅ trong matrix (cột LTT capability) |
| 5 | UX information architecture | ✅ `V5_UI_INFORMATION_ARCHITECTURE.md` |
| 6 | UX wireframe/spec | ✅ IA §3, §7, §9 |
| 7 | Freeze product contract | ✅ IA + `VIRAL_HARVEST_DECISIONS.md` |
| 8 | Regression tests | ✅ `test_455` (20 chốt, quét AST toàn `routes.py`) |
| 9 | Refactor GUI shell | ✅ ba template viết lại |
| 10 | Basic workflow | ✅ 2 câu hỏi + thanh hành động |
| 11 | Advanced panels | ✅ 3 nhóm, accordion đóng sẵn |
| 12 | Preview | ✅ `<video>` + lớp phủ SVG, 0 credit |
| 13 | Region editor | ✅ `vung_che.py` + `asv.js`, toạ độ 0..1 |
| 14 | Subtitle controls | ⏸ `DEFER` — `CAM_TRONG_MVP: subtitle_burn` |
| 15 | Voice controls | ✅ lọc giới/vùng + nghe thử |
| 16 | Edit controls | ⏸ một phần — xem §3 |
| 17 | Missing capabilities | ✅ chỉ một mục: `nghe_thu.duong_cho_app_khac` |
| 18 | RenderManifest wiring | ✅ `ban_dung` schema 1→2, `hinh.vung`, vào vân tay |
| 19 | Result/progress/errors | ✅ %, elapsed, đối chiếu nguồn↔kết quả, lỗi 4 câu |
| 20 | Responsive/mobile | ✅ kiểm ở 375×812 trên trình duyệt thật |
| 21 | E2E | ⚠️ một phần — engine đã đo bằng ffmpeg thật; còn chặng chạy đủ chuỗi |
| 22 | Independent audit | ✅ `V5_UX_AUDIT.md` — và §0 của nó tự nói rõ nó **không độc lập** |
| 23 | Remediation | ✅ R1–R4 đóng — `V5_UX_AUDIT.md` §5–§9 |
| 24 | Re-audit | ✅ **xong 08/09** — `V5_REAUDIT.md`; bắt được 1 khiếm khuyết còn sót (Voice mode), đã sửa + chốt |

---

## 2. Tệp đã đổi

**Mới**

```
docs/auto_scan_video_v5/CURRENT_UI_AUDIT.md
docs/auto_scan_video_v5/VIRAL_RENDER_FEATURE_MAP.md
docs/auto_scan_video_v5/FEATURE_PARITY_MATRIX.md
docs/auto_scan_video_v5/VIRAL_HARVEST_DECISIONS.md
docs/auto_scan_video_v5/V5_UI_INFORMATION_ARCHITECTURE.md
docs/auto_scan_video_v5/V5_IMPLEMENTATION_STATUS.md
apps/auto_scan_video/vung_che.py          bốn luật hình học
server/static/asv.js                       client Studio
tests/test_455_asv_v5_hoi_quy_giao_dien.py 14 chốt hồi quy
tests/test_456_asv_v5_vung_che.py          18 chốt hình học
```

**Sửa**

```
apps/auto_scan_video/templates/*.html      viết lại cả ba
apps/auto_scan_video/routes.py             +4 handler (7→11), ngữ cảnh dùng chung
apps/auto_scan_video/gia.py                ước khoảng, thời gian, danh mục giọng
apps/auto_scan_video/quan_sat.py           `_tien_do_khach` — %, bước, elapsed
apps/ltt_voice/nghe_thu.py                 `duong_cho_app_khac`
apps/ltt_voice/__init__.py                 khai một tên (additive)
tools/lint_app_contract.py                 khai cặp tương ứng (additive)
server/templating.py                       `asv.js` vào danh sách cache-bust
server/static/ltt.css                      +130 dòng bố cục Studio
locale/en/LC_MESSAGES/messages.{po,mo}     +51 chuỗi
```

---

## 3. `DEFER` — có địa chỉ, không bị quên

Mỗi mục dưới đây có chỗ dành sẵn trong IA §4 và, nếu là dữ liệu, một trường
dành sẵn. Mở chúng = **ký một ADR-V5 + bật cờ**, không phải thiết kế lại.

| Mục | Chặn bởi |
|---|---|
| zoom · tỉ lệ khung · crop | `CAM_TRONG_MVP` |
| tốc độ | `DUNG_SAI_DO_DAI_S` |
| logo · watermark chữ | `HAU_MVP` |
| đốt phụ đề + style | `CAM_TRONG_MVP` (vì `autosubvideo` đã sở hữu) |
| nhiều ngôn ngữ đích | `HAU_MVP: multilingual_target` |
| nhiều giọng | `HAU_MVP: multi_speaker_voice` |
| OCR hardsub · tự dò logo · xoá bằng điền nền | chưa đo VRAM |
| cache artifact | thuộc `platform_core`, cần lease |

---

## 4. 🔴 Va chạm vật lý đã tìm ra, và cách xử lý

### Vùng che KHÔNG thể có ở preset “Giữ nguyên hình ảnh”

Đây là phát hiện lớn nhất của lượt triển khai, và nó **không phải** một chi tiết
kỹ thuật:

```
preset giữ hình  → -c:v copy        → byte hình đi thẳng, KHÔNG giải mã lần nào
                                     → không có khung hình nào tồn tại để sửa
preset rút gọn   → -filter_complex  → đã giải mã + mã hoá lại sẵn
                                     → thêm boxblur được
```

Làm mờ một vùng đòi hỏi một **bộ lọc**; một bộ lọc đòi hỏi giải mã rồi mã hoá
lại. Nên vùng che và lời hứa *"hình ảnh được sao chép nguyên vẹn, không giảm
chất lượng"* **loại trừ nhau về mặt vật lý** — không phải vì D-ASV-03 cấm, mà
vì hai điều đó không thể cùng đúng.

⇒ **Ba tầng cùng nói một điều:**

| tầng | làm gì |
|---|---|
| Giao diện | ẩn công cụ vẽ + nói rõ lý do khi preset là giữ hình; **xoá vùng đã vẽ** khi khách đổi preset |
| `ban_dung.kiem` | ném `BanDungError` cho bản dựng vừa `sao_chep` vừa có vùng |
| `giai_doan_ban_dung` | chỉ truyền `vung` ở đường cắt — **không tin giao diện** |

⛔ Nếu chỉ chặn ở giao diện, một yêu cầu dựng tay vẫn tới được, và `ket_xuat` sẽ
**lặng lẽ bỏ qua vùng** rồi giao một video không che gì — khách trả tiền cho một
thứ không xảy ra.

### N-2 — E2E chưa khép hết vòng

`test_457` chốt: chuỗi lọc, vân tay, bản dựng, và lệnh ffmpeg. Cái **chưa** có là
một lượt chạy đủ chuỗi tạo ra tệp thật rồi đo vùng trên tệp đó — nó nằm chung
với 7 phép kiểm `test_448` đang đỏ vì máy B bận (xem §7).

## 5. Kiểm thật đã làm

Không phải "test xanh nên chắc đúng". Đã chạy trên trình duyệt thật
(`127.0.0.1:8199`, bản dev riêng, **không** đụng dịch vụ production ở 8100):

- Studio dựng đúng ở 1440×900 và 375×812, **không tràn ngang**.
- `/uoc-tinh?giay=252` → `{27, 41, 756}`, hiện thành `~27–41 credit`.
- Trình sửa vùng: kéo thật bằng `PointerEvent` → `[{"loai":"lam_mo","y0":0.8,
  "y1":0.95,"x0":0.0999…,"x1":0.8999…}]` — **phân số, không pixel**.
- Hộp quá nhỏ bị bỏ kèm câu giải thích; xoá vùng cuối chạy.
- Vòng tròn: JSON **đúng như trình duyệt sinh ra** được `vung_che.chuan_hoa`
  nhận; một hộp tính bằng pixel bị **từ chối**.
- Console: **không lỗi nào**.
- Mobile: công cụ vùng ẩn, câu "chỉnh trên máy tính" hiện, thanh hành động dính.

### Hai lỗi mà bộ test KHÔNG thấy, và trình duyệt thấy

1. **`display:block` trên `<video>` đè `[hidden]`.** Bảng kiểu tác giả có ưu
   tiên cao hơn bảng kiểu trình duyệt, nên thẻ video chưa có nguồn vẫn chiếm
   100% bề rộng và đẩy khối trạng thái rỗng ra ngoài khung — ở 375px, *"Choose a
   video to start"* hiện ra thành *"ueo / tart"*. Sửa bằng `:not([hidden])`.
2. **`arguments.callee.loai`** trong trình sửa vùng: loại vùng bị đọc **sau** khi
   đã gán `null`, nên mọi hộp sẽ tới máy chủ **không có loại** và bị từ chối cả
   lô — khách mất hết vùng vừa vẽ mà không hiểu vì sao.

⇒ Đúng điều `CLAUDE.md` quy tắc 5 nói: test xanh không chứng minh trang hiển thị
đúng. Đây là lần thứ ba việc mở trình duyệt bắt được lỗi mà test không thấy.

---

## 6. Một đính chính đã ghi vào matrix

Bản đầu của `FEATURE_PARITY_MATRIX.md` xếp *"lọc giọng theo giới/vùng"* là
`EXTEND_LTT_CAPABILITY`, dẫn `CAPABILITY_INVENTORY_V4.md`. **Sai** — bảy tên đó
đã khai ở `apps/ltt_voice/__init__.py:59-65` từ trước, và `gia.giong_chon_duoc`
đã gọi `loc()`.

Nguồn của cái sai: đọc **bản kiểm kê** thay vì đọc **mã**. Bản kiểm kê đúng tại
`706faca`; một pha sau đã đóng mục này và nó không tự biết. Đã sửa, và đã ghi
luật: cột "LTT capability" phải đối chiếu lại với mã **ngay trước khi** mục đó
được implement.

---

## 7. Một lỗ của chính cổng chất lượng, tìm ra khi đi qua nó

`tools/lint_app_contract.py:427` đọc import xuyên-app bằng một regex **một
dòng**. Với `from apps.x.y import (A,\n B)`:

- `A` bị đọc thành `(A` → báo động giả trên một tên **đã khai**;
- `B` **không được kiểm một lần nào** → một tên bị cấm lọt qua cổng **im lặng**.

Vế thứ hai là vế nguy hiểm: nó là một lỗ trong chính phép kiểm ranh giới mà
ADR-002 dựa vào. Đã né bằng cách viết import một dòng; **lỗ vẫn còn**, và đã
được tách thành một việc riêng.

---

## 7. Bảy phép kiểm đỏ — không phải của lượt này, và đã xử lý

### Bằng chứng quy trách nhiệm

```
test-results/gates/loi-22584-bo-test--song-song.log   (13:25, TRƯỚC phiên này)
  → đúng 7 dòng FAILED, tất cả thuộc test_448, và khi đó chúng là
    bước đỏ DUY NHẤT của cả lượt gate (FAIL 1/29).
```

Nguyên nhân: `platform_core/llm/cong_vlm.py:225` ném `BanError` khi máy B trả
lời **bận**. `DONG_THOI_MAY_B=1`, và chính máy này chạy `Voice`/`Codex`
production dùng cùng suất. Diff của lượt này không chạm `dieu_phoi.py`, `ai.py`,
`dich_thuat.py` hay `asv_e2e.py`.

### 🔴 Nhưng có một lỗ thật, và nó nằm trong phạm vi ASV

`test_448._chan_tai_nguyen_ban` tồn tại **đúng để chặn ca này** — docstring của
nó ghi ca này đã xảy ra **ba lần** (05/09 13:44, 06/09 09:14 và 09:20), và mô tả
đúng hậu quả: *"chín câu đọc y hệt chín khiếm khuyết sản phẩm, và không câu nào
nhắc tới máy B"*.

Nó không nổ, vì chỉ khớp một trong **hai** hình dạng của cùng một sự cố:

| hình dạng | tiền tố | rào cũ bắt |
|---|---|---|
| tiêu hết ngân sách hoãn | `HET NGAN SACH HOAN …` | ✅ |
| **hoãn liên tục rồi bỏ cuộc** | `HOAN …` | ❌ ← ca 07/09 |

Nhánh `HET NGAN SACH HOAN` chỉ chạy khi `con_lai <= 0`; lượt 07/09 hết vòng lặp
**trước khi** ngân sách cạn, nên chỉ để lại dòng `HOAN …`.

### ⚠️ Cách sửa hiển nhiên là SAI

Ý đầu tiên — *"thêm `HOAN` vào điều kiện"* — tạo báo động giả. `HOAN {tên}: {exc}`
được ghi cho **mọi** lần hoãn, kể cả lần hoãn xong rồi chạy tiếp và **thành
công**. Một lượt chờ tài nguyên rồi làm được việc là một lượt **tốt**: nó chứng
minh đúng điều ta muốn — bộ chạy biết chờ.

⇒ Mệnh đề đúng là một phép **giao**:

```
có bằng chứng tài nguyên bận   VÀ   lần chạy không đi hết chuỗi
```

Bốn phép kiểm chốt cả hai chiều — và **hai chiều IM mới là phần chống báo động
giả**, phần gần như luôn bị bỏ quên:

```
NÓI  khi hoãn liên tục rồi bỏ cuộc      (hình dạng đã bỏ lọt thật)
NÓI  khi tiêu hết ngân sách hoãn        (hình dạng cũ, không được mất)
IM   khi hoãn XONG rồi chạy được        ← chống báo động giả
IM   khi hỏng vì lý do KHÁC             ← để chẩn đoán thật đi tiếp được
```

### Và một chỗ thứ hai, do phiên Workflow V2 tìm ra

`jobs.fail(db, job, str(exc), retry=False)` **vứt mất** biến `loi` vừa dựng
tiền tố. Hệ quả: `Job.error` nhận chuỗi thô trong khi `nhat_ky` giữ bản có tiền
tố — hai người đọc cùng một sự kiện thấy hai câu khác nhau, và người soi CSDL
thấy bản **nghèo hơn**. Đã đổi thành `jobs.fail(db, job, loi, ...)`.

⚠️ Đoạn đó nằm trong **vòng lặp worker của chính phép kiểm**, không phải mã sản
phẩm — nên mạch production không bị chạm.

### Kết quả đo được

| lượt gate | bước đỏ | FAILED | ERROR |
|---|---|---|---|
| 13:25 (trước phiên này) | 1/29 | **7** (gây hiểu nhầm) | 0 |
| 15:02 · 15:20 · 17:44 | 5 → 3 → 2 | 14 → 12 → 12 | 0 |
| **00:58 (chốt)** | **1/29** | **0** | **19, MỘT nguyên nhân** |

⭐ `0 FAILED` trên **8028 phép kiểm** là con số đáng nhìn nhất: không một khẳng
định nào sai ở đâu trong kho. 19 error đều từ `test_448` và đều mang cùng câu:

```
LUOT NGHIEM THU NAY KHONG CHAY DUOC — tai nguyen dung chung BAN,
khong phai san pham hong.
  Lam gi: hoi cac phien khac ai dang dung may B, doi ho xong, chay lai.
```

⛔ Gate **vẫn FAIL**, và nó **nên** vậy — docstring của cái rào nói thẳng:
*"Không skip: một lượt nghiệm thu không chạy được PHẢI đỏ."* Cái đổi là màu đỏ
ấy giờ nói đúng chuyện gì đã xảy ra.

### Một tension ghi lại có tên, và CỐ Ý không sửa

Trong 19 bài bị chặn, **ba bài không đo lần chạy** — chúng đo *bản báo cáo*:
`test_may_chay_nghiem_thu_duoc_ghi_lai`, `test_bao_cao_GHI_RO_thu_khong_that`,
`test_CUA_GOI_MODEL_tra_ve_CHUOI…`. Ba bài đó **vẫn trả lời đúng được** trên một
bản ghi từ máy bận, nên chặn chúng là mất tín hiệu thật.

⇒ Không sửa, và lý do là ranh giới giữa **sửa** và **tái cấu trúc nhân tiện**:
tôi không đổi thiết kế, tôi chỉ làm cái rào nổ đúng lúc nó đã luôn phải nổ. Tách
"bài đo báo cáo" khỏi "bài đo lần chạy" là một lần tái cấu trúc `test_448` thật
sự, cần có chủ đích.

**Tên của tension:** *cái rào chặn theo BẢN GHI, không theo CÂU HỎI mà từng bài
đặt ra.* Đã chuyển cho phiên Workflow V2 ghi vào `WF-302`.

