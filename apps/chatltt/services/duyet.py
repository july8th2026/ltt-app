"""
duyet.py — duyệt BỀN cho một bước tốn tiền. (H44 P04)

Đặc tả: `02_HOP_DONG.md` §2 (bảng `chatltt_approval`) và §5 (sự kiện).

## Bền, nghĩa là sống sót qua việc đóng tab

Một hộp thoại xác nhận trong trình duyệt **không phải** một cổng duyệt: đóng tab
là mất, và cái mất im lặng. Ở đây quyết định là **một hàng trong CSDL**, nên nó
sống qua reload, qua khởi động lại dịch vụ, và tra lại được sau ba tháng khi có
người hỏi *"ai đã đồng ý tiêu 12 credit này"*.

## Hai ràng buộc UNIQUE, hai việc khác nhau

    UNIQUE(step_id)          mot buoc chi co MOT phieu duyet
    UNIQUE(idempotency_key)  goi `xin_duyet` hai lan khong sinh hai phieu

Cái thứ nhất là **luật nghiệp vụ**: hai phiếu cho một bước nghĩa là người dùng
có thể duyệt một cái và từ chối cái kia, và không ai biết cái nào tính.
Cái thứ hai là **chống lặp mạng**: trình duyệt gửi lại, proxy gửi lại.

## ⛔ Quyết định đi bằng UPDATE CÓ ĐIỀU KIỆN, không bằng `if` trong Python

Đọc-rồi-ghi có một khe giữa hai câu lệnh, và hai yêu cầu song song lọt vừa vào
khe ấy sẽ **cùng** thấy `cho` rồi **cùng** ghi. Ở đây điều kiện `quyet_dinh='cho'`
nằm ngay trong mệnh đề `WHERE`, nên CSDL quyết ai thắng và `rowcount` nói ai
thua. Cùng luật `leases.py` dùng để không hai worker cùng nhận một job.

## Từ chối KHÔNG giết run

`02_HOP_DONG.md` §1: `AWAITING_APPROVAL → TOOL_RESULT_READY`. Người dùng nói
"không" là một **câu trả lời**, và model phải đọc được nó để đổi cách — chứ
không phải một lượt chết giữa chừng mà người dùng phải tự đoán vì sao.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from apps.chatltt.services import thi_hanh
from apps.chatltt.tables import ChatlttApproval

CHO = "cho"
DUYET = "duyet"
TU_CHOI = "tu_choi"
HET_HAN = "het_han"

DA_QUYET = frozenset({DUYET, TU_CHOI, HET_HAN})

#: Bao lâu thì một phiếu chờ tự hết hạn.
#:
#: ⭐ 30 phút, không phải 24 giờ. Một phiếu duyệt mang **báo giá** — và báo giá
#:    gắn với `phien_ban_gia` tại thời điểm hỏi. Để nó sống qua đêm là để người
#:    dùng bấm đồng ý với một cái giá đã đổi.
HAN_CHO_PHUT = 30


class KhongTimThay(LookupError):
    """Không có phiếu ấy, hoặc nó không thuộc người dùng này."""


class DaQuyetRoi(RuntimeError):
    """Phiếu đã có quyết định — không lật lại được."""


def khoa_idem(*, run_id: str, step_id: str, bam_trung: str) -> str:
    """Khoá chống lặp, dẫn xuất — **không** để bên gọi tự nghĩ ra.

    ⛔ Một khoá do client sinh là một khoá client có thể sinh khác đi khi gửi
       lại, và lúc ấy ràng buộc UNIQUE không chặn gì cả. Dẫn xuất từ ba thứ
       định danh chính lời gọi thì hai lần hỏi cùng một việc luôn ra cùng khoá.
    """
    tho = f"{run_id}\x1f{step_id}\x1f{bam_trung}"
    return hashlib.sha256(tho.encode("utf-8")).hexdigest()[:64]


def _het_han_luc(p: ChatlttApproval) -> datetime:
    t = p.created_at
    if t.tzinfo is None:                       # SQLite trả về naive
        t = t.replace(tzinfo=timezone.utc)
    return t + timedelta(minutes=HAN_CHO_PHUT)


def da_het_han(p: ChatlttApproval, *, bay_gio: Optional[datetime] = None) -> bool:
    return (bay_gio or datetime.now(timezone.utc)) >= _het_han_luc(p)


def xin_duyet(db, *, user_id: str, run_id: str, step_id: str, tool_name: str,
              doi_so: dict, policy_class: str, bao_gia_credit: int,
              phien_ban_gia: str, bam_trung: str = "") -> ChatlttApproval:
    """Mở một phiếu chờ. Gọi lại cho cùng một bước trả **đúng phiếu cũ**.

    ⭐ Trả phiếu cũ chứ không ném: một lần gửi lại vì mạng chập không phải lỗi
       của ai, và biến nó thành lỗi buộc mọi bên gọi phải viết mã bắt lỗi cho
       một trường hợp bình thường.
    """
    from sqlalchemy import select

    cu = db.execute(select(ChatlttApproval).where(
        ChatlttApproval.step_id == str(step_id),
        ChatlttApproval.user_id == str(user_id))).scalar_one_or_none()
    if cu is not None:
        return cu

    p = ChatlttApproval(
        step_id=str(step_id), run_id=str(run_id), user_id=str(user_id),
        tool_name=str(tool_name), doi_so=dict(doi_so or {}),
        policy_class=str(policy_class), bao_gia_credit=int(bao_gia_credit),
        phien_ban_gia=str(phien_ban_gia), quyet_dinh=CHO,
        idempotency_key=khoa_idem(run_id=run_id, step_id=step_id,
                                  bam_trung=bam_trung or str(step_id)))
    db.add(p)
    db.flush()
    return p


def _quyet(db, *, user_id: str, approval_id: str, thanh: str,
           quyet_boi: str = "", doi_so_da_sua: Optional[dict] = None) -> ChatlttApproval:
    """UPDATE có điều kiện. `rowcount == 0` ⇒ ai đó đã quyết trước."""
    from sqlalchemy import select, update

    gt: dict = {"quyet_dinh": thanh, "quyet_boi": str(quyet_boi or user_id),
                "quyet_luc": datetime.now(timezone.utc)}
    if doi_so_da_sua is not None:
        gt["doi_so_da_sua"] = dict(doi_so_da_sua)

    kq = db.execute(
        update(ChatlttApproval)
        .where(ChatlttApproval.id == str(approval_id),
               ChatlttApproval.user_id == str(user_id),
               # 🔴 Điều kiện nằm TRONG `WHERE`. Đọc-rồi-ghi có một khe giữa hai
               #    câu lệnh, và hai yêu cầu song song lọt vừa vào khe ấy.
               ChatlttApproval.quyet_dinh == CHO)
        .values(**gt))

    if kq.rowcount == 0:
        p = db.execute(select(ChatlttApproval).where(
            ChatlttApproval.id == str(approval_id),
            ChatlttApproval.user_id == str(user_id))).scalar_one_or_none()
        if p is None:
            raise KhongTimThay(f"khong co phieu duyet {approval_id!r}")
        raise DaQuyetRoi(f"phieu da o trang thai {p.quyet_dinh!r}")

    db.flush()
    return db.execute(select(ChatlttApproval).where(
        ChatlttApproval.id == str(approval_id))).scalar_one()


def duyet(db, *, user_id: str, approval_id: str, quyet_boi: str = "",
          doi_so_da_sua: Optional[dict] = None) -> ChatlttApproval:
    """Đồng ý. `doi_so_da_sua` khi người dùng chỉnh tham số trước khi bấm.

    ⛔ Phiếu **hết hạn** không duyệt được — kiểm trước khi ghi, vì báo giá trên
       phiếu đã cũ và người dùng đang đồng ý với một con số không còn đúng.
    """
    from sqlalchemy import select

    p = db.execute(select(ChatlttApproval).where(
        ChatlttApproval.id == str(approval_id),
        ChatlttApproval.user_id == str(user_id))).scalar_one_or_none()
    if p is None:
        raise KhongTimThay(f"khong co phieu duyet {approval_id!r}")
    if p.quyet_dinh == CHO and da_het_han(p):
        _quyet(db, user_id=user_id, approval_id=approval_id, thanh=HET_HAN,
               quyet_boi="he_thong")
        raise DaQuyetRoi("phieu da het han — hay xin bao gia moi")
    return _quyet(db, user_id=user_id, approval_id=approval_id, thanh=DUYET,
                  quyet_boi=quyet_boi, doi_so_da_sua=doi_so_da_sua)


def tu_choi(db, *, user_id: str, approval_id: str,
            quyet_boi: str = "") -> ChatlttApproval:
    """Không đồng ý. Hết hạn rồi thì từ chối vẫn được — kết quả như nhau."""
    return _quyet(db, user_id=user_id, approval_id=approval_id, thanh=TU_CHOI,
                  quyet_boi=quyet_boi)


def quet_het_han(db, *, bay_gio: Optional[datetime] = None) -> int:
    """Đóng mọi phiếu chờ đã quá hạn. Trả số phiếu đã đóng."""
    from sqlalchemy import select

    moc = (bay_gio or datetime.now(timezone.utc))
    ds = db.execute(select(ChatlttApproval).where(
        ChatlttApproval.quyet_dinh == CHO)).scalars().all()
    n = 0
    for p in ds:
        if da_het_han(p, bay_gio=moc):
            p.quyet_dinh = HET_HAN
            p.quyet_boi = "he_thong"
            p.quyet_luc = moc
            n += 1
    db.flush()
    return n


def doi_so_cuoi(p: ChatlttApproval) -> dict:
    """Đối số **thật sự** phải chạy: bản người dùng sửa nếu có, không thì bản gốc.

    🔴 Bên gọi phải dùng hàm này, đừng đọc `p.doi_so` thẳng. Người dùng sửa
       tham số rồi bấm đồng ý mà hệ thống chạy bản gốc là chạy một việc **không
       ai duyệt** — và nó tiêu tiền thật.
    """
    return dict(p.doi_so_da_sua if p.doi_so_da_sua is not None else p.doi_so)


def ket_qua_cho_model(p: ChatlttApproval) -> thi_hanh.KetQua:
    """Một quyết định KHÔNG-duyệt → `KetQua` để model đọc và đổi cách.

    ⛔ Không ném. `02_HOP_DONG.md` §1: `AWAITING_APPROVAL → TOOL_RESULT_READY`.
       Người dùng nói "không" là một **câu trả lời**, không phải một sự cố — và
       model phải biết để nói lại với người dùng, chứ không im lặng chết.
    """
    if p.quyet_dinh == TU_CHOI:
        return thi_hanh.KetQua(
            False, ma_loi="tu_choi", lop=p.policy_class,
            thong_diep=(f"nguoi dung TU CHOI chay {p.tool_name!r}. Dung goi lai "
                        f"tool nay; hay tra loi bang cach khac hoac hoi ho muon gi."))
    if p.quyet_dinh == HET_HAN:
        return thi_hanh.KetQua(
            False, ma_loi="het_han", lop=p.policy_class,
            thong_diep=(f"de nghi duyet {p.tool_name!r} da het han sau "
                        f"{HAN_CHO_PHUT} phut khong ai tra loi."))
    raise ValueError(f"phieu dang o {p.quyet_dinh!r}, chua co ket qua cho model")


def su_kien_can_duyet(p: ChatlttApproval) -> dict:
    """Sự kiện `approval.required` (§5). Chỉ thứ giao diện cần để vẽ nút."""
    return {"type": "approval.required", "approval_id": p.id,
            "tool_name": p.tool_name, "doi_so": p.doi_so,
            "credit": p.bao_gia_credit, "policy_class": p.policy_class,
            "het_han_luc": _het_han_luc(p).isoformat()}


def su_kien_quyet(p: ChatlttApproval) -> dict:
    ten = {DUYET: "approval.granted", TU_CHOI: "approval.denied",
           HET_HAN: "approval.expired"}[p.quyet_dinh]
    sk = {"type": ten, "approval_id": p.id}
    if p.quyet_dinh == DUYET and p.doi_so_da_sua is not None:
        sk["doi_so_da_sua"] = p.doi_so_da_sua
    return sk


def dang_cho(db, *, user_id: str, run_id: str = "") -> list:
    """Phiếu còn chờ của một người dùng — để dựng lại giao diện sau reload."""
    from sqlalchemy import select

    q = select(ChatlttApproval).where(ChatlttApproval.user_id == str(user_id),
                                      ChatlttApproval.quyet_dinh == CHO)
    if run_id:
        q = q.where(ChatlttApproval.run_id == str(run_id))
    return [su_kien_can_duyet(p)
            for p in db.execute(q.order_by(ChatlttApproval.created_at)).scalars()
            if not da_het_han(p)]


__all__ = ["xin_duyet", "duyet", "tu_choi", "quet_het_han", "doi_so_cuoi",
           "ket_qua_cho_model", "su_kien_can_duyet", "su_kien_quyet", "dang_cho",
           "khoa_idem", "da_het_han", "KhongTimThay", "DaQuyetRoi",
           "CHO", "DUYET", "TU_CHOI", "HET_HAN", "DA_QUYET", "HAN_CHO_PHUT"]
