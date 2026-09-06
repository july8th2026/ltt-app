# B4 — Ghi nhớ (memory): CRUD + ba tầng

> Đo ngày 06/09/2026. Mọi con số trong §0 lấy từ **GitHub API và mã nguồn tải
> về**, không từ trí nhớ — xem `scratchpad/b4/`.

---

## §0 — Đối chiếu cộng đồng (BƯỚC BẮT BUỘC, không phải nguyên tắc)

### §0.1 Đo bốn kho, và một kho hoá ra không phải thứ tôi tưởng

| Kho | Sao | Đẩy gần nhất | Giấy phép | Ghi chú |
|---|---:|---|---|---|
| `mem0ai/mem0` | 64.777 | 2026-09-04 | Apache-2.0 | sống, là kho chính |
| `open-webui/open-webui` | 151.100 | 2026-09-05 | **NOASSERTION** | sống, **không chạm mã** |
| `getzep/zep` | 4.890 | 2026-09-03 | Apache-2.0 | sống |
| `letta-ai/letta` | 24.631 | 2026-08-23 | Apache-2.0 | 🔴 **rỗng — xem dưới** |

🔴 **`letta-ai/letta` KHÔNG chứa mã nguồn.** Cây gốc có đúng **15 mục**, tất cả
là tệp meta (`README`, `LICENSE`, `PRIVACY`, `TERMS`, `.github/`). README nói
thẳng:

> *"This repository now serves as a landing page… The retired Letta V1 server
> source is preserved on the `archive` branch."*

Mã sống ở `letta-ai/letta-code`: **3.217** sao, đẩy 2026-09-06, Apache-2.0, và
**viết bằng TypeScript**.

⛔ **Đây là một lỗi trong chính `09_PLAN_TONG_LAP_GHEP.md` của tôi.** Ở đó tôi
   xếp letta cạnh mem0/zep và loại nó vì *"cần kho vector"*. Kết luận đúng,
   nhưng **căn cứ sai**: 24.631 sao và ngày đẩy 2026-08-23 là số của một **trang
   giới thiệu**, không phải của một sản phẩm. Nếu tôi đã chọn "lắp letta" thì
   phép đo ấy sẽ không cản được gì.

⭐ Đúng hình dạng của bẫy đã ghi trong bộ nhớ: **đọc thứ đại diện thay vì đọc
   thứ thật**. Một `full_name` là thứ đại diện cho một kho; cây tệp mới là kho.
   ⇒ Luật bổ sung cho §0 từ nay: **đếm mục trong cây gốc** trước khi trích số
   sao, vì một kho rỗng vẫn trả về số sao rất đẹp.

### §0.2 mem0 — thứ đáng mượn KHÔNG phải phân loại

Tải `mem0/configs/prompts.py` (1.062 dòng). Đọc thật thì:

**a) Ba loại ghi nhớ của mem0 chia theo CHỦ THỂ, không theo nội dung:**
`USER_MEMORY_EXTRACTION_PROMPT` · `AGENT_MEMORY_EXTRACTION_PROMPT` (ghi nhớ *về
chính trợ lý*) · `PROCEDURAL_MEMORY_SYSTEM_PROMPT` (nhật ký hành động của agent).

**b) Bảy nhóm nội dung** (sở thích · chi tiết cá nhân · kế hoạch · dịch vụ ·
sức khoẻ · nghề nghiệp · linh tinh) — đây là một bài **phân loại**, không phải
một bài **quyền**.

⛔ **Sửa kế hoạch tổng.** `09_PLAN_TONG` §3 B4 viết: *"mượn phân loại kiểu ghi
   nhớ của mem0 (fact / preference / episode)"*. Đo mã: **bộ ba ấy không tồn
   tại** trong mem0. Tôi đã nhớ một bộ ba quen tai và viết nó ra như một phép
   đo. Câu đó sai và được thay bằng §0.2 này.

**c) ⭐ Thứ thật sự đáng mượn: `DEFAULT_UPDATE_MEMORY_PROMPT` — BỐN phép, không
phải một.**

```
1. Add        thông tin mới        -> thêm
2. Update     đã có nhưng KHÁC HẲN -> sửa
3. Delete     MÂU THUẪN với cái cũ -> xoá
4. No Change  đã có rồi            -> không làm gì
```

🔴 Phép số 3 là toàn bộ giá trị. Một kho ghi nhớ **chỉ biết thêm** thì tích luỹ
mâu thuẫn: *"khách thích cà phê"* nằm cạnh *"khách bỏ cà phê"*, và model càng
dùng lâu càng trả lời tệ đi. Đó là lỗi **im lặng và tăng dần** — loại đắt nhất,
vì không có ngày nào nó hỏng để ai đó đi sửa.

