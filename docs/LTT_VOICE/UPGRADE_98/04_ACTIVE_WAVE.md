# 04_ACTIVE_WAVE — Wave A (BẰNG CHỨNG)

Trạng thái: **ĐANG MỞ** · mở lúc 09/09/2026 13:45 +0700 · SHA `99017910`

---

## 0. Sự thật vận hành phải biết trước khi chạy bất cứ phép đo nào

Đo lúc 13:42 +0700, không suy từ tài liệu:

| câu hỏi | trả lời ĐO ĐƯỢC |
|---|---|
| Máy này là gì? | `C:\LTTPlatform` **tồn tại** ⇒ **ĐÂY LÀ MÁY CHỦ PRODUCTION** |
| Dịch vụ nào đang chạy? | `LTTStudioWeb` · `LTTStudioWorker` · `LTTStudioVoice` · `LTTStudioCodex` — **cả bốn Running** |
| Sidecar giọng? | Port **8120 LISTENING**, pid 6712, `/live` trả `{"ok":true,"dich_vu":"ltt-voice"}` |
| Production đang chạy commit nào? | `990179106f7e` — **BẰNG SHA baseline của phiên này** |
| `asset_ver` | `9b7ae80d` · build `2026-09-09T11:59:18` |
| Hợp đồng app đang phục vụ | `tran_ky_tu_cong_khai=100000`, `tran_moi_luot_sinh=1500` |
| GPU | **HAI** card RTX 5060 Ti 16 GB. GPU0: 809 MiB / 0 %. GPU1: 844 MiB / 23 % |

⭐ **Không có deploy drift ở baseline.** Production, `admin-mvp-v3`, và nhánh
làm việc của phiên này đứng trên **cùng một commit**. Mọi lệch xuất hiện từ đây
về sau là do phiên này tạo ra, nên quy trách nhiệm được.

⭐ **Card thứ hai ĐANG SỐNG.** Hồ sơ cũ ghi GPU thứ hai lỗi Code 43. `nvidia-smi`
lúc 13:42 liệt kê **cả hai** card với bộ nhớ và mức dùng thật (card 1 còn đang
ở 23 %). Ghi chú cũ **đã hết đúng** — và nó mở lại một lựa chọn thiết kế mà
U-20 phương án D cần (GPU riêng cho bài dài).

### 0.1 Đo mức tranh chấp trước khi xin quyền chạy benchmark

Đếm từ `C:\LTTPlatform\logs\ltt-job-worker*.jsonl`, 7 ngày gần nhất:

```
ltt_voice.synthesize : 29 lượt
03/09: 15   04/09: 13   05/09: 1   06/09–09/09: 0
```

⇒ **Bốn ngày liền không có một lượt sinh giọng nào của khách.** Suất
`vieneu_gpu` (một suất, `admission_slots=1`) đang **rảnh trên thực tế**.

Đây là phép đo trả lời câu *"chạy benchmark có đụng khách không"* mà không cần
hỏi chủ dự án. Trả lời: **rủi ro tranh chấp thấp**. Nhưng nó **không** miễn cho
phiên này hai ràng buộc còn lại:

1. `python tools\cua_so_yen.py trang-thai` trước **mỗi** lệnh nặng (13:37: `RANH`).
2. Sáu cây khác dùng chung `.git`. Benchmark chạy trên sidecar production,
   không chạm cây họ — nhưng bộ test thì chạm.

## 1. Wave A chia làm hai nhịp, và nhịp một KHÔNG cần GPU

Lý do chia: 66/87 hạng mục chưa đo, và phần lớn chỉ cần **đọc**. Chạy GPU
trước khi biết mình đang tìm gì là chạy để dò — thứ §7 của CLAUDE.md gọi là
dùng công cụ phán quyết làm công cụ chẩn đoán.

### A0 — bàn giấy, không GPU, không lệnh nặng

Thứ tự theo §36 (đúng đắn → **tiền của khách** → sở hữu → dữ liệu → âm thanh):

