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
import re
import shutil
import sys
import urllib.error
import urllib.request
from typing import NamedTuple

try:                                  # Python 3.11+; cu hon thi van cai duoc,
    import tomllib as _tomllib        # chi mat buoc tu kiem sau khi hop nhat
except ImportError:                   # pragma: no cover
    _tomllib = None  # type: ignore[assignment]

MAC_DINH_BASE = "https://app.lttstudios.com"
MODEL = "ltt-3.8"
MODEL_35 = "ltt-3.5"

#: Ten TUYEN cho Claude Desktop — khong phai ten san pham.
#:
#: 🔴 Claude Desktop loc danh sach model truoc khi ve picker: ten khong chua
#:    `claude`/`anthropic` thi bi bo. Ban truoc cua tep nay in `ltt-3.8` vao o
#:    `inferenceModels`, tuc day khach vao dung cai bay: picker rong, **nut gui
#:    vo hieu, khong mot loi bao nao**. Khong log, khong toast, khong banner.
#:
#: ⭐ Bo loc chi doi ten **chua** `claude`; no khong doi mot model Anthropic co
#:    that. Nen ta qua duoc cong ma khong muon ten san pham cua hang khac.
MODEL_DESKTOP = "ltt-llm-claude-compat"
MODEL_DESKTOP_35 = "ltt-llm-claude-compat-35"
NHAN_DESKTOP = {
    MODEL_DESKTOP: "LTT 3.8 (Mạnh)",
    MODEL_DESKTOP_35: "LTT 3.5 (Nhanh)",
}
NHAN_CODEX = {
    "ltt-3.8": "LTT 3.8 (Strong)",
    "ltt-3.5": "LTT 3.5 (Fast)",
}
TANG_DESKTOP = {MODEL_DESKTOP: "opus", MODEL_DESKTOP_35: "haiku"}
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
#:    Truoc 02/09 so nay la 65000 -- da CU tu lau. Khach macOS/Linux tai ban do
#:    ve bi bao ngu canh THAP hon that 26%, tuc Codex nen som va vo co.
#:
#:    Duong di cua con so: 65.000 -> 88.555 (02/09) -> 156.385 (03/09, khi cua
#:    so engine len 204.800). Moi lan doi deu phai doi CA HAI bo cai.
CUA_SO_NGU_CANH = 171458

#: Tran token RA, khop `ngan_sach.TOKEN_RA_TRAN`.
TOKEN_RA_TRAN = 32768

#: Nguong client PHAI nen hoi thoai, khop `ngan_sach.NEN_CHO_CLIENT`.
#:
#: 🔴 KHONG PHAI `CUA_SO_NGU_CANH * 0.8`. Ti le do khong do cai can do: thu phai
#:    vua la khoang trong tu nguong nen len cua so cong bo, va no phai chua tron
#:    MOT luot sinh dai nhat (32.768) — client chi kiem nguong GIUA hai luot.
#:    Voi 0,8 khoang do chi con 25.412, thieu, va production da an mot `413` o
#:    101.938 token vao dung vi vay.
NEN_HOI_THOAI = 138690

#: Tran token cho MOT ket qua tool, do vao `truncation_policy` cua catalog.
#:
#: 🔴 TRUOC 04/09 CHO NAY LA `cua_so` — tuc **ca cua so ngu canh**. Mot ket qua
#:    tool duy nhat duoc phep nuot tron ngu canh. Mac dinh cua chinh Codex la
#:    `TruncationPolicyConfig::bytes(10_000)` voi `APPROX_BYTES_PER_TOKEN = 4`,
#:    tuc **2.500 token** — ta rong hon **62 lan**.
#:
#: ⭐ VA DAY KHONG PHAI MOT TRUONG TRANG TRI. Codex chi kiem nguong nen **GIUA
#:    hai luot**, khong kiem giua cac lan goi tool trong CUNG mot luot
#:    (openai/codex#16033: 83 lenh shell dua ngu canh tu 0 len 400K trong mot
#:    luot, nen khong kip chay; co TODO cua chinh ho thua nhan). Nen khi mot
#:    luot phinh ra, `truncation_policy` la **co che phong thu duy nhat con
#:    lai** — va ta da vo hieu hoa no bang chinh tay minh. Production da an mot
#:    ket qua tool **95.901 token trong mot luot**.
#:
#: Suy ra, khong bia: khoang trong giua nguong nen va cua so cong bo dung bang
#: `TOKEN_RA_TRAN` (171.458 - 138.690 = 32.768). Mot ket qua tool khong duoc
#: chiem qua NUA khoang do, de sau no van con cho cho luot sinh ke tiep.
#:
#: ⚠️ Don vi o day la token **UOC CUA CODEX** (`len/4`), khong phai token that
#:    cua Qwen. Do 03/09: tieng Viet ~3,14 ky tu/token that, nen 16.384 x 4 =
#:    65.536 byte ~ **20.872 token that** — van duoi 32.768, con bien an toan.
TRAN_KET_QUA_TOOL = TOKEN_RA_TRAN // 2

