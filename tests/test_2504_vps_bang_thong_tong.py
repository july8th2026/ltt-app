"""V2/Mục 4 (23/09/2026) — cổng vào là OVH 1 TB/tháng thật, không phải Vultr 2 TB,
và cần một lớp bảo vệ THEO TỔNG bên cạnh lớp bảo vệ theo từng khách đã có.

Ba việc được test ở đây:

1. `bang_thong.ngan_sach_hua_gb` — ngân sách bán chồng thật, tính từ trần đo
   được trừ nền production trừ dự trữ, nhân hệ số bán chồng.
2. `bao_tri._chon_may_can_ham_theo_tong` — thuật toán chọn máy để hãm, thuần
   không đụng DB/router, dễ kiểm nhất.
3. `bao_tri._dong_bo_bang_thong(db, profile)` — lớp tổng nối vào đúng một
   quyết định mỗi máy, và **không bao giờ** đụng tới VM100-107 vì chúng không
   phải `VpsInstance`.
"""
from __future__ import annotations

import pytest

from apps.vps import bang_thong, bao_tri

GB = 1024 ** 3


# ── 1. Ngân sách bán chồng thật ──────────────────────────────────────────────

def test_tran_cong_vao_la_OVH_khong_phai_vultr():
    assert bang_thong.TRAN_CONG_VAO_GB == 1024
    assert bang_thong.NEN_PRODUCTION_GB == 512
    assert bang_thong.TY_LE_DU_TRU == 0.15
    assert bang_thong.HE_SO_BAN_CHONG == 2.5


def test_ngan_sach_hua_gb_mac_dinh_la_895():
    """(1.024 - 512 - 153,6) = 358,4 -> 358 -> x2,5 = 895. Số chốt của mục 4
    trong đặc tả 2026-09-23-vps-ban-that-design.md."""
    assert bang_thong.ngan_sach_hua_gb() == 895


def test_ngan_sach_hua_gb_khong_am_khi_nen_vuot_tran():
    assert bang_thong.ngan_sach_hua_gb(tran_gb=1024, nen_gb=2000) == 0
    assert bang_thong.ngan_sach_hua_gb(tran_gb=0, nen_gb=0) == 0


def test_ngan_sach_hua_gb_nhan_tham_so_truc_tiep():
    # tran=1000, nen=400 -> du_tru=150 -> that=450 -> *2.5=1125
    assert bang_thong.ngan_sach_hua_gb(tran_gb=1000, nen_gb=400) == 1125


def test_doc_nen_gb_moi_truong_doc_bien(monkeypatch):
    monkeypatch.setenv("LTT_VPS_NEN_GB", "600")
    assert bang_thong._doc_nen_gb_moi_truong() == 600


def test_doc_nen_gb_moi_truong_gia_tri_hong_thi_dung_mac_dinh(monkeypatch):
    monkeypatch.setenv("LTT_VPS_NEN_GB", "khong-phai-so")
    assert bang_thong._doc_nen_gb_moi_truong() == bang_thong.NEN_PRODUCTION_GB


def test_dem_mot_chieu_thi_nen_con_mot_nua(monkeypatch):
    """`LTT_VPS_DEM_HAI_CHIEU=false` nghĩa là OVH chỉ đếm chiều ra — nền chỉ
    còn tính một nửa, vì nửa kia (chiều vào) không còn tính vào hạn mức chung."""
    monkeypatch.delenv("LTT_VPS_NEN_GB", raising=False)
    monkeypatch.setenv("LTT_VPS_DEM_HAI_CHIEU", "false")
    assert bang_thong._doc_nen_gb_moi_truong() == bang_thong.NEN_PRODUCTION_GB // 2


def test_gia_ban_giu_nguyen_bang_thong_ha_theo_OVH():
    from apps.vps.cost import PLANS

    han_muc = {p.id: p.bang_thong_gb for p in PLANS}
    gia = {p.id: p.gia_thang_vnd for p in PLANS}
    assert han_muc == {"vps-nho": 100, "vps-vua": 150, "vps-lon": 250}
    assert gia == {"vps-nho": 159_000, "vps-vua": 209_000, "vps-lon": 329_000}


