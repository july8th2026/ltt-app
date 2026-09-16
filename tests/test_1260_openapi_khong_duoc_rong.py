"""test_1260 — spec MAY DOC phai noi dung nhung gi hop dong noi.

## 🔴 Do duoc 14/09/2026

`GET /api/v1/openapi.json`, cua `/chat/completions`:

    requestBody -> {"type": "object", "additionalProperties": true}

Khong mot chu nao ve `model`, `messages`, `max_tokens`, `reasoning_effort`, hay
sau tham so mo cung ngay. Ai tro mot bo sinh client vao spec ay se nhan mot
client chi biet `dict`.

Va ta **quang cao** no: `DEVELOPER_GUIDE.md` ghi *"Spec may doc:
GET /api/v1/openapi.json"*.

⛔ Hai be mat cua CUNG MOT hop dong, mot ben day du (tai lieu nguoi doc, sinh tu
   `params_schema`) va mot ben RONG. Ben rong lai la ben may doc.

## Nguyen nhan va cach sua — mot nguon, khong khai lai

Chu ky handler la `body: dict = Body(...)`, nen FastAPI khong co gi de suy ra.
Catalog thi DA dung san `ToolSpec.input_schema` tu `params_schema`. Ban va chi
noi mot nguon da co vao mot be mat dang rong (`openapi_extra`).

⛔ KHONG doi chu ky handler sang model Pydantic: lam the la khai hop dong o HAI
   noi, va ngay chung lech nhau la ngay spec noi doi. Cung ly le `catalog.py`
   dung khi no SUY RA `capability` tu ten tool thay vi cho khai rieng.
"""
from __future__ import annotations

import pytest


def _spec() -> dict:
    from platform_core.public_api.config import load_public_api_config
    from server.api import build_public_api_app

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "text.chat"})
    return build_public_api_app(cfg).openapi()


def _than_chat() -> dict:
    p = _spec()["paths"]["/chat/completions"]["post"]
    return (p.get("requestBody", {}).get("content", {})
             .get("application/json", {}).get("schema", {}))


def test_than_request_KHONG_duoc_rong():
    """🔴 Phep kiem chinh. `additionalProperties: true` tran la mot spec rong."""
    s = _than_chat()
    props = s.get("properties") or {}
    assert props, (
        "`/chat/completions` khong mo ta mot truong nao trong OpenAPI — ai sinh "
        "client tu spec nay nhan mot client chi biet `dict`. Do dung la trang "
        "thai truoc 14/09/2026.")
    assert len(props) >= 10, (
        f"chi mo ta {len(props)} truong; hop dong co nhieu hon the — spec dang "
        "noi thieu")


def test_spec_KHOP_hop_dong_chu_khong_phai_mot_ban_khai_thu_hai():
    """⛔ Bat bien quan trong hon phep kiem tren: HAI be mat, MOT nguon.

    Mot spec day du nhung tu viet se troi khoi `params_schema` — va luc do no
    con nguy hiem hon mot spec rong, vi no trong nhu that.
    """
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "text.chat"})
    tool = [t for t in build_catalog(cfg) if t.name == "text.chat"][0]

    spec = _than_chat()
    nguon = dict(tool.input_schema)

    # ⚠️ KHONG doi BANG NHAU tuyet doi: FastAPI tu them `title` vao schema no
    #    xuat ra. Bat bien that la "moi thu NGUON noi, spec phai noi y het" —
    #    doi bang nhau se do vi mot khoa trang tri, va mot phep kiem do vi ly do
    #    sai thi som muon cung bi noi long cho de chiu.
    for khoa, gia_tri in nguon.items():
        assert spec.get(khoa) == gia_tri, (
            f"spec lech nguon o `{khoa}` — nghia la co ai do bat dau giu mot "
            f"ban khai thu hai, va hai ban se troi khoi nhau.\n"
            f"  nguon: {gia_tri!r}\n  spec : {spec.get(khoa)!r}")

    thua = sorted(set(spec) - set(nguon) - {"title"})
    assert not thua, (
        f"spec mang them {thua} ma nguon khong co — mot truong khong ai khai "
        "trong `params_schema` ma van hien ra cho khach doc")


@pytest.mark.parametrize("truong", ["messages", "model", "max_tokens",
                                    "reasoning_effort", "response_format",
                                    "tool_choice", "top_p", "seed", "stop"])
def test_truong_nay_phai_co_trong_spec(truong):
    """Tung truong cong khai phai doc duoc tu spec may doc."""
    assert truong in (_than_chat().get("properties") or {}), (
        f"`{truong}` vang trong OpenAPI — khach dung bo sinh client se khong "
        f"bao gio biet no ton tai")


def test_enum_va_mac_dinh_di_theo_ra_spec():
    """Biet TEN truong ma khong biet GIA TRI hop le thi van khong goi dung duoc."""
    props = _than_chat()["properties"]
    re_ = props["reasoning_effort"]
    assert re_.get("enum"), "`reasoning_effort` khong mang enum ra spec"
    assert "none" not in re_["enum"], (
        "`none` da bi go 14/09 nhung spec van cong bo no")
    # Q131: mac dinh di THEO MODEL (`ngan_sach.nghi_mac_dinh`), nen spec khong
    # duoc cong bo mot default CHUNG — mot default chung se noi sai cho LTT 3.5.
    assert "default" not in re_, (
        "`reasoning_effort` cong bo default chung, trai Q131 (default theo model)")
    assert props["model"].get("enum"), "`model` khong mang danh sach alias ra spec"


def test_mo_ta_KHONG_con_khuyen_dung_none():
    """Giu cho mo ta khong con day khach toi mot gia tri da bi go."""
    mo_ta = str(_than_chat()["properties"]["reasoning_effort"].get("description") or "")
    assert "`none`" not in mo_ta, (
        "mo ta van khuyen dung `none`, ma gia tri ay da bi go khoi enum — "
        "khach lam theo se an 400")
