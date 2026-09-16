"""H39/G7 — đo băng thông, hãm tốc khi vượt, và chặn thư ra.

Trang bán đã hứa hai điều từ trước khi có mã nào giữ chúng:

> *"Băng thông có hạn mức theo gói. Vượt hạn mức thì bị giảm tốc, không bị tính
> thêm tiền."*

Nên bộ test này kiểm cả **lời hứa** lẫn **cách giữ nó**, và chỗ dễ sai nhất không
phải phép so sánh với hạn mức — mà là phép cộng dồn: bộ đếm của `nft` **về 0** khi
router khởi động lại, và một hiệu số âm cộng vào tổng là **hoàn lại băng thông**
cho khách.
"""
from __future__ import annotations

import pytest

from apps.vps import bang_thong


class _May:
    def __init__(self, plan_id="vps-nho", da_dung=0, giam_toc=False,
                 ip="10.51.0.50", trang_thai="dang_chay"):
        self.id = "may-1"
        self.plan_id = plan_id
        self.bang_thong_byte = da_dung
        self.bang_thong_moc_len = 0
        self.bang_thong_moc_xuong = 0
        self.bi_giam_toc = giam_toc
        self.ip_noi_bo = ip
        self.trang_thai = trang_thai
        self.dia_them_gb = 0


GB = 1024 ** 3


# ── 1. Cộng dồn: chỗ dễ sai nhất ────────────────────────────────────────────

def test_cong_don_binh_thuong():
    assert bang_thong.cong_don(1000, 900, 1500) == (1600, 1500)


def test_bo_dem_VE_0_thi_khong_duoc_tra_so_am():
    """Router khởi động lại → `nft` đếm lại từ 0. Lấy hiệu mà không xử lý việc
    này cho ra `50 - 900 = -850`, và một số âm cộng vào tổng **hoàn lại** băng
    thông cho khách — hạn mức thành vô nghĩa sau mỗi lần khởi động lại."""
    tong, moc = bang_thong.cong_don(1000, 900, 50)
    assert tong == 1050, "phai cong nguyen phan moi, khong tru"
    assert moc == 50


def test_cong_don_nhieu_luot_lien_tiep():
    tong, moc = 0, 0
    for doc in (100, 250, 250, 900, 10, 60):     # 900 -> 10 la mot lan dat lai
        tong, moc = bang_thong.cong_don(tong, moc, doc)
    assert tong == 900 + 60
    assert moc == 60


def test_so_am_dau_vao_khong_lam_vo_phep_tinh():
    assert bang_thong.cong_don(-5, -5, -5) == (0, 0)


# ── 2. Hạn mức ──────────────────────────────────────────────────────────────

def test_moi_goi_deu_co_han_muc():
    """Một gói không khai hạn mức là một gói không hãm được — và nó sẽ là gói mà
    một khách tải 2 TB đi qua."""
    from apps.vps.cost import PLANS

    for p in PLANS:
        assert p.bang_thong_gb > 0, f"{p.id} chua khai bang_thong_gb"


def test_han_muc_tang_dan_theo_goi():
    from apps.vps.cost import PLANS

    gb = [p.bang_thong_gb for p in PLANS]
    assert gb == sorted(gb), "goi dat hon ma han muc thap hon la mot loi ban hang"


def test_vuot_han_muc_dung_o_dung_nguong():
    tran = bang_thong.han_muc_byte("vps-nho")
    assert bang_thong.vuot_han_muc(_May(da_dung=tran - 1)) is False
    assert bang_thong.vuot_han_muc(_May(da_dung=tran)) is True


def test_goi_la_thi_khong_ham_chu_khong_no():
    """Gói không tra được (dữ liệu cũ, gói đã rút) thì **không hãm** — hãm một
    máy vì không tra được bảng giá là phạt khách vì lỗi của ta."""
    assert bang_thong.han_muc_byte("khong-co-goi-nay") == 0
    assert bang_thong.vuot_han_muc(_May(plan_id="khong-co-goi-nay",
                                        da_dung=99 * GB)) is False


