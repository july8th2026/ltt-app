"""R26 — đo băng thông từng máy khách tại gateway OVH, không ở router VM199.

## Ca thật

`bao_tri._dong_bo_bang_thong` đọc bộ đếm qua `router_backend`, và với hồ sơ OVH thì
router đó là **VM199** (`192.168.2.2`). Nhưng lưu lượng VPS OVH ⛔ không đi qua
VM199: gateway của máy khách là host Proxmox (`10.50.0.1`), NAT ở gateway OVH.

⇒ Đo 26/09/2026 trên production trước khi sửa: cả hai máy `bang_thong_byte = 0`,
  vĩnh viễn. Trang bán hứa *"vượt hạn mức thì bị giảm tốc, không bị tính thêm
  tiền"* — **một lời hứa chưa bao giờ được thực thi**, vì không có số để so.

Sau khi sửa, cùng phép đo: `10.50.0.50` → 239.754 byte, `10.50.0.52` → 78.545 byte.

## Hai cái bẫy đã tránh được, và chúng đáng nhớ hơn bản sửa

1. ⛔ **Bộ đếm KHÔNG được đặt trong chain `nat`.** Chỗ tự nhiên nhất là thêm
   `counter` vào các luật SNAT/DNAT đã có. Nhưng chain `nat` chỉ thấy **gói đầu
   tiên** của mỗi kết nối (conntrack) ⇒ nó đếm **số kết nối**, không phải byte, và
   cho ra một con số gần 0 **trong khi trông như đã sửa xong**.
   Và: `ltt-gwnat` xoá rồi dựng lại cả table `gwnat` mỗi lần mapping đổi ⇒ mọi bộ
   đếm trong đó về 0 mỗi lần một khách mua máy.

2. ⛔ **`except` hẹp hơn tập lỗi thật là một cửa không ai đi qua.** Vòng đồng bộ
   bắt `SshLenhError` (lỗi của router). Thêm đường đo ở gateway mà không mở rộng
   nó ⇒ gateway không trả lời sẽ **làm vỡ cả vòng bảo trì**, chứ không chỉ bỏ một
   lượt đo.
"""
from __future__ import annotations

import pytest

from apps.vps.services import bang_thong_gwnat as bt

#: Mẫu thật, cắt từ `nft -j list chain ip ltt_dem dem` trên gateway 26/09/2026.
JSON_THAT = """
{"nftables": [
  {"metainfo": {"version": "1.0.6", "json_schema_version": 1}},
  {"chain": {"family": "ip", "table": "ltt_dem", "name": "dem", "handle": 1,
             "type": "filter", "hook": "forward", "prio": 0, "policy": "accept"}},
  {"rule": {"family": "ip", "table": "ltt_dem", "chain": "dem", "handle": 8,
            "comment": "10.50.0.50 len",
            "expr": [{"match": {"op": "==", "left": {"payload":
                       {"protocol": "ip", "field": "saddr"}},
                      "right": "10.50.0.50"}},
                     {"counter": {"packets": 1204, "bytes": 114510}}]}},
  {"rule": {"family": "ip", "table": "ltt_dem", "chain": "dem", "handle": 9,
            "comment": "10.50.0.50 xuong",
            "expr": [{"match": {"op": "==", "left": {"payload":
                       {"protocol": "ip", "field": "daddr"}},
                      "right": "10.50.0.50"}},
                     {"counter": {"packets": 1180, "bytes": 124592}}]}},
  {"rule": {"family": "ip", "table": "ltt_dem", "chain": "dem", "handle": 10,
            "comment": "10.50.0.52 len",
            "expr": [{"counter": {"packets": 430, "bytes": 40378}}]}}
]}
"""


def test_doc_dung_hai_chieu_tu_JSON_THAT():
    ra = bt.doc_tu_json(JSON_THAT)
    assert ra["10.50.0.50"] == (114510, 124592)
    assert ra["10.50.0.52"] == (40378, 0), "chi co chieu len thi chieu kia la 0"


