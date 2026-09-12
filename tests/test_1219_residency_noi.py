"""dual-model Task 5.5 — TRỌNG TÀI cư trú 3090: nối máy trạng thái vào sự thật.

`test_1216` chứng minh **luật** (hàm thuần), `test_1217` chứng minh **cửa**
(admission đọc dòng cư trú). Tệp này chứng minh thứ còn lại, và là thứ duy nhất
làm hai cái kia có ích: **có người bước máy** — đọc lease + hàng job + phòng chờ
+ máy B, ghi dòng `gpu_residency`, phát lệnh.

Bốn bất biến của cả chương trình được đo ở đây, và mỗi cái đi kèm một đối chứng
NGƯỢC CHIỀU, vì cả bốn đều xanh được bằng cách làm sai:

  · **Không lượt nào bị giết để đổi cư trú** ⇒ đối chứng: một lease 3.8 còn sống
    (hoặc gateway còn in-flight) thì **không** có lệnh `nha` nào, và lease ấy vẫn
    còn nguyên sau lượt bước. Không có vế sau thì "đổi cư trú xong" cũng xanh
    trong khi ta vừa cắt lượt của một khách đang chờ chữ.
  · **Máy B câm ⇒ KHÔNG chuyển trạng thái** ⇒ đối chứng: đúng bộ đầu vào ấy với
    máy B khoẻ thì máy **có** chuyển. Không có vế sau, một bản cài "không bao giờ
    chuyển gì" cũng xanh.
  · **Dòng phải được TẠO dù máy B câm** ⇒ đối chứng: trước lượt bước, cùng lượt
    xin 3.8 ấy bị `CHO_RESIDENCY`. Không có vế trước thì ta không chứng minh được
    lượt bước là thứ mở cửa, chỉ chứng minh cửa đang mở.
  · **Kẻ thua khoá lạc quan không làm gì** ⇒ đối chứng: bỏ phần "một trọng tài
    khác ghi trước" đi thì đúng lượt ấy phát đúng một lệnh `nha`.

⚠️ PHẠM VI, nói trước khi ai đó đọc rộng hơn: mọi thứ ở đây là **SQLite + một máy
   B giả**. Nên tệp này *không* đo: khoá advisory thật (SQLite bỏ qua
   `pg_advisory_xact_lock` — thứ tự khoá được đo bằng một phiên giả ghi lại lệnh,
   tức đo **công thức**, không đo tính loại trừ), hợp đồng HTTP thật của máy B
   (đó là `test_1218`), và VRAM thật.
"""
from __future__ import annotations

import ast
import logging
import pathlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import update

from apps.ltt_llm.ngan_sach import NHOM_CU_TRU_38, POOL_38, SO_SLOT, TAI_NGUYEN_38
from platform_core.llm import luat_nhan as L
from platform_core.llm import residency as R

GOC = pathlib.Path(__file__).resolve().parents[1]
NGUON = GOC / "platform_core" / "llm" / "residency.py"
T0 = datetime(2026, 9, 12, 9, 0, tzinfo=timezone.utc)
NHOM = NHOM_CU_TRU_38
TAI_NGUYEN_ANH = "anh_3090"
#: Ba app ảnh + bốn tool của chúng. Gõ ra ở đây có chủ ý: một app ảnh MỚI quên
#: khai cư trú sẽ không làm ca nào đỏ, nên danh sách này là chỗ người thêm app
#: phải đi qua (và `test_ba_manifest_anh_khai_dung_bo_ba` nói rõ vì sao).
APP_ANH = ("anhnoibo", "taoanh", "thumbnail")
JOB_ANH = "anhnoibo.generate"


class DongHo:
    """Đồng hồ tiêm, trả **giây epoch** — cùng gốc với `time.time` mà `buoc` dùng."""

    def __init__(self, t0: datetime = T0):
        self.t = t0.timestamp()

    def __call__(self) -> float:
        return self.t

    def tien(self, s: float) -> None:
        self.t += s

    def luc(self, lech: float = 0.0) -> datetime:
        return datetime.fromtimestamp(self.t + lech, timezone.utc)


class MayBGia:
    """Máy B giả: bốn phương thức của `MayBResidency`, không một dòng HTTP.

    ⭐ `nha()` tự đặt `llm_da_nap = False` vì **máy B thật làm thế**: sau một lượt
       `POST /api/models/unload/<model>` thì `/running` không còn hồ sơ ấy (L-17,
       đo 12/09 bước 2). Nhờ mô hình đúng chỗ này, câu "đúng MỘT lệnh `nha`" mới
       là một phép đo chứ không phải một sự trùng hợp: nếu trọng tài phát lại
       lệnh khi máy B đã nói xong, ca chu trình sẽ thấy hai.
    """

    def __init__(self) -> None:
        self.llm_da_nap: bool | None = True
        self.inflight: int | None = 0
        self.vram: int | None = 20_000
        self.nap_ket_qua = ""
        self.lenh: list[str] = []
        self.loi: Exception | None = None
        self.loi_comfy: Exception | None = None
        self.comfy_dang_chay = True
        self.so_lan_hoi = 0

    def trang_thai(self) -> R.TinMayB:
        self.so_lan_hoi += 1
        if self.loi is not None:
            raise self.loi
        return R.TinMayB(llm_da_nap=self.llm_da_nap, inflight_llm=self.inflight,
                         vram_3090_mib=self.vram, nap_ket_qua=self.nap_ket_qua)

    def nha(self) -> None:
        self.lenh.append(R.NHA_LLM_LENH)
        self.llm_da_nap = False

    def nap(self) -> None:
        self.lenh.append(R.NAP_LLM_LENH)
        self.nap_ket_qua = ""          # máy B đặt lại khi nhận lệnh mới (1216)

    def free_comfy(self) -> None:
        self.lenh.append(R.FREE_COMFY_LENH)
        self.comfy_dang_chay = False

    def chay_comfy(self) -> None:
        self.lenh.append("chay_comfy")
        if self.loi_comfy is not None:
            raise self.loi_comfy
        self.comfy_dang_chay = True


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'res55.db').as_posix()}")
    import platform_core.db as dbmod
    from platform_core.llm import admission

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    # Hai bộ đệm bản khai là trạng thái CẢ TIẾN TRÌNH: không xoá thì kết quả phụ
    # thuộc tệp nào chạy trước.
    admission.quen_ban_do_cu_tru()
    admission._da_nhac.clear()
    R.quen_ban_do_job()
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()
        admission.quen_ban_do_cu_tru()
        R.quen_ban_do_job()


@pytest.fixture()
def dh() -> DongHo:
    return DongHo()


