# Đường tài liệu dài của LTT VOICE

> Nguồn chân lý về **hằng số** vẫn là `apps/ltt_voice/tham_so_cong_khai.py` và
> `voice_sidecar/tham_so.py`. Tệp này không chép lại một con số nào từ đó — nó
> giải thích **cấu trúc**, và cấu trúc thì không trôi theo một lượt đo.

## Câu hỏi sai và câu hỏi đúng

Câu hỏi sai: *"VieNeu tạo tối đa được bao nhiêu ký tự?"*

Câu hỏi đúng: *"Một lượt sinh nên dài bao nhiêu để chất lượng tốt nhất, và phải
điều phối bao nhiêu lượt như thế để đọc một tài liệu dài tuỳ ý?"*

Một **model** TTS có ngữ cảnh hữu hạn. Một **sản phẩm** TTS không nhất thiết có
độ dài tài liệu hữu hạn. Trần của model phải được tầng điều phối hấp thụ.

## Bốn con số, và chúng là bốn thứ khác nhau

| Tên | Ở đâu | Nó trả lời điều gì |
|---|---|---|
| chunk nội bộ của engine | `tham_so.MAX_CHARS_CHUNK` | engine tự cắt bao nhiêu bên trong **một** lượt |
| trần một lượt sinh | `tham_so.TRAN_KY_TU_MOT_LUOT` | model đọc liền được bao nhiêu **trước khi chất lượng tụt** |
| kích thước lô GPU | `tham_so.TRAN_SO_VAN_BAN_BATCH` | bao nhiêu đoạn vào GPU một lần — chi tiết thi hành |
| trần yêu cầu của khách | `tham_so_cong_khai.TRAN_KY_TU_CONG_KHAI` | khách gửi được bao nhiêu trong một lần |

⛔ **Gộp bất kỳ hai cái nào là một lỗi đã xảy ra thật ở dự án này.**

- Trước 31/08 hai cái cuối là **một** con số ⇒ bài 3.000 ký tự bị **từ chối**,
  trong khi chính thông điệp lỗi đã nói *"phải đi đường long-form nhiều lượt"* —
  con đường ấy chưa bao giờ được xây.
- Trước 01/09 cửa văn bản dài áp **kích thước lô GPU** lên chính người gọi ⇒ một
  bài 12 đoạn nhận `413 "Lo 12 van ban, vuot tran 8"`. Không ai chọn giới hạn ấy
  cho khách; nó là số của một cái vòng lặp đi lạc.

## Đường đi

```
       VĂN BẢN THÔ (dài tuỳ ý)
                │
                ▼
        text_pipeline.chuan_bi          chuẩn hoá số/ký hiệu/từ điển riêng
                │
                ▼
        chia_doan(can_bang=True)        ranh giới CÂU, các đoạn đều nhau
                │
      ┌─────────┴─────────┐
      │ 1 đoạn            │ nhiều đoạn
      ▼                   ▼
  /v1/speech        ban_doc_dai.dung
  (đường ngắn,            │
   không đổi)             ├── kiểm kho: đoạn nào đã có?      ← ĐỌC TIẾP
                          │
                          ├── /v1/lo-ra-tep  (theo lô)       ← GỘP LÔ GPU
                          │      └─ ghi float32 ra đĩa
                          │      └─ cất vào kho ngay từng cái
                          │      └─ ctx.progress()           ← TIẾN ĐỘ THẬT
                          │
                          └── /v1/ghep-tep                   ← BỘ NHỚ CÓ TRẦN
                                 3 lượt đọc, 1 lượt ghi
                │
                ▼
        toc_do.ap_dung_tep              tệp → tệp, không qua RAM
                │
                ▼
        storage.put(handle)             luồng, không BytesIO
```

## Bản kế hoạch nằm ở đâu — và vì sao KHÔNG có bảng CSDL

Câu trả lời hiển nhiên là một bảng `voice_render_segment` với trạng thái từng
đoạn. Chúng ta **không** làm thế:

- phép chia đoạn là **tất định** — cùng văn bản + cùng trần ⇒ cùng danh sách,
  nên *"đoạn thứ i là gì"* không cần lưu;
- *"đoạn thứ i xong chưa"* đã có một nguồn chân lý rồi: **tệp có trong kho
  không**.

Một bảng trạng thái song song với kho là **hai nguồn chân lý cho cùng một câu
hỏi**, và chúng sẽ lệch: job chết sau `put` mà trước `commit` thì bảng nói
"chưa" trong khi tệp nói "rồi". Kho tự nó đã là bản kế hoạch.

⇒ Không bảng mới, không migration, không thứ hai để đồng bộ.

### Khoá đoạn: `voice/seg/{owner}/{job_id}/{i}.wav`

**Không** phải hàm băm của nội dung, và đó là một đánh đổi có chủ ý.

Băm nội dung sẽ cho **tái dùng giữa các job** (khách sửa một chữ rồi đọc lại thì
79 đoạn kia dùng lại được) — hấp dẫn hơn hẳn. Nhưng
`platform_core/job_content.py` nhận diện tệp của một job bằng cách tìm
`/{job_id}/` **như một đoạn đường dẫn**. Một khoá theo băm không khớp, và hệ quả
đã được ghi ngay trong `jobs.py`: tệp **không bao giờ bị dọn**, trong khi vòng
bảo trì vẫn chạy và vẫn báo thành công — một rò rỉ hoàn toàn im lặng.