### §0.3 Open WebUI — mượn HÀNH VI, không chạm mã (NOASSERTION)

Tải `backend/open_webui/models/memories.py` (268 dòng). Bốn điều đáng mượn:

1. **Lược đồ nhỏ đến bất ngờ**: `id · user_id · type · path · content · meta ·
   created_at · updated_at`. Không embedding, không điểm số, không TTL.
2. **`type` là `Literal['user','context']`** — tức *ai viết* (người gõ tay / hệ
   suy ra), **không phải** *nói về cái gì*. Hai trục hoàn toàn khác nhau, và
   gộp chúng là lỗi thiết kế đầu tiên ai cũng mắc.
3. **`apply_memory_operations`** nhận một **lô** `add / replace / move /
   remove` — cùng hình dạng bốn phép của mem0, được viết thành mã thật.
4. ⭐ **Không có oracle tồn tại**: sai chủ sở hữu và không tồn tại đều ném
   `Memory not found`. Một API phân biệt hai ca đó là một API cho phép dò id
   của người khác.

⛔ Giấy phép `NOASSERTION` + điều khoản thương hiệu ⇒ **đọc hành vi, không chép
   một dòng mã nào**.

### §0.4 Ngưỡng chấp nhận theo §0 mức hai — nơi phụ thuộc CHẠY

| Ứng viên | Chạy ở đâu nếu lắp | Phán quyết |
|---|---|---|
| `mem0` | **runtime sản xuất** | ⛔ loại — kéo `posthog` (gọi bên thứ ba) + kho vector, mà `pgvector` không có |
| `zep` | dịch vụ thường trú | ⛔ loại — thêm một tiến trình tranh 10 lõi với bộ test |
| `letta-code` | — | ⛔ loại — **TypeScript**, không phải lựa chọn cho backend này |
| mem0 *bốn phép* | **đặc tả** | ✅ **mượn** — ngưỡng gần như bằng 0 |
| OWUI *lược đồ + hành vi* | **đặc tả** | ✅ **mượn** |

⇒ B4 **tự viết mã, mượn đặc tả**. Và lần này câu đó có căn cứ: ba ứng viên bị
loại bởi ba lý do **khác nhau**, không phải bởi một sở thích chung.

---

## §1 — Bài toán thật: quyền và giao diện, không phải ngữ nghĩa

mem0/zep giải bài *"tìm lại đúng mẩu ghi nhớ trong hàng chục nghìn mẩu"* — bài
đó cần embedding. Bài của ChatLTT là:

> Người dùng **nhìn thấy** máy nhớ gì về mình, **sửa** được, **xoá** được, và
> biết **vì sao** nó nhớ.

Đo kho hiện tại: `grep -rn "ghi_nho\|memory\|GhiNho" apps/chatltt --include=*.py`
→ **không một dòng nào**. Đây là đất trống thật.

Điểm chèn cũng đã đo được: `apps/chatltt/services/luot.py:64 dung_ngu_canh()`
dựng `messages` **thuần từ cây hội thoại** — hiện không có tin `system` nào được
tiêm. Ghi nhớ sẽ vào đúng chỗ đó, và **chỉ** chỗ đó.

---

## §2 — Sáu quyết định phải chấm TRƯỚC khi viết mã

### D1. Ai viết ghi nhớ — **người dùng gõ, và model GỌI TOOL**. Không tự trích ngầm.

Ba đường:

| đường | chi phí | có thấy được không |
|---|---|---|
| (a) LLM tự trích sau **mỗi** lượt (đường mem0) | **một lượt gọi model NỮA mỗi lượt** | không |
| (b) chỉ người dùng gõ tay | 0 | có, nhưng gần như không ai gõ |
| (c) **model gọi tool `noi_bo.ghi_nho`** | 0 thêm — nằm trong lượt khách đã trả | **có**, hiện ra ở khối `tool_call` |

⇒ **(b) + (c)**. Loại (a) vì nó là một **khoản thu ngầm**: khách hỏi một câu và
bị tính hai lượt model, mà cái thứ hai họ không yêu cầu và không nhìn thấy. Đó
đúng là hình dạng lỗi *"sàn làm tròn là một tầng khác với bảng giá"* đã ghi
trong bộ nhớ — bảng giá đúng mà tiền thu ra sai.

⭐ Và vòng lặp tool **đã có sẵn** (`dieu_phoi.py`, P05). (c) không phải xây thêm
   hạ tầng; nó là một mục trong `KHOI` của `tool_noi_bo.py`.

### D2. Ba tầng là **phạm vi ÁP DỤNG**, không phải phân loại nội dung

