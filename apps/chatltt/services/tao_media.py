"""
tao_media.py — tao ANH va TIENG ngay trong hoi thoai. (H43 Phase 09)

    bao_gia()   tinh gia MOT lan tao, chua giu tien, chua tao gi
    tao()       tao message assistant giu cho + execution + nop job (giu tien)
    dong_bo()   doc trang thai job -> ap su kien -> khi xong thi gan khoi artifact

## Vi sao NGUOI DUNG phai bam, khong phai model tu quyet

MVP khong chay planner tu dong (`AUTONOMOUS_OPERATING_CONTRACT`, muc "Deferred").
Mot luot anh la 3-12 credit va mot luot tieng tinh theo giay — de model tu quyet
la de no tieu tien cua khach ma khach chua dong y. Nen: **bao gia -> nguoi dung
xac nhan -> nop**.

## Vi sao KHONG dung nut Dung o day

Anh va tieng di qua hang doi job (`ASYNC_JOB`), va huy mot job dang chay tren GPU
may B khong phai thao tac nen tang ho tro dong deu. Nguoi dung doi hoac bo di;
tien quyet toan theo san pham THAT (anh that su sinh ra, giay tieng that su co).

⛔ Tep nay khong biet ten app nao so huu `image.ltt`/`speech.ltt`, khong biet gia,
   khong biet may B o dau. Tat ca qua `platform_core.runtime_noi_bo.job`.
"""
from __future__ import annotations

import logging
from typing import Optional

_log = logging.getLogger("ltt.chatltt.media")

from apps.chatltt.services import chinh_sach
from apps.chatltt.services import hoi_thoai as H
from apps.chatltt.services import su_kien as S
from apps.chatltt.tables import ChatlttExecution, ChatlttMessage
from apps.chatltt.services import loi_ra_ngoai as LRN

log = logging.getLogger("apps.chatltt.tao_media")

#: Khoi artifact theo phuong thuc cua nang luc.
KHOI_THEO_PHUONG_THUC = {"image": "image", "audio": "audio"}


class ThamSoSai(ValueError):
    """`ma`: ma nghiep vu cua app (vd `voice_language_mismatch`), rong neu khong co."""

    def __init__(self, thong_diep: str = "", ma: str = ""):
        super().__init__(thong_diep)
        self.ma = str(ma or "")


def bao_gia(ten: str, params: dict, *, db=None, user_id: str = "",
            conv_id: str = "") -> dict:
    """Bao gia mot luot tao. Nem `ThamSoSai` khi tham so sai — CHUA giu tien.

    🔴 VOI TIENG: neu khach khong chi dinh giong nao, MODEL TU CHON mot giong
       trong kho chung cho hop noi dung — va viec do xay ra **o day**, ngay
       truoc khi bao gia, chu khong phai luc nop.

    ⭐ Vi sao o day: khach phai **nhin thay giong** truoc khi dong y tra tien.
       Chon sau khi dong y nghia la ho tra cho mot thu chua duoc xem.

    ⛔ Va phu phi phai duoc NOI RA. Mot lan hoi model ton **1 credit** (gia lam
       tron len — do 04/09), nen bao gia tra ve ca `giong` kem `ton_credit` de
       giao dien noi that: "1 credit doc + 1 credit chon giong". Mot phu phi im
       lang la mot loi tinh tien, du so tien nho.
    """
    from platform_core.runtime_noi_bo import job as J

    chinh_sach.kiem_cho_phep(ten)
    giong = None
    if ten == chinh_sach.NANG_LUC_TIENG and db is not None:
        giong = _giong_cho_luot(db, user_id=user_id, conv_id=conv_id,
                                params=params)
        if giong:
            params = dict(params, preset=giong["preset"])
    try:
        bg = J.bao_gia(ten, params, db=db, user_id=user_id)
    except J.ThamSoSai as e:
        raise ThamSoSai(str(e), ma=e.ma) from None
    ra = {"nang_luc": ten, "credit": bg.credit, "phien_ban_gia": bg.phien_ban_gia,
          "tham_so": bg.tham_so_sach}
    if giong:
        ra["giong"] = giong
    return ra


