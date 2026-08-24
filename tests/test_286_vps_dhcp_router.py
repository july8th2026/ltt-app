"""H39/G5 — đặt chỗ DHCP trên VM router, và cột vé console.

Hai nhóm test không liên quan nhau về chủ đề nhưng chung một bài học: **thứ bộ
test không cưỡng chế thì production sẽ cưỡng chế**.

* DHCP: một MAC sai dạng lọt vào `dhcp-hosts` làm dnsmasq bỏ qua **cả tệp**, và
  triệu chứng là mọi máy khách mất mạng — không lỗi nào chỉ vào nguyên nhân.
* Vé console: cột `pve_ve` từng là `String(255)`. Vé thật của Proxmox dài hơn
  thế, nên Postgres từ chối INSERT và console trả **500 cho mọi máy**. SQLite
  không cưỡng chế độ dài `VARCHAR` nên `test_282` đi qua sạch sẽ trong khi tính
  năng chưa chạy được lần nào.
"""
from __future__ import annotations

import pytest
from sqlalchemy import String, Text

from apps.vps.services import router
from apps.vps.services.ssh_lenh import DichDen, SshLenhError


class _Ghi:
    """Thay SSH: giữ lại kịch bản bash đã sinh, không chạy gì."""

    def __init__(self, tra: str = ""):
        self.lenh: list[list[str]] = []
        self.tra = tra

    def __call__(self, lenh):
        self.lenh.append(lenh)
        return self.tra

    @property
    def kich_ban(self) -> str:
        """Kịch bản bash **đã gỡ lớp `shlex.quote`**.

        Không gỡ thì mọi assert phải viết theo dạng `'"'"'"'` của shell, và
        test trở thành thứ kiểm cách bọc chuỗi chứ không kiểm việc cần kiểm.
        """
        import shlex

        if not self.lenh:
            return ""
        return shlex.split(self.lenh[-1][2])[0]


def _client(tra: str = ""):
    ghi = _Ghi(tra)
    return router.RouterClient(
        DichDen(host="h", user="ltt", khoa="k", nhan="VM router"), chay=ghi), ghi


# ── 1. Chặn dữ liệu bẩn TRƯỚC khi nó chạm shell từ xa ───────────────────────

@pytest.mark.parametrize("mac", [
    "", "bc-24-11-c9-5f-ad", "bc:24:11:c9:5f", "zz:24:11:c9:5f:ad",
    "bc:24:11:c9:5f:ad:00", "bc:24:11:c9:5f:a",
    "bc:24:11:c9:5f:ad; rm -rf /", "$(whoami)",
])
def test_mac_sai_dang_bi_TU_CHOI_chu_khong_di_toi_router(mac):
    c, ghi = _client()
    with pytest.raises(router.RouterError):
        c.dat_cho(mac, "10.51.0.50")
    assert ghi.lenh == [], "khong duoc goi router"


@pytest.mark.parametrize("ip", ["", "10.51.0", "10.51.0.999", "10.51.0.1;reboot",
                                "not-an-ip", "10.51.0.1/24"])
def test_dia_chi_sai_dang_bi_TU_CHOI(ip):
    c, ghi = _client()
    with pytest.raises(router.RouterError):
        c.dat_cho("bc:24:11:c9:5f:ad", ip)
    assert ghi.lenh == []


def test_ten_may_bi_loc_ky_tu_la():
    """Tên đi thẳng vào một dòng cấu hình. Dấu phẩy trong tên tách sai cột và
    dnsmasq đọc phần sau như một trường khác."""
    c, ghi = _client()
    c.dat_cho("bc:24:11:c9:5f:ad", "10.51.0.50", ten="vps-abc,1.2.3.4;rm -rf /")
    assert "rm -rf" not in ghi.kich_ban
    assert "bc:24:11:c9:5f:ad,10.51.0.50,vps-abc1234rm-rf" in ghi.kich_ban


def test_mac_duoc_chuan_hoa_ve_chu_thuong():
    """dnsmasq so khớp không phân biệt hoa thường, nhưng `danh_sach_dat_cho` và
    `go_cho` so chuỗi — lệch hoa thường là gỡ trượt chỗ của chính mình."""
    c, ghi = _client()
    c.dat_cho("BC:24:11:C9:5F:AD", "10.51.0.50")
    assert "bc:24:11:c9:5f:ad,10.51.0.50" in ghi.kich_ban


# ── 2. Chạy lại được, và dọn cả hai vế ──────────────────────────────────────