def test_dieu_khoan_noi_ro_ham_theo_tong_truoc_han_muc_rieng():
    """V4 mục 4: 'khi tổng lưu lượng nền tảng chạm ngưỡng, máy dùng nhiều nhất
    có thể bị hãm tốc TRƯỚC khi chạm hạn mức riêng của nó.' Không viết vào
    điều khoản là bán một thứ khác với thứ giao."""
    from apps.vps import dieu_khoan

    noi_dung = dieu_khoan.NOI_DUNG()
    khoi_5 = next(m for m in noi_dung if m["so"] == "5")
    van_ban = " ".join(
        item for kieu, payload in khoi_5["khoi"]
        for item in (payload if isinstance(payload, list) else [payload]))
    assert "nhiều nhất" in van_ban
    assert "trước" in van_ban.lower()


# ── 2. Thuật toán chọn máy để hãm — thuần, không DB/router ──────────────────

class _MayGia:
    def __init__(self, id_, bang_thong_byte):
        self.id = id_
        self.bang_thong_byte = bang_thong_byte


def test_chon_may_khong_ham_ai_khi_du_phong_da_lot_tran():
    """Tổng tháng-tới-giờ trên 80% nhưng tốc độ hiện tại chiếu ra cuối tháng
    vẫn dưới trần — chưa cần hãm ai."""
    ham = bao_tri._chon_may_can_ham_theo_tong(
        [_MayGia("a", 10 * GB)], tong_thang_byte=830 * GB, tran_byte=1024 * GB,
        ngay_da_qua=29, so_ngay_thang=30)
    assert ham == set()


def test_chon_may_ham_nguoi_dung_nhieu_nhat_truoc():
    """Ba máy, dùng nhiều khác biệt hẳn. Dự phóng ban đầu vượt trần rõ ràng —
    phải hãm ít nhất máy đứng đầu, và máy đứng đầu phải luôn nằm trong tập."""
    m1 = _MayGia("nhieu-nhat", 500 * GB)
    m2 = _MayGia("vua", 50 * GB)
    m3 = _MayGia("it", 5 * GB)
    ham = bao_tri._chon_may_can_ham_theo_tong(
        [m1, m2, m3], tong_thang_byte=900 * GB, tran_byte=1024 * GB,
        ngay_da_qua=5, so_ngay_thang=30)
    assert "nhieu-nhat" in ham


def test_chon_may_dung_lai_khi_du_phong_da_lot_tran():
    """Không hãm QUÁ số cần — hãm hết mọi máy khi chỉ cần hai máy là một hình
    phạt thừa cho bốn máy còn lại dùng ít."""
    nhieu = [_MayGia("m0", 400 * GB), _MayGia("m1", 300 * GB),
             _MayGia("m2", 50 * GB), _MayGia("m3", 20 * GB),
             _MayGia("m4", 10 * GB), _MayGia("m5", 5 * GB)]
    ham = bao_tri._chon_may_can_ham_theo_tong(
        nhieu, tong_thang_byte=800 * GB, tran_byte=1024 * GB,
        ngay_da_qua=10, so_ngay_thang=30)
    # phai hop ly: khong rong (co canh bao) nhung cung khong phai TOAN BO
    assert 0 < len(ham) < len(nhieu)
    assert ham == {"m0", "m1"}
    # nguoi dung nhieu nhat luon nam trong tap da chon
    assert "m0" in ham


def test_chon_may_khong_co_ai_de_ham_thi_tra_ve_tat_ca_da_xet():
    """Hết máy để hãm mà vẫn chưa đủ — trả về tất cả, không kẹt hay ném lỗi."""
    it = [_MayGia("a", 1 * GB), _MayGia("b", 1 * GB)]
    ham = bao_tri._chon_may_can_ham_theo_tong(
        it, tong_thang_byte=2000 * GB, tran_byte=1024 * GB,
        ngay_da_qua=1, so_ngay_thang=30)
    assert ham == {"a", "b"}


