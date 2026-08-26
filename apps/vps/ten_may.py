"""Tên máy — **nhãn hiển thị**, không phải hostname (D-01).

## Vultr có HAI trường; ta chỉ có một, và đó là một sự thật của sản phẩm

| Vultr | Nó là gì | Ta có? |
|---|---|---|
| `hostname` | tên **trong hệ điều hành**, Vultr ghi vào máy qua cloud-init | ❌ |
| `label` | tên **trong bảng điều khiển**, thuần hiển thị, đổi lúc nào cũng được | ✅ |

Khách **tự cài Windows từ đĩa ISO** (chốt 2026-08-24): không cloud-init, không
Cloudbase-Init, không sysprep. Nên nền tảng **không có cách nào** đặt tên bên
trong máy, và sẽ không có chừng nào mô hình bán còn là *"máy trống + đĩa cài"*.

⚠️ Ghi điều đó ra đây vì cái tên `VpsInstance.ten` **không tự nói ra** rằng nó
   không phải hostname — và một phiên sau sẽ đoán rằng nó là hostname rồi đi tìm
   chỗ ghi nó vào máy.

## Vì sao tên phải NGẮN, và đó là lý do kỹ thuật chứ không phải gu

Ba thao tác không hoàn tác được (`cai-lai`, `khoi-phuc`, `xoa`) đòi khách **gõ
đúng tên máy** — khuôn của GitHub. Khuôn đó hiệu quả vì cái tên **có nghĩa với
người gõ**: gõ `may-ban-hang` là một khoảnh khắc dừng lại để nhận ra mình đang
xoá cái gì.

Trước D-01 thì `ten` luôn rỗng và nhánh thật đang chạy là `may.id[:8]` — tức để
xoá máy của mình, khách phải chép tay `a3f9c1d0`. **Chép–dán không có khoảnh
khắc dừng lại đó**, tức rào chắn đang chạy ở dạng tệ nhất của nó.

Nên cũng không chép khuôn DigitalOcean (`ubuntu-s-1vcpu-1gb-nyc1-01`): một tên
20+ ký tự là một tên **sẽ bị chép–dán**, và rào chắn lại mất tác dụng. `vps-01`
gõ được bằng tay trong hai giây.

## Tên do khách đặt nên khách đặt được `ab`

Chấp nhận, và Vultr · GitHub · DigitalOcean đều chấp nhận: rào chắn này chống
**bấm nhầm**, không chống một người cố tình tự làm hại mình. Độ dài tối thiểu 2
chỉ để tên còn là một cái tên.
"""
from __future__ import annotations

import re

from sqlalchemy import select

#: Giới hạn độ dài. Cột là `String(80)`; 40 là thừa chỗ, và giữ tên vừa một dòng
#: trên thẻ máy ở 390px.
DAI_TOI_THIEU = 2
DAI_TOI_DA = 40

#: Tiền tố của tên tự sinh. Đổi nó là đổi tên **máy mới**, không đổi máy đã có.
TIEN_TO = "vps"

#: Ký tự cho phép: chữ (kể cả dấu tiếng Việt), số, `-`, `_`, khoảng trắng.
#:
#: `\w` với `re.UNICODE` đã gồm chữ có dấu — **không** liệt kê tay bảng chữ cái
#: tiếng Việt: một bảng gõ tay sẽ thiếu đúng ký tự mà người dùng thứ nhất cần,
#: và nó thiếu một cách im lặng (tên bị từ chối, không ai biết vì sao).
_HOP_LE = re.compile(r"^[\w\-. ]+$", re.UNICODE)


class TenKhongHopLeError(ValueError):
    """Tên không dùng được. Câu lỗi viết cho **khách đọc**, không cho log."""


def chuan_hoa(ten: str) -> str:
    """Cắt khoảng trắng hai đầu, gộp khoảng trắng liên tiếp.

    🔑 Bắt buộc, không phải làm đẹp: `"may  A "` và `"may A"` phải là **một**
    tên. Thiếu bước này thì khách gõ tên vào ô xác nhận phá huỷ sẽ bị từ chối
    một chuỗi **trông giống hệt** cái đang hiện trên màn hình — và không có cách
    nào để họ tự thấy khoảng trắng thừa.
    """
    return re.sub(r"\s+", " ", str(ten or "")).strip()


