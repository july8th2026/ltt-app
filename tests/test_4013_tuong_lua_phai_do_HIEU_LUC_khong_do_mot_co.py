"""Tường lửa Proxmox có hiệu lực hay không là một phép AND BA TẦNG.

## Ca thật, và tôi là người mắc

Ngày 25/09/2026 tôi đặt `ipfilter=1` + `macfilter=1` cho từng VM khách để chống một
khách ARP/IP spoof khách khác, rồi công cụ `vps_chuan_hoa.py` in `firewall dat` và
tôi **báo với chủ dự án là đã áp**.

Đo lại trên chính hai máy đang chạy:

    cluster/firewall/options      -> {"digest": ...}      # KHONG co khoa `enable`
    vm 204 net0                   -> ...,firewall=0,...   # co tren NIC TAT
    vm 204 firewall/options       -> {"enable": 1, "ipfilter": 1, "macfilter": 1}

⇒ Proxmox chỉ áp luật của một VM khi **cả ba** cùng bật: cụm, cờ trên NIC, và
  tuỳ chọn của VM. Hai tầng đang tắt ⇒ `ipfilter`/`macfilter` là **no-op hoàn toàn**.

🔴 Và đây là phần tệ nhất: công cụ đọc **một cờ** rồi kết luận về **một tính chất**.
   Nó không sai về cờ — cờ đó đúng là `1`. Nó sai về điều nó **tuyên bố**: *"máy này
   được bảo vệ"*. Đúng khuôn *"phạm vi phép đo hẹp hơn lời tuyên bố"*, và tôi mắc nó
   trong một công cụ viết ra **cùng ngày** để chặn đúng lớp lỗi ấy.

⚠️ Vì sao không ai thấy: hai tầng tắt ⇒ máy khách **vẫn chạy bình thường**. Một cấu
   hình bảo mật không có hiệu lực thì trông **y hệt** một cấu hình đang bảo vệ tốt —
   chỉ khác lúc có người thật đi thử.

## ⇒ Phép đo phải trả lời đúng câu người đọc hỏi

Người đọc hỏi *"máy này có được chặn spoof không"*, ⛔ không hỏi *"khoá `ipfilter`
trong bảng tuỳ chọn của VM bằng mấy"*. Nên hàm phải nêu **cả ba tầng** và nói rõ
tầng nào đang hở.
"""
from __future__ import annotations

from apps.vps.services import proxmox


class _Cli(proxmox.ProxmoxClient):
    """Client thật nhưng chặn đúng lớp gọi mạng, để đo phần suy luận."""

    def __init__(self, tra_ve):
        self._tra_ve = tra_ve
        self.config = type("C", (), {"node": "pve"})()

    def _goi(self, method, duong, **kw):       # noqa: D102
        for khoa, gia in self._tra_ve.items():
            if duong.endswith(khoa):
                return gia
        raise AssertionError(f"khong du lieu gia cho {duong}")


def _canh(*, cum=None, nic="firewall=0", vm=None):
    return _Cli({
        "/cluster/firewall/options": cum if cum is not None else {"digest": "x"},
        "/qemu/204/config": {"net0": f"e1000=BC:24:11:00:00:01,bridge=vmbr1,{nic},mtu=1420"},
        "/qemu/204/firewall/options": vm if vm is not None else {
            "enable": 1, "ipfilter": 1, "macfilter": 1},
    })


def test_ca_THAT_hien_nay_phai_bao_la_KHONG_HIEU_LUC():
    """Đúng ba giá trị đo được trên production 25/09/2026."""
    hieu_luc, ly_do = proxmox.tuong_lua_hieu_luc(_canh(), 204)
    assert hieu_luc is False
    assert "cum" in ly_do and "nic" in ly_do, ly_do


def test_chi_bat_cum_thi_van_chua_du():
    hieu_luc, ly_do = proxmox.tuong_lua_hieu_luc(
        _canh(cum={"enable": 1}), 204)
    assert hieu_luc is False and "nic" in ly_do


def test_chi_bat_nic_thi_van_chua_du():
    hieu_luc, ly_do = proxmox.tuong_lua_hieu_luc(
        _canh(nic="firewall=1"), 204)
    assert hieu_luc is False and "cum" in ly_do


def test_bat_du_ba_tang_thi_moi_la_hieu_luc():
    hieu_luc, ly_do = proxmox.tuong_lua_hieu_luc(
        _canh(cum={"enable": 1}, nic="firewall=1"), 204)
    assert hieu_luc is True and ly_do == ""


def test_tang_VM_tat_thi_cung_khong_hieu_luc():
    hieu_luc, ly_do = proxmox.tuong_lua_hieu_luc(
        _canh(cum={"enable": 1}, nic="firewall=1",
              vm={"enable": 0, "ipfilter": 1, "macfilter": 1}), 204)
    assert hieu_luc is False and "vm" in ly_do


def test_ipfilter_TAT_thi_khong_the_goi_la_chong_spoof():
    """Ba tầng bật mà `ipfilter` tắt thì tường lửa chạy nhưng ⛔ không chặn spoof.

    Đây là câu người đọc thật sự hỏi, nên hàm phải phân biệt được.
    """
    hieu_luc, ly_do = proxmox.tuong_lua_hieu_luc(
        _canh(cum={"enable": 1}, nic="firewall=1",
              vm={"enable": 1, "ipfilter": 0, "macfilter": 1}), 204)
    assert hieu_luc is False and "ipfilter" in ly_do


def test_ly_do_neu_DU_ca_ba_tang_dang_ho_khong_chi_tang_dau_tien():
    """⛔ Đừng dừng ở tầng hở đầu tiên: người sửa cần biết phải bật mấy chỗ.

    Báo một tầng rồi để người ta bật xong, chạy lại, lại báo tầng kế — ba lượt cho
    một việc, và giữa các lượt họ tưởng mình đã xong.
    """
    hieu_luc, ly_do = proxmox.tuong_lua_hieu_luc(_canh(), 204)
    assert hieu_luc is False
    assert ly_do.count(",") >= 1, f"phai neu ca hai tang dang ho: {ly_do!r}"
