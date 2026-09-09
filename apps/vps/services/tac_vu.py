"""Chờ một tác vụ nền của Proxmox — **chỗ duy nhất** biết "xong" nghĩa là gì.

## Vì sao một `POST` thành công không phải một việc đã xong

Mọi thao tác nặng của Proxmox (`start`, `shutdown`, `stop`, `clone`, `snapshot`,
`rollback`, `destroy`) trả về **ngay** một chuỗi UPID và chạy phần việc thật ở nền.
HTTP 200 ở đây chỉ nói *"tôi đã nhận việc"*. Nó không nói máy đã bật, không nói ảnh
đã chụp xong, và **không** nói việc sẽ thành công.

Trước tệp này, `grep trang_thai_tac_vu` toàn kho ra đúng **một** chỗ dùng — trong
`jobs.py`. Ba đường còn lại (bật, tắt, khôi phục) lấy UPID rồi ghi thẳng "đã xong"
vào CSDL. Đó là ba lỗi P0 cùng một gốc.

## Ba câu hỏi khác nhau, và gộp chúng là gốc của lỗi

| Câu hỏi | Hàm | Sai lầm khi gộp |
|---|---|---|
| Tác vụ nền kết thúc chưa? | `cho_xong` | trả lời "rồi" cho một tác vụ **thất bại** |
| Nó kết thúc **tốt** chứ? | `cho_xong` (kiểm `exitstatus`) | Proxmox trả `status=stopped` cho cả thành công lẫn thất bại |
| Máy có **thật sự** tới trạng thái mong đợi không? | `cho_dien` | tác vụ OK mà máy vẫn tắt là chuyện có thật — Windows từ chối tắt là ví dụ |

Ba câu này phải hỏi **riêng**, và `cho_va_xac_minh` chỉ là đường gộp cho những chỗ
cần cả ba. Một hàm duy nhất trả `bool` sẽ mất thông tin ở đúng chỗ cần nó nhất.

## Chỉ thử lại phép ĐỌC

`_goi` của `proxmox.py` cố ý không thử lại gì cả, kể cả GET, vì chỉ người gọi mới
biết thao tác có an toàn khi lặp không. Ở đây thì biết: hỏi trạng thái một tác vụ
là **đọc thuần**, nên một lần mạng chớp không được làm hỏng cả một lần khôi phục
đã chạy được nửa đường. Nhưng số lần chịu đựng phải **có trần** — một endpoint
trạng thái hỏng vĩnh viễn mà cứ hỏi mãi là một vòng lặp im lặng giữ worker.

⛔ **Không bao giờ** thử lại POST ở đây. Xem `proxmox.py` quy tắc 1.

## `nhip` tiêm được — và phải tiêm CẢ ĐỒNG HỒ, không chỉ giấc ngủ

Nhịp chờ đi qua một đối tượng `Nhip` để test không phải chờ thật.

⚠️ Bản đầu chỉ tiêm `ngu`. Kết quả: hàm không ngủ nữa nhưng hạn chót vẫn tính
   theo `time.monotonic()`, nên mọi ca quá hạn **quay tít một lõi CPU cho tới khi
   đủ 300 giây thật**. Bộ test vẫn xanh — nó chỉ mất 301 giây. Đo được, và đó là
   lý do hai thứ này phải đi cùng nhau trong một đối tượng thay vì hai tham số
   mà người gọi có thể quên một.
"""
from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

#: Nhịp hỏi lại trạng thái (giây).
NHIP_S = 5.0

#: Trần thời gian mặc định cho một tác vụ nền (giây). 20 phút — dài hơn một lần
#: clone Windows trên ảo hoá lồng, ngắn hơn `max_runtime_s` của job để job tự báo
#: lỗi thay vì bị nền tảng cắt như một job treo (hai thứ đó nhìn giống nhau trong
#: log nhưng cần hai cách xử lý khác nhau).
HAN_MAC_DINH_S = 20 * 60

#: Trần thời gian chờ máy tới một trạng thái điện. Ngắn hơn nhiều: một lệnh tắt
#: mềm mà Windows không đáp trong 5 phút thì nó sẽ không đáp — nó đang hiện một
#: hộp thoại "có muốn lưu không" và chờ một con người.
HAN_DIEN_S = 5 * 60

#: Bao nhiêu lần đọc trạng thái hỏng liên tiếp thì bỏ cuộc.
#:
#: 3, không phải 1: một lần chớp mạng giữa lúc khôi phục sẽ huỷ một việc đã chạy
#: được nửa đường. Và không phải vô hạn: một endpoint hỏng vĩnh viễn mà cứ hỏi
#: mãi là một vòng lặp im lặng giữ worker cho tới khi hết hạn.
DOC_HONG_TOI_DA = 3

