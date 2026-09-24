# D5/B — yêu cầu SINH cho làn có đường giọng sống

> ⛔ Làn `timeline` ⛔ **không có** `LTT_VOICE_SIDECAR_TOKEN` và ⛔ **không đi tìm** —
> đó là **bí mật** (`CLAUDE.md`). Tệp này là **đầu bài**, ⛔ không phải lệnh chạy.

## Cần gì

| | |
|---|---|
| câu thử | `cau_thu.json` — **12 câu**, lấy từ **bản dịch nền thật**, khe **sau khi gộp ≤5** |
| tốc độ | **1,00** (⭐ ĐỐI CHỨNG) · 1,15 · 1,25 · 1,35 · 1,45 |
| mỗi mức | ⭐ **≥ 3 lượt** (đường sinh ⛔ không tái lập) — báo **trung vị**, ⛔ không một con số |
| giọng | **đúng giọng sản phẩm** đang dùng cho ASV. ⛔ Đổi giọng là đổi câu hỏi |

⭐ Câu thử **⛔ không phải câu bịa**: 12 câu trải hệ số nén **0,88× → 1,81×**,
**16–95 âm tiết**, **65–427 ký tự** — trong đó **6 ca nặng nhất** của ba phim.
⚠️ Câu `0,88×` là **đối chứng**: nó vốn đã vừa, nên nếu nó cũng hỏng ở tốc độ cao
thì vấn đề ⛔ **không** nằm ở việc nén để cho vừa.

## Đo gì trên mỗi tệp sinh ra

```
CER  = vòng ASR: chép lời tệp sinh ra -> so với văn bản gốc đã đưa vào
       (⭐ đúng nếp `tools/do_bai_dai.py` — ⛔ không tự nghĩ phép đo mới)
DNSMOS = điểm chất lượng, bộ có sẵn trong `qc-venv`
```

## Trả về gì

```json
{"theo_toc_do": {"1.00": {"<ma_cau>": {"cer": 0.09, "dnsmos": 3.5}, ...},
                 "1.15": {...}, "1.25": {...}, "1.35": {...}, "1.45": {...}}}
```

`<ma_cau>` = trường `ma` trong `cau_thu.json`. ⇒ `doc_duong_cong.py` đọc thẳng.

## ⛔ CÁCH ĐỌC ĐÃ CHỐT TRƯỚC — ⛔ đừng đổi sau khi thấy số

`doc_duong_cong.py` (commit này đi **TRƯỚC** lô âm thanh đầu tiên — tra `git log`):

```
ngưỡng "gãy" TỰ HIỆU CHUẨN trên độ tản (IQR) của chính mức 1,00
GÃY tại X  <=>  (1) trung vị hiệu THEO CẶP vượt độ tản ấy
           VÀ   (2) ≥ 2/3 số câu cùng xấu đi   (phép dấu)
```

⭐ ⛔ **Không mượn một hằng số nào** (*"CER > 0,02"*, *"DNSMOS tụt > 0,3"* đều là số
mượn — đúng họ `N-34` đã mắc **bốn lần** trong phiên này).

Bánh cóc: `tests/test_2063_asv_tran_giong.py` — 6 phép, gồm **tiêm** một bước nhảy
thật (phải bắt, và bắt **đúng mức**) và **đối chứng ngược** (một câu ngoại lệ
⛔ **không** đủ để gọi là gãy).

## ⚠️ Giới hạn phải khai cùng mọi kết quả

> ASR đo **DỄ NGHE HIỂU**, ⛔ **không** đo **DỄ CHỊU**. Một giọng nhanh có thể
> **hiểu được** mà **khó nghe**. DNSMOS đỡ một phần, ⛔ **không thay được tai người**.

⇒ Câu dùng được: *"ở 1,35, độ nghe hiểu và điểm chất lượng máy chấm **⛔ chưa gãy**"*.
⛔ Câu **KHÔNG** được viết: *"đã xác nhận 1,35 nghe ổn"*.

## Vì sao đáng làm

`TRAN_TANG_TOC = 1.15` là **số mượn Subdub**, ⛔ chưa ai đo trên giọng ta (`N-45`) —
và là **trần chặt nhất** trong ba dự án tham chiếu. Sau khi gộp ≤5:

| trần | % khe còn phải rút gọn |
|---|---|
| 1,15 (nay) | **26,5 %** |
| 1,30 | **16,9 %** |

⇒ ⭐ Nếu trần thật của giọng ta cao hơn 1,15, ta tới **16,9 %** mà ⛔ **không chạm một
chữ nào** của bản dịch — rẻ hơn hẳn cần gạt LLM (`len_ratio < 0,85` ⇒ chrF++ **39,31**
so với **49,85**).
