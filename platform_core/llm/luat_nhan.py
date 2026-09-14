"""luat_nhan.py — MỘT hàm quyết định có nhận một lượt vào model nhà hay không. (multijob)

⭐ HÀM THUẦN: không CSDL, không đồng hồ, không mạng. `admission.xet_va_giu` chụp ảnh
   trạng thái (lease sống + người đang chờ) TRONG advisory lock của tài nguyên rồi
   hỏi hàm này; phép kiểm gọi thẳng nó với dữ liệu tự dựng. Một chỗ quyết định cho
   cả bốn cửa (stream, đồng bộ, job, planner) ⇒ bốn cửa không thể có bốn luật.

Luật (spec §5, theo thứ tự xét — lượt bị từ chối ở luật ĐẦU TIÊN nó vi phạm, và
mã lý do đó đi vào sổ lượt để phân tích sau):

  0. nhóm GPU đang mở cửa cho vai trò này        · CHO_RESIDENCY
  1. còn slot                                    · CHO_SLOT
  2. Σ đặt chỗ + lượt này ≤ pool KV (khi pool>0)  · CHO_NGAN_SACH
  3. nền/nội bộ: ≤ max(1, N−`chua`) slot, và nhường   · CHO_SLOT / NEN_NHUONG
     mọi người tương tác đang chờ (`chua` = 0 mặc
     định ⇒ nền dùng HẾT slot; xem `tran_nen`)
  4. trần tài khoản ceil(N/2) — CHỈ khi có người   · TRAN_TAI_KHOAN
     khác đang chờ (work-conserving)
  5. whale: ≤1 whale; whale nhường lượt tương tác   · WHALE_NHUONG / WHALE_CHAN
     đang chạy tối đa `cho_whale_toi_da_s`, quá thì
     whale thành CHẶN: không nhận lượt nào khác
  6. FCFS chặt: người chờ đứng TRƯỚC chặn lượt này  · XEP_SAU
     (trừ người chỉ vướng trần tài khoản, và whale
     đang nhường) — chống bỏ đói phiên dài

⛔ llama.cpp KHÔNG preempt được lượt đang chạy (b10689). Nên thứ tự hàng một mình
   không cứu người đang chờ màn hình. Đòn bẩy TỪNG là chừa slot; từ 14/09/2026
   `chua_slot_tuong_tac` mặc định 0 và đòn bẩy còn lại là `NEN_NHUONG` — suất vừa
   nhả về tay người tương tác đang chờ, nhưng họ phải đợi hết một lượt đang chạy.

⭐ VÌ SAO CƯ TRÚ LÀ LUẬT **0** CHỨ KHÔNG PHẢI LUẬT 7 (dual-model 5.3, D01 B).

   Luật 1–6 chia **một tài nguyên đang tồn tại** cho những người tranh nhau nó.
   Luật 0 trả lời câu đứng TRƯỚC đó: *tài nguyên ấy lúc này có phải của bạn
   không* — RTX 3090 chỉ cư trú được MỘT model, nên trong cửa sổ ảnh thì
   `ltt_38_3090` không có slot nào cả, chứ không phải "hết slot".

   Thứ tự ấy là cơ học, không phải thẩm mỹ. Đặt nó sau luật 1–2 thì một lượt
   đang chờ **cư trú** vẫn bị đem so với số slot và vẫn cộng vào Σ token đặt chỗ
   trước khi bị từ chối — tức nó tranh một ngân sách mà nó còn chưa có quyền dự.
   Hệ quả đọc được ở sổ lượt: mã lý do thành `cho_slot`/`cho_ngan_sach`, và người
   phân tích sẽ đi sửa số slot cho một chuyện không liên quan gì tới slot.

⛔ `CHO_RESIDENCY` nghĩa là *"chưa nhận thêm"*, KHÔNG BAO GIỜ là *"dừng thứ đang
   chạy"* (L-9). Không lượt nào bị giết để đổi cư trú: `residency.buoc_thuan` chờ
   drain, và cửa này chỉ ngừng rót thêm việc vào.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

TUONG_TAC = "tuong_tac"
NEN = "nen"
NOI_BO = "noi_bo"
_HANG = {TUONG_TAC: 0, NEN: 1, NOI_BO: 2}

# Mã lý do ỔN ĐỊNH — đi vào `llm_waiters.ly_do_cho`, log và `/ops/jobs-metrics`.
CHO_SLOT = "cho_slot"
CHO_NGAN_SACH = "cho_ngan_sach"
NEN_NHUONG = "nen_nhuong_tuong_tac"
TRAN_TAI_KHOAN = "tran_tai_khoan"
WHALE_NHUONG = "whale_nhuong"
WHALE_CHAN = "whale_chan"
XEP_SAU = "xep_sau"
#: Nhóm GPU đang cư trú cho thành viên KHÁC (D01 B) — xem `llm/residency.py`.
CHO_RESIDENCY = "cho_residency"


@dataclass(frozen=True)
class ThamSo:
    so_slot: int
    #: Pool KV dùng chung. 0 = không áp ngân sách token (tool cũ, hành vi cũ).
    pool: int = 0
    cho_whale_toi_da_s: float = 30.0
    lao_hoa_s: float = 300.0
    #: Số suất GIỮ LẠI cho lượt tương tác, không cho nền/nội bộ chạm tới.
    #: 0 = nền dùng hết slot (mặc định từ 14/09/2026 — xem `tran_nen`).
    chua_slot_tuong_tac: int = 0
    #: Nhóm GPU của tài nguyên này có đang mở cửa cho vai trò của lượt không.
    #:
    #: 🔴 MẶC ĐỊNH `True`, và mặc định ấy là thứ giữ cho nền tảng chạy: mọi tài
    #:    nguyên KHÔNG thuộc một nhóm cư trú (LTT-3.5 trên 5060 Ti, giọng nói,
    #:    mọi tool cũ) không có trọng tài nào để hỏi — một mặc định `False` ở đây
    #:    sẽ đóng cửa cả những cái đó, trong im lặng, và thứ dừng lại sẽ là cả
    #:    nền tảng chứ không riêng 3090. `admission.xet_va_giu` chỉ hạ nó xuống
    #:    khi bản khai của app nói tài nguyên này CÓ nhóm cư trú.
    residency_mo: bool = True


@dataclass(frozen=True)
class Luot:
    """Một lượt đang GIỮ slot hoặc đang CHỜ. `tuoi_s` chỉ có nghĩa với lượt chờ."""

    id: str
    user_id: str
    lop: str = TUONG_TAC
    token_dat_truoc: int = 0
    la_whale: bool = False
    tuoi_s: float = 0.0


@dataclass(frozen=True)
class PhanXu:
    nhan: bool
    ly_do: str = ""


def tran_tai_khoan(so_slot: int) -> int:
    return max(1, math.ceil(so_slot / 2))


def tran_nen(so_slot: int, chua: int = 0) -> int:
    """Số slot tối đa cho nền/nội bộ. `chua` = số suất GIỮ LẠI cho tương tác.

    🔴 `chua` MẶC ĐỊNH 0 — nền được dùng HẾT slot (chốt chủ sản phẩm 14/09/2026:
       *"không trở slot về 2, vì ta đã có hàng chờ job rồi"*). Trước đó hằng số 1
       nằm chết trong hàm, và hệ quả đo được là một lô 3 job trên card 3 slot chỉ
       bao giờ chạy 2: lượt thứ ba chờ 30 giây trong khi GPU còn một suất trống.

    ⚠️ Người tương tác KHÔNG mất bảo vệ khi `chua = 0`: vế sau của luật 3
       (`NEN_NHUONG`) vẫn chặn mọi lượt nền mới khi có người tương tác đang CHỜ,
       nên suất vừa nhả ra luôn về tay người ngồi đợi màn hình trước hàng job.
       Thứ mất đi là suất chờ SẴN — người tương tác nay đợi hết một lượt đang
       chạy (đo 14/09: ~30 s ở `max_tokens=1500`) thay vì vào ngay.

    🔴 `max(1, …)` KHÔNG phải dè dặt: ở N = 1 (pha 1) với `chua = 1` thì "N−1" là
       0, tức job nền không bao giờ được chạy. Chừa slot chỉ có nghĩa khi có hơn
       một slot.

    ⛔ HỆ QUẢ PHẢI BIẾT: ở `chua = 0` (mặc định), vế đầu của luật 3 là **mã
       không bao giờ chạy**. `tran_nen(N, 0) = N`, mà muốn `Σ lượt-không-tương-tác
       ≥ N` thì tổng lượt đang giữ cũng phải `≥ N` — và luật 1 đã từ chối ở đó
       rồi, từ chối mọi lớp như nhau. Tức **lớp của lượt ĐANG GIỮ không còn ảnh
       hưởng gì tới quyết định** trừ khi ai đó đặt `chua ≥ 1`; thứ còn phân biệt
       là lớp của lượt ĐANG XIN, qua `NEN_NHUONG` ở vế sau.

       Ghi ra đây vì nó đã cắn một lần: `test_1204::test_lease_cu_mode_job_...`
       chứng minh "lease cũ được đọc là nền" *bằng chính vế đầu ấy*, nên khi
       `chua` về 0 nó đỏ — không phải vì ánh xạ hỏng, mà vì phép kiểm đo qua một
       cánh cửa vừa bị khoá. Nó đã được viết lại quanh phép ánh xạ.
    """
    return max(1, so_slot - chua)


def sap_xep_cho(dang_cho: Iterable[Luot], dang_giu: Iterable[Luot],
                ts: ThamSo) -> list[Luot]:
    """Thứ tự phục vụ người chờ: lớp → lão hoá → ai đang giữ ít slot hơn → chờ lâu hơn.

    ⭐ "Ai đang giữ ít hơn trước" là công bằng theo tài khoản (cùng tinh thần
       `jobs.py:206-224`); lão hoá đẩy người chờ quá `lao_hoa_s` lên trước để
       không ai đói. Giá tiền KHÔNG tham gia phép xếp — như hàng `jobs`.
    """
    so_giu: dict[str, int] = {}
    for g in dang_giu:
        so_giu[g.user_id] = so_giu.get(g.user_id, 0) + 1

    def khoa(c: Luot) -> tuple:
        gia = c.tuoi_s >= ts.lao_hoa_s
        return (_HANG.get(c.lop, 9), 0 if gia else 1, so_giu.get(c.user_id, 0),
                -c.tuoi_s, c.id)

    return sorted(dang_cho, key=khoa)


def _vuong_tran_tai_khoan(l: Luot, dang_giu: list[Luot], dang_cho: list[Luot],
                          ts: ThamSo) -> bool:
    nguoi_khac_cho = any(c.user_id != l.user_id for c in dang_cho if c.id != l.id)
    if not nguoi_khac_cho:
        return False
    return sum(1 for g in dang_giu if g.user_id == l.user_id) >= tran_tai_khoan(ts.so_slot)


def _whale_dang_nhuong(l: Luot, ts: ThamSo) -> bool:
    return l.la_whale and l.tuoi_s < ts.cho_whale_toi_da_s


def xet(yc: Luot, dang_giu: Iterable[Luot], dang_cho: Iterable[Luot],
        ts: ThamSo) -> PhanXu:
    """Có nhận `yc` ngay bây giờ không. `dang_cho` có thể chứa chính `yc`."""
    # 0. cư trú GPU — TRƯỚC cả phép chụp hai danh sách, vì lượt này còn chưa dự
    #    tranh slot hay ngân sách: nhóm GPU lúc này đang là của model kia.
    if not ts.residency_mo:
        return PhanXu(False, CHO_RESIDENCY)

    giu = list(dang_giu)
    cho_tat_ca = list(dang_cho)
    cho_khac = [c for c in cho_tat_ca if c.id != yc.id]

    # 1. slot
    if len(giu) >= ts.so_slot:
        return PhanXu(False, CHO_SLOT)
    # 2. ngân sách KV
    if ts.pool > 0 and sum(g.token_dat_truoc for g in giu) + yc.token_dat_truoc > ts.pool:
        return PhanXu(False, CHO_NGAN_SACH)
    # 3. nền / nội bộ: chừa ≥1 slot cho tương tác, và nhường người tương tác đang chờ
    if yc.lop != TUONG_TAC:
        if sum(1 for g in giu if g.lop != TUONG_TAC) >= tran_nen(
                ts.so_slot, ts.chua_slot_tuong_tac):
            return PhanXu(False, CHO_SLOT)
        if any(c.lop == TUONG_TAC for c in cho_khac):
            return PhanXu(False, NEN_NHUONG)
    # 4. trần tài khoản (chỉ khi có người khác chờ)
    if _vuong_tran_tai_khoan(yc, giu, cho_tat_ca, ts):
        return PhanXu(False, TRAN_TAI_KHOAN)
    # 5. whale
    if yc.la_whale:
        if any(g.la_whale for g in giu):
            return PhanXu(False, WHALE_NHUONG)
        if yc.tuoi_s < ts.cho_whale_toi_da_s and any(g.lop == TUONG_TAC for g in giu):
            return PhanXu(False, WHALE_NHUONG)
    elif any(c.la_whale and c.tuoi_s >= ts.cho_whale_toi_da_s for c in cho_khac):
        return PhanXu(False, WHALE_CHAN)
    # 6. FCFS chặt giữa những người chờ
    ds = cho_tat_ca if any(c.id == yc.id for c in cho_tat_ca) else cho_tat_ca + [yc]
    for c in sap_xep_cho(ds, giu, ts):
        if c.id == yc.id:
            break
        if _vuong_tran_tai_khoan(c, giu, cho_tat_ca, ts) or _whale_dang_nhuong(c, ts):
            continue
        return PhanXu(False, XEP_SAU)
    return PhanXu(True)
