"""test_nhanh.py — chạy toàn bộ pytest song song, KẾT QUẢ Y HỆT lượt nối tiếp.

    python tools/test_nhanh.py            # toan bo, song song
    python tools/test_nhanh.py --lf       # chi nhung test vua do
    python tools/test_nhanh.py -k credit  # loc theo ten
    python tools/test_nhanh.py -n 8       # chon so worker

## ⭐ VÌ SAO CÓ TỆP NÀY

Bộ test đầy đủ mất **2 giờ**, và điều đó đổi cách người ta làm việc theo hướng
xấu: nó biến `pytest` từ một vòng lặp thành một sự kiện. Hệ quả đo được ngày
26/08 — hạng mục H40 đóng mà **chưa lượt `pytest` đầy đủ nào chạy xong**, và
lượt đầy đủ đầu tiên chạy sau đó tìm ra **36 lỗi**, trong đó một phép kiểm
**chưa bao giờ xanh** trên máy này.

Một bộ test quá chậm để chạy là một bộ test không ai chạy.

## Hai việc, và việc thứ nhất quan trọng hơn

**① Bỏ `fsync` cho SQLite tạm** *(nằm ở `platform_core/db.py`, không ở đây)*.
Đo được: `create_all` 44 bảng mất **2,16s** trên tệp thường và **0,05s** với
`synchronous=OFF` + `journal_mode=MEMORY` — **43 lần**. Vì gần như mọi test dựng
một CSDL mới, đó là hơn ba giờ trong tổng số hai giờ… nghe vô lý cho tới khi
nhớ rằng phần còn lại chạy song song được.

Đo thật trên một lát cắt 109 test: **193s → 42s**, chỉ nhờ hai dòng pragma.

**② Chạy song song** — việc của tệp này.

## ⛔ VÀ ĐÂY LÀ PHẦN KHÓ: SONG SONG KHÔNG ĐƯỢC ĐỔI KẾT QUẢ

Đã khảo sát tĩnh trước khi bật, không bật rồi chờ hỏng:

| Rủi ro | Thực tế đo được |
|---|---|
| Test ghi vào cây kho | **3 tệp** — xem `TEP_NOI_TIEP` |
| Cổng mạng cố định | **0** — mọi chỗ `bind` đều dùng cổng `0` (OS cấp) |
| Trạng thái toàn cục | `monkeypatch` là của từng tiến trình ⇒ xdist an toàn |
| CSDL dùng chung | mỗi test một SQLite trong `tmp_path` |

`--dist loadfile` gửi **trọn một tệp cho một worker**, nên thứ tự trong tệp giữ
nguyên — nhiều tệp ở đây dựa vào điều đó.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent

#: ⛔ BA TỆP PHẢI CHẠY NỐI TIẾP, MỘT TIẾN TRÌNH.
#:
#: Chúng ghi đè tệp **thật** trong kho rồi khôi phục trong `finally`:
#:
#:   test_209  `tools/*_baseline.json`
#:   test_210  `sdk/*` (TS + Python)
#:   test_306  `locale/en/LC_MESSAGES/messages.po` + `check_dich_thieu.moc`,
#:             và nó còn tạo một tệp test giả trong `tests/` rồi xoá
#:
#: Chạy song song với phần còn lại thì một worker có thể đọc trúng lúc tệp đang
#: bị sửa. Đó không phải giả thuyết: ngày 26/08 chính `test_306` đã làm hỏng
#: **hai** lượt gate (≈4 giờ) chỉ vì khôi phục không đúng từng byte và đúng cả
#: dấu thời gian.
#:
#: ⭐ Thêm một tệp cùng loại thì phải khai vào đây. `test_309` chốt danh sách
#:    này, nên quên khai sẽ làm gate đỏ chứ không lặng lẽ chạy song song.
TEP_NOI_TIEP = (
    "tests/test_209_versioning_status.py",
    "tests/test_210_sdk_ecosystem.py",
    "tests/test_306_banh_coc_bo_qua_va_dich.py",
)

BO_QUA = ("--ignore=tmp", "--ignore=test-results")


def _chay(argv: list[str], nhan: str) -> tuple[int, float]:
    print(f"\n{'─' * 70}\n  {nhan}\n{'─' * 70}", flush=True)
    t0 = time.monotonic()
    ma = subprocess.run(argv, cwd=GOC).returncode
    return ma, time.monotonic() - t0


def main() -> int:
    p = argparse.ArgumentParser(description="Chay pytest song song, ket qua y het.")
    p.add_argument("-n", default="auto",
                   help="so worker (mac dinh: auto = so nhan CPU)")
    p.add_argument("--lf", action="store_true",
                   help="chi chay nhung test vua do (--last-failed)")
    p.add_argument("-k", default="", help="loc theo ten test")
    p.add_argument("--noi-tiep", action="store_true",
                   help="chay mot tien trinh — de doi chieu ket qua")
    args, con_lai = p.parse_known_args()

    chung = [sys.executable, "-m", "pytest", "-q", *BO_QUA, *con_lai]
    if args.lf:
        chung.append("--lf")
    if args.k:
        chung += ["-k", args.k]

    t_dau = time.monotonic()

    if args.noi_tiep:
        ma, _ = _chay(chung, "MOT TIEN TRINH (doi chieu)")
        print(f"\nTONG: {time.monotonic() - t_dau:.0f} giay")
        return ma

    # ── Pha 1: song song, TRU cac tep lam ban cay ────────────────────────────
    loai = [f"--deselect={t}" for t in TEP_NOI_TIEP]
    ma1, t1 = _chay(chung + ["-n", args.n, "--dist", "loadfile", *loai],
                    f"PHA 1 — song song ({args.n} worker), tru {len(TEP_NOI_TIEP)} tep")

    # ── Pha 2: cac tep ghi vao cay kho, noi tiep ─────────────────────────────
    # ⛔ Chay ca khi pha 1 do: bo qua chung se lam bao cao cuoi noi doi ve do phu.
    co = [t for t in TEP_NOI_TIEP if (GOC / t).is_file()]
    ma2, t2 = (0, 0.0)
    if co:
        ma2, t2 = _chay(chung + co, f"PHA 2 — noi tiep ({len(co)} tep ghi vao cay kho)")

    tong = time.monotonic() - t_dau
    print(f"\n{'═' * 70}")
    print(f"  pha 1 song song : {t1:6.0f} giay")
    print(f"  pha 2 noi tiep  : {t2:6.0f} giay")
    print(f"  TONG            : {tong:6.0f} giay ({tong / 60:.1f} phut)")
    print(f"{'═' * 70}")

    ma = ma1 or ma2
    print("RESULT: PASS" if ma == 0 else "RESULT: FAIL")
    if ma == 0:
        print("\n⚠️  Day KHONG thay the `tools/gate.py`. Gate con chay 21 phep kiem")
        print("    tinh + ba bo test frontend + bat bien da tien trinh.")
    return ma


if __name__ == "__main__":
    raise SystemExit(main())