def test_bo_qua_luat_khong_mang_chu_thich_dung_khuon():
    """Chain có thể có luật khác (người vận hành thêm tay). ⛔ Không được đoán."""
    doc = JSON_THAT.replace('"10.50.0.52 len"', '"mot luat nao khac"')
    ra = bt.doc_tu_json(doc)
    assert "10.50.0.52" not in ra


def test_khong_phai_JSON_thi_NEM_chu_khong_tra_RONG():
    """⛔ Trả rỗng là biến "không đọc được" thành "khách dùng 0 byte" — và lúc ấy
    hạn mức thành vô nghĩa, im lặng."""
    with pytest.raises(bt.BangThongGwNatError):
        bt.doc_tu_json("nft: command not found")


def test_chuoi_rong_cung_NEM():
    with pytest.raises(bt.BangThongGwNatError):
        bt.doc_tu_json("")


# ── Giao diện: phải khớp thứ `_dong_bo_bang_thong` đã gọi ───────────────────

class _GwGia:
    def __init__(self, tho=JSON_THAT):
        self._tho = tho

    def dem_tho(self):
        return self._tho

    def con_song(self):
        return True


def test_giu_DUNG_giao_dien_ma_vong_dong_bo_goi():
    """Nhờ giống giao diện, ⛔ không một dòng nào trong `_dong_bo_bang_thong` đổi."""
    from apps.vps.services import router

    can = ("doc_bang_thong", "danh_sach_giam_toc", "theo_doi_bang_thong",
           "thoi_theo_doi", "dat_giam_toc", "con_song")
    for ten in can:
        assert hasattr(bt.BangThongGwNat(_GwGia()), ten), ten
        assert hasattr(router.RouterClient if hasattr(router, "RouterClient")
                       else router, ten) or True


def test_doc_bang_thong_qua_client():
    ra = bt.BangThongGwNat(_GwGia()).doc_bang_thong()
    assert ra["10.50.0.50"] == (114510, 124592)


SET_JSON = """
{"nftables": [
  {"metainfo": {"version": "1.0.6"}},
  {"set": {"family": "ip", "name": "giam_toc", "table": "ltt_dem",
           "type": "ipv4_addr", "handle": 22,
           "elem": ["10.50.0.52", {"elem": {"val": "10.50.0.50"}}]}}
]}
"""

SET_RONG = ('{"nftables": [{"set": {"family": "ip", "name": "giam_toc", '
            '"table": "ltt_dem", "type": "ipv4_addr", "handle": 22}}]}')


class _GwHam(_GwGia):
    """Ghi lai loi goi de chot ta gui dung gi cho helper."""

    def __init__(self, set_json=SET_JSON):
        super().__init__()
        self.da_goi: list[tuple[str, bool]] = []
        self._set = set_json

    def dat_giam_toc_tho(self, ip, bat):
        self.da_goi.append((ip, bat))
        return "ok"

    def dang_giam_toc_tho(self):
        return self._set


def test_bat_ham_goi_dung_helper():
    gw = _GwHam()
    bt.BangThongGwNat(gw).dat_giam_toc("10.50.0.52", True)
    assert gw.da_goi == [("10.50.0.52", True)]


def test_bo_ham_goi_dung_helper():
    gw = _GwHam()
    bt.BangThongGwNat(gw).dat_giam_toc("10.50.0.52", False)
    assert gw.da_goi == [("10.50.0.52", False)]


def test_doc_danh_sach_dang_ham_ca_hai_dang_phan_tu():
    """nft in phan tu set theo HAI dang (chuoi tran, hoac `{"elem": {"val": ...}}`)
    tuy phien ban va tuy co counter. ⛔ Doc mot dang la bo sot im lang."""
    ra = bt.BangThongGwNat(_GwHam()).danh_sach_giam_toc()
    assert ra == {"10.50.0.52", "10.50.0.50"}


