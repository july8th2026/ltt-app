"""Cộng dồn băng thông của từng máy, và quyết định khi nào hãm tốc.

## Vì sao không đọc thẳng bộ đếm của router

`nft` trả về con số **tích luỹ từ lúc nạp ruleset**, không phải "đã dùng bao
nhiêu trong chu kỳ này". Nó về 0 mỗi lần:

* router khởi động lại,
* ai đó chạy lại `cai-dat-router.sh`,
* phần tử bị xoá rồi thêm lại (máy được cài lại).

Đọc thẳng nó thì sau một lần khởi động lại, mọi khách đang gần chạm trần bỗng
"chưa dùng gì" — và hạn mức thành vô nghĩa mà không ai để ý. Ngược lại, nếu ai đó
"sửa" bằng cách lấy hiệu số mà quên xử lý trường hợp về 0, thì lần khởi động lại
sẽ cho ra một hiệu **âm**, và một hiệu âm cộng vào tổng sẽ **hoàn lại** băng thông
cho khách.

Nên ở đây làm đúng khuôn cộng dồn có xử lý đặt lại:

    delta = so_hien_tai - moc_lan_truoc      nếu so_hien_tai >= moc
    delta = so_hien_tai                      nếu nhỏ hơn (bộ đếm đã về 0)

## Hạn mức là mức HÃM, không phải mức CẮT

Trang bán viết: *"Băng thông có hạn mức theo gói. Vượt hạn mức thì bị giảm tốc,
không bị tính thêm tiền."* Nên vượt trần thì địa chỉ vào set `giam_toc` của
router; máy vẫn chạy, vẫn RDP được, chỉ chậm. Cắt hẳn biến câu trên thành một lời
nói dối, và tính thêm tiền cũng vậy.

## Bán chồng, và nói thẳng ra

Cổng vào nay là **OVH VPS-1 2027** (`vps-1a9e4515.vps.ovh.ca`, zone `os-sgp2`),
không còn là Vultr — hằng số `TRAN_CONG_VAO_GB = 2048` (chú thích "Vultr 2 TB")
đã SAI kể từ ngày đổi nhà cung cấp, và không ai sửa cho tới khi phiên
2026-09-23 đo lại. Bán hết các gói là hứa nhiều hơn 1 TB/tháng thật của OVH —
chủ ý, cùng khuôn với đĩa thin (V14): phần lớn khách dùng một phần nhỏ hạn mức.
Nhưng nó **là** một rủi ro, không phải một mẹo — nếu nhiều khách cùng chạm trần
thì cả cổng vào (kể cả VM100-107, việc thật của chủ dự án) bị OVH hãm xuống 10
Mbps. `tong_da_hua_gb()` và `ngan_sach_hua_gb()` có ở đây để theo dõi và giới
hạn con số đó thay vì phát hiện nó trên hoá đơn — xem
`docs/superpowers/specs/2026-09-23-vps-ban-that-design.md` mục 4.

## Ngân sách thật — vì sao trừ nền rồi mới nhân bán chồng

    Tran OVH VPS-1 SGP                          1.024 GB/thang
    - Nen production (VM100-107), do that          512 GB
    - Du tru an toan 15%                           154 GB
    -----------------------------------------------------
    = Ngan sach THAT cho khach                     358 GB/thang
    x He so ban chong 2,5 (cong khai, giam sat)
    -----------------------------------------------------
    = Ngan sach HUA cho khach                      895 GB/thang

`NEN_PRODUCTION_GB = 512` là số đo THẬT trên card `ens3` của cổng vào qua 27,75
ngày (RX 234,5 GB + TX 239,4 GB) — không phải số khai, đổi cổng vào thì đo lại
chứ đừng sửa tay. `TY_LE_DU_TRU = 0.15` là khoảng đệm trước vạch hãm 10 Mbps —
vạch đó đập vào **cả VM100-107**, nên phải có đệm trước khi chạm chứ không phải
phản ứng sau khi đã chạm.
"""
from __future__ import annotations

import os

from apps.vps.cost import lay_plan

#: Hạn mức băng thông cổng vào mỗi tháng, tính bằng GB.
#:
#: Nguồn: OVH công bố VPS ở Mumbai/Singapore/Sydney có hạn mức tháng **1 TB**
#: cho VPS-1 và VPS-2, vượt thì hãm xuống 10 Mbps
#: (ovhcloud.com/en-sg/vps/unmetered-vps/, chân trang, đọc 23/09/2026).
TRAN_CONG_VAO_GB = 1024

#: Băng thông nền production (VM100-107) chiếm mỗi tháng — đo THẬT trên `ens3`
#: của cổng vào qua 27,75 ngày: RX 234,5 GB + TX 239,4 GB ≈ 512 GB. Đọc từ biến
#: môi trường `LTT_VPS_NEN_GB` nếu có khai (số nguyên hợp lệ), mặc định số đo
#: này. Đổi cổng vào hay đổi việc thật đang chạy thì đo lại, đừng sửa tay.
NEN_PRODUCTION_GB = 512

#: Dự trữ an toàn trước vạch hãm 10 Mbps của OVH — vạch đó đập vào CẢ cổng vào,
#: gồm cả VM100-107, nên ngân sách phải chừa khoảng trước khi chạm, không phải
#: phản ứng sau khi đã chạm.
TY_LE_DU_TRU = 0.15

#: Hệ số bán chồng công khai trên trang bán, có giám sát ở lớp 2 của
#: `apps/vps/bao_tri.py` (`_can_ham_theo_tong`) — cùng khuôn với đĩa thin V14.
HE_SO_BAN_CHONG = 2.5