def test_dat_cho_xoa_dong_cu_theo_CA_MAC_LAN_DIA_CHI():
    """Bỏ sót vế địa chỉ thì một máy đã xoá còn giữ chỗ, và máy mới nhận đúng
    địa chỉ đó **không bao giờ được cấp** — dnsmasq gặp hai dòng cùng địa chỉ
    thì giữ dòng đầu. Triệu chứng: máy chạy tốt nhưng không có mạng."""
    c, ghi = _client()
    c.dat_cho("bc:24:11:c9:5f:ad", "10.51.0.50")
    kb = ghi.kich_ban
    assert "-e '^bc:24:11:c9:5f:ad,'" in kb
    assert "-e ',10.51.0.50,'" in kb
    assert "-e ',10.51.0.50$'" in kb


def test_dat_cho_ghi_qua_tep_TAM_roi_moi_mv():
    """Ghi thẳng vào tệp đang được đọc thì một lần mất điện để lại tệp cụt, và
    dnsmasq đọc tệp cụt là mất chỗ của những khách nằm ở phần bị mất."""
    c, ghi = _client()
    c.dat_cho("bc:24:11:c9:5f:ad", "10.51.0.50")
    assert f"mv {router.TEP_DAT_CHO}.moi {router.TEP_DAT_CHO}" in ghi.kich_ban


def test_nap_lai_bang_reload_chu_khong_restart():
    """`restart` giữa lúc một khách đang gia hạn thuê bao làm máy họ rớt mạng
    vì một khách KHÁC vừa được tạo."""
    c, ghi = _client()
    c.dat_cho("bc:24:11:c9:5f:ad", "10.51.0.50")
    assert "systemctl reload dnsmasq" in ghi.kich_ban
    assert "restart dnsmasq" not in ghi.kich_ban

    c2, ghi2 = _client()
    c2.go_cho("bc:24:11:c9:5f:ad")
    assert "systemctl reload dnsmasq" in ghi2.kich_ban
    assert "restart dnsmasq" not in ghi2.kich_ban


def test_go_cho_khong_keu_khi_tep_chua_ton_tai():
    c, ghi = _client()
    c.go_cho("bc:24:11:c9:5f:ad")
    assert ghi.kich_ban.rstrip().endswith("true")


def test_chi_MOT_lenh_chay_bang_root():
    """Cho cả đoạn bash chạy `sudo` chỉ để tiện là mở rộng thiệt hại của mọi lỗi
    trong đoạn đó mà không đổi lại được gì."""
    c, ghi = _client()
    c.dat_cho("bc:24:11:c9:5f:ad", "10.51.0.50")
    assert ghi.lenh[-1][0] == "bash", "kich ban KHONG duoc chay bang sudo"
    assert ghi.kich_ban.count("sudo -n ") == 1


# ── 3. Đọc lại danh sách ────────────────────────────────────────────────────

def test_doc_danh_sach_dat_cho():
    c, _ = _client("bc:24:11:c9:5f:ad,10.51.0.50,vps-a\n"
                   "BC:24:11:AA:BB:CC,10.51.0.51\n"
                   "\n"
                   "rac-khong-dung-dang\n")
    assert c.danh_sach_dat_cho() == {"bc:24:11:c9:5f:ad": "10.51.0.50",
                                     "bc:24:11:aa:bb:cc": "10.51.0.51"}


def test_tep_rong_thi_tra_dict_rong_chu_khong_no():
    c, _ = _client("")
    assert c.danh_sach_dat_cho() == {}


# ── 4. Khai thiếu thì nói rõ thiếu gì ───────────────────────────────────────

def test_thieu_host_thi_bao_dung_TEN_BIEN():
    with pytest.raises(SshLenhError) as e:
        router.doc_cau_hinh({})
    assert "LTT_VPS_ROUTER_HOST" in str(e.value)


def test_thieu_khoa_ssh_thi_bao_ro():
    with pytest.raises(SshLenhError) as e:
        router.doc_cau_hinh({"LTT_VPS_ROUTER_HOST": "1.2.3.4"})
    assert "khoa SSH" in str(e.value)


# ── 5. Job phải dùng đúng MAC đã ghim vào máy ───────────────────────────────

def test_job_dat_cho_bang_DUNG_MAC_da_ghim_vao_net0():
    """Hai nơi tính MAC khác nhau thì DHCP giữ chỗ cho một địa chỉ mà card của
    máy không bao giờ dùng tới — và máy im lặng không có mạng."""
    import inspect

    from apps.vps import jobs

    nguon = inspect.getsource(jobs._tao_may)
    assert "dat_cho(" in nguon
    assert "dinh_danh.mac(may.id)" in nguon
    assert "mac=dinh_danh.mac(may.id)" in nguon, "net0 phai ghim cung MAC do"


