"""Khoá `wakeup` theo ĐƯỜNG THI HÀNH đầy đủ — `foreach1:0/delay1`.

🔴 NỢ ĐÃ ĐO (plan wf-v2 §4 P3, `models.py:1471`)

    UNIQUE(run_id, node_run_id, kind, due_at)

Nếu `node_run_id` là **node_id trần** thì hai vòng lặp của một `foreach` có
`delay` trong thân sinh **cùng một khoá**: vòng 2 đè (hoặc va) timer vòng 1, và
run đứng chờ tới hạn cuối cùng.

## Nguồn (tra trước khi tự suy — không phải suy luận của tôi)

Activepieces đã dính **đúng** lỗi này và đã sửa. Khoá waitpoint của họ là
`UNIQUE(flow_run_id, step_name)` (`brain/knowledge/flows-execution/flow-runs.md`),
và quyết định `brain/knowledge/decisions/000015-fan-in-is-an-event-driven-waitpoint-barrier.md`
(activepieces@`17e2ac0b`) viết thẳng ra:

    "Identity is path-keyed, and that needed no new column. The engine sends
     `loop_1:3/loop_2:0/approval` in the existing `stepName` field… Which fixes
     a live bug on the way past: a delay or approval **inside a loop** used to
     reuse one waitpoint row across every iteration, so iteration 2 found
     iteration 1's COMPLETED row … and skipped its pause entirely."

⇒ Ta lấy **cùng hình dạng khoá** (`<vòng>:<chỉ số>/<node>`), và lấy luôn kết
  luận *"that needed no new column"*: cột `node_run_id` giữ nguyên `String(64)`,
  không migration. Xem `test_duong_qua_dai_van_vua_cot` — chỗ ta phải đi xa hơn
  họ, vì cột của ta có TRẦN CỨNG còn `stepName` của họ thì không.

## Phép này KHÔNG phủ cái gì

Nó không phủ đường chạy foreach đầy đủ qua `dong_co.xu_ly_run` — node `foreach`
chỉ có mặt ở Task 5. Nó đi qua đúng hai API mà thân vòng lặp sẽ gọi
(`foreach.mo_vong` để biết chỉ số, `danh_thuc.hen_node` để hẹn), nên nó bắt
được lỗi khoá, **không** bắt được lỗi lập lịch.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def _han() -> datetime:
    """MỘT hạn dùng chung cho cả hai vòng — đó chính là ca va chạm."""
    return (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(tzinfo=None)


@pytest.fixture()
def vong(db):
    """Một `foreach` hai phần tử, thân có một node `delay1`."""
    from platform_core.workflow import foreach
    return foreach.mo_vong(db, run_id="r1", node_id="f1", muc=["a", "b"],
                           max_items=10)


# ── ĐỐI CHỨNG: chứng minh mối nguy có thật, và CSDL thật sự cưỡng chế ────────

def test_doi_chung_node_id_tran_thi_vong_2_va_vong_1(db, vong):
    """⛔ Cách CŨ (node_id trần) — hai vòng, MỘT khoá, `IntegrityError`.

    Đây là đối chứng của cả tệp: nếu phép này không đỏ thì ràng buộc duy nhất
    đã biến mất và mọi phép "xanh" phía dưới là xanh giả.
    """
    from platform_core.workflow import danh_thuc, foreach

    han = _han()
    chi_so = foreach.chi_so_chua_xong(db, vong)
    assert chi_so == [0, 1]
    danh_thuc.hen(db, run_id="r1", kind="delay", due_at=han,
                  node_run_id="delay1")            # vòng 0
    with pytest.raises(IntegrityError):
        danh_thuc.hen(db, run_id="r1", kind="delay", due_at=han,
                      node_run_id="delay1")        # vòng 1 — CÙNG khoá
    db.rollback()


# ── LUẬT MỚI ────────────────────────────────────────────────────────────────

def test_moi_vong_foreach_giu_timer_rieng(db, vong):
    """Hai vòng `foreach` có `delay` cùng hạn ⇒ HAI hàng wakeup."""
    from platform_core.models import Wakeup
    from platform_core.workflow import danh_thuc, foreach

    han = _han()
    for i in foreach.chi_so_chua_xong(db, vong):
        danh_thuc.hen_node(db, run_id="r1", node_id="delay1", kind="delay",
                           due_at=han, vong=((vong.node_id, i),))
    db.flush()
    hang = db.query(Wakeup).filter_by(run_id="r1", kind="delay").all()
    assert len(hang) == 2, "vong 2 da de timer vong 1"
    assert sorted(w.node_run_id for w in hang) == ["f1:0/delay1", "f1:1/delay1"]


def test_duong_thi_hanh_hinh_dang_giong_activepieces():
    """`loop_1:3/loop_2:0/approval` — đúng hình dạng quyết định 000015 mô tả."""
    from platform_core.workflow.danh_thuc import duong_thi_hanh

    assert duong_thi_hanh("approval", vong=(("loop_1", 3), ("loop_2", 0))) \
        == "loop_1:3/loop_2:0/approval"
    assert duong_thi_hanh("delay1") == "delay1"      # ngoài vòng lặp: y như cũ


def test_cung_node_cung_vong_van_la_MOT_khoa(db, vong):
    """Luỹ đẳng vẫn phải giữ: hẹn lại **cùng** vòng là cùng một khoá.

    Khử trùng bằng ràng buộc (`danh_thuc.hen` docstring) chỉ còn nghĩa nếu
    khoá của một lần hẹn **lặp lại được**. Nới khoá quá tay thì mọi lần phát
    lại thành một timer mới.
    """
    from platform_core.workflow import danh_thuc

    han = _han()
    danh_thuc.hen_node(db, run_id="r1", node_id="delay1", kind="delay",
                       due_at=han, vong=(("f1", 0),))
    with pytest.raises(IntegrityError):
        danh_thuc.hen_node(db, run_id="r1", node_id="delay1", kind="delay",
                           due_at=han, vong=(("f1", 0),))
    db.rollback()


def test_duong_qua_dai_van_vua_cot(db):
    """Cột là `String(64)`. Đường dài hơn ⇒ khoá băm, **không** cắt cụt.

    ⛔ Cắt cụt là cách im lặng nhất để hai đường khác nhau thành một khoá — đúng
       cái lỗi tệp này tồn tại để chặn, chỉ đổi nguyên nhân. PostgreSQL ném
       `StringDataRightTruncation` ở 65 ký tự, SQLite thì nuốt — nên nếu không
       tự chặn thì lỗi chỉ lộ trên production.
    """
    from platform_core.models import Wakeup
    from platform_core.workflow.danh_thuc import duong_thi_hanh, hen_node

    sau = tuple((f"vong_lap_ten_rat_dai_so_{i}", i) for i in range(6))
    khoa = duong_thi_hanh("mot_node_ten_cung_rat_dai_de_day_qua_64", vong=sau)
    assert len(khoa) <= 64
    # Hai đường KHÁC nhau vẫn phải ra hai khoá khác nhau.
    khac = duong_thi_hanh("mot_node_ten_cung_rat_dai_de_day_qua_64",
                          vong=sau[:-1] + ((sau[-1][0], 99),))
    assert khoa != khac and len(khac) <= 64

    han = _han()
    hen_node(db, run_id="r1", node_id="mot_node_ten_cung_rat_dai_de_day_qua_64",
             kind="delay", due_at=han, vong=sau)
    hen_node(db, run_id="r1", node_id="mot_node_ten_cung_rat_dai_de_day_qua_64",
             kind="delay", due_at=han, vong=sau[:-1] + ((sau[-1][0], 99),))
    db.flush()
    assert db.query(Wakeup).filter_by(run_id="r1", kind="delay").count() == 2


def test_chi_so_am_hay_ten_vong_rong_bi_tu_choi():
    """Khoá là một bất biến; xây nó từ rác thì nó không còn chặn gì."""
    from platform_core.workflow.danh_thuc import duong_thi_hanh

    for xau in ((("", 0),), (("f1", -1),), (("f/1", 0),), (("f:1", 0),)):
        with pytest.raises(ValueError):
            duong_thi_hanh("n1", vong=xau)
