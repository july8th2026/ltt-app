"""Handler chạy trong worker (spec §14, §17–§20). Không bao giờ chạy trong request.

Hai job:
- `video_crawler.kham_pha`: khám phá (xem trước), không tải, miễn phí.
- `video_crawler.tai`: tải danh sách mục đã chọn, hoặc "cào hết" theo nguồn (khám phá rồi tải).

Quy tắc tiền của nền tảng (docs/03_THEM_APP_MOI.md §2): thất bại thì NÉM, không trả êm.
- Lỗi phía khách ở mọi mục ⇒ `LoiNguoiGoi` (không thử lại, hoàn đủ).
- Lỗi tạm thời ⇒ exception thường (nền tảng thử lại).
- Xong một phần ⇒ hoàn tất, báo `credit_cost` = số tải được, phần còn lại được hoàn.
Thoát bằng exception (kể cả huỷ) ⇒ xoá tệp đã lưu của job này: dọn job hết hạn chỉ quét `result` (spec §18).
"""
from __future__ import annotations

import importlib
import tempfile
import time
from pathlib import Path

from apps.video_crawler import nen_tang
from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao

JOB_KHAM_PHA = "video_crawler.kham_pha"
JOB_TAI = "video_crawler.tai"

#: Nhịp tim tối thiểu: ngưỡng mồ côi của nền tảng là 5 phút (platform_core/jobs.py ORPHAN_TIMEOUT).
_NHIP_TIM_S = 30.0
#: Bước tiến độ (%).
_BUOC = 5


def _adapter(nen_id: str):
    """Adapter của nền, tra qua registry (`NenTang.adapter` = tên module trong adapters/)."""
    ten = nen_tang.lay_nen_bat(nen_id).adapter
    mod = importlib.import_module(f"apps.video_crawler.adapters.{ten}")
    for v in vars(mod).values():
        if isinstance(v, type) and getattr(v, "nen_tang", None) == nen_id and hasattr(v, "tai"):
            return v()
    raise RuntimeError(f"adapter {ten!r} không khai lớp cho nền {nen_id!r}")


def _loi_job(ds: list[LoiCao]) -> Exception:
    """Một exception đại diện cho job thất bại hoàn toàn."""
    from platform_core.jobs import LoiNguoiGoi
    if any(e.tam_thoi for e in ds):
        tam = next(e for e in ds if e.tam_thoi)
        return RuntimeError(f"{tam.ma}: {tam.thong_diep}")
    return LoiNguoiGoi(ds[0].thong_diep)


class _TienDo:
    """Gộp tiến độ từng mục thành % của cả job. Gọi ctx.progress khi % đổi hoặc quá nhịp tim.

    ctx.progress là nơi nền tảng báo huỷ (ném JobCancelled) — nên mọi tiến độ adapter đi qua đây.
    """

    def __init__(self, ctx, tong: int, *, tran: int = 95):
        self.ctx = ctx
        self.tong = max(tong, 1)
        self.tran = tran
        self.i = 0
        self._pct = -1
        self._luc = 0.0

    def bao(self, phan_tram: int, thong_diep: str = "") -> None:
        """Đơn điệu + bước 5%. yt-dlp tải luồng hình rồi luồng tiếng, mỗi luồng đếm lại từ 0 — không chặn
        thì thanh tiến độ giật lùi và mỗi % thành một dòng lịch sử job (kiểm GUI 22/09)."""
        if self.ctx is None:
            return
        p = max(0, min(int(phan_tram), 100))
        tong_pct = int((self.i + p / 100) / self.tong * self.tran) // _BUOC * _BUOC
        bay_gio = time.monotonic()
        if tong_pct > self._pct:
            self._pct, self._luc = tong_pct, bay_gio
            self.ctx.progress(tong_pct, thong_diep[:200])
        elif bay_gio - self._luc >= _NHIP_TIM_S:          # nhịp tim (ngưỡng mồ côi 5 phút), không đổi %
            self._luc = bay_gio
            self.ctx.progress(max(self._pct, 0), thong_diep[:200])


def _su_kien(ctx, ma: str, thong_diep: str) -> None:
    if ctx is not None:
        from platform_core import job_events
        ctx.event(ma, thong_diep, visibility=job_events.CUSTOMER)


