"""Handler của `workflow.piece` và `workflow.connector` (plan wf-v2 P6).

Nó làm đúng bốn việc, theo thứ tự đó:

1. **Giải mã credential** — `credential.lay_de_dung` là hàm DUY NHẤT trả bản
   rõ, và chỉ tiến trình job được gọi (spec §9.4).
2. **Đọc store** của phạm vi (`connector_store`) ⇒ đưa vào `vao.json`.
3. **Chạy** — `connector.chay` (AppContainer + proxy lọc miền) cho piece;
   `youtube_upload` cho connector native.
4. **Áp `store_ops`** và chuyển `files` sang artifact.

## ⛔ Bí mật không bao giờ ra `result`

`Job.result` đi vào `WaitpointSignal.result_ref` rồi vào `node_run_snapshot` —
tức vào một bản ghi mà trình soạn thảo đọc được. Runner đã che theo TÊN ở phía
Node (`runner.js::cheBiMat`); đây là cửa thứ hai, và hai cửa là đúng: một che
sót ở cửa một mà không có cửa hai là một token của khách nằm trong CSDL.
"""
from __future__ import annotations

import json

from platform_core.db import get_session
from platform_core.workflow import connector as _connector
from platform_core.workflow import connector_store as _store

#: Tên tham số mang **ref** credential của khách. ⛔ Không phải bí mật: ref là
#: một id, và chỗ duy nhất giải mã nó là tiến trình này.
THAM_SO_CREDENTIAL = "credential"


class LoiHandler(RuntimeError):
    pass


def _bi_mat(db, ref: str, owner_id: str, *, run_id: str, node_id: str):
    """Bản rõ của credential, hoặc `None` khi node không khai credential."""
    if not ref:
        return None
    from platform_core import credential as kho

    lam_moi = None
    try:
        from platform_core import oauth_google
        lam_moi = oauth_google.bo_lam_moi()
    except ImportError:
        # 🔴 CHI `ImportError`. Chu thich cu ghi "nha cung cap chua cau hinh",
        #    nhung `bo_lam_moi()` chi TRA VE mot closure — cau hinh doc BEN
        #    TRONG no, luc goi. Nen "chua cau hinh" khong the nem o day, va
        #    `except Exception` dang boc mot ca khong ton tai, trong khi nuot
        #    that nhung loi THAT trong `oauth_google` (vd mot `NameError` do
        #    go sai ten) thanh "credential nay khong phai OAuth".
        lam_moi = None      # credential khong phai OAuth van dung duoc
    return kho.lay_de_dung(db, ref, owner_id=owner_id, run_id=run_id,
                           node_id=node_id, lam_moi=lam_moi)


def _chay_piece(db, params: dict, meta: dict) -> dict:
    owner_id = str(params.get("owner_id") or "")
    pham_vi = _store.pham_vi_run(str(meta.get("run_id") or ""))
    props = {k: v for k, v in params.items()
             if not k.startswith("_") and k not in
             ("owner_id", THAM_SO_CREDENTIAL)}
    auth = _bi_mat(db, str(params.get(THAM_SO_CREDENTIAL) or ""), owner_id,
                   run_id=str(meta.get("run_id") or ""),
                   node_id=str(meta.get("node_id") or ""))
    kq = _connector.chay(
        str(meta.get("op") or "run_action"),
        piece=str(meta["piece"]), version=str(meta["piece_version"]),
        name=str(meta["name"]), props=props, auth=auth,
        store=_store.doc(db, owner_id=owner_id, pham_vi=pham_vi),
        run_id=str(meta.get("run_id") or ""))
    if kq.store_ops:
        # Spec §11.4: áp trong cùng transaction đóng job. `db` ở đây LÀ phiên
        # của handler, và `job_runner` commit nó khi job kết thúc.
        _store.ap(db, owner_id=owner_id, pham_vi=pham_vi, ops=kq.store_ops)
    if not kq.ok:
        raise LoiHandler(f"{kq.ma_loi}: {kq.thong_diep}"[:2000])
    return {"output": kq.output, "files": kq.files, "_do": kq.do}


