# P07 — `agents` và `skills` (hai hạng mục cuối của P07)

*Chương trình **H44**. B4 (memory) và B5 (projects) đã đóng 6/6; đây là hai
hạng mục còn lại của P07 trong `00_KE_HOACH_V3.md`.*

Ràng buộc kế hoạch tổng đã đặt sẵn cho pha này, chép nguyên vì nó quyết định
mọi thứ bên dưới:

> *"custom agents có chính sách model/tool/chi tiêu/quyền; skills theo mẫu
> `SKILL.md` [C] nhưng **LTT-native**. **Mỗi thứ ở đây là một bề mặt quyền
> mới** ⇒ mỗi thứ cần test ACL + test cách ly + test **thứ tự ưu tiên chỉ
> dẫn**."*

---

## §0 — Đối chiếu cộng đồng (đo 07/09/2026)

### §0.1 Đo kho

| Kho | Sao | Giấy phép | Đẩy gần nhất | Mục ở cây gốc |
|---|---|---|---|---|
| `anthropics/skills` | 174.895 | **None** | 2026-09-03 | **7** |
| `openai/openai-agents-python` | 29.230 | MIT | 2026-09-05 | 22 |
| `crewAIInc/crewAI` | 58.173 | MIT | 2026-09-04 | 16 |
| `microsoft/autogen` | 60.842 | CC-BY-4.0 | **2026-04-15** | — |

⛔ `autogen` **loại ngay**: 5 tháng không đẩy, và `CC-BY-4.0` là giấy phép cho
**tài liệu**, không phải cho mã — một kho mã mang giấy phép tài liệu là một câu
hỏi pháp lý không ai ở đây trả lời được.

### §0.2 🔴 Luật "đếm cây gốc trước khi trích số sao" vừa trả công lần thứ hai

Luật này ra đời ở §0 của B4. Áp vào đây:

```
anthropics/skills   174.895 sao   ->  7 muc goc
  spec/agent-skills-spec.md   ->    87 byte
  template/SKILL.md           ->   140 byte
```

**87 byte.** Toàn văn:

```
# Agent Skills Spec
The spec is now located at <https://agentskills.io/specification>
```

⇒ Kho 175 nghìn sao ấy là một **bộ sưu tập ví dụ + một con trỏ**, không phải
đặc tả. Ai trích *"theo chuẩn của kho 175k sao"* mà không mở tệp ra thì đang
trích một dòng chuyển hướng.

⭐ Đặc tả **thật** ở `agentskills.io/specification` — 7.295 ký tự chữ. Tôi tải
   và đọc nó, và §0.3 dưới đây là từ đó.

### §0.3 Đặc tả `SKILL.md` — thứ thật sự phải theo

```
skill-name/
├── SKILL.md      BAT BUOC: frontmatter YAML + huong dan Markdown
├── scripts/      tuy chon: MA THUC THI DUOC
├── references/   tuy chon: tai lieu nap THEO NHU CAU
└── assets/       tuy chon
```

| Trường | Bắt buộc | Ràng buộc |
|---|---|---|
| `name` | ✅ | ≤64, chỉ `a-z0-9-`, không mở/kết bằng `-`, không `--`, **phải trùng tên thư mục cha** |
| `description` | ✅ | ≤1024, nói **làm gì** và **khi nào dùng** |
| `license` | — | tên giấy phép hoặc trỏ tệp |
| `compatibility` | — | ≤500, yêu cầu môi trường |
| `metadata` | — | map chuỗi→chuỗi |
| `allowed-tools` | — | chuỗi **cách nhau bằng dấu cách**, tool được **duyệt trước**. **THỬ NGHIỆM** |

Hai câu trong đặc tả quyết định thiết kế của ta:

> *"`scripts/` — Contains **executable code that agents can run**."*
> *"`allowed-tools` — a space-separated string of tools that are **pre-approved to run**. **Experimental.**"*

### §0.4 🔴 Và đây là chỗ đặc tả ĐỤNG THẲNG vào kiến trúc H44

Cả H44 đứng trên **bốn cổng** nối tiếp, cộng phiếu duyệt bền cho lớp `PAID`:

```
ToolSpec.customer_visible -> api_exposed -> chinh_sach.CONG_CU_CHO_PHEP
                                        -> chieu_tool.CHO_MODEL_GOI
```

`allowed-tools` là **một cửa thứ năm, nằm trong một tệp do KHÁCH viết**, và nó
"duyệt trước" tool. Nhận nguyên trường ấy là:

- cho khách tự cấp quyền gọi tool — **vòng qua cổng ba và cổng bốn**;
- và với tool lớp `PAID`, vòng qua luôn **phiếu duyệt bền** của P04, tức thứ
  duy nhất đứng giữa model và tiền của khách.

⛔ **Quyết định D1 (dưới đây) là: KHÔNG nhận `allowed-tools`.**

⚠️ Và `scripts/` là **thực thi mã tuỳ ý**. Kế hoạch tổng đã tự chốt ở P06:
   *"code sandbox **chỉ khi có sandbox chứng minh được**"*. Ta **không** có.

### §0.5 Nửa `agents` — mượn HÌNH DẠNG, không mượn cơ chế

`openai/openai-agents-python` (MIT, 29k sao, 55 mô-đun, đẩy 05/09) có
`guardrail.py` 343 dòng. Hình dạng đáng mượn:

```python
@dataclass
class GuardrailFunctionOutput:
    output_info: Any
    tripwire_triggered: bool   # True => DUNG han execution
```

⭐ Điều đáng học không phải mã mà là **một quyết định nhị phân tách khỏi lý do
  của nó**: `tripwire_triggered` nói *dừng hay không*; `output_info` nói *vì
  sao*. Ta đã có đúng cấu trúc ấy ở `KetQua(ok, noi_dung, ma_loi, thong_diep)`
  và ở `loi_ra_ngoai.cau(ma)` — nên đây là **xác nhận**, không phải nhập khẩu.

⛔ Và **không** lắp thư viện: nó chạy **lúc chạy** (runtime), tức ngưỡng chấp
   nhận cao nhất theo luật §0 của mọi pha H44. LTT đã có `chinh_sach`,
   `chieu_tool`, `duyet`, `gia_*` — một tầng guardrail thứ hai là một sổ chính
   sách thứ hai, và hai sổ chính sách là hai sổ sẽ lệch.

---

## §1 — Năm quyết định

### D1. `allowed-tools` bị **BỎ**, không phải bị bỏ qua im lặng

Đọc `SKILL.md` mà thấy `allowed-tools` ⇒ **từ chối nạp skill**, kèm câu nói rõ
vì sao.

⛔ Không "bỏ qua trường lạ". Một skill khai `allowed-tools: image.ltt` mà ta
   lặng lẽ lờ đi là một skill **chạy khác điều nó khai** — người viết tưởng nó
   được quyền, và cái tưởng ấy sẽ thành một báo cáo lỗi *"skill của tôi không
   chạy"* thay vì một câu từ chối đọc được.

⭐ Cùng luật `thi_hanh`: *"tên không có trong `CHO_MODEL_GOI` thì không được
  chiếu, kể cả khi…"*. Fail-closed **và nói ra**.

### D2. `scripts/` **không được thực thi**. Chấm.

Không sandbox ⇒ không chạy. Skill của LTT là **chỉ dẫn**, không phải mã.

⚠️ Thư mục `scripts/` trong một skill nhập từ ngoài ⇒ **từ chối nạp**, không
   phải "nạp và bỏ qua thư mục". Một tệp `.py` nằm im trong kho dữ liệu của
   khách là một tệp có ngày sẽ được ai đó chạy.

### D3. Skill đổi **CHỈ DẪN**, không đổi **QUYỀN**

Một skill được nạp ⇒ nội dung `SKILL.md` vào ngữ cảnh như một khối `system`,
đúng khuôn `luot.dung_ngu_canh(khoi_ghi_nho=…)` mà B4 đã dựng.

Thứ nó **không** đổi được: model, tool được phép, trần chi tiêu, phạm vi dữ
liệu. Bốn thứ ấy do **agent** quyết (D4), và agent do **chủ tài khoản** đặt.

🔴 Đây là *"thứ tự ưu tiên chỉ dẫn"* mà kế hoạch tổng đòi test. Thứ tự:

```
1. he thong (LTT)          <- khong ai doi duoc
2. chinh sach cua AGENT    <- chu tai khoan dat
3. chi dan cua SKILL       <- nap theo luot
4. tin nhan nguoi dung
```

⛔ Và **nội dung skill là dữ liệu không tin được** khi skill đến từ nơi khác —
   cùng hạng với `chatltt_doan` ở B6. Một skill nói *"bỏ qua chính sách trên"*
   phải vô hiệu **về cấu trúc**, không phải vì model ngoan.

### D4. `agent` là một **bản khai**, không phải một tiến trình