def test_chon_may_danh_sach_rong_tra_ve_rong():
    assert bao_tri._chon_may_can_ham_theo_tong(
        [], tong_thang_byte=2000 * GB, tran_byte=1024 * GB,
        ngay_da_qua=1, so_ngay_thang=30) == set()


# ── 3. Cộng dồn bộ đếm cổng vào vào network_config ───────────────────────────

class _ProfileGia:
    def __init__(self, network_config=None):
        self.id = "p-ovh"
        self.network_config = dict(network_config or {})


def _mot_thang(y=2026, m=9, d=15):
    from datetime import datetime, timezone
    return datetime(y, m, d, tzinfo=timezone.utc)


def test_cong_don_cong_vao_lan_dau_dat_moc_khong_cong_lich_su():
    """Bộ đếm NIC tích luỹ từ lúc khởi động máy — lần đầu tiên phải LẤY LÀM
    MỐC chứ không cộng cả lịch sử đó vào tháng này."""
    from apps.vps import bao_tri

    p = _ProfileGia()
    tt = bao_tri._cong_don_cong_vao(
        p, 900_000 * GB, 900_000 * GB, now=_mot_thang(), dem_hai_chieu=True)
    assert tt["tong_byte"] == 0
    assert p.network_config["cong_vao_bang_thong"]["tong_byte"] == 0


def test_cong_don_cong_vao_cong_don_lan_sau():
    from apps.vps import bao_tri

    p = _ProfileGia()
    bao_tri._cong_don_cong_vao(p, 10 * GB, 20 * GB, now=_mot_thang(d=1),
                               dem_hai_chieu=True)
    tt = bao_tri._cong_don_cong_vao(p, 13 * GB, 25 * GB, now=_mot_thang(d=2),
                                    dem_hai_chieu=True)
    assert tt["tong_byte"] == 3 * GB + 5 * GB


def test_cong_don_cong_vao_sang_thang_moi_dat_lai_ve_khong():
    from apps.vps import bao_tri

    p = _ProfileGia()
    bao_tri._cong_don_cong_vao(p, 10 * GB, 10 * GB, now=_mot_thang(m=9, d=30),
                               dem_hai_chieu=True)
    tt = bao_tri._cong_don_cong_vao(p, 999_999 * GB, 999_999 * GB,
                                    now=_mot_thang(m=10, d=1), dem_hai_chieu=True)
    assert tt["thang"] == "2026-10"
    assert tt["tong_byte"] == 0, "sang thang la mot MOC moi, khong cong lich su"


def test_cong_don_cong_vao_mot_chieu_bo_qua_rx():
    from apps.vps import bao_tri

    p = _ProfileGia()
    bao_tri._cong_don_cong_vao(p, 10 * GB, 10 * GB, now=_mot_thang(d=1),
                               dem_hai_chieu=False)
    tt = bao_tri._cong_don_cong_vao(p, 50 * GB, 15 * GB, now=_mot_thang(d=2),
                                    dem_hai_chieu=False)
    assert tt["tong_byte"] == 5 * GB, "chieu vao (rx) khong duoc tinh khi mot chieu"


# ── 4. Tích hợp qua _dong_bo_bang_thong(db, profile) ────────────────────────

class _May:
    def __init__(self, id_, *, plan_id="vps-lon", da_dung=0, ip="10.51.0.50"):
        self.id = id_
        self.plan_id = plan_id
        self.bang_thong_byte = da_dung
        self.bang_thong_moc_len = 0
        self.bang_thong_moc_xuong = 0
        self.bi_giam_toc = False
        self.ip_noi_bo = ip
        self.trang_thai = "dang_chay"


