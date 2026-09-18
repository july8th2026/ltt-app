"""test_1430 — suy nghĩ do MÁY CHỦ quyết, effort theo TỪNG model (plan v2 Task 3 + 4, L-26).

Chủ dự án chốt 18/09/2026: *"mục tiêu là chất lượng và sức mạnh kết quả cao; giá
trị phải theo khuyến nghị chính thức của model"*.

  * `ltt-3.5` (Qwen3.5-9B): model card chỉ có suy nghĩ BẬT/TẮT, không có nấc
    effort ⇒ MỘT chế độ, suy nghĩ BẬT. Effort gửi tới được NHẬN (Codex luôn gửi)
    nhưng GỠ trước máy B + header `X-LTT-Effort-Bo-Qua: 1`. Tắt suy nghĩ: cấm.
  * `ltt-3.8` (Qwen3.8-27B): model card có `low|medium|xhigh`, mặc định `xhigh`.
    `high`/`max` ⇒ `xhigh`, `minimal` ⇒ `low`, `none` ⇒ 400.
  * Budget suy nghĩ chỉ engine quyết (`--reasoning-budget` trong llama-swap.yaml):
    mọi trường ghi đè budget/bật-tắt của client bị gỡ ở CẢ BA cửa.
  * Sàn `max_tokens` của 3.5 ≥ budget suy nghĩ + 512 (budget đọc từ yaml).
  * Catalog `/v1/models` là nơi DUY NHẤT client (LTTCODE Task 13) đọc danh sách mức.
"""
from __future__ import annotations

import copy
import json
import pathlib
import types

import pytest

from platform_core.runtime_noi_bo import luong
from platform_core.runtime_noi_bo.luong import ThamSoSai, chuan_hoa_suy_nghi

GOC = pathlib.Path(__file__).resolve().parents[1]
YAML_KHO = GOC / "llm_gateway" / "deploy" / "llama-swap.yaml"

#: Mọi hình dạng "ghi đè suy nghĩ" của client (danh sách trường của 026f52dd +
#: khoá template v22.5 dòng 6-14 + thẻ nội dung dòng 35-77).
THAN_GHI_DE = {
    "reasoning_budget_tokens": 99999,
    "thinking_budget_tokens": 1,
    "reasoning_budget_message": "het gio",
    "reasoning_control": True,
    "thinking": {"type": "enabled", "budget_tokens": 10000},
    "chat_template_kwargs": {"enable_thinking": False, "preserve_thinking": True,
                             "preserve_reasoning": False,
                             "auto_disable_thinking_with_tools": True,
                             "tool_call_format": "xml"},
}
KHOA_GHI_DE = ("reasoning_budget_tokens", "thinking_budget_tokens",
               "reasoning_budget_message", "reasoning_control", "thinking")


def _chuoi_trong(x) -> list[str]:
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict):
        return [s for v in x.values() for s in _chuoi_trong(v)]
    if isinstance(x, list):
        return [s for v in x for s in _chuoi_trong(v)]
    return []


def _sach_ghi_de(gui: dict) -> None:
    for k in KHOA_GHI_DE:
        assert k not in gui, f"`{k}` van di len may B"
    ctk = gui.get("chat_template_kwargs") or {}
    for k in ("enable_thinking", "preserve_thinking", "preserve_reasoning",
              "auto_disable_thinking_with_tools"):
        assert k not in ctk, f"`chat_template_kwargs.{k}` van di len may B"
    for s in _chuoi_trong({k: gui.get(k) for k in
                           ("messages", "system", "input", "instructions")}):
        assert "<|think_" not in s, f"the suy nghi con trong noi dung: {s!r}"


