# B2 — XÁC THỰC BỘ CHẤM ngữ nghĩa (làn `xac-thuc-cham`, 24/09/2026)

> **Câu hỏi duy nhất:** lượt chạy thật chấm **44/95 mục (46%)** là *dịch sai*.
> **46% đó là bản dịch tệ thật, hay bộ chấm quá tay?**
>
> Hai câu trả lời dẫn tới hai việc hoàn toàn khác nhau — sửa **bản dịch** hay sửa
> **bộ chấm**. Chưa biết mà đi sửa là có thể thay cả cách dịch để chữa một bộ chấm
> báo bừa.

## 1. NGƯỠNG — viết TRƯỚC khi chạy dòng lệnh nào

```
Bộ chấm ĐÁNG TIN khi: tỉ lệ báo động giả ≤ 15% trên ≥ 100 cặp FLORES zh→vi.
> 15% ⇒ con số 44/95 KHÔNG dùng được để kết luận về bản dịch, và việc tiếp theo
        là sửa BỘ CHẤM, không phải sửa bản dịch.
```

**Đối chứng âm (bắt buộc, không được bỏ):** ≥ 30 cặp đã làm hỏng có chủ ý,
tách hai loại — **lật nghĩa** và **sai thực thể**, ≥ 15 cặp mỗi loại.

```
Bộ chấm còn SỐNG khi: tỉ lệ bắt lỗi tiêm ≥ 50% ở MỖI loại.
< 50% ở một loại ⇒ ta MÙ ở đúng loại đó, và mọi con số báo động giả đo được
      trên loại đó chỉ nói "bộ chấm ít nói", không nói "bộ chấm đúng".
```

🔴 **Vì sao phải có đối chứng âm:** không có nó, *"tỉ lệ báo động giả 0%"* có thể
chỉ nghĩa là bộ chấm **không bao giờ báo gì** — và ta sẽ kết luận nó đáng tin
trong khi nó đã chết.

⚠️ `L_DICH.md` §3 ghi MetricX có **AUC 0,61** cho **lật nghĩa** zh→vi — gần như
tung đồng xu. Nếu lớp `qc_ai` cũng yếu ở lật nghĩa thì **ta mù ở đúng chỗ tệ
nhất**, và đó là phát hiện quan trọng hơn con số tổng.

## 2. Cách đo (Q6 — chủ dự án chốt)

FLORES-200 có cặp `zho_Hans` ↔ `vie_Latn` **do người dịch**. Đưa cặp
(nguồn zh, bản dịch chuẩn vi) cho **chính** lớp chấm ngữ nghĩa của ASV
(`qc_ai.loi_nhac_ngu_nghia` → `ai.goi` → `qc_ai.doc_ngu_nghia`). Mỗi lần nó phán
*"dịch sai"* trên một bản dịch của **người** ⇒ **báo động giả theo định nghĩa**.

⚠️ **Cổng đang áp `--temp 1.0` và `seed` KHÔNG có hiệu lực** (đo 24/09). ⇒ mỗi cặp
chấm **≥ 3 lượt**, lấy **trung vị** (đa số trên 3 lượt), và báo cáo **kèm dải**
(min–max của từng lượt). ⛔ Một lượt đơn lẻ không được dùng làm phán quyết.

## 3. Kết quả

*(điền sau khi chạy — mục này để trống có chủ ý cho tới khi có số thật)*

## 4. Phán quyết

*(điền sau khi chạy)*
