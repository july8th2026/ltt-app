# V5_REAUDIT — chạy lại đúng phép đo của `CURRENT_UI_AUDIT.md`

Bước 24 của §15. Tệp này **không** kể lại V5 đã làm gì — `V5_IMPLEMENTATION_STATUS.md`
đã kể. Nó chỉ làm một việc: lấy lại **đúng hai phép đo** của bản audit đầu,
chạy lại trên cây hôm nay, và đặt hai kết quả cạnh nhau.

⭐ Vì sao phải là *đúng* phép đo cũ: một bản tái audit tự chọn thước đo mới thì
   luôn thắng. Thước phải cố định từ trước, nếu không thì nó đo lòng tin của
   người đo chứ không đo sản phẩm.

Đo ngày **08/09/2026**, cây `.claude/worktrees/auto-scan-video-v4-mvp-7173d9`.

---

## 0. Kích thước bề mặt — cùng phép đếm, hai thời điểm

| | audit đầu | hôm nay |
|---|---|---|
| `templates/asv_trang_chinh.html` | 103 | **310** |
| `templates/asv_chi_tiet.html` | 55 | **107** |
| `templates/asv_tien_do.html` | 59 | **159** |
| **Tổng HTML** | **217** | **576** |
| `routes.py` | 428 — 7 handler | **663 — 12 handler** |
| JS riêng của app | *không có* | **`server/static/asv.js` — 450 dòng** |
| khối `@media` chạm `asv-*` | **0** | **6** |

Trần hợp đồng là **900 dòng / 30 handler** (`tools/lint_app_contract.py`). Ở
663/12 thì còn 26% dòng và 60% handler — nghĩa là V5 **không** tiêu hết ngân
sách hợp đồng, và app sau còn chỗ mà lớn.

⚠️ Con số duy nhất đáng lo trong bảng này là **576 dòng HTML**. Nó gấp 2,7 lần
bản cũ, và phần lớn phần thêm là *chú thích lý do* chứ không phải thẻ. Đó là
một lựa chọn có giá: template dài hơn thì khó đọc lướt hơn.

---

## 1. Bảng bề mặt — chấm lại bằng đúng luật cũ

Luật chấm giữ nguyên: lần đủ chuỗi `control → form → route → service → job/stage
→ output`, **không** chấm bằng sự có mặt của thẻ HTML.

Cột **bằng chứng** nói phép chấm này dựa vào đâu, vì ba loại bằng chứng không
mạnh như nhau: `trình duyệt` > `phép kiểm` > `truy vết mã`.

| Surface | audit đầu | hôm nay | bằng chứng |
|---|---|---|---|
| Create run | ✅ (form 4 fieldset dọc) | ✅ — 2 câu hỏi cơ bản, phần còn lại vào `Advanced options` | trình duyệt |
| Upload — đường bền | ⚠️ route sống, UI không gọi | ✅ — `asv.js` xin vé, PUT thẳng, `oTep.disabled` sau khi xong | phép kiểm `test_458` |
| Upload — multipart | ✅ | ✅ giữ làm đường lui | truy vết mã |
| Preset | ✅ nhưng không nói hệ quả | ✅ — mỗi preset kèm hệ quả về hình và độ dài | trình duyệt |
| Timing mode | ✅ nhưng bày ngang hàng | ✅ — chuyển xuống `Advanced` | trình duyệt |
| Voice mode | ⚠️ **UI mâu thuẫn chính nó** | ✅ — xem §2, đây là hàng bước 24 bắt được | trình duyệt |
| Voice picker | ⚠️ không lọc, không nghe thử | ✅ — lọc giới/vùng + nghe thử | trình duyệt |
| Cost estimate | ❌ | ✅ — `routes.uoc_tinh` | trình duyệt |
| Time estimate | ❌ | ⛔ **vẫn ❌ — CỐ Ý**, xem §3 | — |
| Preview | ❌ | ✅ — `createObjectURL`, không tải lên trước | trình duyệt |
| Progress | ✅ nhưng không `%`, không elapsed | ✅ — `45% · elapsed 9 minutes 12 seconds` | trình duyệt |
| History | ⚠️ in `r.status` thô | ✅ — `Incomplete / Processing / Done` | trình duyệt |
| Detail | ✅ nhưng trống rỗng | ✅ — đối chiếu nguồn↔kết quả + `Settings used` | trình duyệt |
| Retry | ✅ nhãn mơ hồ | ✅ — *"Retrying costs no extra credit"* | trình duyệt |
| Cancel | ✅ không hỏi xác nhận | ⚠️ **vẫn chưa hỏi xác nhận** | trình duyệt |
| Download | ✅ chỉ tải | ✅ — phát thử ngay trong trang | trình duyệt |
| Error | ⚠️ chỉ in tên bước | ✅ — bốn câu: chuyện gì · vì sao dừng · làm gì tiếp · tốn gì | trình duyệt |
| Operator details | ✅ thiếu số render | ✅ — bộ mã hoá + ×realtime | truy vết mã |
| Mobile | ❌ | ✅ — 375px: `scrollWidth 375 == innerWidth 375`, 0 phần tử vượt biên | trình duyệt |
| Empty state | ⚠️ đúng một câu | ✅ | trình duyệt |
| Loading state | ❌ | ✅ — nút `disabled` khi gửi | truy vết mã |
| Disabled state | ❌ | ✅ | trình duyệt |

