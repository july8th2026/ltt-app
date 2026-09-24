"""Spec §4.5 — ba nguồn NodeDefinition, không nguồn nào trùng."""
from __future__ import annotations

import pytest

from platform_core.workflow import nut, nut_loi
from platform_core.workflow.cong_cu import CongCu


def _cc(ten="t.x", **kw):
    goc = dict(ten=ten, app_slug="t", job_type="t.x", type_version=1,
               params_schema={}, side_effect="external",
               idempotency_fields=("a",), tinh_gia=lambda p: 1,
               returns={"out": "text"}, mo_ta="Mot tool",
               resource={"class": "api"})
    goc.update(kw)
    return {ten: CongCu(**goc)}


def test_nut_loi_khai_trigger_manual():
    nd = nut_loi.tat_ca()["trigger.manual"]
    assert nd.kind == "trigger" and nd.category == "TRIGGERS"
    assert nd.cong_vao == ()                       # trigger khong co cong vao
    assert dict((t, c.type) for t, c in nd.cong_ra) == {"event": "event"}
    assert nd.gia == nut.Gia.mien_phi()
    # Compiler hom nay tu choi `trigger.*` (`bien_dich._node`) => plan 04.
    assert nd.publish_duoc is False


def test_tat_ca_hop_ba_nguon():
    ra = nut.tat_ca(cong_cu=_cc())
    assert "app.t.x" in ra and "trigger.manual" in ra
    assert ra["app.t.x"].kind == "app" and ra["app.t.x"].publish_duoc is True


def test_nguon_piece_MAC_DINH_rong_va_allowlist_CO_TRAN(monkeypatch):
    """⭐ Tripwire nổ đúng hẹn (24/09): phase gốc 8 nạp piece thật vào palette.

    Bản trước chốt `nut.NGUON_PIECE() == []`. Hai vấn đề, và cái thứ hai mới
    là cái đáng sửa:

    1. *"nguồn mặc định rỗng"* là **sự thật nhất thời** — nó hết đúng khi có
       connector thật. Mệnh đề **bền** là: hàm mặc định rỗng, và allowlist
       **có trần**.
    2. ⛔ `NGUON_PIECE` là một **biến toàn cục bị ghi đè lúc import**. Đo được:
       gọi trong một tiến trình sạch ra **0**, chạy dưới pytest ra **7** —
       tức bài kiểm đọc một giá trị **phụ thuộc thứ tự import**, cùng hạng với
       ca `lru_cache` bị đầu độc. Nên chốt **hàm mặc định**, không chốt biến.
    """
    assert nut._nguon_piece_rong() == [], "ham MAC DINH phai rong"

    # 🔑 Vế bền: loader tính theo piece **NẠP**, ⛔ không theo catalog (730
    #    piece). Một allowlist không trần thì "allowlist" chỉ là một cái tên.
    ds = nut.NGUON_PIECE()
    assert isinstance(ds, list) and len(ds) <= 20, (
        f"allowlist phai CO TRAN, dang co {len(ds)} piece — neu catalog da tran "
        f"vao day thi chi phi nap khong con theo so piece dung that")
    nd = nut.tu_piece({
        "type": "piece.google-sheets.find_rows", "type_version": 1,
        "title": "Tim dong", "description": "Tim dong trong Google Sheets",
        "icon": "S", "auth": ["oauth2"],
        "params": {"sheet_id": {"type": "string", "required": True}},
        "returns": {"rows": "json[]"}})
    assert nd.kind == "connector" and nd.category == "CONNECTORS"
    assert nd.thi_hanh == "job" and nd.credential == ("oauth2",)
    assert {"network", "credential"} <= nd.quyen
    assert nd.publish_duoc is False


def test_trung_type_giua_hai_nguon_thi_NEM_khong_am_tham_de_len():
    def nguon():
        return [{"type": "app.t.x", "type_version": 1, "title": "Gia mao",
                 "description": "", "icon": "", "auth": [], "params": {},
                 "returns": {}}]
    with pytest.raises(nut.LoiNut, match="trung type"):
        nut.tat_ca(cong_cu=_cc(), nguon_piece=nguon)


def test_tool_khai_workflow_False_khong_len_palette():
    assert "app.t.x" not in nut.tat_ca(cong_cu=_cc(workflow=False))


def test_tool_thieu_hop_dong_V2_khong_len_palette():
    # Spec 4.5: chi tool khai du `side_effect` + `idempotency` + `resource`
    # moi len palette workflow. Task 7 khai du cho 17/19.
    assert "app.t.x" not in nut.tat_ca(
        cong_cu=_cc(idempotency_fields=(), resource={}))
    assert "app.t.x" in nut.tat_ca(cong_cu=_cc())


def test_chua_du_hop_dong_dem_duoc_tung_truong_thieu():
    assert nut.chua_du_hop_dong(
        _cc(idempotency_fields=(), resource={})) == {"t.x": ["idempotency",
                                                             "resource"]}
    assert nut.chua_du_hop_dong(_cc()) == {}
