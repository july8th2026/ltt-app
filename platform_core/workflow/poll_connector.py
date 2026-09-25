"""Trigger **poll** của piece connector — `PIECE_POLL` (spec §11.4, FLOW D).

Một trigger POLLING của Activepieces trả về *"những bản ghi mới kể từ lần
trước"*. Nhiệm vụ của mô-đun này là biến danh sách ấy thành **một run cho mỗi
bản ghi mới**, và ⛔ không bao giờ hai run cho một bản ghi.

## Hai lớp khử trùng, và cần cả hai

1. **Store của piece** (`connector_store`) — piece tự nhớ nó đã thấy gì. Đây là
   lớp *"lần poll thứ hai không trả lại bản ghi cũ"*.
2. **Khoá `poll:<trigger_id>:<ban_ghi_id>`** (`khoa_idem.khoa_poll`) — chốt ở
   chỉ mục `ux_workflow_run_idem`.

⭐ Vì sao không đủ một lớp: store **mất được**. Một lần khôi phục CSDL, một lần
   sửa tay, một `xoa_pham_vi` nhầm — và lần poll kế tiếp coi **mọi** bản ghi là
   mới, tức tạo lại run cho cả lịch sử, tức tiêu credit thật. Lớp 2 biến sự cố
   ấy thành "không có gì xảy ra". Cùng lập luận `ban_su_kien` đã viết cho
   `trigger.event`, và cùng lý do.

## ⛔ Chu kỳ tối thiểu 300 giây

Spec §11.4. Mỗi lượt poll là **một tiến trình Node** trong AppContainer trên
máy production; một trigger đặt `chu_ky_s = 5` là 12 tiến trình mỗi phút cho
một khách. Trần nằm ở `tao_cau_hinh`, tức **lúc tạo**, chứ không ở vòng bắn —
từ chối lúc chạy thì khách đã lưu được một thứ không chạy.

## Vì sao có `ban()` riêng thay vì dùng `ban_trigger.ban_mot`

`ban_mot` tạo **một** run cho **một** mốc lịch. Poll thì một mốc ra **N** run
(N = số bản ghi mới), và N chỉ biết được **sau khi** đã gọi ra ngoài. Đó là
một hình dạng khác, không phải một tham số khác — nên `ban_trigger` hỏi mô-đun
loại *"anh có tự bắn không"* thay vì mọc thêm một nhánh `if kind == ...`.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional

from platform_core.models import Workflow, WorkflowTrigger
from platform_core.workflow import connector as _connector
from platform_core.workflow import connector_store as _store
from platform_core.workflow import khoa_idem, tao_run, trigger as _trigger

KIND = "PIECE_POLL"

#: Spec §11.4 — `trigger.config.chu_ky_s >= 300`.
CHU_KY_TOI_THIEU_S = 300

#: Trần số bản ghi xử lý trong MỘT lượt poll. ⭐ Có trần vì lượt poll **đầu
#: tiên** của một Sheet 50 000 dòng sẽ trả về 50 000 bản ghi, và mỗi bản ghi là
#: một run có giữ credit. Chạm trần ⇒ xử phần đầu, phần còn lại rơi vào lượt
#: sau (store của piece đã ghi nhận phần đã thấy).
TRAN_BAN_GHI_MOI_LUOT = 100


class LoiPoll(ValueError):
    """Cấu hình poll sai. Ném **lúc tạo trigger**, không đợi lúc bắn."""


def tao_cau_hinh(*, piece: str, piece_version: str, ten_trigger: str,
                 props: Optional[dict] = None, credential_ref: str = "",
                 chu_ky_s: int = CHU_KY_TOI_THIEU_S) -> dict:
    """`config` hợp lệ cho một trigger `PIECE_POLL`. ⛔ Không dựng tay dict này
    ở chỗ khác — trần chu kỳ phải đi qua đúng một cửa."""
    if int(chu_ky_s) < CHU_KY_TOI_THIEU_S:
        raise LoiPoll(
            f"chu_ky_s = {chu_ky_s} < {CHU_KY_TOI_THIEU_S} (spec §11.4): moi "
            "luot poll la mot tien trinh Node tren may production")
    if not piece or not ten_trigger:
        raise LoiPoll("thieu `piece` hoac `ten_trigger`")
    return {"piece": str(piece), "piece_version": str(piece_version),
            "ten_trigger": str(ten_trigger), "props": dict(props or {}),
            "credential_ref": str(credential_ref),
            "chu_ky_s": int(chu_ky_s)}


def id_ban_ghi(ban_ghi) -> str:
    """Id ổn định của một bản ghi piece trả về.

    ⭐ Ưu tiên `id`/`_id`, nếu không có thì **băm nội dung**. ⛔ Không dùng chỉ
       số trong danh sách: thứ tự của một API bên thứ ba không phải hợp đồng,
       và một bản ghi chen vào giữa sẽ làm mọi chỉ số sau nó trỏ sang bản ghi
       khác — tức tạo lại run cho những thứ đã chạy.
    """
    if isinstance(ban_ghi, dict):
        for k in ("id", "_id", "rowId", "row_id"):
            if ban_ghi.get(k) not in (None, ""):
                return str(ban_ghi[k])[:80]
    tho = json.dumps(ban_ghi, sort_keys=True, default=str)
    return "h" + hashlib.sha256(tho.encode("utf-8")).hexdigest()[:32]


class PiecePoll:
    """Loại trigger. Hai câu hỏi của `LoaiTrigger`, cộng `moc_gan_nhat` và
    `ban` (hợp đồng mở rộng — xem docstring mô-đun)."""

    kind = KIND

    def toi_han(self, cau_hinh: dict, bay_gio: datetime) -> bool:
        return True

    def moc_gan_nhat(self, cau_hinh: dict,
                     bay_gio: datetime) -> Optional[datetime]:
        return bay_gio

    def lan_ke_tiep(self, cau_hinh: dict,
                    bay_gio: datetime) -> Optional[datetime]:
        chu_ky = int((cau_hinh or {}).get("chu_ky_s") or 0)
        if chu_ky < CHU_KY_TOI_THIEU_S:
            return None
        return bay_gio + timedelta(seconds=chu_ky)

    # ⭐ Hợp đồng mở rộng: `ban_trigger.ban_mot` gọi hàm này nếu có, và khi ấy
    #    nó KHÔNG tự tạo run. Trả về số run MỚI đã tạo.
    def ban(self, db, t: WorkflowTrigger, *, moc: datetime,
            la_bu: bool) -> int:
        return mot_luot_poll(db, t, moc=moc)


def _goi_runner(db, t: WorkflowTrigger):
    """Gọi `run_trigger` trong vỏ. Trả `(ban_ghi, store_ops)`.

    🔴 **⛔ KHÔNG áp `store_ops` ở đây.** Đó là thứ tự sai, và nó mất bản ghi
       của khách: `store_ops` chính là chỗ piece ghi *"tôi đã thấy r1, r2"*.
       Áp nó **trước** khi run được tạo nghĩa là một lần tạo run hỏng giữa
       chừng (hết hạn mức run đồng thời, CSDL rớt) để lại một store nói "đã
       thấy" cho những bản ghi **chưa bao giờ** có run — và chúng không bao giờ
       quay lại. Người gọi áp `store_ops` **sau cùng**; xem `mot_luot_poll`.

    ⛔ Lỗi **nổi lên**: `ban_trigger.ban_den_han` đã bọc mỗi trigger trong một
       savepoint riêng và đếm `loi_lien_tiep` (5 lần ⇒ tự tắt, spec §11.4).
       Nuốt lỗi ở đây là vô hiệu hoá đúng cơ chế đó.
    """
    cau_hinh = dict(t.config or {})
    pham_vi = _store.pham_vi_trigger(t.id)
    auth = None
    ref = str(cau_hinh.get("credential_ref") or "")
    if ref:
        from platform_core import credential as kho
        auth = kho.lay_de_dung(db, ref, owner_id=t.owner_id)
    kq = _connector.chay(
        "run_trigger", piece=str(cau_hinh["piece"]),
        version=str(cau_hinh.get("piece_version") or ""),
        name=str(cau_hinh["ten_trigger"]),
        props=dict(cau_hinh.get("props") or {}), auth=auth,
        store=_store.doc(db, owner_id=t.owner_id, pham_vi=pham_vi))
    if not kq.ok:
        raise LoiPoll(f"{kq.ma_loi}: {kq.thong_diep}"[:500])
    ra = kq.output
    ban_ghi = [] if ra is None else (list(ra) if isinstance(ra, list) else [ra])
    return ban_ghi, list(kq.store_ops or [])


def mot_luot_poll(db, t: WorkflowTrigger, *, moc: datetime,
                  goi=None) -> int:
    """Một lượt poll ⇒ **một run cho mỗi bản ghi MỚI**. Trả số run mới.

    `goi` cho phép phép kiểm thay lớp gọi runner mà **không** thay logic khử
    trùng — thứ đang được đo. Nó trả `(ban_ghi, store_ops)` hoặc, để gọn cho
    phép kiểm, chỉ `ban_ghi`.

    🔴 **Hạn mức run đồng thời (`tao_run.QuaHanMuc`) là một điểm DỪNG, ⛔ không
       phải một lỗi.** Đo 24/09: một lượt poll 125 bản ghi ném `QuaHanMuc: toi
       da 5 run dong thoi` và làm **cả lượt poll** hỏng — mà `ban_den_han` đếm
       đó là một lần lỗi của trigger, nên **5 lượt poll đông là trigger tự
       tắt**. Đúng hành vi là: tạo được bao nhiêu thì tạo, phần còn lại để lượt
       sau — và vì `store_ops` chỉ áp khi chạy trọn vẹn, phần còn lại **quay
       lại** ở lượt sau thay vì biến mất.
    """
    wf = db.get(Workflow, t.workflow_id)
    if wf is None:
        raise LoiPoll(f"workflow {t.workflow_id!r} khong con")
    ket = (goi or _goi_runner)(db, t)
    ban_ghi, store_ops = ket if isinstance(ket, tuple) else (ket, [])
    if len(ban_ghi) > TRAN_BAN_GHI_MOI_LUOT:
        ban_ghi = ban_ghi[:TRAN_BAN_GHI_MOI_LUOT]
    so_moi = 0
    du_cho = True
    for bg in ban_ghi:
        rid = id_ban_ghi(bg)
        try:
            _run, moi = tao_run.tao_run(
                db, workflow=wf, owner_id=t.owner_id, trigger_kind="poll",
                idempotency_key=khoa_idem.khoa_poll(t.id, rid),
                inputs={"ban_ghi": bg, "ban_ghi_id": rid,
                        "fired_at": moc.isoformat()})
        except tao_run.QuaHanMuc:
            du_cho = False
            break
        if moi:
            so_moi += 1
    # ⭐ Áp `store_ops` **sau cùng**, và **chỉ khi** đã xử hết danh sách. Dừng
    #    giữa chừng ⇒ không ghi "đã thấy" ⇒ lượt sau piece trả lại đúng những
    #    bản ghi ấy, và khoá `poll:<trigger>:<ban_ghi>` lo phần không-trùng.
    if store_ops and du_cho:
        _store.ap(db, owner_id=t.owner_id,
                  pham_vi=_store.pham_vi_trigger(t.id), ops=store_ops)
    db.flush()
    return so_moi


_trigger.dang_ky(PiecePoll())


def _goi_on_enable(db, t: WorkflowTrigger) -> list:
    """Gọi OP `trigger_on_enable` thật qua runner — trả `store_ops`.

    ⭐ Vì sao là một hàm RIÊNG, không gộp vào `_goi_runner`: `run_trigger` và
       `trigger_on_enable` là hai OP khác nhau của
       `connector_runner/src/runner.js`. Nhiều trigger POLLING thật dùng
       `DedupeStrategy.TIMEBASED` của Activepieces (vd.
       `google-sheets/new-spreadsheet`, `google-sheets/new-worksheet`) — bản
       thân `pollingHelper.poll()` của họ **ném** nếu `store.get("lastPoll")`
       rỗng; `onEnable` là nơi DUY NHẤT seed mốc đó. `@ltt/piece-gia` (piece
       giả cũ của FLOW D) không có ràng buộc này nên khoảng trống chưa từng
       lộ — xem đầu tệp `tests/test_3505_wf_flow_d_poll_pg.py`.

    ⛔ **Không cần mạng cho bước này.** Spike 25/09 (piece thật
       `@activepieces/piece-google-sheets@0.17.0`, `auth=None`): cả
       `onEnable` (strategy TIMEBASED) lẫn phép `run()` từ chối khi thiếu
       `lastPoll` đều chạy XONG **trước** khi piece gọi `items()` — tức trước
       khi chạm API thật. Chỉ `run()` SAU KHI đã bật mới cần `auth` thật.
    """
    cau_hinh = dict(t.config or {})
    pham_vi = _store.pham_vi_trigger(t.id)
    auth = None
    ref = str(cau_hinh.get("credential_ref") or "")
    if ref:
        from platform_core import credential as kho
        auth = kho.lay_de_dung(db, ref, owner_id=t.owner_id)
    kq = _connector.chay(
        "trigger_on_enable", piece=str(cau_hinh["piece"]),
        version=str(cau_hinh.get("piece_version") or ""),
        name=str(cau_hinh["ten_trigger"]),
        props=dict(cau_hinh.get("props") or {}), auth=auth,
        store=_store.doc(db, owner_id=t.owner_id, pham_vi=pham_vi))
    if not kq.ok:
        raise LoiPoll(f"{kq.ma_loi}: {kq.thong_diep}"[:500])
    return list(kq.store_ops or [])


def bat(db, t: WorkflowTrigger, *, goi=None) -> int:
    """Bật một trigger `PIECE_POLL` — tương đương `onEnable` của Activepieces.

    🔴 **Gọi ĐÚNG MỘT LẦN, lúc trigger được tạo/bật, TRƯỚC lượt
       `mot_luot_poll` đầu tiên.** Bỏ qua bước này với một piece TIMEBASED
       thật làm **mọi** lượt poll sau đó ném `LoiPoll` ("lastPoll doesn't
       exist in the store.") — `run()` của piece từ chối chạy khi chưa có mốc.

    `goi` cho phép phép kiểm thay lớp gọi runner (cùng quy ước `mot_luot_poll`),
    ⛔ không thay logic áp `store_ops` — thứ đang được đo. Trả số `store_ops`
    đã áp (0 là hợp lệ: một số piece — vd. `LAST_ITEM` không dữ liệu — không
    ghi gì lúc bật).
    """
    ops = (goi or _goi_on_enable)(db, t)
    if ops:
        _store.ap(db, owner_id=t.owner_id,
                  pham_vi=_store.pham_vi_trigger(t.id), ops=ops)
    db.flush()
    return len(ops)


def tao_trigger(db, *, workflow_id: str, owner_id: str, piece: str,
                piece_version: str, ten_trigger: str, props: Optional[dict] = None,
                credential_ref: str = "", chu_ky_s: int = CHU_KY_TOI_THIEU_S,
                goi_bat=None) -> WorkflowTrigger:
    """Tạo MỘT trigger `PIECE_POLL` **và bật nó** (`bat`) trong một bước.

    ⭐ Đường NÊN DÙNG để tạo trigger poll thật, thay vì gọi thẳng
       `trigger.tao(kind=poll_connector.KIND, ...)`. `platform_core.workflow.
       trigger` (lõi) cố tình không biết piece nào cần `onEnable` — đúng
       nguyên tắc `G42` ở đầu tệp đó ("lõi không biết tên loại"); hàm này khép
       kín hiểu biết ấy ở ĐÚNG một chỗ thuộc về nó: mô-đun `PIECE_POLL`.
    """
    cau_hinh = tao_cau_hinh(piece=piece, piece_version=piece_version,
                            ten_trigger=ten_trigger, props=props,
                            credential_ref=credential_ref, chu_ky_s=chu_ky_s)
    t = _trigger.tao(db, workflow_id=workflow_id, owner_id=owner_id,
                     kind=KIND, cau_hinh=cau_hinh)
    bat(db, t, goi=goi_bat)
    return t


__all__ = ["CHU_KY_TOI_THIEU_S", "KIND", "LoiPoll", "PiecePoll",
           "TRAN_BAN_GHI_MOI_LUOT", "bat", "id_ban_ghi", "mot_luot_poll",
           "tao_cau_hinh", "tao_trigger"]
