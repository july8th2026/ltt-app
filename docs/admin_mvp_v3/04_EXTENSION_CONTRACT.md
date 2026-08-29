# 04 — Extension + Registration Contract

MODE: ARCHITECTURE DECISION ONLY.

Mục tiêu: thêm hoặc chuyển một trang Admin phải là việc **domain-local**, không
phải sửa nhiều danh sách trung tâm.

---

## 1. Quyết định nền: PORT, không thiết kế mới

Repo đã có một hợp đồng đăng ký/điều hướng **đang chạy production, có test chốt**
ở khu `/developers` (`01` §6). Bốn cấu trúc của nó, tại
`server/routes/developer/_chung.py`:

| Cấu trúc | Dòng | Vai trò |
|---|---|---|
| `SECTIONS` | `:132` | `khoá → href → nhãn`. **Mọi** trang phải có một dòng |
| `NHOM_NAV` | `:176` | nhóm → các khoá lên thanh bên |
| `CHA_CUA` | `:184` | mục con → mục cha (để cha sáng) |
| `MUC_CON` | `:198` | mục cha → dải mục con hiện trong trang |

`test_303` chốt trần 12 mục cho `NHOM_NAV`; `test_300` chốt danh sách trang công
khai **cả hai chiều**.

**Chốt: Admin dùng lại đúng bốn cấu trúc này**, đặt tại
`server/routes/admin/_chung.py`.

**Vì sao không thiết kế cái mới**, dù prompt 04 cho phép:
1. Nó đã trả giá học phí rồi (bình luận `_chung.py:154–175` ghi lại vì sao 16 mục
   phẳng là sai và vì sao hạ mục ≠ xoá route — đúng hai bài học Admin đang cần).
2. Hai khu dùng **một** khuôn thì người thứ ba đọc một lần là hiểu cả hai.
3. Prompt 00 cấm tạo abstraction chỉ giảm trùng lặp trên giấy. Một khuôn thứ hai
   cho cùng một việc chính là thứ đó.

**Khác biệt duy nhất so với `/developers`:** không bọc nhãn bằng `N_()`. Admin
hôm nay là tiếng Việt cứng (`admin.py:103` `_ADM_NAV`) và không có yêu cầu đa ngữ.
Thêm i18n là mở rộng phạm vi, không phải port.

---

## 2. Hợp đồng — `server/routes/admin/_chung.py`

```
SECTIONS = (
  (khoá, href, nhãn), …          # mọi trang, kể cả trang không lên nav
)
NHOM_NAV = ( (nhãn_nhóm, (khoá, …)), … )   # trần 6 mục cha
CHA_CUA  = { khoá_con: khoá_cha, … }        # BẮT BUỘC cho cả CTX và HIDDEN
MUC_CON  = { khoá_cha: ((khoá, nhãn_trong_ngữ_cảnh), …), … }  # trần 6/miền
```

**Ba luật bắt buộc**

**R1 — `SECTIONS` là nguồn duy nhất.** `_ADM_NAV` (`admin.py:103`),
`admin_api.NAV` (`admin_api.py:1883`) và 5 thẻ `<a>` hardcode trong
`admin_templates/sqladmin/base.html:54–59` đều **bị thay**, không phải bị bổ sung.
Sau C0, `grep -n "_ADM_NAV\|^NAV = " server/` phải rỗng.

**R2 — route CTX/HIDDEN vẫn phải có dòng.** Route không lên thanh bên vẫn cần một
dòng ở `SECTIONS` + một dòng ở `CHA_CUA`; nếu không, mở `/admin/api-kill-switch`
sẽ không mục nào sáng. Đây là 12 route hôm nay đang thiếu chính xác điều đó
(`02` A-03).

**R3 — trần là test, không phải lời khuyên.** `len(NHOM_NAV các mục) ≤ 6` và
`len(MUC_CON[x]) ≤ 6`. Vượt trần = gate đỏ. Khuôn: `test_303`.

---

## 3. Đăng ký view

Giữ nguyên cơ chế sqladmin (`admin.add_view`) — prompt cấm framework mới, và
`BaseView`/`@expose` đang chạy tốt. Việc cần đổi chỉ là **ai giữ danh sách**.

| Hôm nay | Sau C0 |
|---|---|
| `admin.add_view(X)` × 19 viết tay ở `admin.py:1364–1387` | một vòng lặp trên `AREAS` |
| `from server.admin_api import VIEWS` rồi lặp | `admin_api` tự khai area của nó |
| `admin.py` import `NAV` từ `admin_api` (phụ thuộc ngược — `02` C-03) | miền → registry, không có chiều ngược |