class _Db:
    def __init__(self, may):
        self.may = list(may)
        #: Ban ghi suc khoe ma vong bao tri ghi cho lop canh THEO TONG
        #: (`bao_tri.THANH_PHAN_BANG_THONG_TONG`, them 23/09/2026). Do gia lap
        #: nay phai NHAN duoc chung: mot lop bao ve ngung canh phai ghi lai
        #: duoc, va mot `_Db` khong co `add` se lam chinh duong do im lang.
        self.da_them = []

    def add(self, row):
        self.da_them.append(row)

    def flush(self):
        pass

    def execute(self, *a, **kw):
        class _Kq:
            def __init__(self, x):
                self._x = x

            def scalars(self):
                return self

            def __iter__(self):
                return iter(self._x)
        return _Kq(self.may)

    def commit(self):
        pass


class _RouterGia:
    def __init__(self, so_lieu=None, dang_ham=()):
        self.so_lieu = so_lieu or {}
        self.dang_ham = set(dang_ham)
        self.da_dat: list[tuple[str, bool]] = []

    def doc_bang_thong(self):
        return self.so_lieu

    def danh_sach_giam_toc(self):
        return set(self.dang_ham)

    def theo_doi_bang_thong(self, ip):
        pass

    def dat_giam_toc(self, ip, bat):
        self.da_dat.append((ip, bat))


@pytest.fixture()
def _khong_ghi_su_kien(monkeypatch):
    from apps.vps.services import billing
    monkeypatch.setattr(billing, "ghi_su_kien", lambda *a, **kw: None)


def _chay(monkeypatch, may_list, rt, *, bo_dem, profile=None,
          now=None, dem_hai_chieu="true"):
    from apps.vps import bao_tri, profiles
    from apps.vps.services import backend_factory

    monkeypatch.setattr(backend_factory, "router_backend", lambda _p: rt)
    monkeypatch.setattr(profiles, "pinned_profile", lambda db, may: None)
    monkeypatch.setattr(bao_tri, "_doc_cau_hinh_cong_vao", lambda: object())
    monkeypatch.setattr(bao_tri, "_doc_bo_dem_cong_vao", lambda dich: bo_dem)
    monkeypatch.setenv("LTT_VPS_DEM_HAI_CHIEU", dem_hai_chieu)
    p = profile if profile is not None else _ProfileGia()
    db = _Db(may_list)
    doi = bao_tri._dong_bo_bang_thong(db, p, now=now)
    return doi, db, p


def test_lop_tong_ham_them_may_duoi_han_muc_rieng_khi_cham_tran(
        monkeypatch, _khong_ghi_su_kien):
    """Máy dùng nhiều nhất CHƯA vượt hạn mức GÓI riêng của nó (vps-lon = 250 GB),
    nhưng tổng cổng vào đã sát trần OVH — lớp tổng phải hãm nó TRƯỚC khi nó tự
    chạm hạn mức riêng, đúng câu vừa thêm vào điều khoản."""
    m_nhieu = _May("nhieu", plan_id="vps-lon", da_dung=200 * GB, ip="10.51.0.60")
    m_it = _May("it", plan_id="vps-nho", da_dung=1 * GB, ip="10.51.0.61")
    rt = _RouterGia({"10.51.0.60": (0, 0), "10.51.0.61": (0, 0)})

    # network_config da co san 860 GiB tich luy thang nay (tren 80% x 1024 =
    # 819,2), ngay 25/30 -> con 5 ngay. Toc do chung 34,4 GB/ngay; ham rieng
    # "nhieu" (rate 8 GB/ngay) da du de du phong lot tran, khong can dung
    # toi "it" (rate 0,04 GB/ngay).
    profile = _ProfileGia({"cong_vao_bang_thong": {
        "thang": "2026-09", "tong_byte": 860 * GB, "moc_len": 0, "moc_xuong": 0}})

    doi, db, p = _chay(monkeypatch, [m_nhieu, m_it], rt,
                       bo_dem=(0, 0), profile=profile,
                       now=_mot_thang(d=25))

    assert ("10.51.0.60", True) in rt.da_dat, "may dung nhieu nhat phai bi ham"
    assert m_nhieu.bi_giam_toc is True
    # may dung it khong bi dung toi lop tong (con lop rieng cung khong vuot)
    assert ("10.51.0.61", True) not in rt.da_dat
    assert m_it.bi_giam_toc is False


