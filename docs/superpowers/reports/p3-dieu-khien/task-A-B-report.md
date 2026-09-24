# P3 · Việc A + B (điều phối giao) — nối dây node `ai.*`, và bỏ số cứng `[4:]`

## Nguồn đã tra

- **Chính làn p7 đã ghi lỗi ra trước khi nó kịp cắn** —
  `platform_core/workflow/nut_loi/ai_llm.py` đầu tệp:

  > *"CHƯA nối vào `cau_noi.nop_job`/`ap_ket_qua`: cầu nối job chung suy tên
  > ToolSpec bằng `node["type"][4:]` (cắt đúng 4 ký tự cho tiền tố `"app."`) —
  > áp trực tiếp cho `"ai.llm"` ra `"lm"`, vô nghĩa."*

  ⇒ Không phải tôi suy ra; người viết mã đã đo và ghi lại. Việc của tôi là
  **tổng quát hoá cầu nối**, đúng thứ họ nói là ngoài phạm vi của họ.
- `platform_core/workflow/cong_cu.py` — `CongCu.ten` là **tên ToolSpec**
  (`"text.chat"`), còn `ai.llm` khai `job_type = "ltt_llm.chat"`. Hai chuỗi
  khác nhau, nên không có phép cắt chuỗi nào nối được chúng.
- Task 4 của chính làn này đã gặp **cùng** lỗi ở dạng `core.if` → `".if"`.

## Đỏ trước — và bằng chứng là chính câu lỗi sai

```
$ python -m pytest tests/test_1788_wf_tien_to_loai_node.py -q
14 failed in 3.39s

E   AssertionError: ai.llm chua song trong nut_loi.tat_ca()
E   ImportError: cannot import name 'ten_cong_cu' from 'platform_core.workflow.cau_noi'
E   AssertionError: cong_cu_khong_con: 'lm'
E   assert 'ai.llm' in "cong_cu_khong_con: 'lm'"
```

Dòng thứ ba là toàn bộ vấn đề: một node `ai.llm` đi qua `cau_noi.nop_job` để
lại trong sổ câu `cong_cu_khong_con: 'lm'` — **đổ lỗi cho registry** cho một
lỗi của chính cầu nối, và người đọc log đi tìm một tool chưa bao giờ tồn tại.

## Xanh sau

```
$ python -m pytest tests/test_1788_wf_tien_to_loai_node.py -q
14 passed in 2.36s
```

## ⛔ Cách "thông minh" đã bị LOẠI BẰNG SỐ ĐO

Cách hấp dẫn nhất là tra ngược: `ai.llm` khai `job_type="ltt_llm.chat"`, vậy cứ
tìm `CongCu` nào có `job_type` ấy. **Đo trên registry hôm nay (19 tool):**

```
job_type bi DUNG CHUNG boi >1 tool:
  {'prompt_ai_ommi.generate': 2, 'taoanh.generate': 2, 'upscalevideo.render': 2}
```

Ba va chạm **đã tồn tại**. Một tra ngược đúng hôm nay cho `ltt_llm.chat` và sai
vào đúng ngày ai đó thêm tool thứ hai trên nó — im lặng, và nó chọn tool nào thì
tuỳ thứ tự dict.

⇒ **Node `ai.*` phải KHAI ToolSpec nó bọc.** Trường ấy chưa tồn tại trên
`NodeDefinition`. ⚠️ Tôi **không** tự thêm nó: nó phải được đặt trong
`nut_loi/ai_*.py` — tệp của làn p7 — nên đây là **một câu hỏi cho điều phối**,
không phải một quyết định của tôi. Trong lúc chờ, `ten_cong_cu` là chỗ **duy
nhất** phải sửa ngày trường ấy có mặt, và `ai.*` **ném to** thay vì đi tiếp với
một cái tên bịa.

## Việc đã làm

**A.** `nut_loi/__init__.py` import `ai_llm` + `ai_router` (`ai_loi` được hai
tệp kia kéo theo). Ba tệp gọi `dang_ky(...)` **lúc import**, nên không ai import
thì chúng không tồn tại — palette không vẽ, `bien_dich._node_loi` báo
`node_khong_ton_tai` cho một thứ đã có thật. *Một mô-đun đăng ký mà không ai
import là một mô-đun chết.* (`noqa: F401` đúng chỗ: tác dụng là **hiệu ứng phụ**.)

**B.** `cau_noi.TIEN_TO_APP` + `LoiTienTo` + `ten_cong_cu(loai)`:
- cắt bằng `len(TIEN_TO_APP)`, ⛔ không bằng một hằng số viết tay;
- `"app."` không có đuôi ⇒ cũng ném (bản cũ cho ra `""`, rồi lại
  `cong_cu_khong_con: ''`);
- **cả hai** cửa (`nop_job` và `ap_ket_qua`) bắt và chốt node `FAILED` với mã
  `loi_he_thong` (§5.6 — lỗi **của ta**) và **tên loại thật** trong câu lỗi.
  ⚠️ Cửa thứ hai phải chốt trạng thái: không chốt thì job đã kết thúc mà node
  đứng QUEUED tới khi `TRAN_RUN` 20 giờ hết hạn — đúng cái bẫy `F5` đã ghi.

## Bánh cóc CẮN THẬT (tiêm lỗi rồi đo)

