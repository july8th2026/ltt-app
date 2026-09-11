# Pha 22 — Dubbing adaptation + fit

**Trạng thái: XONG phần làm được ở máy này — ĐO NGƯỠNG chờ lượt nghiệm thu thật
kế tiếp.** Ngày 11/09/2026.

Đề bài: *VoiceBinding trước rewrite · rút/nới có giới hạn · thử lại/tái dùng từng
đoạn · từ điển phát âm · benchmark ngưỡng fit.*

## 0. Đo trước: phần lớn đã có từ V4

| đề bài | hiện trạng |
|---|---|
| rút/nới có giới hạn | **có** — bậc thang bốn nấc của `nan_cho_vua` (đo → viết lại riêng đoạn → co giãn có trần → đánh dấu cần sửa) |
| thử lại / tái dùng từng đoạn | **có** — phục hồi mức đoạn trong `giai_doan_giong`, `test_441` |
| từ điển phát âm | **có** — `tu_dien`, `test_460` |
| VoiceBinding trước rewrite | **đúng trong mã, chưa ai chốt** |
| benchmark ngưỡng fit | **lỗ** — `DUNG_SAI_DAI = 0,08` tự khai *"CHƯA ĐO trên dữ liệu thật"* |

## 1. VoiceBinding trước rewrite — nay được chốt

Lời thoại được viết lại cho vừa tốc độ đọc của **một** giọng. `test_476` chốt bằng
AST: `giai_giong` được gọi **đúng một lần** trong `chay`, và **trước** mọi nấc của
bậc thang; hàm viết lại không tự đọc lại `giong_id` từ `settings`. Đối chứng: tiêm
một lần giải giọng thứ hai vào vòng lặp đoạn ⇒ **đỏ**.

## 2. Dữ liệu thật đầu tiên — và vì sao nó chưa đủ để đo ngưỡng

Báo cáo nghiệm thu tái sinh ở pha 27 (model thật + giọng thật, 11/09):

| cánh | đoạn | vừa | co giãn | **cần sửa** | lệch lớn nhất |
|---|---|---|---|---|---|
| giữ hình | 6 | 3 | 1 | **2** | +56,2% |
| cắt | 6 | 4 | 0 | **2** | +56,2% |

Nhìn thô: **4/12 đoạn đi hết bậc thang mà vẫn không vừa**, có đoạn dài hơn khe 56%.
Nhưng cả hai cánh cùng `lech_lon_nhat = 0,5618` và cùng `so_doan_dung_lai = 2` —
rất có thể là **cùng hai đoạn tái dùng**, tức 2 đoạn khác nhau chứ không phải 4.

⛔ **Không kết luận được từ dữ liệu này**, và lý do là chính lỗ của pha này: tóm
tắt giai đoạn chỉ có con số **gộp**. Sổ cái chỉ lưu trạng thái + số vòng, không lưu
giây/khe. Không có cách nào hỏi *"bao nhiêu đoạn nằm gần ngưỡng 0,08"*.

## 3. Việc đã làm: tóm tắt mang TỪNG ĐOẠN

`nan_cho_vua.tom_tat` nay ghi `tung_doan`: mã · trạng thái · giây · khe · lệch ·
số vòng · hệ số co giãn. **Không** ghi lời thoại — tóm tắt là siêu dữ liệu của giai
đoạn, lời thoại là nội dung của khách (đối chứng: tiêm rò `chu` ⇒ **đỏ**).

⭐ Đoạn tái dùng vẫn được `ket_luan` tính lại từ **độ dài thật** của tệp cũ, nên
dữ liệu từng đoạn đầy đủ cả với đoạn lấy từ cache.

⚠️ **Không nâng `PHIEN_BAN_NAN`**: đây là hình dạng báo cáo, không phải chính sách —
không đoạn nào đổi trạng thái hay đổi âm thanh. Hằng số đó cũng không nằm trong vân
tay engine, nên báo cáo nghiệm thu hiện tại vẫn hiệu lực.

## 4. Còn nợ — một hành động cụ thể

**Lượt nghiệm thu thật kế tiếp sẽ tự mang dữ liệu từng đoạn.** Khi đó mới trả lời
được: bao nhiêu đoạn nằm trong khoảng (0,08 ; 0,15], nấc co giãn cứu được bao
nhiêu, và 0,08 có đúng chỗ không. Lượt ấy cần quyền đọc `secrets` (UAC) — cùng
đường đã chạy ở pha 27.

n = 12 là quá nhỏ cho một ngưỡng. Đo ngưỡng thật cần một lô nguồn đa dạng — việc
của pha 33.
