"""Buoc 0 - Kiem tra thu muc truoc khi chep sang may khac.

Chay TREN MAY PHAT TRIEN, truoc khi copy. Muc dich chinh: chac chan khong
mang bi mat nao di theo. Chi doc, khong sua gi.

    python setup/0-kiem-tra-truoc-khi-chuyen.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
fail = []

print("=" * 66)
print("KIEM TRA TRUOC KHI CHUYEN SANG MAY KHAC")
print("=" * 66)

# 1. Khong duoc mang bi mat di
print("\n[1] Bi mat")
danger = []
for pat in ("**/*.enc", "**/app.env", "**/*service_account*.json",
            "**/cert.pem", "cloudflare/config.yml", "cloudflare/*.json"):
    danger += [p for p in ROOT.glob(pat) if p.is_file()]
if danger:
    fail.append("co file bi mat")
    for p in danger:
        print("    NGUY HIEM:", p.relative_to(ROOT))
else:
    print("    OK - khong co token, khoa, hay credentials nao")

# config.json phai la ban mau
cfg = ROOT / "data" / "config.json"
if cfg.exists():
    data = json.loads(cfg.read_text(encoding="utf-8"))
    real = [k for k, v in data.items()
            if isinstance(v, str) and v and "REPLACE_ME" not in v
            and k in ("meta_app_secret", "tiktok_client_secret", "sheet_id",
                      "telegram_bot_token")]
    if real:
        fail.append("config.json co gia tri that")
        print("    NGUY HIEM: config.json chua gia tri that:", real)
    else:
        print(f"    OK - config.json la ban mau ({len(data)} khoa)")

# 2. Du file de chay
print("\n[2] Day du file")
need = ["CLAUDE.md", "README.md", "requirements.txt", "requirements-server.txt",
        "config.example.json", "server/run.py", "server/app.py",
        "platform_core/registry.py", "platform_core/storage.py",
        "setup/1-kiem-tra-may.ps1", "setup/2-cai-dat.ps1",
        "setup/3-cloudflare.ps1", "setup/4-nghiem-thu.ps1",
        "docs/00_BAT_DAU_TU_DAY.md", "docs/01_COPY_LEN_SERVER.md",
        "docs/02_LENH_CHO_CLAUDE.md", "docs/03_THEM_APP_MOI.md",
        "docs/04_CLOUDFLARE_TUNNEL.md",
        "data/translations/vi.json", "data/translations/en.json"]
miss = [n for n in need if not (ROOT / n).exists()]
if miss:
    fail.append("thieu file")
    print("    THIEU:", miss)
else:
    print(f"    OK - du ca {len(need)} file bat buoc")

# 3. App
print("\n[3] App")
apps = [d.name for d in (ROOT / "apps").iterdir()
        if d.is_dir() and (d / "manifest.py").exists()]
print(f"    OK - {len(apps)} app: {', '.join(sorted(apps))}")

# 4. Script cai
print("\n[4] Script cai (ASCII, khong BOM)")
bad = []
for ps in sorted((ROOT / "setup").glob("*.ps1")):
    raw = ps.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        bad.append(f"{ps.name}: co BOM")
    n = sum(1 for b in raw if b > 127)
    if n:
        bad.append(f"{ps.name}: {n} byte khong ASCII")
if bad:
    fail.append("script cai co van de")
    for b in bad:
        print("    LOI:", b)
else:
    print("    OK - ca 4 script thuan ASCII, khong BOM")

# 5. Kich thuoc
print("\n[5] Kich thuoc")
files = [p for p in ROOT.rglob("*")
         if p.is_file() and "__pycache__" not in p.parts
         and ".pytest_cache" not in p.parts]
mb = sum(p.stat().st_size for p in files) / 1024 / 1024
print(f"    {len(files)} file, {mb:.1f} MB (khong tinh cache)")

print("\n" + "=" * 66)
if fail:
    print("KET QUA: CHUA DUOC -", ", ".join(fail))
    raise SystemExit(1)
print("KET QUA: SAN SANG chuyen sang may khac.")
