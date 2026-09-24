# B1 — cổng NGHE CHÉP (`transcribe`)

> Làn `asvf-nghiem-thu-v2`, 24/09/2026. Mắt xích **đầu tiên** của thang cổng —
> mọi bước sau đứng trên văn bản nguồn nó tạo ra.

## 1. NGƯỠNG — viết TRƯỚC khi đo, ⛔ không nới

```
ĐẠT khi:  WER ≤ 0,25  VÀ  CER ≤ 0,12
          trên ≥ 3 phim CÓ TIẾNG NÓI (món ăn · cắm trại · PUBG)
```

⛔ **Không đạt ⇒ sửa rồi đo lại. KHÔNG nới ngưỡng.** Nếu ngưỡng sai thì phải nói ra
là ngưỡng sai *trước* khi nhìn số, không phải sau.

**Vì sao mức đó.** CER đo được trước đây là **0,018** trên **1 clip 33 dòng** ở một
đường **KHÁC** (faster-whisper CPU, văn bản đối chiếu **tay**). Hardsub có thể **rút
gọn** so với lời nói, nên ngưỡng phải lỏng hơn số cũ — nhưng 0,25/0,12 vẫn là một
**ngưỡng**, không phải một mô tả.

⛔ **Phim súng hơi (`真人气枪游戏…`) KHÔNG dùng** — B0 ghi *"không chắc có giọng"*.
Một phim không có tiếng nói không đo được đường nghe chép, và đưa nó vào sẽ cho một
con số trông như thất bại của engine.

## 2. ⚠️ GIỚI HẠN CỦA CHÂN LÝ NỀN — đọc cùng lúc với mọi con số ở §4

Hardsub **không phải** bản ghi lời nói. Nó là **bản chữ do người làm phim viết**, và
nó có thể:

| | hệ quả lên WER |
|---|---|
| **rút gọn** lời nói (bỏ từ đệm, gộp câu) | WER **cao giả** — ASR chép đúng thứ người nói, hardsub không có |
| viết lại cho gọn màn hình | WER cao giả |
| bỏ hẳn đoạn không quan trọng | WER cao giả |
| sai chính tả / thiếu dấu | WER cao giả, **không** phải lỗi ASR |

⇒ **Mọi con số WER ở §4 phải đọc kèm dòng này.** Một WER 0,3 ở đây **không** chứng
minh ASR sai 30 % — nó nói *"ASR và hardsub khác nhau 30 %"*, và phần nào thuộc về ai
thì phép đo này **không tách được**.

⭐ Chiều lệch là **một phía**: các nguyên nhân trên đều đẩy WER **lên**. Nên một WER
**thấp** là bằng chứng mạnh (ASR khớp cả một chân lý nền không hoàn hảo); một WER
**cao** là bằng chứng **yếu**, và phải soi tay trước khi quy cho engine.

## 3. Cách chuẩn hoá trước khi so

*(điền sau Bước 3 — ⛔ ghi ra, đừng để trong mã)*

## 4. Kết quả

*(điền sau Bước 4 — mỗi dòng kèm: engine thật, card có được cấp không)*

| phim | WER | CER | số dòng nguồn | số dòng hardsub | engine | card |
|---|---|---|---|---|---|---|
| | | | | | | |

## 5. Phán quyết

*(điền sau Bước 6)*

## 6. ⚠️ Nếu bench hỏng: ghi TRIỆU CHỨNG trước, quy nguyên nhân sau

Đây là lượt **đầu tiên** đường `asr` chạy thật (Task 5 vừa đổi mặc định), nên xác
suất gặp một **tiền đề chưa khai** là cao.

⛔ **Đừng kết luận *"đường `asr` hỏng"*.** Lượt A ngày 24/09 là tiền lệ: một tiền đề
chưa ai khai (AUTO_MATCH đòi nguồn **có tiếng nói**) bị đọc thành *"AUTO_MATCH là
đường chết"*, và mất ba vòng mới tách ra được. Ghi đúng cái **thấy** — mã lỗi, giai
đoạn, số — rồi mới đi tìm **vì sao**.
