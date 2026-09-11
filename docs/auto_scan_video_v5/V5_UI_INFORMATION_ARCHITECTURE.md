# V5_UI_INFORMATION_ARCHITECTURE — kiến trúc thông tin của GUI mới

> Artifact 5/5. Đây là **hợp đồng sản phẩm** của GUI V5. Sau khi tệp này tự
> review PASS, implementation chạy tự động theo thứ tự §15 của prompt.

---

## 1. Một câu định hình mọi quyết định dưới đây

> Khách đến đây với **một video và một ý định**. Màn hình phải hỏi đúng ý định
> đó, rồi tự suy ra ba mươi tham số còn lại.

Đó là lý do V5 **không** bày 20 checkbox như Viral, và cũng **không** giữ nguyên
4 fieldset radio ngang hàng như ASV hôm nay.

---

## 2. Ba màn hình, không hơn

```
/auto-scan-video                Studio      — tạo lần chạy (mặc định) + lịch sử
/auto-scan-video/run/{id}       Tiến trình  — đang chạy → kết quả (cùng một trang)
/auto-scan-video/run/{id}/tai   tải xuống
```

⛔ **Không thêm màn hình thứ tư.** Trần hợp đồng app là 900 dòng / 30 handler cho
`routes.py`; hiện 428/7. V5 thêm nhiều nhất **6 handler** (§9), còn 17 chỗ dự phòng.

⭐ Trang chi tiết **không tách** "đang chạy" và "đã xong" thành hai trang: cùng
một URL, nội dung đổi theo trạng thái. Khách gửi link cho người khác thì link vẫn
đúng ở mọi thời điểm.

---

## 3. Bố cục Studio (desktop ≥ 1024px)

```
┌──────────────────────────────────────────────────────────────────┐
│  Lồng tiếng Việt cho video                    Lần chạy của tôi   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   NGUỒN & XEM TRƯỚC                 BẠN MUỐN GÌ                  │
│   ┌────────────────────────┐        ┌──────────────────────────┐ │
│   │                        │        │  ● Giữ nguyên video      │ │
│   │    ▶  video preview    │        │  ○ Cắt gọn thông minh    │ │
│   │                        │        ├──────────────────────────┤ │
│   │  00:00 ──────── 04:12  │        │  Giọng đọc               │ │
│   └────────────────────────┘        │  [ ♀ Bắc · Ngọc Huyền ▾] │ │
│   video-goc.mp4 · 78 MB · 4:12      │  [ ▶ nghe thử ]          │ │
│                                     └──────────────────────────┘ │
│   ▸ Tuỳ chọn nâng cao                                            │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  ~120–140 credit · ~6 phút            [ Bắt đầu lồng tiếng ]     │
└──────────────────────────────────────────────────────────────────┘
```

### 3.1 Bốn quyết định trong bố cục này

**(a) Preview ở bên trái, luôn hiện.** Không phải trang trí: nó là nền cho trim
marker, vùng che và safe area. Không có nó thì §6B và §10 của prompt không có chỗ
đứng.

**(b) Chỉ HAI câu hỏi ở tầng cơ bản** — *muốn gì* và *giọng nào*. Đây là thay đổi
lớn nhất so với hôm nay.

⭐ **"Cách khớp thời gian" bị gỡ khỏi tầng cơ bản.** Nó là **hệ quả** của preset,
không phải một lựa chọn độc lập, và bày ngang hàng là bắt khách quyết một việc họ
không có cơ sở để quyết. Nó xuống Nâng cao › Thời lượng, và preset đặt mặc định
đúng cho nó.

**(c) Ước giá + ước thời gian ở thanh dưới, cạnh nút.** Cạnh hành động, không ở
một góc xa. Là **khoảng có cận trên** (`~120–140`), không phải một con số đơn —
xem `VIRAL_HARVEST_DECISIONS.md` H-07.

**(d) Một `<details>` duy nhất cho Nâng cao.** Đóng mặc định. Người mới không bao
giờ phải nhìn thấy nó.

---

## 4. Basic ↔ Advanced

### Basic — đúng 4 thứ
```
Video · Kiểu xử lý · Giọng đọc · Bắt đầu
```

### Advanced — 5 nhóm, accordion, mỗi nhóm đóng mặc định