@pytest.fixture()
def may_b() -> MayBGia:
    return MayBGia()


# ── Trợ giúp dựng sự thật ────────────────────────────────────────────────────

def _lease(db, resource: str, *, holder: str = "h", lop: str = "", job_id: str = ""):
    from platform_core.models import ExecutionLease

    ve = ExecutionLease(resource=resource, slot=0, user_id="u", mode="job",
                        holder_id=holder, job_id=job_id, lop=lop)
    db.add(ve)
    db.commit()
    return ve


def _nha_lease(db, resource: str) -> None:
    from platform_core.models import ExecutionLease

    for ve in db.query(ExecutionLease).filter(
            ExecutionLease.resource == resource).all():
        db.delete(ve)
    db.commit()


def _job(db, *, job_type: str = JOB_ANH, status: str = "queued",
         admitted_at: datetime | None = None, params: dict | None = None,
         tai_nguyen: str = ""):
    """Một dòng `jobs` như GIAO DIỆN nộp: `admission_resource` **rỗng**.

    🔴 Cột rỗng là sự thật của production, không phải một sự lười của phép kiểm:
       ba app ảnh nộp job qua `job_submit.submit_with_credit`, đường ấy không đi
       qua `registry.admission_luc_nop` nên nó không ghi cột. Xem
       `test_dem_job_anh_theo_ban_khai_khong_theo_cot`.
    """
    from platform_core.models import Job

    job = Job(user_id="u", app_slug="anhnoibo", job_type=job_type,
              params=params or {}, status=status, admitted_at=admitted_at,
              admission_resource=tai_nguyen,
              admission_slots=1 if tai_nguyen else 0)
    db.add(job)
    db.commit()
    return job


def _nguoi_cho(db, *, cua: str = "stream", tao_luc: datetime | None = None,
               nhip_luc: datetime | None = None, resource: str = TAI_NGUYEN_38,
               trang_thai: str = "cho", rid: str = ""):
    from platform_core.models import LlmWaiter

    w = LlmWaiter(resource=resource, cua=cua, lop=L.TUONG_TAC, user_id="u",
                  request_id=rid or f"r{id(object()) % 10**9}",
                  created_at=tao_luc or T0, heartbeat_at=nhip_luc or tao_luc or T0,
                  trang_thai=trang_thai)
    db.add(w)
    db.commit()
    return w


def _xin38(db, *, holder: str = "x"):
    from platform_core.llm import admission

    return admission.xet_va_giu(db, resource=TAI_NGUYEN_38, slots=SO_SLOT,
                                user_id="u", mode="stream", holder_id=holder,
                                token_pool=POOL_38, lop=L.TUONG_TAC,
                                token_dat_truoc=10_000)


def _xin_anh(db, *, holder: str = "w1", lop: str = ""):
    from platform_core.llm import admission

    return admission.xet_va_giu(db, resource=TAI_NGUYEN_ANH, slots=1, user_id="u",
                                mode="job", holder_id=holder, job_id="j1", lop=lop)


def _dong(db):
    from platform_core.models import GpuResidency

    db.expire_all()
    return db.get(GpuResidency, NHOM)


def _buoc(db, dh: DongHo, may_b: MayBGia) -> R.TrangThai:
    return R.buoc(db, nhom=NHOM, may_b=may_b, bay_gio=dh)


# ═════════════════════════════════════════════════════════════════════════════
#  1. Chu trình đầy đủ — đúng thứ tự plan liệt kê
# ═════════════════════════════════════════════════════════════════════════════

def test_chu_trinh_day_du_va_dung_mot_lenh_nha(db, dh, may_b):
    """`XA_LLM → NHA_LLM → ANH → TRA_ANH → NAP_LLM → LLM`, và ai được nhận ở đâu.

    Mỗi bước kiểm **hai** thứ: trạng thái mới, và **cửa nào mở** ở trạng thái đó.
    Chỉ kiểm trạng thái là kiểm một cái tên; cửa mới là thứ khách chạm vào.
    """
    # ── Bước 1: một lease 3.8 đang chạy, gateway còn 1 lượt bay, job ảnh vào hàng
    _lease(db, TAI_NGUYEN_38, holder="luot-38")
    _job(db)
    may_b.inflight = 1

    assert _buoc(db, dh, may_b).ten == R.XA_LLM
    assert may_b.lenh == [], "nha khi lease 3.8 con song = giet luot cua khach"
    # L-9: lượt đang chạy KHÔNG bị giết — nó còn nguyên sau lượt bước.
    assert R._dem_lease(db, TAI_NGUYEN_38) == 1
    # Cửa 3.8 đã đóng: lượt MỚI bị từ chối (drain = ngừng nhận, không phải giết).
    assert _xin38(db, holder="moi")[1] == L.CHO_RESIDENCY
    db.rollback()

    # ── Bước 2: lease cũ nhả nhưng gateway CÒN in-flight ⇒ vẫn chưa nhả model
    _nha_lease(db, TAI_NGUYEN_38)
    dh.tien(2)
    assert _buoc(db, dh, may_b).ten == R.XA_LLM
    assert may_b.lenh == [], "hai so phai cung bang 0 moi la drain xong"

    # ── Bước 3: gateway báo 0 ⇒ NHA_LLM + đúng một lệnh `nha`
    may_b.inflight = 0
    dh.tien(2)
    assert _buoc(db, dh, may_b).ten == R.NHA_LLM
    assert may_b.lenh == [R.NHA_LLM_LENH]

    # ── Bước 4: máy B xác nhận model đã rời card ⇒ ANH, cửa sổ ảnh mở
    dh.tien(2)
    tt = _buoc(db, dh, may_b)
    assert tt.ten == R.ANH and tt.cua_so_bat_dau == dh()
    # ComfyUI phải SỐNG trước khi cửa nhận job ảnh mở (5.4a: `free_comfy` dừng
    # hẳn dịch vụ, nên phía ảnh không tự hồi).
    assert may_b.comfy_dang_chay is True
    assert may_b.lenh == [R.NHA_LLM_LENH, "chay_comfy"]
    ve_anh, ly_do = _xin_anh(db)
    assert ve_anh is not None, ly_do
    db.commit()
    assert _xin38(db, holder="trong-cua-so")[1] == L.CHO_RESIDENCY
    db.rollback()

    # Job ảnh chạy: rời hàng đợi, mang mốc `admitted_at` trong cửa sổ.
    from platform_core.models import Job
    dong_job = db.query(Job).first()
    dong_job.status = "running"
    dong_job.admitted_at = dh.luc()
    db.commit()
    dh.tien(30)
    assert _buoc(db, dh, may_b).ten == R.ANH, "dang ve thi cua so phai mo tiep"

    # ── Bước 5: vẽ xong, hàng rỗng ⇒ TRA_ANH (cửa ảnh đóng)
    dong_job.status = "done"
    db.commit()
    _nha_lease(db, TAI_NGUYEN_ANH)
    dh.tien(2)
    assert _buoc(db, dh, may_b).ten == R.TRA_ANH
    assert _xin_anh(db, holder="w2")[1] == L.CHO_RESIDENCY
    db.rollback()

    # ── Bước 6: VRAM còn bẩn ⇒ ở lại + `free_comfy` (nghĩa: làm VRAM sạch)
    may_b.vram = 9_000
    dh.tien(2)
    assert _buoc(db, dh, may_b).ten == R.TRA_ANH
    assert may_b.lenh == [R.NHA_LLM_LENH, "chay_comfy", R.FREE_COMFY_LENH]
    assert may_b.comfy_dang_chay is False

    # ── Bước 7: VRAM hạ ⇒ NAP_LLM + `nap`
    may_b.vram = 1_500
    dh.tien(2)
    assert _buoc(db, dh, may_b).ten == R.NAP_LLM
    assert may_b.lenh[-1] == R.NAP_LLM_LENH

    # ── Bước 8: nạp xong ⇒ LLM, và người chờ 3.8 được nhận
    may_b.nap_ket_qua, may_b.llm_da_nap = "ok", True
    dh.tien(17)
    tt = _buoc(db, dh, may_b)
    assert (tt.ten, tt.lan_nap_loi) == (R.LLM, 0)
    ve, ly_do = _xin38(db, holder="nguoi-cho")
    assert ve is not None, ly_do
    db.commit()

    # ⭐ Cả chu trình: ĐÚNG MỘT `nha`, một `nap`, và **một cặp** ComfyUI
    #    (bật vào cửa sổ ảnh, dừng khi trả card) — không lệnh nào ngoài bảng.
    assert may_b.lenh == [R.NHA_LLM_LENH, "chay_comfy", R.FREE_COMFY_LENH,
                          R.NAP_LLM_LENH]
    assert may_b.lenh.count("chay_comfy") == may_b.lenh.count(R.FREE_COMFY_LENH)


