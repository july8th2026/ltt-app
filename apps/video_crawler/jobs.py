"""Handler chạy trong worker (spec §14, §17–§20). Không bao giờ chạy trong request.

Hai job:
- `video_crawler.kham_pha`: khám phá (xem trước), không tải, miễn phí.
- `video_crawler.tai`: tải danh sách mục đã chọn, hoặc "cào hết" theo nguồn (khám phá rồi tải).

Quy tắc tiền của nền tảng (docs/03_THEM_APP_MOI.md §2): thất bại thì NÉM, không trả êm.
- Lỗi phía khách ở mọi mục ⇒ `LoiNguoiGoi` (không thử lại, hoàn đủ).
- Lỗi tạm thời ⇒ exception thường (nền tảng thử lại).
- Xong một phần ⇒ hoàn tất, báo `credit_cost` = số tải được, phần còn lại được hoàn.
Thoát bằng exception (kể cả huỷ) ⇒ xoá tệp đã lưu của job này: dọn job hết hạn chỉ quét `result` (spec §18).

Dedup bền (Q4, bảng `vc_da_tai`): GIÀNH chỗ (owner, nền, video) trước khi tải từng mục — job khác của cùng user đang
giữ ⇒ mục đó bỏ qua như "trùng", không tính tiền. Xong ⇒ 'xong' + storage key; thoát bằng exception ⇒ nhả chỗ cùng lúc
với dọn tệp.
"""
from __future__ import annotations

import contextlib
import logging
import random
import tempfile
import time
from pathlib import Path

from platform_core.i18n import _ as _t

from apps.video_crawler import gia, nen_tang
from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao

JOB_KHAM_PHA = "video_crawler.kham_pha"
JOB_TAI = "video_crawler.tai"
_LOG = logging.getLogger(__name__)
#: Nghỉ ngẫu nhiên GIỮA hai video của một job tải (yt-dlp wiki: 5–10 s giữa lượt tải; N7). Mục đầu không chờ.
NGHI_GIUA_MUC_S = (5.0, 10.0)
_ngu = time.sleep          # test thay hàm này

#: Nhịp tim tối thiểu: ngưỡng mồ côi của nền tảng là 5 phút (platform_core/jobs.py ORPHAN_TIMEOUT).
_NHIP_TIM_S = 30.0
#: Bước tiến độ (%).
_BUOC = 5
#: Hỏi "đã huỷ chưa" ít nhất chừng này giây một lần, kể cả khi % đứng yên (review MAJOR 4).
_KIEM_HUY_S = 5.0
#: Ngân sách thời gian job tải: dừng giữa các mục khi quá mốc này, dừng cứng khi quá thêm 300 s.
#: Trần nền tảng 7200 s; chạm trần thì `_het_gio` GIẾT tiến trình ⇒ khối dọn tệp không chạy (review MAJOR 5).
NGAN_SACH_TAI_S = 6600.0


def _adapter(nen_id: str):
    """Adapter của nền (test thay hàm này bằng adapter giả)."""
    from apps.video_crawler import adapters
    return adapters.tao(nen_id)


@contextlib.contextmanager
def _phien(adapter, owner_id: str, nen_id: str):
    """Đặt `adapter.tep_cookie` = cookies.txt TẠM của đúng chủ job (nếu có phiên) trong suốt job; xoá khi ra.

    Cookie chỉ đi: DB (mã hoá) → tệp tạm quyền 600 trong thư mục job → yt-dlp. Không vào params/result/sự kiện.
    """
    nen = nen_tang.lay(nen_id)
    if not nen.cookie_dang_nhap or not hasattr(adapter, "tep_cookie"):
        yield
        return
    from apps.video_crawler import phien
    from platform_core.db import get_session
    phien.don_tam_cu(Path(tempfile.gettempdir()))    # thư mục của job bị `_het_gio` giết (review lần 2)
    with tempfile.TemporaryDirectory(prefix="vc_phien_") as tam:
        gen = get_session(); db = next(gen)
        try:
            ql = phien.tep_cookie_tam(db, owner_id=owner_id, nen_tang=nen_id, thu_muc=Path(tam))
            duong = ql.__enter__()
        finally:
            with contextlib.suppress(StopIteration):
                next(gen)
        try:
            adapter.tep_cookie = str(duong) if duong else None
            yield
        finally:
            adapter.tep_cookie = None
            ql.__exit__(None, None, None)