| Nhóm | V5 làm ngay | Chỗ dành sẵn (`DEFER`) |
|---|---|---|
| **Thời lượng** | cắt đầu/cuối (trim), cách khớp thời gian | tốc độ |
| **Vùng che** | trình sửa vùng: làm mờ · đánh dấu phụ đề gốc | xoá bằng điền nền · tự dò logo · logo của tôi |
| **Lời thoại** | nguồn lời (tự động / phụ đề nhúng / nghe tiếng nói) · từ điển tên riêng | OCR hardsub · sửa SRT rồi render lại |
| **Giọng** | lọc theo giới · vùng · phong cách · nghe thử · âm lượng gốc · giữ nhạc nền | nhiều giọng cho nhiều người nói |
| **Đầu ra** | (trống ở V5) | phụ đề đốt vào hình (→ `autosubvideo`) · thêm ngôn ngữ đích · tỉ lệ khung · ảnh bìa |

⛔ **Nhóm rỗng thì KHÔNG hiện.** Một accordion mở ra thấy trống là một lời hứa
hỏng. "Đầu ra" chỉ xuất hiện khi có ít nhất một mục thật.

⭐ Cột phải là hiện thân của luật **L3**: mỗi mục `DEFER` đã có địa chỉ. Ngày ADR
được ký, việc còn lại là bật cờ.

---

## 5. Preset — bốn, không hai

Hôm nay có 2 preset kỹ thuật. V5 giữ nguyên **hai đường xử lý** đó nhưng bày
thành ngôn ngữ ý định, và mỗi preset **đặt trước** cả một bộ chính sách:

| Preset (khách thấy) | `EditPolicy` | `TimingPolicy` | Nói với khách |
|---|---|---|---|
| **Giữ nguyên video** *(mặc định)* | `localize_preserve_picture` | `fit_original` | "Hình ảnh và độ dài y như bản gốc. Chỉ thay lời thoại." |
| **Cắt gọn thông minh** | `smart_localize` | `fit_original` | "Bỏ đoạn thừa, giữ mạch nội dung. Video sẽ ngắn hơn." |
| **Tuỳ chỉnh** | — | — | hiện khi khách chạm bất kỳ control Nâng cao nào |

⭐ **"Tuỳ chỉnh" không phải một lựa chọn khách bấm** — nó **tự bật** khi giá trị
lệch khỏi preset. Nó là một **chỉ báo trung thực**, không phải một nút. Đây là
cách duy nhất giữ preset khỏi nói dối sau khi khách sửa một ô ở Nâng cao.

⛔ Preset ánh xạ vào **chính sách trong `ban_dung`**, không vào trạng thái riêng
của UI. Prompt §9 yêu cầu đúng điều này, và nó là ranh giới giữ cho retry/resume
tái lập được đúng cấu hình.

---

## 6. Preview — một cấu hình, không hai

⛔ **Không có "preview config" và "render config".** §10 của prompt cấm, và lý do
sâu hơn: hai bộ cấu hình là hai nguồn chân lý, và cái thứ hai luôn trôi.

```
ban_dung (RenderManifest)  ─┬─→  trình dựng lệnh ffmpeg   (kết xuất thật)
                            └─→  lớp phủ CSS/SVG trên <video>  (xem trước)
```

Preview **không phải một job**. Nó là:
- `<video src="{presigned url}">` — trình duyệt phát trực tiếp từ R2;
- vùng che, safe area, logo vẽ bằng **CSS/SVG chồng lên**, đọc **cùng** mảng
  toạ độ chuẩn hoá mà `ban_dung` sẽ mang;
- trim marker là hai chốt trên thanh thời gian, ghi vào **cùng** trường
  `khoang_giu`.

⭐ Hệ quả then chốt: **preview tốn 0 credit, 0 GPU, 0 job.** Đó là khác biệt với
Viral (Preview 5s của họ là một lần chạy ffmpeg thật), và nó làm preview thành
thứ khách dùng thoải mái thay vì thứ họ tiếc.

⚠️ Giới hạn phải nói thẳng trong UI: lớp phủ cho thấy **vùng nào bị tác động**,
không cho thấy **hiệu ứng cuối cùng** (độ mờ thật, phông chữ thật). Một dòng nhỏ
"Xem trước vị trí — hiệu ứng thật áp dụng khi kết xuất" là đủ, và nó ngăn khiếu
nại "trông không giống lúc xem trước".

---

## 7. Tiến trình

