"""nghien_cuu.py — vòng nghiên cứu: mục tiêu → nguồn → tổng hợp → KIỂM TRÍCH DẪN.
(H44 B6 bước 2)

## Bước cuối không phải "tổng hợp". Nó là **kiểm trích dẫn**.

Mượn vòng của `gpt-researcher` (đọc đặc tả 07/09): *mục tiêu → kế hoạch → thu
nguồn → trích → tổng hợp → kiểm trích dẫn*. Năm bước đầu ai cũng nghĩ ra; bước
thứ sáu là bước phân biệt một sản phẩm nghiên cứu với **một cái máy nói linh
tinh có tự tin** — chính câu P06 §4 dùng để giải thích vì sao trích dẫn tồn tại.

🔴 Và issue #1846 của họ cho thấy nó hỏng thế nào trong thực tế: một nguồn không
   bao giờ được đọc ⇒ *"báo cáo kết thúc mà không có trích dẫn kiểm được"*. Báo
   cáo vẫn trôi chảy. Không ai thấy gì sai.

⇒ Ở đây, một khẳng định **không phân giải được về một nguồn đã thu** thì bị
  **loại khỏi báo cáo**, và số bị loại được **nói ra**. Không im lặng giữ lại,
  không im lặng vứt đi.

## Model KHÔNG được tự do trỏ vào đâu cũng được

Model nhận nguồn kèm **số thứ tự** và chỉ được trích dẫn bằng số ấy. Nó không
nhìn thấy `doan_id`, nên nó **không thể** bịa một id trông giống thật — thứ mà
một phép kiểm chuỗi sẽ cho qua.

⭐ Cùng hình dạng với `thi_hanh(boi_canh=…)`: thứ model không nhìn thấy thì model
   không đặt được.

## Trần là tiền, nên trần phải NÓI RA khi chạm

Mỗi vòng là một lượt model. `dieu_phoi` của P05 đã có `tran_vong`/`tran_tool` và
`ly_do_ket`; ở đây cũng vậy — chạm trần thì `BaoCao.ly_do_dung` nói ra, và giao
diện hiện nó. Cắt im lặng là để khách trả tiền cho một câu trả lời thiếu mà
tưởng là đủ.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from apps.chatltt.services.nguon import Nguon

#: Trần vòng thu nguồn. Mỗi vòng là một lượt model + một lượt truy vấn.
TRAN_VONG = 3
#: Trần tổng số nguồn gom được. Ngữ cảnh model có hạn, và mỗi nguồn là token.
TRAN_NGUON = 12
#: Trần nguồn mỗi vòng.
TRAN_NGUON_MOI_VONG = 5

#: Lý do dừng. Cùng khuôn `dieu_phoi.LY_DO_KET`: một enum, không phải một câu.
LY_DO = ("xong", "tran_vong", "tran_nguon", "khong_co_nguon", "loi")

#: `[1]`, `[2]` … — cách DUY NHẤT model được trỏ về nguồn.
_TRICH = re.compile(r"\[(\d+)\]")


class LoiNghienCuu(RuntimeError):
    """Vòng nghiên cứu hỏng ở một chỗ không phải lỗi của người dùng."""


@dataclass
class KhangDinh:
    """Một câu trong báo cáo, **đã** gắn nguồn của nó."""

    chu: str
    #: Các `Nguon` đã phân giải được. Rỗng ⇒ khẳng định này bị loại.
    nguon: list = field(default_factory=list)


@dataclass
class BaoCao:
    cau_hoi: str
    khang_dinh: list = field(default_factory=list)
    nguon: list = field(default_factory=list)
    ly_do_dung: str = "xong"
    so_vong: int = 0
    #: Số câu model viết ra mà **không** phân giải được về nguồn nào.
    so_bi_loai: int = 0

    @property
    def rong(self) -> bool:
        return not self.khang_dinh


def _cau(van: str) -> list[str]:
    """Tách báo cáo thành câu. Một dòng là một khẳng định.

    ⭐ Tách theo **dòng**, không theo dấu chấm: model viết báo cáo theo gạch đầu
       dòng, và một dấu chấm trong *"12,5 tr.đ"* hay *"tr. 7"* sẽ cắt giữa câu —
       rồi nửa sau mất trích dẫn và bị loại oan.
    """
    return [d.strip(" -•\t") for d in (van or "").splitlines() if d.strip(" -•\t")]


def kiem_trich_dan(van: str, nguon: list[Nguon]) -> tuple[list[KhangDinh], int]:
    """Chữ model viết → các `KhangDinh` **đã phân giải nguồn**, và số câu bị loại.

    🔴 Đây là bước quyết định của cả tệp. Một khẳng định trỏ vào `[7]` khi chỉ
       có 3 nguồn là một khẳng định **bịa**, và nó phải biến mất khỏi báo cáo —
       không phải được giữ lại kèm một cảnh báo nhỏ ở cuối trang.

    ⛔ Và một câu **không có** trích dẫn nào cũng bị loại. Nghe khắt khe, nhưng
       đó chính là lời hứa: sản phẩm này không viết câu nào nó không chỉ được
       nguồn. Câu mở đầu kiểu *"Dưới đây là tổng hợp"* mất đi là cái giá rẻ.
    """
    ra: list[KhangDinh] = []
    bi_loai = 0
    for c in _cau(van):
        so = {int(m) for m in _TRICH.findall(c)}
        hop_le = [nguon[i - 1] for i in sorted(so) if 1 <= i <= len(nguon)]
        if not hop_le:
            bi_loai += 1
            continue
        ra.append(KhangDinh(chu=_TRICH.sub("", c).strip(), nguon=hop_le))
    return ra, bi_loai


def _danh_sach_nguon(nguon: list[Nguon]) -> str:
    """Nguồn → chữ cho model, **đánh số từ 1**.

    ⛔ Không đưa `doan_id` vào đây. Model không nhìn thấy id thì không bịa được
       một id trông giống thật — thứ mà một phép kiểm chuỗi sẽ cho qua.
    """
    return "\n\n".join(f"[{i}] {n.chu}" for i, n in enumerate(nguon, 1))


def chay(*, cau_hoi: str, thu, goi_model,
         tran_vong: int = TRAN_VONG, tran_nguon: int = TRAN_NGUON) -> BaoCao:
    """Chạy vòng nghiên cứu.

    `thu(cau_hoi, so_toi_da) -> list[Nguon]` và `goi_model(nhac) -> str` được
    **tiêm vào**, không import ở đây.

    ⭐ Vì sao tiêm: vòng lặp không được biết nguồn đến từ đâu (§0.3 của kế hoạch
       — `gpt-researcher` có 21 bộ thu), và cũng không được biết model nào đang
       chạy. Cả hai là thứ `apps/chatltt/jobs.py` nối vào ở bước 3.

    ⛔ Kho rỗng ⇒ trả `BaoCao` rỗng với `ly_do_dung="khong_co_nguon"`, **không**
       gọi model. Gọi model với không nguồn nào là mời nó viết một bài trôi chảy
       không trích dẫn — rồi `kiem_trich_dan` loại sạch, và ta đã tiêu tiền của
       khách cho một lượt chắc chắn ra rỗng.
    """
    bc = BaoCao(cau_hoi=str(cau_hoi or "").strip())
    if not bc.cau_hoi:
        raise LoiNghienCuu("cau hoi rong")

    gom: list[Nguon] = []
    da_thay: set = set()
    hoi = bc.cau_hoi
    for vong in range(1, int(tran_vong) + 1):
        bc.so_vong = vong
        con = max(0, int(tran_nguon) - len(gom))
        if con == 0:
            bc.ly_do_dung = "tran_nguon"
            break
        moi = thu(hoi, min(TRAN_NGUON_MOI_VONG, con))
        for n in moi:
            khoa = (n.loai, n.trich_dan.get("doan_id") or n.chu[:80])
            if khoa in da_thay:
                continue
            da_thay.add(khoa)
            gom.append(n)
        if not moi:
            # Khong con gi moi de thu — dung som, dung dot them mot vong model.
            break
        if vong < tran_vong:
            # ⭐ Vong sau hoi HEP hon, dua tren thu da doc. Day la ca ly do vong
            #    lap ton tai: mot cau hoi rong tra ve nguon rong.
            hoi = str(goi_model(
                "Dua tren cac nguon duoi day, viet MOT cau truy van ngan de tim "
                "them thong tin CON THIEU cho cau hoi goc. Chi tra ve cau truy "
                f"van.\n\nCau hoi goc: {bc.cau_hoi}\n\n{_danh_sach_nguon(gom)}"
            ) or "").strip() or bc.cau_hoi
    else:
        # ⭐ Het vong = `tran_vong`, KHONG dieu kien. Toi da thu them mot dieu
        #    kien "chi bao tran khi vong cuoi con dao ra duoc", va no sai: het
        #    vong nghia la ta **chua bao gio hoi lai** xem con gi khong, nen
        #    bao "xong" la khang dinh mot su day du chua kiem.
        #
        # ⇒ Voi `tran_vong=1` thi ly do LUON la `tran_vong`. Do la dung: mot
        #   vong khong bao gio kiem duoc rang con hay het.
        bc.ly_do_dung = "tran_vong"

    bc.nguon = gom
    if not gom:
        # ⛔ Khong goi model. Xem docstring.
        bc.ly_do_dung = "khong_co_nguon"
        return bc

    van = goi_model(
        "Tra loi cau hoi CHI bang cac nguon duoi day. Moi cau phai ket thuc "
        "bang so nguon trong ngoac vuong, vi du [1] hoac [1][3]. KHONG viet cau "
        "nao khong co nguon. Moi cau mot dong.\n\n"
        f"Cau hoi: {bc.cau_hoi}\n\n{_danh_sach_nguon(gom)}")

    bc.khang_dinh, bc.so_bi_loai = kiem_trich_dan(str(van or ""), gom)
    return bc