def test_job_anh_rut_khoi_hang_giua_luc_drain_thi_huy_viec_doi(db, dh, may_b):
    """Đối chứng của chu trình: không phải mọi `XA_LLM` đều dẫn tới một lần nạp.

    Đường huỷ bỏ (`XA_LLM → LLM`) tiết kiệm đúng 16,3 s nạp lại. Không có ca này
    thì một bản cài "đã vào XA_LLM là phải đi hết vòng" cũng xanh.
    """
    from platform_core.models import Job

    _job(db)
    assert _buoc(db, dh, may_b).ten == R.XA_LLM
    db.query(Job).delete()
    db.commit()
    dh.tien(2)
    assert _buoc(db, dh, may_b).ten == R.LLM
    assert may_b.lenh == []


# ═════════════════════════════════════════════════════════════════════════════
#  2. Máy B câm — fail-closed, và dòng vẫn được tạo
# ═════════════════════════════════════════════════════════════════════════════

def test_may_b_nem_thi_khong_chuyen_trang_thai_nao(db, dh, may_b, caplog):
    _buoc(db, dh, may_b)                       # tạo dòng ở LLM
    _job(db)                                   # có việc ảnh ⇒ lẽ ra sang XA_LLM
    may_b.loi = RuntimeError("cong LLM may B khong tra loi")

    with caplog.at_level(logging.WARNING, logger="platform_core.llm.residency"):
        tt = _buoc(db, dh, may_b)

    assert tt.ten == R.LLM, "chuyen tren su that khong biet"
    assert _dong(db).trang_thai == R.LLM
    assert may_b.lenh == []
    assert any("khong hoi duoc may B" in r.getMessage() for r in caplog.records)


def test_doi_chung_cung_dau_vao_do_voi_may_b_khoe_thi_CO_chuyen(db, dh, may_b):
    """Không có ca này, một bản cài không bao giờ chuyển gì cũng xanh ở ca trên."""
    _buoc(db, dh, may_b)
    _job(db)
    assert _buoc(db, dh, may_b).ten == R.XA_LLM


def test_tao_dong_ngay_luot_dau_du_may_b_cam(db, dh, may_b):
    """🔴 Nghĩa vụ 5.3 §6.1: máy B im lặng KHÔNG được thành "3.8 ngừng bán".

    Không có dòng ⇒ luật 0 đóng **cả hai** cửa. Nếu trọng tài chỉ tạo dòng sau
    khi đọc được máy B thì một cổng LLM chết = mọi lượt 3.8 chờ hết ngân sách rồi
    429, vô hạn — chứ không phải "giữ nguyên cư trú hiện tại".
    """
    may_b.loi = RuntimeError("cong LLM may B khong tra loi")

    # Đối chứng TRƯỚC: chưa có dòng thì cửa 3.8 ĐÓNG.
    assert _xin38(db)[1] == L.CHO_RESIDENCY
    db.rollback()
    assert _dong(db) is None

    tt = _buoc(db, dh, may_b)

    assert tt.ten == R.TRANG_THAI_KHOI_TAO == R.LLM
    assert _dong(db) is not None and _dong(db).trang_thai == R.LLM
    ve, ly_do = _xin38(db)
    assert ve is not None, ly_do          # 3.8 bán lại được ngay lượt bước đầu
    db.commit()


def test_trang_thai_khoi_tao_khong_phat_lenh_nao(db, dh, may_b):
    """Tạo dòng là một lời KHAI, không phải một hành động trên card.

    Đây là nửa còn lại của lựa chọn `TRANG_THAI_KHOI_TAO = LLM`: nó an toàn vì
    lượt bước đầu không nhả, không nạp, không dọn VRAM của ai.
    """
    _buoc(db, dh, may_b)
    assert may_b.lenh == []