```
nguoi_dung   ap cho MOI hoi thoai cua nguoi ay
du_an        ap trong mot project           (B5 — cot nullable, chua bat)
hoi_thoai    chi ap trong mot hoi thoai
```

Bảy nhóm nội dung của mem0 (§0.2b) **không** vào lược đồ: chúng là nhãn để hiển
thị, và nhãn thì để `meta`. Cột trong bảng chỉ dành cho thứ có **ràng buộc**.

### D3. ⛔ Model KHÔNG được chọn phạm vi — cùng luật `thi_hanh(boi_canh=…)` của P05

Model đề nghị *nội dung*; **bên gọi** điền `conv_id` và `user_id`. Một lượt chạy
trong hội thoại X không thể ghi nhớ cho hội thoại Y, kể cả khi model xin.

Đây không phải cẩn thận thừa: phạm vi là **quyền**, và một tham số quyền nằm
trong schema tool là một tham số kẻ tấn công điều khiển được bằng nội dung tài
liệu đính kèm — đúng kịch bản P10 phải kiểm.

### D4. Lớp chính sách **bất đối xứng**: ghi là `FREE`, quên là `DESTRUCTIVE`

`chieu_tool.LOP_CUA` mặc định trả `DESTRUCTIVE` cho tên lạ (fail-closed). Khai tay:

| tool | lớp | vì sao |
|---|---|---|
| `noi_bo.ghi_nho` | `FREE` | không tốn credit, dữ liệu của chính người hỏi, **sửa lại được** |
| ~~`noi_bo.quen`~~ | — | **BỎ** — xem dưới |

🔴 **SỬA 06/09, phát hiện khi viết bước 5: model KHÔNG CÓ ĐỊA CHỈ để gọi `quen`.**

Khối ghi nhớ tiêm vào ngữ cảnh chỉ mang **chữ**, không mang `id` — cố ý, vì `id`
tốn token ở **mọi** lượt. Không có `id` thì model không `quen` được, và cũng
không `thay` được. Kế hoạch này đã khai một tool mà cơ chế của nó không tồn tại.

Hai đường sửa, cả hai đều **chưa tới lúc**:

1. tiêm `id` vào ngữ cảnh — đổi một thứ đang tối giản chỉ để phục vụ một tool
   còn chưa mở cửa;
2. `quen` theo **nội dung** thay vì theo `id` — cần một phép so khớp mà chưa có
   phép đo nào nói ta cần.

⇒ `thay` và `quen` ở lại phía **người dùng** (route ở bước 4). Đây không phải
  một hạng mục bị cắt: bài toán B4 tự nói là *"quyền và giao diện"*, còn bốn
  phép của mem0 được mượn làm **đặc tả cho KHO**. *Kho có phép nào* và *ai được
  gọi phép nào* là hai câu hỏi khác nhau, và trước hôm nay tôi trả lời chúng
  bằng một câu.

🔴 Nhưng *"sửa lại được"* chỉ đúng **nếu người dùng biết nó đã xảy ra**. Nếu khối
`tool_call` không được vẽ — mà P09 đo được rằng nó **hiện không vẽ gì cả** — thì
`FREE` là một lời nói dối. ⇒ **B4 không được bật cổng thứ tư trước P09.** Ghi
vào điều kiện bật cờ, không ghi vào một chú thích.

### D5. Trần cứng, và trần đặt **trên** nhu cầu thường

Ghi nhớ được tiêm vào **mọi lượt** ⇒ nó là một khoản thuế token **vĩnh viễn**,
không phải một lần. Không có trần thì khoản thuế ấy tăng mãi.

```
TRAN_MOI_PHAM_VI   = 50    ban ghi
TRAN_KY_TU_TIEM    = 4000  ky tu cho CA khoi ghi nho, moi luot
```

⚠️ Đặt cao hơn ca thường **một bậc**: một người dùng nặng sau nhiều tháng có
chừng 10–20 mẩu. Bộ nhớ đã ghi luật *"phanh luôn ăn tệ hơn không có phanh"* —
trần đặt **dưới** nhu cầu bình thường biến thất bại thành **mặc định**.

Đầy trần ⇒ **nói ra** (`KhoDay`), không lặng lẽ vứt mẩu cũ nhất.

### D6. Không embedding — và đó là HỆ QUẢ của D5, không phải một thoả hiệp

`pgvector` không có trên PostgreSQL 17.10 này. Nhưng lập luận đúng không phải
*"thiếu nên đành chịu"*:

> D5 chốt rằng cả kho ghi nhớ ≤ 4.000 ký tự và **được tiêm trọn vẹn**. Không có
> gì để *truy hồi* — truy hồi chỉ có nghĩa khi kho lớn hơn ngữ cảnh.

