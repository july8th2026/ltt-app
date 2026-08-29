# 21 — Hợp đồng giao diện khu `/admin`

Đọc cái này trước khi thêm một trang vào khu quản trị. Ngắn có chủ ý.
(Khuôn lấy từ `docs/developer_portal_mvp_ui/10_DEVELOPER_UI_CONTRACT.md` — hai
khu dùng chung một cách làm.)

---

## 1. Vỏ

Trang mới trả `_admin_shell(...)`. **Không có vỏ nào khác, và đừng dựng.**

```
server/templates/admin/_vo.html      thanh bên · thanh trên · bánh mì · mục con
└─ tab · cảnh báo/lỗi/thành công     ← vỏ lo hết
   └─ thân trang của bạn             ← bạn chỉ viết phần này
```

```python
return HTMLResponse(_admin_shell(
    "Tiêu đề tab", "khoa_o_SECTIONS", than_html,
    tieu_de="Tiêu đề trang",          # vỏ dựng <h1> — ĐỪNG tự dựng nữa
    mo_ta="Một câu nói trang này trả lời việc gì.",
    hanh_dong="<a class='btn'>…</a>",  # tuỳ chọn
    thanh_cong="…", loi="…", canh_bao="…",
    q_khach="…",                       # giữ nguyên ô tìm ở thanh trên
))
```

⚠️ Khai `tieu_de` thì **bỏ `.pagehead` trong thân**. Hai chỗ cùng dựng `<h1>` là
hai `<h1>` trên một trang.

⛔ Vỏ **không** `extends "base.html"`, và đó là quyết định: khu quản trị là
app-shell tràn viền, còn `base.html` thêm header nền tảng + `.page` giới hạn bề
rộng. Nhưng vỏ **có** `{% include "_kieu_chung.html" %}` — `.btn-danger`,
`.btn-sm`, `.table` sống ở đó chứ không ở `ltt.css`.

---

## 2. Bề rộng — authority ở ĐÚNG một dòng

`.adm-content{max-width:1600px}` trong `ltt.css`.

**Đừng đặt `max-width` hay `width` trên trang.** Cần khác thì đổi con số đó — nó
chỉ ảnh hưởng khu quản trị (`grep` chứng minh `.adm-*` chỉ hai tệp admin dùng).

⛔ **Đừng đụng `.app-side`** (210px) — dùng chung `/developers` + `/vps`.

---

## 3. Điều hướng — khai ở MỘT chỗ

`server/routes/admin/_chung.py`:

| | |
|---|---|
| `SECTIONS` | khoá → đường dẫn → nhãn. **Mọi** trang phải có một dòng, kể cả trang không lên thanh bên |
| `NHOM_NAV` | khoá nào lên thanh bên. **Trần 6 mục cha** (`test_317`) |
| `CHA_CUA` | mục con → mục cha. Bắt buộc cho cả trang hành động và tab |
| `MUC_CON` | dải mục con hiện trong trang cha. **Trần 6/miền** |
| `TAB_CUA` | tab cấp ba trong một mục con |

**Trang mới đi vào đâu?** Thanh bên đã đủ 6 mục ⇒ nó là **mục con** hoặc **hành
động theo ngữ cảnh**: thêm vào `CHA_CUA` (+ `MUC_CON` nếu muốn hiện), không thêm
vào `NHOM_NAV`.

⛔ **Không bao giờ xoá một route để dọn điều hướng.** Hạ khỏi thanh bên ≠ xoá.
Một URL đã vào dấu trang và tin nhắn hỗ trợ thì 404 là thiệt hại thật.

⛔ **Không tạo danh sách điều hướng thứ hai.** Khu này từng có **bốn** (xem
`19_BROWSER_QA.md` §4.1) và đó là lý do nửa SQLAdmin có menu khác hẳn nửa kia.

---

## 4. Kiểu lấy ở đâu

