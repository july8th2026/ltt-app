"""
luot.py — điều phối MỘT lượt text của ChatLTT: dựng ngữ cảnh → gọi facade → ghi sự kiện. (H43 Phase 08)

    bat_dau()   HTTP request: tạo message user (trừ khi tạo lại) + assistant giữ chỗ
                + execution, COMMIT, trả id. Nhanh, không chạm model.
    chay()      luồng nền (thread trong tiến trình web): mở phiên CSDL riêng, gọi
                `runtime_noi_bo.luong.mo_luong`, áp sự kiện, ghi partial theo nhịp,
                phát cho người xem qua `dang_chay`, tôn trọng Dừng.

## Vì sao tách bat_dau/chay và vì sao thread

Sự kiện đầu (`response.started`) phải tới trình duyệt trong vài giây, nhưng máy
B có thể mất tới 75 s để mở luồng (nạp model). Request HTTP không được giữ
generator đồng bộ của facade — nó chặn. Nên lượt chạy ở thread; route SSE chỉ
**xem** qua hàng đợi và gửi `: ping` khi chưa có gì (D7). Đóng tab không giết
lượt: chữ vẫn về CSDL (AC-09); Dừng là một hành động tường minh.

⛔ Tệp này không biết URL máy, id model nội bộ, giá. Nó chỉ biết `tool_name`
   ("text.chat"), alias, và hình dạng sự kiện.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from sqlalchemy import select

from apps.chatltt.services import chinh_sach, dang_chay
from apps.chatltt.services import hoi_thoai as H
from apps.chatltt.services import su_kien as S
from apps.chatltt.tables import ChatlttExecution, ChatlttMessage

log = logging.getLogger("apps.chatltt.luot")

#: Trần ký tự một lượt gửi của người dùng — trần SẢN PHẨM (ngữ cảnh do executor
#: kẹp bằng token; đây chỉ chặn dán nhầm cả một tệp). 200K ký tự ≈ 80K token.
TRAN_KY_TU_LUOT = 200_000


class ThamSoSai(ValueError):
    pass


class _MacDinh:
    """Sentinel: "bên gọi KHÔNG khai cha" — khác hẳn "cha là gốc" (`None`).

    🔴 Hai ý nghĩa, một giá trị `null` trong JSON. Không tách ra thì **không
       gửi lại được một lượt ở gốc**: `parent_id: null` bị hiểu thành "dùng lá
       đang xem", nên bản sửa của lượt đầu tiên nối vào cuối hội thoại thay vì
       thành anh em của nó — cây sai một cách im lặng, và chỉ lộ ra khi ai đó
       bấm chuyển nhánh.
    """

    def __repr__(self) -> str:                                  # pragma: no cover
        return "<mac dinh>"


MAC_DINH = _MacDinh()


def dung_ngu_canh(duong: list) -> list:
    """Đường gốc→cha của assistant → `messages` OpenAI. Chỉ khối `text`; khối
    reasoning/status/error/artifact không đi vào ngữ cảnh."""
    ra = []
    for m in duong:
        if m.role not in ("user", "assistant", "system"):
            continue
        chu = "\n\n".join(str(k.get("text") or "") for k in (m.blocks or [])
                          if k.get("type") == "text")
        if not chu.strip():
            continue
        ra.append({"role": m.role, "content": chu})
    return ra


def bat_dau(db, *, user_id: str, conv_id: str, van_ban: str = "",
            model_alias: str = "", parent_id=MAC_DINH,
            tao_lai_cua: Optional[str] = None, reasoning_effort: str = "") -> dict:
    """Ghi user message + assistant giữ chỗ + execution rồi COMMIT. Không chạm model.

    · gửi mới:      không khai `parent_id` ⇒ nối vào **lá đang xem**
    · sửa-gửi-lại:  `parent_id` = cha của message cũ (`None` = gốc) ⇒ **anh em mới**
    · tạo lại:      `tao_lai_cua` = id assistant cũ ⇒ assistant anh em mới dưới cùng user
    """
    hoi = H.lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    alias = str(model_alias or hoi.model_alias or "")
    if not alias:
        raise ThamSoSai("chua chon model")
    if tao_lai_cua:
        cu = H.lay_thong_diep(db, user_id=user_id, conv_id=conv_id, msg_id=tao_lai_cua)
        if cu.role != "assistant" or not cu.parent_id:
            raise ThamSoSai("chi tao lai duoc mot cau tra loi")
        user_msg = H.lay_thong_diep(db, user_id=user_id, conv_id=conv_id, msg_id=cu.parent_id)
    else:
        chu = str(van_ban or "")
        if not chu.strip():
            raise ThamSoSai("noi dung trong")
        if len(chu) > TRAN_KY_TU_LUOT:
            raise ThamSoSai(f"noi dung qua dai (> {TRAN_KY_TU_LUOT} ky tu)")
        cha = hoi.current_leaf_id if parent_id is MAC_DINH else parent_id
        user_msg = H.them_thong_diep(db, user_id=user_id, conv_id=conv_id, role="user",
                                     blocks=[{"type": "text", "text": chu}], parent_id=cha)
    tra_loi = H.them_thong_diep(db, user_id=user_id, conv_id=conv_id, role="assistant",
                                blocks=[], parent_id=user_msg.id, status="streaming",
                                model_alias=alias)
    ex = S.mo_execution(db, message=tra_loi, tool_name=chinh_sach.NANG_LUC_TEXT, mode="stream")
    if reasoning_effort:
        ex.usage = {"reasoning_effort": str(reasoning_effort)}
    if not hoi.title:
        hoi.title = _tieu_de_tu(user_msg)
    hoi.model_alias = alias
    db.commit()
    return {"conversation_id": hoi.id, "user_message_id": user_msg.id,
            "assistant_message_id": tra_loi.id, "execution_id": ex.id}


def _tieu_de_tu(user_msg: ChatlttMessage) -> str:
    chu = " ".join(str(k.get("text") or "") for k in (user_msg.blocks or [])
                   if k.get("type") == "text").strip()
    return (chu[:60] + ("…" if len(chu) > 60 else "")) if chu else ""


def _da_huy_trong_csdl(db, execution_id: str) -> bool:
    """Dừng từ tiến trình khác ghi `status='cancelled'`; đọc bằng SELECT vô hướng,
    KHÔNG `refresh()` — refresh sẽ đè `partial_text` đang giữ trong bộ nhớ."""
    tt = db.execute(select(ChatlttExecution.status)
                    .where(ChatlttExecution.id == execution_id)).scalar()
    return tt == "cancelled"


def chay(execution_id: str, *, user_id: str) -> None:
    """Thân luồng nền. Mọi kết cục đều để lại execution ở trạng thái kết thúc."""
    from platform_core.db import get_session
    from platform_core.runtime_noi_bo import luong as L

    so = dang_chay.bat_dau(execution_id, user_id)
    gen = get_session()
    db = next(gen)
    ex: Optional[ChatlttExecution] = None
    tra_loi: Optional[ChatlttMessage] = None
    try:
        ex = db.get(ChatlttExecution, execution_id)
        if ex is None or ex.user_id != str(user_id):
            return
        tra_loi = db.get(ChatlttMessage, ex.message_id)
        duong = H.duong_toi_la(db, user_id=user_id, conv_id=ex.conversation_id,
                               leaf_id=tra_loi.parent_id)
        params = {"model": tra_loi.model_alias, "messages": dung_ngu_canh(duong)}
        re_ = (ex.usage or {}).get("reasoning_effort")
        if re_:
            params["reasoning_effort"] = re_

        ghi_nhan: dict = {}
        it = L.mo_luong(db, user_id=user_id, tool_name=ex.tool_name, params=params,
                        correlation_id=ex.id, holder_id=ex.id, ghi_nhan=ghi_nhan)
        luc_ghi = time.monotonic()
        ky_tu = 0
        try:
            for sk in it:
                ket = S.ap_dung(ex, sk, message=tra_loi)
                if sk.get("type") == "response.delta":
                    ky_tu += len(sk.get("text") or "")
                so.phat(sk)
                bay_gio = time.monotonic()
                if S.nen_ghi(luc_ghi_cuoi=luc_ghi, bay_gio=bay_gio, ky_tu_moi=ky_tu,
                             ket_thuc=ket):
                    if ket:
                        S.dong_bo_khoi_text(tra_loi, ex)
                    db.commit()
                    luc_ghi, ky_tu = bay_gio, 0
                    if not ket and (so.dung.is_set() or _da_huy_trong_csdl(db, ex.id)):
                        it.close()
                        _huy(db, ex, tra_loi, so, ghi_nhan)
                        break
                elif so.dung.is_set():
                    it.close()
                    _huy(db, ex, tra_loi, so, ghi_nhan)
                    break
        except L.LoiCuaLuong as e:
            # Lỗi TRƯỚC byte đầu: chưa giữ tiền (trừ DangBan/ThieuCredit đã dọn).
            sk = {"type": "response.failed", "code": _ma_loi(e), "ly_do": str(e)}
            if isinstance(e, L.DangBan):
                sk["retry_after_s"] = e.thu_lai_sau_s
            S.ap_dung(ex, sk, message=tra_loi)
            S.dong_bo_khoi_text(tra_loi, ex)
            so.phat(sk)
        if ex.status in ("streaming", "queued"):
            # Luồng cạn mà không có sự kiện kết thúc — không được để "đang chảy" mãi.
            sk = {"type": "response.failed", "code": "luong_cat", "ly_do": "luong ket thuc som"}
            S.ap_dung(ex, sk, message=tra_loi)
            S.dong_bo_khoi_text(tra_loi, ex)
            so.phat(sk)
        db.commit()
    except Exception as e:                                      # noqa: BLE001
        log.exception("luot %s vo", execution_id[-8:])
        try:
            db.rollback()
            if ex is not None:
                ex = db.get(ChatlttExecution, execution_id)
                tra_loi = db.get(ChatlttMessage, ex.message_id) if ex else None
            if ex is not None and ex.status in ("streaming", "queued"):
                sk = {"type": "response.failed", "code": "loi_noi_bo", "ly_do": type(e).__name__}
                S.ap_dung(ex, sk, message=tra_loi)
                if tra_loi is not None:
                    S.dong_bo_khoi_text(tra_loi, ex)
                db.commit()
                so.phat(sk)
        except Exception:                                       # noqa: BLE001
            log.exception("khong ghi duoc trang thai loi cho luot %s", execution_id[-8:])
    finally:
        dang_chay.ket_thuc(execution_id)
        try:
            next(gen)
        except StopIteration:
            pass


def _huy(db, ex, tra_loi, so, ghi_nhan: dict) -> None:
    sk = {"type": "response.cancelled"}
    S.ap_dung(ex, sk, message=tra_loi)
    so.phat(sk)
    if ghi_nhan.get("usage"):
        u = dict(ghi_nhan["usage"], type="usage.updated")
        S.ap_dung(ex, u, message=tra_loi)
        so.phat(u)
    if ghi_nhan.get("billing"):
        S.ap_dung(ex, ghi_nhan["billing"], message=tra_loi)
        so.phat(ghi_nhan["billing"])
    S.dong_bo_khoi_text(tra_loi, ex)
    db.commit()


def _ma_loi(e) -> str:
    from platform_core.runtime_noi_bo import luong as L
    if isinstance(e, L.DangBan):
        return "ban"
    if isinstance(e, L.ThieuCredit):
        return "het_credit"
    if isinstance(e, L.KhongMoDuoc):
        return "qua_dai" if e.qua_dai else "khong_mo_duoc"
    if isinstance(e, L.KhongCoNangLuc):
        return "khong_co_nang_luc"
    return "tham_so"


def khoi_chay_nen(execution_id: str, *, user_id: str) -> threading.Thread:
    t = threading.Thread(target=chay, args=(execution_id,), kwargs={"user_id": user_id},
                         name=f"chatltt-{execution_id[-8:]}", daemon=True)
    t.start()
    return t


def dung(db, *, user_id: str, execution_id: str) -> dict:
    """Nút Dừng: ghi `cancelled` xuống CSDL (chắc) + cờ trong tiến trình (nhanh)."""
    ex = db.get(ChatlttExecution, str(execution_id))
    if ex is None or ex.user_id != str(user_id):
        raise H.KhongTimThay("khong co luot nay")
    if ex.status in ("streaming", "queued"):
        ex.status = "cancelled"
        db.commit()
    trong_tien_trinh = dang_chay.yeu_cau_dung(ex.id)
    return {"execution_id": ex.id, "status": ex.status, "trong_tien_trinh": trong_tien_trinh}
