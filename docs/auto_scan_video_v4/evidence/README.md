# Bằng chứng ASV V4 — hai loại tệp, và một cái tên từng nói dối

Thư mục này chứa **hai loại tệp khác hẳn nhau**, và trước 2026-09-05 không có
cách nào nhìn ra loại nào là loại nào từ cái tên.

## Cuộn — luôn mô tả bản đang xét

| Tệp | Ai ghi |
|---|---|
| `nghiem_thu_hien_hanh.json` | `tests/test_448_asv_v4_e2e_nghiem_thu.py` |
| `hieu_nang_hien_hanh.json` | `tests/test_450_asv_v4_hieu_nang.py` |
| `suat_gpu_hien_hanh.json` | `tests/test_450_asv_v4_hieu_nang.py` |
| `asr_cuda_hien_hanh.json` | `tests/test_450_asv_v4_hieu_nang.py` |

Mỗi lượt chạy **ghi đè** tệp của nó. Đó là **cố ý**, và pha 28 đã nói rõ vì sao:
bằng chứng ghi trước một commit chạm vào đường chạy thì **không còn mô tả bản
đang xét**. Pha 28 sinh lại chúng ở RC chính vì lý do đó, và gọi việc ấy là
"không phải một thủ tục".

## Đóng băng — ảnh chụp một thời điểm, không ai ghi lại

`00_gate_baseline.txt` · `04_gate.txt` · `05_gate.txt` · `B3_gate.txt` ·
`do_n6.json` · `gate_n6.txt`

Không mã nguồn nào trỏ tới chúng. Chúng là bản dump giữ nguyên.

## 🔴 Vì sao đổi tên bốn tệp cuộn (2026-09-05)

Chúng từng tên `22_nghiem_thu.json`, `24_hieu_nang.json`, `24_suat_gpu.json`,
`24_asr_cuda.json` — **mang số pha**, y hệt các tệp đóng băng bên trên. Cái tên
hứa "bằng chứng của pha 22"; cơ chế thì ghi đè mỗi lượt.

Hai điều đó không thể cùng đúng dưới một cái tên, và hậu quả đo được:

* `22_REPORT.md` trích số từ tệp và **liên kết tới nó**. Sau lượt chạy thật ở
  pha 29, những con số ấy không còn trong tệp nữa. Liên kết vẫn sống, nội dung
  vẫn đúng — chỉ là nó không còn là thứ báo cáo 22 mô tả.
* `27_REPORT.md` và `28_REPORT.md` cũng trỏ vào **cùng một đường dẫn** và mỗi
  cái nói nó chứa số của **mình**. Ba báo cáo, một tệp, một nội dung.

⭐ Không cái nào trong ba báo cáo sai khi được viết. Cái sai là một cái tên
   **không có cách nào tự biết nó đã cũ** — đúng cơ chế đã làm bảng "cái gì
   đang sống" trong `CLAUDE.md` nói sai năm lần.

⚠️ Nên khi đọc một con số trích trong `reports/*.md`, hãy tin **con số in trong
   báo cáo** (nó đóng băng cùng báo cáo), đừng cho rằng mở tệp cuộn ra sẽ thấy
   lại đúng con số ấy.
