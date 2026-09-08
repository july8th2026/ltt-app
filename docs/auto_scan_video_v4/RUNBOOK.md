# Auto Scan Video V4 — runbook vận hành

Sổ tay cho người trực khi một lần chạy hỏng. Mỗi mục trả lời ba câu theo đúng thứ
tự: **nhìn vào đâu**, **kết luận được gì**, **làm gì**.

⛔ Không mục nào ở đây bảo bạn sửa dữ liệu bằng tay. Mọi thao tác đều đi qua một
hàm đã có, vì một lần `UPDATE` gõ tay trên `asv_stage` sẽ đi vòng qua
`cap_nhat_giai_doan` — nơi giữ `revision` — và hai tiến trình cùng ghi sẽ mất một
bên mà không ai biết.

⚠️ Runbook này được viết ở pha 25 và **chưa được diễn tập trên máy chủ thật**. Các
lệnh đọc đều an toàn; các lệnh ghi được đánh dấu 🔻 và cần chủ dự án đồng ý.

---

## 0. Trước khi nhận khách: máy có chạy được không

```bash
python -c "import json,sys; sys.path.insert(0,'.'); from apps.auto_scan_video import san_sang; print(json.dumps(san_sang.tom_tat(), ensure_ascii=False, indent=1))"
```

`san_sang: false` nghĩa là **một phụ thuộc bắt buộc đang thiếu**, và một lần chạy
sẽ đi qua bốn giai đoạn rồi hỏng ở giai đoạn thứ năm — sau khi khách đã đợi và
credit đã bị giữ.

| trạng thái | nghĩa là |
|---|---|
| `co` | hỏi được, và có |
| `khong` | hỏi được, chưa cấu hình — làm theo `ghi_chu` |
| `chua_do` | **không hỏi được**. Không phải "không có" — phải tìm ra vì sao trước |

⛔ `/health/ready` của nền tảng **không** kiểm những thứ này. Nó trả lời "CSDL có
sống không" và "tiến trình có mồ côi không". Cả hai đều đúng và cả hai đều không
nói gì về giọng, model hay bộ mã hoá.

---

## 1. Một lần chạy đứng im

**Nhìn vào đâu**

```python
from apps.auto_scan_video import features, quan_sat
run = features.lay_run(db, "<run_id>", "<owner_id>")
quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)   # từng giai đoạn + job con
quan_sat.doi_soat_nhanh(db, run)                       # tiền có khớp bằng chứng không
```

**Kết luận được gì**

| dấu hiệu | nghĩa |
|---|---|
| giai đoạn `queued`, job con `queued`, `next_run_at` ở tương lai | đang **hẹn chạy lại** — đợi, đừng đụng |
| giai đoạn `queued`, **không** job con | job mồ côi đã bị huỷ; vòng điều phối kế tiếp sẽ nộp lại |
| giai đoạn `running` lâu bất thường | so với pha 24: `audio_prepare` ≈ 22 s và `transcribe` ≈ 34–41 s cho nguồn 32 s, **tăng theo độ dài nguồn**. Một nguồn 2 giờ ở mức đó là hàng chục phút — chưa phải sự cố |
| giai đoạn `failed_retryable` | pha 23: sẽ được nộp lại, tối đa `features.LAN_THU_GIAI_DOAN_TOI_DA` lần |
| giai đoạn `failed_terminal` | dừng hẳn; lần chạy sẽ về `error` ở vòng điều phối kế tiếp |

**Làm gì**

- Còn lượt thử → **không làm gì**. Nộp lại bằng tay chỉ tạo job thứ hai.
- 🔻 Muốn dừng: `features.huy_run(db, run_id, owner_id)`. Huỷ là **hợp tác** —
  giai đoạn đang chạy dừng ở lần hỏi `is_cancelled()` gần nhất, không bị giết.
- ⛔ Một lần chạy **đã kết thúc** (`done`/`error`/`cancelled`) thì
  `thu_lai_giai_doan` **từ chối**, và đó là cố ý: nó đã quyết toán, không còn chỗ
  giữ credit. Khách làm lại bằng một lần chạy mới.

---

## 2. Job nằm chờ tài nguyên

**Nhìn vào đâu**: `Job.status == "queued"` với `admission_resource` đã khai, và
`next_run_at` bị đẩy lên đều đặn.

**Kết luận được gì**: `audio_prepare` và `transcribe` **dùng chung một suất**
(`tach_nguon_cuc_bo`), nên hai lần chạy không bao giờ tách nguồn tiếng đồng thời.
Đó là chủ ý, và pha 24 đo lại để xác nhận: chạy song song cho thông lượng ×1,5
nhưng đỉnh CPU **78,6%**, trượt ngưỡng 70% đã viết sẵn trong `pipeline.CHUOI`.