def test_bat_comfy_that_bai_thi_KHONG_vao_cua_so_anh(db, dh, may_b, caplog):
    """5.4a dừng **hẳn** dịch vụ LTTComfyUI, nên vào `ANH` mà ComfyUI chưa sống
    lại là mở cửa nhận job ảnh vào một máy không vẽ được.

    Ở lại `NHA_LLM` là trạng thái không mở cửa cho ai ⇒ không job nào bị nhận,
    và lượt sau thử lại (lệnh idempotent). Đây cũng là ca chứng minh lệnh ấy nằm
    ở **lối vào** cửa sổ ảnh chứ không ở cuối cửa sổ LLM: đặt sai chỗ thì "chưa
    bật được" và "cửa đã mở" là hai việc rời nhau.
    """
    _job(db)
    _buoc(db, dh, may_b)                       # LLM -> XA_LLM
    dh.tien(2)
    assert _buoc(db, dh, may_b).ten == R.NHA_LLM
    may_b.loi_comfy = RuntimeError("SCM 1051: con dich vu phu thuoc dang chay")

    dh.tien(2)
    with caplog.at_level(logging.ERROR, logger="platform_core.llm.residency"):
        assert _buoc(db, dh, may_b).ten == R.NHA_LLM
    assert _dong(db).trang_thai == R.NHA_LLM
    assert any("khong bat lai duoc ComfyUI" in r.getMessage()
               for r in caplog.records)
    assert _xin_anh(db)[1] == L.CHO_RESIDENCY      # cửa ảnh vẫn ĐÓNG
    db.rollback()

    # Đối chứng: bật được ⇒ vào `ANH` ngay lượt sau, không cần một cú hích nào.
    may_b.loi_comfy = None
    dh.tien(2)
    assert _buoc(db, dh, may_b).ten == R.ANH
    ve, ly_do = _xin_anh(db)
    assert ve is not None, ly_do
    db.commit()


# ═════════════════════════════════════════════════════════════════════════════
#  3. Khoá lạc quan
# ═════════════════════════════════════════════════════════════════════════════

def test_ghi_phien_ban_cu_thua_ma_khong_pha_gi(db, dh, may_b):
    _buoc(db, dh, may_b)
    cu = _dong(db).phien_ban

    assert R._ghi_dong(db, NHOM, R.TrangThai(ten=R.XA_LLM, tu_luc=dh()), cu) is True
    db.commit()
    assert (_dong(db).trang_thai, _dong(db).phien_ban) == (R.XA_LLM, cu + 1)

    # Kẻ thua: cùng `phien_ban` đã cũ.
    assert R._ghi_dong(db, NHOM, R.TrangThai(ten=R.NHA_LLM, tu_luc=dh()), cu) is False
    db.commit()
    assert (_dong(db).trang_thai, _dong(db).phien_ban) == (R.XA_LLM, cu + 1)


def test_mat_luot_ghi_thi_KHONG_phat_lenh(db, dh, may_b, monkeypatch):
    """Kẻ thua không phát lệnh — đó là điều làm "đúng một `nha`" đúng cả khi hai
    tiến trình worker chồng nhau (một lượt deploy)."""
    from platform_core.models import GpuResidency

    _job(db)
    _buoc(db, dh, may_b)                       # ⇒ XA_LLM, đã drain (0/0)
    assert _dong(db).trang_thai == R.XA_LLM

    that = R._quan_sat

    def chen(*a, **k):
        qs = that(*a, **k)
        # Một trọng tài KHÁC vừa ghi xong, giữa lúc ta đọc và lúc ta ghi.
        db.execute(update(GpuResidency).where(GpuResidency.nhom == NHOM)
                   .values(phien_ban=GpuResidency.phien_ban + 1))
        return qs

    monkeypatch.setattr(R, "_quan_sat", chen)
    dh.tien(2)
    tt = _buoc(db, dh, may_b)

    assert tt.ten == R.XA_LLM
    assert may_b.lenh == [], "ke thua phat lenh = hai lenh cho mot lan doi cu tru"


def test_doi_chung_khong_chen_thi_dung_mot_lenh_nha(db, dh, may_b):
    _job(db)
    _buoc(db, dh, may_b)
    dh.tien(2)
    assert _buoc(db, dh, may_b).ten == R.NHA_LLM
    assert may_b.lenh == [R.NHA_LLM_LENH]


# ═════════════════════════════════════════════════════════════════════════════
#  4. Dựng `QuanSat` — mỗi trường là một câu hỏi, nên mỗi trường một ca
# ═════════════════════════════════════════════════════════════════════════════

def _qs(db, dh, may_b, tt: R.TrangThai) -> R.QuanSat:
    return R._quan_sat(db, nhom=NHOM, tt=tt, tai_nguyen=R.thanh_vien(NHOM),
                       tin=may_b.trang_thai(), bay_gio=dh())


def test_dem_job_anh_theo_ban_khai_khong_theo_cot(db, dh, may_b):
    """🔴 Đếm theo `Job.admission_resource` là một BẾ TẮC CÂM, không phải một
    phép đếm hẹp hơn.

    Cột ấy chỉ được ghi ở hai đường nộp có `registry.admission_luc_nop`; ba app
    ảnh nộp từ giao diện và để nó **rỗng**. Còn `job_runner` đòi lease theo **bản
    khai của tool**. Nên nếu trọng tài đếm theo cột: job ảnh của giao diện bị cửa
    admission từ chối (nhóm đang ở `LLM`) trong khi trọng tài không thấy ai chờ ⇒
    không bao giờ mở cửa sổ ảnh. Xanh mọi chỗ, và app ảnh không bao giờ chạy.
    """
    _job(db, tai_nguyen="")                    # đúng như giao diện nộp
    assert _qs(db, dh, may_b, R.TrangThai()).job_anh_cho == 1


def test_job_cua_tool_khong_khai_nhom_thi_khong_dem(db, dh, may_b):
    """Đối chứng ngược: một `job_type` lạ **không** vào phép đếm, dù cột có ghi
    tên tài nguyên của ảnh. Không có vế này thì "đếm hết" cũng xanh."""
    _job(db, job_type="taovideo.render", tai_nguyen=TAI_NGUYEN_ANH)
    assert _qs(db, dh, may_b, R.TrangThai()).job_anh_cho == 0


def test_dem_anh_trong_cua_so_theo_moc_admitted_at(db, dh, may_b):
    """Đếm từ bảng `jobs`, không từ một bộ đếm ghi tay (`models.GpuResidency`)."""
    cua_so = dh.luc()
    _job(db, status="done", admitted_at=cua_so - timedelta(seconds=1))   # trước
    _job(db, status="done", admitted_at=cua_so + timedelta(seconds=5))   # trong
    _job(db, status="done", admitted_at=None)                            # chưa nhận
    tt = R.TrangThai(ten=R.ANH, cua_so_bat_dau=cua_so.timestamp())
    assert _qs(db, dh, may_b, tt).anh_bat_dau_trong_cua_so == 1


def test_dem_lease_tach_doi_hai_vai(db, dh, may_b):
    _lease(db, TAI_NGUYEN_38, holder="a")
    _lease(db, TAI_NGUYEN_ANH, holder="b")
    qs = _qs(db, dh, may_b, R.TrangThai())
    assert (qs.lease_llm, qs.lease_anh) == (1, 1)


