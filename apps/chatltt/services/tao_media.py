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

from apps.chatltt.services import chinh_sach
from apps.chatltt.services import hoi_thoai as H
from apps.chatltt.services import su_kien as S
from apps.chatltt.tables import ChatlttExecution, ChatlttMessage

log = logging.getLogger("apps.chatltt.tao_media")

#: Khoi artifact theo phuong thuc cua nang luc.
KHOI_THEO_PHUONG_THUC = {"image": "image", "audio": "audio"}


class ThamSoSai(ValueError):
    pass


def bao_gia(ten: str, params: dict, *, db=None, user_id: str = "") -> dict:
    """Bao gia mot luot tao. Nem `ThamSoSai` khi tham so sai — CHUA giu tien."""
    from platform_core.runtime_noi_bo import job as J

    chinh_sach.kiem_cho_phep(ten)
    try:
        bg = J.bao_gia(ten, params, db=db, user_id=user_id)
    except J.ThamSoSai as e:
        raise ThamSoSai(str(e)) from None
    return {"nang_luc": ten, "credit": bg.credit, "phien_ban_gia": bg.phien_ban_gia,
            "tham_so": bg.tham_so_sach}


def tao(db, *, user_id: str, conv_id: str, ten: str, params: dict,
        credit_da_bao: Optional[int] = None,
        parent_id=None) -> dict:
    """Nop mot job tao anh/tieng gan vao hoi thoai. COMMIT truoc khi tra ve.

    `credit_da_bao` la so nguoi dung DA NHIN THAY. Lech voi gia tinh lai ⇒ tu
    choi: nguoi dung phai duoc bao lai, khong bi tru mot so khac voi so ho dong y.
    """
    from platform_core.runtime_noi_bo import job as J

    chinh_sach.kiem_cho_phep(ten)
    hoi = H.lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    try:
        bg = J.bao_gia(ten, params, db=db, user_id=user_id)
    except J.ThamSoSai as e:
        raise ThamSoSai(str(e)) from None
    if credit_da_bao is not None and int(credit_da_bao) != bg.credit:
        raise ThamSoSai(
            f"gia da doi: bao {credit_da_bao}, tinh lai {bg.credit}")

    cha = hoi.current_leaf_id if parent_id is None else parent_id
    tra_loi = H.them_thong_diep(db, user_id=user_id, conv_id=conv_id,
                                role="assistant", blocks=[], parent_id=cha,
                                status="queued")
    ex = S.mo_execution(db, message=tra_loi, tool_name=ten, mode="job")
    ex.credit_giu = bg.credit
    job = J.nop_job(db, user_id=user_id, bao_gia=bg, correlation_id=ex.id,
                    idempotency_key=f"chatltt:{ex.id}")
    ex.job_id = job.id
    db.commit()
    return {"conversation_id": hoi.id, "message_id": tra_loi.id,
            "execution_id": ex.id, "job_id": job.id, "credit": bg.credit}


def _khoi_artifact(ten: str, result: dict) -> list:
    """Ket qua job -> khoi noi dung. Khong doan: chi doc dung cong ra da khai."""
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
        khoi = _khoi_artifact(ex.tool_name, result)
        S.ap_dung(ex, {"type": "execution.completed"}, message=tin)
        thu = int(result.get("credit_cost") or 0)
        S.ap_dung(ex, {"type": "billing.updated", "credit_giu": ex.credit_giu,
                       "credit_thu": thu,
                       "credit_hoan": max(0, ex.credit_giu - thu)}, message=tin)
        if tin is not None:
            tin.blocks = khoi or [{"type": "status", "code": "khong_co_ket_qua"}]
        db.commit()
    elif tt in ("error", "cancelled"):
        ma = "huy" if tt == "cancelled" else "that_bai"
        S.ap_dung(ex, {"type": "execution.failed", "code": ma,
                       "ly_do": str(getattr(job, "error", "") or "")[:500]},
                  message=tin)
        S.ap_dung(ex, {"type": "billing.updated", "credit_giu": ex.credit_giu,
                       "credit_thu": 0, "credit_hoan": ex.credit_giu},
                  message=tin)
        if tin is not None:
            tin.blocks = [{"type": "error", "code": ma,
                           "text": str(getattr(job, "error", "") or "")[:500]}]
        db.commit()
    else:
        moi = int(getattr(job, "progress", 0) or 0)
        cu = int((ex.usage or {}).get("progress") or 0)
        if moi != cu:
            S.ap_dung(ex, {"type": "execution.progress", "progress": moi},
                      message=tin)
            db.commit()
    return S.snapshot(ex)


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