def _bo_budget_may_chu(gui: dict, duong: str, max_ra: int = 4000) -> dict:
    """Bản sao `gui` đã tách budget MÁY CHỦ đặt cho 3.5 (sự cố 18/09 22:45).

    Chốt nó là của máy chủ (`min(budget engine, max_ra − 512)`), không phải số
    khách gửi, và ở đúng TRƯỜNG llama.cpp đọc cho cửa ấy — rồi mới để
    `_sach_ghi_de` kiểm phần còn lại.
    """
    from apps.ltt_llm.ngan_sach import BUDGET_SUY_NGHI_35, TOKEN_CHO_TRA_LOI
    gui = dict(gui)
    mong = min(BUDGET_SUY_NGHI_35, max_ra - TOKEN_CHO_TRA_LOI)
    if duong.endswith("/messages"):
        assert gui.pop("thinking", None) == {"type": "enabled", "budget_tokens": mong}
        assert "reasoning_budget_tokens" not in gui
    else:
        assert gui.pop("reasoning_budget_tokens", None) == mong
        assert "thinking" not in gui
    return gui


# ── Than theo tung giao thuc (ba cua) ────────────────────────────────────────

def _than_chat(model: str, **them) -> dict:
    return {"model": model, "max_tokens": 4000,
            "messages": [{"role": "system", "content": "<|think_off|>ngan gon"},
                         {"role": "user", "content": [
                             {"type": "text", "text": "xin chao <|think_low|>"}]}],
            **copy.deepcopy(THAN_GHI_DE), **them}


def _than_messages(model: str, **them) -> dict:
    return {"model": model, "max_tokens": 4000, "stream": True,
            "system": [{"type": "text", "text": "<|think_max|> tro ly"}],
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "<|think_off|>xin chao"}]}],
            **copy.deepcopy(THAN_GHI_DE), **them}


def _than_responses(model: str, **them) -> dict:
    return {"model": model, "max_output_tokens": 4000, "stream": True,
            "instructions": "<|think_off|> tro ly",
            "input": [{"type": "message", "role": "user", "content": [
                {"type": "input_text", "text": "<|think_minimal|>xin chao"}]}],
            **copy.deepcopy(THAN_GHI_DE), **them}


# ══ Task 4 Step 1: go ghi de o ham dung chung ═══════════════════════════════

@pytest.mark.parametrize("dung", [_than_chat, _than_messages, _than_responses],
                         ids=["chat", "messages", "responses"])
@pytest.mark.parametrize("model", ["ltt-3.8", "ltt-3.5", "qwen38-api", "qwen35-api"])
def test_go_moi_truong_ghi_de_suy_nghi(dung, model):
    than = dung(model)
    goc = copy.deepcopy(than)
    gui, _bo_qua = chuan_hoa_suy_nghi(than, model)
    _sach_ghi_de(gui)
    assert than == goc, "khong duoc sua than dau vao"
    # Khoa template KHONG phai suy nghi thi giu nguyen.
    assert gui["chat_template_kwargs"] == {"tool_call_format": "xml"}
    # Chu cua khach giu nguyen, chi mat the.
    assert "xin chao" in json.dumps(gui, ensure_ascii=False)


def test_thinking_moi_hinh_dang_deu_go():
    for th in ({"type": "enabled"}, {"type": "adaptive"}, {"type": "disabled"}):
        gui, _ = chuan_hoa_suy_nghi({"model": "ltt-3.8", "thinking": th,
                                     "messages": []}, "ltt-3.8")
        assert "thinking" not in gui


def test_than_sach_di_qua_nguyen_ven():
    than = {"model": "ltt-3.8", "messages": [{"role": "user", "content": "a"}],
            "max_tokens": 10, "temperature": 0.5}
    gui, bo_qua = chuan_hoa_suy_nghi(than, "ltt-3.8")
    assert gui == than and bo_qua is False


# ══ Task 4 Step 2: effort theo model ═════════════════════════════════════════

@pytest.mark.parametrize("muc", ["low", "medium", "high", "xhigh", "minimal", "max"])
def test_35_nhan_effort_nhung_go_truoc_may_B(muc):
    for than in ({"model": "ltt-3.5", "reasoning_effort": muc},
                 {"model": "ltt-3.5", "reasoning": {"effort": muc}},
                 {"model": "ltt-3.5",
                  "chat_template_kwargs": {"reasoning_effort": muc}}):
        gui, bo_qua = chuan_hoa_suy_nghi(than, "ltt-3.5")
        assert bo_qua is True, than
        assert "reasoning_effort" not in gui
        assert "effort" not in (gui.get("reasoning") or {})
        assert "reasoning_effort" not in (gui.get("chat_template_kwargs") or {})


