"""test_1253 — cong NHIEM. Mot phep do bi nhiem phai bi LOAI, khong duoc dien giai.

🔴 BON TIN HIEU NHIEM DUOI DAY DEU LA CHUYEN DA XAY RA NGAY 13/09/2026, khong
   phai gia dinh phong xa:

   1. **Production doi ban giua luot do.** Mot phien khac deploy dung luc toi do
      bao hoa; ca sau job chet cung mot khac o giay 14,15. Toi suyt ghi thanh
      *"6 job dong thoi lam sap he"*. Phai vut ca luot.
   2. **Nen khong sach.** Sau xac lease cua luot truoc con giu TOAN BO suc chua;
      bat dau do luc ay la do mot he da day san.
   3. **Mot so mu giua chung.** `requests_processing` tra `-1` suot mot luot 16
      kich ban vi sai cong + thieu tien to. `-1` trong y het `0`.
   4. **Tai khoan la xuat hien.** Mot phien khac goi vao production giua luot do
      thi con so "ai giu bao nhieu suat" khong con thuoc kich ban nao.

⛔ Voi ca bon, cau tra loi dung la **`dat = None`** (NHIEU), khong phai `False`.
   `False` noi *"he hong"*; `None` noi *"ta chua biet"*. Lan tron hai dieu ay la
   cach mot bo do sinh ra ket luan trong rat chac chan va hoan toan sai.
"""
from tools.nghiem_thu_van_hanh import chay


def _so(ten, gia_tri, doc_duoc=True):
    from tools.nghiem_thu_van_hanh.soi import MauSo
    return MauSo(ten, gia_tri, doc_duoc)


def _chup(commit="abc123", lease=0, mu=False):
    ds = [_so("lease", lease), _so("jobs", 0), _so("credit", 0),
          _so("residency", 0), _so("http", commit), _so("slot", 0, not mu)]
    return {m.ten: m for m in ds}


# ── bon tin hieu nhiem ────────────────────────────────────────────────────
def test_nhiem_khi_PRODUCTION_DOI_BAN_giua_luot():
    """🔴 Dung chuyen 13/09: mot phien khac deploy giua luot do bao hoa."""
    co, ly_do = chay.co_nhiem(_chup(commit="aaa"), _chup(commit="bbb"))
    assert co is True
    assert "commit" in ly_do.lower(), ly_do


def test_nhiem_khi_NEN_KHONG_SACH_luc_bat_dau():
    co, ly_do = chay.co_nhiem(_chup(lease=6), _chup(lease=0))
    assert co is True
    assert "nen" in ly_do.lower() or "lease" in ly_do.lower(), ly_do


def test_nhiem_khi_mot_SO_MU():
    co, ly_do = chay.co_nhiem(_chup(), _chup(mu=True))
    assert co is True
    assert "mu" in ly_do.lower() or "slot" in ly_do.lower(), ly_do


def test_KHONG_nhiem_khi_moi_thu_binh_thuong():
    co, ly_do = chay.co_nhiem(_chup(), _chup())
    assert co is False, ly_do


# ── ket qua bi nhiem phai la None, KHONG phai False ───────────────────────
def test_luot_bi_NHIEM_tra_None_chu_khong_tra_False():
    """⛔ `False` noi 'he hong'. `None` noi 'ta chua biet'. Lan tron hai dieu ay
       la cach mot bo do sinh ra ket luan sai ma rat chac chan.
    """
    kq = chay.KetQuaKichBan(ma="J4", dat=None, nhiem=True, mau=[],
                            truoc={}, sau={}, ly_do_nhiem="deploy giua luot")
    assert kq.dat is None
    assert kq.nhiem is True
    assert kq.ly_do_nhiem


def test_bang_tong_ket_DEM_RIENG_luot_nhiem():
    """Luot nhiem khong duoc tinh vao ti le dat — ke ca theo chieu xau."""
    ds = [
        chay.KetQuaKichBan("J1", True, False, [], {}, {}),
        chay.KetQuaKichBan("J2", False, False, [], {}, {}),
        chay.KetQuaKichBan("J4", None, True, [], {}, {}, "deploy giua luot"),
    ]
    t = chay.tong_ket(ds)
    assert t["dat"] == 1
    assert t["truot"] == 1
    assert t["nhiem"] == 1
    assert t["tong_ket_luan_duoc"] == 2, (
        "luot nhiem dang bi tinh vao mau so — ti le 'dat' se noi sai")


# ── ky vong khai ra ma KHONG do duoc ──────────────────────────────────────
def test_ky_vong_KHONG_DO_DUOC_thi_KHONG_BAO_GIO_la_dat():
    """🔴 Ve nay sinh ra tu mot cuoc ra soat 13/09: **26/43 ky vong (60%) chua
       bao gio duoc kiem**, va bo do van bao "dat".

    Nang nhat: `J4` bao dat cho kich ban BAO HOA ma chua tung xac minh sau suat
    co bi giu khong — no chi so `chay_ngay` roi bo qua `dinh_lease: 6`.

    ⛔ Mot bang noi "dat" cho nhung thu no khong kiem con TE HON khong co bang:
       no mua su yen tam bang mot loi khong co co so.
    """
    from tools.nghiem_thu_van_hanh.kich_ban import KichBan

    kb = KichBan("TT", "thu", "stream", (("ltt-3.8", 1),),
                 {"chay_ngay": 1, "dinh_lease": 6})
    ket, thieu = chay._cham(kb, {"chay_ngay": 1})      # thieu `dinh_lease`
    assert ket is None, "khong do duoc `dinh_lease` ma van bao dat"
    assert thieu == ["dinh_lease"]


def test_do_DU_ky_vong_thi_moi_duoc_bao_dat():
    from tools.nghiem_thu_van_hanh.kich_ban import KichBan

    kb = KichBan("TT", "thu", "stream", (("ltt-3.8", 1),),
                 {"chay_ngay": 1, "dinh_lease": 6})
    ket, thieu = chay._cham(kb, {"chay_ngay": 1, "dinh_lease": 6})
    assert ket is True and thieu == []


def test_bac_duoc_mot_ky_vong_thi_VAN_la_TRUOT_du_con_khoa_thieu():
    """Thay sai roi thi khong can do not — "hong" la mot phat hien chac chan."""
    from tools.nghiem_thu_van_hanh.kich_ban import KichBan

    kb = KichBan("TT", "thu", "stream", (("ltt-3.8", 1),),
                 {"chay_ngay": 1, "dinh_lease": 6})
    ket, _ = chay._cham(kb, {"chay_ngay": 99})
    assert ket is False
