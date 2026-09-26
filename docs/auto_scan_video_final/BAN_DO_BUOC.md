# BẢN ĐỒ TỪNG BƯỚC của ASV — hợp đồng vào/ra THẬT, đọc từ mã

> Làn `asvf-nghiem-thu-v2`, 24/09/2026. Dựng cho **thang đo từng bước** (chủ dự án
> đổi hướng 24/09, `L_NGHIEM_THU.md` §2d).
>
> ⛔ **Tệp này ghi cái THẤY TRONG MÃ, không thiết kế lại.** Chỗ nào xấu thì ghi là
> xấu. Một bản đồ đẹp hơn sự thật thì vô dụng đúng lúc cần nó nhất.

## 1. Hình dạng chung — và nó ĐỒNG DẠNG, đó là tin tốt

Cả **12** giai đoạn có cùng một chữ ký:

```python
def chay(db, kho: Storage, *, run, ctx=None) -> dict
```

Không giai đoạn nào nhận đường dẫn tệp làm tham số. Mỗi bước **tự tra** đầu vào của
nó bằng cách đọc `asv_stage.outputs["khoa_asset"]` của các giai đoạn trước, qua vài
hàm trợ giúp cục bộ (`_khoa_json`, `_khoa_theo_duoi`, `_khoa_master`, …).

⇒ **Chạy MỘT bước riêng lẻ là làm được**, và không cần đi qua hàng đợi:

```
1. dựng một `AsvRun`
2. gieo `outputs.khoa_asset` của các giai đoạn TRƯỚC, trỏ vào artifact có sẵn
3. gọi `chay(db, kho, run=run, ctx=JobContext(job_id, gpu_uuid=...))`
```

⭐ Hai thứ làn này đã có là đúng thứ bước 3 cần: `fx.card_cho_job` (card thật) và
`fx.ghim_python_co_card` (venv có CUDA). Không có chúng, mọi bench đo **khuôn**.

## 2. ⛔ KHAI `sau` HẸP HƠN THỨ MÃ THẬT SỰ ĐỌC

Đây là phát hiện quan trọng nhất của bản đồ, và nó **chặn ngay bước 1** nếu không
biết trước.

| giai đoạn | `pipeline.CHUOI` khai `sau=` | mã THẬT SỰ đọc artifact của |
|---|---|---|
| `compose` | `(timing_align,)` | `timing_align` · **`media_prepare`** · **`audio_prepare`** · **`content_process`** · **`voice_synthesis`** |
| `timing_align` | `(voice_synthesis, audio_prepare)` | + **`media_prepare`** · **`content_process`** · **`edit_plan`** |
| `qc` | `(render,)` | + **`compose`** · **`timing_align`** · **`voice_synthesis`** |
| `qc_ai` | `(qc_do_luong,)` | + **`compose`** · **`render`** · **`content_process`** · **`edit_plan`** · **`timing_align`** |
| `qc_do_luong` | `(qc,)` | + **`content_process`** · **`voice_synthesis`** |
| `content_process` | `(edit_plan,)` | + **`transcribe`** |
| `edit_plan` | `(transcribe,)` | + `qc` *(đường vòng sửa)* |
| `voice_synthesis` | `(content_process,)` | + `qc` *(đường vòng sửa)* |
| `transcribe` | `(audio_prepare,)` | + **`media_prepare`** |
| `media_prepare` · `audio_prepare` | `()` / `(media_prepare,)` | `run.source_key` trực tiếp |

Đã đối chiếu tận dòng, không suy từ tên. Ví dụ `giai_doan_ban_dung.py` (COMPOSE):

```
 84  khoa      = _khoa_json(db, run, pipeline.MEDIA_PREPARE)
153  truoc     = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
173  khoa_ke   = _khoa_json(db, run, pipeline.VOICE_SYNTHESIS)
176  khoa_nen  = _khoa_theo_duoi(db, run, pipeline.AUDIO_PREPARE, ".wav")
```

trong khi bản khai là `GiaiDoan(COMPOSE, …, sau=(TIMING_ALIGN,))`.

### ⚠️ ĐÍNH CHÍNH (cùng ngày) — mục §2 ở trên phát biểu quá một bậc

Bảng trên đúng về **khai trực tiếp vs đọc trực tiếp**. Nhưng **bao đóng bắc cầu**
của `sau` **phủ hết** mọi lần đọc thật — kiểm tận dòng, cả 12 giai đoạn `OK`. Nên:

* lịch chạy và vô hiệu hoá **đúng hôm nay**, và đúng **nhờ bao đóng**;
* khoản nợ thật là: **bao đóng đó chịu lực mà không được khai**.

⛔ Và một lỗi nữa trên đường chưa đo được: `features.py` (quanh dòng 263) ghi một
sự cố **đã xảy ra thật** cùng họ — chạy lại `media_prepare` → job `audio_prepare`
**cũ của lượt trước vẫn chạy** → `transcribe` chạy trên bản tiếng của **lượt
trước**. Kèm câu đáng nhớ: *"một lỗi chỉ hỏng đôi khi thì trước đó nó vẫn hỏng, chỉ
là chưa ai thấy"*. ⇒ Đường **chạy lại / vô hiệu hoá một phần** là chỗ quan hệ hẹp
**đã cắn một lần**, nên N-08 **không** phải *"vô hại hôm nay"* mà là **"chưa đo
trên đường chạy lại"**.

