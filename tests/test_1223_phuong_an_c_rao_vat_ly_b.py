"""Phương án C, bước 3 — máy B là RÀO VẬT LÝ, đọc thẳng `llama-swap.yaml`.

Kế hoạch: `docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md` §3.3, mục 2, 3, 5 (mục 1, 4,
6 thuộc bước 2 ở máy A). Bất biến phải giữ:

  * cổng dựng sổ từ CÙNG tệp llama-swap khởi động: bể = `-c`, số chuỗi = `-np`
    (không phải `token_budget` của A — B là rào vật lý);
  * trần vào **theo model** = `-c − max_out − DEM_UOC`, cùng công thức với A (O-02);
  * giữ chỗ: có `X-LTT-Token-Dat` ⇒ đúng số của A; vắng ⇒ ≥ A − DEM_UOC;
  * không còn luật whale/RPM ở cổng (O-01, O-03).

Mọi chỗ đọc máy A đi qua ba hàm `_a_*` ngay dưới (đã gộp bước 2: `DEM_UOC`,
`luat_cho(AdmissionModel)` qua `luong._dat_cho`).
"""
from __future__ import annotations

import ast
import pathlib

import pytest
import yaml

from llm_gateway import vat_ly as VL
from llm_gateway.config import DEM_UOC_MAC_DINH, Config

GOC = pathlib.Path(__file__).resolve().parents[1]
YAML_KHO = GOC / "llm_gateway" / "deploy" / "llama-swap.yaml"
M38, M35 = "qwen38-api", "qwen35-api"


# ── Máy A: một chỗ đọc ───────────────────────────────────────────────────────

def _a_dem_uoc() -> int:
    from apps.ltt_llm import ngan_sach as ns
    return int(ns.DEM_UOC)


def _a_tran_vao(model_id: str) -> int:
    from apps.ltt_llm import ngan_sach as ns
    return int(ns.tran_vao_cua(model_id))


def _a_dat_cho(than: dict, alias: str) -> tuple[dict, int]:
    """`(thân máy A gửi sang B, token_dat_truoc)` theo ĐÚNG đường `tien_kiem`."""
    from apps.ltt_llm.executor import EXECUTOR
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.llm import luat_nhan
    from platform_core.runtime_noi_bo import luong

    tin = luong.uoc_tin_nhan(than)
    vao = int(EXECUTOR.estimate_input(tin))
    xin_ra = luong.tran_token_ra(than, vao, EXECUTOR)
    gui = dict(than)
    luong._kep_tran_gui(gui, "/v1/messages", xin_ra)
    gui["model"] = EXECUTOR.model_id(alias)
    suc = MANIFEST.tools[0].admission_cho(alias)
    dat = luong._dat_cho(suc, lop=luat_nhan.TUONG_TAC, token_vao_uoc=vao,
                         xin_ra=xin_ra, so_anh=luong.dem_anh(than))["token_dat_truoc"]
    return gui, int(dat)


# ── 0. Bộ đọc hẹp == yaml.safe_load trên tệp thật ────────────────────────────

def _theo_pyyaml(van: str) -> dict:
    cfg = yaml.safe_load(van)
    macros = cfg.get("macros") or {}
    ra = {}
    for ten, m in (cfg.get("models") or {}).items():
        cmd = str(m["cmd"])
        for _ in range(8):
            for k, gt in macros.items():
                cmd = cmd.replace("${%s}" % k, str(gt))
        t = cmd.split()
        ra[ten] = VL.VatLy(ctx=_so_co(t, "-c", "--ctx-size"),
                           np=_so_co(t, "-np", "--parallel"),
                           reasoning_budget=_so_co(t, "--reasoning-budget"),
                           kvu=("-kvu" in t or "--kv-unified" in t))
    return ra


def _so_co(t: list, *cs: str):
    return next((int(t[t.index(c) + 1]) for c in cs if c in t), None)


def test_bo_doc_hep_KHOP_pyyaml_tren_tep_that():
    """venv máy B không có PyYAML, nên cổng có bộ đọc riêng; nó phải nói đúng
    điều PyYAML nói — trên CHÍNH tệp llama-swap khởi động."""
    van = YAML_KHO.read_text(encoding="utf-8")
    assert VL.doc_van_ban(van) == _theo_pyyaml(van)
    vl = VL.doc_van_ban(van)
    assert set(vl) == {M38, M35}
    assert all(v.kvu for v in vl.values()), "-kvu vang: be KV khong con la MOT be -c"


