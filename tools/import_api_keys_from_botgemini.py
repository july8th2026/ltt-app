"""
import_api_keys_from_botgemini.py — nhập MỘT LẦN 6 API key từ D:\\BOT GEMINI sang
bộ máy APIKEYS của LTTSTUDIOSAPP (H8.5).

Cách chạy (trên MÁY CHỦ, bằng venv của nền tảng, sau khi đã chạy migration tạo
bảng api_keys):

    C:\\LTTPlatform\\venv\\Scripts\\python.exe ^
        C:\\LTTPlatform\\app\\tools\\import_api_keys_from_botgemini.py

Quy trình: đọc `D:\\BOT GEMINI\\data\\api_keys.json` (dict id->record) → giải mã
`api_key_value` bằng CHÍNH module security của BOT GEMINI (khoá FERNET_KEY trong
`D:\\BOT GEMINI\\.env`) → mã hoá LẠI bằng `LTT_TOKEN_ENCRYPTION_KEY` của nền tảng
→ INSERT vào bảng `api_keys`. `categories` suy từ Provider Registry.

AN TOÀN: secret chỉ ở RAM lúc chuyển; KHÔNG ghi ra log/đĩa (chỉ in 4 số cuối).
Idempotent: bỏ qua key đã có (trùng provider + preview).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _HERE)   # để import platform_core khi chạy từ thư mục app


def _load_env_file(path: str) -> None:
    """Nạp KEY=VALUE từ một file .env vào os.environ (không ghi đè biến đã có)."""
    if not path or not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _bg_decrypt_fn(bg_root: str):
    """Nạp riêng lẻ app/core/security.py của BOT GEMINI (không kích hoạt cả app
    package) để dùng hàm decrypt của nó — nó tự đọc FERNET_KEY từ BOT GEMINI/.env."""
    sec_path = os.path.join(bg_root, "app", "core", "security.py")
    if not os.path.exists(sec_path):
        raise SystemExit(f"Khong thay {sec_path} — dat --bot-gemini dung duong dan.")
    spec = importlib.util.spec_from_file_location("bg_security", sec_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "decrypt"):
        raise SystemExit("security.py cua BOT GEMINI khong co ham decrypt().")
    return mod.decrypt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot-gemini", default=r"D:\BOT GEMINI")
    ap.add_argument("--app-env", default=r"C:\LTTPlatform\secrets\app.env",
                    help="file app.env chua LTT_DATABASE_URL + LTT_TOKEN_ENCRYPTION_KEY")
    ap.add_argument("--dry-run", action="store_true", help="chi in, khong ghi DB")
    args = ap.parse_args()

    _load_env_file(args.app_env)
    if not os.environ.get("LTT_DATABASE_URL"):
        raise SystemExit("Thieu LTT_DATABASE_URL (kiem --app-env).")
    if not os.environ.get("LTT_TOKEN_ENCRYPTION_KEY"):
        raise SystemExit("Thieu LTT_TOKEN_ENCRYPTION_KEY — se ma hoa bang machine-id, "
                         "khong ben. Dat env roi chay lai.")

    json_path = os.path.join(args.bot_gemini, "data", "api_keys.json")
    if not os.path.exists(json_path):
        raise SystemExit(f"Khong thay {json_path}")
    data = json.load(open(json_path, encoding="utf-8"))
    records = list(data.values()) if isinstance(data, dict) else list(data)

    bg_decrypt = _bg_decrypt_fn(args.bot_gemini)

    from platform_core import api_keys, providers, secretbox
    from platform_core.db import get_session

    gen = get_session(); db = next(gen)
    them = bo_qua = loi = 0
    try:
        san_co = {(k.provider, k.key_preview) for k in api_keys.liet_ke(db)}
        for rec in records:
            provider = (rec.get("provider") or "").strip().lower()
            enc = rec.get("api_key_value") or ""
            if not provider or not enc:
                loi += 1; continue
            try:
                plain = bg_decrypt(enc)
            except Exception as e:      # noqa: BLE001
                print(f"  [LOI] {provider}: giai ma that bai ({type(e).__name__})")
                loi += 1; continue
            if not plain:
                print(f"  [LOI] {provider}: giai ma ra rong"); loi += 1; continue

            pv = secretbox.preview(plain)
            if (provider, pv) in san_co:
                print(f"  [BO QUA] {provider} {pv} da co"); bo_qua += 1; continue

            prov = providers.get(provider)
            cats = list(prov.categories) if prov else []
            if args.dry_run:
                print(f"  [DRY] se them {provider} {pv} categories={cats}")
                them += 1; continue
            key = api_keys.tao_key(
                db, provider=provider, credential=plain,
                name=(rec.get("name") or provider),
                categories=cats,
                base_url=(rec.get("base_url") or ""),
                supported_models=(rec.get("supported_models") or []),
                default_model=(rec.get("default_model") or ""),
                priority=int(rec.get("priority") or 100),
            )
            if rec.get("enabled") is False:
                key.enabled = False
            san_co.add((provider, pv))
            them += 1
            print(f"  [OK] them {provider} {pv} categories={cats}")
        if not args.dry_run:
            db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    print(f"\nXONG: them={them} bo_qua={bo_qua} loi={loi} "
          f"{'(DRY-RUN, chua ghi)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
