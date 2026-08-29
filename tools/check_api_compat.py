"""So sanh be mat cong khai voi ban chuan da dong bang.

    python tools\\check_api_compat.py             # kiem tra, khong sua gi
    python tools\\check_api_compat.py --accept    # chap nhan thay doi, ghi lai

Vi sao can: moi manh cua hop dong deu da ton tai o dau do — route trong
`server/api/inventory.py`, hinh dang tool sau `contract_hash`, ma loi trong
registry, loai su kien trong `webhooks`. Cai chua ton tai la mot cach hoi "co gi
doi khong, va doi do co duoc phep khong". Nen mot thay doi pha vo tuong thich co
the len tau vi khong ai diff mot thu ma khong ai gom lai.

`docs/PUBLIC_API/CONTRACT_BASELINE.json` la ban chuan. No nam trong git, nen
thay doi hop dong hien ra trong diff cua pull request — dung cho no phai hien ra.

`--accept` KHONG phai mot cach de qua cua. No ghi lai ban chuan, va viec ghi lai
do la mot thay doi trong git ma nguoi review nhin thay. Y la: pha vo tuong thich
phai la mot quyet dinh CO CHU DICH, khong phai mot tai nan.

Nam trong `tools/gate.py`.
"""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BASELINE = ROOT / "docs" / "PUBLIC_API" / "CONTRACT_BASELINE.json"

def _utf8_stdout() -> None:
    """Console cua Windows khong mac dinh UTF-8, ma cac thong bao o day co dau.

    Goi TRONG `main()` chu khong o cap module: file nay cung duoc `import` tu
    test, va doi `sys.stdout` luc import se cuop mat co che bat output cua
    pytest — dung nghia den, no lam vo phien chay test.
    """
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True)


def _current() -> dict:
    """Be mat ma ma nguon dang phuc vu, doc lap voi cau hinh may nay.

    Bat MOI tool ma app khai `api_exposed`, khong phai chi nhung tool
    deployment nay bat: hop dong la thu chung ta hua voi khach, khong phai thu
    mot may tinh tinh co dang chay.
    """
    from platform_core.public_api.config import load_public_api_config
    from platform_core.public_api.contract import snapshot
    from platform_core.registry import discover
    from server.api.inventory import API_V1_ROUTES

    apps = discover()
    names = ",".join(sorted(
        tool.name for item in apps if not item.error
        for tool in item.manifest.tools if tool.api_exposed))
    config = load_public_api_config({"LTT_PUBLIC_API": "1",
                                     "LTT_PUBLIC_API_TOOLS": names})
    return snapshot(config, routes=API_V1_ROUTES, apps=apps)


def _write(payload: dict) -> None:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    BASELINE.write_text(text + "\n", encoding="utf-8", newline="")


def main() -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser()
    parser.add_argument("--accept", action="store_true",
                        help="ghi lai ban chuan (thay doi CO CHU DICH)")
    args = parser.parse_args()

    from platform_core.public_api.contract import compare

    current = _current()

    if not BASELINE.is_file():
        _write(current)
        print(f"Da tao ban chuan: {BASELINE.relative_to(ROOT)}")
        print(f"{len(current['routes'])} route, {len(current['tools'])} tool, "
              f"{len(current['error_codes'])} ma loi.")
        return 0

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    result = compare(baseline, current)

    if args.accept:
        _write(current)
        print(f"Da ghi lai ban chuan ({len(result.differences)} thay doi, "
              f"{len(result.breaking)} pha vo tuong thich).")
        for item in result.differences:
            print("  " + item.line())
        if result.breaking:
            print("\nNHO: dat cho no mot phien ban moi hoac mot ke hoach ngung "
                  "ho tro, va ghi vao docs/PUBLIC_API/CHANGELOG.md.")
        return 0

    if result.clean:
        print(f"Hop dong khong doi: {len(current['routes'])} route, "
              f"{len(current['tools'])} tool, "
              f"{len(current['error_codes'])} ma loi.")
        return 0

    for item in result.additive:
        print("  " + item.line())
    if not result.breaking:
        print(f"\n{len(result.additive)} thay doi CONG THEM (khong pha vo "
              f"tuong thich). Chay `--accept` de ghi vao ban chuan.")
        return 0

    print("\nPHA VO TUONG THICH:")
    for item in result.breaking:
        print("  " + item.line())
    print(
        "\nMot tich hop dang chay se hong vi nhung thay doi tren.\n"
        "Neu la co y: dat phien ban moi (hoac lich ngung ho tro), ghi vao\n"
        "docs/PUBLIC_API/CHANGELOG.md, roi chay:\n"
        "    python tools/check_api_compat.py --accept\n"
        "Lan ghi lai do se hien trong diff — dung cho no phai hien ra.")
    _canh_bao_ban_chuan_ban()
    return 1


def _canh_bao_ban_chuan_ban() -> None:
    """Noi ro khi ban chuan trong cay KHAC ban da commit.

    ## Vi sao dong nay ton tai

    `tests/test_209_versioning_status.py` phai ghi vao CHINH tep nay de kiem
    duong day that cua `--accept`. No co `try/finally` de hoan nguyen — nhung
    `finally` KHONG chay khi tien trinh bi giet (gate qua gio, Ctrl-C, worker
    chet). Mot luot chay bi ngat de lai tep ban, va lan chay sau do vi mot ly do
    khong lien quan gi toi viec dang lam:

        [BREAKING] version: api_version changed v0 -> v1

    Ngay 29/08 dieu do xay ra HAI LAN trong mot buoi sang, cho HAI phien khac
    nhau, va ca hai deu mat thoi gian truy nguoc. Thong bao tren khong sai — no
    chi khong noi ra kha nang de xay ra nhat.

    ⛔ Ham nay KHONG tu sua tep va KHONG lam diu ket qua: gate van do. No chi
       them mot cau de nguoi doc biet cho ma nhin.
    """
    import subprocess

    try:
        commit = subprocess.run(
            ["git", "show", f"HEAD:{BASELINE.relative_to(ROOT).as_posix()}"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            timeout=15)
    except (OSError, subprocess.SubprocessError):
        return                      # khong co git thi thoi, dung phan doan
    if commit.returncode != 0:
        return
    if commit.stdout == BASELINE.read_text(encoding="utf-8"):
        return                      # ban chuan dung bang ban commit -> that su la thay doi ma

    print(
        "\n⚠️  Ban chuan trong cay KHAC ban da commit.\n"
        "    Neu ban khong co y sua no, day rat co the la RAC cua mot luot test\n"
        "    bi ngat: `test_209` ghi vao chinh tep nay va chi hoan nguyen o\n"
        "    `finally` — thu do khong chay khi tien trinh bi giet.\n"
        "    Dau hieu nhan ra: ten co tien to `ghost_` hoac HTTP 418.\n"
        "    Kiem bang:  git diff docs/PUBLIC_API/CONTRACT_BASELINE.json\n"
        "    Neu la rac:  git checkout -- docs/PUBLIC_API/CONTRACT_BASELINE.json\n"
        "⛔  DUNG chay `--accept` de cho qua: no ghi lai ban chuan theo ma hien\n"
        "    tai, nen mot thay doi pha vo tuong thich THAT se bi nuot mat.")


if __name__ == "__main__":
    raise SystemExit(main())
