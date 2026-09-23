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

#: Ngân sách TỔNG cho ảnh bìa của một job khám phá (W2-L8) — một trang có tới 20 mục, CDN chậm không được
#: kéo dài job khám phá (đã miễn phí, khách chờ trực tiếp). Hết ngân sách ⇒ mục còn lại giữ URL CDN gốc
#: (route vẫn phục vụ được qua nhánh "cách cũ" của `anh_bia.doc`), không phải lỗi.
NGAN_SACH_ANH_BIA_S = 20.0


def _adapter(nen_id: str):
    """Adapter của nền (test thay hàm này bằng adapter giả)."""
    from apps.video_crawler import adapters
    return adapters.tao(nen_id)


class _NguonPhien:
    """Job này đăng nhập bằng gì: `rieng` (phiên của khách), `kho` (tài khoản hệ thống), `""` (ẩn danh).

    ⛔ `tai_khoan_id` KHÔNG được đi vào `result`/`params`/log — chỉ vào sự kiện INTERNAL. Khách không bao giờ
       biết, tải về hay nhìn thấy tài khoản nào đã phục vụ lượt của họ (THIET_KE_PHIEN_VA_KENH §2.2.4).
    """

    def __init__(self):
        self.nguon = ""
        self.tai_khoan_id = ""
        self.ma_loi: str | None = None
        #: Thân job thoát bằng exception (kể cả huỷ) ⇒ KHÔNG cộng điểm cho tài khoản kho.
        self.hong = False

    def ghi_ket_qua(self, ket_qua: dict | None) -> None:
        """Lấy mã lỗi NẶNG nhất của các mục hỏng để chấm điểm tài khoản kho.

        Job xong-một-phần không ném gì cả: vài mục `can_dang_nhap` là cái chết của tài khoản kho, và nhìn
        exception thôi thì cái chết ấy không bao giờ được ghi nhận.
        """
        if self.nguon != "kho" or self.ma_loi:
            return
        from apps.video_crawler import kho_tai_khoan
        self.ma_loi = kho_tai_khoan.ma_tu_ket_qua(ket_qua)


@contextlib.contextmanager
def _phien(adapter, owner_id: str, nen_id: str, *, ctx=None):
    """Đặt `adapter.tep_cookie` = cookies.txt TẠM cho suốt job; xoá khi ra. Trả `_NguonPhien` của lượt này.

    Thứ tự chọn nguồn (THIET_KE_PHIEN_VA_KENH §2.2, chủ dự án duyệt 23/09):
    1. phiên RIÊNG của khách cho nền đó ⇒ dùng (khách đứng tên lượt tải của chính họ);
    2. không có, nền có kho ⇒ MƯỢN một tài khoản hệ thống (LTT đứng tên) — hết chỗ ⇒ `DangBan` (về hàng đợi,
       không tiêu lượt, không chạm tiền); kho không còn tài khoản sống ⇒ `LoiNguoiGoi` (hoàn tiền);
    3. nền không có kho ⇒ chạy ẩn danh như trước.

    Cookie chỉ đi: DB (mã hoá) → tệp tạm quyền 600 trong thư mục job → yt-dlp. Không vào params/result/sự kiện.
    """
    nen = nen_tang.lay(nen_id)
    trang = _NguonPhien()
    if not nen.cookie_dang_nhap or not hasattr(adapter, "tep_cookie"):
        yield trang
        return
    from apps.video_crawler import kho_tai_khoan, phien
    from platform_core.db import get_session
    phien.don_tam_cu(Path(tempfile.gettempdir()))    # thư mục của job bị `_het_gio` giết (review lần 2)
    job_id = (getattr(ctx, "job_id", "") or "") if ctx is not None else ""
    # `ExitStack` chứ không phải hai biến `ql`: `DangBan`/`LoiNguoiGoi` ném ra GIỮA lúc chọn nguồn cũng phải
    # đóng đúng những gì đã mở — một đường thoát không dọn là một tệp cookie nằm lại.
    with tempfile.TemporaryDirectory(prefix="vc_phien_") as tam, contextlib.ExitStack() as ngan:
        gen = get_session(); db = next(gen)
        muon = None
        try:
            duong = ngan.enter_context(
                phien.tep_cookie_tam(db, owner_id=owner_id, nen_tang=nen_id, thu_muc=Path(tam)))
            if duong is not None:
                trang.nguon = "rieng"
            elif kho_tai_khoan.nen_co_kho(nen_id):
                kho_tai_khoan.kiem_tran_khach(db, owner_id, nen_id)
                muon = kho_tai_khoan.muon(db, nen_id, owner_id=owner_id, job_id=job_id)
                if muon is None:
                    # Hai câu trả lời rất khác nhau: còn tài khoản nhưng hết CHỖ ⇒ đợi lượt sau; kho rỗng ⇒
                    # nói thật với khách và hoàn tiền, đừng để job quay vòng tới khi hết lượt thử.
                    if kho_tai_khoan.con_tai_khoan_song(db, nen_id):
                        from platform_core.jobs import DangBan
                        raise DangBan(_t("Tài khoản hệ thống của nền này đang bận — lượt của bạn sẽ chạy "
                                         "ngay khi có chỗ."))
                    raise kho_tai_khoan.loi_kho_rong(nen_id)
                duong = ngan.enter_context(kho_tai_khoan.tep_cookie_tam(db, muon, thu_muc=Path(tam)))
                trang.nguon, trang.tai_khoan_id = "kho", muon.tai_khoan_id
                _su_kien_noi_bo(ctx, "phien_kho",
                                f"nguon_phien=kho tai_khoan={muon.tai_khoan_id} nhan={muon.nhan}")
        finally:
            with contextlib.suppress(StopIteration):
                next(gen)
        try:
            adapter.tep_cookie = str(duong) if duong else None
            yield trang
        except BaseException as e:
            trang.hong = True
            if trang.ma_loi is None:
                trang.ma_loi = kho_tai_khoan.ma_tu_loi(e)
            raise
        finally:
            adapter.tep_cookie = None
            if muon is not None:
                _tra_kho(muon, trang.ma_loi, thanh_cong=not trang.hong)