#: Hai hang cua CHINH Claude Code: no KHONG nen o `CLAUDE_CODE_AUTO_COMPACT_WINDOW`
#: ma o
#:
#:     min(AUTO_COMPACT_WINDOW, cua so model) - min(MAX_OUTPUT_TOKENS, 20000) - 13000
#:
#: 🔴 TRUOC 18/09 ta khai AUTO_COMPACT_WINDOW = nguong Codex (138.690) va Claude
#:    nen o 105.690 — SOM 33.000 token, 76% (R-05). Codex thi nen dung o
#:    `model_auto_compact_token_limit`; hai client, hai nghia cua "nguong".
#:
#: ⭐ Nguon, theo thu tu do tin:
#:    * do that 18/09: Claude Code 2.1.274 tro ve LTT, `/context` voi cua so
#:      138.7k in "Autocompact buffer 33k"; voi 171.458 va 209.141 cung 33k;
#:      khai 171.690 thi bi kep ve 171.5k (= MAX_CONTEXT_TOKENS);
#:    * ma client 2.1.274: `Dz()` = window - min(maxOut, 20000), `KPe()` = Dz - 13000;
#:    * tai lieu (`model-config.md`): cua so 1M nen "at about 967K" = 1M - 33K.
#:    Nang Claude Code thi DO LAI (`/context`, dong "Autocompact buffer").
#:
#: ⚠️ Bien chi nhan tu 100.000 den 1.000.000 (env-vars.md).
CLAUDE_TRU_RA_TOI_DA = 20_000
CLAUDE_DEM_NEN = 13_000

#: Cua so cong bo cua MODEL THU HAI (`ltt-3.5`). **Khong dung chung so.**
#:
#: ⛔ NO VAN LA MOT CON SO RIENG, du hien gio no tinh co bang con so text CU.
#:    Ban truoc 01/09 khai 88.555 cho CA HAI model va do la mot loi hua sai
#:    (luc do vision chay `-c 65536`, cua so that cua no la 28.262). Su trung
#:    hop hom nay khong xoa duoc ly do phai tach: hai model, hai `-c`, hai con
#:    so — va chung se lech lai ngay lan nang cua so ke tiep.
#:
#: 📈 03/09: 28.262 -> 88.555, khi vision len `-c 131072` + KV q4_0. Do that:
#:    89.868 token vao doc lai dung moc dau-cuoi, VRAM 21.099 MiB (+748 so voi
#:    ho so 65K cu), va A/B doc anh tren cung mot anh: ca hai ho so tra dung moc.
#: 📈 12/09 (dual-model 2.6): hai con so nay TACH KHOI `ltt-3.8`, va su tach do
#:    la ket qua cua phep do chu khong phai mot lua chon. Tu 11/09 toi 12/09
#:    chung tinh co bang nhau vi ca hai model tam dung mot ngu canh engine; do
#:    xong thi `ltt-3.8` phai ha xuong `-c 221184` (3090 khong du VRAM cho
#:    262.144 + mmproj + 3 slot — L-14 §G1b) trong khi `ltt-3.5` giu tron
#:    262.144 tren 5060 Ti (§G3). Ho so vision cu (`qwen38-vision`) da bi go.
#: ⛔ Nguon chan ly la `apps/ltt_llm/ngan_sach.py`; tep nay CHEP theo, va
#:    `test_334` buoc hai dau lai nen khong lech duoc trong im lang.
CUA_SO_NGU_CANH_35 = 209141
#: Nguong nen cua model thu hai, khop `ngan_sach.nen_cua("qwen35-api")`.
#:
#: ⭐ TRUOC 03/09 SO NAY LA **0**, va so 0 do la mot cau tra loi that: cua so
#:    cong bo cua vision khi ay (28.262) HEP HON mot luot sinh dai nhat (32.768),
#:    nen khong nguong nen nao giu duoc loi hua va bo cai phai bo han truong do.
#:    Nang cua so len 131K la thu lam cho no dinh nghia duoc tro lai.
NEN_HOI_THOAI_35 = 176373


