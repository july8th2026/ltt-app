"""Thu tiền VPS: trừ credit theo chu kỳ 30 ngày, treo rồi xoá khi hết tiền.

Sao chép **đúng khuôn Q98** (`platform_core/nexus/billing.py`), không phát minh lại:
trừ từ số dư credit đã có, không tự động quẹt thẻ. Nhờ vậy tránh hẳn thứ Q53 hoãn
(consent / hạn mức / chống phát lại của thẻ định kỳ). Khách nạp credit trong trình
duyệt qua PayOS (H9); ở đây chỉ trừ.

## Khác Nexus ở đúng một chỗ, và chỗ đó quan trọng

Nexus hết tiền thì **chỉ chặn điều khiển, không xoá gì** — máy là của khách, dữ liệu
là của khách, giữ lại không tốn gì của mình.

VPS thì ngược lại: máy nằm trên **đĩa của mình**, và đĩa là nút thắt. Một máy đã bỏ
mà giữ mãi là một chỗ không bán lại được. Vì thế V8 chốt: **treo ngay, xoá sau 7
ngày**. Con số 7 ngày không phải chuyện lịch sự — nó là chuyện còn chỗ để bán.

## Vòng thu phí PHẢI nằm sau một lease

Số tiến trình worker mặc định bằng số GPU. Một vòng thu phí chạy ở mọi tiến trình
sẽ trừ tiền khách N lần trong cùng một chu kỳ. `platform_core/leases.py` sinh ra
đúng để chống lớp lỗi này (H36) — người gọi có trách nhiệm bọc `thu_phi_dinh_ky`
trong một lease, y như `_mot_luot_bao_tri`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from apps.vps import trang_thai_may
from apps.vps.cost import CHU_KY_NGAY, credit_thang
from apps.vps.services.provisioning import ghi_su_kien
from apps.vps.tables import VpsInstance

log = logging.getLogger(__name__)

#: Treo bao lâu trước khi xoá vĩnh viễn (V8).
AN_HAN_TRUOC_KHI_XOA_NGAY = 7

#: Loại bút toán trong sổ credit. Một chuỗi riêng để đối soát tách được doanh thu
#: VPS khỏi doanh thu tool AI mà không phải đoán từ ghi chú.
KIND = "vps_thang"


class ThieuCreditError(RuntimeError):
    """Không đủ credit cho chu kỳ. Người gọi quyết định treo hay từ chối tạo."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def con_han(may: VpsInstance, *, now: datetime | None = None) -> bool:
    """Máy này đã trả tiền tới hiện tại chưa."""
    han = _aware(may.paid_until)
    return han is not None and han > (now or _now())


def con_bao_nhieu_ngay(may: VpsInstance, *, now: datetime | None = None):
    """Còn mấy ngày nữa hết hạn. `None` = chưa thu chu kỳ nào.

    Tách khỏi `con_han` (trả `bool`) vì giao diện cần **con số** để cảnh báo sớm:
    hết hạn là treo ngay và xoá sau 7 ngày (V8), nên khách phải thấy nó đang tới
    gần chứ không phải biết khi đã mất máy.

    Làm tròn XUỐNG, và không bao giờ trả số âm — quá hạn thì là 0, vì "còn −2
    ngày" không nói được gì cho người đọc.
    """
    han = _aware(may.paid_until)
    if han is None:
        return None
    con = (han - (now or _now())).total_seconds() / 86400
    return max(0, int(con))