**Bốn khiếm khuyết P0 của bản đầu:** P0-1 đóng · P0-2 đóng · P0-3 đóng ·
P0-4 đóng.

---

## 2. Thứ bước 24 tìm ra — và vì sao chỉ bước 24 tìm được

Hàng **Voice mode** của bản audit đầu viết:

> `AUTO_MATCH` và `USER_SELECTED` hiện đồng thời với ô select giọng luôn bật —
> khi chọn `AUTO_MATCH` thì ô select vẫn `required`, tức UI mâu thuẫn với chính nó.

Tôi đã định chấm hàng này ✅ theo trí nhớ. Đo thật thì **nó vẫn hỏng**: bấm
`AUTO_MATCH` xong đọc lại thẻ, kết quả là `required: true, disabled: false` —
y nguyên câu bản đầu viết.

Và phía máy chủ thì **không** đòi như thế. `routes.py:315`:

```python
if (che_do_giong == hop_dong_v4.CHE_DO_GIONG_TU_CHON and not giong_id):
```

⇒ Máy chủ chỉ đòi `giong_id` ở một chế độ. Trình duyệt đòi ở **cả hai**. Hai
bên nói hai luật khác nhau về cùng một ô.

⚠️ **Hôm nay nó không nổ**, và đó mới là lý do phải sửa. Danh sách giọng luôn
có một mục được chọn sẵn, nên phép cưỡng chế thừa ấy chưa từng chặn ai. Nó là
một mâu thuẫn **im lặng** — sẽ thành lỗi thật đúng vào ngày có người thêm một
mục rỗng vào đầu danh sách, và ngày đó không ai nhớ tới hàng này nữa.

**Đã sửa** ở ba lớp, và cách nối là phần đáng nói:

| lớp | đổi gì |
|---|---|
| `routes.py` | phát `che_do_giong_can_giong = hop_dong_v4.CHE_DO_GIONG_TU_CHON` ra ngữ cảnh |
| `asv_trang_chinh.html` | radio nào khớp thì mang `data-can-giong="1"` |
| `asv.js` | `oS.required = !chon \|\| chon.dataset.canGiong === "1"` |

⭐ Bản sửa đầu của tôi gõ thẳng chuỗi `"USER_SELECTED"` vào JS. Nó **chạy đúng**,
   và nó sai kiểu khác: một bản sao của hằng số hợp đồng, nằm ở một tệp mà không
   phép kiểm hợp đồng nào soi tới. Hằng số đổi thì JS trôi, và trôi im lặng.
   Nên luật đi từ `hop_dong_v4` → ngữ cảnh → thuộc tính → JS **đọc**.

Đo lại trên trình duyệt sau khi sửa:

```
banDau       : USER_SELECTED  required=true
khiAutoMatch : AUTO_MATCH     required=false
quayLai      : USER_SELECTED  required=true
```

⛔ Và **không** đóng `disabled` ô giọng ở chế độ `AUTO_MATCH`. Nhãn của chính
chế độ ấy nói *"hiện tại hãy tự chọn giọng"* — tắt ô chọn sẽ mâu thuẫn với câu
chữ đứng ngay cạnh nó. Năng lực tự khớp giọng chưa được nối (`doc_ho_so`,
`loi_nhac_ho_so` còn trong `MO_COI_DA_BIET` của `test_453`), và giao diện đang
nói thật về điều đó.

---

## 3. Hai hàng KHÔNG xanh, và cả hai là cố ý

**`Time estimate` — vẫn ❌.** `V5_UI_INFORMATION_ARCHITECTURE.md` §7 cấm bịa
ETA. Một ước *"còn 2 phút"* dựng trên một lượt chạy chưa đo được gì là một con
số bịa; khách sẽ nhớ nó rồi đợi gấp ba. Màn tiến độ vì thế hiện **thời gian đã
chạy** — một sự thật — chứ không hiện thời gian còn lại.

⇒ Hàng này đỏ trong bảng nhưng **không phải món nợ**. Nó là một lựa chọn, và
  chỗ đúng để lật lại là ADR chứ không phải một lần sửa giao diện.

**`Cancel` — vẫn ⚠️.** Nút huỷ vẫn không hỏi xác nhận. Đây **là** một món nợ
thật, nhỏ, và tôi để lại có ý thức: nó không nằm trong bốn P0, và thêm một hộp
xác nhận là thêm một mẫu tương tác mới mà nền tảng chưa có ở đâu khác — làm
riêng cho một app là gieo mầm lệch chuẩn. Đúng chỗ của nó là một tiện ích dùng
chung ở `platform_core`.

