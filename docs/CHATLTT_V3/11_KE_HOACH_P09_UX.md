# P09 — UX V3: vẽ được khối `tool_call`

> Đo ngày 06/09/2026. Số của §0 lấy từ GitHub API và mã tải về (`scratchpad/p09/`);
> số của §1 lấy từ **thí nghiệm chạy trên chính mã này**, không từ đọc mã.

---

## §0 — Đối chiếu cộng đồng

### §0.1 Đo kho, và áp luật mới rút ra từ B4

| Kho | Sao | Đẩy gần nhất | Giấy phép | **Mục ở cây gốc** |
|---|---:|---|---|---:|
| `assistant-ui/assistant-ui` | 12.029 | 2026-09-06 | MIT | **31** ✅ có mã thật |

⭐ Cột cuối là luật rút ra từ B4 §0.1: **đếm mục trong cây gốc trước khi trích số
sao**. `letta-ai/letta` có 24.631 sao và **15 mục toàn tệp meta** — một kho rỗng
vẫn trả về số sao rất đẹp. Lần này phép đo ấy trả lời "có mã", nên đi tiếp.

### §0.2 Bốn thứ mượn được, và cả bốn là ĐẶC TẢ (ngưỡng gần bằng 0)

Đọc `packages/core/src/types/message.ts` + `apps/docs/.../tool-fallback.tsx`.

**a) Trạng thái là một union có `requires-action` RIÊNG, không phải một `bool`.**

```ts
ToolCallMessagePartStatus =
  | { type: "requires-action"; reason: "tool-calls" | "interrupt" }
  | { type: "running" }
  | { type: "complete" }
  | { type: "incomplete"; reason: "cancelled" | "length" | "content-filter"
                                 | "error" | "other" }
```

🔴 Đây là thứ đắt nhất trong cả §0, và nó chỉ thẳng vào một lỗ ở **backend của
ta** — xem §1.

**b) `isError` TÁCH khỏi `status`.** Một tool chạy xong mà trả lỗi là
`complete` + `isError`, **không** phải `incomplete`. Hai câu khác nhau: *"nó
không chạy được"* và *"nó chạy rồi, kết quả là một lỗi"*.

**c) Bố cục năm phần, gập lại mặc định:**

```
ToolFallbackRoot        khung gap duoc
  ToolFallbackTrigger   ten tool + trang thai   <- LUON hien
  ToolFallbackContent                            <- gap lai mac dinh
    ToolFallbackArgs    doi so
    ToolFallbackResult  ket qua
```

Và trong bản mẫu streaming của họ: `if (isRunning) setIsOpen(true)` — **tự mở
khi đang chạy**, người dùng gập lại sau. Hiện khi còn quan trọng, im khi đã xong.

**d) ⭐ Câu sắc nhất, chép nguyên ý từ chú thích của họ về trường `approval`:**
phiếu duyệt mang theo **câu hỏi đặt cho người dùng**, để bộ vẽ *"hiện câu hỏi
thay vì suy ra một quyết định từ tên tool"*.

⇒ Nhãn duyệt **không** được sinh từ `ten` tool. Ta đã có `chatltt_approval` mang
báo giá; §3 chấm phần chữ.

⛔ **Không lắp mã.** `assistant-ui` là hệ React riêng với runtime, provider và
primitive của nó; frontend ChatLTT là 1.990 dòng tự viết với `kieu.ts` riêng.
Lắp nó là thay cả tầng hiển thị để lấy một thành phần. Mượn ở **mức ba**.

---

## §1 — Đo hiện trạng, và một lỗ ở BACKEND lộ ra trước

### §1.1 Giao diện: khối `tool_call` không được vẽ gì

`ThongDiepView.tsx` (290 dòng) chỉ đọc `image` · `audio` · `error` · `status`
và phần `text`. Khối `tool_call` rơi vào nhánh "khối lạ" — đúng A5, nhưng nghĩa
là **vòng lặp tool chạy mà không ai nhìn thấy**.

⚠️ `tests/KhoiLa.test.tsx` hiện **chốt rằng `tool_call` KHÔNG được vẽ**
(`expect(chu).not.toContain('tool_call')`, `not.toContain('bieu_thuc')`). Nó sẽ
đỏ ở bước 3 — và đó là bánh cóc làm đúng việc, không phải một trở ngại.

