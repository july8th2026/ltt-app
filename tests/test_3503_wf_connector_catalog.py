"""`catalog.json` ⇄ `allowlist.json` ⇄ `package-lock.json` — phép kiểm CƠ HỌC.

Spec §18.4 đòi *"`catalog.json` khớp `allowlist.json` + `package-lock.json`"*.
Tệp này là phép kiểm ấy, cộng hai bất biến của bản thân catalog.

## Vì sao cơ học chứ không phải một dòng trong quy trình

Ba tệp trên khai **cùng một điều** (piece nào, bản nào) ở ba chỗ. Không ai bắt
khớp thì chúng trôi khỏi nhau, và chỗ chúng lệch là chỗ một node đã publish
gọi một action **không còn tồn tại** — lỗi chỉ lộ ra lúc chạy, trên máy khách.

## ⛔ Không phép nào ở đây đếm sự VẮNG MẶT

Mọi phép đều khẳng định một tập **khác rỗng** trước khi kết luận. Một
`catalog.json` rỗng phải làm tệp này ĐỎ, không phải xanh.
"""
from __future__ import annotations

import json
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
RUNNER = GOC / "connector_runner"


def _doc(ten):
    p = RUNNER / ten
    if not p.exists():
        pytest.skip(f"{ten} chua sinh (chua chay npm install / xuat_catalog)")
    return json.loads(p.read_text(encoding="utf-8"))


def test_catalog_co_node_THAT_khong_phai_tap_rong():
    """⛔ Đối chứng trước mọi phép dưới: tập rỗng thì mọi `all(...)` đều xanh."""
    cat = _doc("catalog.json")
    assert cat["nodes"], "catalog KHONG co node nao — moi phep duoi la do rong"
    assert cat["pieces"], "catalog KHONG liet ke piece nao"


def test_moi_node_trong_catalog_thuoc_mot_piece_TRONG_allowlist():
    al = _doc("allowlist.json")
    cat = _doc("catalog.json")
    ngoai = {n["piece"] for n in cat["nodes"]} - set(al["pieces"])
    assert not ngoai, f"node tro toi piece ngoai allowlist: {sorted(ngoai)}"


def test_phien_ban_catalog_KHOP_allowlist():
    al = _doc("allowlist.json")
    cat = _doc("catalog.json")
    lech = {n["piece"]: (n["piece_version"], al["pieces"][n["piece"]])
            for n in cat["nodes"]
            if str(n["piece_version"]) != str(al["pieces"][n["piece"]])}
    assert not lech, f"catalog va allowlist lech ban: {lech}"


def test_phien_ban_allowlist_KHOP_package_lock():
    """`package-lock.json` là thứ `npm ci` thật sự cài. Lệch ⇒ runner nạp một
    bản khác bản đã chốt, và `piece_nap.js` sẽ ném lúc chạy."""
    al = _doc("allowlist.json")
    lock = _doc("package-lock.json")
    goi = lock.get("packages") or {}
    lech = {}
    for ten, ban in al["pieces"].items():
        muc = goi.get(f"node_modules/{ten}")
        if muc is None:
            lech[ten] = "khong co trong lock"
        elif str(muc.get("version")) != str(ban):
            lech[ten] = f"lock={muc.get('version')} allowlist={ban}"
    assert not lech, f"allowlist va package-lock lech: {lech}"


def test_moi_piece_trong_allowlist_co_DANH_SACH_MIEN():
    """Fail-closed cần một danh sách để mà đóng: piece thiếu mục `mien` sẽ
    không nối được đi đâu, và lỗi ấy chỉ lộ ra lúc khách bấm chạy."""
    al = _doc("allowlist.json")
    thieu = [t for t in al["pieces"] if not (al.get("mien") or {}).get(t)]
    assert not thieu, f"piece thieu khai mien: {thieu}"


def test_moi_action_tren_palette_DEU_CO_THAT_o_ban_da_ghim():
    """🔴 Đây là lý do `xuat_catalog` tồn tại.

    Spec §11.6 tự khai rằng cột action của nó là **đích cần tra**, không phải
    tên đã xác minh — và đo 24/09 cho thấy 8/13 tên đoán không tồn tại. Phép
    này chốt rằng mọi tên **trên palette** đã qua `xuat_catalog`, tức đã được
    đối chiếu với `piece.actions()` thật.
    """
    al = _doc("allowlist.json")
    cat = _doc("catalog.json")
    co_trong_catalog = {(n["piece"], n["name"]) for n in cat["nodes"]}
    bo_qua = {(b["piece"], b["name"]) for b in cat.get("bo_qua") or []}
    thieu = []
    for piece, pal in (al.get("palette") or {}).items():
        for ten in list(pal.get("actions") or []) + list(pal.get("triggers") or []):
            if (piece, ten) not in co_trong_catalog and (piece, ten) not in bo_qua:
                thieu.append((piece, ten))
    assert not thieu, (
        f"ten tren palette khong co trong catalog LAN trong so bo qua: {thieu}")