def _da_tai(owner_id: str, nen_id: str) -> set[str]:
    from apps.video_crawler import features
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        return features.da_tai_ids(db, owner_id, nen_id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _kham_pha(adapter, nen_id: str, nguon: dict, owner_id: str, tien_do) -> tuple[list[CrawlItem], int]:
    yc = YeuCauCao(nen_tang=nen_id, che_do=nguon["che_do"], dau_vao=nguon["dau_vao"],
                   so_luong=int(nguon["so_luong"]))
    try:
        muc = adapter.kham_pha(yc, bao_tien_do=tien_do)
    except LoiCao as e:
        raise _loi_job([e]) from e
    bo = 0
    if nguon.get("khong_trung"):
        cu = _da_tai(owner_id, nen_id)
        giu = [m for m in muc if m.id not in cu]
        bo, muc = len(muc) - len(giu), giu
    return muc[: yc.so_luong], bo


def _xu_ly_kham_pha(params: dict, ctx) -> dict:
    adapter = _adapter(params["nen_tang"])
    td = _TienDo(ctx, 1)
    muc, bo = _kham_pha(adapter, params["nen_tang"], params, params["owner_id"], td.bao)
    if ctx is not None:
        ctx.progress(100, f"Tìm thấy {len(muc)} video")
    return {"muc": [m.to_dict() for m in muc], "bo_qua_trung": bo}


def _xu_ly_tai(params: dict, ctx) -> dict:
    from platform_core.storage import get_storage

    nen_id, owner_id = params["nen_tang"], params["owner_id"]
    job_id = getattr(ctx, "job_id", "") or "khong-ctx"
    adapter = _adapter(nen_id)
    bo = 0
    if params.get("nguon"):
        muc, bo = _kham_pha(adapter, nen_id, params["nguon"], owner_id, _TienDo(ctx, 1, tran=5).bao)
    else:
        muc = [CrawlItem(nen_tang=nen_id, id=m["id"], url=m["url"], tieu_de=m.get("tieu_de", ""))
               for m in params["muc"]]
    if not muc:
        if bo:   # mọi mục đều đã tải trước đó: hoàn tất, KHÔNG tính tiền, và nói rõ (kiểm GUI 22/09)
            _su_kien(ctx, "bo_qua_trung", f"Bỏ qua {bo} video đã tải trước đó")
            if ctx is not None:
                ctx.progress(100, f"Không có video mới — bỏ qua {bo} video đã tải trước đó")
            return {"muc": [], "video_keys": [], "loi": [], "bo_qua_trung": bo, "credit_cost": 0}
        from platform_core.jobs import LoiNguoiGoi
        raise LoiNguoiGoi("Không tìm thấy video nào.")

    kho = get_storage()
    td = _TienDo(ctx, len(muc))
    xong: list[dict] = []
    loi: list[LoiCao] = []
    loi_muc: list[dict] = []
    da_luu: list[str] = []
    try:
        for i, item in enumerate(muc):
            td.i = i
            if ctx is not None and ctx.is_cancelled():
                from platform_core.job_runner import JobCancelled
                raise JobCancelled()
            key = f"video_crawler/{owner_id}/{job_id}/{item.id}.mp4"
            try:
                if not kho.exists(key):          # lượt thử lại: mục đã lưu thì không tải lại
                    with tempfile.TemporaryDirectory(prefix="vc_") as tam:
                        tep = adapter.tai(item, Path(tam), bao_tien_do=td.bao)
                        with open(tep.duong_dan, "rb") as f:
                            kho.put(key, f, content_type="video/mp4")
                        ten = tep.ten_hien_thi
                else:
                    ten = f"{item.tieu_de[:80]} [{item.id}].mp4"
                da_luu.append(key)
            except LoiCao as e:
                loi.append(e)
                loi_muc.append({"id": item.id, "ma": e.ma, "thong_diep": e.thong_diep})
                _su_kien(ctx, "muc_loi", f"{item.tieu_de or item.id}: {e.thong_diep}")
                continue
            xong.append({**item.to_dict(), "tep": key, "ten_tep": ten, "kich_thuoc": kho.size(key)})
            _su_kien(ctx, "muc_xong", f"Đã tải {item.tieu_de or item.id}")
        if not xong:
            raise _loi_job(loi)
        if ctx is not None:                    # trong khối dọn: huỷ đúng lúc này vẫn không để tệp mồ côi
            ctx.progress(100, f"Xong: {len(xong)}/{len(muc)} video")
    except BaseException:
        for k in da_luu:
            try:
                kho.delete(k)
            except Exception:  # noqa: BLE001 — dọn best-effort, lỗi gốc mới là thứ cần báo
                pass
        raise
    if bo:
        _su_kien(ctx, "bo_qua_trung", f"Bỏ qua {bo} video đã tải trước đó")
    return {"muc": xong, "video_keys": [m["tep"] for m in xong], "loi": loi_muc,
            "bo_qua_trung": bo, "credit_cost": len(xong)}


def handle(params: dict, ctx=None) -> dict:
    loai = getattr(ctx, "job_type", "") or (JOB_TAI if ("muc" in params or "nguon" in params) else JOB_KHAM_PHA)
    if loai == JOB_KHAM_PHA:
        return _xu_ly_kham_pha(params, ctx)
    if loai == JOB_TAI:
        return _xu_ly_tai(params, ctx)
    raise RuntimeError(f"video_crawler không nhận job_type {loai!r}")