⇒ Viết lại theo luật đã ghi: **mệnh đề phải BẤT BIẾN với tập hợp**, và bản viết
lại phải **khó xanh hơn**. Mệnh đề đúng không phải *"`tool_call` không hiện"* mà:

> Khối **chưa ai định nghĩa** thì không vẽ gì; khối **đã định nghĩa** thì vẽ ra
> **câu tiếng Việt**, không bao giờ là khoá JSON thô.

### §1.2 🔴 Backend: khối không phân biệt được "ĐANG CHẠY" với "ĐÃ XONG"

Đo bằng **thí nghiệm**, không bằng đọc mã — `_them_khoi` gọi thẳng với ba bước:

```
DANG CHO JOB -> ok=True   cho_duyet=False  tom_tat=''
DA XONG      -> ok=True   cho_duyet=False  tom_tat='{"key": "a.png"}'
DA HONG      -> ok=False  cho_duyet=False  tom_tat='LOI[het_tien]: ...'
```

Nguyên nhân ở `luot_v3._them_khoi`:

```python
"ok": bool(b.ket_qua is None or b.ket_qua.ok),   # chua co ket qua => "ok"
"cho_duyet": bool(b.cho_duyet and b.ket_qua is None),
```

và `b.cho_job` **không đi vào khối chút nào**. Mà đường ấy có thật: khi
`chay_tool` trả `ChoJob`, `dieu_phoi` đặt `b.cho_job` và **xoá** `b.cho_duyet`,
rồi `DP.chay()` trả về và `_dong()` ghi khối ngay — tức khối được ghi **trong
lúc job còn chạy**.

⇒ Một lượt vẽ ảnh, ngay khi job vừa được xếp hàng, đã được tuần tự hoá thành
**"image.ltt — xong ✓"**. Hôm nay không ai thấy vì không ai vẽ nó. Ngày bắt đầu
vẽ, đó là một **lời nói dối trên màn hình**.

⛔ **Và cái bẫy phải tránh ở đây:** vẽ spinner khi `tom_tat === ''`. Nó "chạy
đúng" hôm nay, nhưng `tom_tat` rỗng là **thứ đại diện** cho "chưa có kết quả" —
một tool trả kết quả rỗng hợp lệ sẽ hiện thành đang-chạy vĩnh viễn. Sửa **sự
thật** trước, rồi vẽ.

---

## §2 — Bốn quyết định

### D1. Backend mang một trường `trang_thai` MỘT chiều, không phải ba cờ rời

Ba `bool` rời (`ok`/`cho_duyet`/+`cho_job`) cho **8** tổ hợp, trong đó chỉ 4 có
nghĩa. Một union một chiều thì mọi giá trị đều có nghĩa — đúng hình dạng
`ToolCallMessagePartStatus` của §0.2a.

```
"cho_duyet"   dang cho NGUOI bam        (b.cho_duyet)
"dang_chay"   dang cho MAY xong job     (b.cho_job)
"xong"        co ket qua, ok            (b.ket_qua.ok)
"loi"         co ket qua, that bai      (not b.ket_qua.ok)
```

⭐ Giữ `ok` lại **cho tương thích ngược**: 220 hội thoại thật có thể đã mang
khối cũ. Bộ vẽ suy `trang_thai` từ `ok`/`cho_duyet` khi trường mới vắng mặt —
và **chỉ** ở chiều đọc, không ở chiều ghi.

### D2. Gập mặc định, tự mở khi CHƯA PHẢI MỘT THÀNH CÔNG IM LẶNG

Mượn §0.2c. Xong rồi thì gập — người đọc muốn thấy **câu trả lời**, không phải
nhật ký công cụ.

⚠️ **Sửa trong lúc làm.** Vị từ ban đầu là *"còn việc"* = `cho_duyet` hoặc
`dang_chay`. `KhoiTool.test.tsx` bắt ngay: **`loi` cũng phải tự mở.** Một câu
báo lỗi nằm sau một cú bấm là một câu báo lỗi không ai đọc — người dùng chỉ
thấy *"Không chạy được"* và không bao giờ biết **vì sao**.

⇒ Vị từ đúng: chỉ một kết quả **`xong`** mới được quyền im.

### D3. Nhãn duyệt lấy từ PHIẾU, không suy từ tên tool (§0.2d)

`chatltt_approval` đã mang báo giá. Bộ vẽ hiện **câu hỏi + giá**; nó không được
dựng một câu từ `ten`.

### D4. Đối số hiện dưới dạng **cặp khoá–giá trị**, không phải JSON thô