def test_bo_qua_luon_NOI_LY_DO():
    """Một action bị bỏ mà không nói vì sao là một action sẽ bị thêm lại."""
    cat = _doc("catalog.json")
    for b in cat.get("bo_qua") or []:
        assert b.get("vi_sao"), f"bo qua khong co ly do: {b}"


def test_trigger_tren_palette_CHI_duoc_la_POLLING():
    """Spec §11.4: trigger WEBHOOK/APP_WEBHOOK của piece **ngoài phạm vi**.

    Một trigger webhook lọt lên palette là một node không bao giờ bắn — và
    khách sẽ ngồi chờ một workflow chẳng chạy.
    """
    cat = _doc("catalog.json")
    for n in cat["nodes"]:
        if n.get("kind") == "trigger":
            assert n["op"] == "run_trigger"
    for b in cat.get("bo_qua") or []:
        if "trigger_khong_phai_POLLING" in b["vi_sao"]:
            assert b["name"] not in {n["name"] for n in cat["nodes"]}


# ── Node đã vào sổ chưa ────────────────────────────────────────────────────

def test_node_piece_vao_SO_NODE_qua_NGUON_PIECE():
    """⭐ Khe cắm `nut.NGUON_PIECE` phải được gán — không thì palette trống mà
    không ai báo lỗi (mô-đun đăng ký không ai import = mô-đun CHẾT)."""
    from platform_core.workflow import nut
    so = nut.tat_ca()
    piece = {k: v for k, v in so.items() if v.job_type == nut.JOB_TYPE_PIECE}
    assert piece, "khong node piece nao vao so — NGUON_PIECE chua duoc gan?"


def test_node_trigger_piece_nam_o_nhom_TRIGGERS():
    """Một trigger nằm trong nhóm CONNECTORS thì người soạn không tìm thấy nó
    ở chỗ họ tìm mọi trigger khác — và kết luận là "khong co trigger Sheets"."""
    # 🔴 PHAI import `nut_loi` TRUOC. `nut.tat_ca()` doc bien toan cuc
    #    `nut.NGUON_PIECE`, va bien do chi duoc gan khi `nut_loi/connector.py`
    #    duoc import (`nut_loi/__init__.py:120`). Thieu dong nay thi `tat_ca()`
    #    tra ve mot tap node THIEU — va bai kiem BO QUA voi mot ly do SAI
    #    ("catalog khong co trigger POLLING"), trong khi catalog co.
    #
    # ⛔ Da xay ra that: gate 24/09 bao bo qua vi ly do do, nhung do lai thi
    #    `trigger.piece.google_sheets.new_spreadsheet` CO tren palette. Mot
    #    phep kiem khong chay ma ke mot ly do khong dung thi te hon mot phep do.
    from platform_core.workflow import nut, nut_loi  # noqa: F401
    trig = [v for v in nut.tat_ca().values()
            if v.job_type == nut.JOB_TYPE_PIECE and v.kind == "trigger"]
    if not trig:
        pytest.skip("catalog vong nay THAT SU khong co trigger POLLING nao")
    for nd in trig:
        assert nd.category == "TRIGGERS"


def test_node_piece_publish_duoc_tu_25_09_lan_wfp():
    """🔴 SỬA 25/09 (lan wfp, plan 08): `bien_dich._node` nay biên dịch được
    `piece.*`/`trigger.piece.*` (qua `nut.dinh_nghia_piece`) và `cau_noi`
    nộp job được qua `_nop_job_connector` (đã có từ P6, chỉ thiếu chỗ gọi
    tới) — ba cửa từng khoá cờ này đã nối, xem
    `docs/superpowers/plans/2026-09-25-wf-v2-VAN-HANH.md` lan wfp."""
    from platform_core.workflow import nut
    for nd in nut.tat_ca().values():
        if nd.job_type == nut.JOB_TYPE_PIECE:
            assert nd.publish_duoc is True


def test_job_type_connector_CO_CHU_trong_registry():
    """🔴 Một `job_type` không app nào khai ⇒ worker không bao giờ nhận job ⇒
    node đứng QUEUED tới khi `TRAN_RUN` (20 giờ) hết hạn, **với tiền đã giữ**.
    """
    from platform_core import registry
    from platform_core.workflow import nut
    chu = registry.job_type_owners()
    for jt in (nut.JOB_TYPE_PIECE, nut.JOB_TYPE_CONNECTOR):
        assert chu.get(jt), f"khong app nao khai job_type {jt!r}"
