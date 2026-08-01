"""
import_r2_modelark_from_botgemini.py — nhập MỘT LẦN cấu hình R2 + ModelArk AK/SK
từ D:\\BOT GEMINI sang `secrets\\app.env` của nền tảng (H10 + seedance Pha 2).

Nguồn (BOT GEMINI, mã hoá Fernet bằng FERNET_KEY trong `.env` của nó):
- `data/r2_storage.json`   : account_id, access_key_id, bucket (thường), secret_key (mã hoá)
- `data/modelark_asset.json`: access_key, secret_key (mã hoá), region

Ghi ra `secrets\\app.env` các biến của NỀN TẢNG:
- LTT_STORAGE=r2 · LTT_R2_ACCOUNT_ID · LTT_R2_ACCESS_KEY_ID · LTT_R2_SECRET_ACCESS_KEY · LTT_R2_BUCKET
- LTT_MODELARK_ACCESS_KEY · LTT_MODELARK_SECRET_KEY · LTT_MODELARK_REGION

AN TOÀN: secret chỉ ở RAM lúc chuyển; **KHÔNG in giá trị** (chỉ in tên biến +
độ dài). Ghi app.env KHÔNG BOM (Python utf-8). Idempotent: cập nhật khoá đã có,
thêm khoá mới, giữ nguyên các dòng khác.

    C:\\LTTPlatform\\venv\\Scripts\\python.exe ^
        C:\\LTTPlatform\\app\\tools\\import_r2_modelark_from_botgemini.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys


def _bg_decrypt_fn(bg_root: str):
    sec_path = os.path.join(bg_root, "app", "core", "security.py")
    if not os.path.exists(sec_path):
        raise SystemExit(f"Khong thay {sec_path} — dat --bot-gemini dung duong dan.")
    spec = importlib.util.spec_from_file_location("bg_security", sec_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "decrypt"):
        raise SystemExit("security.py cua BOT GEMINI khong co ham decrypt().")
    return mod.decrypt


def _maybe_decrypt(dec, value: str) -> str:
    """Giải mã nếu là chuỗi Fernet; nếu đã là plain (vd access_key_id) thì giữ nguyên."""
    v = (value or "").strip()
    if not v:
        return ""
    try:
        out = dec(v)
        return out if out else v
    except Exception:      # noqa: BLE001 — không giải mã được → coi như plain
        return v


def _cap_nhat_env(path: str, updates: dict) -> None:
    """Cập nhật KEY=VALUE trong app.env (giữ dòng khác), ghi KHÔNG BOM."""
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    con_lai = dict(updates)
    out = []
    for ln in lines:
        s = ln.strip()
        if s and not s.startswith("#") and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in con_lai:
                out.append(f"{k}={con_lai.pop(k)}")
                continue
        out.append(ln)
    if con_lai:
        out.append("")
        out.append("# R2 + ModelArk (nhap tu BOT GEMINI, H10 + seedance)")
        for k, v in con_lai.items():
            out.append(f"{k}={v}")
    with open(path, "w", encoding="utf-8") as fh:   # utf-8 Python = KHONG BOM
        fh.write("\n".join(out) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot-gemini", default=r"D:\BOT GEMINI")
    ap.add_argument("--app-env", default=r"C:\LTTPlatform\secrets\app.env")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    dec = _bg_decrypt_fn(args.bot_gemini)
    updates: dict = {}

    # ── R2 ────────────────────────────────────────────────────────────────────
    r2p = os.path.join(args.bot_gemini, "data", "r2_storage.json")
    if os.path.exists(r2p):
        d = json.load(open(r2p, encoding="utf-8"))
        acc = (d.get("account_id") or "").strip()
        akid = _maybe_decrypt(dec, d.get("access_key_id") or "")
        sk = _maybe_decrypt(dec, d.get("secret_key") or "")
        bucket = (d.get("bucket") or "").strip()
        if acc and akid and sk and bucket:
            updates.update({
                "LTT_STORAGE": "r2", "LTT_R2_ACCOUNT_ID": acc,
                "LTT_R2_ACCESS_KEY_ID": akid, "LTT_R2_SECRET_ACCESS_KEY": sk,
                "LTT_R2_BUCKET": bucket,
            })
            print(f"  R2: account={acc[:6]}… bucket={bucket} akid=({len(akid)} ky tu) sk=({len(sk)} ky tu) OK")
        else:
            print("  R2: THIEU truong (account/akid/sk/bucket) — bo qua")
    else:
        print(f"  R2: khong thay {r2p} — bo qua")

    # ── ModelArk AK/SK (seedance Pha 2) ───────────────────────────────────────
    mp = os.path.join(args.bot_gemini, "data", "modelark_asset.json")
    if os.path.exists(mp):
        d = json.load(open(mp, encoding="utf-8"))
        ak = _maybe_decrypt(dec, d.get("access_key") or "")
        sk = _maybe_decrypt(dec, d.get("secret_key") or "")
        region = (d.get("region") or "ap-southeast-1").strip()
        if ak and sk:
            updates.update({"LTT_MODELARK_ACCESS_KEY": ak,
                            "LTT_MODELARK_SECRET_KEY": sk,
                            "LTT_MODELARK_REGION": region})
            print(f"  ModelArk: ak=({len(ak)} ky tu) sk=({len(sk)} ky tu) region={region} OK")
        else:
            print("  ModelArk: THIEU AK/SK — bo qua")
    else:
        print(f"  ModelArk: khong thay {mp} — bo qua")

    if not updates:
        print("Khong co gi de nhap.")
        return 1
    print("Se ghi cac bien:", ", ".join(sorted(updates)))
    if args.dry_run:
        print("(DRY-RUN — chua ghi app.env)")
        return 0
    _cap_nhat_env(args.app_env, updates)
    print(f"Da ghi {len(updates)} bien vao {args.app_env} (khong BOM, khong lo gia tri).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