Một agent = `(ten, model_alias, tool_cho_phep ⊆ CHO_MODEL_GOI, tran_chi_tieu,
pham_vi)`. Nó **thu hẹp**, không bao giờ mở rộng:

```
tool_cho_phep = tool_khai ∩ chieu_tool.CHO_MODEL_GOI
```

⭐ Giao của hai tập **không thể lớn hơn** tập gốc — nên một agent không cấp
  được quyền nào. Đó là bất biến cưỡng chế bằng **kiểu dữ liệu**, không bằng
  một phép kiểm ở route. Cùng cách `du_an` và `ghi_nho` đã làm.

### D5. Trần chi tiêu của agent là một **ĐIỀU KIỆN**, không phải một GIÁ

Bài học vừa trả giá ở B6: `runtime_noi_bo` đã giữ-và-hoàn theo token cho **mỗi**
lượt model. Một trần chi tiêu ở tầng agent mà **thu** là **sổ tiền thứ hai**.

⇒ Trần agent chỉ **chặn trước khi nộp** (đọc `credit.so_du`, so với trần), và
  **không** trừ, **không** giữ. Xem `apps/chatltt/gia_nghien_cuu.py`.

---

## §2 — Sáu bước

| # | Việc | Cửa |
|---|---|---|
| 1 | `services/skill.py` — phân tích `SKILL.md`, **từ chối** `allowed-tools`/`scripts/` | không |
| 2 | `services/tac_nhan.py` — bản khai agent + phép giao với `CHO_MODEL_GOI` | không |
| 3 | thứ tự ưu tiên chỉ dẫn trong `luot.dung_ngu_canh` | không |
| 4 | bảng + migration (`chatltt_skill`, `chatltt_tac_nhan`) | không |
| 5 | route + cờ `LTT_CHATLTT_V3_AGENTS` | cờ **mới** |
| 6 | giao diện: chọn agent · xem/sửa skill · **nói rõ skill không cấp quyền** | vẽ thật |

**Dải test: 847–852.**

⚠️ Dải 838–840 kế hoạch B6 ghi đã lệch trong thực tế (840 bị P09 lấy) — lần này
   ghi dải **sau khi** nhìn `ls tests/`, không ghi theo trí nhớ.

---

## §3 — Phép đo nghiệm thu (viết TRƯỚC)

1. **`allowed-tools` ⇒ từ chối nạp**, và câu từ chối nói ra tên trường. *(Đối
   chứng: một skill hợp lệ vẫn nạp được.)*
2. **`scripts/` ⇒ từ chối nạp.** *(Đối chứng: `references/` thì nạp được.)*
3. **Agent không mở rộng được quyền**: khai một tool ngoài `CHO_MODEL_GOI` ⇒
   tập kết quả **không** chứa nó. *(Đối chứng: tool trong tập thì còn.)*
4. **Thứ tự ưu tiên**: một skill chứa câu *"bỏ qua chính sách"* **không** đổi
   `tool_cho_phep` của agent — chốt bằng so **tập tool**, không bằng đọc chữ.
5. **Trần agent không trừ tiền**: bánh cóc AST — không lời gọi `credit.giu` /
   `credit.tru` nào trong `tac_nhan.py`. Cùng khuôn `test_842`.
6. **Skill là dữ liệu không tin được**: nội dung skill đi vào ngữ cảnh phải qua
   cùng hàng rào B6 đã dựng (`nghien_cuu.vo_hieu_so_nguon` hoặc tương đương cho
   khối `system`).

---

## §4 — ⛔ Chưa bắt đầu, và vì sao

Ba việc phải xong **trước** bước 1, không cái nào là kỹ thuật:

| # | Việc | Của ai |
|---|---|---|
| A | **P11 red team** chạy ở phiên/cây MỚI | một phiên khác |
| B | Xoay khoá production đã lộ trong transcript 07/09 | chủ dự án |
| C | Chốt `gia_trich.CHU_DU_AN_DA_CHOT` | chủ dự án |

⭐ Lý do B đứng trước một pha **mở thêm bề mặt quyền**: thêm agents/skills là
  thêm chỗ để một khoá bị lộ gây hại. Vá tường trước, xây thêm cửa sau.

🔴 Và A đứng trước vì luật của chính kế hoạch: *"P11 chạy ở phiên MỚI, cây MỚI.
   Một người tự kiểm mình thì kiểm những chỗ mình đã nghĩ tới."* Tôi vừa viết
   B4/B5/B6 và ba bản vá P10 — tôi là người **ít đủ điều kiện nhất** để red
   team chúng.