# ── Trạng thái điện: từ chuỗi của Proxmox sang mã của ta ─────────────────────
#
# Proxmox nói `running` / `stopped` / `paused`. Ta không dùng thẳng chuỗi của nó
# vì mô hình của ta có một giá trị thứ tư mà Proxmox không có: `khong_ro` —
# "đã hỏi và không có câu trả lời". Xem `apps/vps/trang_thai_may.py`.

_TU_PROXMOX = {"running": "chay", "stopped": "tat", "paused": "tam_dung",
               "suspended": "tam_dung"}


class TacVuLoi(RuntimeError):
    """Gốc của mọi lỗi ở tầng này. Mang `ma` để chỗ gọi phân loại được."""

    ma = "tac_vu_loi"


class TacVuThatBai(TacVuLoi):
    """Tác vụ đã kết thúc và Proxmox nói nó **hỏng** (`exitstatus` khác `OK`)."""

    ma = "tac_vu_that_bai"


class TacVuQuaHan(TacVuLoi):
    """Hết hạn chờ mà tác vụ vẫn chưa kết thúc.

    ⚠️ Đây **không** phải "tác vụ thất bại". Nó có thể vẫn đang chạy và vẫn sẽ
    thành công sau đó. Người gọi phải xử lý khác nhau: một tác vụ thất bại thì
    làm lại được; một tác vụ quá hạn thì **hỏi lại thế giới thật trước đã**.
    """

    ma = "tac_vu_qua_han"


class KhongDocDuoc(TacVuLoi):
    """Không đọc được trạng thái sau `DOC_HONG_TOI_DA` lần liên tiếp."""

    ma = "khong_doc_duoc"


class DienKhongDat(TacVuLoi):
    """Tác vụ báo OK nhưng máy **không** tới trạng thái điện mong đợi.

    Có thật, và là ca mà mọi test "so thứ tự gọi hàm" bỏ lọt: Proxmox nhận lệnh
    `shutdown`, gửi ACPI cho guest, tác vụ kết thúc `OK` — rồi Windows hiện một
    hộp thoại và không tắt. Tác vụ thành công, máy vẫn chạy.
    """

    ma = "dien_khong_dat"


#: Bộ chờ được tiêu bao nhiêu phần trần thời gian của job.
#:
#: 0,8 — chừa 20% để job còn kịp ghi lý do thật, trả credit, và dọn dẹp. Hết sạch
#: ngân sách rồi mới hỏng thì nền tảng cắt job giữa lúc nó đang dọn.
PHAN_NGAN_SACH_JOB = 0.8


def han_theo_job(job_type: str) -> float:
    """Trần chờ cho một tác vụ nền chạy **bên trong** một job cụ thể.

    ## Vì sao không dùng một hằng số duy nhất

    `HAN_MAC_DINH_S` là 1200 giây, nhưng `manifest.max_runtime_s["vps.destroy"]`
    là **600**. Một bộ chờ 1200 giây nằm trong một job 600 giây thì **không bao
    giờ** tới lượt nó bỏ cuộc: nền tảng cắt job trước, và cái chết đó trông giống
    hệt một job treo trong log — không có dòng nào nói tác vụ Proxmox mới là thứ
    không xong.

    Đây là lỗi có sẵn từ trước VPS V2 (`jobs.CHO_TAC_VU_S = 20*60` dùng chung cho
    cả `vps.destroy`), và nó không bao giờ nổ ra thành một thông báo đọc được.
    `tests/test_551` ghim quan hệ này cho **mọi** job type, nên thêm một job mới
    có trần ngắn cũng không tái tạo lại được nó.
    """
    from apps.vps.manifest import MANIFEST

    tran = MANIFEST.max_runtime_s.get(str(job_type or ""))
    if not tran:
        return float(HAN_MAC_DINH_S)
    return min(float(HAN_MAC_DINH_S), float(tran) * PHAN_NGAN_SACH_JOB)


class Nhip:
    """Đồng hồ + giấc ngủ, đi thành MỘT.

    Tách làm hai tham số là để người gọi tiêm một nửa và quên nửa kia — đúng lỗi
    đã xảy ra: không ngủ nhưng vẫn đo hạn theo đồng hồ thật ⇒ quay tít một lõi.
    """

    def __init__(self, ngu=time.sleep, dong_ho=time.monotonic):
        self.ngu = ngu
        self.dong_ho = dong_ho


#: Nhịp thật. Mặc định của mọi hàm ở đây, và thứ production dùng.
NHIP_THAT = Nhip()