### Khách thấy
```
Đang tạo giọng đọc                                  62%
████████████████████████░░░░░░░░░░░░░░
đã chạy 3 phút 40 giây · còn khoảng 2 phút

  ✓ Chuẩn bị video          ✓ Tách nhạc nền khỏi giọng
  ✓ Chép lời thoại gốc      ✓ Dịch sang tiếng Việt
  ⟳ Tạo giọng đọc           · Khớp thời điểm
  · Dựng bản ghép           · Kết xuất video
  · Kiểm chất lượng
```

Ba thay đổi so với hôm nay:
1. **Bước đang chạy được nêu tên to**, không chìm trong danh sách 11 dòng.
2. Có **%** và **elapsed**.
3. Các bước xong **thu gọn thành lưới**, không chiếm một dòng mỗi bước.

⛔ **Không giả ETA** (§12). Quy tắc: chỉ hiện "còn khoảng…" khi đã có ít nhất một
giai đoạn đo được **của chính lần chạy này**. Chưa đủ thì hiện elapsed và im lặng
về phần còn lại. Một ETA bịa tệ hơn không có ETA.

⚠️ Nhãn tiếp tục lấy khoá **từ `pipeline`** như `routes.NHAN_GIAI_DOAN` đang làm.
Đây là tài sản, không phải chi tiết — nó làm việc đổi tên giai đoạn mà quên sửa
nhãn thành một phép kiểm đỏ.

### Operator thấy (`<details>`, chỉ admin — giữ nguyên cơ chế hôm nay)
```
encoder h264_nvenc · 1,8× realtime · GPU 0 · 4,1 GB VRAM
điểm nghẽn: bộ lọc phụ đề chạy CPU
run 3f9a… · giữ 140 · tính 118 · lane gpu-2
```

Nguồn: `ket_xuat.bo_ma_hoa_thuc_te` + `ket_xuat.ho_so_chan_doan` — **đã có**,
chỉ thiếu đường lên UI.

---

## 8. Lỗi

Mỗi lỗi trả lời đúng bốn câu (§13), theo đúng thứ tự này:

```
┌─────────────────────────────────────────────────────────────┐
│  Không tạo được giọng đọc                                   │
│                                                             │
│  Bản dịch dài hơn thời lượng cho phép của đoạn này, nên     │
│  giọng đọc không khớp được vào đúng thời điểm.              │
│                                                             │
│  Bạn có thể: thử lại — hệ thống sẽ rút gọn lời dịch.        │
│                                                             │
│  [ Thử lại từ bước Tạo giọng đọc ]   [ Huỷ lần chạy ]      │
│  Thử lại không tính thêm credit.                            │
└─────────────────────────────────────────────────────────────┘
```

⛔ Khách **không bao giờ** thấy: traceback, lệnh ffmpeg, id provider, đường dẫn
lưu trữ, tên worker, job id. Operator được phép — trong `<details>` đã có.

⭐ Dòng cuối ("Thử lại không tính thêm credit") không phải trang trí. Không có nó,
khách phải **đoán** hậu quả tiền bạc của việc bấm một nút — và họ sẽ đoán sai về
phía không dám bấm.

---

## 9. Trang kết quả (cùng URL, `status == done`)

```
┌──────────────────────────────────────────────────────────┐
│   Nguồn              →           Kết quả                 │
│  ┌──────────┐                  ┌──────────┐              │
│  │   ▶      │                  │   ▶      │              │
│  └──────────┘                  └──────────┘              │
│  4:12 · tiếng Trung            4:12 · tiếng Việt         │
│                                                          │
│  [ Tải video ]  [ Chạy lại với cài đặt này ]  [ Xong ]   │
│                                                          │
│  ▸ Cài đặt đã dùng                                       │
│  ▸ Hệ thống đã giữ lại gì   (chỉ preset cắt gọn)         │
└──────────────────────────────────────────────────────────┘
```

- **So sánh cạnh nhau** là điều §11 đòi, và nó cũng là cách rẻ nhất để khách tự
  nghiệm thu.
- **"Chạy lại với cài đặt này"** điền sẵn cài đặt của lần chạy cũ vào Studio,
  và **nói ra** rằng nó vừa làm thế.

  ⛔ **Không** nạp lại `vung`. Vùng che là toạ độ trên khung hình của *một* video
  cụ thể; đặt chúng lên video khác là che nhầm một vùng khách không chọn — và
  khách sẽ không biết, vì ô chọn tệp đã đổi còn các ô khác thì không. Cài đặt nói
  *"xử lý thế nào"* thì nạp lại được; cài đặt nói *"ở chỗ nào trên khung hình
  này"* thì không.

  ⚠️ **Đính chính so với bản đầu của tài liệu này.** Bản đầu viết đây là *"chỗ
  cache artifact trả lời rõ nhất (đổi giọng ⇒ không chép lời lại)"*. Sai ở thời
  điểm: cache artifact vẫn đang `DEFER` (thuộc `platform_core`, chưa có), nên hôm
  nay nút này **chạy lại từ đầu**. Lợi ích thật của nó chỉ là *khách không phải
  gõ lại* — đủ để làm, nhưng không phải lý do đã viết.