class HoSoModel(NamedTuple):
    """MOT model, nhu bo cai nay can biet ve no.

    ⚠️ Sau truong PHAI di cung nhau. Roi rac chung ra la cach `ltt-3.5` duoc
       cam voi cua so cua `ltt-3.8` — mot `413` giua phien, im lang, chi vi mot
       con so bi bo lai.
    """

    ten: str
    tuyen_desktop: str
    cua_so: int
    nen: int
    reasoning: str
    reasoning_levels: tuple[str, ...]

    @property
    def cua_so_nen_claude(self) -> int:
        """`CLAUDE_CODE_AUTO_COMPACT_WINDOW` sao cho Claude nen DUNG o `nen`.

        Kep o `cua_so`: Claude tu kep ve MAX_CONTEXT_TOKENS, nen khai hon la
        noi mot dang, client lam mot dang. Kep lam Claude nen som hon `nen`
        dung phan bi kep (3.8: 232 token) — phia an toan.
        """
        return min(self.nen + min(TOKEN_RA_TRAN, CLAUDE_TRU_RA_TOI_DA)
                   + CLAUDE_DEM_NEN, self.cua_so)


#: 🔑 HAI MODEL DANG BAN, theo thu tu hien cho khach.
#:
#: ⛔ Nguon chan ly van la `apps/ltt_llm/ngan_sach.py`. Tep nay chay tren may
#:    KHACH, khong co kho ma, nen no CHEP so — va `test_275` doi chieu hai chieu.
HO_SO_MODEL = {
    MODEL: HoSoModel(MODEL, MODEL_DESKTOP, CUA_SO_NGU_CANH, NEN_HOI_THOAI,
                     "medium", ("low", "medium", "xhigh")),  # L-33 (19/09)
    MODEL_35: HoSoModel(MODEL_35, MODEL_DESKTOP_35,
                        CUA_SO_NGU_CANH_35, NEN_HOI_THOAI_35, "medium",
                        ("medium",)),
}

TEN_MODEL = tuple(HO_SO_MODEL)

#: Cua so nen Claude cua model mac dinh — RIENG voi `NEN_HOI_THOAI` cua Codex.
CUA_SO_NEN_CLAUDE = HO_SO_MODEL[MODEL].cua_so_nen_claude


def hs_cua(ten) -> HoSoModel:
    """Ten -> ho so. Ten la hoac rong ve mac dinh, va KHONG nem.

    ⭐ Khong nem vi tep nay chay tren may KHACH: mot traceback o day bien "cam
       khong duoc" thanh "cong cu hong", va khach khong co cach nao doc tiep.
    """
    return HO_SO_MODEL.get((ten or "").strip(), HO_SO_MODEL[MODEL])


