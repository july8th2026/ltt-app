"""FLOW G (spec §18.5) — điều kiện ra của phase gốc 11. Plan wf-v2 P8 Task 6.

> G | câu *"Đọc Sheet mỗi sáng, lấy READY, tạo video, chờ tôi duyệt"* | Agent
>     sinh draft v3 qua validator không lỗi, có **cron + sheets + filter +
>     foreach + video + human**

## 🔴 HAI TRONG SÁU THÀNH PHẦN KHÔNG TỒN TẠI HÔM NAY — và đó là phép đo

`test_sau_thanh_phan_FLOW_G_hai_cai_chua_co` đo **bản khai thật**, không đọc
plan: hôm nay `nut.tat_ca()` không có node nào cho **Sheets** (connector là
phase gốc **8**, chưa chạy) và không có node **cron** (P4 làm trigger thành
**hàng trong `workflow_trigger`**, ⛔ không phải node trong đồ thị — một thiết
kế khác spec §18.5 giả định khi viết dòng ấy).

⇒ FLOW G đạt **4/6** thành phần, và hai cái thiếu là **sự vắng mặt đo được**,
không phải một chỗ tôi bỏ qua. Nếu mai Sheets lên palette mà phép kiểm này vẫn
xanh thì nó sai — nên nó có vế ngược: nó **đỏ** ngay khi hai thứ ấy xuất hiện,
buộc người thêm chúng phải nâng FLOW G lên 6/6.

## Phép này KHÔNG phủ cái gì

- ⛔ Không gọi model thật. Đầu ra model là **dữ liệu vàng** tiêm vào; số đo của
  một lượt gọi máy B thật nằm ở `reports/p8-agent/task-6-report.md`.
- ⛔ Không chạy run. FLOW G là phép kiểm về **soạn thảo** (draft qua validator),
  không phải về thi hành — §18.5 xếp A–F và H là các flow chạy trên PostgreSQL;
  G không nằm trong danh sách ấy.
"""
from __future__ import annotations

import json

import pytest

from platform_core.agent import ke_hoach_v3
from platform_core.workflow import cong_cu, nut

CAU = "Đọc Sheet mỗi sáng, lấy READY, tạo video, chờ tôi duyệt"


@pytest.fixture(scope="module")
def cc():
    """Registry THẬT — FLOW G nói về node có thật trên nền tảng này."""
    return cong_cu.tat_ca()


def _do_thi_vang() -> str:
    """Đầu ra model (vàng) cho `CAU`, dùng đúng node đang có."""
    nodes = [
        {"id": "loc", "type": "core.filter", "type_version": 1,
         "params": {"items": "workflow.input.hang",
                    "dieu_kien": "item.trang_thai == 'READY'"}},
        {"id": "vong", "type": "core.foreach", "type_version": 1,
         "params": {"items": "nodes.loc.output.results", "max_items": 20,
                    "parallelism": 2, "on_item_error": "collect"}},
        {"id": "video", "type": "app.video.generate", "type_version": 1,
         "params": {"prompt": "{{ nodes.vong.output.so_muc }}"}},
        {"id": "het_vong", "type": "core.foreach_end", "type_version": 1,
         "params": {"foreach": "vong"}},
        {"id": "duyet", "type": "core.human", "type_version": 1,
         "params": {"cau_hoi": "Duyet video nay?", "timeout_s": 36000,
                    "het_han": "reject"}},
    ]
    canh = [("loc", "vong"), ("vong", "video"), ("video", "het_vong"),
            ("het_vong", "duyet")]
    edges = [{"id": f"e{i}", "source_node": a, "target_node": b,
              "source_port": "out", "target_port": "in", "kind": "DATA"}
             for i, (a, b) in enumerate(canh, 1)]
    return json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False)


# ── 1. Draft v3 đi qua ĐÚNG validator publish, KHÔNG lỗi ────────────────────