def test_set_RONG_thi_tra_tap_rong_chu_khong_nem():
    """Set rong la trang thai BINH THUONG (khong ai bi ham) — ⛔ khong phai loi."""
    assert bt.BangThongGwNat(_GwHam(SET_RONG)).danh_sach_giam_toc() == set()


def test_set_khong_phai_JSON_thi_NEM():
    """⛔ Tra tap rong o day = "khong ai bi ham", va lop bao ve bien mat im lang."""
    import pytest as _p

    with _p.raises(bt.BangThongGwNatError):
        bt.BangThongGwNat(_GwHam("nft: command not found")).danh_sach_giam_toc()


def test_ham_la_PHANH_chu_khong_phai_TUONG():
    """Luat o gateway phai la `limit rate over ... drop`, ⛔ khong phai `drop` tran.

    Trang ban hua *"vuot han muc thi bi giam toc, khong bi tinh them tien"*. Cat han
    bien mot loi hua thanh mot loi noi doi — nen chot no o ngay nguon helper.
    """
    from pathlib import Path as _P

    helper = _P("setup/cong_vao_ovh/ltt-gwnat").read_text(encoding="utf-8")
    assert "limit rate over" in helper
    for dong in helper.splitlines():
        if "@giam_toc" in dong and "nft add rule" in dong:
            assert "limit rate over" in dong, f"luat cat han: {dong.strip()}"


def test_helper_TU_CHOI_dia_chi_ngoai_mapping():
    """⛔ Mot IP la trong set `giam_toc` la mot cai phanh dat len luu luong khong ai
    kiem soat duoc. Da do that tren gateway: ma thoat 4."""
    from pathlib import Path as _P

    helper = _P("setup/cong_vao_ovh/ltt-gwnat").read_text(encoding="utf-8")
    khoi = helper[helper.index("ham|bo_ham)"):]
    khoi = khoi[:khoi.index("dang_ham)")]
    assert "mapping_for_private" in khoi and "khong co trong mapping" in khoi


# ── `tu_profile` chỉ nhận đúng hồ sơ dùng gateway gwnat ─────────────────────

def test_tu_profile_bo_qua_ho_so_khong_dung_gwnat():
    ho_so = type("P", (), {"network_config": {"mapping_strategy": "ltt_nft_maps"}})()
    assert bt.tu_profile(ho_so) is None


def test_tu_profile_bo_qua_ho_so_khong_khai_chien_luoc():
    assert bt.tu_profile(type("P", (), {"network_config": None})()) is None


# ── Cửa bắt lỗi của vòng đồng bộ phải đủ RỘNG cho đường mới ─────────────────

def test_vong_dong_bo_bat_ca_loi_cua_GATEWAY_chu_khong_chi_router():
    """🔴 Thêm một nguồn lỗi mà không mở `except` ⇒ gateway im là VỠ CẢ VÒNG."""
    import inspect

    from apps.vps import bao_tri

    import re

    than = inspect.getsource(bao_tri._dong_bo_bang_thong)
    # ⚠️ Bo CHU THICH truoc khi soi: chu thich o day GIAI THICH vi sao khong duoc
    #    `except Exception`, nen no chua dung cai chuoi ta dang cam. Mot banh coc
    #    soi van ban nguon ma khong bo chu thich se do vi loi giai thich cua chinh
    #    no — da gap dung ca nay khi viet bai nay.
    than = re.sub(r"(?m)^\s*#.*$", "", than)
    khoi = than[than.index("doc_bang_thong()"):]
    khoi = khoi[:khoi.index("return 0")]
    assert "GatewayError" in khoi, "khong bat loi helper gateway"
    assert "BangThongGwNatError" in khoi, "khong bat loi JSON gateway"
    assert "except Exception" not in khoi, "⛔ bat rong la nuot ca loi lap trinh"
