"""Hạn chờ CỘNG DỒN (neo `run.created_at`) và bộ quét hết hạn bằng KEYSET.

## T5 — vì sao neo vào `run.created_at`

Một hạn tính từ *lúc mở điểm chờ* cộng dồn được vô hạn: mười `core.delay` nối
tiếp, mỗi cái "tối đa 7 ngày", là **70 ngày** — và suốt 70 ngày ấy khoản giữ
chỗ credit của run vẫn treo (`tien.giu_cho_run`: MỘT khoản mỗi run). Không ai
khai ra con số 70 ngày; nó chỉ **xuất hiện**.

⚠️ Phép `test_doi_chung_neo_vao_BAY_GIO_thi_KHONG_chan_duoc_gi` là đối chứng:
   nó cho thấy cách neo-vào-"bây giờ" trả về **cùng một hạn** cho một run vừa
   tạo và một run đã chạy 19 giờ — tức không chặn được gì.

## T6 — vì sao KEYSET, không `OFFSET`

Báo cáo p3b (`docs/superpowers/reports/p3b-do-tai/report.md`) vừa đo đúng lớp
lỗi này ở `foreach`: **127 000 hàng đọc** cho `N=1000` vì mỗi tick đọc lại cả
tập. Và bài học đo lường đi kèm: **số câu SQL gần như không đổi theo N**, nên
một phép kiểm đếm *câu* sẽ báo "không có vấn đề" và sai. Ở đây phép kiểm đếm
**hàng trả về mỗi trang** và chốt rằng nó là `gioi_han`, không phải tổng số
hàng quá hạn.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

from datetime import datetime, timedelta, timezone

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def _gio(n: float) -> timedelta:
    return timedelta(hours=n)


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class _Run:
    """Run giả — `han_cho` chỉ đọc `created_at`, và nói ra điều đó."""

    def __init__(self, created_at):
        self.created_at = created_at


# ── T5: hạn CỘNG DỒN ────────────────────────────────────────────────────────

def test_khong_dat_han_rieng_van_co_han_CHUNG():
    """"Không hạn" ở mức node **không** có nghĩa "không hạn" ở mức run — cái
    thứ hai là cái giữ tiền."""
    from platform_core.workflow import han_cho

    run = _Run(_bay_gio())
    assert han_cho.han_cho(run) is not None
    assert han_cho.han_cho(run) == han_cho.tran_cua_run(run)


def test_han_rieng_NGAN_HON_thi_thang():
    from platform_core.workflow import han_cho

    run = _Run(_bay_gio())
    han = han_cho.han_cho(run, giay=60)
    assert han < han_cho.tran_cua_run(run)
    assert timedelta(seconds=55) <= (han - _bay_gio()) <= timedelta(seconds=65)


def test_han_rieng_DAI_HON_bi_KEP_xuong_moc_chung():
    from platform_core.workflow import han_cho

    run = _Run(_bay_gio())
    assert han_cho.han_cho(run, giay=400 * 3600) == han_cho.tran_cua_run(run)


def test_RUN_DA_CHAY_LAU_thi_cua_so_con_lai_NGAN_DI():
    """⭐ Đây là chữ "CỘNG DỒN": chuỗi `delay` thứ ba không được bắt đầu đếm lại
    từ đầu. Run đã sống 19 giờ thì còn đúng 1 giờ cho MỌI điểm chờ còn lại."""
    from platform_core.workflow import han_cho

    moi = _Run(_bay_gio())
    cu = _Run(_bay_gio() - _gio(19))
    con_lai_moi = han_cho.han_cho(moi, giay=10 * 3600) - _bay_gio()
    con_lai_cu = han_cho.han_cho(cu, giay=10 * 3600) - _bay_gio()
    assert con_lai_cu < con_lai_moi
    assert _gio(0.9) <= con_lai_cu <= _gio(1.1), con_lai_cu


def test_doi_chung_neo_vao_BAY_GIO_thi_KHONG_chan_duoc_gi():
    """⛔ Cách SAI — đối chứng. Neo vào "bây giờ" cho **cùng một** hạn cho một
    run vừa tạo và một run đã chạy 19 giờ, nên nó không chặn được chuỗi nào."""
    def han_sai(run, *, giay):
        return _bay_gio() + timedelta(seconds=giay)

    moi = _Run(_bay_gio())
    cu = _Run(_bay_gio() - _gio(19))
    assert (han_sai(moi, giay=3600).replace(microsecond=0)
            == han_sai(cu, giay=3600).replace(microsecond=0))


def test_che_do_het_han_ngoai_tap_bi_NEM(db):
    from platform_core.workflow import han_cho

    assert han_cho.kiem_che_do("route") == "route"
    with pytest.raises(han_cho.LoiHanCho):
        han_cho.kiem_che_do("coi_nhu_xong")
    # Mặc định theo loại — spec §5.7.
    assert han_cho.che_do_mac_dinh("HUMAN") == "reject"
    assert han_cho.che_do_mac_dinh("WEBHOOK") == "fail"


def test_tran_cong_don_KHONG_VUOT_TTL_cua_run():
    """⛔ Hứa một hạn mà TTL của run cắt trước là hứa suông: node sẽ chết vì
    `TIMED_OUT` của cả run, không vì `che_do_het_han` người soạn đã chọn."""
    from platform_core.workflow import han_cho
    from platform_core.workflow.dong_co import TRAN_RUN

    run = _Run(_bay_gio())
    assert han_cho.tran_cua_run(run) - run.created_at <= TRAN_RUN


# ── T6: quét hết hạn bằng KEYSET ───────────────────────────────────────────

def _diem_cho(db, n: int, *, qua_han: int, tu: int = 0):
    """`n` điểm chờ PENDING, hết hạn cách đây `qua_han` giây."""
    from platform_core.workflow import cho_doi

    luc = _bay_gio() - timedelta(seconds=qua_han)
    ra = []
    for i in range(tu, tu + n):
        wp = cho_doi.tao_waitpoint(db, run_id=f"r{i}", owner_id="u1",
                                   kind="WEBHOOK")
        # Cùng MỘT mốc cho tất cả: đó chính là ca mà con trỏ chỉ-có-thời-gian
        # hỏng (bỏ sót hoặc lặp vô hạn).
        wp.het_han_luc = luc
        ra.append(wp)
    db.flush()
    return ra


def test_keyset_doc_DUNG_gioi_han_hang_moi_trang(db):
    """⛔ Phép này đếm **HÀNG**, không đếm **CÂU SQL** (bài học p3b)."""
    from platform_core.workflow import cho_doi

    _diem_cho(db, 50, qua_han=10)
    trang = cho_doi.het_han_den_han(db, gioi_han=7)
    assert len(trang) == 7, "mot trang phai la `gioi_han` hang, khong phai 50"


def test_keyset_di_het_bang_KHONG_SOT_KHONG_LAP(db):
    """Cả 50 hàng có **cùng** `het_han_luc` — ca mà một con trỏ chỉ mang thời
    gian sẽ bỏ sót 49 hàng hoặc lặp vô hạn một hàng."""
    from platform_core.workflow import cho_doi

    goc = {w.id for w in _diem_cho(db, 50, qua_han=10)}
    thay: list[str] = []
    con_tro = None
    for _ in range(20):
        trang = cho_doi.het_han_den_han(db, con_tro=con_tro, gioi_han=7)
        if not trang:
            break
        thay.extend(w.id for w in trang)
        con_tro = (trang[-1].het_han_luc, trang[-1].id)
    assert len(thay) == len(set(thay)), "co hang bi LAP"
    assert set(thay) == goc, "co hang bi SOT"


def test_chua_qua_han_va_DA_DONG_deu_khong_lot_vao(db):
    from platform_core.workflow import cho_doi

    _diem_cho(db, 3, qua_han=10)
    chua = _diem_cho(db, 4, qua_han=-3600, tu=100)      # hạn ở TƯƠNG LAI
    da_dong = _diem_cho(db, 2, qua_han=10, tu=200)
    for wp in da_dong:
        wp.status = "COMPLETED"
    db.flush()
    ra = {w.id for w in cho_doi.het_han_den_han(db, gioi_han=100)}
    assert len(ra) == 3
    assert not (ra & {w.id for w in chua}), "han o tuong lai khong duoc lot"
    assert not (ra & {w.id for w in da_dong}), "diem cho da dong khong con cho"


def test_quet_het_han_DANH_THUC_run_va_luy_dang(db):
    """Lưới an toàn: hàng `wakeup` mất ⇒ bộ quét phải hẹn lại, và gọi hai lần
    không được đẻ hai hàng (`uq_wakeup_khu_trung`)."""
    from platform_core.models import Wakeup
    from platform_core.workflow import noi_lai

    _diem_cho(db, 5, qua_han=10)
    luc = _bay_gio()
    assert noi_lai.quet_het_han(db, moc=luc, gioi_han=2) == 5
    assert db.query(Wakeup).filter_by(kind="het_han").count() == 5
    assert noi_lai.quet_het_han(db, moc=luc, gioi_han=2) == 5
    assert db.query(Wakeup).filter_by(kind="het_han").count() == 5, \
        "goi lai khong duoc de them hang"


def test_quet_het_han_KHONG_tu_quyet_dinh_che_do(db):
    """⛔ Bộ quét chỉ ĐÁNH THỨC. Diễn giải `che_do_het_han` sống ở
    `nut_loi/cho.tiep_mot` — hai nơi cùng quyết định là hai nơi trả lời khác
    nhau."""
    from platform_core.workflow import noi_lai

    wps = _diem_cho(db, 2, qua_han=10)
    noi_lai.quet_het_han(db)
    for wp in wps:
        assert wp.status == "PENDING", "bo quet khong duoc DONG diem cho"