def thu_mot_chu_ky(db: DbSession, may: VpsInstance, *,
                   now: datetime | None = None) -> int:
    """Trừ credit cho MỘT chu kỳ và đẩy `paid_until` lên. Trả số credit đã trừ.

    Cộng dồn từ `paid_until` cũ chứ không từ hôm nay: khách trả muộn hai ngày thì
    hai ngày đó vẫn thuộc chu kỳ đã trả, không bị mất. Trả sớm cũng không bị thiệt.
    """
    from platform_core import credit

    thoi_diem = now or _now()
    gia = credit_thang(may.plan_id, may.dia_them_gb)
    if gia <= 0:
        # Giá 0 = miễn phí (máy nội bộ, hoặc bảng giá chưa đặt). Vẫn đẩy hạn để
        # vòng quét không hỏi lại máy này mỗi phút.
        may.paid_until = _moc_ke_tiep(may, thoi_diem)
        _dat_lai_bang_thong(may)
        return 0

    so_du = credit.so_du(db, may.user_id)
    if so_du < gia:
        raise ThieuCreditError(
            f"can {gia} credit cho chu ky toi, so du con {so_du}")

    credit.tru(db, may.user_id, gia, kind=KIND,
               note=f"VPS {may.plan_id} — {CHU_KY_NGAY} ngay")
    may.paid_until = _moc_ke_tiep(may, thoi_diem)
    may.xoa_sau = None

    # 🔑 ĐỌC TRƯỚC KHI ĐẶT LẠI. `_dat_lai_bang_thong` đưa bộ đếm về 0, và ta
    # **không có bảng lịch sử băng thông** — nên mỗi chu kỳ trôi qua mà không
    # chụp lại con số này là một chu kỳ **mất vĩnh viễn**, không có bản sao nào
    # ở đâu để dựng lại.
    #
    # Chi phí để giữ nó: một trường trong `chi_tiet` của một sự kiện đã được ghi
    # sẵn ở đúng thời điểm này. Không bảng mới, không di trú, không route mới,
    # không đổi gì khách nhìn thấy. Đổi lại, sau vài chu kỳ ta có dữ liệu thật
    # để trả lời câu duy nhất đáng hỏi về băng thông: *"chu kỳ trước tôi dùng
    # bao nhiêu?"* — xem D-04 ở `docs/VPS/UI_MVP_V2/01_QUYET_DINH_D01_D04.md`.
    #
    # ⭐ Khuôn nên lặp lại: **dữ liệu không chụp là dữ liệu mất; giao diện thì
    #    lúc nào dựng cũng được.** Ghi trước, vẽ sau.
    da_dung_byte = int(may.bang_thong_byte or 0)
    _dat_lai_bang_thong(may)
    ghi_su_kien(db, may.id, "thu_phi", boi="he_thong",
                credit=gia, den=may.paid_until.isoformat(),
                bang_thong_byte=da_dung_byte)
    return gia


def _dat_lai_bang_thong(may: VpsInstance) -> None:
    """Chu kỳ mới, hạn mức mới: bộ đếm băng thông của chu kỳ về 0.

    KHÔNG đụng tới router ở đây. Cờ `bi_giam_toc` để nguyên; lượt đồng bộ kế
    tiếp thấy số đã dùng dưới trần và tự bỏ hãm — nhờ vậy `billing` không phải
    biết router là gì, và một router không trả lời không chặn được việc thu tiền.
    """
    may.bang_thong_byte = 0


def _moc_ke_tiep(may: VpsInstance, now: datetime) -> datetime:
    """Mốc hết hạn sau khi thu thêm một chu kỳ.

    Hai trường hợp, và ranh giới giữa chúng là chỗ dễ làm sai nhất:

    * **Trễ trong vòng một chu kỳ** (vòng thu chạy chậm vài giờ, hoặc khách nạp
      credit muộn hai ngày): cộng dồn từ **mốc cũ**. Máy vẫn chạy trong những
      ngày đó, nên tính từ hôm nay là biếu không khách phần đã chạy.
    * **Trễ hơn cả một chu kỳ** (máy bị treo lâu rồi khách nạp lại): bắt đầu lại
      **từ hôm nay**. Cộng dồn ở đây sẽ để lại một mốc vẫn nằm trong quá khứ —
      máy vừa thu xong đã hết hạn ngay, và vòng thu sẽ trừ tiếp mỗi lượt cho tới
      khi cạn sạch số dư của khách. Đó là lỗi nuốt tiền, không phải lỗi lệch ngày.
    """
    goc = _aware(may.paid_until)
    if goc is None:
        return now + timedelta(days=CHU_KY_NGAY)
    ke_tiep = goc + timedelta(days=CHU_KY_NGAY)
    return ke_tiep if ke_tiep > now else now + timedelta(days=CHU_KY_NGAY)