def test_35_reasoning_giu_khoa_khac_ngoai_effort():
    gui, bo_qua = chuan_hoa_suy_nghi(
        {"model": "ltt-3.5", "reasoning": {"effort": "high", "summary": "auto"}},
        "ltt-3.5")
    assert bo_qua and gui["reasoning"] == {"summary": "auto"}


def test_35_khong_gui_effort_thi_khong_bao_bo_qua():
    _gui, bo_qua = chuan_hoa_suy_nghi({"model": "ltt-3.5", "messages": []},
                                      "ltt-3.5")
    assert bo_qua is False


@pytest.mark.parametrize("vao,ra", [("low", "low"), ("medium", "medium"),
                                    ("xhigh", "xhigh"), ("high", "xhigh"),
                                    ("max", "xhigh"), ("minimal", "low"),
                                    ("HIGH", "xhigh")])
def test_38_chuan_hoa_effort(vao, ra):
    gui, bo_qua = chuan_hoa_suy_nghi({"model": "ltt-3.8", "reasoning_effort": vao},
                                     "ltt-3.8")
    assert gui["reasoning_effort"] == ra and bo_qua is False
    gui, _ = chuan_hoa_suy_nghi({"model": "ltt-3.8", "reasoning": {"effort": vao}},
                                "ltt-3.8")
    assert gui["reasoning"] == {"effort": ra}
    gui, _ = chuan_hoa_suy_nghi(
        {"model": "ltt-3.8", "chat_template_kwargs": {"reasoning_effort": vao}},
        "ltt-3.8")
    assert gui["chat_template_kwargs"] == {"reasoning_effort": ra}


@pytest.mark.parametrize("model", ["ltt-3.8", "ltt-3.5"])
@pytest.mark.parametrize("muc", ["none", "off", "NONE"])
def test_tat_suy_nghi_bi_tu_choi_o_moi_dang(model, muc):
    for than in ({"reasoning_effort": muc}, {"reasoning": {"effort": muc}},
                 {"chat_template_kwargs": {"reasoning_effort": muc}}):
        with pytest.raises(ThamSoSai):
            chuan_hoa_suy_nghi({"model": model, **than}, model)


@pytest.mark.parametrize("model", ["ltt-3.8", "ltt-3.5"])
def test_effort_la_bi_tu_choi(model):
    with pytest.raises(ThamSoSai):
        chuan_hoa_suy_nghi({"reasoning_effort": "sieu-cao"}, model)


# ── Ba cua that: than ma may A gui len may B ─────────────────────────────────

