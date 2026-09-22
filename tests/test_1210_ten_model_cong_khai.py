"""Đúng HAI tên model công khai, tên cũ đã cắt (D02, dual-model 2.3).

Ba lớp, và mỗi lớp trả lời một câu khác nhau:

**A. Bản khai** — `/api/v1/models` nói đúng `{"ltt-3.8", "ltt-3.5"}`, và không
tên công khai nào trùng **id nội bộ** hay **slug app**. Đó là cả nội dung của
D02: trước 11/09 bí danh là `ltt_llm`, trùng hệt slug, nên "lớp đệm alias" chỉ
tồn tại trên giấy — ngày ta muốn đổi model bên dưới thì tên khách đã ghim là tên
của *ứng dụng*, không phải của *model*.

**B. Bốn cửa** — sync / một-cục / stream / job đều từ chối tên cũ, và **cùng một
mã lỗi** `model_not_found`. Một cửa nói `invalid_request` còn cửa kia nói
`model_not_found` cho cùng một sự thật là bắt khách đoán xem tên của họ sai
chính tả hay đã bị gỡ.

**C. Hai cột admission ghi lúc nộp** (Ruling R20) — đây là nửa dễ quên nhất của
2.3 và nó **không nhìn thấy được từ cửa**: `jobs.claim` + `job_scheduler` gác
hàng đợi bằng `Job.admission_resource`/`admission_slots`, hai cột CSDL ghi lúc
**nộp**. Ngày manifest chuyển sang `admission_theo_model`, bộ ba tĩnh thành rỗng
và hai cột ấy im lặng mang `slots=0` — lease vẫn chặn nên **không** chạy quá
suất, nhưng hàng đợi nhặt-rồi-trả, fairness và scheduler envelope hỏng, và
`job_runner` dán nhãn `resource_wait` bằng tên tài nguyên cũ.

Dải test của chương trình: 1200-1249 (Task 1.2).
"""
from __future__ import annotations

import ast
import dataclasses
import json
import pathlib
import uuid

import pytest

_GOC = pathlib.Path(__file__).resolve().parents[1]

#: Đúng hai, đúng thứ tự khai (mặc định đứng trước).
TEN_MOI = ("ltt-3.8", "ltt-3.5")

#: Đã cắt. `ltt-llm-claude-compat` **không** nằm ở đây có chủ ý: nó là *tên
#: tuyến của giao thức* cho Claude Desktop (`streaming.TUYEN_TUONG_THICH`),
#: không phải bí danh sản phẩm — `test_290` giữ đúng ranh giới ấy.
TEN_CU = ("ltt_llm", "ltt_llm_vision", "qwen38-vision")

#: Slug của app sở hữu `text.chat`. Tên công khai **không được** trùng nó.
SLUG_APP = "ltt_llm"


def _tool_chat():
    from apps.ltt_llm.manifest import MANIFEST
    return next(t for t in MANIFEST.tools if t.name == "text.chat")


# ── A. Bản khai: đúng hai tên, và chúng là BÍ DANH thật ──────────────────────