def _tra_kho(muon, ma_loi: str | None, *, thanh_cong: bool = True) -> None:
    """Nhả chỗ + chấm điểm trên một phiên DB MỚI: phiên lúc mượn đã đóng từ đầu job (job tải chạy hàng giờ)."""
    from apps.video_crawler import kho_tai_khoan
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        kho_tai_khoan.tra(db, muon, ma_loi=ma_loi, thanh_cong=thanh_cong)
    finally:
        with contextlib.suppress(StopIteration):
            next(gen)


def _su_kien_noi_bo(ctx, ma: str, thong_diep: str) -> None:
    """Sự kiện chỉ vận hành đọc được. Đây là chỗ DUY NHẤT id tài khoản kho được ghi lại."""
    if ctx is not None:
        from platform_core import job_events
        ctx.event(ma, thong_diep, visibility=job_events.INTERNAL)


def _loi_job(ds: list[LoiCao]) -> Exception:
    """Một exception đại diện cho job thất bại hoàn toàn."""
    from platform_core.jobs import LoiNguoiGoi
    if any(e.tam_thoi for e in ds):
        tam = next(e for e in ds if e.tam_thoi)
        e = RuntimeError(_t("{ma}: {thong_diep}").format(ma=tam.ma, thong_diep=tam.thong_diep))
        # Tạm thời ⇒ PHẢI được thử lại ⇒ không thể là `LoiNguoiGoi`; nhưng hết lượt thì khách vẫn nên đọc
        # câu đã soạn chứ không phải câu chung (`platform_core.jobs.mo_ta_loi` mang nó qua `Job.error`).
        e.cau_khach = tam.thong_diep
        return e
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


def _luu_anh_bia(muc: list[CrawlItem], *, owner_id: str, job_id: str, nen_id: str) -> list[dict]:
    """`m.to_dict()` của mỗi mục; ảnh bìa (nếu có) đã tải và LƯU vào storage bằng `anh_bia.luu_kham_pha`
    (W2-L8). Một ảnh lỗi ⇒ mục đó GIỮ url CDN gốc (không hỏng job); tổng thời gian tải ảnh có trần
    `NGAN_SACH_ANH_BIA_S` — hết ngân sách thì các mục còn lại cũng giữ url gốc, không thử tải nữa."""
    from apps.video_crawler import anh_bia
    bat_dau = time.monotonic()
    ra: list[dict] = []
    for i, m in enumerate(muc):
        d = m.to_dict()
        if d.get("anh_bia") and time.monotonic() - bat_dau < NGAN_SACH_ANH_BIA_S:
            try:
                key = anh_bia.luu_kham_pha(d["anh_bia"], nen_tang=nen_id, owner_id=owner_id,
                                           job_id=job_id, chi_so=i)
            except Exception as e:  # noqa: BLE001 — `luu_kham_pha` không tự ném, nhưng phòng lỗi bất ngờ
                _LOG.warning("video_crawler: loi bat ngo khi luu anh bia muc %s: %s", i, type(e).__name__)
                key = None
            if key:
                d["anh_bia"] = key
        ra.append(d)
    return ra


def _xu_ly_kham_pha(params: dict, ctx) -> dict:
    adapter = _adapter(params["nen_tang"])
    td = _TienDo(ctx, 1)
    with _phien(adapter, params["owner_id"], params["nen_tang"], ctx=ctx) as p:
        muc, bo = _kham_pha(adapter, params["nen_tang"], params, params["owner_id"], td.bao)
    job_id = getattr(ctx, "job_id", "") or "khong-ctx"
    muc_dict = _luu_anh_bia(muc, owner_id=params["owner_id"], job_id=job_id, nen_id=params["nen_tang"])
    if ctx is not None:
        ctx.progress(100, _t("Tìm thấy {n} video").format(n=len(muc)))
    # `nguon_phien` là "rieng" | "kho" | "" — KHÔNG bao giờ kèm tài khoản nào (id chỉ ở sự kiện INTERNAL).
    return {"muc": muc_dict, "bo_qua_trung": bo, "nguon_phien": p.nguon}


def _xu_ly_tai(params: dict, ctx) -> dict:
    adapter = _adapter(params["nen_tang"])
    with _phien(adapter, params["owner_id"], params["nen_tang"], ctx=ctx) as p:
        ra = _tai_voi(adapter, params, ctx)
        p.ghi_ket_qua(ra)          # mục hỏng vì `can_dang_nhap` ⇒ chấm điểm tài khoản kho trước khi trả chỗ
    return {**ra, "nguon_phien": p.nguon}


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
            _LOG.warning(_t("video_crawler: không nhả được chỗ của job %s: %s"), job_id, type(loi_nha).__name__)
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
