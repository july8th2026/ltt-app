# 25+26 — ĐỀ XUẤT NODE SDK & HỢP ĐỒNG THI HÀNH (pha F, đóng)

> `26_EXECUTION_STATE_MACHINE` đã nằm ở `23_24 §5` (máy trạng thái là một phần
> của lược đồ). Tài liệu này hoàn tất phần còn lại của pha F: **hợp đồng khai
> báo một node**, và chốt `Q8`.
>
> **Nguyên tắc nền, không thương lượng:** `WF-705` — **SDK là phần MỞ RỘNG của
> `AppManifest`/`ToolSpec`, không phải một registry thứ hai.** Dự án này đã trả
> giá nhiều lần cho mô hình hai nguồn chân lý.

---

## 1. `ToolSpec` HÔM NAY ĐÃ ĐÚNG Ở ĐÂU

Trước khi thêm, ghi lại thứ **không được đụng** (`21_22`: KEEP #1, #25):

| Đã có | Vì sao đúng |
|---|---|
| `params_schema` / `returns` | cổng vào/ra có kiểu, do app khai |
| `job_type` + `job_type_by` + `job_type_lanes` | **làn theo tham số** — đo được 2026-08-29: đường API xin 12.000 MB cho `preset=fast` vốn chỉ ăn 848 MB |
| `admission_resource` + `admission_slots` | slot tài nguyên dùng chung |
| `api_exposed` + `api_contract` | ba cổng độc lập, fail-closed |
| `customer_visible` | soft-retire, không xoá capability |
| `tuy_chon_dong` | enum động **theo người dùng** — không hệ nào trong 7 kho có |
| `sync_executor` | tham chiếu dotted, resolve lúc CẦN |

⭐ **`tuy_chon_dong` đáng nhắc riêng:** ba cơ chế enum động của các kho khác
(`model_ref`, `source`, `depends_on`) đều **thuần tiến trình** — không cái nào
biết *người dùng là ai*. LTT có. Đây là thứ đi trước ngành, không phải đi sau.

---

## 2. SÁU TRƯỜNG THÊM VÀO `ToolSpec`

Mỗi trường trỏ về một bằng chứng cụ thể, không phải một ý tưởng.

### 2.1 `type_version` — 🔴 lỗ hổng im lặng

```python
type_version: int = 1   # tăng khi params_schema/returns đổi KHÔNG tương thích
```

**Bằng chứng:** Activepieces ghim `pieceName` **+** `pieceVersion` ngay trong
node (`04 §9`), và họ có **10.077 connector** — quy mô mà "quên ghim version"
trở thành thảm hoạ.

**Lỗ ở LTT hôm nay (`G05`):** node ghim `tool.name`, **không** ghim version.
Đổi `params_schema` của một tool ⇒ mọi `workflow_version` đã publish trỏ tới nó
**đổi ý nghĩa âm thầm**. Không lỗi nào báo.

**Cưỡng chế:** `workflow_version_node` lưu `(node_type, type_version)`; validator
từ chối chạy version ghim `type_version` không còn tồn tại, kèm thông điệp nói rõ
tool nào và bản nào.

### 2.2 `side_effect` — ⭐ chỗ neo của toàn bộ mô hình bảo đảm

```python
side_effect: str = "external"     # "none" | "external" | "irreversible"
```

**Bằng chứng:** Temporal (`10 §1.2`) — bảo đảm là **hợp đồng đặt lên mã**, không
phải tính năng của hệ:

> *"activity code must either be idempotent or non-retryable
> (i.e. at least once or at most once)"*

**Ba giá trị, ba hành vi khôi phục khác nhau:**

| | Nghĩa | Khi attempt thành `ABANDONED` (provider có thể đã nhận) |
|---|---|---|
| `none` | thuần tính toán | **thử lại tự do** |
| `external` | gọi provider, kết quả đọc lại được | thử lại **sau khi kiểm** bằng `idempotency.key_fields` |
| `irreversible` | gửi mail, tạo VPS, ghi bên ngoài | ⛔ **KHÔNG BAO GIỜ tự thử lại** — chuyển terminal, báo người |

🔴 **Đây là phần LTT đang thiếu và đã đo được là cần:** `AmbiguousProviderError`
xảy ra **10 lần / 28 ngày** (`01 §A.4`). Hôm nay `mark_ambiguous()` xử lý **mọi
job như nhau**. Nhưng `vps.provision` (đã tạo máy thật, tính tiền thật) và
`image.generate` (chỉ tốn một lượt gọi) **không cùng loại rủi ro**.

### 2.3 `idempotency` — khoá tất định do app khai

```python
idempotency: dict = {}    # {"key_fields": ("prompt", "model", "seed")}
```

Nền tảng dựng `dedupe_key` từ các trường app chỉ định, thay vì băm **toàn bộ**
params. Vì sao cần: một tham số như `request_id` hay `callback_ts` lọt vào khoá
sẽ làm khử trùng **không bao giờ khớp**.

Và nó **sửa luôn cache hiện tại** (`01 §5.7`, `G31`): `_cached_result()` hôm nay
so sánh **params bằng nhau tuyệt đối** rồi quét 50 job — nghĩa là một tool có
`seed` ngẫu nhiên nằm ngoài params sẽ **trả lại kết quả cũ cho khách**.

### 2.4 `mock` — điều kiện để test được, không phải tiện nghi

```python
mock_result: Optional[Callable[[dict], dict]] = None
```

**Bằng chứng:** Windmill đặt `mock: {enabled, return_value}` **trong lược đồ
công khai của flow** (`07+08 §2.2`), không trong bộ test — họ coi *"chạy thử
workflow mà không chạm bước đắt tiền"* là **năng lực sản phẩm**.

🔴 **Với LTT đây là điều kiện cần, không phải tuỳ chọn.** `F4`: một node có thể
là **20 phút A100**. Không có `mock`, một khách muốn thử workflow 8 bước phải
đốt **tám lượt GPU** — và **ta** cũng không test được `M6`/`M7` (chaos, ForEach
100 phần tử) mà không đốt tiền thật.

### 2.5 `resource` — gom bốn thứ đang rải rác

```python
resource: dict = {}
# {"class": "gpu", "vram_min_mb": 12000, "slots": 1, "est_duration_s": 900}
```

Hôm nay bốn giá trị này nằm ở **bốn chỗ khác nhau** trong `AppManifest`:
`gpu_vram_mb{}` · `max_runtime_s{}` · `cho_tai_nguyen_s{}` · `so_lan_thu{}` —
tất cả khoá theo `job_type`, tách rời khỏi `ToolSpec` khai ra job đó.

⭐ **`est_duration_s` là trường MỚI và nó phục vụ `WF-202`:** scheduler không
xếp một việc 20 phút vào chỗ vừa nhả ra bởi một việc 5 giây. Hôm nay LTT có số
đo cho đúng vấn đề này (`AppManifest.cho_tai_nguyen_s`: job 5 giây mất **75 %
thông lượng** vì hằng số 20 giây) nhưng chỉ dùng nó cho **giãn cách thử lại**,
không dùng để **xếp chỗ** (`G28`).

### 2.6 `timeout_expr` — trần theo tham số, không phải hằng số

```python
timeout_expr: str = ""    # vd "duration_s * 30 + 120"; rỗng ⇒ dùng resource/mặc định
```

**Bằng chứng:** Windmill cho `timeout` là `InputTransform` (biểu thức).
**Lý do ở LTT:** video 5 giây và video 60 giây đang chung một trần
`max_runtime_s` tĩnh ⇒ hoặc trần quá rộng (job treo giữ slot lâu), hoặc quá chặt
(job dài bị giết oan).

⚠️ **Ràng buộc `Q5`:** biểu thức chỉ được dùng **tập toán tử cố định** trên
chính `params` của node — số học và so sánh, **không** truy cập kết quả bước
khác, **không** gọi hàm ngoài. Nó phải tính được **lúc validate**, vì `WF-501`
cần trần chi phí trước khi chạy.

---

## 3. 🔴 CHỐT `Q8` — `AiTransform`: **KHÔNG, ở dạng Windmill. CÓ, ở dạng bị chặn.**

Windmill có (`07+08 §2.5`):

```yaml
AiTransform:
  description: Value resolved by the AI runtime for this input.
               The AI engine decides how to satisfy the parameter.
```

**Vì sao dạng nguyên bản phải từ chối:** nó phá **ranh giới bất khả xâm phạm số
1** (`02 §1.3`) — *"chi phí tối đa phải tính được TRƯỚC khi chạy, tất định"*.
Nếu LLM chọn `model` hoặc `duration_s` lúc chạy thì **không tồn tại** một con số
trần để giữ chỗ. Và `WF-501` là **thứ duy nhất trong 41 yêu cầu mà không kho nào
trong bảy kho có** — bỏ nó là bỏ tài sản riêng của LTT.

**Dạng nhận được — `ai_choice`, ba ràng buộc:**

```python
# trong params_schema của một trường:
{"type": "enum",
 "values": ["nhanh", "can_bang", "chat_luong"],
 "ai_choice": True}          # ⭐ LLM được CHỌN, trong tập ĐÃ KHAI
```

1. **Tập hữu hạn, khai tĩnh.** LLM chọn *trong* tập, không sinh giá trị mới.
2. **Trần chi phí tính theo giá trị ĐẮT NHẤT trong tập.** Báo giá vẫn tất định;
   chi phí thật ≤ trần, và phần dư được hoàn qua `budget.settle` như mọi lượt.
3. **Chỉ cho `enum` và `model_ref`.** Không cho `int`/`number` (miền vô hạn ⇒
   không có "giá trị đắt nhất").

⭐ **Điều này giữ đúng `WF-804`:** LLM **không** điều khiển luồng, nó điền một ô
trong một tập ta đã duyệt. Đồ thị vẫn tất định, trần vẫn tính trước.

`HIGH` — quyết định có lập luận; đối chứng Windmill cho hình dạng, ranh giới
`WF-501` cho giới hạn.

---

## 4. HỢP ĐỒNG NODE ĐẦY ĐỦ

```python
@dataclass(frozen=True)
class ToolSpec:
    # ── ĐÃ CÓ, KHÔNG ĐỔI ─────────────────────────────────────────
    name: str                    # "<domain>.<action>"
    job_type: str
    description: str
    params_schema: dict          # + hỗ trợ "ai_choice" trên enum/model_ref
    returns: dict
    verifiable: tuple = ()
    customer_visible: bool = True
    api_exposed: bool = False
    api_contract: dict = field(default_factory=dict)
    admission_resource: str = ""
    admission_slots: int = 0
    sync_executor: str = ""
    tuy_chon_dong: dict = field(default_factory=dict)
    job_type_by: str = ""
    job_type_lanes: dict = field(default_factory=dict)

    # ── THÊM CHO WORKFLOW V2 ─────────────────────────────────────
    type_version: int = 1                      # §2.1 — ghim vào node
    side_effect: str = "external"              # §2.2 — none|external|irreversible
    idempotency: dict = field(default_factory=dict)   # §2.3 — {"key_fields": (...)}
    mock_result: Optional[Callable] = None     # §2.4 — chạy thử không tốn tiền
    resource: dict = field(default_factory=dict)      # §2.5 — class/vram/slots/est_duration_s
    timeout_expr: str = ""                     # §2.6 — biểu thức trên params
```

**Bốn tính chất giữ nguyên:**

1. **Bản khai bằng DỮ LIỆU**, không phải hàm — registry **kiểm được lúc nạp**.
   `job_type_lanes` đã chọn đường này có chủ ý, và lý do ghi trong `registry.py`:
   *"một hàm thì không kiểm được gì cho tới khi nó chạy — và chỗ nó chạy là chỗ
   tiêu tiền của khách."* Áp cho cả sáu trường mới.
2. **Thêm trường không phá app cũ** — mọi trường có mặc định.
3. **Nền tảng không biết tên app nào.**
4. **App khai, nền tảng quyết** — node **không** chọn GPU, không biết host,
   không biết provider nào phục vụ.

### 4.1 Registry phải kiểm gì thêm lúc nạp

| Kiểm | Từ chối khi |
|---|---|
| `side_effect ∈ {none, external, irreversible}` | giá trị lạ |
| `idempotency.key_fields ⊆ params_schema` | trỏ trường không tồn tại |
| `resource.class` khai kèm `vram_min_mb` khi `= "gpu"` | thiếu |
| `timeout_expr` chỉ dùng tên trong `params_schema` + toán tử cho phép | vượt phạm vi |
| `ai_choice` chỉ trên `enum`/`model_ref` **có `values`** | trên `int`/`number`, hoặc enum không có `values` |
| `mock_result` trả về khớp `returns` | *(chỉ kiểm được lúc gọi — có test riêng)* |

---

## 5. NODE KHÔNG SINH JOB (`WF-206`, `G15`)

Bảy loại node điều khiển **không** đi qua hàng đợi, **không** tốn credit, nhưng
**có** `node_run` và snapshot (để quan sát + bền vững):

```
Input · Const · Router · Join · Delay · Approval · Subworkflow · Collect
```

**Vì sao là yêu cầu, không phải tiện nghi:** `ToolSpec.job_type` hôm nay **bắt
buộc**. Không có đường này thì mỗi lần rẽ nhánh phải giả trang thành một job —
một vòng hàng đợi, một lượt claim, một dòng sổ tiền bằng 0. Với mô hình snapshot
(`23_24 §4.2`) đó là **hàng rác nhân theo số nhánh**.

Chúng khai bằng một `NodeTypeSpec` riêng ở `platform_core` (nền tảng sở hữu, vì
chúng không thuộc app nào), cùng hình dạng cổng/kiểu như `ToolSpec`.

---

## 6. MỘT NGUỒN LUẬT NỐI DÂY (`WF-703`, `G39`) — chốt cơ chế

Hôm nay luật kiểu viết tay **hai nơi, hai ngôn ngữ**: `connectionAllowed()` (TS)
và `validator` (Python), **đã lệch**.

**Cơ chế chốt:** server là nguồn; client **hỏi**, không **chép**.

```
GET /agent/api/palette   →  { tools: [...],
                              port_types: [...],           ← bảng kiểu
                              coercions: [["T","T[]"]] }   ← luật ép kiểu DUY NHẤT
```

Client dựng `connectionAllowed()` **từ dữ liệu này**, không hardcode. Kèm một
test đối chiếu (`M9`): với mọi cặp (cổng ra, cổng vào) trong palette, quyết định
của client và server **trùng khớp 100 %**.

⇒ Giải luôn `G40` (frontend đang biết tên tool cụ thể trong
`presentationAdapter.ts`): modality/nhãn/tier chuyển thành **trường trong
`ToolSpec`**, client đọc dữ liệu. Backend đã cấm biết tên app và **có test**
(`test_60`, `test_147`); frontend sẽ có bánh cóc tương đương.

---

## 7. HỆ KIỂU CỔNG (`WF-701`, `G37`)

Hôm nay 13 kiểu tham số gộp còn 9 kiểu cổng; `int` · `number` · `bool` · `dict`
**đều thành `json`** ⇒ validator không phân biệt được cổng số với cổng object.

```
Nguyên thuỷ : text · number · integer · boolean · json · file
Media       : image · video · audio · document
Tham chiếu  : model_ref · connection_ref · artifact_ref · workflow_ref · secret_ref
Tập hợp     : T[]  (mọi T ở trên)
```

**Ép kiểu — đúng MỘT luật:** `T → T[]` (bọc). Mọi ép kiểu khác **từ chối**.
Muốn `number → text` thì đặt một node chuyển đổi — nó **hiện trên đồ thị**,
người ta thấy được.

**Cardinality** (`WF-702`, `G38`) — mỗi cổng khai:
```python
{"type": "image[]", "required": True, "multiple": True, "variadic": False}
```
`multiple` = nhận **nhiều cạnh**; khác hẳn `image[]` = nhận **một mảng**. Hôm
nay hai thứ này không phân biệt được.

---

## 8. PHA F ĐÓNG — ĐỐI CHIẾU 41 YÊU CẦU

| Nhóm | Đã có bản thiết kế |
|---|---|
| Đồ thị `WF-101`–`107` | ✅ `23_24 §4.1` — edge là thực thể, 3 `kind`, version có hash |
| Thi hành `WF-201`–`209` | ✅ `23_24 §6` — 8 hệ con, `finally`, `behavior` tràn |
| Bền vững `WF-301`–`305` | ✅ `23_24 §4.2` — snapshot chỉ-thêm |
| Waitpoint/tài nguyên `WF-401`–`405` | ✅ `23_24 §4.3` + §2.5 ở đây |
| Tiền `WF-501`–`504` | ✅ giữ nguyên + `finally` + `ai_choice` bị chặn |
| Artifact `WF-601`–`604` | ✅ `23_24 §4.4` |
| SDK/kiểu `WF-701`–`706` | ✅ **tài liệu này** |
| Trigger/API/Agent `WF-801`–`805` | ✅ `23_24 §4.5` + middleware cạnh |
| Bảo mật `WF-901`–`905` | ✅ middleware cạnh cho `WF-903`; phần còn lại KEEP |

**Bốn câu hỏi mở còn lại → nay còn MỘT:**

| # | Trạng thái |
|---|---|
| `Q1` `Q3` `Q5` `Q7` | ✅ chốt ở `12_19` |
| `Q2` `Q4` | ✅ chốt ở `23_24` |
| `Q8` | ✅ **chốt ở đây** — `ai_choice`, ba ràng buộc |
| `Q6` | ⬜ **chờ một số đo** — bao nhiêu `AgentWorkflow` bản nháp trong CSDL production |

⭐ `Q6` **không chặn** thiết kế. Theo luật `CLAUDE.md` 07/09 (chưa có khách), câu
trả lời đã rõ về hình dạng: **không có lớp tương thích runtime**; nếu có bản
nháp thì viết **một script chuyển một lần**. Số đo chỉ quyết định script đó có
cần viết hay không.

---

## 9. CÒN LẠI: PHA G VÀ H

```
27  MIGRATION_STRATEGY      ← thu hẹp mạnh: không có runtime để di trú
28  IMPLEMENTATION_ROADMAP  ← 5 đợt đã suy ra ở 21_22 §22.4
29  RISK_REGISTER
30  FINAL_ARCHITECTURE_DECISION  ← so 5 phương án A–E; ADOPT=0 đã loại A, làm yếu B
    ARCHITECTURE_DECISION_RECORD
00  EXECUTIVE_SUMMARY       ← 20 câu của đề bài §25, viết CUỐI CÙNG
```

---

*Không sửa mã sản phẩm LTT. `ToolSpec` mở rộng trong tài liệu này là **đề xuất**;
chưa dòng nào được viết vào `platform_core/registry.py`.*