def test_phan_tram_khong_vo_bo_cuc_trang():
    assert bang_thong.phan_tram(_May(da_dung=0)) == 0
    assert bang_thong.phan_tram(_May(da_dung=150 * GB)) == 50
    assert bang_thong.phan_tram(_May(da_dung=99_999 * GB)) == 999


def test_doc_duoc_ra_cau_nguoi_doc():
    assert bang_thong.doc_duoc(0) == "0 KB"
    assert bang_thong.doc_duoc(5 * 1024 ** 2) == "5 MB"
    assert bang_thong.doc_duoc(3 * GB) == "3.0 GB"


# ── 3. Bán chồng: nói thẳng con số ──────────────────────────────────────────

def test_tong_da_hua_doi_chieu_duoc_voi_tran_cong_vao():
    """Bán chồng là chủ ý (cùng khuôn với đĩa thin ở V14), nhưng nó phải là một
    con số nhìn thấy được — không phải một bất ngờ trên hoá đơn Vultr."""
    may = [_May(plan_id="vps-lon") for _ in range(3)]
    assert bang_thong.tong_da_hua_gb(may) == 3000
    assert bang_thong.TRAN_CONG_VAO_GB == 2048


# ── 4. Vòng bảo trì: đo, hãm, và bỏ hãm ─────────────────────────────────────

class _RouterGia:
    def __init__(self, so_lieu=None, hong=False, dang_ham=()):
        self.so_lieu = so_lieu or {}
        self.hong = hong
        self.dang_ham = set(dang_ham)
        self.da_dat: list[tuple[str, bool]] = []
        self.da_bat_do: list[str] = []

    def doc_bang_thong(self):
        if self.hong:
            from apps.vps.services.ssh_lenh import SshLenhError
            raise SshLenhError("router khong tra loi")
        return self.so_lieu

    def danh_sach_giam_toc(self):
        return set(self.dang_ham)

    def theo_doi_bang_thong(self, ip):
        self.da_bat_do.append(ip)

    def dat_giam_toc(self, ip, bat):
        self.da_dat.append((ip, bat))


class _Db:
    def __init__(self, may):
        self.may = list(may)
        self.da_commit = 0

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
        self.da_commit += 1


@pytest.fixture()
def _khong_ghi_su_kien(monkeypatch):
    from apps.vps.services import billing
    monkeypatch.setattr(billing, "ghi_su_kien", lambda *a, **kw: None)


def _chay(monkeypatch, may, rt):
    from apps.vps import bao_tri
    from apps.vps.services import router as bo_dinh_tuyen

    monkeypatch.setattr(bo_dinh_tuyen, "client_tu_moi_truong", lambda: rt)
    db = _Db(may)
    return bao_tri._dong_bo_bang_thong(db), db


def test_cong_don_ca_hai_chieu_vao_MOT_tong(monkeypatch, _khong_ghi_su_kien):
    """Lên và xuống cùng tính vào một hạn mức. Tách hai hạn mức nghe có vẻ công
    bằng hơn nhưng khách không nghĩ theo hai chiều, và trang bán chỉ hứa một số."""
    m = _May()
    _chay(monkeypatch, [m], _RouterGia({"10.51.0.50": (3 * GB, 5 * GB)}))
    assert m.bang_thong_byte == 8 * GB


def test_vuot_tran_thi_HAM_TOC_tren_router(monkeypatch, _khong_ghi_su_kien):
    m = _May(da_dung=299 * GB)
    rt = _RouterGia({"10.51.0.50": (2 * GB, 0)})     # 299 + 2 = 301 > 300
    doi, _ = _chay(monkeypatch, [m], rt)
    assert doi == 1
    assert rt.da_dat == [("10.51.0.50", True)]
    assert m.bi_giam_toc is True