**Làm gì**: đợi. Nếu hàng đợi dài kéo dài, đó là câu hỏi **công suất**, không phải
sự cố — và tách suất phải kèm một phép đo mới, không phải một lần đổi ý.

---

## 2b. `ltt_llm: ban` — máy B chỉ phục vụ MỘT lượt tại một thời điểm

**Nhìn vào đâu**: `asv_stage.error` chứa `khong provider nao phuc vu duoc:
ltt_llm: ban`, ở một trong ba giai đoạn khai `tai_nguyen="llm_remote"`
(`edit_plan`, `content_process`, `qc_ai`). Và trong `nhat_ky_job` của báo cáo
nghiệm thu: `HET NGAN SACH HOAN sau 90s (tai nguyen ban)`.

**Kết luận được gì**

🔑 `apps/ltt_llm/ngan_sach.py` khai thẳng: **`DONG_THOI_MAY_B = 1`**. Máy B chạy
`llama-server --parallel 1` — và đó **không phải dè dặt**, nó là con số đúng:
speculative decoding chỉ tối ưu ở một luồng.

⇒ Bất cứ thứ gì khác đang dùng model nhà — một job của khách thật, một phiên
khác đo đạc, một lượt `bench_llm_*` — **giữ trọn suất duy nhất đó**. Phần dôi ra
ăn 429, và chính chú thích ở `ngan_sach.py` gọi tên: *"không phải lỗi của bên
nào, là hai trần không biết nhau"*.

⚠️ **`/health` và `/live` của cổng KHÔNG nói được điều này.** Cả hai trả 200 khi
máy đang bận — `apps/ltt_llm/features.py:334` ghi rõ *"Ban (429) khong nhin thay
o `/live`"*. Nên "cổng khoẻ" và "gọi được" là hai câu hỏi khác nhau, và chỉ câu
thứ hai mới trả lời được bằng một lượt gọi thật.

⛔ Và **đừng** dùng `tools/kiem_ltt_llm.py` để chẩn đoán: nó mang khiếm khuyết
F-05 của `docs/audit_ltt_llm` — *"không bao giờ có thể xanh, và nó đỏ về phía
báo động"* (gửi bí danh `ltt_llm` thay vì tên model thật). Nó sẽ khẳng định một
sự cố không tồn tại.

**Làm gì**

1. **Đợi, rồi chạy lại.** Đây không phải sự cố. Một lượt nghiệm thu hỏng vì bận
   tốn ~3 phút, không tốn 21 phút — rẻ để thử lại.
2. Hỏi các phiên khác ai đang dùng model nhà. Trên máy này CPU thấp **không**
   chứng minh gì: `ltt_llm` chạy ở **máy B (192.168.2.66)**, máy khác hẳn.
3. Nếu cần chạy nghiệm thu ngay mà không cần model thật: `-ModelGia`. Báo cáo sẽ
   **tự khai** phần nào là bản thay thế (`test_bao_cao_GHI_RO_thu_khong_that`),
   nên nó vẫn là bằng chứng — chỉ là bằng chứng yếu hơn, và nó nói ra điều đó.

🔴 **Lịch sử: 06/09 việc này làm hỏng ba lượt nghiệm thu liên tiếp**
(09:14 · 09:20 · 09:30). Hai lượt đầu **không chờ một giây nào** vì `ai.py` bọc
`KhongCoProviderNao` thành `AiError`, làm mất tín hiệu "bận" trước khi nền tảng
kịp đọc. Đã vá — xem `apps/auto_scan_video/ai.py:_la_ban`. Từ nay một lượt bị
chặn vì bận sẽ **chờ đủ 90 giây rồi nói thẳng ra**, thay vì chết câm và để lại
chín dòng đỏ trông y hệt khiếm khuyết sản phẩm.

---

## 3. Dispatch mơ hồ với provider

**Nhìn vào đâu**

```python
from apps.auto_scan_video import su_dung
su_dung.cac_mo_ho(db, run)      # các lượt "có thể đã gọi, không biết kết quả"
```

**Kết luận được gì**: mất kết nối **sau** khi đã gửi. Provider có thể đã nhận, đã
chạy, đã tính tiền — ta không biết. Hệ thống ghi `mo_ho`, **không** tính tiền, và
**không** tự động thử lại (I5).

**Làm gì**

1. Đối chiếu với bảng điều khiển của provider xem lượt đó có chạy không.
2. 🔻 `su_dung.giai_quyet_mo_ho(db, dong, da_chay=<True|False>)`.

⚠️ Không có gì nhắc bạn rằng có dòng mơ hồ đang chờ. Đó là nợ đã ghi ở pha 23 —
kiểm định kỳ bằng lệnh trên.

---

## 4. Vòng sửa chữa hết lượt

