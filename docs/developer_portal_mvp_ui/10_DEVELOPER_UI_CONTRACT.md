# 10 — Hợp đồng giao diện khu `/developers`

Đọc cái này trước khi thêm một trang mới vào khu API. Ngắn có chủ ý.

## 1. Vỏ

Trang mới `extends "developers_base.html"`. Không có vỏ nào khác, và đừng dựng.

```
base.html                     header nền tảng + <main class="page page--wide">
└─ developers_base.html       .app-shell = .app-side (điều hướng) + .app-main
   └─ trang của bạn           {% block section %}
```

`developers_base.html` đã lo: tiêu đề trang, dải mục con, cảnh báo API tắt / chỉ
đọc, khối lỗi, `csrf_token`, `sao_chep.js`. Bạn chỉ viết phần thân.

## 2. Bề rộng — authority nằm ở ĐÚNG MỘT dòng

`{% block page_mode %}wide{% endblock %}` trong `developers_base.html`
→ `.page--wide{max-width:1600px}` trong `ltt.css`.

**Đừng đặt `max-width` hay `width` trên trang.** Cần rộng hơn cho một trang thì
đổi `page_mode` của trang đó, không viết một con số mới.

`.app-side` là **210px và dùng chung với khu VPS** (`ltt.css`, khối
`.app-shell`). Đổi nó là chạm cả hai khu.

## 3. Điều hướng — khai ở MỘT chỗ

`server/routes/developer/_chung.py`:

| | |
|---|---|
| `SECTIONS` | khoá → đường dẫn → nhãn. **Mọi** trang phải có một dòng ở đây |
| `NHOM_NAV` | ba nhóm, mục nào lên thanh bên. **Trần 12 mục** (`test_303`) |
| `CHA_CUA` | mục con → mục cha. Mở con thì cha sáng |
| `MUC_CON` | dải mục con hiện trong trang cha |

**Trang mới đi vào đâu?** Nếu thanh bên đã đủ 10 mục thì nó là **mục con**:
thêm vào `CHA_CUA` + `MUC_CON`, không thêm vào `NHOM_NAV`.

⛔ **Không bao giờ xoá một route để dọn điều hướng.** Hạ khỏi thanh bên ≠ xoá.
Một URL đã vào dấu trang và tin nhắn hỗ trợ thì 404 là thiệt hại thật.

## 4. Kiểu lấy ở đâu

| Cần | Dùng | Ở đâu |
|---|---|---|
| nút | `.btn` · `.btn-ghost` · `.btn-danger` · `.btn-sm` | `_kieu_chung.html` |
| ô nhập, select, textarea | thẻ trần — **đã có kiểu sẵn** | `_kieu_chung.html` |
| checkbox/radio | thẻ trần, hoặc `.dev-chon` khi cần vùng bấm rộng | `_kieu_chung.html` / `ltt.css` |
| thẻ | `.card` | `_kieu_chung.html` |
| bảng | **`.dev-bang` bọc `<table class="table">`** | `ltt.css` |
| trường form | `.dev-field` (một) · `.dev-hang` (nhiều) | `ltt.css` |
| nhóm trường | `<fieldset class="dev-nhom"><legend>` | `ltt.css` |
| dải lọc | `<form class="dev-loc">` | `ltt.css` |
| trạng thái | `.dev-tt` + `.ok`/`.canh`/`.loi`/`.tat` | `ltt.css` |
| trạng thái rỗng | `.dev-trong` | `ltt.css` |
| bí mật hiện một lần | `.dev-mat` | `ltt.css` |
| khối mã có nhãn | `<figure class="dev-ma"><figcaption>` | `ltt.css` |
| lưới chỉ số | `.chi-so-luoi` + `.chi-so` | `ltt.css` |
| cặp nhãn–giá trị | `<dl class="dev-han-muc">` | `ltt.css` |
| chuỗi dài (id, url) | `.dev-id` | `ltt.css` |
| số, ngày giờ | `.tnum` | `ltt.css` |

**Một câu để nhớ:** nguyên tố (`input`, `button`, `table`, `fieldset`) ở
`_kieu_chung.html` vì cả nền tảng dùng; cấu trúc riêng khu API ở khối `.dev-*`
cuối `ltt.css`.

## 5. Khi nào tạo lớp mới

Chỉ khi **ba trang trở lên** cần cùng một cấu trúc và không lớp nào ghép được.