def test_duoi_tran_thi_KHONG_dung_toi_router(monkeypatch, _khong_ghi_su_kien):
    """Gọi `dat_giam_toc` mỗi giờ cho mọi máy là hàng trăm lệnh SSH mỗi ngày để
    đặt lại đúng thứ đã đặt."""
    m = _May(da_dung=10 * GB)
    rt = _RouterGia({"10.51.0.50": (1 * GB, 0)})
    doi, _ = _chay(monkeypatch, [m], rt)
    assert doi == 0 and rt.da_dat == []


def test_da_ham_ma_xuong_duoi_tran_thi_BO_HAM(monkeypatch, _khong_ghi_su_kien):
    """Chu kỳ mới đặt lại bộ đếm về 0 → phải bỏ hãm. Không bỏ thì khách trả tiền
    xong vẫn dùng máy chậm, và họ sẽ không tự đoán ra vì sao."""
    m = _May(da_dung=0, giam_toc=True)
    rt = _RouterGia({"10.51.0.50": (0, 0)}, dang_ham={"10.51.0.50"})
    doi, _ = _chay(monkeypatch, [m], rt)
    assert doi == 1 and rt.da_dat == [("10.51.0.50", False)]
    assert m.bi_giam_toc is False


def test_router_khong_tra_loi_thi_BO_LUOT_chu_khong_no(monkeypatch,
                                                       _khong_ghi_su_kien):
    """Bộ đếm trên router vẫn chạy tiếp, nên lượt sau cộng bù đủ — không mất gì.
    Nhưng ném ra ngoài thì cả vòng bảo trì của nền tảng dừng theo."""
    m = _May()
    doi, _ = _chay(monkeypatch, [m], _RouterGia(hong=True))
    assert doi == 0 and m.bang_thong_byte == 0


def test_may_khong_co_so_lieu_thi_GHI_LAI_va_giu_nguyen_tong(monkeypatch,
                                                             _khong_ghi_su_kien):
    """Chạy lại `cai-dat-router.sh` là `delete table` rồi dựng lại — **cả ba set
    rỗng**. Máy đang sống mất phép đo, và nếu không ghi lại thì nó dùng bao nhiêu
    cũng không ai biết, vĩnh viễn và im lặng.

    Đã xảy ra thật 24/08 giữa lúc diễn tập G7."""
    m = _May(da_dung=42 * GB)
    rt = _RouterGia({})
    _chay(monkeypatch, [m], rt)
    assert rt.da_bat_do == ["10.51.0.50"], "phai ghi lai may vao set dem"
    assert m.bang_thong_byte == 42 * GB, "khong duoc coi 'khong co so lieu' la 0"


def test_router_MAT_co_ham_thi_dat_lai(monkeypatch, _khong_ghi_su_kien):
    """CSDL nói đang hãm, router thì không — tình huống sau một lần dựng lại
    ruleset. Tin cột trong CSDL thì máy vượt trần chạy full tốc mãi mãi."""
    m = _May(da_dung=400 * GB, giam_toc=True)
    rt = _RouterGia({"10.51.0.50": (0, 0)}, dang_ham=set())
    doi, _ = _chay(monkeypatch, [m], rt)
    assert rt.da_dat == [("10.51.0.50", True)], "phai ham lai tren router"
    assert doi == 1


# ── 5. Chu kỳ mới đặt lại bộ đếm ────────────────────────────────────────────

def test_thu_mot_chu_ky_dat_lai_bang_thong(monkeypatch):
    """Hạn mức là *mỗi chu kỳ*. Không đặt lại thì mọi khách đều chạm trần vĩnh
    viễn sau vài tháng, và không ai hiểu vì sao máy chậm dần."""
    from datetime import datetime, timezone

    from apps.vps.services import billing

    monkeypatch.setattr(billing, "ghi_su_kien", lambda *a, **kw: None)
    monkeypatch.setattr(billing, "credit_thang", lambda *a, **kw: 0)

    m = _May(da_dung=250 * GB)
    m.paid_until = None
    billing.thu_mot_chu_ky(None, m, now=datetime(2026, 8, 24, tzinfo=timezone.utc))
    assert m.bang_thong_byte == 0


