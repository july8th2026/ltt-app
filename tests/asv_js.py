"""Doc ma nguon client cua man Studio — mot TAP TEP, khong phai mot tep.

Pha 06 tach `server/static/asv.js` thanh tam module duoi `server/static/asv/`.
Sau do moi phep kiem hoi *"client co lam X khong"* phai hoi ca tap, chu khong
hoi mot tep.

🔑 Danh sach lay tu `server/templating.py:ASV_STUDIO_JS` — **chinh bo ma trang
   phat ra the `<script>` va chinh bo ma `asset_ver` bam**. Nen tap ma phep
   kiem doc luon la tap ma trinh duyet nap, khong phai mot ban chep se troi.

⛔ Doc bang **AST**, khong bang `import server.templating`. Import keo theo ca
   ung dung va chay `_tinh_asset_ver()` luc import; mot phep kiem tinh khong
   duoc tra cai gia do. Cung ly do ma `cong-cu-tools-doi-stdout-vo-pytest` da
   ghi lai: doc AST thay vi import.
"""
from __future__ import annotations

import ast
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
TINH = GOC / "server" / "templating.py"
STATIC = GOC / "server" / "static"


def ds_module() -> tuple[str, ...]:
    """Ten cac module theo DUNG thu tu trang nap chung."""
    cay = ast.parse(TINH.read_text(encoding="utf-8"))
    for n in cay.body:
        if not isinstance(n, ast.Assign):
            continue
        for dich in n.targets:
            if isinstance(dich, ast.Name) and dich.id == "ASV_STUDIO_JS":
                gt = ast.literal_eval(n.value)
                return tuple(str(x) for x in gt)
    raise AssertionError(
        "khong thay `ASV_STUDIO_JS` trong server/templating.py — man Studio "
        "khong con mot nguon danh sach module duy nhat")


def duong(ten: str) -> Path:
    return STATIC / ten


def doc(ten: str | None = None) -> str:
    """Noi dung MOT module, hoac ca tam noi lai theo thu tu nap.

    ⚠️ Ban noi lai chi tra loi duoc cau *"client CO lam X"*. Cau *"module NAO
       lam X"* thi phai truyen `ten` — va do la cau manh hon, nen dung no khi
       phep kiem thuc su noi ve mot khoi cu the.
    """
    if ten is not None:
        return duong(ten).read_bytes().decode("utf-8")
    return "\n".join(duong(m).read_bytes().decode("utf-8") for m in ds_module())