def _giong_cho_luot(db, *, user_id: str, conv_id: str, params: dict):
    """Giong cho mot luot tieng, khi khach chua tu chon. `None` neu ho da chon.

    ⛔ KHACH CHON THI KHONG DUOC DE MODEL DE LEN. `voice_id` (giong nhan ban)
       hay `preset` khach tu dat deu la mot lua chon co y — thay no bang mot lua
       chon cua may la lay mat quyen quyet dinh cua nguoi tra tien.
    """
    from apps.chatltt.services import chon_giong

    if params.get("voice_id") or params.get("preset"):
        return None
    if not conv_id:
        return None
    return chon_giong.chon(db, user_id=user_id, conv_id=conv_id,
                           text=str(params.get("text") or ""))


def tao(db, *, user_id: str, conv_id: str, ten: str, params: dict,
        credit_da_bao: Optional[int] = None,
        parent_id=None, tin_nhan=None,
        run_id: str = "", step_id: str = "") -> dict:
    """Nop mot job tao anh/tieng gan vao hoi thoai. COMMIT truoc khi tra ve.

    `credit_da_bao` la so nguoi dung DA NHIN THAY. Lech voi gia tinh lai ⇒ tu
    choi: nguoi dung phai duoc bao lai, khong bi tru mot so khac voi so ho dong y.

    ## `tin_nhan` — hai duong vao, mot ban logic (H44 P05)

    Duong NUT BAM (V1): khong truyen `tin_nhan` ⇒ ham tu tao mot tin nhan
    assistant moi. Do la dung: nguoi dung bam "tao anh" thi ket qua la mot luot
    rieng trong cay hoi thoai.

    Duong MODEL TU GOI (V3): truyen `tin_nhan` cua run dang chay ⇒ job gan vao
    ĐUNG tin nhan ay. Khong co tham so nay thi mot lan model goi `image.ltt`
    sinh ra mot tin nhan thu hai — va cau tra loi cua no roi vao mot cho khac
    voi cho no dang noi.

    ⛔ Va lua chon thay the — goi thang `J.nop_job` tu V3 — la chep lai bao gia,
       kiem tham so, va ghi `giong` da dung. Ba ban chep se lech, va chung lech
       o cho tinh tien.
    """
    from platform_core.runtime_noi_bo import job as J

    chinh_sach.kiem_cho_phep(ten)
    hoi = H.lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    try:
        bg = J.bao_gia(ten, params, db=db, user_id=user_id)
    except J.ThamSoSai as e:
        raise ThamSoSai(str(e), ma=e.ma) from None
    if credit_da_bao is not None and int(credit_da_bao) != bg.credit:
        raise ThamSoSai(
            f"gia da doi: bao {credit_da_bao}, tinh lai {bg.credit}")

    if tin_nhan is None:
        cha = hoi.current_leaf_id if parent_id is None else parent_id
        tra_loi = H.them_thong_diep(db, user_id=user_id, conv_id=conv_id,
                                    role="assistant", blocks=[], parent_id=cha,
                                    status="queued")
    else:
        tra_loi = tin_nhan
    ex = S.mo_execution(db, message=tra_loi, tool_name=ten, mode="job")
    ex.credit_giu = bg.credit
    # Noi but toan nay voi buoc sinh ra no. Ca hai deu `nullable` nen duong V1
    # (nut bam) van hop le voi ca hai NULL.
    if run_id:
        ex.run_id = str(run_id)
    if step_id:
        ex.step_id = str(step_id)
    # ⭐ GHI LAI GIONG DA DUNG. Day la thu `chon_giong.giong_da_dung()` doc o
    #    luot sau de KHONG phai hoi model lai — mot lan hoi ton 1 credit, va mot
    #    hoi thoai doi giong giua chung cung nghe nhu doi nguoi doc.
    #
    # ⛔ Doc tu `bg.tham_so_sach` chu khong tu `params`: day la tham so DA QUA
    #    cua kiem cua nen tang. Ghi lai thu khach gui ma chua qua cua la ghi mot
    #    gia tri co the chua bao gio duoc dung.
    _preset = (bg.tham_so_sach or {}).get("preset") if ten == chinh_sach.NANG_LUC_TIENG else None
    if _preset:
        ex.usage = dict(ex.usage or {}, giong={"preset": str(_preset)})
    job = J.nop_job(db, user_id=user_id, bao_gia=bg, correlation_id=ex.id,
                    idempotency_key=f"chatltt:{ex.id}")
    ex.job_id = job.id
    db.commit()
    return {"conversation_id": hoi.id, "message_id": tra_loi.id,
            "execution_id": ex.id, "job_id": job.id, "credit": bg.credit}