| # | Việc | Hạng mục mở khoá | Vì sao trước |
|---|---|---|---|
| A0-1 | Đọc `gia.py` + `platform_core/credit.py` đường giữ chỗ / quyết toán / hoàn tiền cho `ltt_voice.synthesize` | 41, 42, 43 | Sổ sách **đang chạy thật**: 5.500 bút toán. Bậc 2 của §36. Không cần GPU |
| A0-2 | Đọc `features.giai_giong` + `tables.VoiceProfile` — cách ly chủ sở hữu | 05, 06, 76 | Bậc 3 của §36 |
| A0-3 | Đọc `kiem_model.py` + `chot_sinh.py` — kiểm model theo nội dung lúc khởi động | 09, 10, 74 | Xác minh U-08 thật hay chỉ có trong bảng |
| A0-4 | Đọc `text_pipeline.py` (823) · `tu_dien*.py` · `lan_ngon_ngu.py` · `toc_do.py` | 21–26 | Quyết định corpus benchmark **phụ thuộc** hiểu chuẩn hoá |
| A0-5 | Đối chiếu provenance/license từng giọng: `KHO_GIONG/00_KIEM_KE.md` ↔ `tables.py` ↔ `test_508` | 07, 46, 47, 48, 53 | §7.5 trần 80 tới khi đóng |
| A0-6 | Vẽ bản đồ phụ thuộc `voice.js` (105 KB) **trước** khi bàn tách tệp | 67 | §24 cấm tách vì kích thước |
| A0-7 | Đọc `Job.priority` — quyết đưa vào `order_by` hay gỡ | 14 | Không để trạng thái thứ ba |

### A1 — cần GPU, chạy sau khi A0 nói rõ đo cái gì

| # | Việc | Hạng mục | Ràng buộc |
|---|---|---|---|
| A1-1 | Chạy `tools/do_ho_so_giong.py` ≥3 lượt, kiểm σ, ghi `ho_so_giong.json` | 39, 40 | §18: **không** sửa `ho_so_giong.py`. Nếu σ lớn ⇒ tăng số lượt, không làm tròn |
| A1-2 | Corpus 30 VI × 3 vòng | 30 | Thay corpus 6 câu hiện tại |
| A1-3 | Corpus 30 EN × 3 vòng | 31 | §22: không suy từ "model song ngữ" |
| A1-4 | Corpus 15 mixed × 3 vòng | 32 | Chưa từng có |
| A1-5 | Clone benchmark: ref 3s / 10s / 30s | 33–36 | Cần nguồn ghi âm. **Không** dùng `giong_11labs/` của `D:\Viral` |
| A1-6 | Nhất quán người nói qua nhiều lượt (`do_giu_giong_nhieu_luot.py`) | 29, 36 | Đã có bộ đo |
| A1-7 | Load/concurrency: 1 dài + 1 ngắn · 1 dài + 5 ngắn · nhiều dài | 12, 13, 15, 81 | Mở khoá trần 88 |

### A2 — cần NGƯỜI THẬT (không tự làm được)

| # | Việc | Hạng mục | Trạng thái |
|---|---|---|---|
| A2-1 | Nghe mù A/B, ghi lý do | 80, và trần 94 của mọi hạng mục acoustic | **NEEDS_OWNER_DECISION** — §19 nói thẳng: điểm acoustic do chính Builder nghe là **KHÔNG HỢP LỆ** |

⇒ Hạng mục 30/31/32/34 **không thể** vượt 94 trong phiên này dù benchmark có
đẹp đến đâu. Ghi ra ngay từ Wave A để không ai kỳ vọng nhầm ở cuối.

## 2. Thứ Wave A KHÔNG làm

- Không nối `/v1/stream` (Wave B).
- Không thêm giọng vào kho (Wave C).
- Không đụng `platform_core/` trừ khi A0-7 kết luận `Job.priority` phải sửa ở
  đó — và khi ấy phải dừng lại nói rõ vì sao (CLAUDE.md luật 20).
- Không chạy gate đầy đủ (§27).
- Không deploy (§30). Production đang đúng commit; không có lý do chạm vào.

## 3. Điều kiện đóng Wave A

Đóng khi mỗi hạng mục 12, 13, 14, 27, 29, 30, 31, 32, 33–36, 39, 40, 41, 42,
43 có **một trong hai**: điểm kèm bằng chứng đo được, hoặc
`BLOCKED_WITH_EVIDENCE` kèm lý do thuộc §15 STEP 10.