| Cần | Dùng | Ở đâu |
|---|---|---|
| nút | `.btn` · `.btn ghost` · `.btn-danger` · `.btn-sm` | `_kieu_chung.html` |
| ô nhập, select, textarea | thẻ trần — **đã có kiểu sẵn** | `_kieu_chung.html` |
| thẻ | `.card` | `_kieu_chung.html` |
| bảng | **`.dev-bang` bọc `<table class="table">`** | `ltt.css` |
| dải lọc | `<form class="dev-loc">` | `ltt.css` |
| trạng thái | `.dev-tt` + `.ok`/`.canh`/`.loi`/`.tat` | `ltt.css` |
| trạng thái rỗng | `.dev-trong` | `ltt.css` |
| chuỗi dài (id, url) | `.dev-id` | `ltt.css` |
| cặp nhãn–giá trị | `<dl class="dev-han-muc">` | `ltt.css` |
| số, ngày giờ | `.tnum` | `ltt.css` |
| lưới nội dung + rail | `.adm-luoi-rail` + `.adm-rail` | `ltt.css` |
| lưới thẻ theo chủ đề | `.adm-luoi-360` | `ltt.css` |
| tiêu đề khối trong thẻ | `.adm-khoi-dau` | `ltt.css` |
| dòng thời gian | `.adm-dongthoigian` | `ltt.css` |
| khối hành động nguy hiểm | `.adm-nguyhiem` + `.adm-form-nguyhiem` | `ltt.css` |
| hàng đợi chú ý | `.adm-hangdoi` | `ltt.css` |

**Một câu để nhớ:** nguyên tố (`input`, `button`, `table`) ở `_kieu_chung.html`
vì cả nền tảng dùng; cấu trúc dùng chung với `/developers` ở khối `.dev-*`; cấu
trúc riêng khu quản trị ở khối `.adm-*`.

---

## 5. Khi nào tạo lớp CSS mới

Chỉ khi **ba trang trở lên** cần cùng một cấu trúc và không lớp nào ghép được.

- Ghép được từ primitive → ghép, đừng đặt tên mới.
- Chỉ một trang cần → `style=""` một chỗ chấp nhận được; một lớp mới thì không.
- Grid có bề rộng tối thiểu → **luôn** dùng `minmax(min(Npx,100%),1fr)`. Bỏ
  `min()` là cả trang cuộn ngang ở 390px, không phải chỉ cái khối đó
  (`19_BROWSER_QA.md` §4.4).

---

## 6. Sự thật dữ liệu — luật cứng

Trang chỉ được hiện thứ có read-model thật đứng sau.

- Danh sách cấm ở `06b_SO_DANG_KY_NOI_DUNG_CAM.md`. `test_317` grep template.
- Muốn dùng một mẫu bị cấm: **không sửa test**. Chỉ ra read-model, ghi vào `05`
  Phần I, rồi xoá dòng ở `06b` kèm lý do.
- Một chỉ số **đọc không được lúc chạy** → ô đó ghi "không lấy được", **không**
  hiện `0`. Số 0 ở ô chú ý nghĩa là "mọi thứ ổn".
- **Đơn vị tiền không trộn**: VND ghi `đ`, credit ghi `credit`. 1 credit = 100 đ.

---

## 7. Thao tác ghi — luật cứng

Mọi handler `POST` phải có, không có ngoại lệ:

1. `verify_csrf_token` **trước** khi làm bất cứ việc gì;
2. `ghi_nhat_ky(db, request, hanh_dong, doi_tuong, chi_tiet)`;
3. phản hồi tường minh — kể cả khi **không có gì thay đổi** (idempotent). Im lặng
   chuyển hướng ⇒ người bấm không biết mình vừa không làm gì, và sẽ bấm tiếp;
4. xác nhận nêu **hệ quả**, không phải "Bạn có chắc không?".

`test_322` quét tự động (1) và (2) — thêm POST mà quên là gate đỏ.

⛔ Không bao giờ ghi **giá trị** secret vào nhật ký; chỉ ghi **việc** đã xảy ra.

⛔ Hành động nguy hiểm **không** đứng chung hàng với thao tác đọc. Tách khối, đặt
sau, mỗi việc kèm hệ quả viết bằng chữ.

⛔ **Không** đặt mutation trong bảng danh sách. Thao tác lên một đối tượng sống ở
trang của đối tượng đó, nơi người thao tác nhìn thấy mình đang tác động vào ai.