def test_dem_lease_anh_bat_ke_lop_cua_no(db, dh, may_b):
    """Nhãn `lop` của lease **không** được tham gia phép đếm cư trú.

    Ca này bảo vệ nghĩa vụ 2 của brief (job ảnh phải mang `lop="nen"`): việc sửa
    nhãn ấy là sửa **sổ sách**, và nó không được kéo theo một thay đổi hành vi ở
    trọng tài. Nếu phép đếm lọc theo lớp thì một lần sửa nhãn sẽ làm trọng tài
    thôi thấy lượt vẽ đang chạy — tức nạp 16 GB lên một card đang vẽ.
    """
    _lease(db, TAI_NGUYEN_ANH, holder="b", lop=L.NEN)
    assert _qs(db, dh, may_b, R.TrangThai()).lease_anh == 1
    _nha_lease(db, TAI_NGUYEN_ANH)
    _lease(db, TAI_NGUYEN_ANH, holder="b2", lop=L.TUONG_TAC)
    assert _qs(db, dh, may_b, R.TrangThai()).lease_anh == 1


def test_nguoi_cho_llm_gom_phong_cho_va_job_nen(db, dh, may_b):
    _nguoi_cho(db, tao_luc=dh.luc(), nhip_luc=dh.luc())
    _job(db, job_type="ltt_llm.chat", params={"model": "ltt-3.8"})
    assert _qs(db, dh, may_b, R.TrangThai()).nguoi_cho_llm == 2


def test_job_35_khong_tinh_la_nguoi_cho_3090(db, dh, may_b):
    """Đối chứng theo TỪNG CARD: `ltt-3.5` ở 5060 Ti, nó không chờ 3090 bao giờ.

    Cùng `job_type` (`text.chat` phục vụ hai model), nên một phép đếm theo
    `job_type` sẽ nhầm — và nhầm về phía đóng cửa sổ ảnh sớm mãi mãi.
    """
    _job(db, job_type="ltt_llm.chat", params={"model": "ltt-3.5"})
    assert _qs(db, dh, may_b, R.TrangThai()).nguoi_cho_llm == 0


def test_nguoi_cho_mat_nhip_khong_giu_hang(db, dh, may_b):
    from platform_core.llm import phong_cho

    _nguoi_cho(db, tao_luc=dh.luc(),
               nhip_luc=dh.luc(-phong_cho.HAN_NHIP_CHO_S - 1))
    qs = _qs(db, dh, may_b, R.TrangThai())
    assert qs.nguoi_cho_llm == 0 and qs.han_chot_llm_s is None


def test_han_chot_theo_TRAN_CUA_TUNG_CUA(db, dh, may_b):
    """Trần chờ khác nhau theo cửa (D-06 stream 300 s; TD-7 đồng bộ 60 s).

    Một con số chung sẽ sai cho một nửa người chờ, và sai về phía *"còn nhiều
    thời gian"* nghĩa là họ chết thật trong lúc ta vẽ thêm một ảnh.
    """
    from platform_core.llm import tham_so_da_luot

    ts = tham_so_da_luot.doc()
    _nguoi_cho(db, cua="stream", tao_luc=dh.luc(), nhip_luc=dh.luc(), rid="s1")
    assert _qs(db, dh, may_b, R.TrangThai()).han_chot_llm_s == pytest.approx(
        ts.cho_stream_toi_da_s)

    _nguoi_cho(db, cua="sync", tao_luc=dh.luc(), nhip_luc=dh.luc(), rid="s2")
    # Hạn chót SỚM NHẤT, không phải hạn chót của người vào trước.
    assert _qs(db, dh, may_b, R.TrangThai()).han_chot_llm_s == pytest.approx(
        ts.cho_dong_bo_toi_da_s)


def test_cua_cua_APP_lay_tran_stream_khong_lay_tran_dong_bo(db, dh, may_b):
    """Một cửa do app đặt tên (vd `apps/chatltt/chinh_sach.CUA`) phải đi theo
    **mặc định của đường chờ** — 300 s — chứ không theo một bảng tên cửa trong
    `platform_core`. Bảng ấy là cách tên app lọt vào nền tảng, và nó đã lọt thật
    một lần trong chính lượt viết này (`test_residency_khong_nhac_ten_app…` bắt
    được). Trần đồng bộ cho một cửa stream sẽ đóng cửa sổ ảnh sớm ở **mọi** lượt.
    """
    from platform_core.llm import tham_so_da_luot

    _nguoi_cho(db, cua="mot_cua_cua_app", tao_luc=dh.luc(), nhip_luc=dh.luc())
    assert _qs(db, dh, may_b, R.TrangThai()).han_chot_llm_s == pytest.approx(
        tham_so_da_luot.doc().cho_stream_toi_da_s)


def test_cua_so_anh_dong_som_khi_nguoi_cho_sap_het_han(db, dh, may_b):
    """Nối hai đầu: một hạn chót thật (dòng `llm_waiters`) làm đóng cửa sổ ảnh.

    `test_1216` đã chứng minh LUẬT này với `han_chot_llm_s` tiêm tay; ca đây
    chứng minh trọng tài **dựng được** con số ấy từ CSDL. Lo ngại §2 của báo cáo
    5.1/5.2 là đúng chỗ này: dựng sai thì máy vẫn xanh mà cửa sổ vẫn sai.
    """
    from platform_core.models import GpuResidency

    db.add(GpuResidency(nhom=NHOM, trang_thai=R.ANH, tu_luc=dh.luc(),
                        cua_so_bat_dau=dh.luc(), lan_nap_loi=0, phien_ban=0))
    db.commit()
    _job(db)                                        # còn ảnh chờ
    _job(db, status="done", admitted_at=dh.luc())   # 1 ảnh đã vẽ trong cửa sổ
    # Người chờ stream vào trước 200 s ⇒ còn 100 s < 16,3 + 110 + 30.
    _nguoi_cho(db, cua="stream", tao_luc=dh.luc(-200), nhip_luc=dh.luc())

    assert _buoc(db, dh, may_b).ten == R.TRA_ANH


def test_doi_chung_khong_ai_cho_thi_ve_tiep(db, dh, may_b):
    """Trần của D01 là trần TRÊN, không phải một hạn phải dừng: giữ card cho một
    hàng rỗng là giữ không, nhưng dừng khi không ai đợi cũng là bỏ không."""
    from platform_core.models import GpuResidency

    db.add(GpuResidency(nhom=NHOM, trang_thai=R.ANH, tu_luc=dh.luc(),
                        cua_so_bat_dau=dh.luc(-5_000), lan_nap_loi=0, phien_ban=0))
    db.commit()
    _job(db)
    for _ in range(9):
        _job(db, status="done", admitted_at=dh.luc(-10))
    assert _buoc(db, dh, may_b).ten == R.ANH