def treo(db: DbSession, may: VpsInstance, ly_do: str, *,
         now: datetime | None = None) -> None:
    """Treo máy: tắt nhưng **giữ nguyên đĩa**, và đặt mốc xoá.

    Chỉ đổi trạng thái trong CSDL. Việc tắt VM thật là của người gọi (nó cần
    client Proxmox, mà module này cố ý không biết Proxmox tồn tại).
    """
    thoi_diem = now or _now()
    # `bi_treo` là **vòng đời**, không phải trạng thái điện: nó nghĩa là hết hạn
    # thanh toán, và nó phải sống sót qua mọi thứ xảy ra với nguồn điện của máy.
    # Ý định đi kèm là `tat` (người gọi sẽ tắt cứng), nhưng ta chưa đo lại —
    # nên quan sát về `khong_ro`, không phải một khẳng định.
    trang_thai_may.dat(may, vong_doi=trang_thai_may.BI_TREO,
                       dien_mong_muon=trang_thai_may.TAT,
                       dien_quan_sat=trang_thai_may.KHONG_RO,
                       ly_do=ly_do)
    if may.xoa_sau is None:
        may.xoa_sau = thoi_diem + timedelta(days=AN_HAN_TRUOC_KHI_XOA_NGAY)
    ghi_su_kien(db, may.id, "bi_treo", boi="he_thong", ly_do=ly_do,
                xoa_sau=may.xoa_sau.isoformat())


def den_han_thu(db: DbSession, *, now: datetime | None = None) -> list:
    """Những máy tới kỳ phải thu. Máy đã xoá, đang tạo, hay đang treo không tính.

    Lọc `paid_until` bằng Python chứ không bằng SQL: điều kiện thật là *NULL hoặc
    đã quá hạn*, và hai engine (PostgreSQL khi chạy thật, SQLite khi chạy test) so
    sánh NULL với dấu `<` theo hai kiểu khác nhau. Số máy ở đây tính bằng hàng
    chục, không phải hàng triệu — lọc trong Python rẻ hơn nhiều so với một lỗi
    chỉ xuất hiện trên một trong hai engine.
    """
    thoi_diem = now or _now()
    return [
        m for m in db.execute(
            select(VpsInstance).where(
                VpsInstance.trang_thai.in_(("dang_chay", "da_tat")))
        ).scalars()
        if not con_han(m, now=thoi_diem)
    ]


def den_han_xoa(db: DbSession, *, now: datetime | None = None) -> list:
    """Những máy đã treo quá hạn ân hạn và phải xoá vĩnh viễn (V8)."""
    thoi_diem = now or _now()
    return [
        m for m in db.execute(
            select(VpsInstance).where(VpsInstance.trang_thai == "bi_treo")
        ).scalars()
        if _aware(m.xoa_sau) is not None and _aware(m.xoa_sau) <= thoi_diem
    ]


def thu_phi_dinh_ky(db: DbSession, *, now: datetime | None = None,
                    khi_treo=None) -> dict:
    """Một lượt thu phí cho mọi máy tới kỳ. **Phải chạy dưới một lease.**

    Trả về đếm số máy đã thu / đã treo, để người gọi ghi log một dòng có nghĩa
    thay vì im lặng.

    ## `khi_treo` — vì sao mặc định KHÔNG đủ

    Mặc định gọi `treo()` ở file này, và nó **chỉ ghi sổ**: đổi trạng thái, đặt
    hạn xoá. Máy vẫn **chạy tiếp trên Proxmox**. Nghĩa là một khách hết tiền vẫn
    dùng máy bình thường suốt 7 ngày ân hạn, và RAM vẫn bị giữ.

    Không gọi thẳng `services/dieu_khien.treo` (bản có tắt máy) vì `dieu_khien`
    đã import file này — vòng import. Nên người gọi tiêm vào: xem `bao_tri.py`,
    nơi có sẵn client Proxmox.
    """
    thoi_diem = now or _now()
    dat_treo = khi_treo or (lambda may, ly_do: treo(db, may, ly_do, now=thoi_diem))
    da_thu = da_treo = 0
    for may in den_han_thu(db, now=thoi_diem):
        try:
            thu_mot_chu_ky(db, may, now=thoi_diem)
            da_thu += 1
        except ThieuCreditError as exc:
            dat_treo(may, str(exc))
            da_treo += 1
        db.commit()
    return {"da_thu": da_thu, "da_treo": da_treo}