- **"Hệ thống đã giữ lại gì"** chỉ hiện với `smart_localize`, và nói bằng ngôn
  ngữ khách: *"Bỏ 6 đoạn im lặng và 2 đoạn lặp lại — tổng 48 giây"*. Không hiện
  điểm số, không hiện tên thuật toán.
- ⛔ **Không** có nút "Tạo ngôn ngữ khác" ở V5 — `multilingual_target` đang
  `DEFER`. Chỗ của nó là cạnh "Chạy lại", và IA ghi nhận điều đó ở đây để ngày
  mở không phải bố trí lại.

---

## 10. Route mới — trần 6

| Method | Path | Việc |
|---|---|---|
| `GET` | `/uoc-tinh` | ước giá + ước thời gian theo thời lượng + cài đặt (JSON) |
| `GET` | `/giong` | danh mục giọng đã lọc (giới/vùng/phong cách) |
| `POST` | `/giong/nghe-thu` | sinh câu mẫu — **có giới hạn tần suất** |
| `GET` | `/run/{id}/nguon` | URL presigned của video nguồn (preview) |
| `GET` | `/run/{id}/ket-qua` | URL presigned của bản kết quả (preview) |
| `POST` | `/nhap` | lưu nháp `ban_dung` (vùng che, trim) trước khi bấm Bắt đầu |

Sau V5: `428 + ~250 = ~680` dòng / `13` handler. Trong trần 900/30.

⚠️ **Cả sáu handler phải giữ nguyên bốn tài sản** đã ghi ở
`CURRENT_UI_AUDIT.md` §3: cờ `_cong_co` **trước** `require_login`; lọc chủ sở hữu
ở tầng dịch vụ qua `_run_cua_toi`; 404 chứ không 403; CSRF trên mọi `POST`.

---

## 11. Mở rộng `ban_dung` (RenderManifest)

`SCHEMA_BAN_DUNG` **1 → 2**. Additive, đọc được ngược.

```
ban_dung v2
├── schema, phien_ban, ma            (đã có)
├── video   {khoa, thoi_luong_giay}  (đã có)
├── ke_hoach {preset, che_do, khoang_giu[]}   (đã có — trim ghi vào khoang_giu)
├── vung[]                           ✚ MỚI
│     {loai: "lam_mo" | "danh_dau_phu_de",
│      y0, y1, x0, x1,               phân số 0..1, KHÔNG pixel
│      tu_giay, den_giay}            rỗng = toàn bộ
├── tieng   {master, lop[], goc_vol} (đã có)
├── giong   {ma, che_do}             (đã có)
├── ra      {container, codec, ...}  (đã có)
└── chua_dung[]                      ✚ MỚI — chỗ dành sẵn, luôn rỗng ở V5
```

### Bốn luật của trường `vung[]`

1. **Toạ độ là phân số 0..1.** Không bao giờ pixel. Video đổi độ phân giải thì
   vùng vẫn đúng.
2. **Sai định dạng hoặc ngoài khoảng ⇒ TỪ CHỐI, không đoán.** Từ chối ở cửa
   (`routes`), không để xuống worker rồi hỏng giữa chuỗi.
