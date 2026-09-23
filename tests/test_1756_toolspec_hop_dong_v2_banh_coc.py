"""Bánh cóc: tool CHƯA khai đủ hợp đồng V2 chỉ được ÍT ĐI (spec §4.5, §19).

⭐ Chốt TẬP HỢP chứ không chốt SỐ LƯỢNG — cùng bài học `check_so_test`: một
   thiếu sót MỚI vẫn lọt nếu một thiếu sót CŨ được dọn trong cùng lượt.
"""
from __future__ import annotations

from platform_core.workflow import nut
from platform_core.workflow.cong_cu import tat_ca

#: ⛔ CHỈ ĐƯỢC CO LẠI. Lý do từng tool: plan 02 Task 7 (ba làn VRAM).
CHUA_DU = frozenset({"video.upscale", "image.upscale"})


def test_khong_tool_nao_MOI_bi_thieu():
    thieu = nut.chua_du_hop_dong(tat_ca())
    moi = sorted(set(thieu) - CHUA_DU)
    assert not moi, ("tool MOI thieu truong hop dong V2:\n  "
                     + "\n  ".join(f"{t}: thieu {thieu[t]}" for t in moi))


def test_danh_sach_mien_tru_khong_chua_thu_da_xong():
    thieu = nut.chua_du_hop_dong(tat_ca())
    thua = sorted(CHUA_DU - set(thieu))
    assert not thua, f"`CHUA_DU` con {thua} nhung chung da khai du — go khoi danh sach"


def test_phep_kiem_nay_thuc_su_doc_duoc_registry():
    # Doi chung: `tat_ca()` rong thi hai bai tren deu xanh ma khong do gi.
    assert len(tat_ca()) >= 19


def test_17_tool_len_duoc_palette_workflow():
    app = {t for t in nut.tat_ca() if t.startswith("app.")}
    assert len(app) == 17, sorted(app)
    assert "app.video.upscale" not in app and "app.image.upscale" not in app


def test_resource_class_deu_thuoc_tu_vung_dong():
    for ten, cc in tat_ca().items():
        lop = (cc.resource or {}).get("class")
        if lop is not None:
            assert lop in nut.RESOURCE_CLASS, (ten, lop)