@pytest.fixture()
def db_s(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "s.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from tests.conftest import mo_cu_tru_3090
    mo_cu_tru_3090()
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def _nguoi(db) -> str:
    import uuid

    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    u = tao_nguoi_dung(db, email=f"sn-{uuid.uuid4().hex[:8]}@example.com",
                       password="a-good-password-12")
    db.flush()
    credit.cap_tay(db, u.id, 100_000, by="test")
    db.commit()
    return u.id


@pytest.mark.parametrize("duong,dung", [("/v1/messages", _than_messages),
                                        ("/v1/responses", _than_responses)])
@pytest.mark.parametrize("model", ["ltt-3.8", "ltt-3.5"])
def test_cua_stream_tien_kiem_va_chuan_bi_gui_than_sach(db_s, duong, dung, model):
    uid = _nguoi(db_s)
    than = dung(model, reasoning_effort="high")
    tk = luong.tien_kiem(db_s, user_id=uid, tool_name="text.chat", than=than,
                         duong=duong)
    _sach_ghi_de(_bo_budget_may_chu(tk.than_gui, duong) if model == "ltt-3.5"
                 else tk.than_gui)
    if model == "ltt-3.5":
        assert "reasoning_effort" not in tk.than_gui and tk.effort_bo_qua is True
    else:
        assert tk.than_gui["reasoning_effort"] == "xhigh"
        assert tk.effort_bo_qua is False
    cb = luong.chuan_bi(db_s, user_id=uid, tool_name="text.chat", than=than,
                        duong=duong)
    try:
        _sach_ghi_de(_bo_budget_may_chu(cb.than_gui, duong) if model == "ltt-3.5"
                     else cb.than_gui)
        assert (("reasoning_effort" in cb.than_gui) == (model == "ltt-3.8"))
    finally:
        luong.hoan(cb.user_id, cb.request_id)
        luong._nha_suat(cb.lease_id)


@pytest.mark.parametrize("model", ["ltt-3.8", "ltt-3.5"])
def test_cua_stream_none_la_400_truoc_may_B(db_s, model):
    uid = _nguoi(db_s)
    for than in (_than_messages(model, reasoning_effort="none"),
                 _than_responses(model, reasoning={"effort": "none"})):
        with pytest.raises(luong.ThamSoSai):
            luong.tien_kiem(db_s, user_id=uid, tool_name="text.chat", than=than,
                            duong="/v1/responses")


def test_cua_dong_bo_chat_completions_dung_chung_ham():
    """`/chat/completions` (và cửa job, và `/messages` không stream) đi qua
    `features.kiem_tham_so` — nó phải gọi CÙNG hàm, không một bản sao."""
    from apps.ltt_llm.features import ThamSoSai as TSS
    from apps.ltt_llm.features import kiem_tham_so

    sach = kiem_tham_so(_than_chat("ltt-3.8", reasoning_effort="high"))
    _sach_ghi_de(sach)
    assert sach["reasoning_effort"] == "xhigh"
    sach = kiem_tham_so(_than_chat("ltt-3.5", reasoning_effort="xhigh"))
    _sach_ghi_de(sach)
    assert "reasoning_effort" not in sach
    for model in ("ltt-3.8", "ltt-3.5"):
        with pytest.raises(TSS):
            kiem_tham_so(_than_chat(model, reasoning_effort="none"))


# ── HTTP: header bo qua, va than len may B o cua stream ─────────────────────

from tests.test_272_cua_streaming import (_account, _dat_luong, _h,  # noqa: E402
                                          api)
from server.api.inventory import API_V1_PREFIX  # noqa: E402

_ = api  # fixture


@pytest.mark.parametrize("duong,dung", [("/messages", _than_messages),
                                        ("/responses", _than_responses)])
def test_http_35_effort_bo_qua_co_header_va_than_sach(api, monkeypatch, duong, dung):
    da_goi = _dat_luong(monkeypatch)
    _uid, token = _account()
    r = api.post(API_V1_PREFIX + duong, headers=_h(token),
                 json=dung("ltt-3.5", reasoning_effort="xhigh"))
    assert r.status_code == 200, r.text
    assert r.headers.get("X-LTT-Effort-Bo-Qua") == "1"
    assert da_goi, "khong goi may B"
    _sach_ghi_de(_bo_budget_may_chu(da_goi[-1]["than"], da_goi[-1]["duong"]))
    assert "reasoning_effort" not in da_goi[-1]["than"]


def test_http_38_khong_co_header_bo_qua(api, monkeypatch):
    da_goi = _dat_luong(monkeypatch)
    _uid, token = _account()
    r = api.post(API_V1_PREFIX + "/messages", headers=_h(token),
                 json=_than_messages("ltt-3.8", reasoning_effort="high"))
    assert r.status_code == 200, r.text
    assert "X-LTT-Effort-Bo-Qua" not in r.headers
    assert da_goi[-1]["than"]["reasoning_effort"] == "xhigh"


@pytest.mark.parametrize("duong", ["/messages", "/responses"])
def test_http_none_la_400(api, monkeypatch, duong):
    _dat_luong(monkeypatch)
    _uid, token = _account()
    than = (_than_messages if duong == "/messages" else _than_responses)(
        "ltt-3.8", reasoning_effort="none")
    r = api.post(API_V1_PREFIX + duong, headers=_h(token), json=than)
    assert r.status_code == 400, r.text


# ══ Task 4 Step 3: san max_tokens 3.5 >= budget suy nghi + 512 ═══════════════

def _budget_yaml(model_id: str) -> int:
    from llm_gateway import vat_ly as VL
    vl = VL.doc_van_ban(YAML_KHO.read_text(encoding="utf-8"))
    b = vl[model_id].reasoning_budget
    assert b and b > 0, f"llama-swap.yaml khong khai --reasoning-budget cho {model_id}"
    return int(b)


@pytest.mark.parametrize("muc", [None, "low", "medium", "xhigh"])
def test_san_35_du_cho_budget_suy_nghi_cong_tra_loi(muc):
    from apps.ltt_llm.ngan_sach import san_token_ra
    assert san_token_ra("ltt-3.5", muc) >= _budget_yaml("qwen35-api") + 512


def test_khong_con_none_trong_bang_san_va_manifest():
    from apps.ltt_llm import manifest, ngan_sach
    assert "none" not in ngan_sach._SAN_NHE
    for bang in ngan_sach.SAN_TOKEN_RA_THEO_NGHI.values():
        assert "none" not in bang
    tool = manifest.MANIFEST.tools[0]
    assert "none" not in tool.api_contract["enums"]["reasoning_effort"]


# ══ Task 3: catalog /v1/models theo tung model ═══════════════════════════════

def _mau(ten: str):
    return types.SimpleNamespace(name=ten, description=ten,
                                 constraints={"context_window": 100_000,
                                              "max_output_tokens": 32_768,
                                              "reads_images": True})


def test_catalog_38_xhigh_mac_dinh_ba_muc():
    from server.api.tools import _dang_codex
    d = _dang_codex(_mau("ltt-3.8"))
    assert d["default_reasoning_level"] == "xhigh"
    assert [m["effort"] for m in d["supported_reasoning_levels"]] == [
        "low", "medium", "xhigh"]


def test_catalog_35_mot_muc_co_dinh():
    from server.api.tools import _dang_codex
    d = _dang_codex(_mau("ltt-3.5"))
    assert d["default_reasoning_level"] == "medium"
    assert [m["effort"] for m in d["supported_reasoning_levels"]] == ["medium"]


def test_catalog_doc_tu_examples_khong_go_cung():
    import server.api.tools as T
    from platform_core.public_api import examples as E
    assert not hasattr(T, "_MUC_SUY_LUAN"), "muc suy nghi go cung van con"
    for slug, muc in E.CODEX_MODEL_REASONING_LEVELS.items():
        d = T._dang_codex(_mau(slug))
        assert [m["effort"] for m in d["supported_reasoning_levels"]] == list(muc)
        assert d["default_reasoning_level"] == E.CODEX_MODEL_REASONING[slug]
        assert d["supported_reasoning_levels"] == E.muc_suy_nghi(slug)


def test_catalog_va_ham_chuan_hoa_noi_cung_mot_dieu():
    """Mỗi mức catalog khai phải đi qua `chuan_hoa_suy_nghi` nguyên vẹn (3.8),
    hoặc bị bỏ qua CÔNG KHAI (3.5) — không mức nào catalog khai lại bị 400."""
    from platform_core.public_api import examples as E
    for slug, muc in E.CODEX_MODEL_REASONING_LEVELS.items():
        for m in muc:
            gui, bo_qua = chuan_hoa_suy_nghi({"reasoning_effort": m}, slug)
            if slug in E.CODEX_MODEL_REASONING_CO_DINH:
                assert bo_qua and "reasoning_effort" not in gui
            else:
                assert gui["reasoning_effort"] == m and not bo_qua


# ══ Cửa ĐỒNG BỘ /chat/completions: budget suy nghĩ do máy chủ đặt theo cửa ══
#
# Coordinator 18/09 bác "3.5 ở cửa đồng bộ ⇒ 400" (phá khách đang dùng). Thay
# bằng: máy chủ tự đặt `reasoning_budget_tokens` (llama.cpp 91f6a6cf3
# server-common.cpp:1366-1369 nhận nó MỖI request) sao cho còn chỗ trả lời
# trong `max_tokens` của cửa đồng bộ. Budget KHÁCH gửi vẫn bị gỡ.

def _dat_dieu_phoi(monkeypatch, noi_dung="chao ban"):
    """Giả `dieu_phoi.goi` — tầng NGAY TRƯỚC thân gửi máy B (`them` đi thẳng
    vào thân). Trả nội dung khác rỗng như một lượt suy nghĩ không cạn trần."""
    from platform_core.llm import dieu_phoi
    from platform_core.llm.cong_vlm import KetQuaChat, SuDung
    goi = []

    def gia(db, **kw):
        goi.append(kw)
        return types.SimpleNamespace(
            noi_dung=noi_dung, suy_nghi="nghi", tool_calls=(),
            finish_reason="stop", su_dung=SuDung(10, 20, 0, True),
            ket_qua=KetQuaChat(noi_dung=noi_dung))

    monkeypatch.setattr(dieu_phoi, "goi", gia)
    return goi


def _h_dong_bo(token):
    import uuid
    return {**_h(token), "Idempotency-Key": uuid.uuid4().hex}


def _than_dong_bo(model: str, **them) -> dict:
    d = {"model": model, "messages": [{"role": "user", "content": "xin chao"}]}
    d.update(them)
    return d


@pytest.mark.parametrize("max_tokens", [None, 1024, 2000])
def test_dong_bo_35_tra_200_va_may_chu_dat_budget(api, monkeypatch, max_tokens):
    from apps.ltt_llm.ngan_sach import TOKEN_CHO_TRA_LOI
    goi = _dat_dieu_phoi(monkeypatch)
    _uid, token = _account()
    than = _than_dong_bo("ltt-3.5", reasoning_effort="high",
                         reasoning_budget_tokens=99_999,
                         thinking={"type": "enabled", "budget_tokens": 50_000})
    if max_tokens is not None:
        than["max_tokens"] = max_tokens
    r = api.post(API_V1_PREFIX + "/chat/completions", headers=_h_dong_bo(token), json=than)
    assert r.status_code == 200, r.text
    assert r.json()["choices"][0]["message"]["content"] == "chao ban"
    assert r.headers.get("X-LTT-Effort-Bo-Qua") == "1"
    assert goi, "khong goi may B"
    kw = goi[-1]
    them_b = kw.get("them") or {}
    budget = them_b.get("reasoning_budget_tokens")
    assert budget is not None, f"may chu khong dat budget: {them_b}"
    # budget của MÁY CHỦ, không phải của khách; chừa chỗ trả lời; ≤ budget engine
    assert budget != 99_999 and budget <= _budget_yaml("qwen35-api")
    assert budget + TOKEN_CHO_TRA_LOI <= kw["max_tokens"]
    assert budget > 0
    assert "thinking" not in them_b and kw.get("reasoning_effort") is None


def test_dong_bo_38_khong_dat_budget_va_khong_header(api, monkeypatch):
    goi = _dat_dieu_phoi(monkeypatch)
    _uid, token = _account()
    r = api.post(API_V1_PREFIX + "/chat/completions", headers=_h_dong_bo(token),
                 json=_than_dong_bo("ltt-3.8", reasoning_effort="high",
                                    max_tokens=500, reasoning_budget_tokens=7))
    assert r.status_code == 200, r.text
    assert "X-LTT-Effort-Bo-Qua" not in r.headers
    them_b = goi[-1].get("them") or {}
    assert "reasoning_budget_tokens" not in them_b, them_b
    assert goi[-1]["reasoning_effort"] == "xhigh"


# ══ Sự cố 18/09 22:45: 3.5 trả 200 RỖNG ở cửa KHÁC `/chat/completions` ════════
#
# Đo production `/api/v1/messages` không stream, 3.5, `max_tokens=1500`: 2/5 lượt
# `stop_reason=max_tokens`, `output_tokens=1500`, không chữ nào. Gốc: chỉ
# `server/api/chat.py` truyền budget máy chủ; `_mot_cuc`, cửa job và cửa stream
# không ⇒ engine dùng `--reasoning-budget` 2.048 > `max_tokens`. Đo trực tiếp
# engine B (n=10, 1500): không budget 5/10 rỗng; `reasoning_budget_tokens=988`
# 0/10 rỗng, suy nghĩ ≤ 987 token.

@pytest.mark.parametrize("duong,dung", [("/messages", _than_messages),
                                        ("/responses", _than_responses)])
def test_mot_cuc_35_may_chu_dat_budget(api, monkeypatch, duong, dung):
    from apps.ltt_llm.ngan_sach import TOKEN_CHO_TRA_LOI
    goi = _dat_dieu_phoi(monkeypatch)
    _uid, token = _account()
    than = dung("ltt-3.5", stream=False)
    than["max_output_tokens" if duong == "/responses" else "max_tokens"] = 1500
    r = api.post(API_V1_PREFIX + duong, headers=_h(token), json=than)
    assert r.status_code == 200, r.text
    assert goi, "khong goi may B"
    kw = goi[-1]
    budget = (kw.get("them") or {}).get("reasoning_budget_tokens")
    assert budget == 1500 - TOKEN_CHO_TRA_LOI, kw.get("them")
    assert budget + TOKEN_CHO_TRA_LOI <= kw["max_tokens"]


def test_mot_cuc_38_khong_dat_budget(api, monkeypatch):
    goi = _dat_dieu_phoi(monkeypatch)
    _uid, token = _account()
    than = _than_messages("ltt-3.8", stream=False)
    than["max_tokens"] = 1500
    r = api.post(API_V1_PREFIX + "/messages", headers=_h(token), json=than)
    assert r.status_code == 200, r.text
    assert "reasoning_budget_tokens" not in (goi[-1].get("them") or {})


@pytest.mark.parametrize("max_tokens,mong", [(1500, 988), (600, 88), (400, 0),
                                             (32_768, 2048)])
def test_features_chay_35_tu_dat_budget_khi_ben_goi_khong_truyen(monkeypatch,
                                                                 max_tokens, mong):
    """Cửa job và `_mot_cuc` gọi `features.chay` không truyền budget."""
    from apps.ltt_llm import features
    goi = _dat_dieu_phoi(monkeypatch)
    features.chay(None, {"model": "ltt-3.5", "max_tokens": max_tokens,
                         "messages": [{"role": "user", "content": "xin chao"}]})
    assert goi[-1]["them"].get("reasoning_budget_tokens") == mong


def test_features_chay_38_khong_dat_budget(monkeypatch):
    from apps.ltt_llm import features
    goi = _dat_dieu_phoi(monkeypatch)
    features.chay(None, {"model": "ltt-3.8", "max_tokens": 1500,
                         "messages": [{"role": "user", "content": "xin chao"}]})
    assert "reasoning_budget_tokens" not in (goi[-1].get("them") or {})


@pytest.mark.parametrize("duong,dung", [("/v1/messages", _than_messages),
                                        ("/v1/responses", _than_responses)])
@pytest.mark.parametrize("model", ["ltt-3.8", "ltt-3.5"])
def test_cua_stream_35_budget_dung_truong_cua_llama(db_s, duong, dung, model):
    """`/v1/messages` của llama.cpp VỨT `reasoning_budget_tokens` cấp cao nhất
    (`server_chat_convert_anthropic_to_oai` chỉ dịch `thinking.budget_tokens`);
    `/v1/responses` chép nguyên thân. Sai trường = budget im lặng về 2.048."""
    uid = _nguoi(db_s)
    than = dung(model)
    than.pop("max_tokens", None)
    than.pop("max_output_tokens", None)
    than["max_output_tokens" if duong.endswith("/responses") else "max_tokens"] = 1500
    tk = luong.tien_kiem(db_s, user_id=uid, tool_name="text.chat", than=than,
                         duong=duong)
    cb = luong.chuan_bi(db_s, user_id=uid, tool_name="text.chat", than=than,
                        duong=duong)
    try:
        for gui in (tk.than_gui, cb.than_gui):
            if model == "ltt-3.5":
                _sach_ghi_de(_bo_budget_may_chu(gui, duong, max_ra=1500))
            else:
                _sach_ghi_de(gui)
    finally:
        luong.hoan(cb.user_id, cb.request_id)
        luong._nha_suat(cb.lease_id)