### Vì sao hôm nay nó KHÔNG hỏng trên lượt chạy TỪ ĐẦU

Chuỗi hiện tại là một **đường gần thẳng**, nên mọi giai đoạn chưa khai đều tình cờ
đã `succeeded` trước. Chính `pipeline.ha_nguon_cua` nói thẳng điều đó:

> *"hôm nay kết quả này TRÙNG với 'mọi giai đoạn đứng sau trong `CHUOI`'"*

⛔ Nhưng `ha_nguon_cua` là thứ quyết định **giai đoạn nào bị vô hiệu khi một bước
chạy lại**, và nó dùng quan hệ **đã khai**. Nên:

* **xen một bước mới vào giữa** — đúng việc thang mới nhắm tới — sẽ làm bản khai và
  thực tế lệch nhau, và chỗ lệch **không tự kêu**;
* chạy song song hai nhánh sẽ đọc một artifact chưa có, và lỗi hiện ra ở **bước
  đọc**, không ở bước khai sai.

⇒ Cho **bench từng bước**: phải gieo đúng những giai đoạn mã **thật sự đọc** (cột
phải), ⛔ **không** gieo theo cột `sau`. Gieo theo `sau` sẽ cho một lỗi *"thiếu đầu
vào"* nghe như khiếm khuyết sản phẩm.

## 3. Bước đầu tiên của thang mới: `transcribe`

Mọi thứ sau nó đứng trên nó, nên đo nó trước là đúng thứ tự.

| | |
|---|---|
| mã | `giai_doan_chep_loi.chay` |
| đọc | `media_prepare` (bản WAV đầy đủ) · `transcribe` (đường vòng sửa) |
| trợ giúp | `_khoa_tieng_asr(db, run)` |
| ghi | `.wav` + `outputs`: `so_doan` · `so_tu` · `ngon_ngu` · `engine` · `canh_chinh` · `nguon_loi` · `phu_song` · `dinh_tuyen` · `khoa_chung` |
| job | `asv_gpu.transcribe`, VRAM khai **7.600 MB**, cần card |

### Số đã đo được (lượt A/B/C, phim `v3`, 24/09) — điểm khởi đầu, không phải mục tiêu

```
nguon_loi  = "ocr"     engine = rapidocr/3.9.2+PP-OCRv6_small
ngon_ngu   = "zh"      so_doan = 95     phu_song = 92,0
so_tu      = 0         canh_chinh = "ocr_frame"
dinh_tuyen = {che_do: "auto", ly_do: ["khong_co_phu_de_nhung"]}
```

⛔ **BỐN con số trên là của ĐƯỜNG ĐÃ BỊ (26/09, Task 21), giữ làm ảnh chụp.**
Sản phẩm nay chỉ đi **MỘT** đường voice → voice, nên một lượt `transcribe` hôm nay
cho `nguon_loi = "asr"`, `canh_chinh` thuộc `{aligned, fallback_unaligned}`,
`dinh_tuyen = {che_do: "asr", nguon_loi: "asr", ly_do: [], cat_lai: {...}}`, và
`so_tu > 0`. ⭐ Chính vì thế hai câu hỏi ngay dưới đã đổi câu trả lời — xem
`B1_PLAN_DUONG_ONG_GD1.md` §11 và `apps/auto_scan_video/nguon_loi.py` đầu tệp.

⚠️ Hai điều bản đồ **chưa** trả lời được, và bước `transcribe` phải trả lời:

1. **`so_tu = 0` với `so_doan = 95`.** Đường OCR không đếm từ, hay nó đếm sai? Một
   con số 0 cạnh 95 đoạn là thứ sẽ bị đọc thành "không có nội dung".
2. **Chưa có đối chứng độ đúng.** `phu_song = 92,0` nói về **độ phủ**, không nói về
   **độ đúng** của văn bản. Làn `ocr` có `l_ocr_gt_v2.json` (nhãn tay) —
   `L_OCR.md` là nơi bắt đầu.

⛔ Và `so_tu = 0` là **đầu vào của N-06**: lượt A chết vì AUTO_MATCH không có tiếng
nguồn, và dấu hiệu duy nhất ở tầng này là cặp `nguon_loi="ocr"` + `so_tu=0`.

## 4. Việc còn lại của bản đồ

* ⏸ Hợp đồng vào/ra **chi tiết tới từng khoá** của 11 bước còn lại — dựng khi tới
  bước đó, không dựng trước (một bản đồ viết trước khi đo sẽ mang giả định).
* ⏸ **N-06** trả lời ở bước *hồ sơ giọng*; **N-07** ở bước *cắt cảnh*
  (hoãn có chủ ý, `LOI_TONG.md`).