def _chay_youtube(db, params: dict, meta: dict) -> dict:
    """`connector.youtube.upload` — xem `platform_core/workflow/youtube_upload.py`.

    🔴 `side_effect = irreversible`: URL phiên resumable được LƯU **trước** khi
       gửi byte đầu tiên, nên một lần thử lại nối tiếp phiên cũ thay vì mở
       phiên mới. Đó là khác biệt giữa "thử lại an toàn" và "đăng hai video".
    """
    import httpx

    from platform_core.workflow import youtube_upload as yt

    owner_id = str(params.get("owner_id") or "")
    run_id = str(meta.get("run_id") or "")
    pham_vi = _store.pham_vi_run(run_id)
    khoa_phien = f"yt:phien:{meta.get('node_id') or ''}"
    goi = _bi_mat(db, str(params.get(THAM_SO_CREDENTIAL) or ""), owner_id,
                  run_id=run_id, node_id=str(meta.get("node_id") or ""))
    token = (goi or {}).get("access_token") if isinstance(goi, dict) else goi
    if not token:
        raise LoiHandler("credential_loi: thieu access_token cua Google")

    du_lieu = _doc_artifact(db, owner_id, str(params.get("video") or ""))
    cu = _store.doc(db, owner_id=owner_id, pham_vi=pham_vi)
    phien_url = str(cu.get(khoa_phien) or "")
    with httpx.Client(timeout=120.0) as client:
        if not phien_url:
            phien_url = yt.mo_phien(
                client, access_token=str(token), so_byte=len(du_lieu),
                title=str(params.get("title") or ""),
                description=str(params.get("description") or ""),
                tags=params.get("tags") or [],
                privacy=str(params.get("privacy") or "private"),
                category_id=str(params.get("category_id") or ""),
                publish_at=str(params.get("publish_at") or ""))
            # ⭐ LƯU TRƯỚC KHI GỬI BYTE. Một lần mất điện ngay sau `mo_phien`
            #    mà chưa lưu thì lần thử lại mở phiên thứ hai — tức hai video.
            _store.ap(db, owner_id=owner_id, pham_vi=pham_vi,
                      ops=[{"op": "put", "key": khoa_phien, "value": phien_url}])
            db.commit()
        kq = yt.upload(client, access_token=str(token), du_lieu=du_lieu,
                       phien_url=phien_url)
    _store.ap(db, owner_id=owner_id, pham_vi=pham_vi,
              ops=[{"op": "delete", "key": khoa_phien}])
    return {"video_id": kq.video_id, "status": kq.status,
            "da_noi_lai": kq.da_noi_lai}


def _doc_artifact(db, owner_id: str, ref: str) -> bytes:
    if not ref:
        raise LoiHandler("dau_vao_sai: thieu artifact_ref cua video")
    from platform_core import storage
    from platform_core.models import Artifact

    a = db.get(Artifact, ref)
    if a is None or str(a.owner_id) != owner_id:
        # ⛔ Kiểm chủ sở hữu, ⛔ không chỉ "có tồn tại": một `artifact_ref`
        #    đoán được của người khác là một đường đọc tệp của người khác.
        raise LoiHandler(f"dau_vao_sai: artifact {ref!r} khong thuoc ve ban")
    # 🔴 `Storage` KHONG co `.get` — giao dien la `.open(key) -> BinaryIO`
    #    (`platform_core/storage.py:68`). Ban cu nem `AttributeError` o
    #    dung duong doc artifact dau vao cua job connector, va bo test
    #    khong thay vi khong bai nao di qua day voi mot artifact that.
    with storage.get_storage().open(a.key) as f:
        return f.read()


def handle(params: dict, ctx=None) -> dict:
    meta = dict((params or {}).get("_connector") or {})
    if not meta:
        raise LoiHandler("loi_he_thong: job connector thieu `_connector`")
    loai = str(meta.get("node_type") or "")
    # 🔴 `get_session()` la mot GENERATOR (kieu dependency cua FastAPI), khong
    #    phai context manager. `with get_session() as db:` nem
    #    `TypeError: 'generator' object does not support the context manager
    #    protocol` — tuc CUA VAO nay chet ngay dong dau, cho MOI job connector.
    #
    # ⛔ Bo test cu khong thay vi moi bai goi THANG `_chay_youtube`/`_chay_piece`.
    #    Chung do phan ben trong va bo qua dung cai cua production di qua.
    #    `test_3504::test_CUA_VAO_handle_mo_duoc_phien_CSDL` nay chot cho do.
    #
    # ⭐ Dung khuon san co cua kho (`runtime_noi_bo/luong.py::_phien_moi`):
    #    lay generator, `next()` de co phien, va `finally` de dong.
    gen = get_session()
    db = next(gen)
    try:
        if loai == "connector.youtube.upload":
            return _chay_youtube(db, params, meta)
        return _chay_piece(db, params, meta)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _kich_thuoc(x) -> int:
    return len(json.dumps(x, default=str))


__all__ = ["LoiHandler", "THAM_SO_CREDENTIAL", "handle"]
