"""
hoi_thoai.py — cây hội thoại của ChatLTT: nghiệp vụ thuần, không HTTP. (H43 Phase 07)

Mọi hàm đọc/ghi đều nhận `user_id` và **chỉ** chạm hội thoại của người đó. Không
có hàm nào tra theo `id` trần — IDOR bị chặn ở đây, route không có cách "quên".

Cây: `ChatlttMessage.parent_id` (NULL = gốc). Anh em = cùng cha. Nhánh đang xem
= `ChatlttConversation.current_leaf_id` (lưu CSDL, không lưu trình duyệt).

Hành vi kế thừa từ LibreChat (báo cáo Phase 01 §1–§2), viết lại:
  · sửa message user rồi gửi lại = **anh em mới cùng cha**, KHÔNG xoá con
  · tạo lại = **assistant anh em mới** dưới cùng message user
  · `dung_cay(phang)` = `buildTree` một lượt; cha vắng ⇒ nút lên gốc (đúng
    hành vi của họ, nhưng ChatLTT ép `created_at(con) > created_at(cha)` lúc GHI
    nên không cần vá muộn như `fork.js:46-56`)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy import or_, select

from apps.chatltt.tables import (LOAI_KHOI, TRANG_THAI, VAI, ChatlttConversation,
                                 ChatlttExecution, ChatlttMessage, sinh_id)


log = logging.getLogger("apps.chatltt.hoi_thoai")


class KhongTimThay(LookupError):
    """Hội thoại/message không tồn tại **hoặc không phải của bạn** — cùng một câu."""


class ThamSoSai(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _co_mui_gio(luc: datetime) -> datetime:
    """Ép một mốc thời gian về UTC **có múi giờ**.

    🔴 VÌ SAO CẦN. SQLite không lưu múi giờ: một hàng vừa ghi bằng
       `datetime.now(timezone.utc)` đọc lại ở request sau là **naive**, và
       `naive <= aware` ném `TypeError`. Trên PostgreSQL (`DateTime(timezone=True)`)
       thì luôn aware, nên lỗi này **chỉ hiện ở SQLite** — tức chỉ hiện trong
       test và trên máy phát triển, đúng loại lỗi dễ lọt xuống production nhất.

    ⛔ Coi mốc không múi giờ là UTC chứ không phải giờ địa phương: mọi chỗ ghi
       trong app này đều ghi UTC, nên đó là phép diễn giải đúng, không phải đoán.
    """
    return luc if luc.tzinfo is not None else luc.replace(tzinfo=timezone.utc)


# ── Hội thoại ────────────────────────────────────────────────────────────────

def tao_hoi_thoai(db, *, user_id: str, model_alias: str = "",
                  title: str = "") -> ChatlttConversation:
    hoi = ChatlttConversation(user_id=str(user_id), model_alias=str(model_alias or ""),
                              title=str(title or "")[:200])
    db.add(hoi)
    db.flush()
    return hoi


def lay_hoi_thoai(db, *, user_id: str, conv_id: str,
                  gom_da_xoa: bool = False) -> ChatlttConversation:
    hoi = db.get(ChatlttConversation, str(conv_id))
    if hoi is None or hoi.user_id != str(user_id) or (hoi.deleted_at and not gom_da_xoa):
        raise KhongTimThay("khong co hoi thoai nay")
    return hoi


def liet_ke(db, *, user_id: str, tim: str = "", gom_luu_tru: bool = False,
            limit: int = 50) -> list:
    """Hội thoại của một người, mới nhất trước. `tim` khớp tiêu đề **hoặc** nội dung."""
    q = select(ChatlttConversation).where(
        ChatlttConversation.user_id == str(user_id),
        ChatlttConversation.deleted_at.is_(None))
    if not gom_luu_tru:
        q = q.where(ChatlttConversation.archived_at.is_(None))
    tim = (tim or "").strip()
    if tim:
        mau = f"%{tim}%"
        co_noi_dung = select(ChatlttMessage.conversation_id).where(
            ChatlttMessage.user_id == str(user_id),
            ChatlttMessage.blocks.cast(_Text).ilike(mau))
        q = q.where(or_(ChatlttConversation.title.ilike(mau),
                        ChatlttConversation.id.in_(co_noi_dung)))
    q = q.order_by(ChatlttConversation.updated_at.desc()).limit(max(1, min(int(limit), 200)))
    return list(db.execute(q).scalars())


def doi_ten(db, *, user_id: str, conv_id: str, title: str) -> ChatlttConversation:
    hoi = lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    hoi.title = str(title or "").strip()[:200]
    hoi.updated_at = _now()
    return hoi


def luu_tru(db, *, user_id: str, conv_id: str, luu: bool = True) -> ChatlttConversation:
    hoi = lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    hoi.archived_at = _now() if luu else None
    hoi.updated_at = _now()
    return hoi


def xoa(db, *, user_id: str, conv_id: str) -> ChatlttConversation:
    """Xoá MỀM. Lượt đang chạy trong hội thoại được đánh `cancelled` để reload
    không dựng lại một thứ 'đang chảy' mà không ai xem."""
    hoi = lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    hoi.deleted_at = _now()
    hoi.updated_at = _now()
    for ex in db.execute(select(ChatlttExecution).where(
            ChatlttExecution.conversation_id == hoi.id,
            ChatlttExecution.status.in_(("streaming", "queued")))).scalars():
        ex.status = "cancelled"
        ex.finished_at = _now()
    for m in db.execute(select(ChatlttMessage).where(
            ChatlttMessage.conversation_id == hoi.id,
            ChatlttMessage.status.in_(("streaming", "queued", "draft")))).scalars():
        m.status = "cancelled"
    return hoi


# ── Message / cây ────────────────────────────────────────────────────────────

#: Bao lau sau khi XOA MEM thi don that. Khong phai mot con so tuy y:
#:
#: 🔴 Nguoi dung xoa nham la chuyen thuong, va thu ho mat khong lay lai duoc.
#:    30 ngay la cua so ma `AppProject` cua nen tang da chon cho dung viec do
#:    (Q89), nen dung lai no thay vi phat minh mot con so thu hai.
#:
#: ⛔ KHONG dung day de gia hoa hoi thoai con song. Governance khai
#:    `chatltt_*` la CONTENT **khong tu gia di** — mot hoi thoai chua bi xoa thi
#:    khong bao gio bi don, va do la loi hua voi khach.
GIA_HAN_XOA_NGAY = 30


def don_da_xoa(db, *, gia_han_ngay: int = GIA_HAN_XOA_NGAY, now=None) -> dict:
    """Don that nhung hoi thoai da xoa mem qua han. An toan goi nhieu lan.

    Xoa theo thu tu con -> cha (execution, message, roi conversation) de khong
    bao gio de lai mot hang tro toi mot hang khong con.

    ⚠️ **Khong** cham kho tep o day. Anh/tieng thuoc `jobs`, va `job_content.py`
       cua nen tang moi la thu so huu vong doi cua chung — don o hai noi la hai
       cach dem, va chung se lech.
    """
    from datetime import timedelta

    moc = (now or _now()) - timedelta(days=max(1, int(gia_han_ngay)))
    ids = [r[0] for r in db.execute(
        select(ChatlttConversation.id).where(
            ChatlttConversation.deleted_at.is_not(None),
            ChatlttConversation.deleted_at < moc)).all()]
    if not ids:
        return {"hoi_thoai": 0, "thong_diep": 0, "thi_hanh": 0}
    from sqlalchemy import delete

    n_ex = db.execute(delete(ChatlttExecution).where(
        ChatlttExecution.conversation_id.in_(ids))).rowcount or 0
    n_m = db.execute(delete(ChatlttMessage).where(
        ChatlttMessage.conversation_id.in_(ids))).rowcount or 0
    n_c = db.execute(delete(ChatlttConversation).where(
        ChatlttConversation.id.in_(ids))).rowcount or 0
    return {"hoi_thoai": n_c, "thong_diep": n_m, "thi_hanh": n_ex}


def bao_tri() -> None:
    """Viec dinh ky cua app — nen tang goi duoi lease, dung MOT lan tren cum.

    ⛔ KHONG duoc nem: mot app hong vong bao tri khong duoc lam hong vong bao
       tri cua app khac (cung luat voi `AppManifest.bang_gia`).
    """
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        kq = don_da_xoa(db)
        db.commit()
        if any(kq.values()):
            log.info("don hoi thoai da xoa: %s", kq)
    except Exception:                                           # noqa: BLE001
        db.rollback()
        log.exception("khong don duoc hoi thoai da xoa")
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def kiem_khoi(blocks) -> list:
    if not isinstance(blocks, list):
        raise ThamSoSai("blocks phai la danh sach")
    ra = []
    for k in blocks:
        if not isinstance(k, dict) or k.get("type") not in LOAI_KHOI:
            raise ThamSoSai(f"khoi khong hop le: {k!r}"[:200])
        ra.append(dict(k))
    return ra


def them_thong_diep(db, *, user_id: str, conv_id: str, role: str, blocks: list,
                    parent_id: Optional[str] = None, status: str = "done",
                    model_alias: str = "", chon_lam_la: bool = True) -> ChatlttMessage:
    """Thêm một nút. Ép `created_at(con) > created_at(cha)`; mặc định chọn nó làm lá."""
    hoi = lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    if role not in VAI:
        raise ThamSoSai("role khong hop le")
    if status not in TRANG_THAI:
        raise ThamSoSai("status khong hop le")
    khoi = kiem_khoi(blocks)
    luc = _now()
    if parent_id is not None:
        cha = db.get(ChatlttMessage, str(parent_id))
        if cha is None or cha.conversation_id != hoi.id or cha.user_id != str(user_id):
            raise KhongTimThay("khong co message cha nay")
        # BẤT BIẾN 1 — đồng hồ lùi hay hai lượt ghi trong cùng micro-giây đều
        # không được làm con "già" hơn cha; phép dựng cây phụ thuộc vào nó.
        cha_luc = _co_mui_gio(cha.created_at)
        if luc <= cha_luc:
            luc = cha_luc + timedelta(microseconds=1)
    m = ChatlttMessage(conversation_id=hoi.id, user_id=str(user_id),
                       parent_id=str(parent_id) if parent_id else None,
                       role=role, blocks=khoi, status=status,
                       model_alias=str(model_alias or ""), created_at=luc, updated_at=luc)
    db.add(m)
    db.flush()
    if chon_lam_la:
        hoi.current_leaf_id = m.id
    hoi.updated_at = luc
    return m


def lay_thong_diep(db, *, user_id: str, conv_id: str, msg_id: str) -> ChatlttMessage:
    m = db.get(ChatlttMessage, str(msg_id))
    if m is None or m.conversation_id != str(conv_id) or m.user_id != str(user_id):
        raise KhongTimThay("khong co message nay")
    return m


def cap_nhat_khoi(db, *, user_id: str, conv_id: str, msg_id: str, blocks: list,
                  status: Optional[str] = None) -> ChatlttMessage:
    m = lay_thong_diep(db, user_id=user_id, conv_id=conv_id, msg_id=msg_id)
    m.blocks = kiem_khoi(blocks)
    if status is not None:
        if status not in TRANG_THAI:
            raise ThamSoSai("status khong hop le")
        m.status = status
    m.updated_at = _now()
    return m


def chon_la(db, *, user_id: str, conv_id: str, msg_id: str) -> ChatlttConversation:
    """Đổi nhánh đang xem — lưu ở CSDL để reload quay lại đúng chỗ (AC-07)."""
    hoi = lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    lay_thong_diep(db, user_id=user_id, conv_id=conv_id, msg_id=msg_id)
    hoi.current_leaf_id = str(msg_id)
    return hoi


def tat_ca(db, *, user_id: str, conv_id: str) -> list:
    """Danh sách phẳng theo `created_at` — cha luôn đứng trước con nhờ bất biến 1."""
    hoi = lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    return list(db.execute(select(ChatlttMessage).where(
        ChatlttMessage.conversation_id == hoi.id
    ).order_by(ChatlttMessage.created_at.asc(), ChatlttMessage.id.asc())).scalars())


def anh_em(db, *, user_id: str, conv_id: str, parent_id: Optional[str]) -> list:
    hoi = lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    dk = (ChatlttMessage.parent_id.is_(None) if parent_id is None
          else ChatlttMessage.parent_id == str(parent_id))
    return list(db.execute(select(ChatlttMessage).where(
        ChatlttMessage.conversation_id == hoi.id, dk
    ).order_by(ChatlttMessage.created_at.asc(), ChatlttMessage.id.asc())).scalars())


def duong_toi_la(db, *, user_id: str, conv_id: str,
                 leaf_id: Optional[str] = None) -> list:
    """Gốc → lá (mặc định lá đang xem). Dùng để dựng ngữ cảnh gửi model.

    Đi ngược bằng `parent_id`, có `visited` chống vòng — cùng lối
    `BaseClient.getMessagesForConversation` của LibreChat.
    """
    hoi = lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    la = leaf_id or hoi.current_leaf_id
    if not la:
        return []
    theo_id = {m.id: m for m in tat_ca(db, user_id=user_id, conv_id=conv_id)}
    ra = []
    da_qua = set()
    hien = theo_id.get(str(la))
    while hien is not None and hien.id not in da_qua:
        da_qua.add(hien.id)
        ra.append(hien)
        hien = theo_id.get(hien.parent_id) if hien.parent_id else None
    ra.reverse()
    return ra


def dung_cay(phang: Iterable) -> list:
    """Danh sách phẳng (BẤT KỲ thứ tự) → rừng `{"message", "children", "depth", "sibling_index"}`.

    Hai lượt: lượt một lập bản đồ, lượt hai nối — nên **không** phụ thuộc cha
    đứng trước con (điểm yếu của `buildTree` một lượt của LibreChat, đặc tả
    bằng 5 test `convoStructure.spec.ts`). Cha vắng mặt ⇒ nút lên gốc.
    """
    nut = {}
    thu_tu = []
    for m in phang:
        nut[m.id] = {"message": m, "children": [], "depth": 0, "sibling_index": 0}
        thu_tu.append(m)
    thu_tu.sort(key=lambda m: (_co_mui_gio(m.created_at), m.id))
    goc = []
    dem_con: dict = {}
    for m in thu_tu:
        n = nut[m.id]
        cha = nut.get(m.parent_id) if m.parent_id else None
        khoa = m.parent_id if cha else None
        n["sibling_index"] = dem_con.get(khoa, 0)
        dem_con[khoa] = n["sibling_index"] + 1
        if cha is None:
            goc.append(n)
        else:
            cha["children"].append(n)
    # depth: BFS từ gốc.
    stack = [(n, 0) for n in goc]
    while stack:
        n, d = stack.pop()
        n["depth"] = d
        stack.extend((c, d + 1) for c in n["children"])
    return goc


def su_that(db, *, user_id: str, conv_id: str) -> dict:
    """Toàn bộ sự thật để reload: hội thoại + message phẳng + execution theo message.

    Trình duyệt không giữ gì bắt buộc; message `streaming` mang `partial_text`
    của execution để hiện đúng phần đã sinh (AC-02, AC-08, AC-09).
    """
    hoi = lay_hoi_thoai(db, user_id=user_id, conv_id=conv_id)
    ms = tat_ca(db, user_id=user_id, conv_id=conv_id)
    exs = {e.message_id: e for e in db.execute(select(ChatlttExecution).where(
        ChatlttExecution.conversation_id == hoi.id)).scalars()}
    return {
        "conversation": {"id": hoi.id, "title": hoi.title, "model_alias": hoi.model_alias,
                         "current_leaf_id": hoi.current_leaf_id,
                         "archived": hoi.archived_at is not None,
                         "created_at": hoi.created_at.isoformat(),
                         "updated_at": hoi.updated_at.isoformat()},
        "messages": [_mo_ta(m, exs.get(m.id)) for m in ms],
    }


def _mo_ta(m: ChatlttMessage, ex: Optional[ChatlttExecution]) -> dict:
    d = {"id": m.id, "parent_id": m.parent_id, "role": m.role, "blocks": list(m.blocks or []),
         "status": m.status, "model_alias": m.model_alias, "execution_id": m.execution_id,
         "created_at": m.created_at.isoformat()}
    if ex is not None:
        d["execution"] = {"id": ex.id, "status": ex.status, "mode": ex.mode,
                          "tool_name": ex.tool_name, "partial_text": ex.partial_text,
                          "reasoning_text": ex.reasoning_text,
                          "finish_reason": ex.finish_reason, "usage": dict(ex.usage or {}),
                          "credit": {"giu": ex.credit_giu, "thu": ex.credit_thu,
                                     "hoan": ex.credit_hoan},
                          "error_code": ex.error_code, "error_text": ex.error_text,
                          "job_id": ex.job_id, "seq": ex.seq}
    return d


# `blocks` là JSON; tìm nội dung bằng cast sang text — đủ cho V1 (tìm theo chuỗi
# con), không phải full-text. Khai kiểu ở đây để `liet_ke` không import sqlalchemy.types.
from sqlalchemy import Text as _Text  # noqa: E402
