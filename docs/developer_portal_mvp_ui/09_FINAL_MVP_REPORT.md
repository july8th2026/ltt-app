# 09 — Báo cáo cuối: MVP giao diện cổng lập trình viên

**2026-08-26** · nhánh `public-api-v2` · khu `/developers`

---

## TRƯỚC

Chủ sản phẩm nói cổng *"quá basic"* và *"nhiều khoảng trắng"*. Đo bằng trình
duyệt thật trên một bản có dữ liệu, sáu con số:

| | |
|---|---|
| Nội dung dùng **898 px** trên màn hình 1920 | **47 %**, cả 16 trang, không sai một trang |
| **7 ô nhập** bị trình duyệt vẽ | `2px inset`, nền xám `rgb(59,59,59)`, bo góc 0 — nằm cạnh một `<select>` được vẽ đúng, cách 12 px |
| **3 `fieldset`** viền `2px groove` xám | khung nổi 3D giữa một trang phẳng tối màu |
| **8 lần tài liệu tràn ngang** | bảng khóa tràn từ 1024 px trở xuống |
| **Mọi nút đều đỏ đặc, không nút nào có viền** | kể cả nút phụ |
| `200` và `500` **cùng hình dạng cùng màu** | trang gỡ lỗi không gỡ được gì |

## NGUYÊN NHÂN GỐC

Sáu, và **không cái nào** là "thiếu một hệ thống thiết kế".

1. **Khu API chưa bao giờ khai `page_mode`** ⇒ rơi về `.page{max-width:1180px}`.
   Bốn mức bề rộng đã tồn tại; đây là khu duy nhất nhiều dữ liệu quên khai.
2. **`input[type=text]` không khớp một `<input>` không có thuộc tính `type`.**
   Bốn loại control (`input` không type, `type=search`, checkbox/radio,
   `fieldset`) không khớp luật nào **trong cả nền tảng**. Bằng chứng: năm app đã
   tự vá quanh chúng (`.tv-*`, `.th-*`, `.im-*`, `.clip-*`, `.up-*`). Khu API là
   app duy nhất không tự vá, nên là app duy nhất lộ ra.
3. **19 bảng không có vỏ cuộn** — `.tablewrap` có sẵn nhưng đi cặp với
   `.ui-table`, còn template dùng `<table class="table">` trần.
4. **Hai bộ từ vựng thành phần**, và bộ thắng là bộ nghèo hơn: `_kieu_chung.html`
   nạp **sau** `ltt.css` nên `border:none` của nó nuốt viền của `.btn.ghost`.
   `btn-primary` được dùng ở 7 chỗ và **không tồn tại ở đâu**.
5. **Không có primitive cho hàng form/dải lọc** ⇒ `width:100%` làm bốn ô lọc
   xếp chồng, mỗi ô 850 px.
6. **Trạng thái không được mã hoá** — `<strong>{{ status }}</strong>`.

## ĐÃ ĐỔI

| | |
|---|---|
| **1 dòng** ở `developers_base.html` | `page_mode = wide` → nội dung **898 → 1318 px** |
| **~70 dòng** ở `_kieu_chung.html` | vá bốn lỗ hổng cấp nền tảng + trạng thái form |
| **~230 dòng** cuối `ltt.css` | lớp `.dev-*` — 14 primitive ngữ nghĩa riêng khu API |
| **20 template** | dùng primitive thay markup trần |
| **56 mục** vào `messages.po` | thêm tay, giữ LF, có `msgstr` |
| **3 công cụ mới** | bản chạy có dữ liệu + hai bộ kiểm trình duyệt |

## SAU

| Chốt | trước | sau |
|---|---|---|
| `.app-main` @1920 | 898 px | **1318 px** |
| ô nhập viền `inset` | 42 | **0** |
| `fieldset` viền `groove` | 18 | **0** |
| tài liệu tràn ngang | 8 | **0** |
| lỗi console · phản hồi ≥400 | 0 · 0 | **0 · 0** |
| Hành trình Vàng | — | **39 PASS · 0 FAIL** |
| `pytest` 15 tệp hợp đồng | — | **299 passed · 0 failed** |

## KHÔNG ĐỔI — và đó là điểm chính

- **Không một dòng Python nào bị sửa.** 32 route, 7 CSRF, mọi truy vấn theo
  `user.id`, chính sách ghi log, ngữ nghĩa ký webhook, giá — nguyên vẹn.
- **Không thêm/bớt route.** `test_197` vẫn chốt đúng 32.
- **Điều hướng gom nhóm không hồi quy.** Ba nhóm, 10 mục, sáu route đã hạ cấp
  vẫn sống và vẫn tìm lại được; đúng một `aria-current="page"`.