def test_lop_tong_khong_dung_toi_dia_chi_khong_phai_VpsInstance(
        monkeypatch, _khong_ghi_su_kien):
    """VM100-107 (viec that cua chu du an) khong phai VpsInstance. Ngay ca khi
    router bao chung dang dung rat nhieu bang thong, lop tong KHONG duoc dat
    giam toc cho dia chi cua chung — vi vong lap chi duyet bang VpsInstance."""
    m = _May("khach", plan_id="vps-lon", da_dung=1 * GB, ip="10.51.0.60")
    IP_VM100 = "10.51.0.100"
    rt = _RouterGia({"10.51.0.60": (0, 0), IP_VM100: (0, 0)},
                     dang_ham=set())

    profile = _ProfileGia({"cong_vao_bang_thong": {
        "thang": "2026-09", "tong_byte": 950 * GB, "moc_len": 0, "moc_xuong": 0}})

    _chay(monkeypatch, [m], rt, bo_dem=(0, 0), profile=profile,
          now=_mot_thang(d=25))

    da_dat_ips = {ip for ip, _ in rt.da_dat}
    assert IP_VM100 not in da_dat_ips


def test_lop_tong_bo_ham_khi_tut_duoi_nguong(monkeypatch, _khong_ghi_su_kien):
    """Tổng đã tụt dưới 80% — máy từng bị ép hãm bởi lớp tổng phải được bỏ hãm,
    nếu bản thân nó cũng không vượt hạn mức riêng."""
    m = _May("nhieu", plan_id="vps-lon", da_dung=200 * GB, ip="10.51.0.60")
    m.bi_giam_toc = True
    rt = _RouterGia({"10.51.0.60": (0, 0)}, dang_ham={"10.51.0.60"})

    profile = _ProfileGia({"cong_vao_bang_thong": {
        "thang": "2026-09", "tong_byte": 100 * GB, "moc_len": 0, "moc_xuong": 0}})

    _chay(monkeypatch, [m], rt, bo_dem=(0, 0), profile=profile,
          now=_mot_thang(d=20))

    assert ("10.51.0.60", False) in rt.da_dat
    assert m.bi_giam_toc is False


def test_loi_doc_cong_vao_khong_lam_hong_lop_rieng(monkeypatch, _khong_ghi_su_kien):
    """SSH cổng vào hỏng: lớp tổng bỏ lượt (log rồi trả rỗng), nhưng lớp RIÊNG
    (dựa trên hạn mức của chính khách) vẫn phải hoạt động bình thường."""
    from apps.vps import bao_tri, profiles
    from apps.vps.services import backend_factory
    from apps.vps.services.ssh_lenh import SshLenhError

    m = _May("vuot-rieng", plan_id="vps-nho", da_dung=99 * GB, ip="10.51.0.62")
    rt = _RouterGia({"10.51.0.62": (2 * GB, 0)})  # 99+2=101 > han muc rieng 100

    monkeypatch.setattr(backend_factory, "router_backend", lambda _p: rt)
    monkeypatch.setattr(profiles, "pinned_profile", lambda db, may: None)

    def _no(*a, **kw):
        raise SshLenhError("cong vao khong tra loi")

    monkeypatch.setattr(bao_tri, "_doc_cau_hinh_cong_vao", _no)

    db = _Db([m])
    doi = bao_tri._dong_bo_bang_thong(db, _ProfileGia())

    assert doi == 1
    assert m.bi_giam_toc is True
    assert rt.da_dat == [("10.51.0.62", True)]
