#!/usr/bin/env python3
"""ltt_cai_dat_cli.py - plug LTT Studios into Codex, Claude Code and Claude Desktop.

    python ltt_cai_dat_cli.py --key ltt_sk_...

One file, no dependencies, works on Windows, macOS and Linux.

Why this exists: the thing that stops a developer is almost never the protocol,
it is filling in a config file correctly. Two base URLs that differ by four
characters, a model name that must match exactly, one environment variable that
has to be set at user level rather than in a shell. Each of those fails quietly
with an unhelpful symptom, and each of them is mechanical.

SAFETY, because these are your files and not ours:

  * every write is ADDITIVE - your existing `model`, your other providers and
    your other settings are left exactly as they were;
  * every file we touch is BACKED UP first, next to the original;
  * we never write your key into a config file. Config files get shared,
    committed and screenshotted. The key goes into an environment variable and
    the config only names that variable.

Run with --kiem-tra (--check) to verify a setup without changing anything.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sys
import urllib.error
import urllib.request

MAC_DINH_BASE = "https://app.lttstudios.com"
MODEL = "ltt_llm"
BIEN_KHOA = "LTT_API_KEY"


def _goc(base: str) -> str:
    return (base or MAC_DINH_BASE).rstrip("/")


def _sao_luu(p: pathlib.Path) -> None:
    """Back up before touching. Once per run, never overwriting an older backup."""
    if not p.exists():
        return
    bak = p.with_suffix(p.suffix + ".ltt-bak")
    if not bak.exists():
        shutil.copy2(p, bak)
        print(f"    sao luu: {bak}")


# ── Codex ────────────────────────────────────────────────────────────────────

def codex(base: str, goc_codex: pathlib.Path) -> list:
    """Two files, and the split is not optional.

    Codex 0.145+ refuses `[profiles.X]` inside config.toml outright:
    "cannot be used while config.toml contains legacy `[profiles.ltt]` config".
    The provider block stays in config.toml; the profile moves to its own file.
    """
    ra = []
    goc_codex.mkdir(parents=True, exist_ok=True)

    cfg = goc_codex / "config.toml"
    cu = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
    if "[model_providers.ltt]" in cu:
        ra.append(f"  = da co [model_providers.ltt] trong {cfg}, giu nguyen")
    else:
        _sao_luu(cfg)
        khoi = (
            "\n# --- LTT Studios (them tu dong; khong doi gi o tren) ---\n"
            "[model_providers.ltt]\n"
            'name = "LTT Studios"\n'
            f'base_url = "{_goc(base)}/api/v1"   # co /v1: Codex ghep them /responses\n'
            f'env_key = "{BIEN_KHOA}"\n'
            'wire_api = "responses"\n'
            "stream_idle_timeout_ms = 600000\n")
        cfg.write_text(cu.rstrip("\n") + "\n" + khoi if cu else khoi.lstrip("\n"),
                       encoding="utf-8")
        ra.append(f"  + them [model_providers.ltt] vao {cfg}")

    pro = goc_codex / "ltt.config.toml"
    if pro.exists():
        ra.append(f"  = da co {pro}, giu nguyen")
    else:
        pro.write_text(
            f'model = "{MODEL}"\n'
            'model_provider = "ltt"\n'
            "# Left at its default the model spends most of max_tokens thinking\n"
            "# before it answers.\n"
            'model_reasoning_effort = "low"\n'
            'model_reasoning_summary = "none"\n'
            "model_context_window = 65000\n", encoding="utf-8")
        ra.append(f"  + tao {pro}")
    return ra


# ── Claude Code CLI ──────────────────────────────────────────────────────────

def claude_code(base: str, goc_claude: pathlib.Path) -> list:
    """`~/.claude/settings.json`, merged rather than replaced.

    ANTHROPIC_DEFAULT_HAIKU_MODEL is the one everybody forgets: Claude Code uses
    a second, smaller model for background work. Leave it unset and those calls
    ask for a Claude model this API does not serve, and fail quietly while the
    main session looks fine.
    """
    goc_claude.mkdir(parents=True, exist_ok=True)
    p = goc_claude / "settings.json"
    goc_json = {}
    if p.exists():
        try:
            goc_json = json.loads(p.read_text(encoding="utf-8") or "{}")
        except ValueError:
            return [f"  ! {p} khong phai JSON hop le - BO QUA, khong dam sua"]
        _sao_luu(p)
    env = dict(goc_json.get("env") or {})
    env.update({
        "ANTHROPIC_BASE_URL": f"{_goc(base)}/api",     # KHONG /v1: client tu ghep
        "ANTHROPIC_MODEL": MODEL,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": MODEL,
    })
    # Khoa KHONG vao day. `settings.json` bi chia se va commit thuong xuyen.
    env.setdefault("ANTHROPIC_AUTH_TOKEN", f"${BIEN_KHOA}")
    goc_json["env"] = env
    p.write_text(json.dumps(goc_json, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")
    return [f"  + cap nhat khoi `env` trong {p}"]


# ── Claude Desktop: khong tu dong duoc ──────────────────────────────────────

def claude_desktop(base: str) -> list:
    """Claude Desktop does NOT read ANTHROPIC_BASE_URL. It has its own form, and
    there is no supported file to write, so this prints steps instead of lying
    about having configured it."""
    return [
        "  i Claude Desktop phai lam bang tay (no khong doc bien moi truong):",
        "      Help -> Troubleshooting -> Enable Developer Mode",
        "      Developer -> Configure Third-Party Inference...",
        "      Inference provider  : Gateway",
        f"      Gateway base URL    : {_goc(base)}/api",
        "      Gateway API key     : khoa cua ban",
        "      Gateway auth scheme : Bearer",
        f"      inferenceModels     : {MODEL}",
        "      -> Apply locally",
        "    (inferenceModels BAT BUOC: bo chon model tu dong cua Desktop chi giu",
        "     nhung id trong giong Claude, nen model nay khong tu hien ra.)",
    ]


# ── Kiem tra that, khong tin cau hinh ───────────────────────────────────────

def kiem_tra(base: str, key: str) -> int:
    """Ask the server, do not trust the files we just wrote."""
    url = f"{_goc(base)}/api/v1/models"
    # 🔴 PHAI GUI User-Agent RIENG. Cloudflare chan User-Agent mac dinh cua
    #    urllib (`Python-urllib/3.x`) bang 403 truoc khi request toi may chu ta.
    #    Do that 24/08: cung mot khoa, cung mot URL —
    #        urllib mac dinh   -> 403
    #        bat ky UA nao khac -> 200
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}",
        "User-Agent": "ltt-cai-dat-cli/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            goi = json.loads(r.read())
    except urllib.error.HTTPError as e:
        than = e.read()[:200].decode("utf-8", "replace")
        print(f"  ! {url} tra HTTP {e.code}")
        if e.code == 401:
            print("    -> khoa sai, hoac ban dan nham chuoi")
        elif e.code == 403:
            print("    -> khoa dung nhung chua duoc phep goi tool nay")
        else:
            print(f"    -> {than}")
        return 1
    except Exception as e:                                  # noqa: BLE001
        print(f"  ! khong noi duoc toi {url}: {type(e).__name__}")
        return 1

    ten = [m.get("name") for m in (goi.get("items") or [])]
    if MODEL not in ten:
        print(f"  ! may chu khong liet ke `{MODEL}` (thay: {ten or 'khong co gi'})")
        return 1
    print(f"  OK may chu nhan khoa, va co `{MODEL}`")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Cam LTT Studios vao Codex / Claude Code / Claude Desktop.")
    ap.add_argument("--key", default=os.environ.get(BIEN_KHOA, ""),
                    help=f"khoa ltt_sk_... (mac dinh: bien {BIEN_KHOA})")
    ap.add_argument("--base-url", default=MAC_DINH_BASE)
    ap.add_argument("--kiem-tra", "--check", action="store_true", dest="chi_kiem",
                    help="chi kiem tra, KHONG sua file nao")
    ap.add_argument("--home", default=str(pathlib.Path.home()),
                    help="thu muc home (dung de thu)")
    a = ap.parse_args(argv)

    if not a.key:
        print(f"Thieu khoa. Dat bien {BIEN_KHOA} hoac dung --key.")
        print("Lay khoa o: " + _goc(a.base_url) + "/developers/keys")
        return 2

    home = pathlib.Path(a.home)
    print(f"May chu : {_goc(a.base_url)}")
    print(f"Model   : {MODEL}")
    print("")

    if a.chi_kiem:
        print("Kiem tra (khong sua gi):")
        return kiem_tra(a.base_url, a.key)

    print("Codex:")
    for d in codex(a.base_url, home / ".codex"):
        print(d)
    print("Claude Code (CLI):")
    for d in claude_code(a.base_url, home / ".claude"):
        print(d)
    print("Claude Desktop:")
    for d in claude_desktop(a.base_url):
        print(d)

    print("")
    print("Kiem tra voi may chu:")
    rc = kiem_tra(a.base_url, a.key)

    print("")
    print("CON MOT VIEC BAN PHAI TU LAM - dat khoa o CAP NGUOI DUNG:")
    if os.name == "nt":
        print(f'    setx {BIEN_KHOA} "<khoa cua ban>"')
    else:
        print(f'    echo \'export {BIEN_KHOA}="<khoa cua ban>"\' >> ~/.profile')
    print("  Roi MO LAI terminal / VS Code. Dat trong mot cua so terminal thoi la")
    print("  khong du: tien ich VS Code va Claude Desktop la tien trinh khac va")
    print("  khong thay bien do.")
    print("")
    print("Xong thi chay:  codex --profile ltt")
    return rc


if __name__ == "__main__":
    sys.exit(main())