`test_banh_coc_cau_noi_khong_con_so_cung_cat_tien_to` đọc AST `cau_noi.py` và
cấm **mọi** lát cắt bằng hằng số nguyên khác 0.

```
# doi `chuoi[len(TIEN_TO_APP):]` thanh `chuoi[4:]`
$ pytest …::test_banh_coc_cau_noi_khong_con_so_cung_cat_tien_to -q
1 failed in 0.49s
# phuc hoi
1 passed in 0.37s
```

Đối chứng nằm trong chính phép (`"def ten_cong_cu" in nguon and len(nguon) >
1000`): một đường dẫn sai cho ra "0 lát cắt" rồi xanh giả.

## Vòng hai — điều phối chốt "khai tường minh" (24/09)

```
$ python -m pytest tests/test_1789_wf_node_khai_toolspec.py -q
11 failed, 1 passed   →   12 passed in 3.78s
$ …chay_nang.py --phien p3 -- pytest <28 tep wf + ai + registry> -q -n 6
406 passed, 6 warnings in 43.74s
```

### `NodeDefinition.ten_toolspec` — bắt buộc, ném LÚC DỰNG

Thiếu nó khi `thi_hanh == "job"` ⇒ `LoiNut` ngay ở `import`, chỗ người viết node
nhìn thấy — không phải lúc chạy, *"chỗ đang tiêu tiền của khách"*.
`tu_toolspec` tự khai `cc.ten`; `ai.llm`/`ai.extract`/`ai.router` khai
`TEN_TOOLSPEC = "text.chat"` (⛔ khác `JOB_TYPE_TEXT_CHAT = "ltt_llm.chat"`:
một cái là làn hàng đợi, một cái là khoá tra registry).

### ⚠️ Ngoại lệ DUY NHẤT, và nó không phải một ngoại lệ theo TÊN

`tu_piece` cũng `thi_hanh="job"`, và luật chặt làm `test_1755` đỏ ngay — tức va
chạm **có thật**, không phải giả thuyết. Một node `piece.*` bọc một *piece*,
không bọc ToolSpec nào: nó chạy trên **runner Node** (`JOB_TYPE_PIECE`).

⇒ Miễn theo **bộ thi hành**, không theo tên, và **có người canh**:
`test_banh_coc_NGOAI_LE_dung_bang_MOT_bo_thi_hanh` chứng minh một `job_type`
thứ ba không khai gì vẫn **ném lúc import**.

### `NodeDefinition.hau_kiem` — `ai_loi.dien_giai` đã được nối

Job SUCCEEDED **không** đảm bảo kết quả dùng được (máy B: HTTP 200 · job
SUCCEEDED · `content` RỖNG). `ap_ket_qua` nay hỏi định nghĩa node *"kết quả này
dùng được không"* **trước** khi chốt SUCCEEDED.

⛔ `cau_noi` **không** biết `ai` là gì — bánh cóc đọc AST của chính nó và cấm
mọi hằng chuỗi `ai.` trong MÃ (⚠️ **trừ docstring**: tệp ấy *phải* kể lại ca
`"ai.llm"` ra `"lm"`; một bánh cóc không phân biệt tài liệu với mã sẽ dạy người
ta xoá lời giải thích) và cấm import mô-đun `ai_*`.

💰 **Quyết định tiền, khai ra chứ không để ngầm:** hậu kiểm FAILED ⇒
`cost_credit = 0` (cùng luật mọi node FAILED). Nhưng **ta vẫn tốn tài nguyên
máy B** cho lượt ấy — một khoản lỗ có thật, chặn trên bởi `retry.max ≤ 5`, và
nó phải được theo dõi chứ không được quên.

### Một phép kiểm của chính tôi đo NHẦM ĐỐI TƯỢNG

`test_1785` (Task 6) khẳng định **mọi** node lõi miễn phí. Đúng khi sổ chỉ có
`core.*`; sai ngay khi `ai.*` vào sổ — `ai.llm` **phải** `theo_registry`. Thứ
quyết định giá là **bộ thi hành**, không phải "node lõi". Nay đo **hai chiều**:
inline/run_con tốn tiền ⇒ bút toán `cau_noi` không quản; job miễn phí ⇒ chạy tài
nguyên thật mà không ai trả (lỗ ngược chiều, **dễ lọt hơn vì không ai kêu**).

### Bánh cóc thứ hai CẮN THẬT

```
# TEN_TOOLSPEC = "text.chatt"
$ pytest …::test_banh_coc_moi_node_job_khai_ten_CO_THAT_trong_registry -q
1 failed in 2.20s   →   phuc hoi: 1 passed in 2.08s
```

## Chưa làm được

- `ai.*` vẫn `publish_duoc=False` (quyết định của p7), nên chưa có đường
  **publish** nào dẫn tới hai cửa này — phép kiểm gọi thẳng `cau_noi` và sửa đồ
  thị đã ghim. `bien_dich` chưa biết dịch `tham_so` của `ai.*` thành `params`
  của job `text.chat`.
- `cau_noi.nop_job` vẫn **từ chối** `piece.*` (`LoiTienTo`) — plan 08 phải mở
  đường riêng cho runner Node.
- Lỗ tài nguyên máy B khi hậu kiểm FAILED (ở trên) **chưa có phép đo** nào.