3. **Biến đổi hình làm hộp ra ngoài khung ⇒ LOẠI hộp, KHÔNG kẹp về biên.**

   Với center-crop hệ số `Z`, mỗi toạ độ ánh xạ thành:

   ```
   p' = 0.5 + Z · (p − 0.5)          áp cho cả hai trục
   ```

   Hộp có `y1' ≤ 0` hoặc `y0' ≥ 1` (tương tự với `x`) đã **rời hẳn khung còn
   lại sau crop** ⇒ trả "không còn nghĩa", và người gọi bỏ nó đi.

   ⛔ **Không kẹp về `[0,1]`.** Viral trả giá cho đúng chỗ này (bug zoom
   2026-07): kẹp về biên cho ra một hộp `y0=1, y1=1` — một ô che đặt ở đáy
   khung, nơi chữ nó định che **đã biến mất**. Triệu chứng không phải "thiếu
   một ô che", mà là **một vệt mờ lạ ở góc màn hình** trên video đã giao.

   🔴 **Luật này CỐ Ý chưa có mã, và tài liệu này là nơi duy nhất giữ nó.**
   Bản đầu tôi viết `vung_che.anh_xa_zoom` + ba phép kiểm với lý do "luật có
   trước tính năng". `test_453` chặn lại: `zoom` nằm trong `CAM_TRONG_MVP` nên
   hàm đó **không có người gọi**, và một năng lực không người gọi là một năng
   lực viết xong rồi quên nối vào mạch. Gate đúng, tôi gỡ.

   ⇒ Ngày một ADR-V5 mở `zoom`, việc **đầu tiên** là hiện thực công thức trên
   kèm một phép kiểm cho hộp bị cắt mất — không phải kèm một phép kẹp biên.
4. **`vung[]` phải nằm trong khoá băm.** Đổi vùng mà khoá không đổi là serve
   nhầm kết quả cũ — đúng cái bẫy `cache_artifact.py` gọi là *"sót tham số =
   serve nhầm"*.

---

## 12. Mobile

Ngưỡng `< 768px`: một cột, thứ tự **Preview → Bạn muốn gì → Giọng → Nâng cao →
thanh hành động dính đáy**.

| Thành phần | Xử lý mobile |
|---|---|
| Bảng lịch sử | → thẻ xếp dọc (bảng 3 cột hôm nay sẽ tràn ngang) |
| Trình sửa vùng | **chỉ xem, không sửa** + một dòng nói rõ vì sao |
| So sánh nguồn/kết quả | xếp dọc, không cạnh nhau |
| Thanh hành động | `position: sticky; bottom: 0` — giá + nút luôn thấy |

⭐ Trình sửa vùng chỉ-xem trên mobile là một **quyết định**, không phải một thiếu
sót: kéo-thả hộp chính xác trên màn hình 375px bằng ngón tay cho kết quả tệ hơn
hẳn, và một công cụ chính xác giả còn tệ hơn không có công cụ. UI nói thẳng:
*"Chỉnh vùng che trên máy tính để chính xác hơn."*

---

## 13. Điều gì làm GUI này KHÔNG phải "ViralCrawl khoác áo LTT"

| Viral | V5 |
|---|---|
| 20+ checkbox ngang hàng | 2 câu hỏi cơ bản, 5 nhóm nâng cao đóng sẵn |
| Preview = một lần chạy ffmpeg | Preview = `<video>` + lớp phủ, **0 credit** |
| Cấu hình sống trong biến môi trường | Cấu hình là `ban_dung`, dữ liệu bền vững |
| Một tiến trình chạy tới cùng | 11 giai đoạn, thử lại được từng bước |
| Thất bại = log đỏ | Thất bại = *chuyện gì · làm gì tiếp · tốn gì* |
| Nhóm "né bản quyền" | **Không có** — quyết định thương hiệu |
| Nhanh nhờ lock tệp + env | Nhanh nhờ cache có khoá + lease của nền tảng |

---

## 14. Tự review — năm artifact đã PASS chưa?

| Điều kiện (§25) | |
|---|---|
| `CURRENT_UI_AUDIT.md` — lần đủ chuỗi, không chấm theo HTML | ✅ 22 bề mặt, 4 P0 |
| `VIRAL_RENDER_FEATURE_MAP.md` — đường UI thật, không chỉ README | ✅ index.html → 209 endpoint → CLI 60 cờ → engine |
| `FEATURE_PARITY_MATRIX.md` — không `BUILD NEW` khi chưa chứng minh | ✅ **0 mục** `BUILD NEW` |
| `VIRAL_HARVEST_DECISIONS.md` — 8 câu hỏi trước khi implement | ✅ 8/8 cho cả 8 mục P0 |
| `V5_UI_INFORMATION_ARCHITECTURE.md` — IA + hợp đồng đóng băng | ✅ tệp này |
| Ràng buộc giấy phép được nêu và tuân thủ | ✅ `UNLICENSED` ⇒ chỉ đặc tả + viết lại |
| Va chạm với hợp đồng đã đóng băng được nêu, không lách | ✅ `DEFER` + đường ADR-V5 |

**PASS.** Chuyển sang §15 bước 8 — viết regression test trước khi chạm GUI.