def test_FLOW_G_draft_qua_validator_khong_loi(cc):
    kq = ke_hoach_v3.soan_draft(None, goal=CAU, ngan_sach_credit=200,
                                cong_cu=cc, llm_call=lambda _p: _do_thi_vang())
    assert kq["loi"] == (), kq["loi"]
    assert kq["hop_le"] is True
    assert kq["document"]["version"] == 3
    loai = {n["type"] for n in kq["graph"]["nodes"]}
    assert {"core.filter", "core.foreach", "app.video.generate",
            "core.foreach_end", "core.human"} <= loai
    # Thứ tự tô-pô có thật, không phải một danh sách theo thứ tự model gửi.
    assert kq["graph"]["thu_tu"][0] == "loc"
    assert kq["graph"]["thu_tu"][-1] == "duyet"


def test_FLOW_G_bao_gia_ra_mot_tran_CO_SO(cc):
    from platform_core.workflow import bao_gia
    kq = ke_hoach_v3.soan_draft(None, goal=CAU, ngan_sach_credit=200,
                                cong_cu=cc, llm_call=lambda _p: _do_thi_vang())
    bg = bao_gia.bao_gia_do_thi(kq["graph"], cong_cu=cc)
    # Node điều khiển miễn phí; `app.video.generate` thì không — một trần 0 ở
    # đây nghĩa là báo giá đang nhìn nhầm chỗ.
    assert bg.toi_da > 0 and bg.uoc_tinh > 0
    assert kq["graph"]["bang_gia"]["video"] > 0
    assert kq["graph"]["he_so_lap"]["video"] == 20      # max_items cua foreach


# ── 2. Năm trong sáu thành phần ĐÃ CÓ — đo bản khai, không đọc plan ────────

def _lich_khai_trong_do_thi(so: dict) -> list[str]:
    """`[loai]` cua nhung node LICH co khai tham so — luat cua tripwire duoi.

    ⭐ Tach ra thanh HAM de mot phep TIEM NGHICH goi duoc no. Toi vua **noi**
       tripwire nay (tu *"khong node nao ten cron"* sang *"node duoc ton tai,
       tham so phai RONG"*), va *"noi"* voi *"thay the bang mot cau luon dung"*
       ⛔ khong phan biet duoc tu ben ngoai. Chi mot doi chung phan biet duoc.
    """
    ra = []
    for loai, dn in so.items():
        if "cron" not in loai.lower() and "schedule" not in loai.lower():
            continue
        ts = getattr(dn, "tham_so", None) or {}
        if sorted(ts.get("properties") or {}):
            ra.append(loai)
    return ra


def test_luat_tripwire_lich_THUC_SU_bat_duoc_mot_node_vi_pham():
    """🔴 TIEM NGHICH: dung mot node lich GIA CO tham so, luat phai BAT.

    ⛔ Khong co bai nay thi mot lan "nang" tripwire khong phan biet duoc voi mot
       lan **rut nanh** no: ca hai deu lam bo test xanh.

    ⭐ Va ve KHANG DINH o duoi: node lich THAT (`trigger.schedule`) co tham so
       RONG nen luat tra `[]`. Hai ve cung mot ham => luat co RANG, va rang ay
       ⛔ khong cham vao node that.
    """
    class _Gia:
        tham_so = {"type": "object", "properties": {"cron": {"type": "string"}}}

    assert _lich_khai_trong_do_thi({"trigger.schedule": _Gia()}) ==         ["trigger.schedule"], "luat KHONG bat duoc node lich co tham so"
    # Ten khong phai lich thi luat KHONG cham toi — no hep dung cho can hep.
    assert _lich_khai_trong_do_thi({"core.http": _Gia()}) == []


