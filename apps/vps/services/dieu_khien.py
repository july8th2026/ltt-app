"""Bật, tắt, khởi động lại — và luật "chưa đo được thì chưa được nói là xong".

## Vì sao ba thao tác này BÂY GIỜ đi qua hàng đợi job (đổi ý so với bản cũ)

Bản trước lập luận: *"chúng là một lệnh gọi API rồi trả về ngay… nhét vào hàng đợi
là bắt khách chờ một vòng worker cho một việc mất 200 mili-giây."*

Lập luận đó **đúng với hành vi cũ** — mà hành vi cũ chính là lỗi. 200 mili-giây là
thời gian để Proxmox **nhận** lệnh, không phải để máy **tắt xong**. Một lần khởi
động lại đúng nghĩa là: tắt mềm → chờ tác vụ → *xác minh máy đã STOPPED* → bật →
chờ → *xác minh RUNNING*. Với Windows, đó là hàng chục giây tới vài phút.

Cloudflare cắt request ở **100 giây** (`CLAUDE.md` luật 19). Nên chỉ còn hai đường:
giữ nó chạy thẳng và **nói dối**, hoặc đưa vào hàng đợi. Không có đường thứ ba.

Xem `docs/vps_v2/ADR_INDEX.md` ADR-03.

## Hai nửa của tệp này

| Nửa | Chạy ở đâu | Làm gì |
|---|---|---|
| `xin()` | tiến trình web | kết nạp, mở thao tác, nộp job. **Không** chạm Proxmox |
| `thi_hanh()` | worker | gọi Proxmox, chờ, xác minh, kết luận |

Tách vì hai nửa có hai ngân sách thời gian khác nhau (100 giây của Cloudflare so
với `max_runtime_s` của job) và hai cách hỏng khác nhau. Gộp lại là buộc nửa nhanh
phải chịu trần của nửa chậm.

## Ba luật của tầng này, và cả ba đều là luật TIỀN

1. **Máy bị treo vì nợ thì khách không được tự bật lại.** Không có luật này thì
   "treo" chỉ là một cái nút mà khách bật lên được — tức không treo gì cả.
2. **Máy đang tạo dở thì không được đụng vào.** Bật/tắt giữa lúc job đang dựng là
   cách chắc chắn nhất để có một máy hỏng nửa chừng mà không ai biết vì sao.
3. **Mọi thao tác đều ghi nhật ký vòng đời.** Đây là thứ trả lời "vì sao máy tôi
   bị tắt" khi khách hỏi sau ba tháng — log ứng dụng thì đã xoay vòng mất rồi.

## Tắt mềm hết hạn thì KHÔNG tự rút điện

Rút điện giữa lúc Windows đang ghi đĩa là cách làm hỏng hệ tệp của khách. Nên tắt
mềm quá hạn trả về một trạng thái hỏng **có việc để làm tiếp**, và việc đó là một
nút riêng (`tat_cung`) mà **khách bấm**, có ghi nhật ký. Tự động hoá bước đó là
chuyển một quyết định mất dữ liệu từ người sang máy.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DbSession

from apps.vps import trang_thai_may as tt
from apps.vps.services import billing, provisioning, tac_vu, thao_tac
from apps.vps.services.proxmox import ProxmoxClient, ProxmoxError
from apps.vps.tables import VpsInstance, VpsThaoTac

log = logging.getLogger(__name__)

#: Trạng thái mà khách được phép ra lệnh bật/tắt/khởi động lại.
TRANG_THAI_DIEU_KHIEN_DUOC = ("dang_chay", "da_tat", "loi")

#: Job type cho mọi lệnh điều khiển. MỘT job type cho cả ba lệnh: chúng có cùng
#: hình dạng (gọi → chờ → xác minh) và cùng trần thời gian; ba job type là ba
#: dòng phải nhớ khai trong `manifest` mỗi lần thêm một lệnh.
JOB_TYPE = "vps.control"

#: lệnh → (mã tác vụ, điện mong đợi khi xong)
LENH = {
    "bat": (tt.DANG_BAT, tt.CHAY),
    "tat": (tt.DANG_TAT, tt.TAT),
    "tat_cung": (tt.DANG_TAT, tt.TAT),
    "khoi_dong_lai": (tt.DANG_KD_LAI, tt.CHAY),
    # 25/09: duong cuu ho khi khoi dong lai mem that bai. Ket qua mong muon la
    # may **dang chay** — khac han `tat_cung`, thu ma khach khong con goi duoc.
    "khoi_dong_lai_cung": (tt.DANG_KD_LAI, tt.CHAY),
}

#: Bước con của một thao tác. **Mã**, không phải câu tiếng Việt: `nhan.BUOC` dịch
#: sang tiếng người, cùng khuôn với `trang_thai`. Một câu tiếng Việt nằm trong
#: CSDL là một chuỗi không dịch được sang tiếng Anh và không đếm được.
BUOC_GUI_TAT = "gui_lenh_tat"
BUOC_CHO_TAT = "cho_may_tat"
BUOC_GUI_BAT = "gui_lenh_bat"
BUOC_CHO_BAT = "cho_may_bat"

#: Bước nào nghĩa là **pha tắt đã xong**. Dùng khi nối lại sau một lần worker chết.
#:
#: Không có nó thì một lần khởi động lại chạy lại sau khi máy **đã bật lên rồi**
#: sẽ thấy `dien=chay`, kết luận "chưa tắt", và tắt máy khách một lần nữa.
BUOC_DA_QUA_PHA_TAT = frozenset({BUOC_GUI_BAT, BUOC_CHO_BAT})


class KhongDuocPhepError(RuntimeError):
    """Thao tác không hợp lệ với trạng thái hiện tại của máy."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def kiem_dieu_khien_duoc(may: VpsInstance) -> None:
    """Ném `KhongDuocPhepError` kèm câu giải thích **viết cho khách đọc**."""
    tt_ma = str(may.trang_thai or "")
    if tt_ma == "da_xoa":
        raise KhongDuocPhepError("May nay da bi xoa.")
    if tt_ma == "bi_treo":
        # Luật 1. Câu này khách sẽ đọc, nên nó phải nói được phải làm gì.
        raise KhongDuocPhepError(
            "May dang bi treo do het han thanh toan. Nap credit va gia han de "
            "dung lai.")
    if tt_ma == "dang_tao":
        raise KhongDuocPhepError("May dang duoc tao. Doi vai phut roi thu lai.")
    if tt_ma not in TRANG_THAI_DIEU_KHIEN_DUOC:
        raise KhongDuocPhepError(f"Khong dieu khien duoc may o trang thai {tt_ma!r}.")
    if not may.vmid:
        raise KhongDuocPhepError("May chua duoc tao xong tren may chu.")


