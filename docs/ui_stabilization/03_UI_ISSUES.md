# 03 — Ma trận vấn đề UI (có bằng chứng đo, 2026-08-26)

Mọi con số dưới đây đo bằng `scrollWidth` vs `clientWidth` trên **URL công khai**
`https://app.lttstudios.com`, Chrome thật qua Playwright — không suy từ mã.

⚠️ **Một cái bẫy trong chính phép đo, ghi ra để phiên sau không mắc lại:** phần tử
`sr-only` (chỉ dành trình đọc màn hình) luôn hiện ra như "tràn" với tỉ lệ kiểu
`58/1`, vì chúng **cố ý** rộng 1px. Không lọc chúng ra thì bộ số đầy dương tính
giả, và ta sẽ đi sửa những thứ đang đúng.

---

## UI-001 · Nút file native không vừa khung hẹp — **P1**, gốc của cả một chuỗi

**Phân loại:** BROWSER-NATIVE + COMPONENT
**Trang ảnh hưởng:** `/taoanh` đo trực tiếp; rủi ro ở 10 app có tổng **17** file
input Jinja + **8** React.

**Bằng chứng (1876px và 1280px — số **giống hệt nhau**):**

```text
label.im-upload    can 263px  ->  duoc 185px   thieu 78
div.im-two         can 458px  ->  duoc 381px   thieu 77
fieldset.im-group  can 458px  ->  duoc 381px   thieu 77
form.im-controls   can 474px  ->  duoc 413px   overflow-x:auto  <- THANH CUON
```

**Gốc:** nút file native cần **~263px** tối thiểu (nhãn "Chọn tệp" + "Chưa có tệp
nào được chọn"). `.im-two{grid-template-columns:1fr 1fr}` đặt **hai** cái trong
panel `minmax(340px,430px)` → mỗi ô 185px.

⭐ **Đây là một gốc, không phải bốn triệu chứng.** Bốn phần tử tràn ở trên là một
chuỗi: ô upload đẩy lưới, lưới đẩy fieldset, fieldset đẩy form, form có
`overflow:auto` nên biến phần thừa thành thanh cuộn ngang. Sửa ô upload thì cả
chuỗi tự sập.

⛔ **Nhưng đừng khái quát quá tay.** Ở `/taoanh/thumbnail` cùng một file input
rộng **368px và vừa khít**, không tràn. Mệnh đề đúng là *"native cần ~263px; khung
hẹp hơn sẽ vỡ"*, **không phải** *"file input luôn hỏng"*.

**Bán kính:** shared primitive + đổi nơi gọi. **Rủi ro:** trung bình — phải giữ
nguyên hành vi chọn tệp, validate, multipart, và các móc JS đang đọc `.files`.

---

## UI-002 · `overflow:auto` ở panel cao có hạn — **P2**, trùng lặp 3 app

**Phân loại:** LAYOUT + UI-SYSTEM

```css
.th-controls  {max-height:calc(100vh - 130px); overflow:auto}
.im-controls  {max-height:calc(100vh - 130px); overflow:auto}
.clip-controls{max-height:calc(100vh - 130px); overflow:auto}
```

Ba app sao chép nguyên văn. `overflow:auto` mở **cả hai trục**; ý định là dọc.
Toàn tệp: **17** `overflow:auto` / **1** `overflow-y:auto`; **11** trong số đó có
giới hạn chiều cao.

⛔ Đây **không phải** lý do để dùng `overflow-x:hidden`. Cắt bỏ phần thừa chỉ giấu
UI-001. Sửa đúng là `overflow-y:auto` — panel vẫn cuộn dọc, và nếu còn thừa ngang
thì nó **phải** lộ ra để ta thấy, chứ không bị nuốt.

---

## UI-003 · Hàng chip model tràn tới 3,4 lần bề rộng — **P1**

**Phân loại:** LAYOUT + CONTENT

```text
/taoanh            div.im-chips   407/381   (thua 26 — nhe)
/taoanh/thumbnail  div.th-chips  1322/391   (thua 931)
                   div.th-chips  1292/391
                   div.th-chips   599/391
```

`overflow-x:auto` là **cố ý**, nên về kỹ thuật "đúng thiết kế". Nhưng ở 1322/391
người dùng phải cuộn **hơn ba màn** mới thấy hết lựa chọn model — một lựa chọn
quan trọng bị giấu sau cử chỉ mà không có dấu hiệu nào báo còn nội dung.

⇒ Xếp P1 vì **hệ quả sử dụng**, không vì lỗi kỹ thuật.

---

## UI-004 · 316 màu viết cứng đi vòng qua 64 token — **P2**

**Phân loại:** UI-SYSTEM

437 lần dùng hex, **316 màu duy nhất**, trong một hệ đã có 64 token ngữ nghĩa.
Ngay khuôn file-picker tốt nhất kho (`.tv-ref-pickers`) cũng dùng `#6e302d`,
`#141315`, `#251213`, `#ff635b`, `#78797e`.

⛔ **Không thay hàng loạt.** Mỗi lần thay phải có bằng chứng, vì một màu cứng có
thể đang bù cho một token sai ở chỗ khác. Chỉ chuẩn hoá màu **trong primitive
mới**, để cái mới sạch và cái cũ được thay dần khi có lý do chạm vào.

---

## UI-005 · Hai thế hệ token cùng sống — **P3**

`--err/--ok/--warn` (cũ) cạnh `--status-danger/-success/…` (mới), cộng `--up-*`,
`--tv-accent` riêng app. Người viết app mới không có cách nào biết nên dùng bộ nào.
⇒ Việc của `04_UI_ARCHITECTURE_DECISION.md`: tuyên bố bộ chuẩn, **không xoá** bộ cũ.

---

## KHÔNG PHẢI VẤN ĐỀ — đã kiểm và loại

| Nghi ngờ ban đầu | Kết quả đo |
|---|---|
| Trang tràn ngang ở cấp tài liệu | **KHÔNG** — `docScrollW == docClientW` ở mọi viewport đã đo |
| Vỡ responsive ở tablet/mobile | **KHÔNG** — 768px: **0** tràn; 390px: chỉ `.im-chips` (cố ý), CTA cao 44px |
| Nhiều framework CSS cạnh tranh | **KHÔNG** — một `ltt.css`, 3 bundle React đóng gói riêng, không rò |
| Dấu vết 4 app đã gỡ | **KHÔNG** — chỉ còn chú thích, 0 CSS/nav mồ côi |
| `/jobs` (lịch sử) | **0** tràn |

⭐ **Kết luận trái trực giác, và nó định hình toàn bộ kế hoạch sửa:** trang vỡ ở
**desktop** và **lành ở mobile**. Media query đã đổi `.im-layout` và `.im-two` về
một cột dưới 768px — tức **bản sửa đã nằm sẵn trong CSS**, chỉ không áp dụng ở
desktop nơi panel bị ép hẹp có chủ ý.

⇒ Đây **không phải** dự án responsive. Đừng đụng breakpoint.
