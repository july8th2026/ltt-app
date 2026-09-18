"""test_1440 — ngưỡng nén Claude Code tách khỏi Codex (R-05) + cập nhật profile cũ (R-13).

⭐ R-05. Claude Code KHÔNG nén ở `CLAUDE_CODE_AUTO_COMPACT_WINDOW`. Nó nén ở

       min(AUTO_COMPACT_WINDOW, cửa sổ model) − min(MAX_OUTPUT_TOKENS, 20.000) − 13.000

   Nguồn: mã của chính client 2.1.274 (`Dz()` = window − min(maxOut, `iwn`=20000);
   `KPe()` = Dz − 13000) và đo thật 18/09 bằng `/context` của client đó trỏ về
   LTT: cửa sổ 138.7k → "Autocompact buffer 33k" (nén ở ~105.7k, tức 76% như
   `01_EVIDENCE_MATRIX` đã chụp). Tài liệu chính thức khớp một cách gián tiếp:
   1M → "about 967K" = 1.000.000 − 33.000 (`model-config.md`, changelog).

   Trước đây ta khai AUTO_COMPACT_WINDOW = ngưỡng Codex (138.690) ⇒ Claude nén
   sớm 33.000 token. Codex thì nén ĐÚNG ở `model_auto_compact_token_limit`.

⭐ R-13. Bộ cài từng GIỮ NGUYÊN `ltt.config.toml` / catalog đã có ⇒ người cài
   cũ không bao giờ nhận số mới. Nay: cập nhật đúng các khoá LTT sở hữu, giữ
   khoá của người dùng.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tomllib

import pytest

from apps.ltt_llm import ngan_sach
from platform_core.llm.canonical import ALIAS_SANG_ID

GOC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC / "sdk"))
import ltt_cai_dat_cli as sdk  # noqa: E402

#: Hai hằng của client Claude Code, đọc từ mã 2.1.274 và đo lại bằng `/context`.
TRU_RA_TOI_DA_CLAUDE = 20_000
DEM_NEN_CLAUDE = 13_000
SAN_CUA_SO_NEN_CLAUDE = 100_000     # env-vars.md: "from 100000 to 1000000"


def _cam_cli():
    spec = importlib.util.spec_from_file_location(
        "cam_cli_1440", GOC / "tools" / "cam_cli.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _diem_nen_claude(cua_so_nen: int, cua_so_model: int, max_out: int) -> int:
    """Nơi Claude Code THẬT SỰ nén — công thức của client, không phải của ta."""
    return (min(cua_so_nen, cua_so_model) - min(max_out, TRU_RA_TOI_DA_CLAUDE)
            - DEM_NEN_CLAUDE)


BO_CAI = {"sdk": lambda: sdk, "cam_cli": _cam_cli}


# ── R-05: điểm nén thật của Claude ≈ ngưỡng Codex, không sớm 33K ────────────

@pytest.mark.parametrize("bo_cai", sorted(BO_CAI))
@pytest.mark.parametrize("ten", ["ltt-3.8", "ltt-3.5"])
def test_diem_nen_that_cua_Claude_bang_nguong_Codex(bo_cai, ten):
    mod = BO_CAI[bo_cai]()
    mid = ALIAS_SANG_ID[ten]
    hs = mod.HO_SO_MODEL[ten]
    assert mod.CLAUDE_TRU_RA_TOI_DA == TRU_RA_TOI_DA_CLAUDE
    assert mod.CLAUDE_DEM_NEN == DEM_NEN_CLAUDE
    cua_so = hs.cua_so_nen_claude
    # Không vượt cửa sổ công bố: client tự kẹp về MAX_CONTEXT_TOKENS, và một
    # con số bị kẹp là con số ta không còn kiểm soát.
    assert cua_so <= ngan_sach.cong_bo_cua(mid)
    assert cua_so >= SAN_CUA_SO_NEN_CLAUDE
    diem = _diem_nen_claude(cua_so, hs.cua_so, mod.TOKEN_RA_TRAN)
    nen = ngan_sach.nen_cua(mid)
    # Không muộn hơn ngưỡng Codex (còn chỗ cho trọn một lượt sinh)…
    assert diem <= nen, f"{ten}: Claude nen o {diem} > nguong {nen}"
    # …và không sớm vô cớ: lệch chỉ được phép do kẹp ở cửa sổ công bố.
    assert nen - diem == max(0, nen + TRU_RA_TOI_DA_CLAUDE + DEM_NEN_CLAUDE
                             - ngan_sach.cong_bo_cua(mid)), (
        f"{ten}: Claude nen som {nen - diem} token so voi Codex")


@pytest.mark.parametrize("bo_cai", sorted(BO_CAI))
def test_hang_Claude_rieng_Codex_giu_nguong_cu(bo_cai):
    mod = BO_CAI[bo_cai]()
    assert mod.CUA_SO_NEN_CLAUDE == mod.HO_SO_MODEL["ltt-3.8"].cua_so_nen_claude
    assert mod.CUA_SO_NEN_CLAUDE != mod.NEN_HOI_THOAI
    assert mod.NEN_HOI_THOAI == ngan_sach.nen_cua(ALIAS_SANG_ID["ltt-3.8"])


def test_hai_bo_cai_cung_cua_so_nen_Claude():
    cc = _cam_cli()
    for ten in ("ltt-3.8", "ltt-3.5"):
        assert (cc.HO_SO_MODEL[ten].cua_so_nen_claude
                == sdk.HO_SO_MODEL[ten].cua_so_nen_claude)


@pytest.mark.parametrize("ten", ["ltt-3.8", "ltt-3.5"])
def test_sdk_Claude_nhan_cua_so_nen_Claude_Codex_nhan_nguong(tmp_path, ten):
    hs = sdk.HO_SO_MODEL[ten]
    sdk.claude_code("https://x.test", tmp_path / ".claude", hs)
    env = json.loads((tmp_path / ".claude" / "settings.json")
                     .read_text(encoding="utf-8"))["env"]
    assert env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == str(hs.cua_so_nen_claude)
    sdk.codex("https://x.test", tmp_path / ".codex")
    for tep, m in (("ltt.config.toml", "ltt-3.8"),
                   ("ltt-fast.config.toml", "ltt-3.5")):
        p = tomllib.loads((tmp_path / ".codex" / tep).read_text(encoding="utf-8"))
        assert p["model_auto_compact_token_limit"] == sdk.HO_SO_MODEL[m].nen


@pytest.fixture()
def cc(tmp_path, monkeypatch):
    mod = _cam_cli()
    mod.NHA = tmp_path
    mod.TEP_TRANG_THAI = tmp_path / ".ltt" / "cam_cli_trang_thai.json"
    mod.TEP_CATALOG = tmp_path / ".codex" / "ltt_model_catalog.json"
    mod.TEP_NHAT_KY = tmp_path / "log" / "cam-cli.log"
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))
    (tmp_path / "AppData" / "Roaming" / "Code" / "User").mkdir(parents=True)
    env = {}
    monkeypatch.setattr(mod, "_setx", lambda t, v: (env.__setitem__(t, v), True)[1])
    monkeypatch.setattr(mod, "_xoa_env", lambda t: (env.pop(t, None), True)[1])
    mod._env_gia = env
    return mod


@pytest.mark.parametrize("ten", ["ltt-3.8", "ltt-3.5"])
def test_cam_cli_Claude_va_VSCode_nhan_cua_so_nen_Claude(cc, ten):
    hs = cc.HO_SO_MODEL[ten]
    cc.cam_claude("https://x.test", {"model": ten}, toan_cuc=False)
    assert cc._env_gia["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == str(hs.cua_so_nen_claude)
    cc.cam_vscode("https://x.test", {"model": ten})
    s = json.loads(cc._vscode_settings().read_text(encoding="utf-8"))
    env = {v["name"]: v["value"] for v in s["claudeCode.environmentVariables"]}
    assert env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == str(hs.cua_so_nen_claude)


# ── R-13: người cài cũ nhận số mới, khoá của họ còn nguyên ──────────────────

#: Profile một người cài bản cũ: số CŨ ở khoá LTT, cộng khoá/bảng CỦA HỌ.
PROFILE_CU = (
    '# ghi chu cua nguoi dung\n'
    'model = "ltt-3.8"\n'
    'model_provider = "ltt"\n'
    'model_reasoning_effort = "low"\n'
    'model_context_window = 156385\n'
    'model_auto_compact_token_limit = 123617\n'
    'approval_policy = "never"\n'
    '\n[agents]\n'
    'default_subagent_model = "ltt-3.8"\n'
    'max_concurrent_threads_per_session = 4\n'
    '\n[mcp_servers.cua_toi]\n'
    'command = "node"\n'
    'args = ["server.js", "--port=9"]\n'
)


def _kiem_profile_cap_nhat(p: dict, hs, cat: str) -> None:
    # Khoá LTT sở hữu: số MỚI.
    assert p["model_context_window"] == hs.cua_so
    assert p["model_auto_compact_token_limit"] == hs.nen
    assert p["model_auto_compact_token_limit_scope"] == "total"
    assert p["model_catalog_json"] == cat
    assert p["agents"]["max_concurrent_threads_per_session"] == 1
    # R-11 (18/09): LTT không phục vụ công cụ hosted `web_search` ⇒ profile tắt
    # nó (`codex-rs/config/src/profile_toml.rs`: `web_search: Option<WebSearchMode>`,
    # "disabled" | "cached" | "indexed" | "live").
    assert p["web_search"] == "disabled"
    # Khoá của người dùng: còn nguyên — kể cả lựa chọn effort của họ.
    assert p["approval_policy"] == "never"
    assert p["model_reasoning_effort"] == "low"
    assert p["mcp_servers"]["cua_toi"] == {"command": "node",
                                          "args": ["server.js", "--port=9"]}


def test_sdk_cap_nhat_profile_cu_giu_khoa_nguoi_dung(tmp_path):
    goc = tmp_path / ".codex"
    goc.mkdir()
    (goc / "ltt.config.toml").write_text(PROFILE_CU, encoding="utf-8")
    (goc / "ltt_model_catalog.json").write_text('{"models": []}', encoding="utf-8")
    sdk.codex("https://x.test", goc)
    van = (goc / "ltt.config.toml").read_text(encoding="utf-8")
    assert "# ghi chu cua nguoi dung" in van
    _kiem_profile_cap_nhat(tomllib.loads(van), sdk.HO_SO_MODEL["ltt-3.8"],
                           str(goc / "ltt_model_catalog.json"))
    # Catalog là tệp của LTT: phải được làm mới, có sao lưu.
    cat = json.loads((goc / "ltt_model_catalog.json").read_text(encoding="utf-8"))
    assert [m["slug"] for m in cat["models"]] == ["ltt-3.8", "ltt-3.5"]
    assert (goc / "ltt_model_catalog.json.ltt-bak").exists()
    assert (goc / "ltt.config.toml.ltt-bak").read_text(encoding="utf-8") == PROFILE_CU


def test_sdk_chay_lai_khong_doi_gi(tmp_path):
    goc = tmp_path / ".codex"
    goc.mkdir()
    (goc / "ltt.config.toml").write_text(PROFILE_CU, encoding="utf-8")
    sdk.codex("https://x.test", goc)
    lan1 = (goc / "ltt.config.toml").read_bytes()
    sdk.codex("https://x.test", goc)
    assert (goc / "ltt.config.toml").read_bytes() == lan1


def test_sdk_profile_hong_thi_khong_dung_toi(tmp_path):
    goc = tmp_path / ".codex"
    goc.mkdir()
    rac = 'model = "ltt-3.8"\n[agents\n'
    (goc / "ltt.config.toml").write_text(rac, encoding="utf-8")
    ra = sdk.codex("https://x.test", goc)
    assert (goc / "ltt.config.toml").read_text(encoding="utf-8") == rac
    assert any("ltt.config.toml" in d and "!" in d for d in ra)


def test_sdk_settings_Claude_cap_nhat_khoa_LTT_giu_khoa_nguoi_dung(tmp_path):
    goc = tmp_path / ".claude"
    goc.mkdir()
    (goc / "settings.json").write_text(json.dumps({
        "theme": "dark",
        "env": {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "138690",
                "MY_OWN_VAR": "giu", "ANTHROPIC_AUTH_TOKEN": "$KHAC"}}),
        encoding="utf-8")
    sdk.claude_code("https://x.test", goc)
    d = json.loads((goc / "settings.json").read_text(encoding="utf-8"))
    assert d["theme"] == "dark"
    assert d["env"]["MY_OWN_VAR"] == "giu"
    assert d["env"]["ANTHROPIC_AUTH_TOKEN"] == "$KHAC"
    assert d["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == str(
        sdk.HO_SO_MODEL["ltt-3.8"].cua_so_nen_claude)


def test_cam_cli_cap_nhat_profile_cu_giu_khoa_nguoi_dung(cc, tmp_path):
    goc = tmp_path / ".codex"
    goc.mkdir()
    prof = goc / "ltt.config.toml"
    prof.write_bytes(PROFILE_CU.replace("\n", "\r\n").encode())
    tt = {}
    cc.cam_codex("https://x.test", tt)
    van = prof.read_bytes()
    assert b"\r\n" in van and b"\n" not in van.replace(b"\r\n", b""), "mat CRLF"
    _kiem_profile_cap_nhat(tomllib.loads(van.decode()), cc.HO_SO_MODEL["ltt-3.8"],
                           str(cc.TEP_CATALOG))
    bs = prof.with_suffix(prof.suffix + ".truoc-ltt")
    assert bs.read_bytes() == PROFILE_CU.replace("\n", "\r\n").encode()
    # Chạy lại: không đổi thêm byte nào.
    cc.cam_codex("https://x.test", tt)
    assert prof.read_bytes() == van


# ── R-11: profile MỚI cũng tắt `web_search` (cả hai bộ cài) ─────────────────

def test_profile_moi_tat_web_search_sdk_va_cam_cli(cc, tmp_path):
    for hs in (sdk.HO_SO_MODEL["ltt-3.8"], sdk.HO_SO_MODEL["ltt-3.5"]):
        assert tomllib.loads(sdk._profile_codex(hs, tmp_path / "c.json"))[
            "web_search"] == "disabled"
    for hs in (cc.HO_SO_MODEL["ltt-3.8"], cc.HO_SO_MODEL["ltt-3.5"]):
        assert tomllib.loads(cc._codex_profile(hs))["web_search"] == "disabled"


def test_sdk_KHONG_cham_web_search_trong_config_toml_cua_khach(tmp_path):
    """`config.toml` là của khách: khoá `web_search` của họ ở đó giữ nguyên;
    LTT chỉ tắt trong profile LTT của mình."""
    goc = tmp_path / ".codex"
    goc.mkdir()
    cfg = goc / "config.toml"
    cfg.write_text('web_search = "live"\n', encoding="utf-8")
    sdk.codex("https://x.test", goc)
    assert tomllib.loads(cfg.read_text(encoding="utf-8"))["web_search"] == "live"

def test_mau_cau_hinh_codex_trang_tai_lieu_tat_web_search():
    """Mau xamples.py khach chep tu trang tai lieu cung tat web_search (R-11)."""
    from platform_core.public_api import examples as ex
    for m in ex.CODEX_MODEL_LIMITS:
        for desktop in (False, True):
            goc = ex._codex_model_root(m, desktop=desktop)
            assert tomllib.loads(goc)["web_search"] == "disabled"
