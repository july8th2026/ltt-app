# Thang cổng từng bước — siết một mắt xích một lúc

> Chủ dự án chốt 24/09/2026, **thay** cách làm cũ. Cách cũ: chạy cả chuỗi rồi đi
> tìm lỗi. Cách mới: **siết từng mắt xích, bước nào thật sự đạt mới sang bước sau.**

## Vì sao đổi — bằng dữ liệu của chính ta, không bằng sở thích

| lượt | kết quả | nó nói được gì về mắt xích nào |
|---|---|---|
| `NEN_V3` | B/C ra tệp dùng được, QC T3/T5 đỏ, A chết | 5 lỗi ở 4 tầng khác nhau cùng lúc |
| `NT_CUOI_B` | `done` sau **67 phút** — nhưng 85 khiếm khuyết còn lại | chuỗi chạy được ≠ từng bước đúng |
| `NT_CUOI_A` | chết ở `content_process` vì một tiền đề chưa khai | lỗi nằm ở bước 5, phát hiện sau 3 phút chạy bước 1–4 |

⇒ Một lượt đầy-chuỗi trả về **một mớ lỗi ở nhiều tầng**, và **không** trả lời được
*"mắt xích nào là gốc"*. Nó cũng đắt: 67 phút cho một câu trả lời, và mọi bước sau
bước hỏng thì **không được đo** (bị che).

⛔ **Và nó làm ta nhầm „chạy xong" với „đúng".** Lượt B về `done` trong khi hệ thống
tự chấm 44/95 câu là dịch chưa sát. Nếu chỉ nhìn `run.status` thì đó là một thành công.

## Giao thức cho MỖI bước — năm việc, đúng thứ tự này

```
1. SOÁT MÃ    đọc TRỌN mã vận hành của bước: logic có kín chưa, tham số nào
              là số ĐOÁN, có nhánh nào chết, có tiền đề nào CHƯA KHAI
2. TRA NGUỒN  GitHub/model card/tài liệu engine: cộng đồng có cách tốt hơn không
              (CLAUDE.md luật 10 — tra nguồn TRƯỚC khi tự suy)
3. HỢP ĐỒNG   ghi rõ VÀO / RA / điều kiện tiên quyết / cách hỏng của bước
              ⇒ để sau này xen thêm bước vào giữa mà không phải sửa bước khác
4. SỬA        tối ưu theo 1+2. ⛔ Không đổi nhiều bước một lượt
5. ĐO         bench trên video THẬT của chủ dự án. Có ĐỐI CHỨNG (tiêm lỗi cũ,
              hoặc so với chân lý nền tay). ⛔ Ngưỡng ĐẶT TRƯỚC khi chạy
```

⛔ **Điều kiện đạt phải viết ra TRƯỚC khi đo.** Đặt ngưỡng sau khi thấy số là cách
hợp lý hoá một kết quả tồi. Nếu không đạt: sửa rồi đo lại — ⛔ **không** nới ngưỡng.

⛔ **Không „gần đạt rồi đi tiếp".** Một mắt xích yếu 90% ở đầu chuỗi thì 11 bước sau
đứng trên 90% đó.

## Mười hai mắt xích, và thứ tự siết

Tên giai đoạn lấy từ chính `asv_stage` của lượt thật.

| # | mắt xích | thứ tự siết | đã đo gì | lỗ lớn nhất |
|---|---|---|---|---|
| 0 | **kiểm kê 4 video** | **B0** | ffprobe 22/09 | ⛔ chưa biết phim nào **có tiếng nói**, phim nào chỉ có hardsub |
| 1 | `media_prepare` | B5 | — | |
| 2 | `audio_prepare` (demucs, F0) | B4 | F0 chạy trên card | F0=0 khi phim không có tiếng nói (N-06) |
| 3 | **`transcribe` + định tuyến nguồn lời** | **B1** | OCR CER 0,003 · ASR CER 0,018 (**1 clip, 33 dòng**) | ⛔ **WER chưa đo bao giờ**; hai nhánh whisperx/faster-whisper tham số khác nhau mà **không ai so** |
| 4 | `edit_plan` (cắt cảnh, hiểu cảnh) | B6 | cắt cảnh F1 0,95 | `so_canh=1` ở cả A và B, trong khi lượt nền 6 (N-07) |
| 5 | **`content_process` (DỊCH)** | **B2** | ⛔ **chưa đo trên bản dịch thật** | không glossary · không `seed` · không chốt `temperature` · bộ đo QE **AUC 0,61** cho lật nghĩa |
| 6 | `voice_synthesis` | B3 | WER p50 0,102 · PESQ min 2,72 | 80% thời gian là LLM viết lại, không phải TTS |
| 7 | `timing_align` | B7 | nhịp đọc vi 3,35 / en 3,63 (đo thật) | |
| 8 | `compose` | B8 | LUFS −14,25 / đỉnh −1,69 | |
| 9 | `render` | B9 | T3 sửa xong (`-shortest`) | VMAF **chưa đo** trên nhánh nvenc |
| 10 | `qc` (T1–T18 kỹ thuật) | B10 | 0 mục hỏng ở lượt B | tên `qc_dat` từng nói quá phạm vi (N-02, đã sửa) |
| 11 | `qc_do_luong` | B11 | 14/95 vượt ngưỡng giọng | |
| 12 | `qc_ai` (ngữ nghĩa + hình) | **B2b** | 44/95 ngữ nghĩa · hình **9/9 báo động giả** | ⛔ **bộ chấm chưa được xác thực** — xem dưới |