def test_bo_doc_mo_macro_va_bo_chu_thich():
    van = (
        "macros:\n"
        "  # chu thich\n"
        '  CTX: "-c 4096"\n'
        "  CHUNG: >-\n"
        "    -kvu\n"
        "    ${CTX}\n"
        "models:\n"
        "  # ---\n"
        "  a:\n"
        "    cmd: |\n"
        "      bin ${CHUNG}\n"
        "      -np 2 --reasoning-budget 512\n"
        "    ttl: 5   # x\n"
    )
    assert VL.doc_van_ban(van) == {"a": VL.VatLy(ctx=4096, np=2, reasoning_budget=512,
                                                 kvu=True)}
    assert VL.doc_van_ban(van) == _theo_pyyaml(van)


@pytest.mark.parametrize("cmd", ["bin -c 4096", "bin -np 3", "bin -c x -np 3",
                                 "bin -c 0 -np 3"])
def test_thieu_hoac_hong_c_np_thi_FAIL_CLOSED(cmd):
    """Không biết `-c`/`-np` của card thì không có rào — thà cổng không lên."""
    van = f"models:\n  a:\n    cmd: |\n      {cmd}\n"
    with pytest.raises(VL.YamlHong):
        VL.doc_van_ban(van)


def test_tim_yaml_uu_tien_tep_CANH_goi_roi_moi_toi_ban_kho(monkeypatch, tmp_path):
    """Máy B: `H:\\LTT_LLM\\gateway\\llama-swap.yaml` (tệp `LTTLlamaSwap --config`)
    thắng bản `llm_gateway/deploy/` đi theo gói."""
    monkeypatch.delenv(VL.BIEN_DUONG_YAML, raising=False)
    ung = VL.cac_duong_ung_vien()
    assert ung[0] == VL._thu_muc_goi().parent / "llama-swap.yaml"
    assert ung[1] == YAML_KHO
    monkeypatch.setenv(VL.BIEN_DUONG_YAML, str(tmp_path / "khong-co.yaml"))
    with pytest.raises(VL.YamlHong):
        VL.tim_yaml()


# ── 2. Cổng dựng sổ từ cùng yaml: bể = -c, chuỗi = -np ──────────────────────

def test_cong_dung_so_tu_yaml_be_la_C_chuoi_la_NP(monkeypatch):
    from fastapi.testclient import TestClient

    from llm_gateway.api import create_app
    from tests.test_250_llm_gateway import FakeUpstream, _tt_ranh

    monkeypatch.delenv(VL.BIEN_DUONG_YAML, raising=False)
    monkeypatch.setenv("LTT_LLM_MODELS", f"{M38},{M35}")
    cfg = Config.from_env()
    that = _theo_pyyaml(YAML_KHO.read_text(encoding="utf-8"))
    assert cfg.vat_ly == that

    c = TestClient(create_app(cfg, FakeUpstream(), trong_tai=_tt_ranh()))
    h = c.get("/health").json()
    for m, v in that.items():
        so = h["gioi_han"]["theo_model"][m]
        assert so["token_pool"] == v.ctx, (m, so)
        assert so["max_dong_thoi"] == v.np, (m, so)
        assert h["vat_ly"]["theo_model"][m]["ctx"] == v.ctx
    ctx = {d["id"]: d["context_window"] for d in c.get("/v1/models").json()["data"]}
    assert ctx == {m: v.ctx for m, v in that.items()}


def test_model_mo_nhung_yaml_khong_co_ho_so_thi_KHONG_mo():
    from fastapi.testclient import TestClient

    from llm_gateway.api import create_app
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _tt_ranh

    cfg = _cfg(models_mo=(M38, M35),
               vat_ly={M38: VL.VatLy(ctx=100_000, np=3, kvu=True)})
    c = TestClient(create_app(cfg, FakeUpstream(), trong_tai=_tt_ranh()))
    assert [d["id"] for d in c.get("/v1/models").json()["data"]] == [M38]
    assert c.get("/health").json()["models_thieu_vat_ly"] == [M35]
    r = c.post("/v1/chat/completions", json={"model": M35, "messages": []})
    assert r.status_code == 404


# ── O-02: trần vào THEO MODEL, cùng công thức với máy A ─────────────────────