def test_may_b_thieu_so_inflight_la_KHONG_BIET_khong_phai_0(db, dh, may_b):
    """`None` ≠ 0 ở ba trường của máy B. Một `0` bịa ra là một lệnh `nha` phát
    lên một model đang sinh chữ cho khách."""
    _job(db)
    _buoc(db, dh, may_b)                       # ⇒ XA_LLM
    may_b.inflight = None
    dh.tien(2)
    assert _buoc(db, dh, may_b).ten == R.XA_LLM
    assert may_b.lenh == []


def test_vram_khong_doc_duoc_thi_khong_nap(db, dh, may_b):
    from platform_core.models import GpuResidency

    db.add(GpuResidency(nhom=NHOM, trang_thai=R.TRA_ANH, tu_luc=dh.luc(),
                        lan_nap_loi=0, phien_ban=0))
    db.commit()
    may_b.vram = None
    assert _buoc(db, dh, may_b).ten == R.TRA_ANH
    assert may_b.lenh == [R.FREE_COMFY_LENH]   # dọn rồi đo lại, KHÔNG nạp


# ═════════════════════════════════════════════════════════════════════════════
#  5. Bản khai: ba app ảnh, và nền tảng chỉ ĐỌC
# ═════════════════════════════════════════════════════════════════════════════

def _tool_anh():
    from platform_core.registry import discover

    ra = []
    for app in discover():
        if app.manifest is None or app.manifest.slug not in APP_ANH:
            continue
        for tool in app.manifest.tools or ():
            ra.append((app.manifest.slug, tool))
    return ra


def test_ba_manifest_anh_khai_dung_bo_ba():
    """`anh_3090` + `rtx3090` + `theo_lo`, giống nhau ở cả bốn tool của ba app.

    Bốn (không ba): `taoanh` có hai tool cùng `job_type`, và hai đường nộp job
    đọc `ToolSpec` **của tool được gọi**, nên bỏ sót một tool là bỏ sót một đường
    vào cùng một card.
    """
    thay = {}
    for slug, tool in _tool_anh():
        am = (tool.admission_theo_model or {}).get("*")
        assert am is not None, f"{slug}.{tool.name} chua khai cu tru 3090"
        thay[(slug, tool.name)] = (am.resource, am.residency_group, am.vai_tro,
                                   am.slots)
    assert len(thay) == 4, thay
    assert set(thay.values()) == {(TAI_NGUYEN_ANH, NHOM_CU_TRU_38, R.THEO_LO, 1)}


def test_vai_tro_cua_moi_ban_khai_nam_trong_VAI_TRO():
    """Nghĩa vụ 3: một `vai_tro` gõ sai phải ĐỎ ở cổng, không phải 500 lúc 3 giờ
    sáng — `mo_cho` NÉM với vai lạ, và nay nó ném từ trong cửa admission."""
    for slug, tool in _tool_anh():
        for am in (tool.admission_theo_model or {}).values():
            assert am.vai_tro in R.VAI_TRO, f"{slug}.{tool.name}: {am.vai_tro!r}"
            R.mo_cho(R.LLM, am.vai_tro)        # không ném


def test_doi_chung_vai_tro_go_sai_thi_mo_cho_NEM():
    """Không có ca này, ca trên có thể xanh vì `mo_cho` nuốt mọi thứ."""
    with pytest.raises(ValueError):
        R.mo_cho(R.LLM, "theolo")


def test_hai_vai_cua_nhom_khong_dung_chung_tai_nguyen():
    """Bất biến cốt tuỷ của D01 B đọc ra được từ bản khai: hai vai, hai tài
    nguyên. Cùng một tên tài nguyên cho hai vai thì một lease của bên này sẽ
    được tính là lease của bên kia."""
    thanh_vien = R.thanh_vien(NHOM)
    assert thanh_vien == {R.MAC_DINH: TAI_NGUYEN_38, R.THEO_LO: TAI_NGUYEN_ANH}
    assert len(set(thanh_vien.values())) == 2


def test_cac_nhom_doc_tu_ban_khai_khong_go_ten():
    assert R.cac_nhom() == (NHOM_CU_TRU_38,)


def test_trong_tai_doc_cung_ban_do_voi_admission():
    """Ghim tên `admission._ban_do_cu_tru`: trọng tài **dùng lại** bộ đọc của cửa
    admission thay vì viết bộ thứ hai (hai bộ đọc = hai bản khai, và bản thứ hai
    sẽ trôi). Cái giá là một phụ thuộc vào một tên riêng tư — ca này biến nó
    thành một lỗi ở cổng thay vì một lỗi ở production."""
    from platform_core.llm import admission

    assert callable(getattr(admission, "_ban_do_cu_tru", None))
    assert callable(getattr(admission, "_khoa_resource", None))


def test_residency_khong_nhac_ten_app_trong_ma():
    """⛔ `platform_core` không được biết tên app (`test_147` đo chiều import; ca
    này đo chiều **chuỗi** trong đúng tệp mới của Task 5.5).

    ⚠️ Phạm vi hẹp và cố ý: chỉ `residency.py`, và chỉ **mã thực thi** — hằng
       chuỗi + tên định danh, KHÔNG tính chú thích và docstring. Một chú thích trỏ
       tới `apps/ltt_llm/ngan_sach.py` là một chỉ dẫn cho người đọc, không phải
       một phụ thuộc; một chuỗi `"anhnoibo"` trong mã thì là.
    """
    from platform_core.registry import discover

    slug = [a.manifest.slug for a in discover() if a.manifest is not None]
    assert slug, "khong doc duoc registry ⇒ ca nay khong do duoc gi"
    cay = ast.parse(NGUON.read_text(encoding="utf-8"))
    tai_lieu = set()
    for n in ast.walk(cay):
        than = getattr(n, "body", None)
        if not isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) or not than:
            continue
        dau = than[0]
        if isinstance(dau, ast.Expr) and isinstance(dau.value, ast.Constant) \
                and isinstance(dau.value.value, str):
            tai_lieu.add(id(dau.value))
    xau = []
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
            if id(nut) in tai_lieu:
                continue
            xau.append(nut.value)
        elif isinstance(nut, (ast.Name, ast.Attribute)):
            xau.append(getattr(nut, "id", None) or getattr(nut, "attr", ""))
    for ten in slug:
        vi_pham = [s for s in xau if ten in (s or "")]
        assert not vi_pham, f"residency.py nhac ten app {ten!r}: {vi_pham}"


