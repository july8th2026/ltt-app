"""Hai mươi giọng mẫu khai ở nền tảng phải KHỚP đúng thứ engine có.

## Vì sao tệp này tồn tại

`apps/ltt_voice/giong_mau.py` là một **bản sao**. Bản gốc nằm trong venv cách ly
của engine (`vieneu/assets/voices_v3_turbo.json`), và nền tảng cố tình không đọc
nó lúc chạy: đường duy nhất hỏi engine là `/v1/voices`, mà endpoint đó gọi
`c.nap()` — **19,4 giây nạp model khi nguội**. Một trang liệt kê giọng không được
phép trả giá đó.

⭐ Nên bản sao là đúng. Cái sai là một bản sao **không có phép kiểm** — nó sẽ
   lệch, và triệu chứng của nó tệ hơn hẳn một lỗi thường: khách chọn một giọng
   trong danh sách, bấm Tạo, **bị giữ credit**, job xuống worker, rồi SDK ném
   `ValueError: Voice 'X' not found`. Lỗi hiện ở worker, bằng chữ của thư viện,
   sau khi đã tính tiền — cách xa chỗ sai ba tầng.

Cùng khuôn `tests/test_331_ltt_voice_tham_so.py` đã dùng cho trần ký tự.

## Vì sao phần lớn phép kiểm ở đây BỎ QUA khi không thấy tệp gốc

Venv của engine không có trên mọi máy chạy test (CI, máy phát triển không cài
GPU). Đòi nó có mặt sẽ làm bộ test đỏ vì một lý do không liên quan gì tới mã.
Nhưng những phép kiểm **không** cần tệp gốc — hình dạng dữ liệu, mặt lọc, mã
không trùng — thì luôn chạy.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from apps.ltt_voice import giong_mau as gm

#: Nơi SDK cất bản gốc. Hai đường vì venv nằm ngoài `app\` (C: chật, xem
#: `CLAUDE.md` hàng LTT VOICE) và máy chủ có thể đặt nó ở một trong hai.
DUONG_GOC = (
    pathlib.Path(r"D:\LTTPlatform-runtime\vieneu-venv\Lib\site-packages"
                 r"\vieneu\assets\voices_v3_turbo.json"),
    pathlib.Path(r"C:\LTTPlatform\vieneu-venv\Lib\site-packages"
                 r"\vieneu\assets\voices_v3_turbo.json"),
)


def _ban_goc() -> dict | None:
    for p in DUONG_GOC:
        try:
            if p.is_file():
                return json.loads(p.read_text(encoding="utf-8"))
        except OSError:
            continue
    return None


# ── Luôn chạy: hình dạng dữ liệu ─────────────────────────────────────────────

def test_khong_ma_nao_trung():
    ma = [g.ma for g in gm.DANH_SACH]
    assert len(ma) == len(set(ma)), f"ma trung: {[m for m in ma if ma.count(m) > 1]}"


def test_moi_mat_loc_dung_bo_gia_tri_da_khai():
    """Một giá trị lạ ở đây không làm hỏng gì ngay — nó chỉ làm bộ lọc **im
    lặng không khớp**, và giọng đó biến mất khỏi lưới mà không ai báo."""
    for g in gm.DANH_SACH:
        assert g.gioi in gm.NHAN_GIOI, f"{g.ma}: gioi={g.gioi!r} khong co nhan"
        assert g.vung in gm.NHAN_VUNG, f"{g.ma}: vung={g.vung!r} khong co nhan"
        assert g.phong_cach in gm.NHAN_PHONG_CACH, (
            f"{g.ma}: phong_cach={g.phong_cach!r} khong co nhan")


def test_mac_dinh_nam_trong_danh_sach():
    assert gm.hop_le(gm.MAC_DINH), (
        f"giong mac dinh {gm.MAC_DINH!r} khong co trong DANH_SACH — "
        "khach khong chon gi se roi vao mot preset khong ton tai")


def test_hop_le_tu_choi_ma_bia():
    assert not gm.hop_le("Khong Co Giong Nay")
    assert not gm.hop_le("")
    assert not gm.hop_le(None)  # type: ignore[arg-type]


def test_loc_khong_mat_giong_khi_khong_loc_gi():
    assert len(gm.loc()) == len(gm.DANH_SACH)


def test_loc_theo_tung_mat():
    nam = gm.loc(gioi="nam")
    nu = gm.loc(gioi="nu")
    assert nam and nu
    assert len(nam) + len(nu) == len(gm.DANH_SACH), "co giong khong thuoc gioi nao"

    # Mọi vùng và mọi phong cách đã khai đều phải có ít nhất một giọng — một mặt
    # lọc luôn trả rỗng là một ô chọn dẫn tới ngõ cụt.
    for v in gm.NHAN_VUNG:
        assert gm.loc(vung=v), f"vung {v!r} khong co giong nao"
    for p in gm.NHAN_PHONG_CACH:
        assert gm.loc(phong_cach=p), f"phong cach {p!r} khong co giong nao"


def test_tim_kiem_khong_phan_biet_hoa_thuong():
    assert gm.loc(tim_kiem="adam")
    assert gm.loc(tim_kiem="ADAM")


def test_giong_mau_co_cung_be_mat_voi_giong_nhan_ban():
    """Lưới thẻ và bộ chọn dùng CHUNG một partial cho cả hai loại giọng.

    ⭐ Nên hai loại phải trả lời cùng một bộ câu hỏi. Thiếu một thuộc tính thì
       template ném `UndefinedError` — hoặc tệ hơn, với Jinja mặc định nó in ra
       chuỗi rỗng và cột đó **lặng lẽ trống**.
    """
    for g in gm.DANH_SACH:
        assert g.public_id == g.ma
        assert g.ten_hien_thi
        assert g.trang_thai == "active"
        assert g.la_mau is True


# ── Chỉ chạy khi thấy bản gốc: hợp đồng với engine ───────────────────────────

@pytest.mark.skipif(_ban_goc() is None,
                    reason="khong thay voices_v3_turbo.json (venv engine)")
def test_tap_hop_ma_khop_ban_goc_hai_chieu():
    """🔴 Phép kiểm quan trọng nhất tệp này.

    So **hai chiều**, không chỉ một: thiếu một giọng thì ta bán hụt hàng đã có;
    thừa một giọng thì ta bán thứ không tồn tại, và khách phát hiện ra bằng cách
    mất tiền.
    """
    goc = set((_ban_goc() or {}).get("presets", {}))
    ta = {g.ma for g in gm.DANH_SACH}
    assert ta == goc, (
        f"\n  engine co ma ta KHONG khai : {sorted(goc - ta)}"
        f"\n  ta khai ma engine KHONG co : {sorted(ta - goc)}\n"
        "Sua `apps/ltt_voice/giong_mau.py`. Ma phai dung TUNG KY TU, ke ca dau.")


@pytest.mark.skipif(_ban_goc() is None,
                    reason="khong thay voices_v3_turbo.json (venv engine)")
def test_gioi_tinh_khop_ban_goc():
    goc = (_ban_goc() or {}).get("presets", {})
    doi = {"male": "nam", "female": "nu"}
    for g in gm.DANH_SACH:
        that = doi.get(str(goc[g.ma].get("gender") or ""))
        assert that is None or that == g.gioi, (
            f"{g.ma}: ta khai gioi={g.gioi!r}, engine noi {that!r}")


@pytest.mark.skipif(_ban_goc() is None,
                    reason="khong thay voices_v3_turbo.json (venv engine)")
def test_vung_mien_khop_mo_ta_ban_goc():
    """Vùng miền chỉ có trong chuỗi `description` (`"Nam · Bắc · …"`), không có
    cột riêng — nên đối chiếu bằng cách đọc mẩu giữa."""
    goc = (_ban_goc() or {}).get("presets", {})
    doi = {"Bắc": "bac", "Trung": "trung", "Nam": "nam"}
    for g in gm.DANH_SACH:
        phan = [p.strip() for p in str(goc[g.ma].get("description") or "").split("·")]
        if len(phan) < 2:
            continue
        that = doi.get(phan[1])
        assert that is None or that == g.vung, (
            f"{g.ma}: ta khai vung={g.vung!r}, mo ta cua engine noi {phan[1]!r}")


@pytest.mark.skipif(_ban_goc() is None,
                    reason="khong thay voices_v3_turbo.json (venv engine)")
def test_mac_dinh_khop_ban_goc():
    assert (_ban_goc() or {}).get("default_voice") == gm.MAC_DINH, (
        "giong mac dinh cua ta lech khoi `default_voice` cua engine")
