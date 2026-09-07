"""
test_809 — duyệt bền. (H44 P04)

`02_HOP_DONG.md` §6 đòi hai mệnh đề, và cả hai đều nằm ở đây:

  - `UNIQUE(step_id)` **thật sự** chặn duyệt hai lần — kiểm bằng **đột biến**:
    gỡ ràng buộc ra thì phép kiểm phải ĐỎ. Một phép kiểm chỉ gọi hàm hai lần
    rồi thấy một hàng vẫn xanh khi ràng buộc biến mất, vì hàm tự kiểm trước.
  - Từ chối duyệt ⇒ **model biết**, và run không chết.

Mệnh đề thứ ba, không có trong hợp đồng nhưng đắt hơn cả hai: người dùng sửa
đối số rồi bấm đồng ý mà hệ thống chạy bản **gốc** là chạy một việc không ai
duyệt — và nó tiêu tiền thật.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.chatltt.services import duyet as D


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


U = "u-chu"
KHACH = "u-nguoi-la"


def _xin(db, step="st_1", user=U, gia=12, doi_so=None):
    return D.xin_duyet(db, user_id=user, run_id="run_1", step_id=step,
                       tool_name="image.ltt",
                       doi_so=doi_so if doi_so is not None else {"prompt": "meo"},
                       policy_class="PAID", bao_gia_credit=gia,
                       phien_ban_gia="ltt-vlm-2026-08-22", bam_trung="bam1")


# ── 1. Mở phiếu ────────────────────────────────────────────────────────────

def test_phieu_moi_o_trang_thai_CHO(db):
    p = _xin(db)
    assert p.quyet_dinh == D.CHO
    assert p.id.startswith("ap_")
    assert p.bao_gia_credit == 12 and p.phien_ban_gia


def test_xin_HAI_LAN_cho_mot_buoc_tra_ve_DUNG_PHIEU_CU(db):
    """⭐ Trả phiếu cũ chứ không ném. Một lần gửi lại vì mạng chập không phải
    lỗi của ai, và biến nó thành lỗi buộc mọi bên gọi viết mã bắt lỗi cho một
    trường hợp bình thường."""
    a = _xin(db)
    b = _xin(db, gia=999)
    assert a.id == b.id
    assert b.bao_gia_credit == 12, "gia moi KHONG duoc de len phieu da mo"
    from apps.chatltt.tables import ChatlttApproval
    assert db.query(ChatlttApproval).count() == 1


def test_RANG_BUOC_CSDL_chan_hai_phieu_cho_mot_buoc(db):
    """🔴 Đột biến của hợp đồng §6: nếu `ux_chatltt_approval_step` biến mất thì
    phép kiểm này phải ĐỎ.

    Nên nó **đi vòng qua** `xin_duyet` và chèn thẳng hàng thứ hai. Gọi hàm hai
    lần chỉ chứng minh hàm tự kiểm — không chứng minh ràng buộc còn đó.
    """
    from sqlalchemy.exc import IntegrityError

    from apps.chatltt.tables import ChatlttApproval
    p = _xin(db)
    db.add(ChatlttApproval(
        step_id=p.step_id, run_id=p.run_id, user_id=p.user_id,
        tool_name="khac", doi_so={}, policy_class="PAID",
        idempotency_key="khoa-khac-han"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_RANG_BUOC_CSDL_chan_trung_khoa_idem(db):
    from sqlalchemy.exc import IntegrityError

    from apps.chatltt.tables import ChatlttApproval
    p = _xin(db)
    db.add(ChatlttApproval(
        step_id="st_KHAC", run_id=p.run_id, user_id=p.user_id,
        tool_name="khac", doi_so={}, policy_class="PAID",
        idempotency_key=p.idempotency_key))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_khoa_idem_DAN_XUAT_khong_do_client_nghi_ra(db):
    """⛔ Một khoá do client sinh là một khoá client có thể sinh khác đi khi gửi
    lại — và lúc ấy ràng buộc UNIQUE không chặn gì cả."""
    a = D.khoa_idem(run_id="r", step_id="s", bam_trung="b")
    assert a == D.khoa_idem(run_id="r", step_id="s", bam_trung="b")
    assert a != D.khoa_idem(run_id="r", step_id="s", bam_trung="b2")
    assert len(a) == 64


def test_bam_khong_lan_giua_cac_truong(db):
    """Nối chuỗi bằng dấu phân cách thường ⇒ `("ab","c")` và `("a","bc")` cùng
    băm. Ở đây dùng `\\x1f`, ký tự không xuất hiện trong id."""
    assert (D.khoa_idem(run_id="ab", step_id="c", bam_trung="x")
            != D.khoa_idem(run_id="a", step_id="bc", bam_trung="x"))


# ── 2. Quyết định ──────────────────────────────────────────────────────────

def test_duyet_ghi_ai_va_luc_nao(db):
    p = _xin(db)
    q = D.duyet(db, user_id=U, approval_id=p.id, quyet_boi="u-chu")
    assert q.quyet_dinh == D.DUYET
    assert q.quyet_boi == "u-chu" and q.quyet_luc is not None


def test_tu_choi_ghi_lai(db):
    q = D.tu_choi(db, user_id=U, approval_id=_xin(db).id)
    assert q.quyet_dinh == D.TU_CHOI


def test_DUYET_ROI_khong_lat_lai_duoc(db):
    """🔴 Không có đường nào từ `duyet` về `tu_choi`. Một phiếu lật lại được là
    một phiếu không chứng minh được gì khi có tranh chấp về tiền."""
    p = _xin(db)
    D.duyet(db, user_id=U, approval_id=p.id)
    with pytest.raises(D.DaQuyetRoi):
        D.tu_choi(db, user_id=U, approval_id=p.id)
    with pytest.raises(D.DaQuyetRoi):
        D.duyet(db, user_id=U, approval_id=p.id)


def test_duyet_HAI_LAN_khong_tao_hai_quyet_dinh(db):
    p = _xin(db)
    D.duyet(db, user_id=U, approval_id=p.id, quyet_boi="lan1")
    with pytest.raises(D.DaQuyetRoi):
        D.duyet(db, user_id=U, approval_id=p.id, quyet_boi="lan2")
    db.refresh(p)
    assert p.quyet_boi == "lan1", "lan hai KHONG duoc de len lan mot"


def test_nguoi_KHAC_khong_duyet_duoc_phieu_cua_toi(db):
    """⛔ Không phải `PermissionError` — `KhongTimThay`. Nói "không có quyền"
    là xác nhận phiếu ấy tồn tại (cùng luật `hoi_thoai.py` của V1)."""
    p = _xin(db)
    with pytest.raises(D.KhongTimThay):
        D.duyet(db, user_id=KHACH, approval_id=p.id)
    db.refresh(p)
    assert p.quyet_dinh == D.CHO


def test_phieu_khong_co_that(db):
    with pytest.raises(D.KhongTimThay):
        D.duyet(db, user_id=U, approval_id="ap_khong_ton_tai")


# ── 3. Đối số đã sửa — mệnh đề đắt nhất ────────────────────────────────────

def test_nguoi_dung_SUA_doi_so_thi_chay_BAN_DA_SUA(db):
    """🔴 Chạy bản gốc sau khi người dùng đã sửa là chạy một việc **không ai
    duyệt** — và nó tiêu tiền thật."""
    p = _xin(db, doi_so={"prompt": "meo", "so_luong": 4})
    q = D.duyet(db, user_id=U, approval_id=p.id,
                doi_so_da_sua={"prompt": "meo", "so_luong": 1})
    assert D.doi_so_cuoi(q) == {"prompt": "meo", "so_luong": 1}
    assert q.doi_so == {"prompt": "meo", "so_luong": 4}, "ban GOC phai con de tra"


def test_khong_sua_thi_doi_so_cuoi_la_ban_goc(db):
    q = D.duyet(db, user_id=U, approval_id=_xin(db).id)
    assert D.doi_so_cuoi(q) == {"prompt": "meo"}


def test_doi_so_cuoi_tra_BAN_SAO(db):
    """Trả tham chiếu thì bên gọi sửa vào đó là sửa vào bằng chứng."""
    q = D.duyet(db, user_id=U, approval_id=_xin(db).id)
    D.doi_so_cuoi(q)["prompt"] = "cho"
    assert q.doi_so["prompt"] == "meo"


# ── 4. Hết hạn ─────────────────────────────────────────────────────────────

def _lui(db, p, phut):
    p.created_at = datetime.now(timezone.utc) - timedelta(minutes=phut)
    db.flush()


def test_phieu_qua_han_KHONG_duyet_duoc(db):
    """⛔ Phiếu mang **báo giá**, và báo giá gắn với `phien_ban_gia` lúc hỏi.
    Duyệt một phiếu cũ là đồng ý với một cái giá có thể đã đổi."""
    p = _xin(db)
    _lui(db, p, D.HAN_CHO_PHUT + 1)
    with pytest.raises(D.DaQuyetRoi):
        D.duyet(db, user_id=U, approval_id=p.id)
    db.refresh(p)
    assert p.quyet_dinh == D.HET_HAN, "phai TU DONG dong lai, khong de treo o CHO"


def test_phieu_qua_han_van_TU_CHOI_duoc(db):
    """Kết quả như nhau, nên đừng bắt người dùng gặp lỗi để nói 'không'."""
    p = _xin(db)
    _lui(db, p, D.HAN_CHO_PHUT + 1)
    assert D.tu_choi(db, user_id=U, approval_id=p.id).quyet_dinh == D.TU_CHOI


def test_phieu_TRONG_han_van_duyet_binh_thuong(db):
    p = _xin(db)
    _lui(db, p, D.HAN_CHO_PHUT - 1)
    assert D.duyet(db, user_id=U, approval_id=p.id).quyet_dinh == D.DUYET


def test_quet_het_han_dong_dung_nhung_phieu_qua_han(db):
    a, b = _xin(db, step="st_a"), _xin(db, step="st_b")
    _lui(db, a, D.HAN_CHO_PHUT + 5)
    assert D.quet_het_han(db) == 1
    db.refresh(a), db.refresh(b)
    assert a.quyet_dinh == D.HET_HAN and b.quyet_dinh == D.CHO


def test_quet_KHONG_cham_phieu_da_quyet(db):
    p = _xin(db)
    D.duyet(db, user_id=U, approval_id=p.id)
    _lui(db, p, D.HAN_CHO_PHUT + 99)
    assert D.quet_het_han(db) == 0
    db.refresh(p)
    assert p.quyet_dinh == D.DUYET


# ── 5. Từ chối KHÔNG giết run ──────────────────────────────────────────────

def test_tu_choi_thanh_KetQua_model_doc_duoc(db):
    """⛔ `AWAITING_APPROVAL → TOOL_RESULT_READY` (§1). Người dùng nói "không"
    là một **câu trả lời**, không phải một lượt chết giữa chừng."""
    q = D.tu_choi(db, user_id=U, approval_id=_xin(db).id)
    kq = D.ket_qua_cho_model(q)
    assert kq.ok is False and kq.ma_loi == "tu_choi"
    chu = kq.cho_model()
    assert "TU CHOI" in chu
    assert "Dung goi lai" in chu, "phai noi model DUNG lam gi tiep, khong chi bao that bai"


def test_het_han_cung_thanh_KetQua(db):
    p = _xin(db)
    _lui(db, p, D.HAN_CHO_PHUT + 1)
    D.quet_het_han(db)
    db.refresh(p)
    assert D.ket_qua_cho_model(p).ma_loi == "het_han"


def test_phieu_CON_CHO_chua_co_ket_qua_cho_model(db):
    with pytest.raises(ValueError):
        D.ket_qua_cho_model(_xin(db))


def test_phieu_DA_DUYET_khong_co_ket_qua_tu_choi(db):
    """Duyệt rồi thì kết quả là kết quả của **tool**, không phải của phiếu."""
    q = D.duyet(db, user_id=U, approval_id=_xin(db).id)
    with pytest.raises(ValueError):
        D.ket_qua_cho_model(q)


# ── 6. Sự kiện + dựng lại sau reload ───────────────────────────────────────

def test_su_kien_can_duyet_du_de_ve_nut(db):
    sk = D.su_kien_can_duyet(_xin(db))
    assert sk["type"] == "approval.required"
    for k in ("approval_id", "tool_name", "doi_so", "credit", "policy_class"):
        assert k in sk
    assert sk["credit"] == 12


def test_su_kien_quyet_dung_ten_theo_tung_ket_cuc(db):
    a = D.duyet(db, user_id=U, approval_id=_xin(db, step="s1").id)
    b = D.tu_choi(db, user_id=U, approval_id=_xin(db, step="s2").id)
    assert D.su_kien_quyet(a)["type"] == "approval.granted"
    assert D.su_kien_quyet(b)["type"] == "approval.denied"


def test_su_kien_granted_mang_doi_so_da_sua(db):
    """Giao diện phải vẽ lại đúng thứ sắp chạy, không phải thứ đã đề nghị."""
    q = D.duyet(db, user_id=U, approval_id=_xin(db).id,
                doi_so_da_sua={"prompt": "cho"})
    assert D.su_kien_quyet(q)["doi_so_da_sua"] == {"prompt": "cho"}


def test_dang_cho_dung_lai_duoc_sau_reload(db):
    _xin(db, step="s1")
    D.duyet(db, user_id=U, approval_id=_xin(db, step="s2").id)
    ds = D.dang_cho(db, user_id=U)
    assert len(ds) == 1 and ds[0]["type"] == "approval.required"


def test_dang_cho_BO_QUA_phieu_da_qua_han(db):
    """Một phiếu quá hạn mà giao diện vẫn vẽ nút là mời người dùng bấm vào một
    thứ sẽ báo lỗi."""
    p = _xin(db)
    _lui(db, p, D.HAN_CHO_PHUT + 1)
    assert D.dang_cho(db, user_id=U) == []


def test_dang_cho_khong_ro_ri_sang_nguoi_khac(db):
    _xin(db)
    assert D.dang_cho(db, user_id=KHACH) == []