---

## 4. Bản tái audit này KHÔNG chứng minh gì

Ranh giới phải viết ra, vì một bản audit im lặng về giới hạn của nó đọc như một
lời bảo đảm.

1. **Không chứng minh mạch xử lý chạy đúng.** Ba lần chạy trên màn hình là dữ
   liệu **gieo**, không do một lượt chạy sinh ra. Nó chứng minh *giao diện dựng
   đúng khi có dữ liệu thật ở từng trạng thái* — đúng phạm vi của một bài audit
   giao diện, không hơn.
2. **Không thay `test_448`.** Cổng nghiệm thu đầu-cuối vẫn đỏ vì `ltt_llm` trên
   máy B bận, và nó **nên** đỏ.
3. **Không kiểm trên URL công khai.** Quy tắc 5b của `CLAUDE.md` đòi chốt ở
   `https://app.lttstudios.com`. Cây này chưa deploy, nên vòng Cloudflare (cache
   CSS, CSP biên, minify) **chưa được kiểm**. Phải làm sau khi deploy, không
   thay được bằng loopback.
5. **Không nói gì về cây SAU KHI HOÀ.** `test_453` đo trên một cây **chưa có**
   `apps/lttvideo/`. Trên trunk, `apps/lttvideo/cong/` định nghĩa `tien_do` ở **ba**
   chỗ và gọi nó ở một chỗ (`jobs.py:262`).

   ⇒ **Chạy lại `test_453` ngay sau lượt hoà**, không chỉ trước. Đây đúng cái lớp
   lỗi §2 vừa mô tả: một phép kiểm đúng trên một phạm vi hẹp hơn mệnh đề nó
   chứng minh.

   ⭐ Lập luận nói nó sẽ xanh: `_ham_cong_khai_cua_asv()` dựng tập **ứng viên**
      từ `GOI_ASV` — và luôn như thế — nên ba định nghĩa của `lttvideo` chưa bao
      giờ là ứng viên. Bản sửa 08/09 chỉ đổi phía **người dùng**. Nhưng một lập
      luận không thay được một lượt chạy.

4. **Không đo tương phản WCAG.** `--brand-primary` đo được 3.99 so với ngưỡng
   4.5 — thuộc toàn nền tảng, không thuộc ASV, và vẫn chờ chủ dự án.

---

## 5. Bằng chứng

- Bản dev: `chay_asv_dev.py` cổng 8199 · CSDL SQLite trong scratchpad.
- Ba lần chạy gieo: `r4-dang-chay` (running 5/11) · `r4-da-xong` (done 11/11) ·
  `r4-hong` (error tại `voice_synthesis`).
- Mạng: 68 request, **0 lỗi mới**; `ltt.css` và `asv.js` đều đính `?v=` và hash
  tự đổi `93cb391c → 82b71d29` khi `asv.js` đổi — quy tắc 6 của `CLAUDE.md` chạy.
- Console: 0 lỗi JS.
- Phép kiểm: `test_452` + `test_453` xanh (23 passed) sau khi gỡ `features.tien_do`;
  `test_455` + `test_447` xanh (39 passed); `test_455` riêng 20 passed sau khi
  thêm chốt mới.
- Đối chứng cho chốt mới: tiêm lại bản cũ (chép `"USER_SELECTED"` vào JS)
  → `returncode 1`, đỏ đúng vế; cây đã hoàn nguyên.

⚠️ Và chính chốt ấy đã sập bẫy quen thuộc ở lần chạy đầu: nó quét cả tệp,
   nên nó **đỏ trên chính đoạn chú thích giải thích nó** — đoạn có nhắc tên hằng số
   trong ngoặc kép để nói rõ điều bị cấm. Một bộ dò quét văn bản thô trừng phạt
   việc giải thích, và cách người ta tránh hình phạt ấy là **ngừng giải thích**.
   Đã vá bằng `_bo_chu_thich_js()`, kèm ghi rõ nó **không** phải một trình phân
   tích JS và sẽ bỏ nhầm nếu có chuỗi nào chứa `/*`.

⚠️ Một vết bẩn tự gây ra, ghi lại vì nó sẽ lặp: `chay_asv_dev.py` neo thư mục
dữ liệu theo **cwd**, và `preview_start` chạy nó từ gốc kho — nên nó đẻ
`D:\LTTSTUDIOSAPP\asv_dev\` (1,1 MB) vào **kho chính**, không phải worktree. Đã
xoá, và đã truyền thư mục scratchpad làm `argv[1]` trong `.claude/launch.json`.
Chú thích cảnh báo ngay trong tệp ấy đã có từ lần trước — **nó không đủ**, vì
lần này đường gọi tới từ một chỗ khác.