# ═════════════════════════════════════════════════════════════════════════════
#  6. Thứ tự khoá, và hai nửa của tệp
# ═════════════════════════════════════════════════════════════════════════════

class PhienGia:
    """Phiên giả tự khai là PostgreSQL để `_advisory` thực sự phát lệnh."""

    def __init__(self):
        self.khoa: list[str] = []
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    def execute(self, stmt, params=None):
        self.khoa.append((params or {}).get("k", ""))
        return None


def test_khoa_theo_dung_thu_tu_ten_va_dung_cong_thuc_cua_admission():
    """Một thứ tự cố định là thứ DUY NHẤT chặn deadlock giữa lượt xin và lượt lật.

    Và khoá phải trùng **từng ký tự** với `admission._khoa_resource`: hai công
    thức là hai khoá khác nhau, tức không khoá gì cả — trong im lặng.
    """
    from platform_core.llm import admission

    p = PhienGia()
    R._khoa(p, NHOM, {R.MAC_DINH: TAI_NGUYEN_38, R.THEO_LO: TAI_NGUYEN_ANH})

    mong_doi = PhienGia()
    admission._khoa_resource(mong_doi, TAI_NGUYEN_ANH)
    admission._khoa_resource(mong_doi, TAI_NGUYEN_38)
    assert p.khoa == [f"residency:{NHOM}"] + mong_doi.khoa
    assert p.khoa[1:] == sorted(p.khoa[1:])


def test_thu_tu_khoa_khong_phu_thuoc_thu_tu_ban_khai():
    """Đối chứng: đảo thứ tự `dict` của bản khai ⇒ thứ tự khoá KHÔNG đổi.
    Không có vế này thì `sorted()` có thể bị thay bằng một vòng `for` mà ca trên
    vẫn xanh."""
    a = PhienGia()
    b = PhienGia()
    R._khoa(a, NHOM, {R.MAC_DINH: TAI_NGUYEN_38, R.THEO_LO: TAI_NGUYEN_ANH})
    R._khoa(b, NHOM, {R.THEO_LO: TAI_NGUYEN_ANH, R.MAC_DINH: TAI_NGUYEN_38})
    assert a.khoa == b.khoa


def test_phan_thuan_khong_cham_csdl_hay_mang():
    """Docstring của module khai "PHẦN 1 không CSDL, không HTTP, không đồng hồ".

    Ca này làm câu ấy đo được: mọi hàm định nghĩa TRƯỚC dải kẻ không được import
    gì và không được nhắc tới `db`/`httpx`/`time`/`datetime`. Không có nó, lời
    khai kia sẽ đúng hôm nay và sai vào lần ai đó thêm một truy vấn "cho tiện".
    """
    nguon = NGUON.read_text(encoding="utf-8")
    dong = nguon.splitlines()
    moc = [i for i, s in enumerate(dong, 1) if "PHẦN 2 — TRỌNG TÀI" in s]
    assert len(moc) == 1, "khong tim thay dai ke chia hai nua"
    ranh = moc[0]

    cay = ast.parse(nguon)
    cam = {"db", "httpx", "time", "datetime", "os", "json", "pathlib", "threading"}
    thuan = [n for n in cay.body
             if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.lineno < ranh]
    assert len(thuan) >= 8, f"chi thay {len(thuan)} dinh nghia o phan thuan"
    for n in thuan:
        for con in ast.walk(n):
            assert not isinstance(con, (ast.Import, ast.ImportFrom)), \
                f"{n.name} import trong phan THUAN"
            if isinstance(con, ast.Name):
                assert con.id not in cam, f"{n.name} cham {con.id!r}"
            if isinstance(con, ast.arg):
                assert con.arg not in cam, f"{n.name} nhan tham so {con.arg!r}"


def test_free_comfy_giu_TEN_cua_plan_va_khong_goi_free_thang():
    """R22 / L-14 §3: giữ **tên** `free_comfy`, đổi **nghĩa** thành "làm VRAM
    3090 sạch". ComfyUI ấm giữ 223,5 MiB ngữ cảnh CUDA mà `POST /free` không nhả,
    còn biên của LTT-3.8 chỉ 445 MiB — nên máy A không được tự đoán lại nghĩa ấy
    bằng một lượt `/free` gọi thẳng."""
    assert R.FREE_COMFY_LENH == "free_comfy"
    nguon = NGUON.read_text(encoding="utf-8")
    cay = ast.parse(nguon)
    duong = [n.value for n in ast.walk(cay)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)
             and n.value.startswith("/")]
    assert "/v1/nha_comfy" in duong
    assert not [d for d in duong if d.endswith("/free") or "/unload" in d], duong


# ═════════════════════════════════════════════════════════════════════════════
#  7. Cổng ra máy B (`MayBResidency`) — đường dây, không phải chính sách
# ═════════════════════════════════════════════════════════════════════════════

class DayGia:
    def __init__(self, tra=None):
        self.goi: list[tuple] = []
        self.tra = tra or {}

    def __call__(self, method, path, than=None):
        self.goi.append((method, path, than))
        return self.tra


def test_ba_lenh_di_dung_duong_va_mang_ten_model():
    llm = DayGia()
    render = DayGia({"da_dung": True, "dang_chay": True})
    cong = R.MayBResidency(model_llm="qwen38-api", gpu_uuid="GPU-x",
                           goi_llm=llm, goi_render=render)
    cong.nha()
    cong.nap()
    cong.free_comfy()
    cong.chay_comfy()
    assert llm.goi == [("POST", "/v1/residency/nha", {"model": "qwen38-api"}),
                       ("POST", "/v1/residency/nap", {"model": "qwen38-api"})]
    assert render.goi == [("POST", "/v1/nha_comfy", {"hanh_dong": "dung"}),
                          ("POST", "/v1/nha_comfy", {"hanh_dong": "chay"})]


def test_nha_comfy_200_ma_khong_xac_nhan_thi_NEM():
    """"Thành công im lặng là kết cục tệ nhất" — cổng render khai đúng câu ấy và
    trả bằng chứng (`da_dung` / `dang_chay`). Đọc mã 200 rồi thôi là tin lời SCM,
    thứ mà chính `cai_dat_dich_vu.ps1` dặn "KHONG TIN, HAY DO"."""
    cong = R.MayBResidency(gpu_uuid="GPU-x", goi_llm=DayGia(),
                           goi_render=DayGia({"hanh_dong": "dung"}))
    with pytest.raises(R.LoiMayB):
        cong.free_comfy()
    with pytest.raises(R.LoiMayB):
        cong.chay_comfy()


