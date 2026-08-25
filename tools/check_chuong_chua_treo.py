"""check_chuong_chua_treo.py — chuông đã đúc mà chưa ai treo.

## 🔴 VÌ SAO TỆP NÀY TỒN TẠI — bốn ca, cùng một hình dạng

Audit 2026-08-26 tìm ra bốn lỗi tưởng như độc lập. Đo ra thì chúng là **một**:

| | Máy móc có sẵn? | Có ai gọi không? |
|---|---|---|
| Giữ chỗ credit treo | `usage.reconcile` đếm được | ❌ chỉ test + một CLI thủ công |
| Biên lợi nhuận âm | `costing.scan_for_alerts` đủ docstring, test, `__all__` | ❌ **không gì gọi** |
| Sao lưu | `backup.ps1` thiết kế đúng, tách bí mật | ❌ chưa từng chạy |
| Link 404 trong nav | `anhnoibo` đã biết cách tránh và **đã viết ra lý do** | ❌ chưa thành phép kiểm |

⛔ **Một hàm cảnh báo không được cắm vào đâu trông Y HỆT một hàm cảnh báo đang
chạy** — cho tới ngày cần nó. Nó có docstring, có test, có trong `__all__`. Mọi
dấu hiệu bề ngoài của một thứ đang hoạt động, trừ chính việc hoạt động.

Cụ thể: cảnh báo *"nền tảng đang bán dưới giá vốn"* đã nằm trong mã suốt thời
gian nền tảng bán ảnh ở **45–57 % giá vốn trong 22 ngày**. Nó không im vì nó
hỏng. Nó im vì **không ai cắm dây**.

## 💡 CHỖ TỰ NGHĨ — ghi rõ vì nó là chỗ yếu nhất

Ý đầu tiên là bắt mục *"Còn tồn đọng"* trong `NHAT_KY.md` phải mang mã hạng mục.
**Bỏ ý đó**, vì hai lý do:

1. 104 mục hiện có đều là văn xuôi tự do ⇒ ép mã là **dọn quá khứ**, trong khi
   bánh cóc phải **chặn tương lai**.
2. Một phép kiểm phán xét văn phong sẽ kêu sai liên tục, và một máy dò kêu suốt
   ngày là một máy dò bị tắt trong tuần đầu — đúng cái bẫy `test_307` đã cảnh.

Hình dạng THẬT của bốn ca trên không phải "ghi chép thiếu mã". Nó là: **một hàm
quét/cảnh báo tồn tại mà không đường thực thi nào gọi tới**. Cái đó đo được bằng
máy, không cần phán xét gì.

⇒ Phép kiểm này tìm **hàm quét/cảnh báo** trong `platform_core/` và đòi mỗi hàm
có ít nhất một người gọi **ngoài** chính module của nó và **ngoài** `tests/`.

## ⛔ Giới hạn — nói thẳng để không ai tin quá

Nó **không** bắt được ca sao lưu (kịch bản PowerShell) và ca link-404 (một bài
học nằm trong chú thích). Nó bắt được **hai ca nguy hiểm nhất**, và bắt chắc
chắn. Một phép kiểm hẹp mà đúng có giá trị hơn một phép kiểm rộng mà đoán.

    python tools/check_chuong_chua_treo.py
    python tools/check_chuong_chua_treo.py --update   # sau khi ĐÃ cắm dây
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
MOC = pathlib.Path(__file__).resolve().parent / "chuong_baseline.json"

#: Tên hàm mang nghĩa "đi tìm chuyện bất thường rồi báo". Danh sách này CỐ Ý hẹp:
#: mỗi tiền tố ở đây đều là một động từ tìm-kiếm, không phải một động từ tính-toán.
#: Một hàm tính toán không được gọi thì chỉ là mã chết; một hàm CẢNH BÁO không
#: được gọi là một sự im lặng bị hiểu nhầm thành bình yên.
TIEN_TO = ("scan_", "quet_", "reconcile", "sweep", "kiem_tra_dinh_ky",
           "_alerts", "raise_alerts", "tim_bat_thuong")

#: Quét ở đâu. Chỉ `platform_core/` — nơi các máy dò sống.
KHU = "platform_core"

#: Nơi lời gọi ĐƯỢC TÍNH. `tests/` cố ý KHÔNG có ở đây: đó chính là cái bẫy —
#: `costing.scan_for_alerts` CÓ test, và test đó là thứ duy nhất gọi nó.
NGUOI_GOI = ("platform_core", "server", "apps", "job_worker.py",
             "codex_sidecar_main.py")


def _tep(khu: str):
    d = GOC / khu if (GOC / khu).is_dir() else None
    if d is None:
        f = GOC / khu
        return [f] if f.is_file() else []
    return [f for f in sorted(d.rglob("*.py")) if "__pycache__" not in f.parts]


def tim_ham_canh_bao() -> dict[str, str]:
    """Trả {ten_ham: duong_dan} cho mọi hàm quét/cảnh báo cấp module."""
    ra: dict[str, str] = {}
    for f in _tep(KHU):
        try:
            cay = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for n in cay.body:                      # chỉ hàm cấp module
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            ten = n.name
            if ten.startswith("__"):
                continue
            if any(t in ten for t in TIEN_TO):
                ra[ten] = f.relative_to(GOC).as_posix()
    return ra


def tim_nguoi_goi(ten_ham: set[str]) -> dict[str, set[str]]:
    """Trả {ten_ham: {tep goi no}} — chỉ tính lời gọi thật `x(...)`."""
    goi: dict[str, set[str]] = {t: set() for t in ten_ham}
    for khu in NGUOI_GOI:
        for f in _tep(khu):
            rel = f.relative_to(GOC).as_posix()
            try:
                cay = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for n in ast.walk(cay):
                if not isinstance(n, ast.Call):
                    continue
                fn = n.func
                ten = getattr(fn, "id", None) or getattr(fn, "attr", None)
                if ten in goi:
                    goi[ten].add(rel)
    return goi


def quet() -> list[dict]:
    ham = tim_ham_canh_bao()
    goi = tim_nguoi_goi(set(ham))
    treo = []
    for ten, o_dau in sorted(ham.items()):
        # ⛔ TINH CA NGUOI GOI CUNG MODULE. Ban dau toi loai chung (`c != o_dau`)
        #    va no cho ra 6 duong tinh GIA ngay lap tuc: `_quet_giu_cho_treo` CO
        #    duoc goi — tu `_mot_luot_bao_tri`, cung tep. Duoc goi tu cung module
        #    van la DUOC CAM DAY.
        #
        # ⚠️ Cai gia phai tra, noi thang: mot ham chet duoc goi boi mot ham chet
        #    khac trong cung module se lot. Phep kiem dung se la kha-nang-voi-toi
        #    tu diem vao that. Chua lam, vi phep kiem hep ma DUNG co gia tri hon
        #    phep kiem rong ma doan — va no van bat duoc ca nguy hiem nhat:
        #    ham co docstring + test + `__all__` ma KHONG AI ngoai test goi.
        if not goi[ten]:
            treo.append({"ham": ten, "o": o_dau})
    return treo


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--update", action="store_true")
    args = p.parse_args()

    treo = quet()
    khoa = sorted(f"{t['o']}::{t['ham']}" for t in treo)

    if args.update:
        MOC.write_text(json.dumps(khoa, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print(f"da ghi moc: {len(khoa)} ham chua duoc goi")
        return 0

    moc = json.loads(MOC.read_text(encoding="utf-8")) if MOC.is_file() else []
    moi = sorted(set(khoa) - set(moc))
    da_cam = sorted(set(moc) - set(khoa))

    for k in khoa:
        print(f"{'!!' if k in moi else '  '} {k}")

    if da_cam:
        print(f"\nDA CAM DAY: {', '.join(da_cam)}")
        print("Chay --update de ha moc.")

    if moi:
        print(f"\nTHEM {len(moi)} ham quet/canh bao KHONG AI GOI:")
        for k in moi:
            print(f"   {k}")
        print("\nMot ham canh bao khong duoc cam vao dau trong Y HET mot ham")
        print("canh bao dang chay. Cam no vao `_mot_luot_bao_tri` hoac mot")
        print("duong thuc thi that — hoac xoa no di.")
        print("RESULT: FAIL")
        return 1

    print(f"\nChua duoc goi: {len(khoa)} | moc: {len(moc)} — khong them.")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