#: Cờ môi trường: OVH KHÔNG nói rõ họ đếm băng thông một chiều hay hai chiều.
#: Mặc định giả định HAI CHIỀU (thận trọng hơn — ngân sách ra số NHỎ hơn). Đặt
#: "false" khi xác định được OVH chỉ đếm chiều ra: khi đó nền chỉ còn tính một
#: nửa, vì nửa còn lại (chiều vào) không còn tính vào hạn mức chung nữa.
_CO_DEM_HAI_CHIEU = "LTT_VPS_DEM_HAI_CHIEU"
_CO_NEN_GB = "LTT_VPS_NEN_GB"


def _doc_nen_gb_moi_truong(env: dict | None = None) -> int:
    """`NEN_PRODUCTION_GB` mặc định, có xét biến môi trường và cờ một/hai chiều.

    Tách khỏi `ngan_sach_hua_gb` để hàm đó nhận thẳng `nen_gb` khi test muốn
    kiểm một con số cụ thể mà không phải xoay biến môi trường.
    """
    src = os.environ if env is None else env
    nen = NEN_PRODUCTION_GB
    raw = str(src.get(_CO_NEN_GB, "")).strip()
    if raw:
        try:
            nen = int(raw)
        except ValueError:
            nen = NEN_PRODUCTION_GB
    dem_hai_chieu = str(src.get(_CO_DEM_HAI_CHIEU, "true")).strip().lower() != "false"
    if not dem_hai_chieu:
        nen = nen // 2
    return max(0, nen)


def ngan_sach_hua_gb(*, tran_gb: int | None = None, nen_gb: int | None = None) -> int:
    """GB đã hứa tối đa được phép bán cho khách, mỗi tháng.

    = (tran - nen - tran * TY_LE_DU_TRU) * HE_SO_BAN_CHONG, sàn 0.

    Mặc định (tran=1024, nen=512): (1.024 - 512 - 153,6) = 358,4 → 358 →
    × 2,5 = **895**. Sàn 0: nền vượt trần (đo hỏng, hoặc việc thật phình ra)
    không bao giờ được trả về một ngân sách ÂM — đó là hứa bán cho khách một
    thứ đã âm sẵn.

    `tran_gb`/`nen_gb` để `None` thì đọc hằng số / môi trường ở trên — tách
    tham số ra để test không phải xoay biến môi trường mỗi lần kiểm một
    trường hợp.
    """
    if tran_gb is None:
        tran_gb = TRAN_CONG_VAO_GB
    if nen_gb is None:
        nen_gb = _doc_nen_gb_moi_truong()
    du_tru = tran_gb * TY_LE_DU_TRU
    that_gb = int(tran_gb - nen_gb - du_tru)
    that_gb = max(0, that_gb)
    return int(that_gb * HE_SO_BAN_CHONG)


def cong_don(cu: int, moc_cu: int, hien_tai: int) -> tuple[int, int]:
    """`(tổng_mới, mốc_mới)` sau một lần đọc bộ đếm.

    `hien_tai < moc_cu` nghĩa là bộ đếm đã về 0 (router khởi động lại). Khi đó
    lấy nguyên `hien_tai` làm phần tăng — mất phần đã chạy giữa lần đọc cuối và
    lúc khởi động lại, nhưng **thà thiếu còn hơn âm**: một hiệu âm cộng vào tổng
    sẽ hoàn lại băng thông cho khách.
    """
    cu, moc_cu, hien_tai = max(0, int(cu)), max(0, int(moc_cu)), max(0, int(hien_tai))
    tang = hien_tai - moc_cu if hien_tai >= moc_cu else hien_tai
    return cu + tang, hien_tai


def han_muc_byte(plan_id: str) -> int:
    """Hạn mức của một gói, tính bằng byte. 0 = không khai (không hãm)."""
    plan = lay_plan(plan_id)
    if plan is None:
        return 0
    return max(0, int(getattr(plan, "bang_thong_gb", 0))) * 1024 ** 3


def vuot_han_muc(may) -> bool:
    tran = han_muc_byte(may.plan_id)
    return tran > 0 and int(may.bang_thong_byte or 0) >= tran


def phan_tram(may) -> int:
    """Đã dùng bao nhiêu phần trăm hạn mức. Trần 999 để không vỡ bố cục trang."""
    tran = han_muc_byte(may.plan_id)
    if tran <= 0:
        return 0
    return min(999, int(int(may.bang_thong_byte or 0) * 100 / tran))


def doc_duoc(byte: int) -> str:
    """Số byte thành câu người đọc. Dùng GB/MB thập phân như nhà mạng vẫn dùng."""
    byte = max(0, int(byte or 0))
    if byte >= 1024 ** 3:
        return f"{byte / 1024 ** 3:.1f} GB"
    if byte >= 1024 ** 2:
        return f"{byte / 1024 ** 2:.0f} MB"
    return f"{byte / 1024:.0f} KB"


def tong_da_hua_gb(may_list) -> int:
    """Tổng hạn mức đã hứa cho các máy đang sống — để so với `TRAN_CONG_VAO_GB`.

    Vượt trần **không** phải lỗi (bán chồng là chủ ý), nhưng nó là con số cần
    nhìn thấy trước khi OVH hãm tốc cả cổng, chứ không phải sau.
    """
    tong = 0
    for m in may_list:
        plan = lay_plan(m.plan_id)
        if plan is not None:
            tong += max(0, int(getattr(plan, "bang_thong_gb", 0)))
    return tong