def test_han_gio_comfy_cao_hon_han_cho_cua_cong_render():
    """Không dựng một hạn chờ THỨ HAI bất đồng với hạn của cổng render: nó tự
    chờ dịch vụ (60 s) rồi chờ VRAM tụt (15 s) và trả lời bằng số đo. Hạn ở máy
    A chỉ là chốt chặn vận chuyển, nên nó phải cao hơn hẳn tổng ấy."""
    cong = R.MayBResidency(goi_llm=DayGia())
    assert cong.timeout_comfy_s >= 75.0
    assert cong.timeout_comfy_s > cong.timeout_s


def test_trang_thai_doc_dung_bon_truong():
    llm = DayGia({"llm_da_nap": True, "inflight": {"qwen38-api": 2, "khac": 9},
                  "vram_mib": {"GPU-x": 1234, "GPU-y": 13_000},
                  "nap_ket_qua": "ok"})
    tin = R.MayBResidency(model_llm="qwen38-api", gpu_uuid="GPU-x",
                          goi_llm=llm).trang_thai()
    assert tin == R.TinMayB(llm_da_nap=True, inflight_llm=2,
                            vram_3090_mib=1234, nap_ket_qua="ok")


def test_vram_lay_theo_UUID_khong_lay_max():
    """`max()` cả bảng là đọc VRAM của card không liên can: LTT-3.5 giữ ~13 GB
    thường trực trên 5060 Ti ⇒ 3090 "không bao giờ sạch" ⇒ không bao giờ nạp lại
    LTT-3.8. Đúng khuyết tật Task 6.1 vừa gỡ khỏi `render_gateway/busy.py`."""
    llm = DayGia({"llm_da_nap": False, "inflight": {},
                  "vram_mib": {"GPU-3090": 400, "GPU-5060": 13_000}})
    tin = R.MayBResidency(gpu_uuid="GPU-3090", goi_llm=llm).trang_thai()
    assert tin.vram_3090_mib == 400


def test_thieu_truong_may_b_thanh_None_khong_thanh_0():
    llm = DayGia({"nap_ket_qua": ""})          # không có ba trường kia
    tin = R.MayBResidency(gpu_uuid="GPU-x", goi_llm=llm).trang_thai()
    assert (tin.llm_da_nap, tin.inflight_llm, tin.vram_3090_mib) == (None, None, None)


def test_uuid_khong_biet_va_nhieu_card_thi_vram_la_None():
    llm = DayGia({"vram_mib": {"a": 1, "b": 2}})
    tin = R.MayBResidency(gpu_uuid="", goi_llm=llm).trang_thai()
    assert tin.vram_3090_mib is None


def test_mot_card_duy_nhat_thi_khong_can_uuid():
    llm = DayGia({"vram_mib": {"a": 7}})
    assert R.MayBResidency(gpu_uuid="", goi_llm=llm).trang_thai().vram_3090_mib == 7


def test_model_mac_dinh_doc_tu_canonical_khong_go_lai():
    from platform_core.llm import canonical

    assert R.MayBResidency(goi_llm=DayGia()).model_llm == \
        canonical.ALIAS_SANG_ID[canonical.MODEL_MAC_DINH]


# ═════════════════════════════════════════════════════════════════════════════
#  8. Nghĩa vụ 2 — nhãn `lop` của lease job ảnh
# ═════════════════════════════════════════════════════════════════════════════

def test_job_anh_xin_duoc_voi_lop_nen(db, dh, may_b):
    """Chứng minh dây nối mà `job_runner` (Task 6.3 đang giữ tệp) sẽ cắm được.

    Job ảnh đi qua nhánh đa lượt từ 5.3, nên không truyền `lop` là dán nhãn
    `tuong_tac` cho một việc NỀN — một dòng sai trong sổ lease, và `/ops` sẽ đọc
    sai. Ca này chốt rằng `lop="nen"` **được nhận** ở `anh_3090` (1 suất):
    `tran_nen(1) = max(1, 0) = 1`, nên luật 3 không chặn; và không ai chờ ở
    `llm_waiters` cho tài nguyên ảnh nên vế "nền nhường người tương tác đang
    chờ" cũng không chặn. Không có phép đo này, dòng sửa một-dòng ấy là một
    phỏng đoán.
    """
    from platform_core.models import GpuResidency

    db.add(GpuResidency(nhom=NHOM, trang_thai=R.ANH, tu_luc=dh.luc(),
                        cua_so_bat_dau=dh.luc(), lan_nap_loi=0, phien_ban=0))
    db.commit()
    ve, ly_do = _xin_anh(db, lop=L.NEN)
    assert ve is not None, ly_do
    assert ve.lop == L.NEN
    db.commit()


def test_doi_chung_khong_truyen_lop_thi_lease_mang_nhan_tuong_tac(db, dh):
    """Đối chứng đo đúng KHUYẾT TẬT đang tồn tại, để nó không vô hình: hôm nay
    `job_runner._luat_cho_job` trả `{}` cho tool pool 0 ⇒ nhãn là `tuong_tac`."""
    from platform_core.models import GpuResidency

    db.add(GpuResidency(nhom=NHOM, trang_thai=R.ANH, tu_luc=dh.luc(),
                        cua_so_bat_dau=dh.luc(), lan_nap_loi=0, phien_ban=0))
    db.commit()
    ve, ly_do = _xin_anh(db, lop="")
    assert ve is not None, ly_do
    assert ve.lop == L.TUONG_TAC


# ═════════════════════════════════════════════════════════════════════════════
#  9. `buoc_dinh_ky` — mặt tiếp xúc của vòng bảo trì
# ═════════════════════════════════════════════════════════════════════════════

def test_buoc_dinh_ky_khong_bao_gio_nem(db, monkeypatch, may_b):
    """Một ngoại lệ ở đây cắt phần còn lại của lượt bảo trì (dọn dữ liệu,
    webhook, báo động), không chỉ cắt trọng tài."""
    def no(*a, **k):
        raise RuntimeError("CSDL sap")

    monkeypatch.setattr(R, "buoc", no)
    R.buoc_dinh_ky(may_b)                      # không ném


def test_buoc_dinh_ky_buoc_moi_nhom_da_khai(db, may_b, monkeypatch):
    da_goi: list[str] = []
    monkeypatch.setattr(R, "buoc",
                        lambda db, *, nhom, **k: da_goi.append(nhom))
    R.buoc_dinh_ky(may_b)
    assert da_goi == [NHOM_CU_TRU_38]
