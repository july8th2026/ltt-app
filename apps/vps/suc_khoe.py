"""Sức khoẻ của khu VPS: đếm được, báo động được, và **khử trùng lặp**.

## Vì sao một module riêng thay vì thêm số vào `metrics` của public API

`platform_core/public_api/metrics.py` đếm lưu lượng của **bề mặt API công khai**.
VPS không đi qua bề mặt đó: nó có bảng riêng, job riêng, và ba hệ ngoài riêng
(Proxmox, router, Vultr). Nhét số của nó vào đấy là trộn hai miền, và người đọc
sẽ không biết một con số nói về cái gì.

Nhưng cũng **không** dựng vũ trụ đo lường thứ hai (§L của hợp đồng): tệp này
không có bộ đếm, không có tiến trình nền, không có bảng mới. Nó **đọc trạng thái
đã có** và trả lời hai câu:

* *"khu VPS đang thế nào"* — cho trang admin;
* *"cái gì đang hỏng mà chưa ai biết"* — cho cảnh báo.

## Khử trùng lặp bằng cách suy từ DỮ LIỆU, không bằng một bảng cảnh báo

Cùng khuôn với `platform_core/public_api/ops_alerts.py`: một cảnh báo là một
**mệnh đề về trạng thái hiện tại**, không phải một dòng được ghi ra. Nên hai lượt
quét liên tiếp trên cùng một sự cố cho ra **cùng một** `CanhBao` với cùng khoá —
người gọi so khoá là biết nó cũ hay mới, không cần bảng nào.

Cái giá phải nói rõ: nó **không nhớ** ai đã xem cảnh báo nào. Đây là kênh *phát
hiện*, không phải hệ thống quản lý sự cố.

## Cardinality: đếm, đừng gắn nhãn theo máy

Mọi con số ở đây là **tổng theo loại**. Không có nhãn `instance_id` — mỗi máy
mới là một chuỗi thời gian mới, và với một sản phẩm bán hàng trăm máy thì đó là
cách làm sập chính hệ đo lường. Máy nào cụ thể thì tra bằng `tai_nguyen` của
từng cảnh báo, tối đa `MAU_TOI_DA` mẫu.

## Không nói về thứ không đo được

Không có RAM/đĩa **bên trong** máy khách: guest agent là thiết bị virtio và
virtio treo trên cụm này (`services/mang.py`). Nên tệp này không có trường nào
cho chúng. Một ô "RAM: —" trên trang khách là một lời hứa rằng ta sẽ điền nó.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from apps.vps import trang_thai_may as tt
from apps.vps.services import thao_tac
from apps.vps.tables import VpsInstance, VpsThaoTac

# ── Mức cảnh báo ────────────────────────────────────────────────────────────
#
# Ba mức, không phải năm: `doi_chieu` đã có năm mức cho *phát hiện lệch*, và
# trộn hai thang đo vào nhau là buộc người đọc phải nhớ thang nào đang dùng.
# Ở đây câu hỏi khác: **có phải dựng người dậy không.**

NGHIEM_TRONG = "nghiem_trong"      # tiền hoặc dữ liệu đang chảy — dựng người dậy
CANH_BAO = "canh_bao"              # sẽ thành sự cố nếu để yên — xem trong ngày
THONG_TIN = "thong_tin"            # đáng biết, không đáng thức

MUC = (NGHIEM_TRONG, CANH_BAO, THONG_TIN)

#: Bao nhiêu mẫu tài nguyên đính kèm mỗi cảnh báo.
#:
#: 5 — đủ để người đọc bắt đầu tra, không đủ để một sự cố diện rộng biến một
#: dòng cảnh báo thành một trang giấy.
MAU_TOI_DA = 5

#: Cửa sổ nhìn lại khi đếm thao tác hỏng.
CUA_SO_GIO = 24

#: Bao nhiêu thao tác hỏng trong cửa sổ thì đáng báo.
#:
#: 3, không phải 1: một lần hỏng lẻ là chuyện thường của một hệ nói chuyện với
#: ba dịch vụ ngoài. Ba lần trong một ngày thì không còn là ngẫu nhiên.
NGUONG_HONG = 3


@dataclass(frozen=True)
class CanhBao:
    """Một mệnh đề về trạng thái hiện tại. Khoá `(ma, ...)` là thứ khử trùng lặp."""

    ma: str
    muc: str
    thong_diep: str
    so_luong: int = 0
    tai_nguyen: tuple = ()

    @property
    def khoa(self) -> str:
        """Hai lượt quét trên cùng một sự cố cho ra cùng chuỗi này."""
        return f"{self.ma}:{self.muc}"

    def __str__(self) -> str:
        mau = f" ({', '.join(str(x) for x in self.tai_nguyen[:MAU_TOI_DA])})" \
            if self.tai_nguyen else ""
        return f"[{self.muc}] {self.ma}: {self.thong_diep}{mau}"


@dataclass
class TongQuan:
    """Ảnh chụp khu VPS. Mọi trường là **số đếm**, không có nhãn theo máy."""

    tong_may: int = 0
    theo_suc_khoe: dict = field(default_factory=dict)
    theo_vong_doi: dict = field(default_factory=dict)
    quan_sat_qua_cu: int = 0
    thao_tac_dang_mo: int = 0
    thao_tac_hong_24h: int = 0
    thao_tac_qua_han_24h: int = 0
    bi_cach_ly: int = 0
    thieu_anh_chup: int = 0
    #: Năng lực sao lưu độc lập — `False` là **sự thật**, không phải lỗi cấu hình.
    co_sao_luu_doc_lap: bool = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def tong_quan(db, *, now: datetime | None = None,
              env: dict | None = None) -> TongQuan:
    """Ảnh chụp một lượt. **Không gọi mạng** — chỉ đọc CSDL.

    Không gọi mạng vì trang admin gọi hàm này mỗi lần mở: một lần gọi ra Proxmox
    ở đây biến một node chậm thành một trang admin không mở được, đúng lúc người
    ta cần nó nhất.

    Sự thật *bên ngoài* (Proxmox, router, Vultr) là việc của `doi_chieu.quet`,
    chạy trong vòng bảo trì, và kết quả của nó đã nằm sẵn trong CSDL khi tới đây.
    """
    from apps.vps import sao_luu_doc_lap
    from apps.vps.services import sao_luu

    thoi_diem = now or _now()
    tq = TongQuan()
    tq.co_sao_luu_doc_lap = sao_luu_doc_lap.nang_luc(env).sao_luu_doc_lap

    may = list(db.execute(select(VpsInstance).where(
        VpsInstance.vong_doi != tt.DA_XOA)).scalars())
    tq.tong_may = len(may)
    for m in may:
        tq.theo_suc_khoe[m.suc_khoe] = tq.theo_suc_khoe.get(m.suc_khoe, 0) + 1
        tq.theo_vong_doi[m.vong_doi] = tq.theo_vong_doi.get(m.vong_doi, 0) + 1
        if tt.qua_cu(m, now=thoi_diem):
            tq.quan_sat_qua_cu += 1
        if getattr(m, "cach_ly_luc", None) is not None:
            tq.bi_cach_ly += 1
        if sao_luu.den_han_chup(m, now=thoi_diem):
            tq.thieu_anh_chup += 1

    tu = thoi_diem - timedelta(hours=CUA_SO_GIO)
    for op in db.execute(select(VpsThaoTac)).scalars():
        if op.tinh_trang in thao_tac.DANG_MO:
            tq.thao_tac_dang_mo += 1
            continue
        ket = _aware(op.ket_thuc_luc)
        if ket is None or ket < tu:
            continue
        if op.tinh_trang == thao_tac.HONG:
            tq.thao_tac_hong_24h += 1
        elif op.tinh_trang == thao_tac.QUA_HAN:
            tq.thao_tac_qua_han_24h += 1
    return tq


def canh_bao(db, *, now: datetime | None = None,
             env: dict | None = None) -> list:
    """Những gì đang hỏng mà chưa ai biết. Danh sách rỗng = im lặng.

    Trả **im lặng khi khoẻ** là một yêu cầu, không phải một chi tiết: một dòng
    "mọi thứ ổn" mỗi giờ dạy người đọc bỏ qua kênh này, và họ sẽ bỏ qua đúng vào
    lượt có tin xấu.
    """
    thoi_diem = now or _now()
    tq = tong_quan(db, now=thoi_diem, env=env)
    ra: list[CanhBao] = []

    def them(ma, muc, thong_diep, so_luong, tai_nguyen=()):
        if so_luong:
            ra.append(CanhBao(ma, muc, thong_diep, so_luong,
                              tuple(tai_nguyen)[:MAU_TOI_DA]))

    mat = int(tq.theo_suc_khoe.get(tt.MAT_LIEN_LAC, 0))
    them("mat_lien_lac", NGHIEM_TRONG,
         "may khong hoi duoc trang thai — khach dang tra tien cho mot thu ta "
         "khong nhin thay", mat,
         _mau(db, VpsInstance.suc_khoe == tt.MAT_LIEN_LAC))

    # ⚠️ `qua_cu` KHÁC `mat_lien_lac`: cái đầu nghĩa là **ta chưa hỏi**, cái sau
    #    nghĩa là **đã hỏi và không có trả lời**. Gộp chúng là mất thông tin về
    #    việc vòng đối chiếu có chạy hay không.
    them("quan_sat_qua_cu", CANH_BAO,
         f"phep do cu hon {tt.QUA_CU_SAU_S // 60} phut — vong doi chieu co "
         f"dang chay khong?", tq.quan_sat_qua_cu)

    them("thao_tac_qua_han", NGHIEM_TRONG,
         "thao tac het han ma worker khong dong lai — co the worker dang chet",
         tq.thao_tac_qua_han_24h)

    if tq.thao_tac_hong_24h >= NGUONG_HONG:
        them("thao_tac_hong_nhieu", CANH_BAO,
             f"tren {NGUONG_HONG} thao tac hong trong {CUA_SO_GIO} gio",
             tq.thao_tac_hong_24h)

    them("thieu_anh_chup", CANH_BAO,
         "qua ky chup anh — vong bao tri co chay khong?", tq.thieu_anh_chup,
         _mau(db, VpsInstance.vong_doi != tt.DA_XOA))

    them("bi_cach_ly", THONG_TIN,
         "may dang bi cach ly mang — can nguoi quyet dinh go hay khong",
         tq.bi_cach_ly,
         _mau(db, VpsInstance.cach_ly_luc.is_not(None)))

    them("loi_vong_doi", CANH_BAO,
         "may o trang thai loi — khach dang nhin mot thong bao loi",
         int(tq.theo_vong_doi.get(tt.LOI, 0)),
         _mau(db, VpsInstance.vong_doi == tt.LOI))

    if not tq.co_sao_luu_doc_lap and tq.tong_may:
        # `THONG_TIN`, không phải `CANH_BAO`: đây là một **sự thật kiến trúc**
        # đã biết, không phải một thứ vừa hỏng. Đặt nó ở mức cao hơn là một
        # cảnh báo luôn bật, và một cảnh báo luôn bật là một cảnh báo bị bỏ qua.
        them("khong_co_sao_luu_doc_lap", THONG_TIN,
             "chi co anh chup CUNG POOL — hong dia la mat ca hai. Xem "
             "docs/vps_v2/RUNBOOK_KHOI_PHUC.md muc 4", tq.tong_may)

    return ra


def _mau(db, dieu_kien) -> list:
    """Vài `vmid` làm mẫu cho một điều kiện. Tối đa `MAU_TOI_DA`."""
    return [m.vmid for m in db.execute(
        select(VpsInstance).where(dieu_kien).limit(MAU_TOI_DA)).scalars()
        if m.vmid]


# ── Dòng thời gian của MỘT máy — thứ khách đọc ─────────────────────────────

@dataclass(frozen=True)
class MucThoiGian:
    """Một dòng trên dòng thời gian. **Chỉ chứa thứ khách được nhìn.**"""

    luc: datetime
    loai: str
    #: Mã trạng thái/bước, để `nhan.py` dịch. Không phải câu tiếng Việt.
    ma: str = ""
    dang_chay: bool = False
    that_bai: bool = False


def dong_thoi_gian(db, instance_id: str, *, gioi_han: int = 20) -> list:
    """Các thao tác của một máy, mới nhất trước.

    ⚠️ **Không** trả `upid` và **không** trả `chi_tiet_loi` thô. Cả hai nói ra
    hình dạng hạ tầng (số hiệu VM, id tác vụ, đường dẫn nội bộ) và cả hai đều vô
    ích với khách. Mã lỗi có cấu trúc (`ma_loi`) thì trả — nó ngắn, nó dịch
    được, và nó là thứ khách đọc cho bộ phận hỗ trợ nghe.
    """
    ra = []
    for op in db.execute(
        select(VpsThaoTac)
        .where(VpsThaoTac.instance_id == str(instance_id))
        .order_by(VpsThaoTac.tao_luc.desc())
        .limit(int(gioi_han))
    ).scalars():
        dang = op.tinh_trang in thao_tac.DANG_MO
        ra.append(MucThoiGian(
            luc=op.tao_luc, loai=op.loai,
            ma=(str(op.buoc or "") if dang else str(op.ma_loi or "")),
            dang_chay=dang,
            that_bai=op.tinh_trang in (thao_tac.HONG, thao_tac.QUA_HAN)))
    return ra
