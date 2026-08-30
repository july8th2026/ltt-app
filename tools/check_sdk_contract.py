"""Moi route cong khai phai duoc SDK phu — hoac duoc khai la CO Y khong phu.

    python tools\\check_sdk_contract.py

Vi sao can: mot SDK thieu mot route khong bao gio bao loi. No chi lam nguoi dung
tu viet lay phan do, roi ho viet sai retry hoac quen Idempotency-Key — dung hai
thu SDK sinh ra de lo. Va "quen" trong khong khac gi "co y bo qua", nen file nay
bat phai NOI RA la cai nao.

Doi chieu `server/api/inventory.py` (nguon su that ve route) voi khai bao phu
trong chinh hai file SDK. Khai bao nam TRONG SDK chu khong o day, vi mot danh
sach dat ben ngoai la mot danh sach se troi dat.

Cu phap khai bao, viet ngay tren phuong thuc hoac o cuoi file:

    # @covers GET /tools
    # @covers-not GET /openapi.json — spec, khong phai loi goi cua nguoi dung

Nam trong `tools/gate.py`.
"""
from __future__ import annotations

import io
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: ⭐ SEAM CHO TEST — va do la SUA LOI, khong phai tien nghi.
#:
#:    `test_210` phai chay CHINH cong nay (mot cong chi kiem qua thu vien la mot
#:    cong khong ai kiem day dien). De lam vay no sua THANG hai tep SDK roi tra
#:    ve trong `finally`. Hong theo hai duong, ca hai da xay ra:
#:
#:    ① Tien trinh bi giet giua chung (gate qua gio, Ctrl-C, `| head` -> SIGPIPE)
#:      thi tep o lai **thieu mot dong `@covers`** — va lan chay sau bao
#:      "SDK khong khop hop dong", mot thong bao dung ngu phap nhung sai nguyen
#:      nhan. Da can that 30/08: `sdk/typescript/ltt-public-api.ts` mat dong
#:      `// @covers GET /models` va gate do vi mot loi khong ton tai.
#:    ② `gate.py` chay cong nay SONG SONG voi bo test ⇒ do NGAU NHIEN.
#:
#: ⛔ Bien nay CHI de test dung. Ma chay that khong bao gio dat no.
_THU_MUC_THU = __import__("os").environ.get("LTT_SDK_DIR")
_GOC_SDK = pathlib.Path(_THU_MUC_THU) if _THU_MUC_THU else ROOT / "sdk"

SDKS = {
    "python": _GOC_SDK / "python" / "ltt_public_api.py",
    "typescript": _GOC_SDK / "typescript" / "ltt-public-api.ts",
}

_COVERS = re.compile(r"@covers\s+([A-Z]+)\s+(\S+)")
_COVERS_NOT = re.compile(r"@covers-not\s+([A-Z]+)\s+(\S+)")

def _utf8_stdout() -> None:
    """Console cua Windows khong mac dinh UTF-8, ma cac thong bao o day co dau.

    Goi TRONG `main()` chu khong o cap module: file nay cung duoc `import` tu
    test, va doi `sys.stdout` luc import se cuop mat co che bat output cua
    pytest — dung nghia den, no lam vo phien chay test.
    """
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True)


def declared(path: pathlib.Path) -> tuple[set, dict]:
    """(routes covered, {route: reason it is deliberately not covered})."""
    text = path.read_text(encoding="utf-8")
    covered = {f"{method} {route}" for method, route in _COVERS.findall(text)}
    skipped = {}
    for match in _COVERS_NOT.finditer(text):
        method, route = match.group(1), match.group(2)
        line = text[match.end():text.find("\n", match.end())]
        skipped[f"{method} {route}"] = line.strip(" —-\t")
    return covered, skipped


def main() -> int:
    _utf8_stdout()
    from server.api.inventory import API_V1_PREFIX, API_V1_ROUTES

    wanted = {f"{route.method} {route.path.replace(API_V1_PREFIX, '')}"
              for route in API_V1_ROUTES}

    problems = []
    for name, path in SDKS.items():
        if not path.is_file():
            problems.append(f"{name}: khong thay {path.relative_to(ROOT)}")
            continue
        covered, skipped = declared(path)

        unknown = (covered | set(skipped)) - wanted
        for route in sorted(unknown):
            problems.append(
                f"{name}: khai phu route khong ton tai: {route}")

        missing = wanted - covered - set(skipped)
        for route in sorted(missing):
            problems.append(
                f"{name}: {route} chua khai — them `@covers` neu da lam, "
                f"hoac `@covers-not ... — ly do` neu co y bo")

        for route, reason in sorted(skipped.items()):
            if not reason:
                problems.append(
                    f"{name}: {route} khai bo qua ma khong noi ly do")
        print(f"{name}: {len(covered)} phu, {len(skipped)} co y bo, "
              f"{len(wanted)} route")

    if problems:
        print("\nSDK khong khop hop dong:")
        for line in problems:
            print("  " + line)
        print("\nMot SDK thieu route khong bao loi — no chi de nguoi dung tu "
              "viet lay,\nroi ho viet sai retry hoac quen Idempotency-Key.")
        return 1
    print("SDK khop hop dong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
