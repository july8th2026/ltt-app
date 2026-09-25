"""So MA LOI ON DINH cua Auto Scan Video — MOT so, khong phai hai (I3).

`pipeline.GiaiDoan.ma_loi` khai ma; tep nay noi ma do **nghia gi voi khach** va
**credit co hoan hay khong**.

## 🔴 Vi sao so nay ton tai: G-04

`rang_giong.vi_sao_chua_rang` viet mot cau noi ro thieu gi tu 23/09, va cau do
dung lai o cot `error`. Man mot lan chay doc `outputs.ma_loi`, khong doc `error`
— nen khach doc mot cau chung chung KEM mot nut **"Thu lai buoc nay"** chac chan
hong (AUTO_MATCH tren cung ban chep loi cho ra dung ket qua do). Mot ma loi
khong co cau tuong ung la mot cua loi noi doi.

## ⛔ Va vi sao no KHONG duoc la bo thu hai

`quan_sat.LOI_CO_MA` da co truoc tep nay. Chep cau sang day se la ban thu hai
cua cung mot cau, va kho nay dinh dung bay do **ba lan trong hai ngay**
(`hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`).

⇒ Nen huong phu thuoc duoc dao lai, khong phai chep:

        rang_giong.CAU_CHUA_RANG  ─┐
        (hai cau lech lan o day)  ─┴─>  ma_loi.SO_MA  ─>  quan_sat.LOI_CO_MA

  `quan_sat.LOI_CO_MA` gio **dan xuat** tu `SO_MA`, va
  `tests/test_3200::test_SO_MA_KHONG_la_ban_thu_hai_cua_LOI_CO_MA` so bang `is`
  chu khong bang `==`, nen mot ban sao khong lot qua duoc.

## ⚠️ HIEN TRANG do duoc 24/09: 10 tren 12 mat xich KHONG co ma on dinh

Grep ca kho: **mot cho duy nhat** nem ngoai le mang `ma_loi=`
(`giai_doan_noi_dung.py:142`), cong mot cho gian tiep (`giong_noi.py:184` nem lai
`GiongKhongHopLe(ma_loi=exc.ma)`, chay trong `voice_synthesis`).
`thi_hanh.py:565` la nguoi doc duy nhat.

⇒ Muoi mat xich con lai hong bang **chuoi tu do**, tuc `outputs.ma_loi` cua chung
  luon rong. G-04 khong phai mot ca le o `content_process` — no la hien trang cua
  ca chuoi, va chung khai `ma_loi=("",)` de dieu do DEM DUOC thay vi vo hinh.
"""
from __future__ import annotations

from platform_core.i18n import N_

from . import rang_giong

# ⭐ Ma cong khai cua `apps/ltt_voice/lan_ngon_ngu.py` — nhap vao chu khong go
#    lai, de doi ma o `ltt_voice` thi day do chu khong lech im lang.
from apps.ltt_voice.lan_ngon_ngu import (  # noqa: E402  (sau `.rang_giong` co y)
    MA_LOI_LAN_KHONG_RO, MA_LOI_LECH_LAN)

#: Ma ON DINH -> cau khach doc duoc (khuon `N_()`, chua dich).
#:
#: ⛔ `N_` chu khong `_t`: hang so cap MODULE. `_t` o day dong bang ngon ngu cua
#:    request DAU TIEN vao mot bien toan cuc — xem `routes.NHAN_GIAI_DOAN`.
SO_MA: dict[str, str] = {
    # ── Giong khac lan voi loi long tieng (`voice_synthesis`) ───────────────
    #
    # W4': giong da DONG BANG vao ban long tieng, nen thu lai buoc doc van gap
    # dung giong do.
    MA_LOI_LECH_LAN: N_(
        "Giọng đã chọn không cùng ngôn ngữ với lời lồng tiếng, nên chúng tôi "
        "dừng lại trước khi đọc thay vì giao một bản đọc sai giọng. Hãy tạo "
        "lần chạy mới với một giọng cùng ngôn ngữ với lời lồng tiếng."),
    MA_LOI_LAN_KHONG_RO: N_(
        "Giọng đã chọn chưa xác định được ngôn ngữ nên chưa dùng để đọc được. "
        "Hãy tạo lần chạy mới với một giọng đã ghi rõ Tiếng Việt hoặc Tiếng Anh."),
    # ── AUTO_MATCH khong rang duoc giong (`content_process`) ────────────────
    #
    # ⭐ Khong chep cau vao day: `rang_giong.CAU_CHUA_RANG` la ban duy nhat.
    **rang_giong.CAU_CHUA_RANG,
}

# ⭐ **`HOAN_CREDIT` da bi XOA — 25/09/2026, gia phang.**
#
#    No la mot ban khai chinh sach hoan tien **theo tung ma loi**: ba ma
#    `auto_match_*` duoc hoan (tien da tieu truoc khi chung nem), hai ma
#    `voice_language_*` thi khong (khach tu chon giong lech lan). Chinh docstring
#    cua no tu khai *"CHUA CO NGUOI DOC"* tu ngay duoc viet.
#
# 🔑 Gia phang lam ca cau hoi ay bien mat, ⛔ khong chi lam no thua: tien duoc thu
#    **chi khi** lan chay ve `done` VA co hien vat giao duoc
#    (`features.CHI_THU_KHI_GIAO_DUOC` + `co_hien_vat_giao_duoc`). Moi ket cuc
#    khac — moi ma loi, khong tru ma nao — hoan **100 %**. Nen mot bang phan biet
#    "ma nao duoc hoan" la mot bang phan biet giua hai thu nay **giong het nhau**.
#
# ⛔ Dung dung lai no. Neu mot ngay gia thoi phang, cau hoi phai duoc dat lai tu
#    dau o `features.quyet_toan` — ⛔ khong phai khoi phuc mot bang chua ai doc.


def la_ma(ma: str) -> bool:
    """`ma` co nam trong so chung khong. Chuoi rong -> `False`."""
    return bool(ma) and ma in SO_MA


def cau_cho_khach(ma: str) -> str:
    """Khuon cau (chua dich) cua `ma`; rong neu ma khong co trong so."""
    return SO_MA.get(str(ma or ""), "")