Hình dạng tối thiểu (khái niệm, không bắt buộc class này):

```
# server/routes/admin/_chung.py
AREAS = (KHACH_HANG, TAI_CHINH, API_PLATFORM, VAN_HANH, HE_THONG)
# mỗi area: .sections .nhom_nav .cha_cua .muc_con .views
```

⛔ **Không** dynamic plugin discovery, **không** entrypoint scanning, **không** DI,
**không** reflection. Danh sách `AREAS` viết tay là **đúng** — nó là một tuple
năm phần tử đọc một giây, không phải một cơ chế.

---

## 4. Trang Tổng quan `/admin/` — cơ chế (FACT + chốt)

**FACT.** `/admin/` đã có chủ: sqladmin đăng ký `Route("/", endpoint=self.index,
name="index")` (`sqladmin/application.py:391`) và `index` render
`sqladmin/index.html` (`:430`). Docstring của chính nó ghi:
*"Index route which can be overridden to create dashboards."*

**Chốt.** Kế thừa `Admin` và ghi đè `index` để trả trang Tổng quan trong vỏ admin
của ta.

**Vì sao không dùng hai phương án kia:**
- *Thêm `server/admin_templates/sqladmin/index.html`* → trang sẽ render trong vỏ
  Tabler của sqladmin, tức Tổng quan là trang duy nhất khác vỏ mọi trang khác.
- *Đặt Overview ở `/admin/tong-quan` rồi redirect `/admin/`* → thêm một redirect
  mà `03` §4 đã chốt là 0.

⚠️ **Phải xác minh bằng thực nghiệm ở C0**, không phải bằng suy luận: dựng app,
`GET /admin/` với phiên admin, khẳng định trả vỏ mới. Nếu ghi đè không ăn (thứ tự
đăng ký route), quay lại phương án `/admin/tong-quan` và **sửa `03` §4 trước**.

---

## 5. Cổng nội bộ hoá thay đổi — chứng minh bằng 3 kịch bản

Yêu cầu prompt 04: chứng minh thêm trang là domain-local.

| Kịch bản | Hôm nay | Sau hợp đồng |
|---|---|---|
| Thêm một trang Tài chính | 3 chỗ: class + `_ADM_NAV` + `add_view` — **2 trong đó ở `server/admin.py` trung tâm** | 2 chỗ, **cùng một tệp miền**: class + dòng `SECTIONS`/`MUC_CON` của area Tài chính |
| Thêm một trang API Operations | 3 chỗ: class + `VIEWS` + `NAV` | 2 chỗ, cùng tệp miền |
| Thêm một thao tác Provider | 3 chỗ, cộng khả năng phải sửa tay `sqladmin/base.html` | 2 chỗ, cùng tệp miền |

**Sửa tệp trung tâm (`server/routes/admin/_chung.py`): 0** — trừ khi thêm cả một
**miền mới**, khi đó thêm đúng một phần tử vào `AREAS`. Đó là đúng lúc nên buộc
người ta dừng lại suy nghĩ.

**Nav drift: không thể xảy ra** — một trang không có dòng `SECTIONS` thì không có
href để render; một dòng `SECTIONS` trỏ route không tồn tại bị test bắt (chốt hai
chiều, khuôn `test_300`).

---

## 6. Điều KHÔNG thuộc hợp đồng này

- Không đổi định danh DB/domain (`ApiKey`, `identity` của sqladmin, tên bảng).
  `02` A-04 đổi **nhãn hiển thị**, không đổi mã.
- Không đụng `server/routes/developer/_chung.py`. Hai khu **dùng chung khuôn**,
  không dùng chung dữ liệu.
- Không đụng `.app-side` (`ltt.css:629`) — dùng chung `/developers` + `/vps`
  (`01` §8).

---

## 7. Điều kiện ra

- [ ] `SECTIONS` phủ **hết** 31 route + 3 URL mới + các URL SQLAdmin cần nav
- [ ] `CHA_CUA` phủ hết route CTX/HIDDEN
- [ ] `NHOM_NAV` ≤ 6 mục cha; `MUC_CON[x]` ≤ 6
- [ ] test chốt trần + chốt hai chiều `SECTIONS` ↔ route thật
- [ ] `grep "_ADM_NAV\|^NAV = " server/` rỗng sau C0
- [ ] cơ chế `/admin/` đã xác minh **chạy thật**, không phải suy luận

---

**STOP.** Bước tiếp: `05_PAGE_CONTRACT_MATRIX.md`.