def _bat_bien_hai_ten(tool, slug: str = SLUG_APP) -> None:
    """Bất biến D02 trên MỘT `ToolSpec`. Ném `AssertionError` nếu vi phạm.

    ⭐ VIẾT THÀNH HÀM ĐỂ CÓ ĐỐI CHỨNG. Phép kiểm thật gọi nó với bản khai thật;
       phép đối chứng gọi nó với một bản khai **đã bỏ một tên** và đòi nó ĐỎ.
       Không có đối chứng thì một bất biến chỉ chứng minh rằng nó chạy xong.
    """
    khai = tool.api_contract.get("models") or {}
    assert set(khai) == set(TEN_MOI), (
        f"api_contract.models = {sorted(khai)}, phai dung {sorted(TEN_MOI)}")

    gia_tri = list(tool.params_schema["model"]["values"])
    assert gia_tri == list(TEN_MOI), f"params_schema.model.values = {gia_tri}"
    assert tool.params_schema["model"]["default"] == TEN_MOI[0]

    enums = list(tool.api_contract["enums"]["model"])
    assert enums == list(TEN_MOI), f"api_contract.enums.model = {enums}"

    assert set(tool.admission_theo_model) == set(TEN_MOI), (
        f"admission_theo_model = {sorted(tool.admission_theo_model)} — mot ten "
        f"cong khai khong co suc chua la mot ten se nem KeyError o moi cua")

    for ten, spec in khai.items():
        assert ten not in TEN_CU, f"{ten!r} la ten DA CAT"
        assert ten != slug, (
            f"bi danh {ten!r} trung het slug app — do la khuyet tat D02 sinh ra "
            f"de dep, khong phai mot cach viet gon")
        assert spec["id"] != ten, (
            f"{ten!r} trung het id noi bo: lop dem bien mat")
        assert spec["id"] not in TEN_CU, f"{ten!r} van tro ve id da cat"


def test_bản_khai_dung_hai_ten_cong_khai():
    _bat_bien_hai_ten(_tool_chat())


@pytest.mark.parametrize("bo_ten", TEN_MOI)
def test_doi_chung_bo_mot_ten_khoi_manifest_thi_DO(bo_ten):
    """⭐ ĐỐI CHỨNG mà plan đòi: bỏ một tên khỏi bản khai ⇒ phép kiểm phải ĐỎ."""
    tool = _tool_chat()
    khai = {k: v for k, v in tool.api_contract["models"].items() if k != bo_ten}
    hop_dong = dict(tool.api_contract)
    hop_dong["models"] = khai
    hop_dong["enums"] = {**tool.api_contract["enums"],
                         "model": [t for t in TEN_MOI if t != bo_ten]}
    schema = {**tool.params_schema,
              "model": {**tool.params_schema["model"],
                        "values": [t for t in TEN_MOI if t != bo_ten]}}
    lech = dataclasses.replace(tool, api_contract=hop_dong, params_schema=schema)
    with pytest.raises(AssertionError):
        _bat_bien_hai_ten(lech)


def test_doi_chung_bi_danh_trung_slug_app_thi_DO():
    """Khuôn hỏng **cũ** tiêm lại: bí danh = slug app ⇒ phải ĐỎ.

    Đây là đối chứng cho đúng lỗi 2.3 sửa, chứ không chỉ cho việc đếm hai tên.
    """
    tool = _tool_chat()
    spec = dict(tool.api_contract["models"]["ltt-3.8"])
    hop_dong = {**tool.api_contract, "models": {SLUG_APP: spec,
                                                "ltt-3.5": tool.api_contract["models"]["ltt-3.5"]}}
    with pytest.raises(AssertionError):
        _bat_bien_hai_ten(dataclasses.replace(tool, api_contract=hop_dong))


def test_lop_dem_bi_danh_va_manifest_noi_cung_mot_dieu():
    """`canonical.ALIAS_SANG_ID` và `api_contract.models` là MỘT bảng, hai chỗ đọc."""
    from platform_core.llm import canonical as C

    assert tuple(C.ALIAS_SANG_ID) == TEN_MOI
    assert C.MODEL_MAC_DINH == TEN_MOI[0]
    theo_manifest = {ten: spec["id"]
                     for ten, spec in _tool_chat().api_contract["models"].items()}
    assert theo_manifest == C.ALIAS_SANG_ID, (
        "manifest va canonical dang giu HAI bang bi danh khac nhau")


@pytest.mark.parametrize("cu", TEN_CU)
def test_ten_cu_khong_con_la_mot_model(cu):
    from platform_core.llm import canonical as C

    assert cu not in C.ALIAS_SANG_ID
    assert cu not in C.MODEL_HOP_LE
    with pytest.raises(KeyError):
        C.ban_do_model(cu)