def _dat_khoi(tin, khoi: list, *, noi_them: bool) -> None:
    """Đặt kết quả job vào `blocks`. **NỐI THÊM** khi job thuộc một run V3.

    🔴 Đường V1 (nút bấm) tạo một tin nhắn RIÊNG cho mỗi lần tạo, nên thay
    toàn bộ `blocks` là đúng — tin nhắn ấy không có gì khác.

    ⛔ Đường V3 thì không: tin nhắn đó đang mang khối `tool_call` của cả lượt
       và phần chữ model đã nói. Thay toàn bộ là **xoá sạch** chúng, và người
       dùng thấy một bức ảnh xuất hiện thay chỗ câu trả lời vừa đọc.
    """
    if not noi_them:
        tin.blocks = list(khoi)
        return
    cu = list(tin.blocks or [])
    # Ảnh/tiếng đứng TRƯỚC phần chữ cuối: model sẽ nói về chúng ở vòng sau,
    # nên câu ấy phải nằm dưới thứ nó nói tới.
    i = next((n for n, k in enumerate(cu) if k.get("type") == "text"), len(cu))
    cu[i:i] = [k for k in khoi if k not in cu]
    tin.blocks = cu


def _danh_thuc_run(db, ex) -> None:
    """Job của một run V3 vừa xong ⇒ chạy tiếp lượt đó.

    ## ⚠️ Giới hạn đã biết: đây là đường **KÉO**, không phải đường ĐẨY

    `dong_bo` chạy khi **client hỏi** (`/api/luot/{id}/trang-thai`, nhịp 2 giây).
    Không ai hỏi thì run không tự chạy tiếp — nó nằm im ở `WAITING_BACKGROUND`
    cho tới lần ai đó mở lại hội thoại.

    ⭐ Chấp nhận được cho bản đầu, và **không mất dữ liệu**: job đã xong, tiền
       đã quyết toán, kết quả đã nằm trong `blocks`. Thứ chưa xảy ra chỉ là vòng
       model **nói về** bức ảnh đó.

    ⛔ Đường ĐẨY thật phải là một chỗ móc trong `job_runner` — `platform_core`,
       ngoài ranh giới của app này. Ghi lại ở `05_E2_*.md` để không ai tưởng
       thiếu sót này đã được giải quyết.
    """
    if not getattr(ex, "run_id", None):
        return
    try:
        from apps.chatltt.services import luot_v3
        if luot_v3.nen_chay_tiep(db, user_id=ex.user_id, run_id=ex.run_id):
            luot_v3.chay_tiep_nen(ex.run_id, user_id=ex.user_id)
    except Exception:                                           # noqa: BLE001
        # Job ĐÃ xong và tiền ĐÃ quyết toán. Không đánh thức được run là một
        # sự cố, nhưng biến nó thành lỗi của `dong_bo` là làm hỏng cả việc
        # **đọc tiến độ** — thứ duy nhất đang hoạt động.
        _log.exception("khong danh thuc duoc run %s", str(ex.run_id)[-8:])


