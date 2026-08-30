"""do_current_truth.py - dumps the real state of every app/tool, from the registry.

    python tools\\do_current_truth.py            # bang Markdown
    python tools\\do_current_truth.py --json      # cho may doc

WHY THIS IS A SCRIPT AND NOT A HAND-WRITTEN TABLE.

  `USER_DECISIONS.md` cua goi API Expansion V2, muc 7: *"Khong hardcode mot danh
  sach tai lieu doc lap neu source contract/runtime da co the sinh du lieu
  dong."* Mot bang trang thai go tay la ban sao thu hai cua su that, va no se
  lech dung vao hom ta quen.

  Du an nay da tra gia cho dung dieu do nhieu lan: `CLAUDE.md` hang H35 noi sai
  so tool dang mo **hai lan**, cung mot huong nguy hiem (bao dong trong khi dang
  mo). Lan sua thu hai (30/08) thay con so bang mot LENH DO. Tep nay la cung
  nguyen tac, ap cho ca danh muc.

! DOC-ONLY. Khong ghi gi, khong goi mang, khong can khoa. An toan chay bat cu luc nao.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def _cong_dang_mo() -> set:
    """Tool nao operator DA bat, doc tu cau hinh dang chay.

    ⛔ Fail-closed cua Q92: `LTT_PUBLIC_API_TOOLS` rong = khong tool nao mo.
       `api_exposed` cua ToolSpec la DIEU KIEN CAN, khong phai du.
    """
    import os

    tho = os.environ.get("LTT_PUBLIC_API_TOOLS", "")
    return {t.strip() for t in tho.split(",") if t.strip()}


def thu_thap() -> list:
    from platform_core.public_api.protocol import mode_of_tool
    from platform_core.registry import discover

    mo = _cong_dang_mo()
    ra = []
    for muc in sorted(discover(), key=lambda m: m.manifest.slug):
        m = muc.manifest
        if muc.error:
            ra.append({"app": m.slug if m else "?", "loi": muc.error})
            continue
        for t in m.tools:
            hd = getattr(t, "api_contract", None) or {}
            # ⛔ `execution_mode` KHONG nam tren ToolSpec — no dan xuat tu
            #    `api_contract` qua `mode_of_tool`, mac dinh ASYNC_JOB. Doc
            #    thang thuoc tinh se cho ra rong o MOI dong, va mot cot rong
            #    dong loat trong rat giong "chua ai khai" chu khong giong
            #    "ta doc sai cho".
            ra.append({
                "app": m.slug,
                "tool": t.name,
                "job_type": getattr(t, "job_type", "") or "",
                "che_do": mode_of_tool(hd),
                "api_exposed": bool(getattr(t, "api_exposed", False)),
                "khach_thay": bool(getattr(t, "customer_visible", False)),
                "operator_bat": t.name in mo,
                "models": sorted((hd.get("models") or {}).keys()),
                # Hop dong RONG khac han hop dong CO ma khong khai models.
                "hop_dong_rong": not hd,
                "admission": getattr(t, "admission_resource", "") or "",
                "slots": getattr(t, "admission_slots", None),
                "surface": getattr(m, "surface", ""),
                "lifecycle": getattr(m, "lifecycle", ""),
                "public_web": bool(getattr(m, "public", False)),
            })
        if not m.tools:
            ra.append({
                "app": m.slug, "tool": "(khong khai ToolSpec nao)",
                "job_type": ",".join(getattr(m, "job_types", ()) or ()) or "-",
                "che_do": "-", "api_exposed": False, "khach_thay": False,
                "operator_bat": False, "models": [], "admission": "",
                "slots": None, "hop_dong_rong": True,
                "surface": getattr(m, "surface", ""),
                "lifecycle": getattr(m, "lifecycle", ""),
                "public_web": bool(getattr(m, "public", False)),
            })
    return ra


def _trang_thai(d: dict) -> str:
    """Mot nhan, va no phai phan biet duoc BA thu khac nhau.

    ⭐ "Chua mo" gop chung ba tinh huong rat khac nhau, va gop chung la cach
       nguoi ta ket luan sai: co the app CHUA khai hop dong, co the da khai ma
       operator chua bat, co the co y khong bao gio mo.
    """
    if d.get("loi"):
        return "LOI_NAP"
    if not d["api_exposed"]:
        return "HOP_DONG_RONG" if d.get("hop_dong_rong") else "CHUA_MO_API"
    if not d["operator_bat"]:
        return "DA_KHAI_CHUA_BAT"
    return "DANG_MO"


def bang_markdown(ds: list) -> str:
    dong = ["| app | tool | trạng thái | chế độ | job_type | models | admission |",
            "|---|---|---|---|---|---|---|"]
    for d in ds:
        if d.get("loi"):
            dong.append(f"| `{d['app']}` | — | **LOI_NAP** | | | | {d['loi'][:60]} |")
            continue
        mo = ", ".join(f"`{x}`" for x in d["models"]) or "—"
        ad = d["admission"] or "—"
        if d["slots"]:
            ad += f" ×{d['slots']}"
        dong.append(
            f"| `{d['app']}` | `{d['tool']}` | {_trang_thai(d)} | "
            f"{d['che_do'] or '—'} | `{d['job_type'] or '—'}` | {mo} | {ad} |")
    return "\n".join(dong)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    ds = thu_thap()
    if a.json:
        print(json.dumps(ds, ensure_ascii=False, indent=1))
        return 0

    print(bang_markdown(ds))
    dem = {}
    for d in ds:
        dem[_trang_thai(d)] = dem.get(_trang_thai(d), 0) + 1
    print("\nTong: " + " | ".join(f"{k}={v}" for k, v in sorted(dem.items())))
    print("\n⚠️ `DANG_MO` doc tu bien LTT_PUBLIC_API_TOOLS cua TIEN TRINH NAY.")
    print("   Muon biet production dang mo gi thi hoi may chu:")
    print("   GET /api/v1/tools  (nho User-Agent — xem CLAUDE.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
