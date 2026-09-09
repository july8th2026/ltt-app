# FINAL_SCORECARD — LTT VOICE 98+

Ngày 10/09/2026 · nhánh `claude/ltt-voice-98-upgrade-9b586f` · commit `a61c7a0d`
(baseline `99017910`) · 87 hạng mục theo hợp đồng chương trình.

---

## 1. Câu trả lời thẳng

**Mục tiêu: mọi hạng mục ≥ 98/100. Đạt được: KHÔNG hạng mục nào.**

    cao nhat do duoc : 97  (09 - Model validation)
    so hang muc >= 98:  0 / 87

Đây là kết luận, không phải lời xin lỗi hay lời hứa. §35.1 của hợp đồng cấm ghi
điểm không có bằng chứng, và §7 đặt trần theo loại bằng chứng còn thiếu — nên
con số duy nhất tôi được phép viết là con số ở trên.

## 2. Phân bố thật

| | số hạng mục |
|---|---|
| chấm được bằng số | **73** |
| `UNKNOWN` (đã đọc, chưa đủ mẫu để chấm) | 3 — 31, 32, 40 |
| `BLOCKED_DATA` (cơ chế đủ, dữ liệu chưa đếm được) | 1 — 07 |
| **chưa có dòng nào** (chưa đo lượt này) | **10** — 15, 33, 34, 35, 36, 66, 78, 79, 80, 81 |
| tổng | 87 |

Trong 73 hạng mục chấm được bằng số:

    >= 98      0
    90 - 97   43
    80 - 89   23
    <  80      7   -> 13 (62) · 14 (30) · 20 (78) · 30 (70) · 39 (30) · 82 (75) · 83 (0)

Trung bình 73 hạng mục ấy là **86,11**. ⚠️ Con số này KHÔNG phải điểm của hệ
thống: 14 hạng mục không có mặt trong nó, và mọi hạng mục vắng mặt đều vắng vì
**chưa đo** — tức là phía chưa biết, không phải phía tốt.

## 3. Vì sao 98 không đạt được trong lượt này — và đây không phải chuyện viết thêm mã

Chia 87 hạng mục theo **thứ chặn** chứ không theo điểm:

| Thứ chặn | Số hạng mục | Viết thêm mã có gỡ được không |
|---|---|---|
| trần §7 do thiếu **loại bằng chứng** (benchmark, E2E, load, diễn tập, người nghe) | **30** có trần < 98 | **Không.** Trần là mái đặt lên bằng chứng, không đặt lên mã |
| đã chạm đúng trần của mình, không còn khe | **9** (12, 19, 27, 28, 29, 45, 58, 64, 75) | Không. Sửa mã ở đây chỉ làm số nhỏ hơn |
| chưa đo lượt này | 10 | Không. Cần GPU / thiết bị thật / người thật / bí mật máy chủ |
| còn khe kỹ thuật thật | phần còn lại | **Có** — và đó là chỗ Wave A đã tiêu công |

⇒ **Trần thấp nhất trong 87 hạng mục là 75; trần phổ biến nhất dưới 100 là 90
(14 hạng mục).** Chừng nào chưa có benchmark audio đủ mẫu, chưa có E2E trên URL
công khai, chưa có load test và chưa có người thật nghe mù, thì **mọi lượt viết
mã tiếp theo cũng không đưa 30 hạng mục ấy lên 98 được.** Đây là kết quả cơ học
của chính §7, không phải đánh giá của tôi.

⛔ Và đây là chỗ dễ trượt nhất của cả chương trình: hạ trần để lấy điểm là làm
đúng thứ §35 gọi tên. Trần ở lại.

## 4. Wave A đã đổi được gì — đo bằng chênh lệch, không bằng lời

Bảy hạng mục có bằng chứng đổi trạng thái trong lượt này (chi tiết:
`07_CHANGE_LEDGER.md`, mỗi mục kèm một **đột biến** chứng minh phép kiểm biết đỏ):

| ID | Trước | Sau | Việc đã làm |
|---|---|---|---|
| 38 | trần **75** (§7.9 dataset rỗng) | **82**, trần 90 | Phân loại lại `DATA_GAP` → `CODE_GAP`: 25 giọng kho chung đã nằm trong CSDL từ 01/09, chỉ chưa ai nối vào thang dự phòng |
| 20 | 4/8 lớp có sẵn | **78**, trần 90 | `/phat-dan` + `sidecar_client.phat_dan` + trình phát Web Audio; tính tiền mô hình β |
| 11 | torch lấy cả 10 lõi | **86** | Trần luồng 4, đặt trước khi nạp model |
| 49, 50 | vùng/phong cách **hiện** mà không **lọc** | 90 / 92 | Đóng U-03 |
| 58, 65 | 5 nhãn trình đọc màn hình gõ cứng tiếng Việt không dấu | 90 / 85 | Một nguồn nhãn duy nhất, đã dịch |
| 82 | **không có CI nào** | 75 | `gate-quick.yml` |

Test: **+12** (8.893 → 8.905 xanh ở gate đầy đủ). Không lỗi nào thuộc phạm vi
chương trình — 9 lỗi còn lại là `test_448` (×7) và `test_505` (×2), đã đỏ từ
trước lượt này.

