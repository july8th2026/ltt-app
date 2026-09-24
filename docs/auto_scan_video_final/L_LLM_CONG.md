# L_LLM_CONG — cổng LLM nội bộ của Auto Scan Video, ĐO trên cổng thật (làn `llm-cong`, 24/09/2026)

Công cụ: `tools/do_llm_cong_asv.py` (đi qua `ai.goi` / `dieu_phoi.goi` → `api_pool` → máy B).
Bằng chứng thô: `docs/auto_scan_video_final/bang_chung/llm_cong/` (`p1`…`p4`, `.log` + `.json`).

Cổng thật: `http://192.168.2.66:8299`, `vat_ly.nguon = H:\LTT_LLM\gateway\llama-swap.yaml`,
`/v1/models = ['qwen35-api', 'qwen38-api']`.

## 1. Thao tác · model ASV yêu cầu · model cổng THẬT trả · khớp?

⭐ **Cột "cổng thật trả" lấy từ trường `model` trong THÂN PHẢN HỒI** (`cong_vlm._boc`:
`model=than.get("model")`), không từ hằng số nào trong mã. p50/p95 trên **n=10 lượt/thao tác**.

| thao tác | ASV yêu cầu | cổng THẬT trả | khớp? | p50 / p95 | token vào / ra (trung vị) |
|---|---|---|---|---|---|
| `chuyen_loi_thoai` (dịch + viết lời) | `qwen38-api` | `…/Qwen3.8-27B-UD-Q4_K_M.gguf` | ✅ | **117,2 / 121,5 s** | 824 / 4.426 |
| `qc_ngu_nghia` (QC ngữ nghĩa) | `qwen38-api` | `…/Qwen3.8-27B-UD-Q4_K_M.gguf` | ✅ | **41,1 / 113,8 s** | 422 / 1.640 |
| `doc_canh` (thị giác, `hieu_canh`) | `qwen35-api` | `…/Qwen3.5-9B-Q6_K-unsloth.gguf` | ✅ | **30,1 / 32,5 s** | 959 / 2.197 |
| `qc_hinh` (thị giác) | `qwen35-api` | *(cùng đường `doc_canh`)* | — | — | — |
| `dich_thuat`, `ho_so_noi_dung`, `rut_ngan_cho_vua` | `qwen38-api` | *(chưa đo lượt này)* | — | — | — |

🔑 **Lời khai và cổng thật KHỚP ở cả ba thao tác đã đo.** `manifest.model_llm_noi_bo = "ltt-3.8"`
và `ai.MODEL_THI_GIAC_NOI_BO = "ltt-3.5"` đều đúng với thứ cổng phục vụ.

🔴 **Nhưng trường `model` là ĐƯỜNG DẪN GGUF, không phải id model.** Cổng trả
`H:/LTT_LLM/models/Qwen3.8-27B-UD-Q4_K_M.gguf` chứ không phải `qwen38-api`. `ai.goi_tinh_tien`
ghi nguyên chuỗi đó vào sổ cái (`ai.py:745`, `ai.py:751`, `ghi_chu.model`), nên **sổ vận hành
của ASV đang lưu một đường dẫn tệp làm tên model** — không nhóm được theo model, và đổi tên
tệp GGUF là đổi khoá nhóm. Không ai so sánh nó với id nào (`grep` chỉ thấy hai chỗ ghi), nên
đây là nợ đọc-số, không phải lỗi định tuyến. Giá vẫn đúng: `gia_token.tinh` nhận **bí danh**,
không nhận `kq.model`.

### Trả lời nghi vấn *"cổng llm nội bộ gọi qua 3.5"*

**Đúng một nửa, và nửa nào thì quan trọng.** Thao tác **thị giác** (`doc_canh`, `qc_hinh`)
thật sự chạy trên **Qwen3.5-9B** — đo được, không phải suy từ mã. Mọi thao tác **văn bản**
(dịch/viết lời, QC ngữ nghĩa, nắn cho vừa, hồ sơ nội dung) chạy trên **Qwen3.8-27B**.
⇒ Câu "cổng nội bộ gọi qua 3.5" đúng nếu người nói đang nhìn đường ảnh; sai nếu áp cho
đường dịch.

