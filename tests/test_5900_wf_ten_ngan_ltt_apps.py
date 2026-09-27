"""Làn UI-N — tên NGẮN cho node `app.*` (thay câu bị cắt giữa từ ở 60 ký tự).

## Vấn đề, đo được trên API thật 27/09/2026

`nut._tieu_de` lấy câu đầu của `description` rồi cắt cứng ở 60 ký tự. Mô tả
của app LTT là một câu dài không có dấu chấm giữa ⇒ cắt GIỮA TỪ
(`"...tùy c"`, `"...và FFmpe"`, `"...ánh sáng"` bị chặt cụt). App LTT là
nhóm node bị đặt nhãn tệ nhất trong palette, trong khi node mượn từ
Activepieces (CONNECTORS/FLOW/TRIGGERS) thì sạch.

## Hướng sửa

`ToolSpec.ten_ngan` (registry.py) — trường TUỲ CHỌN, mỗi app tự khai cạnh
`ToolSpec` của chính nó. `_tieu_de` dùng nó khi có; rỗng thì LÙI VỀ hành vi cũ
(câu đầu của `description`, cắt ở 60). Đây KHÔNG phải một bảng `{tên tool:
nhãn}` tập trung trong nền tảng — `test_967_canvas_khong_hardcode_ten_tool.py`
cấm đúng thứ đó, và cấm ở tầng frontend/`platform_core`, không cấm một app tự
đặt tên cho tool của chính nó.

Phép kiểm này đứng ở hai tầng:

1. Đơn vị — `_tieu_de`/`tu_toolspec` dùng `ten_ngan` khi có, lùi về hành vi
   cũ khi vắng (không ai được sửa hành vi cũ khi app chưa khai gì).
2. Tích hợp — toàn bộ registry hôm nay: 0 node `LTT_APPS` có title > 40 ký
   tự, các `category` khác (CONNECTORS/FLOW/TRIGGERS/DATA/…) không bị chạm,
   và mỗi `ten_ngan` đã khai ngắn hơn 28 ký tự (hướng dẫn cho app viết sau).
"""
from __future__ import annotations

from platform_core.workflow import nut
from platform_core.workflow.cong_cu import CongCu


def _cc(ten="t.x", mo_ta="", ten_ngan="", **kw):
    goc = dict(ten=ten, app_slug="t", job_type="t.x", type_version=1,
               params_schema={}, side_effect="external",
               idempotency_fields=("a",), tinh_gia=lambda p: 1,
               returns={"out": "text"}, mo_ta=mo_ta, ten_ngan=ten_ngan,
               resource={"class": "api"})
    goc.update(kw)
    return CongCu(**goc)


# ── Tầng 1: đơn vị ───────────────────────────────────────────────────────────

def test_tieu_de_dung_ten_ngan_khi_co():
    """`ten_ngan` thắng, dù `description` có dài và không dấu chấm."""
    mo_ta_dai = "Mot cau rat dai khong co dau cham nao het cho toi khi no bi cat cung"
    assert nut._tieu_de(mo_ta_dai, "app.x.y", "Tên ngắn gọn") == "Tên ngắn gọn"


def test_tieu_de_LUI_VE_hanh_vi_cu_khi_ten_ngan_RONG():
    """Vắng `ten_ngan` ⇒ y hệt hành vi cũ (câu đầu, cắt ở 60 ký tự).

    Đây là bánh cóc chống hồi quy: app CHƯA khai `ten_ngan` không được đổi
    hành vi title của họ — kể cả khi câu vẫn bị cắt giữa từ như trước.
    """
    mo_ta = "Mot cau rat dai khong co dau cham nao het cho toi khi no bi cat cung"
    cu = nut._tieu_de(mo_ta, "app.x.y")
    assert cu == mo_ta[:60]
    assert nut._tieu_de(mo_ta, "app.x.y", "") == cu
    assert nut._tieu_de(mo_ta, "app.x.y", "   ") == cu, "chuoi trang cung phai LUI VE"