def test_mac_dinh_tham_so_B_khop_may_A(monkeypatch):
    from apps.ltt_llm import ngan_sach as ns

    monkeypatch.delenv("LTT_LLM_MAX_OUTPUT_TOKENS", raising=False)
    monkeypatch.delenv("LTT_LLM_DEM_UOC", raising=False)
    cfg = Config.from_env()
    assert cfg.max_output_tokens == ns.TOKEN_RA_TRAN
    assert cfg.dem_uoc == DEM_UOC_MAC_DINH == _a_dem_uoc()
    import dataclasses
    mac = {f.name: f.default for f in dataclasses.fields(Config)}
    assert mac["dem_uoc"] == DEM_UOC_MAC_DINH


def test_tran_vao_B_bang_tran_vao_A_cho_CA_HAI_model(monkeypatch):
    """Bắt O-02: trước bước 3 B chặn 3.5 ở trần của 3.8 ⇒ 413 sau 200."""
    from fastapi.testclient import TestClient

    from llm_gateway.api import create_app
    from tests.test_250_llm_gateway import FakeUpstream, _tt_ranh

    monkeypatch.delenv("LTT_LLM_MAX_OUTPUT_TOKENS", raising=False)
    monkeypatch.delenv("LTT_LLM_DEM_UOC", raising=False)
    monkeypatch.setenv("LTT_LLM_MODELS", f"{M38},{M35}")
    cfg = Config.from_env()
    c = TestClient(create_app(cfg, FakeUpstream(), trong_tai=_tt_ranh()))
    tran = c.get("/health").json()["tran"]["input_tokens"]
    for m in (M38, M35):
        assert tran[m] == _a_tran_vao(m), (m, tran)
        assert VL.tran_vao(cfg.vat_ly[m], cfg.max_output_tokens, cfg.dem_uoc) == tran[m]
    assert tran[M35] > tran[M38], "hai model mot tran = O-02 quay lai"


def test_xuat_tham_so_a_in_dung_so_ngan_sach():
    """`deploy.ps1` ghi gateway.env bằng tệp này — nó phải in đúng số của A."""
    import importlib.util

    from apps.ltt_llm import ngan_sach as ns

    tep = GOC / "llm_gateway" / "deploy" / "xuat_tham_so_a.py"
    spec = importlib.util.spec_from_file_location("xuat_tham_so_a", tep)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.tham_so() == {"LTT_LLM_MAX_OUTPUT_TOKENS": ns.TOKEN_RA_TRAN,
                             "LTT_LLM_DEM_UOC": _a_dem_uoc()}


# ── 3. Giữ chỗ: A và B cùng số ──────────────────────────────────────────────

