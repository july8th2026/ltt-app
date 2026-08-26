"""Menu trái của khu VPS — **dữ liệu**, không phải HTML chép tay.

## Vì sao là một mô-đun chứ không phải mấy thẻ `<a>` trong template

Trước 25/08, bốn trang VPS mỗi trang tự dựng `topbar_title` riêng và **không
trang nào biết trang kia tồn tại**. Đó là lý do `/vps/{id}` không có đường về
`/vps` — không phải ai quên thêm một liên kết, mà là không có chỗ nào để thêm.

Cổng lập trình viên đã giải đúng bài này (`server/routes/developer.py:SECTIONS`)
và bản này dùng lại nguyên khuôn: **thêm một trang = thêm một dòng**.

## Menu ĐỔI CẤP, và đó là hình dạng thật của dữ liệu

Khu VPS có bốn trang, và **ba trong bốn thuộc về một máy cụ thể**:

    /vps                     danh sách + tạo máy
    /vps/{id}                một máy
    /vps/{id}/cai-dat        hướng dẫn cài Windows cho máy đó
    /vps/{id}/console        console của máy đó

Nên menu ở cấp khu liệt kê **các máy**; menu khi đang trong một máy liệt kê
**các trang của máy đó** kèm một đường về. Cùng ý với Compute › Instances › một
instance của Vultr, nhưng diễn đạt bằng bốn trang của ta chứ không phải mười
lăm trang của họ.

## "Sắp có" là thông tin; một liên kết 404 thì không

Mục chưa có route hiện dạng mờ, không bấm được. Hình dạng của khu là thông tin
cho khách — nó nói ta đang đi đâu. Một liên kết chết thì chỉ nói ta cẩu thả.
"""
from __future__ import annotations

from typing import Any, Optional

from platform_core.i18n import N_, _ as _t

#: Tiền tố của khu. Một chỗ duy nhất — đổi `route_prefix` trong manifest là đổi
#: ở đây, không phải đi sửa mười chỗ trong template.
GOC = "/vps"

#: Mục **chưa có route**. Hiện mờ, không bấm được.
#:
#: Bốn mục dưới đây có thật trong kế hoạch (`docs/VPS/PHUONG_AN_BO_CUC_CONSOLE.md`
#: §3), không phải chỗ giữ chỗ cho vui. Thêm route xong thì chuyển nó lên
#: `_MUC_KHU` / `_MUC_MAY` và xoá khỏi đây.
SAP_CO_KHU: tuple[tuple[str, str], ...] = (
    ("sao_ke", N_("Sao kê")),
)
#: ⛔ `anh_chup` ĐÃ BỎ 2026-08-26 (D-04). Ta chụp **đúng một** bản, **tự động**
#: hằng tuần (`sao_luu.GIU = 1`), khách không tự chụp được — nên "trang ảnh chụp"
#: sẽ là một trang hiện **một hàng**, với một nút đã có sẵn trong khối Nguy hiểm
#: của trang máy. Đó là một trang ta không có lý do nào để xây, và luật ngay trên
#: đây tự cấm: mục "sắp có" phải *"có thật trong kế hoạch, không phải chỗ giữ chỗ
#: cho vui"*. Ngày nào cho khách tự chụp và giữ nhiều bản thì nó quay lại.
#:
#: `bang_thong` thì Ở LẠI, và từ 26/08 nó có lý do thật: `billing.thu_mot_chu_ky`
#: nay chụp `bang_thong_byte` vào sự kiện `thu_phi` trước khi đặt lại, nên sau
#: vài chu kỳ sẽ **có lịch sử** để trang đó nói một điều mà trang máy không nói
#: được — *"chu kỳ trước bạn dùng bao nhiêu"*.
SAP_CO_MAY: tuple[tuple[str, str], ...] = (
    ("bang_thong", N_("Băng thông")),
)


def _muc(khoa: str, nhan: str, href: Optional[str], active: str,
         *, nhom: bool = False, dich: bool = True) -> dict[str, Any]:
    """Một mục menu.

    `dich=False` cho **tên máy**: đó là dữ liệu của khách, không phải chuỗi
    giao diện. Đưa nó qua gettext là để ngỏ khả năng một ngày nào đó một tên
    máy trùng một msgid và bị đổi thành chữ khác.
    """
    return {
        "khoa": khoa,
        # Tra NGAY O DAY. `N_()` o cac hang so ben duoi chi DANH DAU de trich;
        # thieu buoc nay thi menu van tieng Viet tren ban `en` — va khong phep
        # kiem nao doc `.po` thay duoc, vi chuoi CO trong catalog va DA dich.
        "nhan": _t(nhan) if dich else nhan,
        "href": href,
        "active": khoa == active,
        # Tiêu đề nhóm: hiện ra để chia khối, nhưng không phải một liên kết.
        "nhom": nhom,
    }


def menu(active: str, *, may: Any = None, danh_sach_may: Any = ()) -> list[dict]:
    """Menu trái cho một trang trong khu VPS.

    `active` là khoá của trang đang mở. `may` khác `None` nghĩa là đang ở trong
    một máy — menu chuyển sang cấp máy.

    Trả về danh sách phẳng các dict; template chỉ việc lặp. Không có logic nào
    trong template vì logic trong template là logic không test được.
    """
    if may is not None:
        ma = str(getattr(may, "id", "") or "")
        ten = str(getattr(may, "ten", "") or "") or ma[:8]
        ra = [
            _muc("ve_khu", N_("← Tất cả máy"), GOC, active),
            _muc("ten_may", ten, None, active, nhom=True, dich=False),
            _muc("may", N_("Tổng quan"), f"{GOC}/{ma}", active),
            _muc("console", N_("Console"), f"{GOC}/{ma}/console", active),
            _muc("cai_dat", N_("Cài Windows"), f"{GOC}/{ma}/cai-dat", active),
        ]
        ra += [_muc(k, n, None, active) for k, n in SAP_CO_MAY]
        return ra

    ra = [
        _muc("tong_quan", N_("Tổng quan"), GOC, active),
        # Điều khoản là trang con của khu từ 26/08 (trước đó là một liên kết ra
        # site marketing, và site đó chưa bao giờ xuất bản nó — 404 suốt).
        _muc("dieu_khoan", N_("Điều khoản"), f"{GOC}/dieu-khoan", active),
    ]
    ds = list(danh_sach_may or ())
    if ds:
        ra.append(_muc("nhom_may", N_("Máy của tôi"), None, active, nhom=True))
        for m in ds:
            ma = str(m.get("id") if isinstance(m, dict) else getattr(m, "id", ""))
            ten = str((m.get("ten") if isinstance(m, dict)
                       else getattr(m, "ten", "")) or "") or ma[:8]
            ra.append(_muc(f"may:{ma}", ten, f"{GOC}/{ma}", active,
                           dich=False))
    ra += [_muc(k, n, None, active) for k, n in SAP_CO_KHU]
    return ra