def test_tieu_de_rong_ca_hai_suy_tu_ten_tool():
    assert nut._tieu_de("", "app.video.sub_thing") == "App Video Sub Thing"


def test_tu_toolspec_dung_ten_ngan_cua_congcu():
    cc = _cc(ten="video.generate",
              mo_ta="Sinh video Seedance tu mo ta va cac tai san tham chieu tuy chon dai",
              ten_ngan="Tạo video Seedance")
    nd = nut.tu_toolspec(cc)
    assert nd.title == "Tạo video Seedance"
    assert len(nd.title) <= 40


def test_tu_toolspec_KHONG_co_ten_ngan_LUI_VE_cu():
    """App chưa khai `ten_ngan` (mặc định `""` trên `ToolSpec`/`CongCu`) vẫn ra
    đúng title như trước khi trường này tồn tại — kể cả bị cắt giữa từ."""
    mo_ta = "Sinh video Seedance tu mo ta va cac tai san tham chieu tuy chon rat dai qua"
    cc = _cc(ten="video.generate", mo_ta=mo_ta)
    nd = nut.tu_toolspec(cc)
    assert nd.title == mo_ta[:60]


# ── Tầng 2: tích hợp trên registry thật ─────────────────────────────────────

def _tat_ca_that() -> dict:
    return nut.tat_ca()


def test_khong_con_node_LTT_APPS_nao_qua_40_ky_tu():
    ra = _tat_ca_that()
    qua = {t: nd.title for t, nd in ra.items()
           if nd.category == "LTT_APPS" and len(nd.title) > 40}
    assert not qua, f"con title > 40 ky tu: {qua}"


def test_cac_category_KHAC_khong_bi_dung_toi():
    """CONNECTORS/FLOW/TRIGGERS/DATA/AI/… đang đúng — làn này không chạm gì ở
    đó, nên số node > 40 ký tự các nhóm ấy phải vẫn là 0 (như trước khi sửa)."""
    ra = _tat_ca_that()
    for cat in ("CONNECTORS", "FLOW", "TRIGGERS", "DATA", "AI",
                "NETWORK", "SUBWORKFLOWS"):
        qua = {t: nd.title for t, nd in ra.items()
               if nd.category == cat and len(nd.title) > 40}
        assert not qua, f"category {cat} co title > 40: {qua}"


def test_moi_ten_ngan_da_khai_ngan_hon_28_ky_tu():
    """Hướng dẫn cho app viết sau (không phải cưỡng chế cứng của nền tảng):
    `ten_ngan` nên là một cụm ngắn đọc lướt được, không phải một câu."""
    from platform_core import registry

    qua_dai = {}
    for a in registry.discover():
        if a.error:
            continue
        for t in a.manifest.tools:
            ngan = str(getattr(t, "ten_ngan", "") or "")
            if ngan and len(ngan) > 28:
                qua_dai[t.name] = ngan
    assert not qua_dai, f"ten_ngan dai qua 28 ky tu: {qua_dai}"


def test_khong_ten_ngan_nao_bi_CAT_GIUA_TU():
    """Node nào có `title` khớp đúng một `ten_ngan` đã khai thì không bị cắt —
    tức không kết thúc bằng một từ cụt (khác hẳn dấu hiệu cắt cứng ở 60)."""
    from platform_core import registry

    khai = {t.name: str(getattr(t, "ten_ngan", "") or "")
            for a in registry.discover() if not a.error
            for t in a.manifest.tools if getattr(t, "ten_ngan", "")}
    ra = _tat_ca_that()
    for ten_full, nd in ra.items():
        if nd.category != "LTT_APPS":
            continue
        ten_toolspec = nd.ten_toolspec
        if ten_toolspec in khai:
            assert nd.title == khai[ten_toolspec], (
                f"{ten_full}: title khong khop ten_ngan da khai")