# ── 6. Chặn thư ra ──────────────────────────────────────────────────────────

def test_router_chan_ba_cong_thu():
    """Một máy khách gửi thư rác là IP của **ta** vào danh sách đen, và Vultr khoá
    cả tài khoản — tức mọi khách mất máy cùng lúc vì một người.

    Chặn cả 465 và 587 chứ không riêng 25: ba cổng này là ba *đường gửi*, không
    phải ba mức độ tin cậy."""
    from pathlib import Path

    n = Path("tools/vps_gateway/cai-dat-router.sh").read_text(encoding="utf-8")
    assert "tcp dport { 25, 465, 587 }" in n
    assert "reject" in n, "reject de khach thay loi ngay, thay vi cho het gio"


def test_luat_do_bang_thong_dat_SAU_cac_luat_chan():
    """Đếm trước khi chặn nghĩa là tính vào hạn mức của khách cả những gói mà
    **chính ta** vứt đi."""
    from pathlib import Path

    n = Path("tools/vps_gateway/cai-dat-router.sh").read_text(encoding="utf-8")
    assert n.index("ip daddr @rieng") < n.index("ip saddr @bw_len")
    assert n.index("tcp dport { 25, 465, 587 }") < n.index("ip saddr @bw_len")


def test_ham_toc_KHONG_phai_cat_han():
    """Trang bán hứa "giảm tốc, không bị tính thêm tiền". Một luật `drop` trần
    biến lời hứa đó thành lời nói dối."""
    from pathlib import Path

    n = Path("tools/vps_gateway/cai-dat-router.sh").read_text(encoding="utf-8")
    assert "ip saddr @giam_toc limit rate over" in n
    assert "ip daddr @giam_toc limit rate over" in n


# ── 7. Vòng đời: bật đo khi tạo, tắt khi xoá ────────────────────────────────

def test_job_tao_may_BAT_do_bang_thong(monkeypatch):
    """Máy không nằm trong set đếm thì nó dùng bao nhiêu cũng không ai biết."""
    from types import SimpleNamespace
    from apps.vps import jobs
    from apps.vps.services import mutation_coordinator

    class _Router:
        def __init__(self):
            self.reservations = {}
            self.followed = []

        def dat_cho(self, mac, ip, *, ten):
            self.reservations[mac] = ip

        def theo_doi_bang_thong(self, ip):
            self.followed.append(ip)

        def danh_sach_dat_cho(self):
            return self.reservations

        def doc_bang_thong(self):
            return {ip: (0, 0) for ip in self.followed}

    def execute(_db, **kwargs):
        kwargs["mutate"]()
        assert kwargs["readback"]() is True
        return SimpleNamespace(state="OBSERVED")

    monkeypatch.setattr(mutation_coordinator, "execute", execute)
    rt = _Router()
    may = SimpleNamespace(id="12345678-1234-5678-1234-567812345678",
                          ip_noi_bo="10.51.0.50")
    jobs._dat_cho_co_journal(object(), may, rt)

    assert rt.followed == ["10.51.0.50"]


def test_job_xoa_may_TAT_do_va_bo_ham():
    """Địa chỉ được cấp lại cho khách khác: bộ đếm cũ dính sang người mới là một
    hoá đơn sai, và cờ hãm sót lại là một máy chậm không ai giải thích được."""
    import inspect

    assert "thoi_theo_doi(may.ip_noi_bo)" in inspect.getsource(
        __import__("apps.vps.jobs", fromlist=["x"])._go_cho_dhcp)