def khoi_artifact(ten: str, result: dict) -> list:
    """Ket qua job -> khoi noi dung. Khong doan: chi doc dung cong ra da khai.

    ⭐ CÔNG KHAI vì `bo_chay_tool.ket_qua_job` cần **cùng một câu trả lời**:
       thiết bị hiển thị và model phải nhìn thấy đúng một tập artifact. Hai
       phiên bản của câu hỏi *"job này đẻ ra những gì"* là hai phiên bản sẽ
       lệch — và chỗ chúng lệch là chỗ người dùng thấy một bức ảnh trong khi
       model nói rằng nó không tạo được gì.
    """
    from platform_core.runtime_noi_bo.tim import tim_tool

    _m, tool = tim_tool(ten)
    khoi = []
    for cong, kieu in (tool.returns or {}).items():
        goc = str(kieu).rstrip("[]")
        loai = KHOI_THEO_PHUONG_THUC.get(goc)
        if not loai:
            continue
        gt = result.get(cong)
        khoa = gt if isinstance(gt, list) else ([gt] if gt else [])
        for k in khoa:
            if k:
                khoi.append({"type": loai, "key": str(k)})
    return khoi


def dong_bo(db, *, user_id: str, execution_id: str) -> dict:
    """Doc trang thai job va cap nhat execution/message. An toan goi nhieu lan.

    ⭐ Day la cho `su_that()` lay tien do cho mot job: khong co "day" tu worker
       sang web, nen client hoi theo nhip (Q87: 2 s, backoff khi loi).
    """
    from platform_core import job_history

    ex = db.get(ChatlttExecution, str(execution_id))
    if ex is None or ex.user_id != str(user_id):
        raise H.KhongTimThay("khong co luot nay")
    if ex.mode != "job" or not ex.job_id:
        return S.snapshot(ex)
    if ex.status in ("done", "failed", "cancelled"):
        return S.snapshot(ex)

    job = job_history.get_owned(db, user_id, ex.job_id)
    if job is None:
        return S.snapshot(ex)
    tin = db.get(ChatlttMessage, ex.message_id)
    tt = str(getattr(job, "status", ""))

    if tt == "done":
        result = dict(getattr(job, "result", None) or {})
        khoi = khoi_artifact(ex.tool_name, result)
        S.ap_dung(ex, {"type": "execution.completed"}, message=tin)
        thu = int(result.get("credit_cost") or 0)
        S.ap_dung(ex, {"type": "billing.updated", "credit_giu": ex.credit_giu,
                       "credit_thu": thu,
                       "credit_hoan": max(0, ex.credit_giu - thu)}, message=tin)
        if tin is not None:
            _dat_khoi(tin, khoi or [{"type": "status", "code": "khong_co_ket_qua"}],
                      noi_them=bool(ex.run_id))
        db.commit()
        _danh_thuc_run(db, ex)
    elif tt in ("error", "cancelled"):
        ma = "huy" if tt == "cancelled" else "that_bai"
        S.ap_dung(ex, {"type": "execution.failed", "code": ma,
                       # 🔴 `job.error` la chuoi TU DO do handler viet, va
                       #    handler co the da boc `str()` cua mot loi
                       #    thuong nguon vao do. Khong dua no ra khach.
                       "ly_do": LRN.cau("loi_noi_bo")},
                  message=tin)
        S.ap_dung(ex, {"type": "billing.updated", "credit_giu": ex.credit_giu,
                       "credit_thu": 0, "credit_hoan": ex.credit_giu},
                  message=tin)
        if tin is not None:
            _dat_khoi(tin, [{"type": "error", "code": ma,
                             "text": str(getattr(job, "error", "") or "")[:500]}],
                      noi_them=bool(ex.run_id))
        db.commit()
        _danh_thuc_run(db, ex)
    else:
        moi = int(getattr(job, "progress", 0) or 0)
        cu = int((ex.usage or {}).get("progress") or 0)
        cho_moi = _cho_tai_nguyen(job)
        cho_cu = (ex.usage or {}).get("cho_tai_nguyen")
        if moi != cu:
            S.ap_dung(ex, {"type": "execution.progress", "progress": moi},
                      message=tin)
        if cho_moi != cho_cu:
            # 🔴 LY DO CHO DA DUOC BIET CHINH XAC, VA NO DUNG LAI O LOG.
            #
            #    Đo 04/09 trên production: job ảnh nằm `queued` nhiều phút.
            #    Log worker nói rõ từng vòng — `DangBan: "Máy tạo ảnh đang bận.
            #    Bạn có thể thử lại sau, hoặc chọn model đắm máy."` — một câu
            #    tiếng Việt **viết sẵn cho người dùng**, kèm cả gợi ý.
            #
            #    Phía khách chỉ thấy một khối media nằm im. Không biết đang chờ
            #    gì, chờ bao lâu, hay có phải mình làm sai gì không.
            #
            # ⛔ `defer_resource` KHÔNG chạm sổ tiền và KHÔNG tiêu lượt thử —
            #    nên đây là một lần chờ hoàn toàn lành. Che nó đi không bảo vệ
            #    ai; nó chỉ biến một lần chờ có lý do thành một lần treo vô cớ.
            u = dict(ex.usage or {})
            if cho_moi is None:
                u.pop("cho_tai_nguyen", None)
            else:
                u["cho_tai_nguyen"] = cho_moi
            ex.usage = u
        if moi != cu or cho_moi != cho_cu:
            db.commit()
    return S.snapshot(ex)