def _loi_job(ds: list[LoiCao]) -> Exception:
    """Một exception đại diện cho job thất bại hoàn toàn."""
    from platform_core.jobs import LoiNguoiGoi
    if any(e.tam_thoi for e in ds):
        tam = next(e for e in ds if e.tam_thoi)
        return RuntimeError(_t("{ma}: {thong_diep}").format(ma=tam.ma, thong_diep=tam.thong_diep))
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
        self.bat_dau = time.monotonic()
        self._luc_huy = self.bat_dau

    def bao(self, phan_tram: int, thong_diep: str = "") -> None:
        """Đơn điệu + bước 5%. yt-dlp tải luồng hình rồi luồng tiếng, mỗi luồng đếm lại từ 0 — không chặn
        thì thanh tiến độ giật lùi và mỗi % thành một dòng lịch sử job (kiểm GUI 22/09)."""
        if self.ctx is None:
            return
        p = max(0, min(int(phan_tram), 100))
        tong_pct = int((self.i + p / 100) / self.tong * self.tran) // _BUOC * _BUOC
        bay_gio = time.monotonic()
        if bay_gio - self.bat_dau > NGAN_SACH_TAI_S + 300:
            from platform_core.jobs import LoiNguoiGoi
            raise LoiNguoiGoi(_t("Video quá dài để xử lý trong một lượt."))
        if bay_gio - self._luc_huy >= _KIEM_HUY_S and hasattr(self.ctx, "is_cancelled"):
            self._luc_huy = bay_gio
            if self.ctx.is_cancelled():
                from platform_core.job_runner import JobCancelled
                raise JobCancelled()
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


def _voi_db(ham, *args, **kw):
    """Gọi `ham(db, ...)` của `features` trên một phiên DB riêng, ngắn (worker không giữ phiên suốt job)."""
    from apps.video_crawler import features
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        return getattr(features, ham)(db, *args, **kw)
    finally:
        with contextlib.suppress(StopIteration):
            next(gen)


def _da_tai(owner_id: str, nen_id: str, job_id: str | None = None) -> set[str]:
    return _voi_db("da_tai_ids", owner_id, nen_id, tru_job_id=job_id)


def _kham_pha(adapter, nen_id: str, nguon: dict, owner_id: str, tien_do,
              job_id: str | None = None) -> tuple[list[CrawlItem], int]:
    yc = YeuCauCao(nen_tang=nen_id, che_do=nguon["che_do"], dau_vao=nguon["dau_vao"],
                   so_luong=int(nguon["so_luong"]))
    try:
        muc = adapter.kham_pha(yc, bao_tien_do=tien_do)
    except LoiCao as e:
        raise _loi_job([e]) from e
    import re
    from apps.video_crawler.adapters.base import ID_AN_TOAN
    muc = [m for m in muc if re.fullmatch(ID_AN_TOAN, str(m.id))]   # id làm khoá storage (review lần 2)
    muc = list({m.id: m for m in muc}.values())      # trùng id trong kết quả ⇒ một mục (review MAJOR 2)
    bo = 0
    if nguon.get("khong_trung"):
        cu = _da_tai(owner_id, nen_id, job_id)
        giu = [m for m in muc if m.id not in cu]
        bo, muc = len(muc) - len(giu), giu
    return muc[: yc.so_luong], bo


def _xu_ly_kham_pha(params: dict, ctx) -> dict:
    adapter = _adapter(params["nen_tang"])
    td = _TienDo(ctx, 1)
    with _phien(adapter, params["owner_id"], params["nen_tang"]):
        muc, bo = _kham_pha(adapter, params["nen_tang"], params, params["owner_id"], td.bao)
    if ctx is not None:
        ctx.progress(100, _t("Tìm thấy {n} video").format(n=len(muc)))
    return {"muc": [m.to_dict() for m in muc], "bo_qua_trung": bo}


def _xu_ly_tai(params: dict, ctx) -> dict:
    adapter = _adapter(params["nen_tang"])
    with _phien(adapter, params["owner_id"], params["nen_tang"]):
        return _tai_voi(adapter, params, ctx)