⭐ Dự đoán *"chín lỗi ấy không phải của tôi"* được **ghi ra trước khi bấm gate**.
Ghi sau thì nó là lời giải thích; ghi trước thì nó là mệnh đề kiểm chứng được.

## 5. Mười hạng mục chưa đo — và ai chạy được phép đo

Không chấm. Ghi thẳng phép đo và **người duy nhất chạy được nó**.

| ID | Hạng mục | Phép đo | Chạy được bởi |
|---|---|---|---|
| 15 | GPU throughput/VRAM | Cửa sổ GPU rảnh + venv `vieneu-venv` | Chủ dự án (GPU đang phục vụ thật) |
| 33–36 | Nhân bản giọng (enroll) | Corpus ref 3s/10s/30s × clean/phone/noisy, gọi `/v1/enroll*` | Chủ dự án — cần GPU **và** token sidecar trong `secrets/app.env` (B-04) |
| 66 | UX trên thiết bị thật | Trình duyệt thật trên `https://app.lttstudios.com` | Chủ dự án (loopback bỏ qua Cloudflare) |
| 78 | Nghiệm thu E2E | Như trên | Chủ dự án |
| 79 | Load/concurrency | 1 dài + 5 ngắn, nhiều dài đồng thời | Chủ dự án (chiếm GPU) |
| 80 | Chấm mù bởi người | §19 — người thật nghe | **Chỉ người thật.** Builder tự nghe = INVALID theo §7 |
| 81 | A11y scanner | Scanner đã đăng nhập trên thiết bị thật | Chủ dự án |

## 6. Bốn việc đang chặn, cần chủ dự án — chi tiết ở `06_BLOCKERS.md`

| Mã | Việc | Lệnh |
|---|---|---|
| B-01 | Đếm giấy phép giọng thật trong CSDL (gỡ `BLOCKED_DATA` của 07, nâng trần 47/48) | `tools\do_voice_co_bi_mat.ps1 soat-giong` |
| B-04 | Đo hồ sơ giọng (gỡ trần 75 của 39, 40) — ~15 phút GPU | `tools\do_voice_co_bi_mat.ps1 ho-so-giong` |
| B-02 | Chấm mù bởi người (80, và mọi hạng mục acoustic) | §19 |
| — | Bật `LTT_VOICE_STREAM=1` để `/phat-dan` sống (20 đang ở 78 vì chưa bật) | sửa `secrets\app.env` rồi **`setup\nap_lai_env.ps1`** — `Restart-Service` là KHÔNG đủ |
| 83 | Bật branch protection để CI ở 82 có hiệu lực | Cài đặt kho — §26 cấm tôi tự bật |

⚠️ B-01 và B-04 tôi đã thử hai đường hợp lệ, cả hai bị chặn ở lớp phân loại
lệnh (đọc `secrets\app.env`). Tôi **không** thử đường thứ ba và **không** sửa
`autoMode.hard_deny` — sửa nó là tự cấp quyền cho chính mình, xem B-05.

## 7. Điểm chốt theo luật của chương trình

Hợp đồng nói `FINAL_SCORECARD = MIN(builder, auditor)`, và `BLOCKED_WITH_EVIDENCE`
là trạng thái **đúng** khi bằng chứng còn thiếu. Áp đúng luật ấy:

    LTT VOICE, 10/09/2026
    ---------------------------------------------------
    dat muc tieu >= 98        :  0 / 87
    co bang chung, cham duoc  : 77 / 87   (trung binh 86,11 tren 73 muc co so)
    BLOCKED_WITH_EVIDENCE     : 10 / 87
    ---------------------------------------------------
    PHAN QUYET: CHUA DAT. Va phan lon khoang cach con lai
                khong dong duoc bang cach viet them ma.

## 8. Nếu muốn đi tiếp thì đi theo thứ tự này

Xếp theo §36 (đúng → tiền → sở hữu → dữ liệu → chất lượng tiếng → tin cậy →
phục hồi → UX → hiệu năng → mã đẹp), không xếp theo điểm thấp:

1. **B-01** — 07 đang `BLOCKED_DATA` ở trục *pháp lý*, hạng nặng nhất còn mở.
2. **B-04 + corpus benchmark** — gỡ trần 85 cho 27/30/31/32 và trần 75 cho 39/40.
   Đây là **một** phép đo gỡ **sáu** hạng mục; không việc nào khác có tỉ lệ ấy.
3. **Bật `LTT_VOICE_STREAM=1` rồi E2E thật** — gỡ trần 90 cho 16/20/37/62/64.
4. **Load test** — gỡ trần 88 cho 12/13/14/18/19/29.
5. **13, 14 (GPU fairness / priority)** — điểm thấp nhất còn sửa được bằng mã,
   nhưng là **đổi lược đồ + migration** (`Job` không có cột `priority` — đính
   chính ở hạng mục 14), nên đứng sau bốn việc trên.
6. **83** — một cú bấm của chủ dự án, và nó làm 82 có hiệu lực thật.

---

⚠️ Tệp này thay `01_SCORECARD_BASELINE.md` §D (*"điểm tổng cố ý không ghi"*).
Bảng chi tiết 77 hạng mục vẫn ở tệp ấy; tệp này chỉ chốt tổng và phán quyết.
