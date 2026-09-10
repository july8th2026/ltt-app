"""Hợp đồng **năng lực sao lưu**: cái gì có thật, cái gì chưa, và nói ra cho đúng.

## Vì sao tệp này tồn tại dù chưa có PBS

Sản phẩm hiện có **một** lớp bảo vệ dữ liệu: ảnh chụp LVM-thin, **cùng pool** với
đĩa gốc (`services/sao_luu.py`). Nó cứu khách khỏi lỗi của chính họ, và không cứu
khỏi hỏng phần cứng.

Thiếu lớp thứ hai không phải là một lỗi của mã. Nhưng **không nói ra** thì là:
một trang máy hiện "Sao lưu: hằng tuần ✓" bên cạnh một ảnh chụp cùng pool là một
lời hứa mà người ta chỉ phát hiện sai đúng vào lúc mất dữ liệu.

Nên tệp này khai **năng lực**, không khai tính năng:

| Lớp | Có ở đây chưa | Cứu được gì |
|---|---|---|
| A · ảnh chụp cục bộ | ✅ có | xoá nhầm, bản vá hỏng, phần mềm cài vào rồi không gỡ được |
| B · sao lưu độc lập (PBS/khác) | ❌ **chưa** | hỏng đĩa, hỏng pool, hỏng cả node |
| C · bản sao ngoài site | ❌ chưa | cháy, trộm, mã độc tống tiền, sập nhà cung cấp |

## Fail-closed, và đây là một fail-closed KHÁC thường

Thiếu cấu hình ⇒ `co_sao_luu_doc_lap()` trả `False` **và mang theo lý do**. Nó
không ném, không ghi log mỗi lượt, và tuyệt đối không tự bịa ra một trạng thái
"đang chờ backup đầu tiên" — trạng thái ấy trông y hệt một hệ đang chạy tốt.

Điểm khác: fail-closed thông thường chặn một hành động. Ở đây nó chặn một **lời
nói**. Hậu quả của việc quên nó không hiện ra ở lượt chạy nào cả — nó hiện ra ở
một lá thư của khách, nhiều tháng sau.

## Bí mật

`LTT_VPS_PBS_MAT_KHAU` và `LTT_VPS_PBS_VAN_TAY` đọc từ môi trường và **không bao
giờ** đi vào CSDL, sự kiện, hay log. `mo_ta_cau_hinh()` là đường DUY NHẤT để in
cấu hình ra, và nó chỉ in những trường an toàn — xem `_TRUONG_AN_TOAN`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

#: Biến môi trường mô tả một đích sao lưu độc lập.
#:
#: Tên trung tính (`PBS`) nhưng hợp đồng thì không ghim vào Proxmox Backup Server:
#: bất cứ đích nào có *failure domain độc lập* đều điền được vào đây. Điều kiện
#: là **độc lập thật**, không phải một thư mục khác trên cùng cái đĩa.
KHOA_MAY_CHU = "LTT_VPS_PBS_URL"
KHOA_KHO = "LTT_VPS_PBS_DATASTORE"
KHOA_NGUOI_DUNG = "LTT_VPS_PBS_USER"
KHOA_MAT_KHAU = "LTT_VPS_PBS_MAT_KHAU"      # noqa: S105 - ten bien, khong phai bi mat
KHOA_VAN_TAY = "LTT_VPS_PBS_VAN_TAY"

#: Trường nào được phép in ra ngoài (log, trang admin, sự kiện).
#:
#: Danh sách **cho phép**, không phải danh sách cấm: một danh sách cấm chỉ chặn
#: được thứ nó biết tên, và trường bí mật tiếp theo sẽ là trường không ai thêm
#: vào danh sách đó.
_TRUONG_AN_TOAN = ("may_chu", "kho", "nguoi_dung")

#: Sao lưu cũ hơn ngần này thì coi là **quá hạn**, dù nó tồn tại.
#:
#: Một tệp sao lưu có mặt không chứng minh dữ liệu khôi phục được, và một tệp
#: sao lưu từ tháng trước gần như chắc chắn là một job đã chết mà không ai biết.
QUA_HAN_SAU_NGAY = 2


class ChuaCauHinh(RuntimeError):
    """Chưa khai đích sao lưu độc lập. **Không phải lỗi** — là một sự thật."""


@dataclass(frozen=True)
class CauHinhDich:
    """Cấu hình một đích sao lưu độc lập. Bí mật KHÔNG nằm trong `__str__`."""

    may_chu: str
    kho: str
    nguoi_dung: str
    mat_khau: str = ""
    van_tay: str = ""

    def __str__(self) -> str:                        # pragma: no cover - tam thuong
        return f"CauHinhDich({self.may_chu}/{self.kho} as {self.nguoi_dung})"

    __repr__ = __str__


@dataclass(frozen=True)
class NangLuc:
    """Cái gì có thật ở deployment này. Trang máy đọc thẳng cấu trúc này.

    `ly_do` **không được rỗng** khi `sao_luu_doc_lap` là False: một tính năng bị
    tắt mà không nói vì sao là một ô xám mà khách không biết phải làm gì với nó.
    """

    anh_chup_cuc_bo: bool
    sao_luu_doc_lap: bool
    ly_do: str = ""
    dich: str = ""

    @property
    def chong_hong_phan_cung(self) -> bool:
        """Có chống được hỏng đĩa/pool/node không.

        Ảnh chụp cùng pool **không** tính, và đó là cả điểm của thuộc tính này:
        nó là câu trả lời cho *"mất một cái đĩa thì khách còn dữ liệu không"*, và
        nó phải trả `False` chừng nào chưa có lớp B.
        """
        return self.sao_luu_doc_lap


def doc_cau_hinh(env: dict | None = None) -> CauHinhDich:
    """Dựng cấu hình đích từ môi trường. Thiếu thứ bắt buộc → `ChuaCauHinh`.

    Ba trường bắt buộc; mật khẩu và vân tay là tuỳ chọn ở tầng này (đích có thể
    dùng token hoặc CA hệ thống). Việc **cưỡng chế** TLS thuộc về Pha 07.
    """
    src = os.environ if env is None else env
    may_chu = str(src.get(KHOA_MAY_CHU, "")).strip().rstrip("/")
    kho = str(src.get(KHOA_KHO, "")).strip()
    nguoi_dung = str(src.get(KHOA_NGUOI_DUNG, "")).strip()

    thieu = [ten for ten, gt in ((KHOA_MAY_CHU, may_chu), (KHOA_KHO, kho),
                                 (KHOA_NGUOI_DUNG, nguoi_dung)) if not gt]
    if thieu:
        raise ChuaCauHinh("thieu bien moi truong: " + ", ".join(thieu))
    return CauHinhDich(may_chu=may_chu, kho=kho, nguoi_dung=nguoi_dung,
                       mat_khau=str(src.get(KHOA_MAT_KHAU, "")),
                       van_tay=str(src.get(KHOA_VAN_TAY, "")).strip())


def nang_luc(env: dict | None = None) -> NangLuc:
    """Năng lực bảo vệ dữ liệu của deployment này. **Không gọi mạng.**

    Không gọi mạng có chủ ý: trang máy của khách gọi hàm này mỗi lần mở, và một
    lần gọi ra ngoài ở đó biến một đích sao lưu chậm thành một trang chậm cho
    mọi khách.

    Sức khoẻ **thật** của đích (lần sao lưu cuối, lần xác minh cuối) là việc của
    vòng bảo trì, không phải của một lượt render.
    """
    try:
        cf = doc_cau_hinh(env)
    except ChuaCauHinh as exc:
        return NangLuc(
            anh_chup_cuc_bo=True, sao_luu_doc_lap=False,
            ly_do=(f"chua khai dich sao luu doc lap ({exc}). Anh chup cuc bo "
                   f"van chay, nhung no nam CUNG KHO voi dia goc."))
    return NangLuc(anh_chup_cuc_bo=True, sao_luu_doc_lap=True,
                   dich=f"{cf.may_chu}/{cf.kho}")


def mo_ta_cau_hinh(cf: CauHinhDich) -> dict:
    """Cấu hình ở dạng in được — **chỉ** những trường trong danh sách cho phép.

    Đường DUY NHẤT để đưa cấu hình ra log/trang admin/sự kiện. Một `nssm get` in
    sạch khoá production ra log đã xảy ra ở dự án này một lần rồi.
    """
    return {k: getattr(cf, k) for k in _TRUONG_AN_TOAN}


def qua_han(lan_cuoi: datetime | None, *, now: datetime | None = None,
            han_ngay: int = QUA_HAN_SAU_NGAY) -> bool:
    """Bản sao lưu gần nhất đã quá hạn chưa.

    **`None` tính là quá hạn.** Chưa từng sao lưu và sao lưu từ tháng trước cho
    cùng một lượng bảo vệ: không có gì. Trả `False` cho `None` là biến "chưa bao
    giờ chạy" thành "vẫn ổn" — đúng loại im lặng mà lớp này sinh ra để phá.
    """
    if lan_cuoi is None:
        return True
    if lan_cuoi.tzinfo is None:
        lan_cuoi = lan_cuoi.replace(tzinfo=timezone.utc)
    moc = now or datetime.now(timezone.utc)
    return lan_cuoi <= moc - timedelta(days=han_ngay)


def da_xac_minh(lan_xac_minh: datetime | None, lan_sao_luu: datetime | None
                ) -> bool:
    """Bản sao lưu gần nhất đã được **xác minh** chưa.

    Một tệp sao lưu tồn tại không phải bằng chứng dữ liệu khôi phục được. Xác
    minh phải **mới hơn** bản sao lưu nó xác minh — một lần xác minh cũ hơn nói
    về một bản khác.
    """
    if lan_xac_minh is None or lan_sao_luu is None:
        return False
    a = lan_xac_minh if lan_xac_minh.tzinfo else lan_xac_minh.replace(
        tzinfo=timezone.utc)
    b = lan_sao_luu if lan_sao_luu.tzinfo else lan_sao_luu.replace(
        tzinfo=timezone.utc)
    return a >= b
