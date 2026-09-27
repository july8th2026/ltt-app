"""UI-0 Task 1 — node do PALETTE Canvas tao phai bien dich duoc.

`frontend/agent-canvas/src/editorState.ts::nextNode()` dung MOI node voi
`type:'tool'` va dat loai THAT vao `data.tool`. `bien_dich._node()` phan nhanh
theo `type` o MUC TREN CUNG, nen truoc ban va nay moi node `core.*`/`piece.*`
keo tu palette deu chet voi `node_khong_ton_tai`.

## Do duoc tren trinh duyet THAT, 27/09/2026

Mo Canvas -> "Mo bang node" -> bam MOT the `core.set` -> "Chay" -> "Chay ngay":

    runError : "node_khong_ton_tai: core.set"
    banner   : "Workflow chua bien dich duoc"

Lap lai voi `piece.google_sheets.insert_row`: cung ket qua. Doi chung voi mot
node `app.*`: `runStatus = "QUEUED"` — tuc duong `app.*` song sot DO TRUNG HOP
(`slugCongCu` cat tien to `app.`, va slug con lai dung la khoa trong so cong cu
app). 55/67 loai buoc con lai thi khong.
Toan van: `docs/architecture/agent_ui_v2/01_CURRENT_UI_AUDIT.md` §2.1.

## ⭐ Doi chung lam lo nguyen nhan goc

`platform_core/agent/ke_hoach_v3.py::_data_canvas` (Agent Designer) ghi node voi
`type` THAT o muc tren cung va them `data.tool` chi de canvas RENDER duoc, kem
chu thich tu dan cua chinh no:

    ⛔ KHONG thay `type`/`params` top-level bang khoa nay — cong bien dich
       (`bien_dich._node`/`_node_loi`) doc dung hai khoa top-level do

=> AI dung duoc workflow ma con nguoi khong dung duoc. `tests/test_4250` da ghi
ra bang chu chinh co che hong nay tu truoc, nhung chi soi duong Agent Designer;
khong ai noi no sang duong palette.

## ⛔ Vi sao KHONG doi `nextNode()` ghi `type` that o day

Lam vay se doi hinh dang MOI ban nhap dang nam tren production va doi mot buoc
di tru du lieu. Cong bien dich nhan CA HAI hinh dang thi khong ban nhap nao
phai doi, va ban va dao nguoc duoc bang mot commit.
"""
from __future__ import annotations

import pytest

from platform_core.workflow import bien_dich

#: Tham so BAT BUOC toi thieu cua tung node loi. Lay tu `nut_loi.tat_ca()`
#: (do 27/09: `core.if.required=['dieu_kien']`, `core.set.required=['bien']`,
#: `core.stop.required=[]`), ⛔ khong lay tu tri nho.
_THAM_SO = {
    "core.if": {"dieu_kien": "1 == 1"},
    "core.set": {"bien": {}},
    "core.stop": {},
}


def _tai_lieu(tool: str, params: dict | None = None) -> dict:
    """Mot tai lieu v3 MOT trang MOT node, dung hinh dang `nextNode()` sinh."""
    return {
        "version": 3,
        "goal": "",
        "active_page_id": "p1",
        "pages": [{
            "id": "p1",
            "name": "Page 1",
            "nodes": [{
                "id": "n1",
                "type": "tool",
                "position": {"x": 0, "y": 0},
                "data": {"tool": tool, "params": params or {}},
            }],
            "edges": [],
        }],
    }


@pytest.mark.parametrize("tool", sorted(_THAM_SO))
def test_node_loi_tu_palette_bien_dich_duoc(tool):
    ct = bien_dich.cau_truc(_tai_lieu(tool, _THAM_SO[tool]))
    assert [n["type"] for n in ct.nodes] == [tool]


def test_node_app_tu_palette_van_bien_dich_duoc():
    """Duong `app.*` KHONG duoc hong khi them nhanh lui."""
    ct = bien_dich.cau_truc(
        _tai_lieu("image.generate", {"prompt": "mot con meo"}))
    assert ct.nodes[0]["type"] == "app.image.generate"


def test_loai_that_su_khong_ton_tai_van_bao_dung_ma_loi():
    """Nhanh lui KHONG duoc nuot mot loai go sai thanh mot node im lang."""
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.cau_truc(_tai_lieu("khong.ton.tai.that"))
    assert e.value.ma == "node_khong_ton_tai"
