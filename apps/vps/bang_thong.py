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

Cổng vào Vultr có **2 TB/tháng**. Bán hết 16 máy Nhỏ là hứa 4,8 TB — chồng 2,4
lần. Đó là chủ ý, cùng khuôn với đĩa thin (V14): phần lớn khách dùng một phần nhỏ
hạn mức. Nhưng nó **là** một rủi ro, không phải một mẹo — nếu nhiều khách cùng
chạm trần thì chính cổng vào bị Vultr tính thêm tiền. `tong_da_hua_gb()` có ở đây
để theo dõi con số đó thay vì phát hiện nó trên hoá đơn.
"""
from __future__ import annotations

from apps.vps.cost import lay_plan

#: Băng thông cổng vào Vultr được bao gồm mỗi tháng (gói `vhp-1c-1gb-amd`).
TRAN_CONG_VAO_GB = 2048


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
    nhìn thấy trước khi Vultr gửi hoá đơn, chứ không phải sau.
    """
    tong = 0
    for m in may_list:
        plan = lay_plan(m.plan_id)
        if plan is not None:
            tong += max(0, int(getattr(plan, "bang_thong_gb", 0)))
    return tong