def test_provider_khai_dung_nhung_id_ma_bi_danh_tro_toi():
    """Đối chiếu với `providers`, không gõ lại id — và `qwen38-vision` đã gỡ."""
    from platform_core import providers
    from platform_core.llm import canonical as C

    co_that = {m.id for m in providers.REGISTRY[C.THU_TU_PROVIDER[0]].models}
    assert set(C.ALIAS_SANG_ID.values()) <= co_that, (
        f"bi danh tro toi id provider khong khai: "
        f"{sorted(set(C.ALIAS_SANG_ID.values()) - co_that)}")
    assert "qwen38-vision" not in co_that, "ho so vision le ra da bi go (D02)"


def test_bo_cai_client_va_vi_du_deu_dung_ten_moi():
    """Bộ cài ghi tên model vào cấu hình của KHÁCH — một tên chết ở đó là một
    client hỏng ngay lần chạy sau, và chẳng phép kiểm cửa nào nhìn thấy."""
    from platform_core.public_api import examples

    assert examples.CHAT_MODEL in TEN_MOI
    assert examples.CLI_MODEL in TEN_MOI

    import server.api.streaming as st
    assert set(st.TUYEN_TUONG_THICH.values()) <= set(TEN_MOI), (
        "tuyen tuong thich cua Claude Desktop dang tro ve mot ten da cat")


# ── B. Bốn cửa từ chối tên cũ, CÙNG một mã lỗi ───────────────────────────────

def _moi_truong_cua(tmp_path, monkeypatch, *, structured=False):
    """App thật + khoá API thật trên SQLite sạch. Khuôn của `test_1209`."""
    from platform_core.public_api import keys as devkeys, limits
    from platform_core.public_api.scopes import (SCOPE_JOBS_CREATE,
                                                 SCOPE_JOBS_READ,
                                                 SCOPE_TOOLS_READ)

    pepper = "ten-test-pepper-" + "e" * 40
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "ten.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, pepper)
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(
            db, email="ten-" + uuid.uuid4().hex[:8] + "@example.com",
            password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, 10_000, by="test")
        _k, token = devkeys.issue(
            db, user_id=user.id,
            scopes=(SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ),
            env={devkeys.PEPPER_ENV: pepper})
        db.commit()
        uid = user.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "ten-secret-value-here",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "text.chat",
        "LTT_PUBLIC_API_RPM": "600",
        "LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS": "1" if structured else "0",
    })
    return app, token, uid