def doc_dien(client, vmid: int) -> str:
    """Trạng thái điện **thật** của một máy, theo mã của ta.

    Không đọc được thì trả `khong_ro` chứ **không** ném: người gọi hỏi câu "máy
    đang thế nào", và câu trả lời trung thực khi không hỏi được là "không biết",
    không phải một ngoại lệ buộc họ đoán.
    """
    try:
        tt = client.trang_thai_vm(int(vmid)) or {}
    except Exception as exc:                     # noqa: BLE001
        log.debug("vps/tac_vu: khong doc duoc dien cua VM %s: %s", vmid, exc)
        return "khong_ro"
    return _TU_PROXMOX.get(str(tt.get("status") or "").lower(), "khong_ro")


def cho_xong(client, upid: str, *, han_s: float = HAN_MAC_DINH_S,
             nhip_s: float = NHIP_S, nhip: Nhip = NHIP_THAT, bao=None) -> dict:
    """Chờ tới khi tác vụ `upid` kết thúc. Trả bản ghi trạng thái cuối cùng.

    Ném `TacVuThatBai` nếu `exitstatus` khác `OK`, `TacVuQuaHan` nếu hết hạn,
    `KhongDocDuoc` nếu endpoint trạng thái hỏng liên tiếp.

    `bao(phan_tram_thoi_gian, trang_thai)` được gọi mỗi vòng để chỗ trên báo tiến
    độ cho khách — tuỳ chọn, vì tầng này không được biết gì về giao diện.
    """
    upid = str(upid or "")
    if not upid:
        raise TacVuLoi("khong co UPID de cho")

    het_han = nhip.dong_ho() + float(han_s)
    hong_lien_tiep = 0
    while True:
        try:
            tt = client.trang_thai_tac_vu(upid) or {}
            hong_lien_tiep = 0
        except Exception as exc:                 # noqa: BLE001
            hong_lien_tiep += 1
            if hong_lien_tiep >= DOC_HONG_TOI_DA:
                raise KhongDocDuoc(
                    f"khong doc duoc trang thai tac vu sau {hong_lien_tiep} lan: "
                    f"{type(exc).__name__}: {exc}") from exc
            tt = {}

        if str(tt.get("status") or "") == "stopped":
            ket_qua = str(tt.get("exitstatus") or "")
            # Proxmox trả `stopped` cho CẢ thành công lẫn thất bại. `exitstatus`
            # là chỗ duy nhất phân biệt, và chuỗi rỗng nghĩa là không có lỗi.
            if ket_qua and ket_qua != "OK":
                raise TacVuThatBai(f"Proxmox bao tac vu that bai: {ket_qua}")
            return dict(tt)

        con = het_han - nhip.dong_ho()
        if con <= 0:
            raise TacVuQuaHan(
                f"tac vu chua xong sau {han_s:.0f}s (upid={upid[:60]})")
        if bao is not None:
            bao(tt)
        nhip.ngu(min(nhip_s, con))


def cho_dien(client, vmid: int, mong_doi: str, *, han_s: float = HAN_DIEN_S,
             nhip_s: float = NHIP_S, nhip: Nhip = NHIP_THAT) -> str:
    """Chờ tới khi máy **thật sự** ở trạng thái điện `mong_doi`.

    Trả về trạng thái đo được (chính là `mong_doi`). Hết hạn ⇒ `DienKhongDat`,
    kèm trạng thái đo được lần cuối — thứ mà người vận hành cần để biết máy đang
    kẹt ở đâu, chứ không chỉ biết là "hỏng".
    """
    het_han = nhip.dong_ho() + float(han_s)
    dien = doc_dien(client, vmid)
    while dien != mong_doi:
        con = het_han - nhip.dong_ho()
        if con <= 0:
            raise DienKhongDat(
                f"VM {vmid} van o trang thai {dien!r} sau {han_s:.0f}s, "
                f"mong doi {mong_doi!r}")
        nhip.ngu(min(nhip_s, con))
        dien = doc_dien(client, vmid)
    return dien


def cho_va_xac_minh(client, upid: str, vmid: int, mong_doi: str, *,
                    han_tac_vu_s: float = HAN_MAC_DINH_S,
                    han_dien_s: float = HAN_DIEN_S,
                    nhip_s: float = NHIP_S, nhip: Nhip = NHIP_THAT) -> str:
    """Chờ tác vụ xong **rồi** xác minh máy tới đúng trạng thái điện mong đợi.

    Hai bước, đúng thứ tự đó. Đảo lại — xác minh trước rồi mới chờ — sẽ thấy
    trạng thái **cũ** và kết luận sai ngay lập tức.

    Đây là hàm mà tầng vòng đời (Pha 03) và khôi phục (Pha 04) gọi.
    """
    cho_xong(client, upid, han_s=han_tac_vu_s, nhip_s=nhip_s, nhip=nhip)
    return cho_dien(client, vmid, mong_doi, han_s=han_dien_s, nhip_s=nhip_s,
                    nhip=nhip)
