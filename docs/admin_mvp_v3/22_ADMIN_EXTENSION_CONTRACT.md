# 22 — Hợp đồng mở rộng khu `/admin`

Bản chốt sau thi hành, thay `04_EXTENSION_CONTRACT.md` (tài liệu đó là **thiết
kế**; tài liệu này là **thứ thật sự tồn tại trong mã**).

---

## 1. Thêm một trang vào miền đã có — 2 chỗ, cùng một tệp

```python
# server/routes/admin/<mien>.py
class TrangMoiView(AnTrongMenuSqlAdmin, BaseView):
    name = "Nhãn"
    @expose("/duong-dan", methods=["GET"])
    async def xem(self, request: Request):
        from server.admin import _admin_shell           # lazy: tránh vòng import
        ...
        return HTMLResponse(_admin_shell("Tiêu đề", "khoa", than, tieu_de="…"))

VIEWS = (..., TrangMoiView)                              # ← chỗ 1
```

```python
# server/routes/admin/_chung.py
SECTIONS = (..., ("khoa", "/admin/duong-dan", "Nhãn"))   # ← chỗ 2
CHA_CUA  = {..., "khoa": "khoa_cha"}                     #   (cùng tệp)
MUC_CON  = {"khoa_cha": (..., ("khoa", "Nhãn trong ngữ cảnh"))}
```

**Tệp trung tâm phải sửa: 0.** `setup_admin` lặp trên `server.routes.admin.VIEWS`
và không biết tên trang nào.

---

## 2. Thêm cả một MIỀN mới — 1 dòng ở tệp trung tâm

```python
# server/routes/admin/__init__.py
from server.routes.admin import mien_moi as _mien_moi
VIEWS = (*_khach_hang.VIEWS, *_he_thong.VIEWS, *_mien_moi.VIEWS)
```

Một dòng, và đó là **đúng lúc** nên buộc người ta dừng lại suy nghĩ: thanh bên có
trần 6 mục cha, nên một miền thứ bảy nghĩa là một miền cũ phải nhường chỗ.

---

## 3. Bốn cấu trúc, một nguồn

`server/routes/admin/_chung.py` — `SECTIONS` · `NHOM_NAV` · `CHA_CUA` · `MUC_CON`
(+ `TAB_CUA` cho tab cấp ba).

Khuôn lấy nguyên từ `server/routes/developer/_chung.py`. **Hai khu, một cách
làm** — người đọc một khu hiểu ngay khu kia.

### Vì sao không phải một plugin framework

Prompt 04 cho phép thiết kế hợp đồng đăng ký. Không cần: `AREAS` là một tuple
viết tay đọc trong một giây. Không dynamic discovery, không entrypoint scanning,
không DI, không reflection — mọi thứ đó biến "trang này đăng ký ở đâu" từ một
câu trả lời thành một cuộc điều tra.

---

## 4. Trần — là test, không phải lời khuyên

| Trần | Giá trị | Chốt bởi |
|---|---|---|
| mục cha ở thanh bên | **6** | `test_317::test_tran_muc_cha` |
| mục con mỗi miền | **6** | `test_317::test_tran_muc_con_moi_mien` |

Muốn vượt trần thì sửa `03_IA_FREEZE.md` **trước**, rồi mới sửa hằng số. Đổi theo
chiều ngược lại là cách 25 mục phẳng đã hình thành.

Ngoài trần, `test_317` còn chốt:
- mọi tham chiếu trỏ vào khoá **đã khai** (khoá lạ ⇒ thanh bên không sáng gì, và
  người đang xử sự cố không biết mình ở đâu — kiểu hỏng im lặng phải bắt ở cổng);
- **không khoá nào mồ côi** (không ở thanh bên và cũng không có mục cha);
- `dieu_huong(k)` chạy được cho **mọi** khoá, và cho đúng **một** mục sáng;
- `_ADM_NAV` và `admin_api.NAV` **không quay lại**;
- vỏ SQLAdmin không có điều hướng viết tay và có cache-bust.

---

## 5. Ẩn khỏi menu SQLAdmin

Trang nghiệp vụ kế thừa `AnTrongMenuSqlAdmin` (ở `_chung.py`):

```python
class XView(AnTrongMenuSqlAdmin, BaseView): ...
```

Nó đặt `is_visible → False`, **chỉ ẩn khỏi menu của gói**; route sống nguyên.

**Bảng thô (`ModelView`) KHÔNG dùng lớp này** — thanh bên của SQLAdmin **chính
là** khu Data Explorer, và tên bảng ở đó là nội dung đúng của nó.

⚠️ Quên mixin này ⇒ trang xuất hiện **hai lần** trong hai hệ điều hướng khác nhau,
theo hai thứ tự khác nhau. Đó là nguồn điều hướng thứ tư mà `19_BROWSER_QA.md`
§4.1 mô tả — và nó chỉ lộ ra bằng mắt, `grep` không thấy.

---

## 6. Đường phụ thuộc

```
server/routes/admin/_chung.py      ← không import gì của admin
        ↑                    ↑
server/routes/admin/<mien>.py   server/admin.py   server/admin_api.py
```

`_chung.py` là **lá**. `server/admin.py` và `server/admin_api.py` đều import từ
nó; không cái nào import ngược lại.

⚠️ `<mien>.py` import `_admin_shell` **bên trong hàm**, không ở cấp module —
`server/admin.py` import `_chung`, nên một import ở cấp module sẽ tạo vòng.

Trước đợt này chiều phụ thuộc ngược lại: `server/admin.py` import `NAV` từ
`server/admin_api.py`, tức tệp nền phụ thuộc tệp miền (`02_DEEP_AUDIT.md` C-03).

---

## 7. Read-model

Truy vấn cho trang admin sống ở `platform_core/admin_console.py` (miền nền tảng)
hoặc `platform_core/public_api/admin_console.py` (miền API) — **không** trong
handler HTTP.

Ngưỡng: rút ra read-model khi có **≥ 2 call-site thật**. Một call-site thì để
trong view; tạo abstraction cho một chỗ gọi là thứ prompt 00 cấm.

⛔ Read-model **không mang nhãn hiển thị**. Trả mã định danh (`"viec_hong"`), để
template dịch sang chữ. Một chuỗi tiếng Việt trong `platform_core` nằm ngoài tầm
với của bộ dịch, và `tools/check_i18n.py` đếm nó như chuỗi chưa bọc — đúng như vậy.