## Bắt đầu từ đâu, và vì sao

### B0 — kiểm kê 4 video (làm trước mọi thứ, rẻ)

Bốn tệp ở `C:\Users\Thang Tuong\Desktop\TEST VIDEO`, đều là clip mạng tiếng Trung:
món ăn (83 MB) · cắm trại (26 MB) · PUBG (22 MB) · súng hơi (93 MB).

Phải biết cho **từng** tệp: **có tiếng nói không** · **có hardsub không** · có phụ đề
nhúng không · bao nhiêu cảnh. Vì:

- lượt A chết đúng vì phim đó **không có tiếng nói** — ⛔ nếu không biết trước, ta sẽ
  đo bước nghe-chép trên một phim không có gì để chép rồi kết luận sai về bước đó;
- ⛔ và ngược lại: đo bước nghe-chép **chỉ** trên phim có hardsub thì ta đang đo
  đường OCR mà tưởng đang đo đường ASR.

### B1 — văn bản nguồn (`transcribe`)

**Đây là chỗ phải bắt đầu.** Ba lý do, xếp theo sức nặng:

1. **Mọi bước sau đứng trên nó.** Dịch sai vì nguồn sai thì sửa ở dịch là sửa sai chỗ.
   Và 44 mục "dịch sai" ở lượt B **chưa loại trừ** khả năng gốc là văn bản nguồn.
2. **Nó gần như chưa được đo.** Một con số CER trên **một** clip, **33 dòng**. Không
   có WER. Không có phép so hai nhánh engine.
3. Nó rẻ để đo: có chân lý nền bằng tay cho 33 dòng rồi, mở rộng được.

### B2 — dịch, ⛔ và một việc PHẢI làm trước khi sửa gì

⛔ **Xác thực bộ chấm TRƯỚC khi kết luận bản dịch tệ.** Con số 44/95 (46%) là **phán
đoán của một model**, chưa đối chiếu với người. Và model **cùng loại** ở lớp kiểm hình
đã cho **9/9 báo động giả** khi soi tay.

⇒ Lấy ~40 mục bị chấm sai, **đối chiếu tay**, tính tỉ lệ báo động giả. Rẻ, nhanh, và
nó quyết định ta sửa **bản dịch** hay sửa **bộ chấm** — hai việc hoàn toàn khác nhau.

⛔ Đây là bài học `khong-doi-chung-thi-so-khong-khong-phai-phat-hien` áp ngược: một
con số 46% **không** là phát hiện khi chưa có đối chứng.

Sau đó mới tới: chọn model (nghiên cứu đang chạy), glossary + luật tên riêng, chốt
`temperature`, thêm `seed` để bản dịch **tái lập được** — không tái lập thì không đo
được cải thiện.

## Hợp đồng mắt xích — vì sao mục 3 của giao thức quan trọng

Chủ dự án yêu cầu **mỗi bước gói gọn cơ chế, để sau này xen thêm hạng mục vào giữa**.
Muốn vậy mỗi bước phải khai bốn thứ, và khai **cái đang có thật** trong mã:

```
VÀO        : tài sản nào, khoá nào trong `asv_asset`
RA         : tài sản nào, trường nào trong `asv_stage.outputs`
TIÊN QUYẾT : điều kiện gì phải đúng  ⛔ kể cả điều kiện CHƯA AI KHAI
             (N-06: tự khớp giọng ĐÒI nguồn có tiếng nói — chưa ai viết ra)
HỎNG       : mã lỗi ổn định + câu khách đọc được + credit có hoàn hay không
```

⛔ Ghi **bản đồ thật trước**, kể cả chỗ xấu. Thiết kế lại trước khi biết hiện trạng
là cách tạo ra một lớp tương thích cho một thứ chưa ai hiểu.

## Việc GIỮ nguyên, không bị thang này xoá

`N-01` (chặn mở khách: `done` với 85 khiếm khuyết) · `N-06` · `N-07` — **hoãn có chủ ý**,
mỗi cái được trả lời ở đúng bước của nó. ⛔ Không phải bỏ quên.
Mọi bằng chứng đã có (`NT_CUOI_A.md`, `NT_CUOI_B.md`, bảng bốn dòng 85→85) **giữ**:
lượt B vẫn là bằng chứng đầu-cuối đầu tiên của vòng sửa.