def test_go_cho_dung_cung_ham_mac():
    import inspect

    from apps.vps import jobs

    assert "dinh_danh.mac(may.id)" in inspect.getsource(jobs._go_cho_dhcp)


# ── 6. Cột vé console phải KHÔNG có trần độ dài ─────────────────────────────

def test_cot_pve_ve_la_TEXT_khong_phai_varchar_co_tran():
    """Vé `vncproxy` thật dài hơn 255 ký tự. `String(255)` làm Postgres từ chối
    INSERT và console trả 500 cho MỌI máy — trong khi SQLite (bộ test) không
    cưỡng chế độ dài nên `test_282` vẫn xanh. Đã xảy ra thật 24/08."""
    from apps.vps.tables import VpsConsoleVe

    cot = VpsConsoleVe.__table__.c.pve_ve
    assert isinstance(cot.type, Text) or (
        isinstance(cot.type, String) and cot.type.length is None), \
        f"pve_ve dang la {cot.type!r} — ve that dai hon 255 ky tu"


def test_ve_dai_that_van_luu_duoc():
    """Đo bằng một vé dài cỡ thật, không phải một chuỗi mười ký tự."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from apps.vps.services import console
    from apps.vps.tables import VpsInstance

    e = create_engine("sqlite://")
    dbmod.Base.metadata.create_all(e, tables=[
        t for t in dbmod.Base.metadata.sorted_tables
        if t.name in ("vps_console_ve", "vps_instance")])
    db = sessionmaker(bind=e)()
    try:
        m = VpsInstance(user_id="u1", plan_id="vps-nho", os_id="win10",
                        gateway_id="gw1", trang_thai="dang_chay", vmid=200)
        db.add(m)
        db.commit()
        ve_dai = "PVEVNC:" + "A1b2C3d4" * 80          # 647 ky tu
        ve = console.cap_ve(db, m, "u1", cong=5901, pve_ve=ve_dai)
        _, _, ra = console.tieu_ve(db, ve, m.id, "u1")
        assert ra == ve_dai
    finally:
        db.close()


# ── 7. Kịch bản cài router: không được có dấu huyền ─────────────────────────

def test_kich_ban_router_KHONG_chua_dau_huyen():
    """`cai-dat-router.sh` sinh hai tệp cấu hình bằng heredoc **không nháy** —
    phải thế, vì nó cần thay `$NIC_KHACH`, `$TOC_GIAM`… Nhưng trong heredoc không
    nháy, **dấu huyền là thay-thế-lệnh**: một chú thích có `` `static` `` biến
    thành `static: command not found`, và dòng chú thích bị mất chữ.

    Đã dính **ba lần** trong một ngày, mỗi lần mất vài phút chẩn đoán nhầm sang
    dnsmasq và nftables. Nên nay nó là một phép kiểm, không phải một điều cần nhớ.
    """
    from pathlib import Path

    tep = Path("tools/vps_gateway/cai-dat-router.sh")
    noi_dung = tep.read_text(encoding="utf-8")
    assert "`" not in noi_dung, (
        "dau huyen trong heredoc khong nhay = thay-the-lenh; dung dau nhay don")


def test_kich_ban_router_xuong_dong_kieu_LF():
    """Tep nay viet tren Windows va chay tren Debian. Mot ky tu CR sot lai
    lam 'set -o pipefail' thanh 'pipefail<CR>' va bash bao *invalid option
    name* -- mot cau khong chi vao nguyen nhan nao ca. Da dinh that.

    Chi kiem moi nguy THAT: ky tu ke khung trong chu thich thi vo hai tren
    Debian, va mot phep kiem 'phai thuan ASCII' o day se do vi ly do khong
    ai quan tam -- loai test roi se bi xoa trong buc boi thay vi duoc sua.
    """
    from pathlib import Path

    CR = bytes([13])
    tho = Path('tools/vps_gateway/cai-dat-router.sh').read_bytes()
    assert CR not in tho, 'phai la LF, khong phai CRLF'


def test_kich_ban_router_co_du_BA_luat_bat_buoc():
    """Ba luật này là ba lớp bảo vệ khác nhau; thiếu bất kỳ lớp nào cũng hỏng
    lặng lẽ, và không lớp nào thay được lớp kia."""
    from pathlib import Path

    n = Path("tools/vps_gateway/cai-dat-router.sh").read_text(encoding="utf-8")
    assert "ip daddr @rieng" in n, "thieu chan LAN nha"
    assert "tcp dport { 25, 465, 587 }" in n, "thieu chan thu ra"
    assert "maxseg size set rt mtu" in n, "thieu MSS clamp cho duong ham 1420"