def test_nam_thanh_phan_FLOW_G_da_co_va_cron_van_la_HANG(cc):
    """⭐ TRIPWIRE ĐÃ NỔ ĐÚNG HẸN (24/09) — và đây là lượt NÂNG nó.

    Bản trước chốt *"sheets và cron CHƯA có"*, và tự viết sẵn việc phải làm:
    *"Sheets ĐÃ lên palette ⇒ hãy NÂNG phép kiểm này thay vì để nó xanh."*
    Phase gốc 8 đưa `google_sheets` lên palette ⇒ nó đỏ đúng lúc nó phải đỏ.

    ⛔ Cách sai là xoá khẳng định cho hết đỏ. Cách đúng là **đổi mệnh đề**: từ
       *"chưa có"* sang *"đã có, và đây là tên thật"* — vì thứ đáng chốt bây
       giờ là **piece nào thật sự lên palette**, không phải **sự vắng mặt**.
    """
    muc = {m["type"] for m in ke_hoach_v3.danh_muc(cong_cu=cc)}
    co = {"filter": "core.filter", "foreach": "core.foreach",
          "human": "core.human"}
    for ten, loai in co.items():
        assert loai in muc, f"{ten}: {loai} phai co trong danh muc"
    assert any(t.startswith("app.video.") for t in muc), "video"

    so = nut.tat_ca(cong_cu=cc)
    sheets = sorted(t for t in so if "sheet" in t.lower())
    assert sheets, "Sheets phai co tren palette sau phase goc 8"
    # 🔑 Chốt TÊN THẬT, không chốt "có gì đó chứa chữ sheet": 8/13 tên spec
    #    §11.6 đoán ra là KHÔNG TỒN TẠI (phase 8 đo bằng `xuat_catalog`), nên
    #    một phép kiểm chỉ hỏi "có chứa chuỗi" sẽ xanh cho một tên bịa.
    assert "piece.google_sheets.find_rows" in sheets, sheets

    # 🔴 NÂNG 28/09 — tripwire này đã nổ, và nó nổ ĐÚNG. Nâng theo đúng cách
    #    docstring trên tự dặn: *"đổi mệnh đề"*, ⛔ không xoá khẳng định.
    #
    #    Mệnh đề cũ: *"⛔ không node nào tên cron/schedule"*. Nó đã đúng khi
    #    viết, nhưng nó chốt **sự VẮNG MẶT** — và chủ dự án đã duyệt mở lịch hẹn
    #    giờ (28/09) nên sự vắng mặt ấy hết là sự thật.
    #
    #    ⭐ Thứ tripwire này THỰC SỰ bảo vệ ⛔ không phải cái tên: nó là
    #    *"lịch ⛔ KHÔNG được khai trong ĐỒ THỊ"* — vì `WorkflowTrigger` không có
    #    `node_id` (bài ngay dưới đo điều đó), và `params` thì bị **nhân bản khi
    #    khách Save as**, nên hai bản lịch sẽ lệch và không ai biết bản nào bắn.
    #    ⇒ Mệnh đề mới: node CỬA VÀO được tồn tại (như `trigger.manual`), nhưng
    #      `tham_so` của nó phải RỖNG.
    vi_pham = _lich_khai_trong_do_thi(so)
    assert vi_pham == [], (
        f"node khai tham so lich: {vi_pham}. Lich nam o HANG `workflow_trigger` "
        "(khong co cot `node_id`), va `params` bi nhan ban khi khach Save as "
        "=> hai cho khai cung mot dieu")


def test_cron_la_MOT_HANG_chu_khong_phai_mot_NODE():
    """Vì sao *"cron"* của FLOW G không thể là một node hôm nay."""
    from platform_core.models import WorkflowTrigger
    assert WorkflowTrigger.__tablename__ == "workflow_trigger"
    cot = {c.name for c in WorkflowTrigger.__table__.columns}
    # Lịch nằm trong `config` của một HÀNG, gắn vào `workflow_id` — không có
    # `node_id` nào, nên không đồ thị nào chứa được nó.
    assert {"kind", "config", "next_fire_at", "workflow_id"} <= cot
    assert "node_id" not in cot


# ── 3. Agent KHÔNG publish — vế hành vi, cạnh bánh cóc AST ở test_2933 ──────

def test_soan_draft_KHONG_tao_version_nao(cc):
    """`soan_draft` là hàm thuần trên `document`: nó không nhận `db`, không
    ghi. Cửa `/soan` mới là nơi ghi draft — và nó vẫn **không** publish."""
    kq = ke_hoach_v3.soan_draft(None, goal=CAU, ngan_sach_credit=200,
                                cong_cu=cc, llm_call=lambda _p: _do_thi_vang())
    # `db=None` mà chạy được chính là bằng chứng: không câu lệnh CSDL nào chạy.
    assert kq["hop_le"] is True