#: Khoa BAT BUOC trong `[model_providers.ltt]`, kem ly do.
#:
#: Dung khi khach DA CO san bang do: ta khong ghi de (bang cua ho), nhung thieu
#: khoa thi phai noi ra. Do that 02/09: mot bang thieu `stream_idle_timeout_ms`
#: lam luong bi cat o 62 giay, suat bi giu, moi luot sau an 429.
KHOA_PROVIDER_BAT_BUOC = {
    "base_url": "khong co thi Codex goi nham dich",
    "env_key": "khong co thi Codex khong biet doc khoa o bien nao",
    "wire_api": "phai la `responses`",
    "request_max_retries": "chi thu lai mot lan de khong nhan tai cua lane",
    "stream_max_retries": "khong phat lai luong da co the sinh token",
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
    def mot(slug: str, cua_so: int, nen: int, doc_anh: bool = False) -> dict:
        d = {
            "slug": slug, "display_name": NHAN_CODEX[slug],
            "description": f"{slug} (LTT Studios)",
            "default_reasoning_level": HO_SO_MODEL[slug].reasoning,
            "supported_reasoning_levels": [
                {"effort": effort,
                 "description": ("Thinking on" if slug == MODEL_35 else
                                 {"low": "Fast", "medium": "Balanced",
                                  "xhigh": "Deepest"}[effort])}
                for effort in HO_SO_MODEL[slug].reasoning_levels],
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
            "truncation_policy": {"mode": "tokens", "limit": TRAN_KET_QUA_TOOL},
            "supports_parallel_tool_calls": False,
            "supports_image_detail_original": False,
            "context_window": cua_so,
            "max_context_window": cua_so,
            "experimental_supported_tools": [],
            "input_modalities": ["text", "image"] if doc_anh else ["text"],
            "supports_search_tool": False, "use_responses_lite": False,
            "node_repl_auto_review_required": False, "node_repl_disabled": False,
        }
        # Khong co nguong nao giu duoc loi hua (nen=0) thi BO HAN truong, dung
        # ghi mot con so bia: Codex se tin no, va cai gia la mot 413 giua phien.
        if nen > 0:
            d["auto_compact_token_limit"] = nen
        return d

    return json.dumps(
        {"models": [mot("ltt-3.8", CUA_SO_NGU_CANH, NEN_HOI_THOAI, doc_anh=True),
                    mot("ltt-3.5", CUA_SO_NGU_CANH_35,
                        NEN_HOI_THOAI_35, doc_anh=True)]},
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


# ── Cap nhat profile da co: khoa LTT moi, khoa nguoi dung giu nguyen (R-13) ──
#
# 🔴 VI SAO. Ban truoc gap `ltt.config.toml` da co thi IN "giu nguyen" va di
#    tiep. Nghe an toan, nhung nghia la nguoi cai MOT LAN khong bao gio nhan
#    so moi: cua so, nguong nen, duong catalog cu mai — va mot con so cu o day
#    la mot `413` giua phien, khong phai mot canh bao.
#
# ⭐ Luat: moi khoa ta VIET trong profile chuan la khoa LTT so huu va duoc cap
#    nhat; tru `KHOA_SO_THICH` (lua chon cua nguoi dung) chi them khi thieu.
#    Moi dong khac — khoa, bang, chu thich cua nguoi dung — giu tung byte.
#    Ket qua phai parse lai duoc VA khoa cua nguoi dung phai con dung gia tri;
#    khong thi KHONG ghi.

#: Khoa ta dat mac dinh nhung la LUA CHON cua nguoi dung: chi them khi thieu.
KHOA_SO_THICH = frozenset({"model_reasoning_effort",
                           "default_subagent_reasoning_effort"})

_RE_BANG_TOML = re.compile(r"^\s*\[\s*([A-Za-z0-9_.\"' -]+?)\s*\]\s*(?:#.*)?$")
_RE_KHOA_TOML = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*=")


def _gan_nhan_toml(dong: list) -> list:
    """(bang, khoa|None) cho tung dong. Bang goc la ''."""
    bang = ""
    ra: list[tuple[str, str | None]] = []
    for d in dong:
        if d.lstrip().startswith("[["):
            bang = "\0" + d.strip()               # mang bang: khong bao gio la cua ta
            ra.append((bang, None))
            continue
        m = _RE_BANG_TOML.match(d)
        if m:
            bang = m.group(1).strip()
            ra.append((bang, None))
            continue
        k = _RE_KHOA_TOML.match(d)
        ra.append((bang, k.group(1) if k else None))
    return ra


def hop_nhat_profile(cu: str, chuan: str) -> str:
    """Tra ve `cu` voi moi khoa cua `chuan` da cap nhat/them. Nem ValueError
    neu `cu` khong phai TOML hop le hoac ket qua lam hong khoa nguoi dung."""
    nl = "\r\n" if "\r\n" in cu else "\n"
    dong = cu.replace("\r\n", "\n").split("\n")
    if dong and dong[-1] == "":
        dong.pop()
    muon: dict = {}                               # bang -> {khoa: dong}
    dong_chuan = chuan.split("\n")
    for i, (bang, khoa) in enumerate(_gan_nhan_toml(dong_chuan)):
        d = dong_chuan[i]
        if khoa:
            muon.setdefault(bang, {})[khoa] = d.strip()
    nhan = _gan_nhan_toml(dong)
    da_co = set()
    for i, (bang, khoa) in enumerate(nhan):
        if khoa and khoa in muon.get(bang, {}):
            da_co.add((bang, khoa))
            if khoa not in KHOA_SO_THICH:
                dong[i] = muon[bang][khoa]
    for bang, cac_khoa in muon.items():
        thieu = [d for k, d in cac_khoa.items() if (bang, k) not in da_co]
        if not thieu:
            continue
        nhan = _gan_nhan_toml(dong)
        vi_tri = [i for i, (b, _) in enumerate(nhan) if b == bang]
        if bang == "":
            dau_bang = next((i for i, (b, k) in enumerate(nhan)
                             if b != "" and k is None), len(dong))
            chen = dau_bang
            while chen > 0 and not dong[chen - 1].strip():
                chen -= 1
        elif vi_tri:
            chen = vi_tri[-1] + 1
            while chen > vi_tri[0] + 1 and not dong[chen - 1].strip():
                chen -= 1
        else:
            if dong and dong[-1].strip():
                dong.append("")
            dong.append(f"[{bang}]")
            chen = len(dong)
        dong[chen:chen] = thieu
    moi = nl.join(dong) + nl
    if _tomllib is not None:
        truoc = _tomllib.loads(cu)                # hong san -> TOMLDecodeError

        def giu(a: dict, b: dict, bang: str) -> None:
            ta = muon.get(bang, {})
            for k, v in a.items():
                con = k if bang == "" else f"{bang}.{k}"
                if isinstance(v, dict) and con in muon:
                    giu(v, b.get(k) or {}, con)
                elif k in ta and k not in KHOA_SO_THICH:
                    continue
                elif b.get(k) != v:
                    raise ValueError(f"khoa `{con}` cua nguoi dung bi doi")

        giu(truoc, _tomllib.loads(moi), "")
    return moi


# ── Codex ────────────────────────────────────────────────────────────────────

def codex(base: str, goc_codex: pathlib.Path,
          hs: HoSoModel | None = None) -> list:
    """Provider, catalog and both LTT profiles; the split is not optional.

    Codex 0.145+ refuses `[profiles.X]` inside config.toml outright:
    "cannot be used while config.toml contains legacy `[profiles.ltt]` config".
    The provider block stays in config.toml; the profile moves to its own file.
    """
    # `hs` remains in the public signature for old callers that also pass it to
    # `claude_code`. It must not narrow Codex to one model: one install always
    # exposes both LTT products.
    del hs
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
            "request_max_retries = 1\n"
            "stream_max_retries = 0\n"
            "stream_idle_timeout_ms = 600000\n")
        cfg.write_text(cu.rstrip("\n") + "\n" + khoi if cu else khoi.lstrip("\n"),
                       encoding="utf-8")
        ra.append(f"  + them [model_providers.ltt] vao {cfg}")

    # Tao tep catalog TRUOC khi tro toi no: Codex TU CHOI KHOI DONG neu
    # `model_catalog_json` tro toi mot duong dan khong ton tai.
    # ⭐ Catalog la tep CUA LTT tu dau den cuoi: lan cai sau LAM MOI no (co sao
    #    luu), khong "giu nguyen" — giu nguyen la giu so cu mai (R-13).
    cat = goc_codex / "ltt_model_catalog.json"
    moi_cat = _catalog()
    if not cat.exists():
        cat.write_text(moi_cat, encoding="utf-8")
        ra.append(f"  + tao {cat}")
    elif cat.read_text(encoding="utf-8") != moi_cat:
        _sao_luu(cat)
        cat.write_text(moi_cat, encoding="utf-8")
        ra.append(f"  ~ lam moi {cat}")

    for ten_tep, hs_codex in (("ltt.config.toml", HO_SO_MODEL[MODEL]),
                              ("ltt-fast.config.toml", HO_SO_MODEL[MODEL_35])):
        pro = goc_codex / ten_tep
        chuan = _profile_codex(hs_codex, cat)
        if not pro.exists():
            pro.write_text(chuan, encoding="utf-8")
            ra.append(f"  + tao {pro} ({hs_codex.ten})")
            continue
        cu_pro = pro.read_bytes().decode("utf-8")
        try:
            moi = hop_nhat_profile(cu_pro, chuan)
        except ValueError as e:
            ra.append(f"  ! {pro} khong cap nhat duoc ({e}) - KHONG dung toi;"
                      " xoa tep do roi chay lai de nhan so moi")
            continue
        if moi == cu_pro:
            ra.append(f"  = {pro} da dung so moi")
            continue
        _sao_luu(pro)
        pro.write_bytes(moi.encode("utf-8"))
        ra.append(f"  ~ cap nhat khoa LTT trong {pro} (khoa cua ban giu nguyen)")
    return ra


def _profile_codex(hs_codex: HoSoModel, cat: pathlib.Path) -> str:
    """Profile CHUAN. Moi khoa o day la khoa LTT so huu, tru `KHOA_SO_THICH`."""
    return (
            f'model = "{hs_codex.ten}"\n'
            'model_provider = "ltt"\n'
            "# Model-specific quality default; server thinking remains enabled.\n"
            f'model_reasoning_effort = "{hs_codex.reasoning}"\n'
            'model_reasoning_summary = "none"\n'
            f"model_context_window = {hs_codex.cua_so}\n"
            f"model_auto_compact_token_limit = {hs_codex.nen}\n"
            'model_auto_compact_token_limit_scope = "total"\n'
            f"tool_output_token_limit = {TRAN_KET_QUA_TOOL}\n"
            f"model_catalog_json = '{cat}'\n"
            # R-11: LTT khong phuc vu cong cu hosted `web_search`; Codex gui no
            # thi luot hong. Khoa cua PROFILE LTT (config.toml cua khach khong
            # cham). Khuon: codex-rs/config/src/profile_toml.rs `WebSearchMode`.
            'web_search = "disabled"\n'
            "\n[agents]\n"
            f'default_subagent_model = "{hs_codex.ten}"\n'
            f'default_subagent_reasoning_effort = "{hs_codex.reasoning}"\n'
            "max_concurrent_threads_per_session = 1\n")


# ── Claude Code CLI ──────────────────────────────────────────────────────────

def claude_code(base: str, goc_claude: pathlib.Path,
                hs: HoSoModel | None = None) -> list:
    """`~/.claude/settings.json`, merged rather than replaced.

    ANTHROPIC_DEFAULT_HAIKU_MODEL is the one everybody forgets: Claude Code uses
    a second, smaller model for background work. Leave it unset and those calls
    ask for a Claude model this API does not serve, and fail quietly while the
    main session looks fine.
    """
    hs = hs or HO_SO_MODEL[MODEL]
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
        "ANTHROPIC_MODEL": hs.ten,
        "ANTHROPIC_DEFAULT_MODEL": hs.ten,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": hs.ten,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": hs.ten,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": hs.ten,
        "ANTHROPIC_DEFAULT_FABLE_MODEL": hs.ten,
        "CLAUDE_CODE_SUBAGENT_MODEL": hs.ten,
        "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
        "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "1",
        "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
        "CLAUDE_CODE_MAX_RETRIES": "10",
        "API_TIMEOUT_MS": "600000",
        "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": "1",
        "ENABLE_TOOL_SEARCH": "false",
        # 🔴 HAI DONG DUOI KHONG PHAI TINH CHINH — THIEU CHUNG LA MOT LOI TIEN,
        #    va chung da thieu o day trong khi ban Windows (`tools/cam_cli.py`)
        #    thi co. Tuc khach macOS/Linux nhan mot ban cai **yeu hon**, va
        #    khong co gi trong tep nay noi ra dieu do.
        #
        #    Claude Code khong biet `ltt-3.8` nen no GIA DINH cua so 200.000 va
        #    noi thang ra:
        #        "ltt-3.8" is not a model this version of Claude Code
        #        recognizes, so auto-compact will keep this session within
        #        200k tokens (the context window it assumes).
        #    Tran vao that cua ta nho hon nhieu, nen auto-compact khong bao gio
        #    kip nen va khach an 413 giua phien.
        "CLAUDE_CODE_MAX_CONTEXT_TOKENS": str(hs.cua_so),
        "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(TOKEN_RA_TRAN),
        # 🔴 AUTO_COMPACT_WINDOW la CUA SO, khong phai nguong: Claude tu tru
        #    min(maxOut, 20000) + 13000 (xem `CLAUDE_DEM_NEN`). Ghi `hs.nen`
        #    vao day (truoc 18/09) lam Claude nen som 33.000 token (R-05).
        "CLAUDE_CODE_AUTO_COMPACT_WINDOW": str(hs.cua_so_nen_claude),
        "MAX_MCP_OUTPUT_TOKENS": str(TRAN_KET_QUA_TOOL),
    })
    # Khoa KHONG vao day. `settings.json` bi chia se va commit thuong xuyen.
    env.setdefault("ANTHROPIC_AUTH_TOKEN", f"${BIEN_KHOA}")
    goc_json["env"] = env
    p.write_text(json.dumps(goc_json, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")
    return [f"  + cap nhat khoi `env` trong {p}"]


# ── Claude Desktop: khong tu dong duoc ──────────────────────────────────────

def claude_desktop(base: str, hs: HoSoModel | None = None) -> list:
    """Claude Desktop does NOT read ANTHROPIC_BASE_URL. It has its own form, and
    there is no supported file to write, so this prints steps instead of lying
    about having configured it."""
    hs = hs or HO_SO_MODEL[MODEL]
    return [
        "  i Claude Desktop phai lam bang tay (no khong doc bien moi truong):",
        "      Help -> Troubleshooting -> Enable Developer Mode",
        "      Developer -> Configure Third-Party Inference...",
        "      Inference provider  : Gateway",
        f"      Gateway base URL    : {_goc(base)}/api",
        "      Gateway API key     : khoa cua ban",
        "      Gateway auth scheme : Bearer",
        # 🔴 TEN TUYEN, khong phai ten model. Ban truoc in `ltt-3.8` o day
        #    va do la mot loi that: Desktop loc bo no khoi picker, roi nut
        #    gui tat han **ma khong bao gi**. Xem `MODEL_DESKTOP`.
        "      inferenceModels     : " + ", ".join(
            NHAN_DESKTOP[h.tuyen_desktop] + " [" + h.tuyen_desktop + "; tier="
            + TANG_DESKTOP[h.tuyen_desktop] + "; default]"
            for h in HO_SO_MODEL.values()),
        "      -> Apply locally",
        "    (inferenceModels BAT BUOC. Dung dung hai TEN TUYEN o tren;",
        "     Desktop loc model theo id, va hai ten nay cho phep chon ro",
        "     LTT-3.8 hoac LTT-3.5 trong picker.)",
    ]


# ── Kiem tra that, khong tin cau hinh ───────────────────────────────────────

def kiem_tra(base: str, key: str, hs: HoSoModel | None = None) -> int:
    """Ask the server, do not trust the files we just wrote."""
    hs = hs or HO_SO_MODEL[MODEL]
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
    if hs.ten not in ten:
        print(f"  ! may chu khong liet ke `{hs.ten}` (thay: {ten or 'khong co gi'})")
        return 1
    print(f"  OK may chu nhan khoa, va co `{hs.ten}`")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Cam LTT Studios vao Codex / Claude Code / Claude Desktop.")
    ap.add_argument("--key", default=os.environ.get(BIEN_KHOA, ""),
                    help=f"khoa ltt_sk_... (mac dinh: bien {BIEN_KHOA})")
    ap.add_argument("--base-url", default=MAC_DINH_BASE)
    ap.add_argument("--model", default=MODEL, choices=TEN_MODEL,
                    help=f"model can cam (mac dinh {MODEL}); hai model co "
                         "hai cua so ngu canh va hai bang gia")
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
    hs = hs_cua(getattr(a, "model", ""))
    print(f"May chu : {_goc(a.base_url)}")
    print(f"Model   : {hs.ten}  (cua so {hs.cua_so:,} token)")
    print("")

    if a.chi_kiem:
        print("Kiem tra (khong sua gi):")
        return kiem_tra(a.base_url, a.key, hs)

    print("Codex:")
    for d in codex(a.base_url, home / ".codex", hs):
        print(d)
    print("Claude Code (CLI):")
    for d in claude_code(a.base_url, home / ".claude", hs):
        print(d)
    print("Claude Desktop:")
    for d in claude_desktop(a.base_url, hs):
        print(d)

    print("")
    print("Kiem tra voi may chu:")
    rc = kiem_tra(a.base_url, a.key, hs)

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
