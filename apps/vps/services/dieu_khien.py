"""Điều khiển máy đang chạy: bật, tắt, khởi động lại — và ai được phép làm.

## Vì sao ba thao tác này KHÔNG đi qua hàng đợi job

Chúng là **một lệnh gọi API** rồi trả về ngay; Proxmox chạy phần việc thật ở nền và
trả một mã tác vụ. Nhét chúng vào hàng đợi là bắt khách chờ một vòng worker để làm
việc mất 200 mili-giây, và thêm một chỗ để job kẹt.

Ngược lại, `cai_lai` và `xoa` **phải** đi qua job: chúng xoá đĩa rồi dựng lại, mất
vài phút tới hơn mười, mà Cloudflare cắt request ở 100 giây.

## Ba luật của tầng này, và cả ba đều là luật TIỀN chứ không phải luật kỹ thuật

1. **Máy bị treo vì nợ thì khách không được tự bật lại.** Không có luật này thì
   "treo" chỉ là một nút tắt mà khách bật lên được — tức là không treo gì cả.
2. **Máy đang tạo dở thì không được đụng vào.** Bật/tắt giữa lúc job đang clone là
   cách chắc chắn nhất để có một máy hỏng nửa chừng mà không ai biết vì sao.
3. **Mọi thao tác đều ghi nhật ký vòng đời.** Đây là thứ trả lời câu "vì sao máy
   tôi bị tắt" khi khách hỏi sau ba tháng — log ứng dụng thì đã xoay vòng mất rồi.
"""
from __future__ import annotations

from sqlalchemy.orm import Session as DbSession

from apps.vps.services import billing, provisioning
from apps.vps.services.proxmox import ProxmoxClient, ProxmoxError
from apps.vps.tables import VpsInstance

#: Trạng thái mà khách được phép ra lệnh bật/tắt/khởi động lại.
TRANG_THAI_DIEU_KHIEN_DUOC = ("dang_chay", "da_tat", "loi")


class KhongDuocPhepError(RuntimeError):
    """Thao tác không hợp lệ với trạng thái hiện tại của máy."""


def kiem_dieu_khien_duoc(may: VpsInstance) -> None:
    """Ném `KhongDuocPhepError` kèm câu giải thích **viết cho khách đọc**."""
    tt = str(may.trang_thai or "")
    if tt == "da_xoa":
        raise KhongDuocPhepError("May nay da bi xoa.")
    if tt == "bi_treo":
        # Luật 1. Câu này khách sẽ đọc, nên nó phải nói được phải làm gì.
        raise KhongDuocPhepError(
            "May dang bi treo do het han thanh toan. Nap credit va gia han de "
            "dung lai.")
    if tt == "dang_tao":
        raise KhongDuocPhepError("May dang duoc tao. Doi vai phut roi thu lai.")
    if tt not in TRANG_THAI_DIEU_KHIEN_DUOC:
        raise KhongDuocPhepError(f"Khong dieu khien duoc may o trang thai {tt!r}.")
    if not may.vmid:
        raise KhongDuocPhepError("May chua duoc tao xong tren may chu.")


def _lam(db: DbSession, may: VpsInstance, client: ProxmoxClient, *,
         boi: str, ten_thao_tac: str, goi, trang_thai_moi: str) -> str:
    kiem_dieu_khien_duoc(may)
    try:
        upid = goi(int(may.vmid))
    except ProxmoxError as exc:
        # Ghi cả lần THẤT BẠI: khách hỏi "sao bấm mãi không được" thì phải có
        # thứ để đọc, chứ không chỉ có những lần thành công.
        provisioning.ghi_su_kien(db, may.id, f"{ten_thao_tac}_that_bai", boi=boi,
                                 loi=str(exc)[:200])
        db.commit()
        raise
    may.trang_thai = trang_thai_moi
    may.ly_do = ""
    provisioning.ghi_su_kien(db, may.id, ten_thao_tac, boi=boi, upid=str(upid)[:190])
    db.commit()
    return str(upid)


def bat(db: DbSession, may: VpsInstance, client: ProxmoxClient, *, boi: str) -> str:
    return _lam(db, may, client, boi=boi, ten_thao_tac="bat",
                goi=client.bat, trang_thai_moi="dang_chay")


def tat(db: DbSession, may: VpsInstance, client: ProxmoxClient, *, boi: str,
        cung: bool = False) -> str:
    """Tắt máy. `cung=True` là rút điện — chỉ dùng khi tắt mềm không ăn thua.

    Mặc định tắt **mềm**: Windows cần dọn dẹp trước khi tắt, và rút điện giữa
    lúc nó đang ghi đĩa là cách làm hỏng hệ tệp của khách.
    """
    return _lam(db, may, client, boi=boi, ten_thao_tac="tat_cung" if cung else "tat",
                goi=client.tat_cung if cung else client.tat_mem,
                trang_thai_moi="da_tat")


def khoi_dong_lai(db: DbSession, may: VpsInstance, client: ProxmoxClient, *,
                  boi: str) -> str:
    """Khởi động lại = tắt mềm rồi bật.

    Proxmox có endpoint `reboot` riêng, nhưng nó **chờ guest tự tắt** và treo vô
    hạn nếu Windows đang hiện hộp thoại "có muốn lưu không". Ở đây ta tắt mềm rồi
    để khách tự bật lại — chậm hơn một thao tác, nhưng không bao giờ treo.
    """
    return tat(db, may, client, boi=boi)


def treo(db: DbSession, may: VpsInstance, client: ProxmoxClient, *,
         boi: str = "he_thong", ly_do: str = "Het han thanh toan") -> None:
    """Treo máy vì nợ hoặc vì lạm dụng: **tắt cứng**, rồi để `billing` ghi sổ.

    Phần CSDL (trạng thái, lý do, và mốc `xoa_sau` của V8) do `billing.treo` làm
    — nó đã có từ trước và nó là **một chỗ duy nhất** quyết định điều đó. Viết
    lại phần ghi sổ ở đây là dựng chỗ thứ hai, và hai chỗ thì sớm muộn lệch nhau:
    cái này đặt `xoa_sau`, cái kia quên, và máy của khách nằm lại vĩnh viễn hoặc
    bị xoá sớm bảy ngày.

    Khác `tat`: đây không phải thao tác của khách nên không hỏi
    `kiem_dieu_khien_duoc`, và nó tắt **cứng** — khách đã hết hạn thanh toán thì
    việc chờ Windows dọn dẹp không còn là ưu tiên, mà một máy "đang tắt mềm" mãi
    không xong là một máy vẫn đang tiêu tài nguyên của người khác.
    """
    if may.vmid:
        try:
            client.tat_cung(int(may.vmid))
        except ProxmoxError as exc:
            # Không chặn việc treo: treo là quyết định về TIỀN, không phụ thuộc
            # việc Proxmox có tắt được máy hay không. Nhưng phải ghi lại.
            provisioning.ghi_su_kien(db, may.id, "treo_khong_tat_duoc",
                                     boi=boi, loi=str(exc)[:200])
    billing.treo(db, may, ly_do)
