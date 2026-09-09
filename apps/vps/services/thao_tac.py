"""Vòng đời của một **thao tác dài** trên một máy: mở, chạy, kết thúc, thu dọn.

## Ba câu hỏi mà tầng này trả lời, và không tầng nào khác trả lời được

1. *"Máy này có đang bị làm gì không?"* — trang máy hỏi mỗi lần mở, và nút bấm
   phải khoá theo câu trả lời. Trước VPS V2 không có chỗ nào để hỏi.
2. *"Khách vừa bấm hai lần — có phải hai lần không?"* — `khoa_idem` trả lời.
3. *"Worker chết giữa chừng, chạy lại thì làm gì?"* — `upid` đã lưu trả lời:
   **nối lại** vào tác vụ đang chạy, không bắn thêm một lệnh nữa vào Proxmox.

## Ranh giới với hàng đợi job, và vì sao nó không mờ

Thao tác **không** là một hàng đợi. Nó không có worker, không có nhịp quét, không
tự chạy. Nó là **sổ ghi** cho một việc mà job của nền tảng đang làm:

```
route  →  mo()  →  submit job  →  worker: bat_dau() … ghi_upid() … xong()/hong()
```

Đường **cưỡng chế đồng thời** vẫn là lease `vps-may:{id}` trong `jobs._khoa_may`
(H36) — thao tác chỉ *nhìn thấy* xung đột và từ chối sớm ở tầng HTTP, để khách
nhận một câu giải thích thay vì một job bị đá lui im lặng.

Hai lớp, và cả hai đều cần:

| Lớp | Ở đâu | Chống gì | Vì sao chưa đủ một mình |
|---|---|---|---|
| Kết nạp | `mo()` ở route | bấm nhầm, bấm hai lần | có khoảng trống giữa lúc hỏi và lúc job chạy |
| Loại trừ | lease trong worker | hai worker thật sự đụng nhau | tới đó thì khách đã bấm rồi, không giải thích được nữa |

## `qua_han` không phải `hong`

Một thao tác quá hạn **có thể vẫn đang chạy** trên Proxmox và vẫn sẽ thành công.
Ghi nó thành `hong` là mời người ta thử lại một việc đang chạy dở — đúng cách để
có hai lần khôi phục chồng lên nhau. Nên nó có mã riêng, và đường xử lý là **hỏi
lại thế giới thật**, không phải làm lại.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.vps import trang_thai_may
from apps.vps.tables import VpsThaoTac

log = logging.getLogger(__name__)

CHO = "cho"
DANG_CHAY = "dang_chay"
XONG = "xong"
HONG = "hong"
QUA_HAN = "qua_han"
HUY = "huy"

TINH_TRANG = frozenset({CHO, DANG_CHAY, XONG, HONG, QUA_HAN, HUY})

#: Thao tác ở những trạng thái này còn **chiếm** máy.
DANG_MO = frozenset({CHO, DANG_CHAY})

#: Hạn chót mặc định cho một thao tác, tính từ lúc mở.
#:
#: 35 phút — dài hơn `max_runtime_s` lớn nhất của job (1800 giây). Ngắn hơn thì
#: vòng thu dọn sẽ đánh dấu `qua_han` cho một job **vẫn đang chạy đúng luật**, và
#: khách nhận một thông báo lỗi cho một việc sắp xong.
HAN_MAC_DINH = timedelta(minutes=35)


class DangBanError(RuntimeError):
    """Máy này đang có một thao tác khác chạy dở.

    Mang theo thao tác đang chạy để chỗ gọi nói được **cái gì** đang chạy, chứ
    không chỉ nói "bận" — một thông báo "bận" không kèm lý do là thứ khách sẽ
    bấm lại năm lần.
    """

    def __init__(self, dang_chay: VpsThaoTac):
        self.dang_chay = dang_chay
        super().__init__(f"may dang chay thao tac {dang_chay.loai!r}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def dang_mo(db, instance_id: str) -> VpsThaoTac | None:
    """Thao tác còn đang chiếm máy này, hoặc `None`.

    Lấy cái **mới nhất** nếu có nhiều: dữ liệu đúng thì chỉ có một, nhưng một
    hàng mồ côi từ một lần sập không được làm hàm này ném lỗi — trang máy phải
    mở được kể cả khi sổ sách lệch.
    """
    return db.execute(
        select(VpsThaoTac)
        .where(VpsThaoTac.instance_id == str(instance_id),
               VpsThaoTac.tinh_trang.in_(tuple(DANG_MO)))
        .order_by(VpsThaoTac.tao_luc.desc())
    ).scalars().first()


def theo_khoa(db, instance_id: str, khoa_idem: str) -> VpsThaoTac | None:
    """Thao tác đã mở với đúng khoá idempotency này, hoặc `None`."""
    if not khoa_idem:
        return None
    return db.execute(
        select(VpsThaoTac).where(
            VpsThaoTac.instance_id == str(instance_id),
            VpsThaoTac.khoa_idem == str(khoa_idem))
    ).scalars().first()


def mo(db, may, loai: str, *, boi: str, khoa_idem: str = "",
       dien_mong_doi: str = "", han: timedelta | None = None,
       now: datetime | None = None) -> VpsThaoTac:
    """Mở một thao tác. Trả về thao tác **đã có** nếu khoá idempotency trùng.

    Ném `DangBanError` nếu máy đang có thao tác khác chạy dở.

    ## Vì sao bắt `IntegrityError` chứ không "hỏi rồi mới ghi"

    Giữa lúc hỏi và lúc ghi có một khoảng, và hai request của cùng một cú bấm đúp
    lọt qua khoảng đó cùng lúc. Ràng buộc `uq_vps_thao_tac_idem` là **trọng tài
    duy nhất** không có khoảng trống — cùng khuôn với `uq_vps_instance_ip` và với
    `platform_core/gpu_lease.py`.
    """
    thoi_diem = now or _now()
    loai = str(loai or "")
    if loai not in trang_thai_may.TAC_VU_DOC_QUYEN:
        raise ValueError(f"loai thao tac khong hop le: {loai!r}")

    cu = theo_khoa(db, may.id, khoa_idem)
    if cu is not None:
        return cu

    ban = dang_mo(db, may.id)
    if ban is not None:
        raise DangBanError(ban)

    tt = VpsThaoTac(
        instance_id=may.id, loai=loai, boi=str(boi or "he_thong"),
        khoa_idem=(str(khoa_idem) or None), tinh_trang=CHO,
        dien_truoc=str(getattr(may, "dien_quan_sat", "") or ""),
        dien_mong_doi=str(dien_mong_doi or ""),
        tao_luc=thoi_diem, han_luc=thoi_diem + (han or HAN_MAC_DINH))
    db.add(tt)
    try:
        db.flush()
    except IntegrityError:
        # Đường chạy BÌNH THƯỜNG, không phải sự cố: một request song song của
        # cùng cú bấm vừa giành trước. Trả về thao tác của họ.
        db.rollback()
        cu = theo_khoa(db, may.id, khoa_idem)
        if cu is not None:
            return cu
        raise

    trang_thai_may.bat_dau_tac_vu(may, loai)
    return tt


def bat_dau(db, tt: VpsThaoTac, *, buoc: str = "",
            now: datetime | None = None) -> VpsThaoTac:
    """Worker đã nhặt được việc và bắt đầu làm."""
    tt.tinh_trang = DANG_CHAY
    tt.lan_thu = int(tt.lan_thu or 0) + 1
    tt.bat_dau_luc = now or _now()
    if buoc:
        tt.buoc = buoc[:64]
    return tt


def ghi_buoc(db, tt: VpsThaoTac, buoc: str) -> VpsThaoTac:
    """Đổi bước con đang chạy. Viết **tiếng người** — khách sẽ đọc câu này."""
    tt.buoc = str(buoc or "")[:64]
    return tt


def ghi_upid(db, tt: VpsThaoTac, upid: str) -> VpsThaoTac:
    """Ghi thêm một UPID của Proxmox vào thao tác.

    **Cộng dồn, không ghi đè.** Một lần khởi động lại sinh hai UPID (tắt rồi
    bật); giữ lại cái cuối là mất đúng đường nối lại vào tác vụ đầu khi tiến
    trình chết giữa hai bước.

    Ghi **trước** khi chờ, không phải sau: mục đích của cột này là sống sót qua
    một lần tiến trình chết, mà lúc chết thì thứ chưa ghi là thứ đã mất.
    """
    upid = str(upid or "").strip()
    if not upid:
        return tt
    co = [d for d in str(tt.upid or "").splitlines() if d]
    if upid not in co:
        co.append(upid)
    tt.upid = "\n".join(co)
    return tt


def upid_cuoi(tt: VpsThaoTac) -> str:
    """UPID gần nhất đã ghi, hoặc chuỗi rỗng."""
    co = [d for d in str(tt.upid or "").splitlines() if d]
    return co[-1] if co else ""


def xong(db, tt: VpsThaoTac, may=None, *, dien_sau: str = "",
         now: datetime | None = None) -> VpsThaoTac:
    """Kết thúc **thành công** — chỉ gọi sau khi đã xác minh thế giới thật."""
    tt.tinh_trang = XONG
    tt.buoc = ""
    tt.ket_thuc_luc = now or _now()
    if dien_sau:
        tt.dien_sau = dien_sau
    if may is not None:
        trang_thai_may.ket_thuc_tac_vu(may)
    return tt


def hong(db, tt: VpsThaoTac, may=None, *, ma_loi: str = "khong_ro",
         chi_tiet: str = "", qua_han: bool = False,
         now: datetime | None = None) -> VpsThaoTac:
    """Kết thúc **thất bại**. `qua_han=True` cho ca hết hạn chờ.

    Vẫn `ket_thuc_tac_vu(may)`: thất bại là một kết thúc. Để nguyên cờ tác vụ là
    để lại một cái khoá mềm khiến khách không bấm được gì nữa trên một máy đang
    lỗi — tức lấy mất đúng nút "Cài lại" mà họ cần.
    """
    tt.tinh_trang = QUA_HAN if qua_han else HONG
    tt.ma_loi = str(ma_loi or "khong_ro")[:32]
    tt.chi_tiet_loi = str(chi_tiet or "")[:2000]
    tt.buoc = ""
    tt.ket_thuc_luc = now or _now()
    if may is not None:
        trang_thai_may.ket_thuc_tac_vu(may)
    return tt


#: Giữ một thao tác **đã kết thúc** bao lâu trước khi xoá.
#:
#: 180 ngày, không phải 30. Một thao tác hỏng là thứ khách hỏi lại sau vài
#: tháng — *"hồi tháng trước tôi bấm khởi động lại mà máy không lên"* — và câu
#: trả lời nằm ở `ma_loi` của chính hàng này. Ngắn hơn thì ta xoá mất câu trả
#: lời trước khi câu hỏi tới.
#:
#: ⚠️ Con số này phải khớp `governance.STORES["vps_thao_tac"].retention_days`.
#: `tests/test_561` đối chiếu hai chỗ — một chính sách ghi 180 mà mã xoá sau 30
#: là một chính sách nói dối, và không phép kiểm hành vi nào bắt được.
GIU_NGAY = 180


def don_cu(db, *, now: datetime | None = None) -> int:
    """Xoá những thao tác **đã kết thúc** và quá `GIU_NGAY`. Trả số hàng đã xoá.

    ## Vì sao bảng này được xoá còn `vps_event` thì không

    `vps_event` là **bằng chứng**: nó trả lời *"vì sao máy tôi bị tắt"* và nó
    không bao giờ được xoá. `vps_thao_tac` là **hàng đợi có sổ**: nó có hạn
    chót, có UPID để nối lại, và nó kết thúc. Một hàng đợi không dọn được là
    một hàng đợi phình mãi.

    ⛔ Chỉ xoá hàng **đã kết thúc**. Một thao tác còn mở mà bị xoá thì máy của
    khách mang một cờ `tac_vu` không còn ai gỡ — khoá mềm vĩnh viễn, đúng thứ
    `don_qua_han` sinh ra để chống.
    """
    thoi_diem = (now or _now()) - timedelta(days=GIU_NGAY)
    cu = list(db.execute(
        select(VpsThaoTac).where(
            VpsThaoTac.tinh_trang.not_in(tuple(DANG_MO)),
            VpsThaoTac.ket_thuc_luc.is_not(None),
            VpsThaoTac.ket_thuc_luc < thoi_diem)
    ).scalars())
    for x in cu:
        db.delete(x)
    return len(cu)


def don_qua_han(db, *, now: datetime | None = None) -> list:
    """Đóng những thao tác đã quá hạn mà vẫn còn mở. Trả danh sách đã đóng.

    ## Đây là đường phục hồi sau khi một worker chết

    Worker bị kill giữa chừng thì không ai gọi `xong()` hay `hong()`. Không có
    hàm này, thao tác đó nằm lại `dang_chay` **vĩnh viễn** và máy bị khoá mềm mãi
    mãi — khách không bấm được gì và không ai biết vì sao.

    ⚠️ Nó **không** kết luận việc đã thất bại: mã lỗi là `tac_vu_qua_han`, và
    đường xử lý đúng là vòng đối chiếu hỏi lại Proxmox (Pha 05). Xoá cờ ở đây chỉ
    để máy dùng lại được.

    Cần `now` để test không phải chờ thật; mặc định là hiện tại.
    """
    thoi_diem = now or _now()
    from apps.vps.tables import VpsInstance

    da_dong = []
    for tt in db.execute(
        select(VpsThaoTac).where(
            VpsThaoTac.tinh_trang.in_(tuple(DANG_MO)),
            VpsThaoTac.han_luc.is_not(None))
    ).scalars():
        han = tt.han_luc
        if han is not None and han.tzinfo is None:
            han = han.replace(tzinfo=timezone.utc)
        if han is None or han > thoi_diem:
            continue
        may = db.get(VpsInstance, tt.instance_id)
        hong(db, tt, may, ma_loi="tac_vu_qua_han", qua_han=True,
             chi_tiet=f"qua han luc {han.isoformat()}, worker khong dong lai",
             now=thoi_diem)
        # Quan sát về `khong_ro`: ta **không biết** việc đó đã xong hay chưa, và
        # đoán theo hướng nào cũng là bịa. Vòng đối chiếu sẽ đi hỏi.
        if may is not None:
            trang_thai_may.dat(may,
                               dien_quan_sat=trang_thai_may.KHONG_RO,
                               suc_khoe=trang_thai_may.KHONG_RO)
        da_dong.append(tt)
        log.warning("vps: thao tac %s (%s) qua han, da dong", tt.id, tt.loai)
    return da_dong