## 2. Kết nối, số đo, và "rỗng mà báo thành công"

- **30/30 lượt không lỗi truyền tải** (`n=10` × 3 thao tác): không `BanError`, không timeout,
  không `AiMoHo`. `usage` đáng tin 30/30 (tính tiền được). Prefix cache hoạt động
  (`token_vao_cache = 418/422` ở `qc_ngu_nghia`).
- 🔴 **RỖNG MÀ BÁO THÀNH CÔNG: 1/10 ở `qc_ngu_nghia`** — đúng lỗi memory
  `model-nha-tren-may-b` ghi. Bản ghi nguyên văn:

  ```
  finish_reason = "stop"   token_ra = 1.318   khối suy nghĩ = 3.243 ký tự   content = 0 ký tự
  ⇒ LuocDoSai: qc_ngu_nghia: model tra ve rong [finish_reason=stop; khoi suy nghi 3243 ky tu]
  ```

  ⛔ **Không phải hết ngân sách token**: `finish_reason=stop` (không phải `length`) và 1.318
  token ra trên trần **16.384**. Đây là **chế độ rỗng** của engine, và nó xảy ra ở 10 % lượt
  trên một thao tác ASV sẽ gọi mỗi lô. `chuyen_loi_thoai` và `doc_canh`: 0/10.
- ⚠️ **Phạm vi phép đo độ trễ hẹp hơn con số.** Lúc đo, `/health` báo
  `qwen38-api dang_chay = 3 / max 3` (hai tiến trình của làn này + một làn khác đang nghiệm thu).
  Cùng một đầu vào 4 đoạn mất **117 s** khi tranh 3 chỗ và **72–88 s** khi vãn hơn (pha `seed`).
  ⇒ p50/p95 ở bảng trên là **dưới tải**, không phải độ trễ sạch. Muốn số sạch thì phải giữ
  khoá `eval_may_b` — làn này cố ý không giữ (luật: eval độ đúng không khoá).

### Budget suy nghĩ máy chủ đang đặt — hỏi cổng, không đọc hằng số

`/health` → `vat_ly.theo_model` (cổng đọc từ `llama-swap.yaml` **trên máy B**):

| model | ctx | np | `--reasoning-budget` |
|---|---|---|---|
| `qwen38-api` | 221.184 | 3 | **4.096** |
| `qwen35-api` | 262.144 | 4 | **2.048** |

🔴 **`medium` (2.048) KHÔNG áp cho đường ASV.** `ngan_sach.NGHI_MAC_DINH_THEO_MODEL`/
`budget_suy_nghi_dong_bo` là của **cửa `/api/v1`** (`features.chay`, `runtime_noi_bo.luong`).
ASV đi `dieu_phoi.goi` → HTTP thẳng tới cổng máy B, **không qua `features.chay`**, nên máy A
không gửi `reasoning_budget_tokens` nào và cờ engine `--reasoning-budget 4096` là thứ áp thật.
Effort cũng vậy: chỉ `rut_ngan_cho_vua` khai `low`; sáu thao tác còn lại không gửi
`reasoning_effort` ⇒ nhận `--reasoning-effort xhigh` của hồ sơ engine. Đo khớp: 4.426 token ra
/ ~10.000 ký tự suy nghĩ cho một lô 4 đoạn.

## 3. So 3.8 ↔ 3.5 cho ĐÚNG việc dịch zh→vi — **n = 12 đoạn, 2 lượt mỗi model**

Lô 12 đoạn zh THẬT từ `l_dich/bo_cap_co_nhan.json` (faster-whisper large-v3 trên 4 clip
`Desktop\TEST VIDEO`, giữ nguyên lỗi ASR), lời nhắc SẢN PHẨM `long_tieng.loi_nhac`.