`{"bieu_thuc": "2+2"}` đổ nguyên ra màn hình là đúng thứ `KhoiLa.test.tsx` gọi là
*"tệ hơn vỡ: nó trông như sản phẩm vốn thế"*. Khoá dịch sang nhãn tiếng Việt;
khoá chưa có nhãn thì **ẩn**, không hiện tên khoá.

---

## §3 — Sáu bước

| # | Việc | Cửa | Trạng thái |
|---|---|---|---|
| 1 | `_them_khoi` ghi `trang_thai` (4 giá trị), giữ `ok` để đọc ngược | không đổi hành vi nhìn thấy | ✅ `test_834` (9) |
| 2 | `kieu.ts`: `KhoiToolCall` + `trangThaiTool()` cho khối cũ | không | ✅ |
| 3 | Viết lại `KhoiLa.test.tsx` theo mệnh đề bất biến (§1.1) | không | ✅ |
| 4 | `KhoiTool.tsx` — Root/Trigger/Content/Args | vẽ thật | ✅ `KhoiTool.test.tsx` (19) |
| 5 | Nhãn tiếng Việt + bánh cóc phủ nhãn | vẽ thật | ✅ `test_835` (8) |
| 6 | Kiểm trên **URL công khai** (`CLAUDE.md` 5b) | đóng điều kiện #3 của `STATE.md` | ⏳ **chặn: cờ chưa bật trên production** |

Dải test: **834–835** (backend) + `frontend/chatltt/tests/KhoiTool.test.tsx`.

### Kiểm bằng trình duyệt thật (bước 5b của `CLAUDE.md`) — ĐÃ LÀM

Tiến trình riêng cổng **8198**, CSDL vứt đi, cờ V3 bật; production 8100 không bị
chạm (đo lại sau khi tắt: `/health/ready` = 200). Gieo đủ **bốn** trạng thái +
**một khối CŨ** không có `trang_thai`.

| trạng thái | màn hình | thân |
|---|---|---|
| `cho_duyet` | *Tính toán — Đang chờ bạn duyệt* | tự mở: `Phép tính 8123*4471` |
| `dang_chay` | *Vẽ ảnh — Đang chạy* | rỗng (`prompt` chưa có nhãn ⇒ ẩn) |
| `xong` | *Tìm trong tài liệu của bạn — Xong* | gập; bấm mở ra `Tìm`/`Số đoạn` |
| `loi` | *Tính toán — Không chạy được* (viền đỏ) | tự mở: `1/0` + *chia cho khong* |
| khối CŨ | *Xem ngày giờ — Xong* | đọc ngược đúng |

**0 lỗi console, mọi request 200**, bundle phục vụ là `main-Cgkwm1xA.js` — đúng
mã băm vừa build, nên đây là mã của tôi chứ không phải bản cũ trong cache.

🔴 **Và trình duyệt bắt được một lỗi bốn phép kiểm đơn vị không thấy:** tên khả
truy cập của nút là **`"Tính toánĐang chờ bạn duyệt"`** — dính liền. Hai `<span>`
cạnh nhau không có khoảng trắng, và `gap` của flexbox tách chúng trên **màn
hình** chứ không tách trong **chuỗi**. ⇒ Mắt thấy đẹp, tai nghe thấy một từ lạ.
Sửa bằng `aria-label` rời rạc + `<dl>/<dt>/<dd>` cho đối số, và ghim bằng hai
phép kiểm mới.

---

## §4 — Phép đo nghiệm thu (viết TRƯỚC)

1. **Ba trạng thái phân biệt được ở backend**: cùng thí nghiệm §1.2, ba bước ra
   ba `trang_thai` khác nhau. *(Đối chứng: bản cũ phải ĐỎ.)*
2. **Khối cũ vẫn đọc được**: một khối chỉ có `ok`/`cho_duyet` (không
   `trang_thai`) vẫn ra đúng trạng thái ở giao diện.
3. **Không khoá JSON nào lọt ra màn hình**: `bieu_thuc`, `doi_so`, `tool_call`,
   `[object Object]` đều không có trong `textContent`.
4. **Khối chưa ai định nghĩa vẫn không vẽ gì** — A5 giữ nguyên sau khi
   `tool_call` thành loại đã biết.
5. **Đang chạy thì tự mở; xong thì gập.**
6. **Nhãn duyệt không chứa tên tool thô** (`image.ltt` không xuất hiện).