@pytest.fixture()
def cua(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from platform_core.public_api import limits

    app, token, uid = _moi_truong_cua(tmp_path, monkeypatch)
    try:
        with TestClient(app, base_url="https://testserver",
                        raise_server_exceptions=False) as client:
            yield client, token, uid
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        limits.reset()
        import platform_core.db as dbmod
        dbmod.reset_engine()


@pytest.fixture()
def cua_structured(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from platform_core.public_api import limits

    app, token, uid = _moi_truong_cua(
        tmp_path, monkeypatch, structured=True
    )
    try:
        with TestClient(app, base_url="https://testserver",
                        raise_server_exceptions=False) as client:
            yield client, token, uid
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        limits.reset()
        import platform_core.db as dbmod
        dbmod.reset_engine()


def _h(token, idem=True):
    h = {"Authorization": "Bearer " + token}
    if idem:
        h["Idempotency-Key"] = uuid.uuid4().hex
    return h


@pytest.mark.parametrize(
    "duong,than,protocol_code",
    (
        (
            "/chat/completions",
            {"model": "khong-co", "max_tokens": 1,
             "messages": [{"role": "user", "content": "?"}]},
            "model_not_found",
        ),
        (
            "/messages",
            {"model": "khong-co", "max_tokens": 1, "stream": True,
             "messages": [{"role": "user", "content": "?"}]},
            "not_found_error",
        ),
        (
            "/responses",
            {"model": "khong-co", "max_output_tokens": 1, "stream": True,
             "input": [{"role": "user", "content": "?"}]},
            "model_not_found",
        ),
    ),
)
def test_co_structured_ten_model_sai_giu_nghia_o_ba_giao_thuc(
    cua_structured, duong, than, protocol_code
):
    from server.api.inventory import API_V1_PREFIX

    client, token, _uid = cua_structured
    response = client.post(
        API_V1_PREFIX + duong,
        headers=_h(token, idem=duong == "/chat/completions"),
        json=than,
    )

    assert response.status_code == 404, response.text
    body = response.json()
    if duong == "/messages":
        extension = body["error"]["ltt_error"]
        assert body["error"]["type"] == protocol_code
    elif duong == "/responses":
        extension = body["response"]["error"]["ltt_error"]
        assert body["response"]["error"]["code"] == protocol_code
    else:
        extension = body["error"]["ltt_error"]
        assert body["error"]["code"] == protocol_code
    assert extension["canonical_code"] == "model_not_found"
    assert extension["protocol_code"] == protocol_code
    assert extension["request_id"]


def test_danh_muc_cong_khai_liet_ke_dung_hai_ten(cua):
    from server.api.inventory import API_V1_PREFIX

    client, token, _uid = cua
    body = client.get(API_V1_PREFIX + "/models", headers=_h(token, idem=False))
    assert body.status_code == 200, body.text
    ten = {row["name"] for row in body.json()["items"]}
    assert ten == set(TEN_MOI), f"/api/v1/models liet ke {sorted(ten)}"


@pytest.mark.parametrize("cu", ("ltt_llm", "ltt_llm_vision"))
def test_cua_dong_bo_tu_choi_ten_cu_bang_model_not_found(cua, cu):
    from server.api.inventory import API_V1_PREFIX

    client, token, _uid = cua
    r = client.post(API_V1_PREFIX + "/chat/completions", headers=_h(token),
                    json={"model": cu, "max_tokens": 64,
                          "messages": [{"role": "user", "content": "xin chao"}]})
    assert r.status_code == 400, r.text
    assert r.json()["code"] == "model_not_found", r.text


@pytest.mark.parametrize("duong", ("/messages", "/responses"))
def test_cua_mot_cuc_va_stream_tu_choi_ten_cu_bang_model_not_found(cua, duong):
    """Một thân request, hai đường: `_cua` gác cả bản một-cục lẫn bản stream.

    Chốt `stream=True` ở đây có lý do: nếu tên model chỉ bị bắt SAU khi SSE đã
    mở thì khách nhận `200` rồi một sự kiện lỗi giữa luồng — Codex/Claude Code
    không đọc được cái đó thành "đổi tên model đi".
    """
    from server.api.inventory import API_V1_PREFIX

    client, token, _uid = cua
    than = {"model": "ltt_llm", "max_tokens": 64, "stream": True,
            "messages": [{"role": "user", "content": "xin chao"}]}
    if duong == "/responses":
        than = {"model": "ltt_llm", "max_output_tokens": 64, "stream": True,
                "input": [{"role": "user", "content": "xin chao"}]}
    r = client.post(API_V1_PREFIX + duong, headers=_h(token), json=than)
    assert r.status_code == 400, r.text
    assert r.json()["code"] == "model_not_found", r.text


def test_cua_job_tu_choi_ten_cu(cua):
    """Cửa bất đồng bộ cũng phải từ chối — TRƯỚC khi chạm sổ tiền."""
    from platform_core.models import Job
    from server.api.inventory import API_V1_PREFIX

    client, token, _uid = cua
    r = client.post(API_V1_PREFIX + "/jobs", headers=_h(token),
                    json={"tool": "text.chat",
                          "input": {"model": "ltt_llm",
                                    "messages": [{"role": "user",
                                                  "content": "xin chao"}]}})
    assert 400 <= r.status_code < 500, r.text

    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        assert db.query(Job).count() == 0, "mot ten da cat da tao duoc job"
    finally:
        db.close()


def test_ten_moi_khong_bi_chan_o_cua_dong_bo(cua):
    """⭐ ĐỐI CHỨNG CHO CHÍNH BỐN PHÉP KIỂM TRÊN.

    Một cửa từ chối **mọi** tên cũng làm chúng xanh. Nên phải đo rằng tên MỚI đi
    qua được chốt tên — nó sẽ hỏng ở chỗ khác (không có máy B trong test), miễn
    là **không** hỏng bằng `model_not_found`.
    """
    from server.api.inventory import API_V1_PREFIX

    client, token, _uid = cua
    r = client.post(API_V1_PREFIX + "/chat/completions", headers=_h(token),
                    json={"model": "ltt-3.8", "max_tokens": 64,
                          "messages": [{"role": "user", "content": "xin chao"}]})
    ma = r.json().get("code") if r.headers.get(
        "content-type", "").startswith("application/problem") else ""
    assert ma != "model_not_found", (
        "ten MOI cung bi chan — bon phep kiem tren dang do 'cua tu choi tat ca'")


# ── C. Hai cột admission ghi LÚC NỘP, theo model (Ruling R20) ────────────────

@pytest.fixture()
def db_nop(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "nop.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield
    dbmod.reset_engine()


def _nop_chat(model: str):
    """Nộp một job `text.chat` THẬT với `model` và trả `(tai_nguyen, so_suat)`."""
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.runtime_noi_bo import job as rjob
    from platform_core.users import tao_nguoi_dung

    gen = get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="n-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, u.id, 100_000, by="test")
        db.commit()

        bg = rjob.bao_gia("text.chat", {
            "model": model, "max_tokens": 64,
            "messages": [{"role": "user", "content": "xin chao"}]},
            db=db, user_id=u.id)
        j = rjob.nop_job(db, user_id=u.id, bao_gia=bg)
        db.commit()
        return (j.admission_resource, int(j.admission_slots))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_hai_cot_admission_mang_suc_chua_CUA_MODEL_da_nop(db_nop):
    """🔴 R20. Hai model ⇒ hai cặp (tài nguyên, suất) KHÁC NHAU trong hàng `jobs`.

    Sự tương phản **chính là** phép đo: một bản cài sai (đọc bộ ba tĩnh) cho hai
    lượt cùng `("", 0)`, nên chỉ kiểm một model sẽ xanh trên đúng bản hỏng ấy.
    """
    from apps.ltt_llm import ngan_sach

    ba_tam = _nop_chat("ltt-3.8")
    ba_nam = _nop_chat("ltt-3.5")

    assert ba_tam == (ngan_sach.TAI_NGUYEN_38,
                      ngan_sach.HO_SO["qwen38-api"].seq_cap), ba_tam
    assert ba_nam == (ngan_sach.TAI_NGUYEN_35,
                      ngan_sach.HO_SO["qwen35-api"].seq_cap), ba_nam
    assert ba_tam[0] != ba_nam[0], (
        "hai model dung CHUNG mot ten tai nguyen — hang doi dang gop hai card "
        "lam mot va khong ai thay")
    assert ba_tam[1] > 0 and ba_nam[1] > 0, (
        "slots=0 ⇒ `jobs.claim` coi job chat la 'khong dung tai nguyen chia se' "
        "va nhat tu do; day dung la khuyet tat R20 mo ta")


def test_tool_khong_khai_gi_van_giu_ban_chup_luc_nop():
    """App chụp tài nguyên **theo giai đoạn** (vd `auto_scan_video`) không đổi.

    `admission_luc_nop` chỉ thay câu trả lời khi tool CÓ khai; tool không khai gì
    vẫn nhận mặc định của bên gọi, `slots=0` — hành vi trước 2.3 nguyên vẹn.
    """
    from platform_core.registry import ToolSpec, admission_luc_nop

    tran = ToolSpec(name="t.x", job_type="t.x", description="d",
                    params_schema={}, returns={"y": "text"})
    assert admission_luc_nop(tran, {"model": "bat-ky"}, mac_dinh="api") == ("api", 0)


# ── D. Hai CHỖ NỘP không còn đọc bộ ba tĩnh của tool ─────────────────────────

_TEP_NOP = ("platform_core/runtime_noi_bo/job.py",
            "platform_core/public_api/invocation.py")

_TRUONG_CAM = frozenset({"admission_resource", "admission_slots",
                         "admission_token_pool"})


def _goc_ten(node) -> str:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else ""


def _vi_pham(duong_dan: pathlib.Path) -> list:
    """Chỗ đọc bộ ba tĩnh **trên một tool**. Bắt cả `tool.x` lẫn `getattr(tool,"x")`.

    Khuôn `getattr` là khuôn THẬT mà hai tệp này dùng trước 2.3 — một bộ dò chỉ
    nhìn `ast.Attribute` sẽ xanh ngay cả khi chưa ai sửa gì.
    """
    cay = ast.parse(duong_dan.read_text(encoding="utf-8"))
    thay = []
    for node in ast.walk(cay):
        if isinstance(node, ast.Attribute) and node.attr in _TRUONG_CAM:
            if _goc_ten(node.value) != "tool":
                continue
            thay.append((node.lineno, "tool." + node.attr))
        elif (isinstance(node, ast.Call)
              and isinstance(node.func, ast.Name) and node.func.id == "getattr"
              and len(node.args) >= 2
              and isinstance(node.args[1], ast.Constant)
              and node.args[1].value in _TRUONG_CAM
              and _goc_ten(node.args[0]) == "tool"):
            thay.append((node.lineno,
                         'getattr(tool, "' + str(node.args[1].value) + '")'))
    return thay


@pytest.mark.parametrize("ten_tep", _TEP_NOP)
def test_cho_nop_khong_con_doc_bo_ba_tinh(ten_tep):
    vi_pham = _vi_pham(_GOC / ten_tep)
    assert vi_pham == [], (
        ten_tep + " con ghi hai cot admission tu bo ba TINH cua tool: "
        + str(vi_pham))


def test_doi_chung_bo_do_bat_duoc_khuon_getattr(tmp_path):
    cu = tmp_path / "nop_cu.py"
    cu.write_text(
        "def f(tool, manifest):\n"
        '    a = getattr(tool, "admission_resource", "") or "api"\n'
        "    b = tool.admission_slots\n"
        "    return a, b\n", encoding="utf-8")
    assert [t[1] for t in _vi_pham(cu)] == [
        "tool.admission_slots", 'getattr(tool, "admission_resource")']


# ── E. Di trú dữ liệu: cái đang chạy được đổi, LỊCH SỬ thì không ─────────────

REV_CHA = "7c1e4b9a2d58"
REV = "b4d7f2c19e30"


def test_migration_noi_chuoi_va_mot_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config(str(_GOC / "alembic.ini")))
    # Đo "MỘT head" và "REV nằm trên đường tới head", KHÔNG đo "REV LÀ head":
    # bản đầu viết `get_heads() == [REV]` và nó đỏ ngay ở migration kế tiếp của
    # cùng chương trình (`gpu_residency`, 5.1) — đỏ vì một lý do không dính dáng
    # gì tới điều nó đo, là việc cắt tên model cũ có nối đúng chuỗi hay không.
    assert len(scripts.get_heads()) == 1, scripts.get_heads()
    assert scripts.get_revision(REV).down_revision == REV_CHA
    duong = {r.revision for r in scripts.walk_revisions("base", "heads")}
    assert REV in duong, "revision cat ten model khong nam tren duong toi head"


def _chen(conn, bang: str, **gia_tri) -> None:
    """`INSERT` một hàng, tự điền mọi cột `NOT NULL` không có mặc định.

    ⭐ Phản chiếu lược đồ thay vì gõ tay danh sách cột: bảng `jobs` có hơn ba
       mươi cột và phần lớn không liên quan gì tới phép kiểm này. Gõ tay là một
       phép kiểm sẽ đỏ mỗi lần ai đó thêm một cột — đỏ vì lý do không dính dáng
       tới điều nó đo.
    """
    import datetime as _dt

    from sqlalchemy import MetaData, Table

    md = MetaData()
    t = Table(bang, md, autoload_with=conn)
    hang = dict(gia_tri)
    for cot in t.columns:
        if cot.name in hang or cot.nullable:
            continue
        if cot.server_default is not None or cot.default is not None:
            continue
        kieu = str(cot.type).upper()
        if "DATETIME" in kieu or "TIMESTAMP" in kieu:
            hang[cot.name] = _dt.datetime(2026, 9, 11)
        elif "INT" in kieu or "BOOL" in kieu or "NUMERIC" in kieu:
            hang[cot.name] = 0
        else:
            hang[cot.name] = ""
    conn.execute(t.insert().values(**hang))


@pytest.mark.timeout(600)
def test_di_tru_doi_cai_dang_chay_va_KHONG_doi_lich_su(tmp_path, monkeypatch):
    """🔴 HAI NỬA, VÀ NỬA THỨ HAI MỚI LÀ NỬA DỄ LÀM HỎNG.

    Đổi hết mọi hàng mang tên cũ là một câu `UPDATE` ngắn hơn và **sai**: một
    dòng lịch sử nói *"lượt này chạy trên `ltt_llm`"* là sự thật của ngày ấy, và
    khách đối soát bằng đúng những dòng đó.

    Ranh giới: *hàng này còn được ĐỌC ĐỂ CHẠY nữa không?*
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    url = "sqlite:///" + (tmp_path / "mig.db").as_posix()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.chdir(_GOC)
    cfg = Config("alembic.ini")
    command.upgrade(cfg, REV_CHA)

    eng = create_engine(url)
    with eng.begin() as c:
        for ma, tt, model in (("j-queued", "queued", "ltt_llm"),
                              ("j-running", "running", "ltt_llm_vision"),
                              ("j-done", "done", "ltt_llm")):
            _chen(c, "jobs", id=ma, user_id="u1", app_slug="ltt_llm",
                  job_type="ltt_llm.chat", status=tt, dedupe_key=ma,
                  admission_resource="llm_remote", admission_slots=1,
                  params={"model": model, "messages": []})
        _chen(c, "chatltt_conversation", id="cv1", user_id="u1", title="t",
              model_alias="ltt_llm")
        for ma, tt in (("m-dang-chay", "streaming"), ("m-xong", "done")):
            _chen(c, "chatltt_message", id=ma, conversation_id="cv1",
                  user_id="u1", role="assistant", blocks="[]", status=tt,
                  model_alias="ltt_llm")

    command.upgrade(cfg, REV)

    with eng.begin() as c:
        params = dict(c.execute(text("SELECT id, params FROM jobs")).fetchall())
        doc = {k: json.loads(v)["model"] for k, v in params.items()}
        assert doc["j-queued"] == "ltt-3.8"
        assert doc["j-running"] == "ltt-3.8", (
            "`ltt_llm_vision` phai ve `ltt-3.8` — `ltt-3.5` la model KHAC, "
            "card khac, bang gia khac")
        assert doc["j-done"] == "ltt_llm", "job DA XONG la lich su, dung viet lai"

        assert c.execute(text(
            "SELECT model_alias FROM chatltt_conversation WHERE id='cv1'"
        )).scalar() == "ltt-3.8"
        tin = dict(c.execute(text(
            "SELECT id, model_alias FROM chatltt_message")).fetchall())
        assert tin["m-dang-chay"] == "ltt-3.8"
        assert tin["m-xong"] == "ltt_llm", (
            "message DA XONG ghi model NAO DA TRA LOI — do la lich su")