def khoa_idem(instance_id: str, lenh: str, *,
              now: datetime | None = None) -> str:
    """Khoá chống bấm hai lần: (máy + lệnh + **phút**).

    ## Vì sao hạt là PHÚT chứ không phải một uuid mỗi lần bấm

    Một uuid mỗi lần bấm không chống được gì: hai cú bấm sinh hai uuid. Hạt thời
    gian là thứ biến *"hai request"* thành *"một ý định"*.

    Một phút vì đó là khoảng mà một người bấm nhầm hai lần — bấm rồi thấy trang
    chưa đổi nên bấm lại. Dài hơn thì chặn cả một ý định thật (bật lại sau khi
    lần đầu hỏng); ngắn hơn thì không chặn được cú bấm đúp chậm tay.
    """
    phut = (now or _now()).strftime("%Y%m%d%H%M")
    return f"{lenh}:{phut}"[:64]


# ── Nửa CHẠY Ở WEB: kết nạp và nộp việc ─────────────────────────────────────

def xin(db: DbSession, may: VpsInstance, lenh: str, *, boi: str,
        now: datetime | None = None) -> VpsThaoTac:
    """Khách xin một lệnh điều khiển. Trả thao tác đã mở (hoặc thao tác đang có).

    **Không chạm Proxmox.** Nó chỉ kết nạp, mở sổ, và nộp job — cả ba đều nhanh
    và không chờ ai, nên nó vừa trần 100 giây của Cloudflare kể cả khi Proxmox
    đang treo.

    Ném `KhongDuocPhepError` (trạng thái sai) hoặc `thao_tac.DangBanError` (máy
    đang bận). Hai loại khác nhau vì khách cần hai câu trả lời khác nhau.
    """
    if lenh not in LENH:
        raise ValueError(f"lenh khong biet: {lenh!r}")
    kiem_dieu_khien_duoc(may)
    loai, dien_dich = LENH[lenh]

    op = thao_tac.mo(db, may, loai, boi=boi,
                     khoa_idem=khoa_idem(may.id, lenh, now=now),
                     dien_mong_doi=dien_dich, now=now)
    # `dien_mong_muon` đổi NGAY: đó là ý định của khách, và nó đúng từ giây họ
    # bấm. Thứ KHÔNG được đổi là `dien_quan_sat` — ta chưa đo lại lần nào.
    tt.dat(may, dien_mong_muon=dien_dich, ly_do="")
    provisioning.ghi_su_kien(db, may.id, f"xin_{lenh}", boi=boi,
                             thao_tac_id=op.id)

    from platform_core import jobs as job_queue
    from apps.vps.manifest import MANIFEST
    job_queue.submit(db, user_id=boi, app_slug=MANIFEST.slug,
                     job_type=JOB_TYPE,
                     params={"instance_id": may.id, "lenh": lenh,
                             "thao_tac_id": op.id, "boi": boi})
    return op