⭐ Tức trần làm kho vector **thành thừa**, chứ không phải kho vector thiếu làm
   trần **thành thoả hiệp**. Hai câu ấy dẫn tới hai kiến trúc khác nhau, và câu
   sau là câu sẽ khiến ai đó ba tháng nữa đi cài Qdrant lên máy production.

---

## §3 — Lược đồ

```
chatltt_ghi_nho
  id            uuid pk
  user_id       str  index      <- DIEU KIEN cua moi truy van, khong phai bo loc
  pham_vi       str             nguoi_dung | du_an | hoi_thoai
  muc_tieu_id   str  nullable   conv_id / project_id; NULL khi pham_vi=nguoi_dung
  nguon         str             nguoi | model        (= `type` cua OWUI)
  noi_dung      text            <= 500 ky tu / ban ghi
  meta          json nullable   nhan hien thi, id luot da sinh ra no
  created_at / updated_at
  UNIQUE (user_id, pham_vi, muc_tieu_id, noi_dung)   <- chong trung, tra "bo qua"
```

`nguon` tách người/model vì hai thứ đó có **quyền khác nhau**: người sửa được
mọi mẩu; model chỉ `replace` mẩu do chính model ghi trong cùng phạm vi.

---

## §4 — Sáu bước (2,5 ngày)

| # | Việc | Cửa |
|---|---|---|
| # | Việc | Cửa | Trạng thái |
|---|---|---|---|
| 1 | bảng `chatltt_ghi_nho` + migration `d1a7f4c9b620` (add-only) | không đổi hành vi | ✅ |
| 2 | `services/ghi_nho.py`: 4 phép, `user_id` là **điều kiện** | không | ✅ `test_830` (25) |
| 3 | tiêm vào `dung_ngu_canh()` sau cờ `LTT_CHATLTT_V3_MEMORY` | cờ **mới**, mặc định tắt | ✅ `test_831` (11) |
| 4 | route CRUD `/api/ghi-nho` + `cong_ghi_nho` **trước** `require_login` | cổng cờ | ✅ `test_832` (11) |
| 5 | tool `noi_bo.ghi_nho` (`FREE`) — **một** tool, xem D4 | cổng 4 **CÒN ĐÓNG** | ✅ `test_833` (15) |
| 6 | giao diện quản lý | sau P09 | ⏳ |

Dải test: **830–835** (dải 800–899 của H44). Đã dùng 830–833, **62 phép kiểm**.

### Ba điều kiện để bật `LTT_CHATLTT_V3_MEMORY`

1. **P09 vẽ được khối `tool_call`.** Không có nó thì `FREE` là một lời nói dối:
   *"sửa lại được"* đòi người dùng **nhìn thấy** nó đã xảy ra.
2. **Giao diện quản lý (bước 6).** Bật đường tiêm trước khi có chỗ xem/xoá là
   cho một kho ghi nhớ chạy mà chủ của nó không mở ra được.
3. **Đo lại trần 2.000 ký tự** trên 20–50 người dùng thật rồi chốt — hằng số
   hiện tại là một **neo tự suy**, và nó tự khai như vậy.

⛔ Thêm `noi_bo.ghi_nho` vào `chieu_tool.CHO_MODEL_GOI` là một bước **riêng**,
   sau cả ba điều trên. `test_833::test_CHUA_mo_cua_thu_tu` chốt sự vắng mặt ấy.

---

## §5 — Phép đo nghiệm thu (viết TRƯỚC, không viết sau)

1. **Mâu thuẫn phải xoá được**: ghi *"thích cà phê"*, rồi `thay` bằng *"bỏ cà
   phê"* ⇒ `liet_ke` trả **một** mẩu, không phải hai. (Đối chứng: bản không có
   phép `thay` phải **ĐỎ**.)
2. **Phạm vi không rò**: ghi ở hội thoại A ⇒ `dung_ngu_canh` của hội thoại B
   **không** chứa nó.
3. **Không có oracle tồn tại**: `quen` một id của người khác trả **cùng** lỗi
   với `quen` một id không tồn tại.
4. **Model không đặt được phạm vi**: schema của `noi_bo.ghi_nho` **không có**
   trường phạm vi — kiểm bằng AST, không bằng khớp chuỗi.
5. **Trần nói ra**: mẩu thứ 51 ném `KhoDay`, không âm thầm đẩy mẩu cũ ra.
6. **Cờ tắt ⇒ vô hình**: cờ tắt thì route trả **404** (không phải 303 về
   `/login`) và `dung_ngu_canh` không đổi một byte.