ANH = {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                   "data": "QUJD" * 50}}
THAN_MAU = {
    "text": {"model": "ltt-3.8",
             "messages": [{"role": "user", "content": "Tóm tắt giúp tôi. " * 800}]},
    "text_35_max_tokens": {"model": "ltt-3.5", "max_tokens": 2_000,
                           "messages": [{"role": "user", "content": "xin chao " * 300}]},
    "tool": {"model": "ltt-3.8",
             "system": [{"type": "text", "text": "Bạn là coding agent."}],
             "messages": [
                 {"role": "assistant", "content": [{
                     "type": "tool_use", "id": "toolu_1", "name": "Read",
                     "input": {"file_path": "src/app.py", "limit": 4000}}]},
                 {"role": "user", "content": [{
                     "type": "tool_result", "tool_use_id": "toolu_1",
                     "content": [{"type": "text", "text": "def f():\n    pass\n" * 900}]}]},
             ],
             "tools": [{"name": f"Tool{i}", "description": "Đọc một tệp " * 5,
                        "input_schema": {"type": "object", "properties": {
                            "file_path": {"type": "string"},
                            "limit": {"type": "integer"}}}} for i in range(40)]},
    "anh": {"model": "ltt-3.5",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Ảnh này là gì?"}, ANH, ANH]}]},
    "responses": {"model": "ltt-3.8", "max_output_tokens": 4_096,
                  "instructions": "Trả lời ngắn.",
                  "input": [{"role": "user", "content": [
                      {"type": "input_text", "text": "giai thich " * 2_000}]}]},
}


def _b_giu(gui: dict, *, token_khai: int) -> int:
    """Phép giữ chỗ của cổng, đúng thứ `api._kiem_va_chay` làm với thân nhận được."""
    from apps.ltt_llm import ngan_sach as ns
    from llm_gateway.ngan_sach import do_yeu_cau

    max_out = ns.TOKEN_RA_TRAN
    xin = gui.get("max_tokens", gui.get("max_output_tokens"))
    xin_ra = min(int(xin), max_out) if isinstance(xin, int) and xin > 0 else max_out
    v = VL.doc_tep(YAML_KHO)[gui["model"]]
    return VL.token_giu(token_vao=do_yeu_cau(gui).token_vao, xin_ra=xin_ra, v=v,
                        dem_uoc=_a_dem_uoc(), token_khai=token_khai)


@pytest.mark.parametrize("ten", sorted(THAN_MAU))
def test_CO_header_B_giu_DUNG_so_cua_A(ten):
    gui, dat_a = _a_dat_cho(THAN_MAU[ten], THAN_MAU[ten]["model"])
    assert _b_giu(gui, token_khai=dat_a) == dat_a


@pytest.mark.parametrize("ten", sorted(THAN_MAU))
def test_VANG_header_B_giu_KHONG_it_hon_A_tru_DEM_UOC(ten):
    gui, dat_a = _a_dat_cho(THAN_MAU[ten], THAN_MAU[ten]["model"])
    b = _b_giu(gui, token_khai=0)
    assert b >= dat_a - _a_dem_uoc(), f"{ten}: B giu {b}, A giu {dat_a}"


def test_header_hong_thap_hon_dau_vao_KHONG_ha_duoc_san_vat_ly():
    v = VL.VatLy(ctx=100_000, np=3, kvu=True)
    assert VL.token_giu(token_vao=5_000, xin_ra=1_000, v=v, dem_uoc=2_048,
                        token_khai=1) == 5_000


# ── 5. Không còn luật whale/RPM ở cổng (AST) ────────────────────────────────

_CAM = ("whale", "rpm", "ca_voi")
_CHUOI_CAM = ("x-ltt-whale", "luot moi phut", "ca voi", "whale")


def _pham_whale_rpm(van: str) -> list[str]:
    cay = ast.parse(van)
    pham = []
    for nut in ast.walk(cay):
        ten = None
        if isinstance(nut, ast.Name):
            ten = nut.id
        elif isinstance(nut, ast.Attribute):
            ten = nut.attr
        elif isinstance(nut, ast.arg):
            ten = nut.arg
        elif isinstance(nut, (ast.FunctionDef, ast.ClassDef)):
            ten = nut.name
        elif isinstance(nut, ast.keyword):
            ten = nut.arg
        elif isinstance(nut, ast.Constant) and isinstance(nut.value, str):
            # Chuỗi NGẮN là chuỗi mã (tên header, khoá /health, lý do 429);
            # docstring/chú thích dài được phép kể lịch sử.
            s = nut.value.lower()
            if len(s) <= 80 and any(c in s for c in _CHUOI_CAM):
                pham.append(f"chuoi {nut.value!r}")
            continue
        if ten and any(c in ten.lower() for c in _CAM):
            pham.append(ten)
    return sorted(set(pham))


@pytest.mark.parametrize("tep", ["gioi_han.py", "so_theo_model.py", "api.py",
                                 "config.py", "vat_ly.py", "dem.py"])
def test_cong_KHONG_con_luat_whale_hay_rpm(tep):
    """Đọc AST, không quét chữ: chú thích lịch sử được phép nhắc tên, MÃ thì không."""
    pham = _pham_whale_rpm((GOC / "llm_gateway" / tep).read_text(encoding="utf-8"))
    assert not pham, f"{tep} con luat whale/RPM: {pham}"


def test_doi_chung_phep_AST_BAT_duoc_ban_co_whale_rpm():
    """Số 0 cần đối chứng: bộ dò phải đỏ trên chính hình dạng đã gỡ."""
    cu = (
        "class GioiHan:\n"
        "    def __init__(self, *, rpm=120): self.rpm = rpm\n"
        "    def _xin_vao(self, token, la_whale=False):\n"
        "        return 'vuot 120 luot moi phut'\n"
        "def chat(x_ltt_whale: str = ''): pass\n"
    )
    pham = _pham_whale_rpm(cu)
    assert {"rpm", "la_whale", "x_ltt_whale"} <= set(pham), pham


def test_bien_da_go_duoc_BAO_khi_con_dat(monkeypatch):
    from llm_gateway.config import bien_da_go_con_dat

    monkeypatch.setenv("LTT_LLM_RPM", "120")
    monkeypatch.setenv("LTT_LLM_TOKEN_POOL__qwen35-api", "1")
    con = bien_da_go_con_dat()
    assert any(t.upper() == "LTT_LLM_RPM" for t in con)
    assert any(t.upper().startswith("LTT_LLM_TOKEN_POOL__") for t in con)
