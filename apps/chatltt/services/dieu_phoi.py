"""
dieu_phoi.py — máy trạng thái của MỘT run: vòng model → tool → vòng model. (H44 P03)

Đặc tả: `02_HOP_DONG.md` §1 (10 trạng thái + bảng chuyển đổi hợp lệ) và §4 (trần).

## Bộ điều phối THUẦN — không biết CSDL, không biết máy B

`chay()` nhận hai hàm từ ngoài:

    goi_model(messages, tools) -> Iterator[su kien canonical]
    chay_tool(ten, doi_so, ctx) -> thi_hanh.KetQua | CanDuyet

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

#: Trạng thái mà `tiep_tuc()` vào lại được — hai kiểu chờ, một cơ chế.
CHO_DUOC = frozenset({AWAITING_APPROVAL, WAITING_BACKGROUND})

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
class CanDuyet:
    """`chay_tool` trả cái này thay cho `KetQua` ⇒ run **dừng** chờ người duyệt.

    ## Vì sao là GIÁ TRỊ TRẢ VỀ chứ không phải một ngoại lệ

    Chờ duyệt không phải chuyện bất thường — với một tool `PAID` thì đó là
    đường đi **bình thường**. Ngoại lệ dành cho thứ không nằm trong kế hoạch;
    dùng nó cho một nhánh dự kiến biến `try/except` thành cấu trúc điều khiển,
    và rồi một `except Exception` ở đâu đó sẽ nuốt mất một phiếu duyệt.

    ⭐ Và nó giữ `chay_tool` **thuần một kiểu quyết định**: hàm ấy trả lời
       *"chạy xong rồi, đây là kết quả"* hay *"chưa chạy, cần hỏi đã"*. Cả hai
       đều là câu trả lời.
    """

    approval_id: str
    tool_name: str = ""
    doi_so: dict = field(default_factory=dict)


@dataclass
class ChoJob:
    """`chay_tool` trả cái này ⇒ run **dừng** chờ một job nền xong. (P05)

    Anh em của `CanDuyet`, và cố ý giống nhau: hai lý do dừng khác nhau (chờ
    **người** vs chờ **máy**) nhưng cùng một cơ chế — ghi bước, trả về, rồi
    `tiep_tuc()` khi có câu trả lời.

    ⛔ **Không chờ bằng một vòng `while` trong luồng của run.** `job_runner.py`
       đã có vòng đời job và `leases.py` đã có lease; một vòng chờ ở đây là bộ
       đợi thứ hai — và nó giữ một luồng qua cả những lần khởi động lại mà
       `job_runner` chịu được còn nó thì không.

    ⭐ Và nó giải quyết trần 100 giây của Cloudflare miễn phí: run không giữ
       request nào, nên một job 5 phút không làm ai 524.
    """

    job_id: str
    tool_name: str = ""
    doi_so: dict = field(default_factory=dict)


@dataclass
class NgoCanhGoi:
    """Tham số thứ ba của `chay_tool`: **lời gọi này là lời gọi nào**.

    ## Vì sao bộ thi hành cần biết, chứ không chỉ cần `(tên, đối số)`

    Hai việc bắt buộc phải có nó, và cả hai đều là chuyện tiền:

    - **Phiếu duyệt** gắn vào một bước cụ thể (`UNIQUE(step_id)`). Không có
      danh tính bước thì hai lần gọi cùng một tool trong một run không phân
      biệt được, và phiếu thứ hai đụng ràng buộc của phiếu thứ nhất.
    - **`chatltt_execution.step_id`** nối một bút toán với bước sinh ra nó.

    ⛔ Đừng thay nó bằng một bộ đếm riêng bên gọi tự giữ. Hai bộ đếm cho cùng
       một thứ là hai bộ đếm sẽ lệch — và chúng lệch đúng lúc có nhánh lạ xảy
       ra, tức đúng lúc khó lần nhất.
    """

    thu_tu: int
    goi_id: str = ""
    bam: str = ""
    #: Id hàng `chatltt_step` đã ghi. Rỗng khi không ai lưu (test thuần).
    step_id: str = ""


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
    #: `approval_id` khi bước này đang chờ duyệt. `ket_qua` còn `None`.
    cho_duyet: str = ""
    #: `job_id` khi bước này đang chờ một job nền. `ket_qua` còn `None`.
    cho_job: str = ""
    #: `tool_call_id` model đã dùng — cần để dựng lại `role="tool"` khi chạy tiếp.
    goi_id: str = ""
    #: Id hàng `chatltt_step` — `luu_run.ghi_buoc` điền vào lần ghi đầu.
    step_id: str = ""


@dataclass
class Run:
    """Trạng thái một lượt. Ánh xạ 1-1 sang `chatltt_run`."""

    trang_thai: str = CREATED
    so_vong_model: int = 0
    so_loi_goi_tool: int = 0
    ly_do_ket: str = ""
    buoc: list = field(default_factory=list)
    van_ban_cuoi: str = ""
    #: Lịch sử hội thoại đang dựng. **Nằm trong `Run`**, không phải biến cục bộ
    #: của `chay()` — vì một run dừng ở `AWAITING_APPROVAL` rồi `tiep_tuc()`
    #: nhiều phút sau phải nói tiếp đúng câu chuyện đó.
    lich_su: list = field(default_factory=list)
    tools: list = field(default_factory=list)
    _dem_bam: dict = field(default_factory=dict)

    def dang_cho_duyet(self) -> list:
        """Các bước còn treo chờ người duyệt."""
        return [b for b in self.buoc if b.cho_duyet and b.ket_qua is None]

    def dang_cho_job(self) -> list:
        """Các bước còn treo chờ một job nền."""
        return [b for b in self.buoc if b.cho_job and b.ket_qua is None]

    def dang_treo(self) -> list:
        """Mọi bước chưa có kết quả, dù chờ người hay chờ máy.

        ⛔ Một hàm, không hai. `tiep_tuc` phải đòi **đủ** câu trả lời cho mọi
           bước treo; tách thành hai danh sách là để một lần quên kiểm danh sách
           thứ hai biến một lời gọi tool thành im lặng.
        """
        return [b for b in self.buoc
                if (b.cho_duyet or b.cho_job) and b.ket_qua is None]

    def khoa_treo(self, b: "Buoc") -> str:
        """Khoá tra câu trả lời cho một bước treo: `approval_id` hoặc `job_id`."""
        return b.cho_duyet or b.cho_job

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
         chay_tool: Callable[[str, dict, "NgoCanhGoi"], thi_hanh.KetQua],
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
    run = Run(lich_su=list(messages), tools=list(tools))
    _phat = phat or (lambda sk: None)
    _phat({"type": "run.started", "so_vong_toi_da": tran_vong})
    return _vong(run, goi_model=goi_model, chay_tool=chay_tool,
                 tran_vong=tran_vong, tran_tool=tran_tool,
                 phat=phat, ghi=ghi, nen_dung=nen_dung)


def _vong(run: Run, *, goi_model, chay_tool, tran_vong, tran_tool,
          phat=None, ghi=None, nen_dung=None) -> Run:
    """Vòng lặp chính. Tách khỏi `chay()` để `tiep_tuc()` vào lại được."""
    _phat = phat or (lambda sk: None)
    _ghi = ghi or (lambda b: None)
    tools = run.tools

    def _them(b: Buoc) -> Buoc:
        """Chỗ DUY NHẤT một bước được sinh ra. Hai lối vào thì sớm muộn một lối
        quên gọi `_ghi`, và cái mất là một bước — im lặng."""
        run.buoc.append(b)
        _ghi(b)
        return b

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
        for sk in goi_model(run.lich_su, tools):
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

        run.lich_su = run.lich_su + [_tin_nhan_assistant(loi_goi)]
        cham_tran_trung = False
        for lg in loi_goi:
            run.so_loi_goi_tool += 1
            goi_id = lg.id or f"call_{lg.index}"
            bam = ""
            som = None                  # kết quả biết trước khi chạy, nếu có
            try:
                ds = lg.doi_so()
            except gop_manh.DoiSoHong as e:
                # Đối số hỏng là DỮ LIỆU cho model sửa (`02_HOP_DONG.md` §1).
                ds = {}
                som = thi_hanh.KetQua(False, ma_loi=thi_hanh.LOI_DOI_SO,
                                      thong_diep=str(e))
            else:
                bam = gop_manh.bam_trung(lg.ten, ds)
                n = run._dem_bam.get(bam, 0) + 1
                run._dem_bam[bam] = n
                if n > TRAN_TRUNG:
                    # ⛔ Không chạy lần thứ ba. Nói cho model biết vì sao, để nó
                    #    đổi cách thay vì gọi mãi.
                    som = thi_hanh.KetQua(
                        False, ma_loi="trung",
                        thong_diep=(f"da goi {lg.ten!r} voi cung doi so {n-1} lan. "
                                    f"Hay doi cach tiep can hoac tra loi truc tiep."))
                    cham_tran_trung = True

            # ⭐ GHI BƯỚC TRƯỚC KHI CHẠY NÓ. Hai lý do, và lý do thứ hai mới là
            #    lý do bắt buộc:
            #
            #    1. Một tiến trình chết GIỮA lúc tool chạy vẫn để lại dấu vết
            #       "đã định chạy cái này". Ghi sau thì cái chết là im lặng.
            #    2. Phiếu duyệt gắn vào `step_id` (`UNIQUE`), nên bộ thi hành phải
            #       có id ấy **trước** khi nó quyết định hỏi hay chạy.
            b = _them(Buoc(thu_tu=len(run.buoc) + 1, loai="tool", ten=lg.ten,
                           doi_so=ds, doi_so_tho=lg.doi_so_tho, bam=bam,
                           goi_id=goi_id, ket_qua=None))

            if som is not None:
                kq = som
            else:
                _phat({"type": "tool.requested", "tool_name": lg.ten,
                       "policy_class": chieu_tool.lop_chinh_sach(lg.ten)})
                kq = chay_tool(lg.ten, ds, NgoCanhGoi(
                    thu_tu=b.thu_tu, goi_id=goi_id, bam=bam, step_id=b.step_id))

            if isinstance(kq, CanDuyet):
                # ⭐ Bước được GHI ngay, với `ket_qua` còn `None`. Nếu chờ tới lúc
                #    duyệt xong mới ghi thì một tiến trình chết trong lúc chờ sẽ
                #    làm biến mất cả việc đang hỏi — và người dùng nhận một phiếu
                #    duyệt trỏ tới một bước không tồn tại.
                b.cho_duyet = kq.approval_id
                _ghi(b)
                continue

            if isinstance(kq, ChoJob):
                b.cho_job = kq.job_id
                _ghi(b)
                _phat({"type": "task.queued", "job_id": kq.job_id,
                       "tool_name": lg.ten})
                continue

            b.ket_qua = kq
            _ghi(b)
            _phat({"type": "tool.result" if kq.ok else "tool.failed",
                   "tool_name": lg.ten, "tom_tat": kq.tom_tat()})
            run.lich_su = run.lich_su + [_tin_nhan_tool(lg, kq)]

        # ⛔ DỪNG trước khi đi tiếp nếu còn bước chờ duyệt.
        #
        #    Kiểm SAU cả lô, không phải ngay khi gặp cái đầu tiên: một lượt có hai
        #    lời gọi song song thì cả hai đều phải được hỏi, không phải hỏi cái
        #    này rồi bỏ quên cái kia tới vòng sau.
        if run.dang_treo():
            # ⛔ Một lô có thể vừa chờ người vừa chờ máy. Chọn `AWAITING_APPROVAL`
            #    khi có phiếu: đó là trạng thái cần **người** làm gì đó, và việc
            #    nó hiện ra quan trọng hơn — một job tự xong, một phiếu thì không.
            if run.dang_cho_duyet():
                run.chuyen(AWAITING_APPROVAL)
                for b in run.dang_cho_duyet():
                    _phat({"type": "approval.required", "approval_id": b.cho_duyet,
                           "tool_name": b.ten, "doi_so": b.doi_so})
            else:
                run.chuyen(TOOL_RUNNING)
                run.chuyen(WAITING_BACKGROUND)
            return run

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


def tiep_tuc(run: Run, *, ket_qua_duyet: dict, goi_model, chay_tool,
             tran_vong: int = TRAN_VONG_MODEL, tran_tool: int = TRAN_LOI_GOI_TOOL,
             phat=None, ghi=None, nen_dung=None) -> Run:
    """Chạy tiếp một run đang ở `AWAITING_APPROVAL`.

    `ket_qua_duyet` là `{approval_id: KetQua}` — mỗi bước treo một kết quả, dù
    là kết quả của tool (đã duyệt) hay của lời từ chối (`duyet.ket_qua_cho_model`).

    ⛔ **Từ chối không giết run.** `02_HOP_DONG.md` §1:
       `AWAITING_APPROVAL → TOOL_RESULT_READY`. Lời từ chối đi vào lịch sử như
       một kết quả tool bình thường, và model đọc được để đổi cách.

    🔴 **Thiếu một kết quả thì NÉM, không đoán.** Một bước treo không có
       câu trả lời mà vẫn đi tiếp là một lời gọi tool biến mất khỏi lịch sử —
       model thấy nó đã hỏi mà không ai trả lời, và sẽ hỏi lại.
    """
    if run.trang_thai not in CHO_DUOC:
        raise ChuyenTrangThaiSai(
            f"tiep_tuc chi vao duoc tu {sorted(CHO_DUOC)}, dang o {run.trang_thai}")

    _phat = phat or (lambda sk: None)
    _ghi = ghi or (lambda b: None)
    treo = run.dang_treo()
    thieu = [run.khoa_treo(b) for b in treo if run.khoa_treo(b) not in ket_qua_duyet]
    if thieu:
        raise ValueError(f"thieu ket qua duyet cho: {thieu}")

    for b in treo:
        kq = ket_qua_duyet[run.khoa_treo(b)]

        if isinstance(kq, ChoJob):
            # ⭐ Duyệt xong KHÔNG có nghĩa là xong việc. `image.ltt` và
            #    `speech.ltt` nộp một **job**, nên bước ấy đi thẳng từ "chờ
            #    người" sang "chờ máy" — vẫn treo, chỉ đổi lý do.
            #
            # ⛔ Xoá `cho_duyet` khi đặt `cho_job`: một bước mang cả hai là một
            #    bước mà `khoa_treo()` trả về khoá của phiếu duyệt **đã quyết
            #    rồi**, và vòng sau sẽ đòi lại một câu trả lời đã có.
            b.cho_duyet = ""
            b.cho_job = kq.job_id
            _ghi(b)
            _phat({"type": "task.queued", "job_id": kq.job_id,
                   "tool_name": b.ten})
            continue

        b.ket_qua = kq
        _ghi(b)
        _phat({"type": "tool.result" if kq.ok else "tool.failed",
               "tool_name": b.ten, "tom_tat": kq.tom_tat()})
        run.lich_su = run.lich_su + [
            {"role": "tool", "tool_call_id": b.goi_id or f"call_{b.thu_tu}",
             "content": kq.cho_model()}]

    if run.dang_treo():
        # Còn treo ⇒ chưa đi tiếp được. Từ `AWAITING_APPROVAL` sang chờ job phải
        # đi qua `TOOL_RUNNING` (bảng chuyển đổi không có đường tắt).
        if run.trang_thai == AWAITING_APPROVAL:
            run.chuyen(TOOL_RUNNING)
        if run.trang_thai != WAITING_BACKGROUND:
            run.chuyen(WAITING_BACKGROUND)
        return run

    # Đi ĐÚNG bảng chuyển đổi, không nhảy tắt — và hai lối ra khác nhau:
    #
    #     AWAITING_APPROVAL -> TOOL_RUNNING -> TOOL_RESULT_READY
    #     WAITING_BACKGROUND ------------->  TOOL_RESULT_READY
    #
    # ⛔ `WAITING_BACKGROUND -> TOOL_RUNNING` **không** có trong `CHUYEN_HOP_LE`,
    #    và đó là cố ý: job đã chạy xong rồi, quay lại "đang chạy" là nói sai
    #    về thứ vừa xảy ra.
    if run.trang_thai == AWAITING_APPROVAL:
        run.chuyen(TOOL_RUNNING)
    run.chuyen(TOOL_RESULT_READY)

    if run.so_vong_model >= tran_vong:
        run.chuyen(COMPLETED)
        run.ly_do_ket = KET_TRAN_VONG
        _phat({"type": "run.completed", "ly_do_ket": run.ly_do_ket,
               "so_vong": run.so_vong_model,
               "so_loi_goi_tool": run.so_loi_goi_tool})
        return run

    run.chuyen(MODEL_RESUMING)
    return _vong(run, goi_model=goi_model, chay_tool=chay_tool,
                 tran_vong=tran_vong, tran_tool=tran_tool,
                 phat=phat, ghi=ghi, nen_dung=nen_dung)


__all__ = ["chay", "tiep_tuc", "CanDuyet", "ChoJob", "NgoCanhGoi", "CHO_DUOC",
           "Run", "Buoc", "ChuyenTrangThaiSai",
           "CHUYEN_HOP_LE",
           "TRAN_VONG_MODEL", "TRAN_LOI_GOI_TOOL", "TRAN_TRUNG",
           "CREATED", "MODEL_RUNNING", "TOOL_REQUESTED", "AWAITING_APPROVAL",
           "TOOL_RUNNING", "WAITING_BACKGROUND", "TOOL_RESULT_READY",
           "MODEL_RESUMING", "WAITING_SLOT", "COMPLETED", "FAILED", "CANCELLED",
           "KET_XONG", "KET_TRAN_VONG", "KET_TRAN_TOOL", "KET_TRAN_TRUNG",
           "KET_HUY", "KET_LOI"]