- Ghép được từ primitive → ghép, đừng đặt tên mới.
- Chỉ một trang cần → `style=""` một chỗ là chấp nhận được, một lớp mới thì không.
- Cần cho cả nền tảng → sửa `_kieu_chung.html`, và **đo trên vài app khác trước**
  (một `white-space:nowrap` tưởng vô hại đã suýt ăn vào chữ mẫu của
  `/autosubvideo`).

⛔ Không `!important`. Không `body{overflow-x:hidden}`. Không bộ token thứ hai.
Không chép CSS vào template.

## 6. Bảo mật — ba dòng không được quên

1. **Mọi POST mang `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`**,
   và handler gọi `verify_csrf_token` **trước** mọi việc khác.
2. **Chuỗi bí mật hiện một lần** đi qua `.dev-mat`, trong `<code>` (hình dạng
   `test_191` đọc). Không `localStorage`, không route đọc lại, không `?query`.
3. **Mọi truy vấn lọc theo `user.id` của phiên.** Không tin `id` trong URL.

Chi tiết: `02_BEHAVIOR_AND_SECURITY_CONTRACT.md`.

## 7. Khối mã

`<pre>` trần là đủ — `sao_chep.js` tự bọc `.khoi-ma` và gắn nút chép.
Cần nhãn ngôn ngữ (trang có nhiều khối liền nhau) thì bọc `.dev-ma` + `figcaption`.

⛔ **Không bao giờ in một khoá thật vào ví dụ.** Dùng `$LTT_API_KEY`.

## 8. Trạng thái rỗng

Phải trả lời **ba** câu, không phải một:

```html
<div class="dev-trong">
  <strong>{{ _("Chưa có X nào.") }}</strong>        <!-- CÁI GÌ  -->
  <p>{{ _("X xuất hiện sau khi… ") }}</p>            <!-- VÌ SAO  -->
  <a class="btn" href="…">{{ _("Làm việc Y") }}</a>  <!-- BƯỚC TIẾP -->
</div>
```

Trạng thái lỗi thì dùng biến `error` của `_render` — `developers_base.html` đã
in nó ở đầu trang, đừng in lần thứ hai.

## 9. Chữ

Mọi chuỗi hiển thị bọc `_()`, **và phải có `msgid` + `msgstr` không rỗng** trong
`locale/en/LC_MESSAGES/messages.po`.

⛔ **Thêm tay vào `.po`, đừng chạy `i18n.py trich`** — nó sắp xếp lại cả tệp, và
một phiên khác đo được ngày 26/08 rằng `msgmerge` tự sinh **25 bản dịch SAI**
khi trích lại. Xong thì `python tools/i18n.py bien-dich`.

⚠️ Đếm chuỗi bằng regex trên `.po` thì **sai về phía báo thiếu**: `msgid` dài bị
cắt thành nhiều dòng, nên `grep 'msgid "<chuỗi đầy đủ>"'` không bao giờ khớp.
Dùng `babel.messages.pofile.read_po`.

## 10. Trợ năng

- **Đúng MỘT `aria-current="page"` trên cả trang.** Cơ chế đã có trong
  `developers_base.html` — đừng thêm cái thứ hai. `test_303` chốt.
- Trạng thái không bao giờ **chỉ** mã hoá bằng màu: `.dev-tt` luôn kèm chữ thật.
- Mục đang chọn dày viền, không chỉ đổi màu chữ.
- Giữ ngữ nghĩa native: `.dev-chon` bọc quanh checkbox thật, không giấu nó đi.

## 11. Kiểm responsive

```bash
python tools/dev_portal_harness.py --port 8101
```

Một bản `/developers` **có dữ liệu**, CSDL tạm, không chạm production. Rồi:

```bash
playwright-cli -s=devui open "http://127.0.0.1:8101/?qa=<nhan>"
playwright-cli -s=devui --raw run-code --filename=tools/qa/dev_portal_qa.js
```

Chụp 16 trang × 6 khung (1920/1440/1280/1024/768/390) vào
`docs/developer_portal_mvp_ui/evidence/<nhan>/`, và **đo** bốn thứ ảnh chụp
không nói được:

| Chốt | Ngưỡng |
|---|---|
| `.app-main` @1920 | ≥ 1300px |
| `fieldset` viền `groove` | **0** |
| ô nhập viền `inset` | **0** |
| tài liệu tràn ngang | **0** ở mọi khung |
| lỗi console · phản hồi ≥400 | **0** |

⚠️ Bảng rộng thì cuộn **trong `.dev-bang`**, không cho tài liệu cuộn.