| | `ltt-3.8` (Qwen3.8-27B) | `ltt-3.5` (Qwen3.5-9B) |
|---|---|---|
| giây / lô 12 đoạn | 117,6 · 117,6 | **35,8 · 37,6** (≈ 3,2× nhanh hơn) |
| token vào / ra | 1.696 / 5.027 · 4.945 | 1.658 / 2.768 · 2.803 |
| chi phí một lô | **2.094 mcredit** (3 credit) | **76 mcredit** (1 credit) — 27,6× rẻ hơn |
| `long_tieng.doc_chuyen` đọc được? | **2/2 đạt** | **1/3 đạt** |
| MetricX-24 QE (0–25, THẤP LÀ TỐT) | trung vị **3,06** · trung bình **2,88** · max 4,34 · **0/12** vượt ngưỡng 6 | trung vị **3,06** · trung bình **3,81** · max **9,69** · **1/12** vượt ngưỡng |

⚠️ **n=12 đoạn, 2 lượt/model.** Trung vị **bằng nhau**; khác biệt nằm ở trung bình và ở đuôi
(một đoạn 3.5 chấm 9,69 — trên ngưỡng hỏng). ⛔ **Không nói "3.8 dịch tốt hơn"** từ mẫu này:
mẫu chưa tách được chất lượng trung tâm. Điều mẫu này nói được là hai thứ KHÁC:

1. 🔴 **3.5 không giữ được LƯỢC ĐỒ, và đó là rào cứng, không phải chuyện chất lượng.**
   Ba lượt `chuyen_loi_thoai` quan sát được trên 3.5:
   - lượt A: `"doan"` là một **MẢNG** ⇒ `long_tieng.doc_chuyen` ném
     `LongTiengError('Model không trả về bảng đoạn.')` (`long_tieng.py:212-214`);
   - lượt B: **JSON hỏng** — `Expecting ',' delimiter: line 1 column 1829` với
     `finish_reason=stop` (không phải cắt trần);
   - lượt C: đạt.

   ⇒ Muốn chuyển đường dịch sang 3.5 (rẻ 27,6×, nhanh 3,2×) thì **việc phải làm là lược đồ**
   (grammar/`response_format`, hoặc vòng thử lại), không phải đo lại chất lượng. Chất lượng
   của phần *đọc được* đã nằm trong ngưỡng sản phẩm.
2. Cả hai model đều **dưới ngưỡng `NGUONG_DO[("zh","vi")] = 6,0`** ở trung vị, và cùng bậc với
   mốc "bản tốt zh→vi trung bình 2,4" mà `L_DICH.md` §1 đo trên bộ có nhãn.

MetricX từng mã: 3.8 `{s1 0,73 … s10/s11 4,34}` · 3.5 `{s3 9,69 · s8 5,31 · s12 5,25 …}`
(đầy đủ ở `p4_cham.json`).

## 4. Hai lỗ hổng tất định — XÁC NHẬN trên cổng thật

### 4a. `temperature` — đường sống không truyền, cổng áp **1.0**

`giai_doan_noi_dung.py:217` gọi `ai.goi_tinh_tien(...)` **không** có `temperature`;
`ai.py:727` chuyển `temperature=None` xuống, và `cong_vlm.chat` chỉ đặt khoá khi khác `None`
(`cong_vlm.py:341`) ⇒ thân request **không mang `temperature`**. Chỗ duy nhất trong ASV truyền
nó là `dich_thuat.py:201` (`temperature=0.2`) — và `dich_thuat.dich_ban_ghi` **không còn người
gọi nào** (`thi_hanh.py:121` ghi rõ), tức đường đó chết.

