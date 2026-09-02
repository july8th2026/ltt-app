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

#: Cua so ngu canh CONG BO cho client.
#:
#: 🔴 KHONG GO SO NAY LAI. Nguon chan ly la `apps/ltt_llm/ngan_sach.py`
#:    (`CONG_BO_CHO_CLIENT`). Tep nay la mot tep DOC LAP -- chay tren may khach,
#:    khong co kho ma -- nen no phai chep so, khong import duoc.
#:
#:    Vi vay `tests/test_275_cai_dat_cli.py` doi chieu HAI CHIEU: so o day phai
#:    bang `ngan_sach.CONG_BO_CHO_CLIENT`. Doi mot ben ma quen ben kia => gate do.
#:
#:    Truoc 02/09 so nay la 65000 -- da CU tu lau (tran vao tung la 65k, roi 81k,
#:    nay 96.256 => cong bo 88.555). Khach macOS/Linux tai ban nay ve bi bao
#:    ngu canh THAP hon that 26%, tuc Codex nen som va vo co.
CUA_SO_NGU_CANH = 88555

#: Khoa BAT BUOC trong `[model_providers.ltt]`, kem ly do.
#:
#: Dung khi khach DA CO san bang do: ta khong ghi de (bang cua ho), nhung thieu
#: khoa thi phai noi ra. Do that 02/09: mot bang thieu `stream_idle_timeout_ms`
#: lam luong bi cat o 62 giay, suat bi giu, moi luot sau an 429.
KHOA_PROVIDER_BAT_BUOC = {
    "base_url": "khong co thi Codex goi nham dich",
    "env_key": "khong co thi Codex khong biet doc khoa o bien nao",
    "wire_api": "phai la `responses`",
    "stream_idle_timeout_ms":
        "thieu thi Codex CAT luong o ~62 giay trong khi may van sinh",
}


def _catalog() -> str:
    """Catalog model cho Codex, dung khuon `codex_models_manager` doc duoc.

    ⛔ BON CHO DA LAM CODEX TU CHOI TEP (tim ra 30/08, dung mat cong tim lai):
       * `web_search_tool_type: null` -- truong nay khong nhan null; bo han.
       * `effective_context_window_percent` -- CLI doi i64, tien ich VS Code doi
         chuoi. KHONG so nao lam vua long ca hai => BO HAN. No la tuy chon.
       * tro `model_catalog_json` toi tep KHONG ton tai -- Codex tu choi khoi dong.
    """
    def mot(slug: str, doc_anh: bool = False) -> dict:
        return {
            "slug": slug, "display_name": slug,
            "description": f"{slug} (LTT Studios)",
            "default_reasoning_level": "medium",
            "supported_reasoning_levels": [
                {"effort": "low", "description": "Fast"},
                {"effort": "medium", "description": "Balanced"},
                {"effort": "xhigh", "description": "Deepest"}],
            "shell_type": "unified_exec", "visibility": "list",
            "supported_in_api": True, "priority": 1,
            "additional_speed_tiers": [], "service_tiers": [],
            "base_instructions": "",
            "include_skills_usage_instructions": False,
            "include_plugin_usage_instructions": False,
            "include_apps_usage_instructions": False,
            "supports_reasoning_summary_parameter": False,
            "default_reasoning_summary": "none", "support_verbosity": False,
            "apply_patch_tool_type": "freeform",
            "truncation_policy": {"mode": "tokens", "limit": CUA_SO_NGU_CANH},
            "supports_parallel_tool_calls": False,
            "supports_image_detail_original": False,
            "context_window": CUA_SO_NGU_CANH,
            "max_context_window": CUA_SO_NGU_CANH,
            "auto_compact_token_limit": int(CUA_SO_NGU_CANH * 0.8),
            "experimental_supported_tools": [],
            "input_modalities": ["text", "image"] if doc_anh else ["text"],
            "supports_search_tool": False, "use_responses_lite": False,
            "node_repl_auto_review_required": False, "node_repl_disabled": False,
        }

    return json.dumps({"models": [mot("ltt_llm"), mot("ltt_llm_vision", True)]},
                      indent=1)


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
        # Bang do la CUA KHACH nen ta khong ghi de. Nhung thieu khoa thi phai
        # NOI RA -- im lang o day de lai dung cai loi khach dang di sua.
        for khoa, ly_do in KHOA_PROVIDER_BAT_BUOC.items():
            if khoa not in cu:
                ra.append(f"  !! bang san co THIEU `{khoa}` -- {ly_do}")
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

    # Tao tep catalog TRUOC khi tro toi no: Codex TU CHOI KHOI DONG neu
    # `model_catalog_json` tro toi mot duong dan khong ton tai.
    cat = goc_codex / "ltt_model_catalog.json"
    if not cat.exists():
        cat.write_text(_catalog(), encoding="utf-8")
        ra.append(f"  + tao {cat}")

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
            f"model_context_window = {CUA_SO_NGU_CANH}\n"
            f"model_catalog_json = '{cat}'\n", encoding="utf-8")
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
