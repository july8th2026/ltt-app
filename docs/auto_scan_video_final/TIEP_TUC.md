# TIẾP TỤC — điểm dừng 23/09/2026 (chủ dự án tắt máy đổi nguồn)

> Đọc tệp này + `PLAN.md` + `LOI_TONG.md` là đủ để chạy tiếp. Mọi trạng thái nằm
> trong kho, không nằm trong hội thoại.

## Đang ở đâu

- Nhánh tích hợp: **`phien/asv-final`**, HEAD **`d8a39091`**, cây SẠCH.
- ⛔ **Chưa có gì trên `main`. Chưa deploy.** Đúng đề bài (§24): đích là
  `READY_FOR_OWNER_REVIEW`.
- 15 làn đã gộp. Test: 2190 đạt / 2 đỏ — cả hai là `test_448` (báo cáo nghiệm
  thu cũ), chỉ xanh lại khi nghiệm thu mới chạy xong.

## Bốn việc đang dở (dừng giữa chừng, tệp còn trên đĩa)

| làn | worktree | trạng thái khi dừng |
|---|---|---|
| nghiem-thu | `D:\LTTSTUDIOSAPP-asvf-nghiem-thu` | Lượt A (v3, zh→vi, giữ hình + AUTO_MATCH) đang chạy lại; đã có 1 commit riêng (sửa T2 làm tròn) |
| gui | `D:\LTTSTUDIOSAPP-asvf-gui` | 1 tệp sửa dở — đang viết hai hàm `cho_giao_dien` |
| qc-hinh | `D:\LTTSTUDIOSAPP-asvf-qc-hinh` | 3 tệp sửa dở — đang thêm `phan_hoi_qc` vào `hieu_canh.loi_nhac_canh` |
| no-ky-thuat | `D:\LTTSTUDIOSAPP-asvf-no-ky-thuat` | 5 tệp sửa dở — F-08/F-09 xong phần mã, đang chạy phép kiểm chuỗi migration trên SQLite |

⚠️ Không commit hộ chúng: bản sửa đang dở, và một commit "nửa vời" trên nhánh
làn làm người đọc sau tưởng đó là ý đồ.

## Chạy tiếp thế nào

1. Kiểm máy: `python tools\tai_may.py` + `python tools\cua_so_yen.py trang-thai`.
   Khoá treo sau khi tắt máy được **lượt sau tự đoạt** — đừng dọn tay.
2. Mở lại 4 làn (worktree còn nguyên), mỗi làn đọc `BRIEF_CHUNG.md` + brief của nó.
3. Nghiệm thu: chạy lại **lượt A**, rồi B, C, D theo `FINAL_REAL_JOB_REPORT` còn thiếu.
4. Sau khi 4 làn xong: gộp → chạy **L1** (`gate.py --doi`) cho phần việc của phiên
   → chấm `SCORECARD.md` → rà soát độc lập → `READY_FOR_OWNER_REVIEW`.

## Hai việc CHỜ CHỦ DỰ ÁN

- **F-03**: cột `gioi` trống ở cả 25 giọng kho dùng chung ⇒ AUTO_MATCH `en` vẫn
  không ràng được giọng trên production. Cần duyệt điền cho 16/17 giọng `en`
  (trừ Robin — giới tính khai không khớp cao độ đo được). Đây là **ghi CSDL
  production**, chưa ai chạm.
- **Nghe thử** hai giọng tiếng Anh được chọn (Douglas, Clara) — chưa ai nghe.

## Ghi chú bất thường cần theo dõi

- **PostgreSQL bị giết đột ngột lúc 12:31**, không có bản ghi tắt máy — làn
  nghiệm thu phát hiện, **không phải nó gây ra**. Nếu lặp lại thì tìm nguyên nhân
  trước khi tin bất kỳ lượt chạy nào quanh giờ đó.
- Luật máy đổi 23/09 (đã áp dụng): `chay_nang.py` giữ **một khoá `cpu_nhieu`**
  (toàn máy một lượt nặng), trần `-n` **7**, `so_loi` khai theo `-n` thật.
- Venv tạm `D:\ocrb` (~3 GB) của làn OCR chưa xoá được (lệnh xoá bị chặn quyền).