def kiem(ten: str) -> str:
    """Chuẩn hoá và kiểm một tên. Trả tên đã chuẩn hoá, hoặc ném lỗi."""
    from platform_core.i18n import _ as _t

    ten = chuan_hoa(ten)
    if len(ten) < DAI_TOI_THIEU:
        raise TenKhongHopLeError(
            _t("Tên máy phải có ít nhất %(n)s ký tự.") % {"n": DAI_TOI_THIEU})
    if len(ten) > DAI_TOI_DA:
        raise TenKhongHopLeError(
            _t("Tên máy dài quá %(n)s ký tự.") % {"n": DAI_TOI_DA})
    if not _HOP_LE.match(ten):
        raise TenKhongHopLeError(
            _t("Tên máy chỉ được dùng chữ, số, dấu gạch ngang, gạch dưới, "
               "dấu chấm và khoảng trắng."))
    return ten


def _dang_dung(db, user_id: str, tru_id: str = "") -> set[str]:
    """Tên đang dùng của một khách, **không tính máy đã xoá**.

    Máy đã xoá không tính vì tên của nó không còn hiện ở đâu — giữ nó lại chỉ
    làm khách không đặt lại được một cái tên họ vừa thôi dùng.
    """
    from apps.vps.tables import VpsInstance

    q = select(VpsInstance.id, VpsInstance.ten).where(
        VpsInstance.user_id == str(user_id),
        VpsInstance.trang_thai != "da_xoa")
    return {chuan_hoa(t).casefold()
            for i, t in db.execute(q) if t and str(i) != str(tru_id)}


def kiem_va_doc_nhat(db, user_id: str, ten: str, *, tru_id: str = "") -> str:
    """Kiểm tên VÀ kiểm nó chưa bị một máy khác của cùng khách dùng.

    ⚠️ Duy nhất là **lý do an toàn**, không phải lý do gọn gàng: hai máy trùng
       tên làm ô xác nhận phá huỷ trở nên mơ hồ — khách gõ đúng một cái tên và
       không có gì nói cho họ biết cái tên đó ứng với máy nào.

    So sánh **không phân biệt hoa thường** (`casefold`): `May A` và `may a` khác
    nhau với máy nhưng giống hệt nhau với mắt người, và cái mắt người đọc mới là
    thứ rào chắn kia dựa vào.
    """
    from platform_core.i18n import _ as _t

    ten = kiem(ten)
    if ten.casefold() in _dang_dung(db, user_id, tru_id):
        raise TenKhongHopLeError(
            _t("Bạn đã có một máy tên “%(ten)s”. Chọn tên khác.") % {"ten": ten})
    return ten


def tu_sinh(db, user_id: str) -> str:
    """Tên tự sinh cho một máy mới: `vps-01`, `vps-02`, …

    Đếm tới khi gặp số chưa dùng, thay vì `len(may) + 1`: khách có `vps-01` và
    `vps-03` (đã xoá `vps-02`) thì phép cộng cho ra `vps-03` — một tên **đã tồn
    tại**, và lỗi đó chỉ lộ ra ở bước kiểm trùng, dưới dạng một câu lỗi khó hiểu
    cho một tên mà khách không hề gõ.

    Trần 999 là chốt chặn vòng lặp, không phải hạn mức sản phẩm: một khách có
    999 máy là một chuyện cần người nhìn, không phải một chuyện cần một vòng
    `while True`.
    """
    da_dung = _dang_dung(db, user_id)
    for i in range(1, 1000):
        ten = f"{TIEN_TO}-{i:02d}"
        if ten.casefold() not in da_dung:
            return ten
    # Không ném lỗi: khách không được chặn tạo máy vì một quy ước đặt tên. Rơi
    # về id là xấu nhưng dùng được, và nó là đúng hành vi cũ.
    return ""