**Nhìn vào đâu**: `asv_work_item` (cột `status`, `revision`), `asv_stage.outputs`
của `qc` và `qc_ai`, và dòng `WARNING ... vao vong sua N, dat lai ...` trong log
worker — dòng đó nói **vòng thứ mấy**, **giai đoạn nào bị đặt lại**, và **bao
nhiêu đơn vị** bị mở lại.

**Kết luận được gì**

- `nan_cho_vua.VONG_TOI_DA` chặn việc viết lại một câu mãi mãi. Hết lượt mà vẫn
  không vừa khe thì đoạn đó được xếp `can_sua`, và lần chạy vẫn đi tiếp.
- `sua_chua.VONG_SUA_TOI_DA` **chặt hơn** vì nó sửa một phán quyết chủ quan, còn
  vòng nắn sửa một đại lượng đo được và hội tụ.
- Đơn vị mang `ITEM_INVALIDATED` là đơn vị **đã bị mở lại và đang chờ chạy lại**,
  không phải đơn vị hỏng.

⭐ **Trần vòng sửa nằm trong CSDL, không nằm trong một biến đếm.** `UNIQUE(run_id,
ma_dispatch)` trên sổ cái là thứ chặn, nên một tiến trình thứ hai chạy song song
cũng không lách qua được — khác hẳn một biến `so_vong` mà mỗi tiến trình giữ một
bản.

**Làm gì**

🔴 Câu trả lời cũ ở mục này đã **hết đúng**. Nó viết: *"kế hoạch sửa được tính
nhưng chưa được thi hành — không giai đoạn nào đọc nó"*. Hai nửa đó đã được nối:

| ngày | nối cái gì |
|---|---|
| 05/09 | `jobs._sua_chua_neu_can` đọc bậc thang nắn (`khong_vua` → `voice_synthesis`) |
| 06/09 | giai đoạn `qc_ai` đọc thêm nguồn **ngữ nghĩa** (`dich_sai` → `content_process`) |

Nên hôm nay **không phải làm gì cả** khi thấy một vòng sửa: nó tự chạy, tự dừng
khi hết trần, và lần chạy vẫn giao hàng kèm phán quyết. Chỉ khi hết trần mà bản
giao vẫn sai mới cần một lần chạy mới với cài đặt khác (giọng khác, chế độ thời
gian khác).

⚠️ **QC bằng AI mặc định TẮT.** Thấy `qc_ai` xanh mà `so_khong_dat` không có
trong `outputs` thì đọc `qc_ai_bat`: `false` nghĩa là **chưa soát lần nào**, không
phải "soát rồi, không có lỗi". Bật bằng `LTT_ASV_QC_AI=1` ở cấp người vận hành —
đó là một khoản chi mỗi lần chạy, nên nó không nằm trong `settings` của khách.

---

## 5. Artifact hỏng hoặc mất

**Nhìn vào đâu**

```python
from apps.auto_scan_video import assets
assets.kiem_toan_ven(db, kho, asset)     # 'ok' | 'missing' | 'corrupt' | 'expired'
```

**Kết luận được gì**

| kết quả | nghĩa |
|---|---|
| `missing` | bản ghi còn, tệp biến mất → phải tính lại |
| `corrupt` | tệp còn, nội dung lệch checksum → phải tính lại **và đáng ngờ** |
| `expired` | chính sách lưu trữ, **không** phải sự cố |

**Làm gì**

- Lần chạy còn sống → 🔻 `features.thu_lai_giai_doan(...)` cho giai đoạn sinh ra
  artifact đó; hạ nguồn tự vô hiệu theo.
- Lần chạy đã kết thúc → một lần chạy mới. ⚠️ Và nó tính lại **từ đầu**: cache
  cấp giai đoạn chưa từng trúng lần nào (B23-01), nên cả demucs lẫn ASR chạy lại.
- `corrupt` trên nhiều artifact cùng lúc → dừng nhận việc mới và kiểm đĩa trước,
  vì một lỗi lưu trữ đang tiếp diễn sẽ làm hỏng cả những lần chạy lại.

---

## 6. Những thứ runbook này KHÔNG cứu được

Ghi ra để người trực không đi tìm một nút không tồn tại.

| tình huống | vì sao |
|---|---|
| "cắt thông minh mà không cắt cảnh nào" | B22-01 — VLM chưa nối vào `EDIT_PLAN`; mọi cảnh đều được GIỮ |
| "chạy lại mà vẫn tính tiền như mới" | B23-01 — cache cấp giai đoạn chưa từng trúng |
| "preset cắt sao chậm thế" | B24-01 — bộ mã hoá phần cứng không với tới được, đang mã hoá bằng CPU |
| "artifact cũ chiếm hết đĩa" | pha 25 — `expires_at` được đặt nhưng **không ai quét**; `assets.don_theo_run` tồn tại và chưa có người gọi |