- **Không nguồn chân lý thứ hai.** quickstart · tools · pricing · openapi vẫn
  sinh từ registry/hợp đồng đang chạy.
- **Không tính năng mới.** Không biểu đồ, không command palette, không SPA.

## TỆP ĐÃ ĐỔI

```
server/templates/developers_base.html        + page_mode
server/templates/_kieu_chung.html            vá cấp nền tảng (chạm MỌI trang)
server/static/ltt.css                        + lớp .dev-* ở cuối tệp
server/templates/dev_*.html                  18 tệp
locale/en/LC_MESSAGES/messages.{po,mo}       +56 mục
ho_so_he_thong.txt                           sinh lại
tools/dev_portal_harness.py                  MỚI
tools/qa/dev_portal_qa.js                    MỚI
tools/qa/dev_portal_golden.js                MỚI
docs/developer_portal_mvp_ui/                MỚI — 10 tài liệu + ảnh
```

## HAI THỨ TÌM RA MÀ KHÔNG AI ĐI TÌM

**① Một câu nói sai về chính sản phẩm.** `dev_settings.html` viết *"Xuất và xoá
dữ liệu tích hợp… **chưa có ở bước này**. Trong lúc chờ, liên hệ hỗ trợ"* —
trong khi `/developers/privacy/export` **đã chạy**, và nó là **mục con của chính
trang đang nói câu ấy**. Một trang bảo khách đi liên hệ hỗ trợ để làm việc họ tự
bấm được. Không test nào bắt được: đúng cú pháp, đúng bản dịch, đúng route.

**② `.dev-buoc` chưa bao giờ được định nghĩa.** Template dùng nó từ 25/08, và
CSS không có. Danh sách quan trọng nhất của khu — bốn bước tới lượt gọi đầu tiên,
tức Golden Outcome A — vẫn vẽ bằng `<ol>` mặc định của trình duyệt suốt từ đó.

## RỦI RO ĐÃ BIẾT

**1. `_kieu_chung.html` chạm mọi trang.** Đã quét 14 trang ngoài khu API, không
trang nào vỡ. Nhưng nó vẫn là một thay đổi toàn cục, và bốn app tắt bằng cờ ở
bản chạy cục bộ (`/vps`, `/nexus`, `/kichban`, `/anhnoibo`) **chưa được soi**.
⇒ Soi bốn trang đó trên URL công khai sau khi deploy.

**2. Đổi bí mật đổi luôn `key_id` công khai.** Hành vi có sẵn, không phải do
lượt này. Nhưng nay đã đo được, và hệ quả vận hành là thật: *một ticket hỗ trợ
trích mã khóa cũ sẽ không khớp hàng nào.* Trang **có** nói mã mới, nhưng **không**
nói nó đã thay thế mã cũ. Sửa là một câu, nhưng nó chạm nội dung sản phẩm ⇒
**để chủ sản phẩm quyết**, không tự làm.

**3. `/huong-dan/cong-cu` tràn ngang ở 390 px.** Có trước lượt này, trang công
khai, thuộc phạm vi phiên khác (đã lưu trữ: `docs/_luutru/2026-09/ui_stabilization/`).

**4. Cache của Cloudflare.** `ltt.css` đổi ⇒ `asset_ver` (hash nội dung) đổi ⇒
URL đổi ⇒ tới người dùng ngay. Nhưng **trang HTML** phải giữ `Cache-Control:
no-store` để link mang version tới được. Đã đúng; kiểm lại trên URL công khai
sau deploy, **không chỉ loopback** — quy tắc 5b của `CLAUDE.md` đã trả giá một
lần cho việc này.

**5. Ba phiên Claude cùng ghi kho này hôm nay.** Một phiên khác đã commit vào
`ltt.css` (khối `.dk`), `_header.html`, `templating.py`, `messages.po` trong lúc
tôi làm. **Không đè nhau** — khối CSS khác nhau, msgid khác nhau; đã kiểm bằng
`babel`: 56 mục của tôi còn nguyên, `.po` có 479 dòng thêm và **0 dòng xoá**,
vẫn LF, không con ma nào.

⚠️ Phiên đó sửa `.po` mà **không biên dịch lại `.mo`** — tức bản dịch mới của họ
không tới trình duyệt, và không có lỗi nào báo. Tôi đã chạy `i18n.py bien-dich`.

## ⭐ MỘT CÁI BẪY TRONG CHÍNH CỔNG CHẤT LƯỢNG — ĐÃ GHI LẠI

Bốn lượt `gate.py` đầy đủ đều in `CÂY ĐÃ ĐỔI TRONG LÚC CHẠY`, **kể cả lượt chạy
khi không phiên nào khác còn sống**. Nguyên nhân không phải phiên song song:

`_dau_van_tay_cay()` băm **mtime**, còn ba tệp trong `TEP_NOI_TIEP` **ghi đè tệp
thật rồi khôi phục trong `finally`** (`test_306` ghi đè chính `messages.po` —
đúng thiết kế, nó kiểm bánh cóc dịch). Khôi phục nội dung **không** khôi phục
mtime.

⛔ Nên cái chuông của Bẫy 5 kêu ở mọi lượt đầy đủ, và một cảnh báo kêu mọi lần là
một cảnh báo không ai đọc — đúng lúc cây **thật sự** bị đổi thì nó trông y hệt.

Đã ghi thành **Bẫy 15** trong `docs/BAY_TRONG_CONG_CHAT_LUONG.md`, kèm hai đường
sửa và một lệnh đo trực tiếp để dùng trong lúc chưa sửa.

⇒ **Kết quả gate của lượt này VẪN dùng được làm bằng chứng**: đã đo trực tiếp,
ba tệp bị ghi đúng là ba tệp của bộ test, không có tệp lạ nào.

## HOÃN SAU MVP

- Bề rộng khác nhau theo loại trang (văn xuôi vs bảng) — chưa có bằng chứng
  1600 px hại trang văn xuôi.
- Biểu đồ ở Sử dụng — backend chưa có chuỗi thời gian, và nó không phục vụ
  Golden Outcome nào.
- `.app-side` 210 → 240 px — chạm khu VPS, cần đo cả hai.
- Tìm kiếm trong Tài liệu.
- Gộp `dev_jobs` vào `dev_logs` — hấp dẫn, nhưng đụng route và `test_303` chốt
  cả hai đường sống riêng.
- Dọn `.tablewrap`/`.ui-table` và `.btn.ghost`/`.btn-ghost` về một bộ **trên
  toàn nền tảng** — lượt này chỉ thống nhất trong khu API.

## ĐỊNH NGHĨA HOÀN THÀNH

| | |
|---|---|
| 4 Golden Outcome đạt | ✅ 39/39 |
| Route giữ nguyên | ✅ 32/32 |
| Hợp đồng bảo mật giữ nguyên | ✅ không sửa Python |
| Điều hướng gom nhóm không hồi quy | ✅ `test_303` |
| Deep link không mất | ✅ 6 route đã hạ cấp vẫn sống |
| Một vỏ duy nhất | ✅ |
| Dùng hợp lý không gian desktop | ✅ 898 → 1318 px |
| Hết cảm giác form HTML thô | ✅ 0 `inset`, 0 `groove` |
| Form/nút/select/radio/checkbox cùng ngôn ngữ | ✅ |
| Khóa API dùng được + an toàn | ✅ GJ-C 12/12 |
| Hoạt động gỡ lỗi được | ✅ GJ-D 13/13 |
| Quickstart dẫn tới lượt gọi đầu | ✅ GJ-A 9/9 |
| Giá trung thực | ✅ số dư không đổi |
| Khối mã dùng được | ✅ 9 nút chép, không khóa thật |
| Trạng thái rỗng có bước tiếp | ✅ |
| Không tràn ngang hệ thống | ✅ 8 → 0 |
| Di động dùng được | ✅ 390 px |
| Trợ năng không hồi quy | ✅ một `aria-current`, native giữ nguyên |
| Không lỗi console mới | ✅ 0 |
| Test liên quan PASS | ✅ 299 passed |
| Hồi quy bảo mật PASS | ✅ tài liệu 07 |
| Browser QA PASS | ✅ tài liệu 06 |
| Không thêm tính năng ngoài MVP | ✅ |
| Không viết lại | ✅ 0 dòng Python |

---

## VIỆC CỦA CHỦ SẢN PHẨM TRƯỚC KHI DEPLOY

1. **Xoá ảnh của các đợt giữa** (~42 MB) — chỉ giữ `before` và `sau`:
   ```bash
   rm -rf docs/developer_portal_mvp_ui/evidence/b{1,2,3,4,6}
   ```
2. **Chạy `tools/gate.py` trên một cây đứng yên** — không phiên nào khác đang
   ghi. Hai lượt trước đều in `CÂY ĐÃ ĐỔI TRONG LÚC CHẠY`.
3. **Sau deploy, soi trên `https://app.lttstudios.com`, không chỉ loopback.**
   Loopback bỏ qua Cloudflare, và dự án đã một lần bị CF phục vụ `ltt.css` cũ
   trong 4 giờ sau khi sửa CSS.
4. **Soi bốn trang tắt bằng cờ** (`/vps`, `/nexus`, `/kichban`, `/anhnoibo`) —
   thay đổi ở `_kieu_chung.html` chạm chúng nhưng chưa soi được cục bộ.
