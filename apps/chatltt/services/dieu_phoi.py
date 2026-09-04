"""
dieu_phoi.py — máy trạng thái của MỘT run: vòng model → tool → vòng model. (H44 P03)

Đặc tả: `02_HOP_DONG.md` §1 (10 trạng thái + bảng chuyển đổi hợp lệ) và §4 (trần).

## Bộ điều phối THUẦN — không biết CSDL, không biết máy B

`chay()` nhận hai hàm từ ngoài:

    goi_model(messages, tools) -> Iterator[su kien canonical]
    chay_tool(ten, doi_so)     -> thi_hanh.KetQua

⭐ Không phải để "dễ test" — mà vì nó là **ranh giới đúng**. `luot.py` biết
`mo_luong` và phiên CSDL; tệp này biết **luật của một lượt**. Trộn hai thứ lại
là thứ đã làm `routes.py` của một app khác phình lên 1.799 dòng.

## Chạm trần là COMPLETED, không phải FAILED

`02_HOP_DONG.md` §4. Người dùng phải nhận được thứ model **đã làm được**, kèm
một câu nói rõ nó dừng vì trần. `FAILED` là "hỏng"; chạm trần là "đủ rồi" — hai
thông điệp khác nhau với người đang chờ, và với sổ tiền.

## Chuyển đổi lạ thì NÉM

Cùng luật `su_kien.ap_dung` đã dùng: fail-closed. Một chuyển đổi ngoài bảng là
lỗi lập trình, không phải dữ liệu để bỏ qua. Ném ở đây rẻ hơn nhiều so với một
run đi vào trạng thái không ai định nghĩa rồi hỏng ở ba tầng sau.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from apps.chatltt.services import chieu_tool, gop_manh, thi_hanh

# ── 10 trạng thái ──────────────────────────────────────────────────────────
CREATED = "CREATED"
MODEL_RUNNING = "MODEL_RUNNING"
TOOL_REQUESTED = "TOOL_REQUESTED"
AWAITING_APPROVAL = "AWAITING_APPROVAL"
TOOL_RUNNING = "TOOL_RUNNING"
WAITING_BACKGROUND = "WAITING_BACKGROUND"
TOOL_RESULT_READY = "TOOL_RESULT_READY"
MODEL_RESUMING = "MODEL_RESUMING"
WAITING_SLOT = "WAITING_SLOT"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"

KET_THUC = frozenset({COMPLETED, FAILED, CANCELLED})

#: Bảng chuyển đổi HỢP LỆ. Mọi cặp ngoài đây là lỗi lập trình.
CHUYEN_HOP_LE: dict = {
    CREATED: {MODEL_RUNNING, WAITING_SLOT, CANCELLED},
    MODEL_RUNNING: {TOOL_REQUESTED, COMPLETED, FAILED, CANCELLED},
    TOOL_REQUESTED: {AWAITING_APPROVAL, TOOL_RUNNING, TOOL_RESULT_READY,
                     FAILED, CANCELLED},
    AWAITING_APPROVAL: {TOOL_RUNNING, TOOL_RESULT_READY, CANCELLED},
    TOOL_RUNNING: {WAITING_BACKGROUND, TOOL_RESULT_READY, FAILED, CANCELLED},
    WAITING_BACKGROUND: {TOOL_RESULT_READY, FAILED, CANCELLED},
    TOOL_RESULT_READY: {MODEL_RESUMING, COMPLETED, CANCELLED},
    MODEL_RESUMING: {MODEL_RUNNING, WAITING_SLOT, FAILED, CANCELLED},
    WAITING_SLOT: {MODEL_RUNNING, FAILED, CANCELLED},
    COMPLETED: set(), FAILED: set(), CANCELLED: set(),
}

# ── Trần (§4) ──────────────────────────────────────────────────────────────
TRAN_VONG_MODEL = 8
TRAN_LOI_GOI_TOOL = 12
TRAN_TRUNG = 2

# Lý do kết thúc — chuỗi ổn định cho giao diện và test.
KET_XONG = "xong"
KET_TRAN_VONG = "tran_vong"
KET_TRAN_TOOL = "tran_tool"
KET_TRAN_TRUNG = "tran_trung"
KET_HUY = "huy"
KET_LOI = "loi"


class ChuyenTrangThaiSai(RuntimeError):
    """Chuyển đổi ngoài `CHUYEN_HOP_LE`."""


@dataclass
class Buoc:
    """Một bước đã chạy — ánh xạ 1-1 sang `chatltt_step`."""

    thu_tu: int
    loai: str                       # "model" | "tool"
    ten: str = ""
    doi_so: dict = field(default_factory=dict)
    doi_so_tho: str = ""
    ket_qua: Optional[thi_hanh.KetQua] = None
    bam: str = ""


@dataclass
class Run:
    """Trạng thái một lượt. Ánh xạ 1-1 sang `chatltt_run`."""

    trang_thai: str = CREATED
    so_vong_model: int = 0
    so_loi_goi_tool: int = 0
    ly_do_ket: str = ""
    buoc: list = field(default_factory=list)
    van_ban_cuoi: str = ""
    _dem_bam: dict = field(default_factory=dict)

    def chuyen(self, toi: str) -> None:
        cho_phep = CHUYEN_HOP_LE.get(self.trang_thai)
        if cho_phep is None or toi not in cho_phep:
            raise ChuyenTrangThaiSai(f"{self.trang_thai} -> {toi} khong hop le")
        self.trang_thai = toi

    def xong(self) -> bool:
        return self.trang_thai in KET_THUC


def _tin_nhan_tool(lg: gop_manh.LoiGoi, kq: thi_hanh.KetQua) -> dict:
    """Kết quả tool → một message `role="tool"` cho vòng model kế tiếp."""
    return {"role": "tool", "tool_call_id": lg.id or f"call_{lg.index}",
            "content": kq.cho_model()}


def _tin_nhan_assistant(loi_goi: list) -> dict:
    """Lời gọi của model → message `assistant` mang `tool_calls`.

    ⛔ Phải có message này trong lịch sử, nếu không vòng sau thấy một
       `role="tool"` mồ côi — và `llama.cpp` issue #27588 nói rõ đường nối tiếp
       xử lý ca đó không đáng tin.
    """
    return {"role": "assistant", "content": "",
            "tool_calls": [{"id": lg.id or f"call_{lg.index}", "type": "function",
                            "function": {"name": lg.ten,
                                         "arguments": lg.doi_so_tho or "{}"}}
                           for lg in loi_goi]}


def chay(*, messages: list, tools: list,
         goi_model: Callable[[list, list], Iterable[dict]],
         chay_tool: Callable[[str, dict], thi_hanh.KetQua],
         tran_vong: int = TRAN_VONG_MODEL,
         tran_tool: int = TRAN_LOI_GOI_TOOL,
         phat: Optional[Callable[[dict], None]] = None,
         ghi: Optional[Callable[["Buoc"], None]] = None,
         nen_dung: Optional[Callable[[], bool]] = None) -> Run:
    """Chạy trọn một run. Trả `Run` đã ở trạng thái kết thúc.

    `phat` nhận sự kiện canonical để đẩy ra SSE. `nen_dung` cho nút Dừng.

    ## Vì sao `ghi` là kênh RIÊNG, không dùng chung với `phat`

    Trông thì hai kênh cùng nói "vừa có chuyện xảy ra", nhưng chúng khác nhau ở
    hai điểm không hoà được:

    - **Độ trung thực.** `phat` đi ra dây, nên nó đã tóm tắt và cắt bớt.
      `ghi` phải giữ nguyên `doi_so_tho` — chuỗi model thật sự phát ra, thứ
      không dựng lại được từ bất cứ sự kiện SSE nào.
    - **Hậu quả khi hỏng.** Một `phat` hỏng chỉ là người dùng không thấy một
      dòng; một `ghi` hỏng là lịch sử của run có lỗ. Gộp chúng lại buộc hai
      mức nghiêm trọng ấy dùng chung một cách xử lý lỗi.

    Cả hai đều **tuỳ chọn**: máy trạng thái vẫn chạy đúng khi không ai lắng nghe
    và không ai lưu — đó là thứ giữ nó kiểm được bằng số học thuần (`test_803`).
    """
    run = Run()
    lich_su = list(messages)
    _phat = phat or (lambda sk: None)
    _ghi = ghi or (lambda b: None)

    def _them(b: Buoc) -> Buoc:
        """Chỗ DUY NHẤT một bước được sinh ra. Hai lối vào thì sớm muộn một lối
        quên gọi `_ghi`, và cái mất là một bước — im lặng."""
        run.buoc.append(b)
        _ghi(b)
        return b

    _phat({"type": "run.started", "so_vong_toi_da": tran_vong})

    while True:
        if nen_dung and nen_dung():
            run.chuyen(CANCELLED)
            run.ly_do_ket = KET_HUY
            break

        # ── Vòng model ──────────────────────────────────────────────────
        run.chuyen(MODEL_RUNNING if run.trang_thai in (CREATED, MODEL_RESUMING)
                   else MODEL_RUNNING)
        run.so_vong_model += 1
        bo = gop_manh.BoGop()
        chu = []
        ly_do = ""
        loi_luong = ""
        for sk in goi_model(lich_su, tools):
            loai = sk.get("type")
            if loai == "response.delta":
                chu.append(sk.get("text") or "")
            elif loai == "tool_call.delta":
                bo.nhin(sk)
            elif loai == "response.completed":
                ly_do = sk.get("finish_reason") or ""
            elif loai == "response.failed":
                loi_luong = sk.get("code") or "loi"
            _phat(sk)
        _them(Buoc(thu_tu=len(run.buoc) + 1, loai="model"))
        run.van_ban_cuoi = "".join(chu)

        if loi_luong:
            run.chuyen(FAILED)
            run.ly_do_ket = KET_LOI
            break

        loi_goi = bo.xong()
        if not loi_goi:
            # Model trả lời bằng chữ ⇒ xong. Đây là đường ra thường nhất.
            run.chuyen(COMPLETED)
            run.ly_do_ket = KET_XONG
            break

        # ── Có lời gọi tool ─────────────────────────────────────────────
        run.chuyen(TOOL_REQUESTED)
        if run.so_loi_goi_tool + len(loi_goi) > tran_tool:
            run.chuyen(TOOL_RESULT_READY)
            run.chuyen(COMPLETED)
            run.ly_do_ket = KET_TRAN_TOOL
            break

        lich_su = lich_su + [_tin_nhan_assistant(loi_goi)]
        cham_tran_trung = False
        for lg in loi_goi:
            run.so_loi_goi_tool += 1
            try:
                ds = lg.doi_so()
            except gop_manh.DoiSoHong as e:
                # Đối số hỏng là DỮ LIỆU cho model sửa (`02_HOP_DONG.md` §1).
                kq = thi_hanh.KetQua(False, ma_loi=thi_hanh.LOI_DOI_SO,
                                     thong_diep=str(e))
                ds = {}
            else:
                bam = gop_manh.bam_trung(lg.ten, ds)
                n = run._dem_bam.get(bam, 0) + 1
                run._dem_bam[bam] = n
                if n > TRAN_TRUNG:
                    # ⛔ Không chạy lần thứ ba. Nói cho model biết vì sao, để nó
                    #    đổi cách thay vì gọi mãi.
                    kq = thi_hanh.KetQua(
                        False, ma_loi="trung",
                        thong_diep=(f"da goi {lg.ten!r} voi cung doi so {n-1} lan. "
                                    f"Hay doi cach tiep can hoac tra loi truc tiep."))
                    cham_tran_trung = True
                else:
                    _phat({"type": "tool.requested", "tool_name": lg.ten,
                           "policy_class": chieu_tool.lop_chinh_sach(lg.ten)})
                    kq = chay_tool(lg.ten, ds)

            _them(Buoc(thu_tu=len(run.buoc) + 1, loai="tool",
                       ten=lg.ten, doi_so=ds,
                       doi_so_tho=lg.doi_so_tho, ket_qua=kq,
                       bam=gop_manh.bam_trung(lg.ten, ds)))
            _phat({"type": "tool.result" if kq.ok else "tool.failed",
                   "tool_name": lg.ten, "tom_tat": kq.tom_tat()})
            lich_su = lich_su + [_tin_nhan_tool(lg, kq)]

        if run.trang_thai == TOOL_REQUESTED:
            run.chuyen(TOOL_RUNNING)
        run.chuyen(TOOL_RESULT_READY)

        if cham_tran_trung:
            run.chuyen(COMPLETED)
            run.ly_do_ket = KET_TRAN_TRUNG
            break
        if run.so_vong_model >= tran_vong:
            run.chuyen(COMPLETED)
            run.ly_do_ket = KET_TRAN_VONG
            break
        run.chuyen(MODEL_RESUMING)

    _phat({"type": "run.completed" if run.trang_thai == COMPLETED else "run.failed",
           "ly_do_ket": run.ly_do_ket, "so_vong": run.so_vong_model,
           "so_loi_goi_tool": run.so_loi_goi_tool})
    return run


__all__ = ["chay", "Run", "Buoc", "ChuyenTrangThaiSai", "CHUYEN_HOP_LE",
           "TRAN_VONG_MODEL", "TRAN_LOI_GOI_TOOL", "TRAN_TRUNG",
           "CREATED", "MODEL_RUNNING", "TOOL_REQUESTED", "AWAITING_APPROVAL",
           "TOOL_RUNNING", "WAITING_BACKGROUND", "TOOL_RESULT_READY",
           "MODEL_RESUMING", "WAITING_SLOT", "COMPLETED", "FAILED", "CANCELLED",
           "KET_XONG", "KET_TRAN_VONG", "KET_TRAN_TOOL", "KET_TRAN_TRUNG",
           "KET_HUY", "KET_LOI"]
