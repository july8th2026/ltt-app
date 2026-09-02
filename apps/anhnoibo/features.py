"""
features.py — quy tắc nghiệp vụ của `anhnoibo`, dùng chung cho MỌI cánh cửa. (H37/L6)

    cua bat dong bo :  POST /api/v1/jobs  -> worker -> jobs.py::handle -> đây
    cua giao dien   :  bảng điều khiển                                 -> đây
    (cửa thứ ba, nếu có, cũng đi qua đây)

⭐ VÌ SAO GOM VÀO ĐÂY thay vì để trong `jobs.py`. Hôm nay app chỉ có một cửa nên
   chưa đau. Nhưng `ltt_llm` cũng chỉ có một cửa cho tới ngày nó có hai, và lúc
   đó mọi quy tắc trong `jobs.py` phải chép sang cửa mới. Hai bản chép sẽ lệch
   nhau, và ngày chúng lệch là ngày **cùng một yêu cầu bị tính hai giá khác
   nhau** — `public_api/costing.py` gọi đó là "parallel engines" và cấm.

⛔ `routes.py` không phải chỗ chứa nghiệp vụ, và `jobs.py` cũng vậy —
   `AGENTS.md` mục 8. App này một miền nên nghiệp vụ ở `features.py`.

⛔ GIÁ KHÔNG Ở ĐÂY. Nó ở `gia.py`, một mình. File này **gọi** `gia.tinh`, không
   khai lại con số nào.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from platform_core.i18n import _ as _t
from platform_core.jobs import LoiNguoiGoi

from . import gia

#: Tối đa hai ảnh tham chiếu. Thêm nữa thì mỗi ảnh bị thu nhỏ và chất lượng giảm
#: — cổng render cũng chốt cùng con số này (`spec.max_refs`).
MAX_REF = 2

CHE_DO_HOP_LE = ("t2i", "edit", "subject")

#: ⭐ ALIAS CÔNG KHAI -> ID NỘI BỘ. Lớp đệm, và nó có lý do sống: ngày ta đổi
#:    model thì **mã của khách không phải sửa một dòng nào**. Id nội bộ lọt ra
#:    một bề mặt khách đọc được là tích hợp bắt đầu ghim vào nó (`test_212`).
ALIAS_SANG_ID = {"image.ltt": "hidream-o1"}

MODEL_NOI_BO_MAC_DINH = "hidream-o1"


class LoiTaoAnh(Exception):
    """Lỗi hiện cho người dùng. Không kèm chi tiết hạ tầng.

    Đây là lỗi **hạ tầng** (cổng render hỏng, kho không cấp được vé, chưa cấu
    hình) — nền tảng ĐƯỢC thử lại. Lỗi của *yêu cầu* thì dùng `LoiYeuCauAnh`.
    """


class LoiYeuCauAnh(LoiTaoAnh, LoiNguoiGoi):
    """Yêu cầu sai ngay từ đầu (thiếu mô tả, ảnh tham chiếu của người khác…).

    ⛔ Kế thừa `platform_core.jobs.LoiNguoiGoi` để nền tảng **không thử lại**:
       chạy lại y hệt sẽ hỏng y hệt. Trước 03/09/2026 mọi lỗi của `chuan_hoa`
       là `LoiTaoAnh` thường, rơi vào nhánh `retry` — ba lượt thử, ba lần chờ,
       cho một khoá ảnh mà cửa vào đã biết là của người khác. Cùng lớp lỗi
       `LoiNguoiGoi` được sinh ra để sửa (job `a49ce0d3`, 31/08).

    Vẫn là `LoiTaoAnh` để mọi chỗ đang `except LoiTaoAnh` không đổi.
    """


@dataclass(frozen=True)
class YeuCauAnh:
    """Một yêu cầu ĐÃ ĐƯỢC KIỂM. Dựng xong nghĩa là mọi quy tắc đã qua."""
    prompt: str
    che_do: str
    so_anh: int
    ref_keys: tuple = ()
    negative_prompt: str = ""
    owner_id: str = ""

    @property
    def dung_tham_chieu(self) -> bool:
        return self.che_do in gia.CHE_DO_THAM_CHIEU

    def tran_credit(self) -> int:
        """Trần giữ chỗ. Ước CAO có chủ ý — xem `gia.uoc_tran`."""
        return gia.uoc_tran(so_anh_xin=self.so_anh, che_do=self.che_do)


def _kiem_chu_so_huu(khoa: str, owner_id: str) -> str:
    """Khoá lưu trữ có dạng `{app}/{user_id}/{job_id}/...`.

    Kiểm **đoạn thứ hai**, không phải tiền tố app: ảnh tham chiếu hợp lệ có thể
    là artifact của một job trước ở app khác của **cùng người dùng đó**.

    ⛔ Không kiểm thì khách A đọc được ảnh của khách B chỉ bằng cách đoán khoá.
    """
    phan = str(khoa or "").strip("/").split("/")
    if len(phan) < 2 or phan[1] != owner_id:
        raise LoiYeuCauAnh(_t('Ảnh tham chiếu không thuộc người dùng hiện tại.'))
    return khoa


def chuan_hoa(params: dict) -> YeuCauAnh:
    """Đọc tham số thô của bất kỳ cửa nào và trả về một yêu cầu đã kiểm.

    Ném `LoiTaoAnh` với câu chữ khách đọc được. Không chạm mạng, không chạm CSDL,
    không chạm GPU — nên cửa nào cũng gọi được, kể cả để **báo giá trước**.
    """
    prompt = str(params.get("prompt") or "").strip()
    if not prompt:
        raise LoiYeuCauAnh(_t('Chưa nhập mô tả ảnh.'))

    che_do = str(params.get("mode") or "t2i")
    if che_do not in CHE_DO_HOP_LE:
        raise LoiYeuCauAnh(_t('Chế độ không hợp lệ: {ten}').format(ten=che_do))

    owner_id = str(params.get("owner_id") or "").strip()

    # Gom hai đường vào một: `image_key` (đường API, một ảnh) và `image_keys`
    # (đường giao diện, tối đa hai). Xem chú thích ở manifest vì sao có hai.
    refs = [str(k) for k in (params.get("image_keys") or []) if str(k).strip()]
    mot = str(params.get("image_key") or "").strip()
    if mot and mot not in refs:
        refs.insert(0, mot)

    if che_do in gia.CHE_DO_THAM_CHIEU and not refs:
        raise LoiYeuCauAnh(_t('Chế độ này cần ít nhất một ảnh tham chiếu.'))
    if che_do == "t2i" and refs:
        raise LoiYeuCauAnh(_t('Chế độ t2i không nhận ảnh tham chiếu.'))
    if len(refs) > MAX_REF:
        # ⛔ Không tự cắt bớt: cắt bớt là lặng lẽ giao một thứ khác thứ khách
        #    yêu cầu, và khách không có cách nào biết.
        raise LoiYeuCauAnh(_t('Tối đa {n} ảnh tham chiếu.').format(n=MAX_REF))
    if refs and not owner_id:
        # Không biết chủ sở hữu thì không kiểm được quyền — từ chối, đừng đoán.
        raise LoiYeuCauAnh(_t('Thiếu thông tin người dùng để kiểm ảnh tham chiếu.'))
    refs = [_kiem_chu_so_huu(k, owner_id) for k in refs]

    try:
        so_anh = int(params.get("count", 1))
    except (TypeError, ValueError):
        so_anh = 1
    so_anh = max(1, min(so_anh, gia.SO_ANH_TOI_DA))

    return YeuCauAnh(prompt=prompt, che_do=che_do, so_anh=so_anh,
                     ref_keys=tuple(refs),
                     negative_prompt=str(params.get("negative_prompt") or ""),
                     owner_id=owner_id)


@dataclass(frozen=True)
class KetQua:
    """Kết quả một lượt vẽ, và **hoá đơn của nó**."""
    yeu_cau: YeuCauAnh
    image_keys: tuple = ()
    prompt_da_gui: str = ""
    da_dich: bool = False
    canh_bao: tuple = ()

    @property
    def so_anh_that(self) -> int:
        return len(self.image_keys)

    def gia_that_credit(self) -> int:
        """🔴 TIỀN THẬT, tính theo ảnh **đã sinh ra được**.

        Cổng render trả về đúng số ảnh nó tải lên được (`image_keys[:so]` trong
        `render_gateway/runner.py`), nên "xin 4, nhận 2" là một kết cục có thật.

        Không báo con số này về cho nền tảng thì
        `job_runner._quyet_toan_credit` thu **trọn phần đã giữ** — khách trả
        tiền 4 ảnh cho 2 ảnh, im lặng. Đây đúng là lỗi H38 đã mắc và đã sửa.
        """
        return gia.tinh(so_anh=self.so_anh_that, che_do=self.yeu_cau.che_do)

    def as_result(self) -> dict:
        """Khuôn kết quả mà worker trả về nền tảng."""
        from platform_core.public_api import costing

        return {
            "image_keys": list(self.image_keys),
            "prompt": self.prompt_da_gui,
            "da_dich": self.da_dich,
            "canh_bao": list(self.canh_bao),
            "so_anh_xin": self.yeu_cau.so_anh,
            "so_anh_that": self.so_anh_that,
            "credit_cost": self.gia_that_credit(),
            "phien_ban_gia": gia.PHIEN_BAN_GIA,
            # Model nhà cũng có giá vốn — điện + khấu hao GPU, đo thật trên máy
            # B. `tham_chieu` đắt hơn hẳn, nên phải báo cả nó chứ không chỉ số ảnh.
            costing.KHOA_GOI_PROVIDER: [
                {"model": MODEL_NOI_BO_MAC_DINH, "count": self.so_anh_that,
                 "tham_chieu": self.yeu_cau.dung_tham_chieu}],
        }
