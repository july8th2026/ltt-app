---
name: ltt-gate
description: Dùng khi cần chọn cấp kiểm trong kho LTTSTUDIOSAPP — test nhắm, L1 (gate.py --doi), L2 (--pham-vi), L3 (gate.py), khép sau L3 đỏ, hoặc cần gate xanh để gộp main/deploy. Trỏ về hợp đồng vận hành §4, không định nghĩa nhịp mới.
---

# Chọn cấp kiểm (gate) — LTTSTUDIOSAPP

Nguồn chân lý DUY NHẤT: `docs/00_LTT_OPERATING_CONTRACT.md` §4 (bảng "Các cấp"),
§7 (gộp `main`), §8 (deploy). Skill này chỉ là con trỏ — mâu thuẫn thì hợp đồng thắng.
Đọc §4 trước khi bấm bất kỳ lệnh gate nào.

## Bảng tra nhanh (tên lệnh; điều kiện đầy đủ ở hợp đồng)

| Cấp | Lệnh | Hợp đồng |
|---|---|---|
| T | `python -m pytest <tệp…> -q` · `python tools\check_<x>.py` | §4.1 — skill `ltt-test-nham` |
| L1 | `python tools\gate.py --doi [--tu <sha>]` | §4.1, §4.6, §7, §8 |
| L2 | `python tools\gate.py --pham-vi <tp>` | §4.1, §4.10, §8 |
| L3 | `python tools\gate.py` | §4.2 — một lần, tổng kết phiên |

## Điều hay nhầm (đọc lại đúng mục)

- L3 thuộc tổng kết phiên; còn việc chưa làm thì chưa bấm — §4.2.
- ⛔ Không chạy L3 lần hai trên một nhánh; `gate.py` từ chối — §4.6.
- L3 đỏ: sửa tại chỗ, chạy lại đúng phép đỏ (gate in sẵn), khép bằng
  `gate.py --doi --tu <sha lượt L3>` — §4.6.
- Deploy giữa phiên cần L1/L2 xanh trên đúng SHA deploy; test nhắm một mình
  không đủ — §8.
- ⛔ Không dùng `--quick`, `--vong-lap` trong nhịp chuẩn; `test_nhanh.py` rồi
  `gate.py` là trả tiền hai lần — §4.3.
- Gate là công cụ ra phán quyết, không phải công cụ dò lỗi — §4.2.
- Trong lúc gate chạy: không ghi vào cây đang chạy gate — §4.9.

## Trước khi bấm

1. Gate mọi chế độ là lệnh nặng → bộ kiểm máy ở skill `ltt-may-production`
   (`docs/QUY_TAC_CHAY_LENH_NANG.md` §2).
2. Commit hết; frontend đổi thì build trước (`AGENTS.md` §4b).
3. Bước nào tồn tại, chứng minh gì: `tools/gate.py::_steps` — đừng đoán.

Nhiệm vụ được giao cấm chạy gate (vd. phiên phụ) thì tuân theo nhiệm vụ đó.