def _cho_tai_nguyen(job) -> Optional[int]:
    """Job có đang chờ một máy bận không, và còn bao nhiêu giây.

    Trả `None` khi không phải trạng thái đó. Trả **số giây còn lại** (>= 0) khi
    `defer_resource` đã hẹn lại — con số ấy là thật, không phải phỏng đoán:
    `job.next_run_at` do chính nền tảng đặt.

    ⚠️ Trả `0` chứ không `None` khi đã tới hẹn: "sắp thử lại" vẫn là chờ tài
       nguyên, và một `None` ở đó sẽ làm dòng trạng thái nhấp nháy tắt/bật giữa
       hai nhịp hỏi.
    """
    from platform_core.jobs import PROVIDER_REJECTED

    if str(getattr(job, "status", "")) != "queued":
        return None
    if str(getattr(job, "provider_state", "")) != PROVIDER_REJECTED:
        return None
    khi = getattr(job, "next_run_at", None)
    if khi is None:
        return 0
    try:
        con = (khi - _now_utc()).total_seconds()
    except (TypeError, ValueError):
        return 0
    return max(0, int(con))


def _now_utc():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def kiem_so_huu_khoa(khoa: str, user_id: str) -> bool:
    """Khoa kho nay co phai cua nguoi nay khong — kiem theo HINH DANG khoa.

    Cung loi `apps/thumbnail/routes.py` va `apps/ltt_voice/routes/_p_audio.py`:
    khong tra CSDL, vi khoa da mang chu so huu trong duong dan cua no. Hai hinh:

        anhnoibo/<uid>/<job_id>/<i>.png
        voice/out/<uid>/<job_id>/tieng.wav

    ⛔ Fail-closed: hinh la ⇒ False. Them mot nang luc moi thi them mot hinh o
       day, khong noi long phep kiem.

    🔴 KIEM TUNG DOAN TRUOC KHI KIEM HINH. Chi so khop tien to thi
       `anhnoibo/<uid>/../../secrets/app.env` **DUOC PHEP** — hai doan dau dung
       het, phan thoat nam o sau. Loi nay do chinh `test_625` bat ra o luot chay
       dau tien.

    ⚠️ `platform_core/storage.py::_safe_key` cung chan `..`, nhung dua vao no la
       dua an toan cua cua nay vao mot tang khac: doi ngay ai do doi kho (R2,
       CDN) thi lop do co the khong con o giua nua.
    """
    khoa = str(khoa or "")
    if "\\" in khoa:
        return False
    doan = khoa.split("/")
    if any(d in ("", ".", "..") for d in doan):
        return False
    uid = str(user_id)
    if len(doan) >= 4 and doan[0] == "anhnoibo" and doan[1] == uid:
        return True
    if len(doan) >= 4 and doan[0] == "voice" and doan[1] == "out" and doan[2] == uid:
        return True
    # Hinh thu ba (Phase 13): anh nguoi dung GUI VAO cho model vision. Luat o
    # `anh_vao.la_khoa_anh_vao` — mot cho, khong chep lai vi tay.
    from apps.chatltt.services import anh_vao
    if anh_vao.la_khoa_anh_vao(khoa, uid):
        return True
    return False