⇒ Cổng áp mặc định của engine: **`--temp 1.0`** cho CẢ HAI hồ sơ
(`llama-swap.yaml`, hồ sơ `qwen38-api` và `qwen35-api`; tệp đang chạy là
`H:\LTT_LLM\gateway\llama-swap.yaml` — chính tệp `/health` khai, và `--reasoning-budget`
4096/2048 mà cổng báo khớp đúng tệp trong kho, nên đây là cùng một bản).

Đo hành vi (n=6, câu hỏi một từ, `qwen38-api`): không khai ⇒ 2 đáp án khác nhau
(`Xoài`/`xoài`); `temperature=0.0` ⇒ 1 đáp án. Phép đo này **yếu** (câu hỏi quá hẹp);
bằng chứng mạnh là §4b.

### 4b. `seed` — cổng NHẬN, nhưng **KHÔNG có hiệu lực**

Đường gửi: `dieu_phoi.goi(them={"seed": …})` → `than["them"]` → `CongVlm.chat(them=…)` →
`than_gui.update(them)` → cổng máy B chuyển nguyên thân lên llama-server
(`llm_gateway/upstream.py:91`, `json=body`). Cổng **không từ chối** `seed`: 5/5 lượt trả 200.

Cùng một lô 4 đoạn, `seed=20260924`, 5 lượt — câu `s1`:

| | s1 |
|---|---|
| 1 | Kim chi ngày nào cũng gần như không thể thiếu. |
| 2 | Cải muối gần như ngày nào cũng không thể thiếu. |
| 3 | Cải muối gần như ngày nào cũng không thể thiếu. |
| 4 | Cải muối gần như ngày nào cũng không thể thiếu |
| 5 | Bắp muối, gần như ngày nào cũng phải có |

⇒ **4 kết quả khác nhau / 5 lượt.** `seed` đi tới cổng, không bị từ chối, và **không làm lượt
tái lập được**.

Hai đối chứng:

- **không gửi `seed`**: 5 khác nhau / 5 lượt (Kim chi… / Cải muối… / Mỗi ngày… );
- **`temperature=0.0`** (`p3_tatdinh.json`): **5 khác nhau / 5 lượt** — *"ngày nào cũng không
  thể thiếu" · "ngày nào cũng có mặt" · "ngày nào cũng phải có"*.

🔴 **KẾT LUẬN QUYẾT ĐỊNH: bản dịch của ASV KHÔNG tái lập được bằng bất cứ núm nào đi qua
đường sản phẩm.** Ngay cả giải mã tham lam (`temp=0`) cũng cho 5 kết quả khác nhau. Cơ chế hợp
lý: `-np 3` + continuous batching + `--spec-type draft-mtp` — thứ tự ghép lô đổi theo tải, nên
cùng prompt không cho cùng chuỗi. ⛔ Đừng vá bằng cách thêm `seed` vào lời gọi: phép đo trên
cho thấy nó **không mua gì**. Muốn tái lập thì phải **cache theo vân tay** (ASV đã có
`van_tay_canh`/`EDIT_PLAN`) hoặc đổi cấu hình engine, không phải thêm một tham số.

⚠️ Và hệ quả đã biết, nay có số: `thi_hanh.phien_ban_engine` (vân tay `EDIT_PLAN`)
**không chứa id model** — `ai.py:81` ghi điều đó. Cộng với §4b: hai lần chạy cùng một video
cho hai bản lời thoại khác nhau, và vân tay không phân biệt được chúng.

## 5. Việc làn này KHÔNG làm

- Không sửa mã sản phẩm. Bốn phát hiện cần quyết định (sổ cái lưu đường dẫn GGUF · 10 % rỗng ở
  `qc_ngu_nghia` · 3.5 sai lược đồ · không tái lập được) đều là **đo**, chưa vá.
- Không đo `dich_thuat` / `ho_so_noi_dung` / `rut_ngan_cho_vua` (cùng model `qwen38-api` với
  hai thao tác đã đo; `dich_thuat` không còn người gọi).
- Không giữ khoá `cpu_nhieu` hay `eval_may_b` — nên độ trễ là **dưới tải** (§2).