⇒ Tái dùng giữa các job là việc **có thật** nhưng nó cần chính sách lưu giữ
riêng. Mở nó trước khi có chính sách ấy là chọn một tính năng và trả bằng một rò
rỉ.

⭐ Khoá theo `job_id` vẫn đủ cho hai thứ quan trọng nhất, vì nền tảng giữ
**nguyên** `job_id` qua các lần thử lại:

- một đoạn hỏng ⇒ lần thử sau đọc tiếp từ đoạn ấy;
- máy chủ khởi động lại giữa chừng ⇒ y hệt.

Hai cơ chế gặp nhau mà **không cơ chế nào biết về cái kia**: `SO_LAN_THU_JOB`
thử lại cả job với cùng `job_id`; khoá đoạn gắn với `job_id`. Đó là lý do cách
này rẻ.

## Bốn trần đã gỡ, và trần nào chưa

| Trần | Trước | Sau |
|---|---|---|
| **bộ nhớ** | cả bài × 4 bản sao trong RAM sidecar | một đoạn |
| **thời gian** | một lượt HTTP duy nhất cho cả bài | một lượt cho mỗi lô |
| **hạt** | một đoạn hỏng ⇒ mất cả bài | mất đúng đoạn ấy |
| **tiến độ** | không có | lấy từ số đoạn đã xong |
| **trần ký tự công khai** | trần của MODEL | trần của TÀI NGUYÊN |

### Trần công khai: đã mở 03/09/2026, và nó đổi *loại*

Con số cũ nói *"model đọc liền được bao nhiêu trước khi trôi"*. Con số mới nói
*"một job giữ GPU bao lâu thì còn công bằng với người khác"*. Đổi một trần cứng
lấy một trần cứng khác thì vô nghĩa; đổi một trần **chất lượng** lấy một trần
**ngân sách** mới là gỡ đúng thứ. Giá trị và toàn bộ suy luận ở
`apps/ltt_voice/tham_so_cong_khai.py` — không chép lại ở đây.

Ràng buộc chọn ra con số **không phải** thời gian job cũng không phải định dạng
tệp (cả hai còn rộng hơn), mà là **công bằng GPU**: chưa có hàng đợi ưu tiên,
nên một job dài chặn mọi người khác suốt thời gian nó chạy.

Cách đo lại, và điều kiện nâng tiếp, cũng ở tệp ấy. Lệnh:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\do_bai_dai_worktree.ps1
```

⚠️ **`_worktree` chứ không phải bản thường**, và lý do đáng nhớ: dịch vụ
`LTTStudioVoice` đang chạy là bản **đã deploy** ở `C:\LTTPlatform\app`. Cửa
sidecar mới chỉ có trong worktree thì đơn giản là *không có ở đó* — lượt đo đầu
tiên 03/09 nhận `404` cho cả bốn bài ghép và báo chúng là "hỏng". Deploy chỉ để
lấy một số đo là đánh đổi sai, nên script dựng một sidecar **thứ hai** từ
worktree trên một cổng riêng, đo, rồi tắt.

`tools/do_bai_dai.py` đo trên **bản ghép** ở nhiều độ dài, mang theo ba đối
chứng nằm trong chính phép đo:

1. **đối chứng độ dài** — bài một lượt (thứ sản phẩm đang bán hôm nay);
2. **sàn nhiễu người nói** — cắt đôi từng đoạn rồi so hai nửa với nhau;
3. **cùng văn bản, khác vị trí** — corpus lặp vòng, nên đoạn `k` và `k+12` có
   cùng chữ ở hai chỗ khác nhau trong bài. Chênh lệch giữa chúng **không thể do
   nội dung**.

## Những gì CỐ Ý chưa làm

| Việc | Vì sao chưa |
|---|---|
| tái dùng đoạn giữa các job (băm nội dung) | cần chính sách lưu giữ trước, nếu không là rò rỉ kho |
| hàng đợi ưu tiên interactive vs audiobook | chưa có khách nào để tranh GPU; thêm bộ xếp lịch bây giờ là đoán tải |
| RF64/WAVE64 cho tệp > 4 GB | WAV thường tràn ở ~6,5 giờ audio; chưa ai tới đó, nhưng **đây là trần kế tiếp** |
| tải tài liệu lên bằng tệp thay vì thân JSON | trần thân HTTP là chuyện khác trần độ dài tài liệu — xem dưới |

### ⚠️ Trần kế tiếp, để sẵn ở đây cho người sau

1. **Kích thước tệp WAV.** RIFF dùng số 32 bit ⇒ trần ~4 GB ⇒ ở 48 kHz PCM16
   mono là **~6,5 giờ**. Vượt qua thì tệp hỏng *im lặng*: trình phát đọc được
   phần đầu. Cần RF64/WAVE64 hoặc chuyển sang FLAC/MP3 trước ngưỡng đó.
2. **Thân HTTP.** Cloudflare chặn ở 100 MB, và một tài liệu 500.000 ký tự trong
   một JSON là chuyện khác hẳn một tài liệu 500.000 ký tự trong sản phẩm. Đường
   đúng là tải tệp lên / nhập vào Dự án rồi mới đọc.
3. **Thời gian job.** Không còn một lượt HTTP dài, nhưng tổng thời gian job vẫn
   có trần ở nền tảng.