# ── Nửa CHẠY Ở WORKER: gọi, chờ, xác minh ───────────────────────────────────

def _gui_va_cho(client, may, op, *, goi, dien_dich: str, buoc_gui: str,
                buoc_cho: str, han_dien_s: float, nhip, ghi) -> str:
    """Một pha: hỏi thế giới thật → gửi lệnh nếu cần → chờ → xác minh.

    ## "Hỏi thế giới thật trước" không phải tối ưu, mà là tính đúng

    Job có thể chạy lại sau khi worker chết. Bắn lại một lệnh `start` cho máy
    đang chạy thì Proxmox trả lỗi và job hỏng — cho một việc **đã xong**. Cùng
    khuôn với `_vm_da_ton_tai` trong `jobs.py`: mỗi bước tự hỏi xem nó đã xảy ra
    chưa, thay vì tin một cái cờ.
    """
    if tac_vu.doc_dien(client, may.vmid) == dien_dich:
        return dien_dich

    ghi(buoc_gui)
    upid = goi(int(may.vmid))
    # Ghi UPID **trước** khi chờ: mục đích của cột này là sống sót qua một lần
    # tiến trình chết, mà lúc chết thì thứ chưa ghi là thứ đã mất.
    thao_tac.ghi_upid(None, op, str(upid))
    ghi(buoc_cho)
    return tac_vu.cho_va_xac_minh(client, upid, may.vmid, dien_dich,
                                  han_tac_vu_s=tac_vu.han_theo_job(JOB_TYPE),
                                  han_dien_s=han_dien_s, nhip=nhip)


def thi_hanh(db: DbSession, may: VpsInstance, client: ProxmoxClient,
             op: VpsThaoTac, *, lenh: str, nhip: tac_vu.Nhip = tac_vu.NHIP_THAT,
             luu=None, now: datetime | None = None) -> str:
    """Thi hành một lệnh điều khiển tới nơi tới chốn. Trả điện **đo được** cuối cùng.

    `luu()` được gọi sau mỗi lần đổi bước để tiến độ hiện ra cho khách **trong
    lúc** việc đang chạy. Không có nó thì cột `buoc` chỉ có giá trị sau khi mọi
    thứ đã xong — tức đúng lúc không ai cần nó nữa.

    Ném `tac_vu.TacVuLoi` (các lớp con) khi hỏng; người gọi ghi sổ.
    """
    loai, dien_dich = LENH[lenh]
    _luu = luu or (lambda: None)

    def ghi(buoc: str) -> None:
        thao_tac.ghi_buoc(None, op, buoc)
        _luu()

    if loai == tt.DANG_KD_LAI:
        # Nối lại: đã qua pha tắt thì KHÔNG tắt lần nữa. Không có phép kiểm này,
        # một lần chạy lại sau khi máy đã bật lên sẽ thấy `chay`, kết luận "chưa
        # tắt", và tắt máy khách thêm một lần nữa.
        if str(op.buoc or "") not in BUOC_DA_QUA_PHA_TAT:
            _gui_va_cho(client, may, op, goi=client.tat_mem, dien_dich=tt.TAT,
                        buoc_gui=BUOC_GUI_TAT, buoc_cho=BUOC_CHO_TAT,
                        han_dien_s=tac_vu.HAN_DIEN_S, nhip=nhip, ghi=ghi)
        dien = _gui_va_cho(client, may, op, goi=client.bat, dien_dich=tt.CHAY,
                           buoc_gui=BUOC_GUI_BAT, buoc_cho=BUOC_CHO_BAT,
                           han_dien_s=tac_vu.HAN_DIEN_S, nhip=nhip, ghi=ghi)
    elif loai == tt.DANG_BAT:
        dien = _gui_va_cho(client, may, op, goi=client.bat, dien_dich=tt.CHAY,
                           buoc_gui=BUOC_GUI_BAT, buoc_cho=BUOC_CHO_BAT,
                           han_dien_s=tac_vu.HAN_DIEN_S, nhip=nhip, ghi=ghi)
    else:
        goi = client.tat_cung if lenh == "tat_cung" else client.tat_mem
        dien = _gui_va_cho(client, may, op, goi=goi, dien_dich=tt.TAT,
                           buoc_gui=BUOC_GUI_TAT, buoc_cho=BUOC_CHO_TAT,
                           han_dien_s=tac_vu.HAN_DIEN_S, nhip=nhip, ghi=ghi)

    tt.ghi_quan_sat(may, dien, now=now)
    return dien