def _tai_voi(adapter, params: dict, ctx) -> dict:
    from platform_core.storage import get_storage

    nen_id, owner_id = params["nen_tang"], params["owner_id"]
    job_id = getattr(ctx, "job_id", "") or "khong-ctx"
    bo = 0
    if params.get("nguon"):
        muc, bo = _kham_pha(adapter, nen_id, params["nguon"], owner_id, _TienDo(ctx, 1, tran=5).bao, job_id)
    else:
        # `thoi_luong_s` giữ nguyên nếu params đã có (ví dụ mục lấy từ kết quả khám phá) — quyết toán giá
        # đúng theo thời lượng thật; features.dung_params_tai hiện chưa giữ trường này qua danh sách id
        # thô của khách (CONTRACT GAP — xem báo cáo), nên đường đó vẫn rơi về bậc rẻ nhất qua `gia.gia_muc`.
        muc = [CrawlItem(nen_tang=nen_id, id=m["id"], url=m["url"], tieu_de=m.get("tieu_de", ""),
                         thoi_luong_s=m.get("thoi_luong_s"))
               for m in params["muc"]]
    if not muc:
        if bo:   # mọi mục đều đã tải trước đó: hoàn tất, KHÔNG tính tiền, và nói rõ (kiểm GUI 22/09)
            _su_kien(ctx, "bo_qua_trung", _t("Bỏ qua {n} video đã tải trước đó").format(n=bo))
            if ctx is not None:
                ctx.progress(100, _t("Không có video mới — bỏ qua {n} video đã tải trước đó").format(n=bo))
            return {"muc": [], "video_keys": [], "loi": [], "bo_qua_trung": bo, "credit_cost": 0}
        from platform_core.jobs import LoiNguoiGoi
        raise LoiNguoiGoi(_t("Không tìm thấy video nào."))

    kho = get_storage()
    td = _TienDo(ctx, len(muc))
    xong: list[dict] = []
    loi: list[LoiCao] = []
    loi_muc: list[dict] = []
    da_luu: list[str] = []
    so_da_tai = 0                  # số mục đã thực sự tải (nhịp nghỉ N7 chỉ giữa hai lượt tải thật)
    try:
        for i, item in enumerate(muc):
            td.i = i
            if time.monotonic() - td.bat_dau > NGAN_SACH_TAI_S:
                for con in muc[i:]:
                    loi_muc.append({"id": con.id, "ma": "het_thoi_gian",
                                    "thong_diep": _t("Hết thời gian của lượt này, cào lại để lấy phần còn lại.")})
                loi.append(LoiCao("het_thoi_gian", _t("Hết thời gian xử lý."), tam_thoi=False))
                break
            if ctx is not None and ctx.is_cancelled():
                from platform_core.job_runner import JobCancelled
                raise JobCancelled()
            key = f"video_crawler/{owner_id}/{job_id}/{item.id}.mp4"
            if not _voi_db("gianh_cho", owner_id, nen_id, item.id, job_id, tep_con=kho.exists):
                bo += 1                         # job khác của chính user này đang/đã tải video này
                _su_kien(ctx, "muc_trung", _t("{ten}: đã hoặc đang được tải ở lượt khác của bạn — bỏ qua")
                         .format(ten=item.tieu_de or item.id))
                continue
            try:
                if not kho.exists(key):
                    if so_da_tai > 0:
                        _ngu(random.uniform(*NGHI_GIUA_MUC_S))          # lượt thử lại: mục đã lưu thì không tải lại
                    so_da_tai += 1
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
            _su_kien(ctx, "muc_xong", _t("Đã tải {ten}").format(ten=item.tieu_de or item.id))
        if not xong and loi:
            raise _loi_job(loi)
        if ctx is not None:                    # trong khối dọn: huỷ đúng lúc này vẫn không để tệp mồ côi
            ctx.progress(100, f"Xong: {len(xong)}/{len(muc)} video" if xong else
                         _t("Không có video mới — bỏ qua {n} video đã tải trước đó").format(n=bo))
        _voi_db("danh_dau_xong", owner_id, job_id, {m["id"]: m["tep"] for m in xong})
    except BaseException:
        try:
            _voi_db("nha_cho", owner_id, job_id)
        except Exception as loi_nha:  # noqa: BLE001 — best-effort như dọn tệp; dòng mồ côi hết hạn sau 3 giờ
            _LOG.warning("video_crawler: không nhả được chỗ của job %s: %s", job_id, type(loi_nha).__name__)
        for k in da_luu:
            try:
                kho.delete(k)
            except Exception as loi_don:  # noqa: BLE001 — dọn best-effort; lỗi gốc mới là thứ cần báo
                _LOG.warning(_t("video_crawler: không dọn được tệp %s: %s"), k, type(loi_don).__name__)
        raise
    if bo:
        _su_kien(ctx, "bo_qua_trung", _t("Bỏ qua {n} video đã tải trước đó").format(n=bo))
    # Quyết toán theo thời lượng THẬT của từng mục đã tải (một nguồn giá: apps/video_crawler/gia.py),
    # không phải số mục — giữ chỗ ở manifest._gia luôn bậc cao nhất, phần chênh nền tảng tự hoàn.
    tong_gia = sum(gia.gia_muc(m.get("thoi_luong_s")) for m in xong)
    return {"muc": xong, "video_keys": [m["tep"] for m in xong], "loi": loi_muc,
            "bo_qua_trung": bo, "credit_cost": tong_gia}


def handle(params: dict, ctx=None) -> dict:
    loai = getattr(ctx, "job_type", "") or (JOB_TAI if ("muc" in params or "nguon" in params) else JOB_KHAM_PHA)
    if loai == JOB_KHAM_PHA:
        return _xu_ly_kham_pha(params, ctx)
    if loai == JOB_TAI:
        return _xu_ly_tai(params, ctx)
    raise RuntimeError(_t("video_crawler không nhận job_type {loai!r}").format(loai=loai))