# ── Treo vì nợ: không phải thao tác của khách ───────────────────────────────

#: Chờ tối đa cho lệnh tắt cứng lúc treo máy (giây).
#:
#: Ngắn (60s) vì `stop` là **rút điện**, không phải tắt mềm: Proxmox làm xong
#: trong một hai giây. Trần này chỉ để vòng bảo trì không đứng lại vì một node
#: không trả lời — treo là quyết định về TIỀN và nó không được phụ thuộc vào
#: việc Proxmox có rảnh hay không.
HAN_TREO_S = 60


def treo(db: DbSession, may: VpsInstance, client: ProxmoxClient, *,
         boi: str = "he_thong", ly_do: str = "Het han thanh toan",
         nhip: tac_vu.Nhip = tac_vu.NHIP_THAT,
         now: datetime | None = None) -> None:
    """Treo máy vì nợ hoặc vì lạm dụng: **tắt cứng**, rồi để `billing` ghi sổ.

    Phần CSDL (vòng đời, lý do, mốc `xoa_sau` của V8) do `billing.treo` làm — nó
    là **một chỗ duy nhất** quyết định điều đó. Viết lại phần ghi sổ ở đây là
    dựng chỗ thứ hai, và hai chỗ thì sớm muộn lệch nhau: cái này đặt `xoa_sau`,
    cái kia quên, và máy của khách nằm lại vĩnh viễn hoặc bị xoá sớm bảy ngày.

    Khác `xin("tat")`: đây không phải thao tác của khách nên không hỏi
    `kiem_dieu_khien_duoc`, không mở thao tác, không nộp job — nó chạy thẳng
    trong vòng bảo trì (vốn đã nằm dưới một lease) và nó tắt **cứng**.

    ## Vẫn CHỜ, dù trước đây không chờ

    Bản cũ bắn `tat_cung` rồi đi tiếp. Nghĩa là câu "đã treo" trong nhật ký không
    nói được máy có tắt hay không — và một máy hết tiền vẫn chạy là RAM của người
    khác. Giờ có chờ, có trần ngắn, và **thất bại không chặn việc ghi sổ**.
    """
    if may.vmid:
        try:
            upid = client.tat_cung(int(may.vmid))
            dien = tac_vu.cho_va_xac_minh(client, upid, may.vmid, tt.TAT,
                                          han_tac_vu_s=HAN_TREO_S,
                                          han_dien_s=HAN_TREO_S, nhip=nhip)
            tt.ghi_quan_sat(may, dien, now=now)
        except (ProxmoxError, tac_vu.TacVuLoi) as exc:
            # Không chặn việc treo: treo là quyết định về TIỀN, không phụ thuộc
            # việc Proxmox có tắt được máy hay không. Nhưng phải ghi lại, và
            # phải ghi rằng ta **không biết** máy đang ở đâu.
            provisioning.ghi_su_kien(db, may.id, "treo_khong_tat_duoc",
                                     boi=boi, loi=str(exc)[:200])
            tt.ghi_quan_sat(may, tt.KHONG_RO, now=now)
    billing.treo(db, may, ly_do)


def go_dia_cai(db, may, client, *, boi: str = "khach") -> None:
    """Gỡ đĩa cài ra khỏi máy và cho nó khởi động thẳng vào đĩa cứng.

    ## Vì sao đây là một nút, không phải một bước tự động

    Nền tảng **không biết** khách đã cài xong Windows hay chưa: máy khách không
    có guest agent (agent là thiết bị virtio, và virtio treo trên cụm này), nên
    không có cách nào hỏi bên trong. Đoán theo thời gian là đoán sai với người
    cài chậm, và đoán sai theo hướng **rút đĩa giữa lúc họ đang cài**.

    ## Vì sao vẫn cần gỡ, thay vì kệ nó

    Đĩa cài nằm nguyên đó thì mỗi lần khởi động máy lại hiện *"Press any key to
    boot from CD"*. Không bấm thì sau vài giây nó bỏ qua — nhưng **bấm nhầm một
    phím trong lúc đó là vào lại trình cài đặt từ đầu**, và với người vừa cài
    xong thì đó là một cú suýt mất cả buổi.

    Chạy thẳng chứ không qua hàng đợi: đây là một lần `qm set`, không sinh tác vụ
    nền nào và không chờ gì cả — khác hẳn ba lệnh điện ở trên.

    Chạy lại được: gỡ hai lần không lỗi.
    """
    kiem_dieu_khien_duoc(may)
    client.dat_cau_hinh(may.vmid, delete="ide0", boot="order=sata0")
    provisioning.ghi_su_kien(db, may.id, "go_dia_cai", boi=boi, vmid=may.vmid)
    db.commit()
