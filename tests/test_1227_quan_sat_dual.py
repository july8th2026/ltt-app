"""dual-model 6.3 — hai khối quan sát mới của `job_metrics`, và vòng dọn phòng chờ.

Dải **1200–1249** của chương trình Multi-Job / LTT LLM dual-model
(`docs/multijob/08_IMPLEMENTATION_PLAN.md` §28).

═══════════════════════════════════════════════════════════════════════════
 ĐIỀU TỆP NÀY BẢO VỆ
═══════════════════════════════════════════════════════════════════════════

1. **Độ sâu phòng chờ phải TÁCH THEO MODEL.** Hai model nhà nằm trên hai card
   khác nhau của máy B; một hàng dài trước 5060 Ti không nói gì về 3090. Gộp
   chúng lại là biến hai hàng đợi thành một cách âm thầm — và người đọc sẽ đi
   mua thêm slot cho một card đang rảnh.

   ⭐ ĐỐI CHỨNG ĐI KÈM (`test_doi_chung_gop_hai_model_lam_mot_thi_do`): nó **gộp
      thật** hai model rồi chốt rằng phép kiểm trên phải đỏ. Không có nó thì
      "đếm theo model" chỉ là một câu trong docstring: một hàm trả về tổng cũng
      qua được phép kiểm chính nếu dữ liệu thử chỉ có một model.

2. **`residency_3090` phải DẪN XUẤT.** Không bộ đếm ghi tay nào — lý do ở
   docstring `models.GpuResidency`: một bộ đếm ghi tay lệch đúng lúc một tiến
   trình chết giữa cửa sổ, tức đúng lúc người ta cần đọc nó.

3. **`/ops/jobs-metrics` thật sự trả về cả hai khối.** Một khối tính đúng mà
   không ai chiếu ra là một năng lực không ai đi trên đường.

4. **Vòng bảo trì gọi `phong_cho.don_het_han`** (Multi-Job T12). Nó đã được nối
   từ trước; phép kiểm ở đây là cái **bánh cóc** giữ nó đừng biến mất — và nó đo
   sự *có mặt* bằng một mệnh đề dương (gọi hàm thật, đếm số lần chạy), không
   bằng một phép grep vào mã.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

T0 = datetime(2026, 9, 12, 9, 0, tzinfo=timezone.utc)

M38 = "qwen38-api"
M35 = "qwen35-api"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'qs.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


def _cho(db, *, model, lop="tuong_tac", tuoi_s=5.0, nhip_s=0.0,
         cho_residency_s=0.0, trang_thai="cho", resource="r", moc=None):
    """Một dòng `llm_waiters`. `nhip_s` = nhịp tim CŨ bao nhiêu giây so với `moc`.

    ⚠️ `moc` mặc định là `T0` — đúng cho mọi ca **tiêm đồng hồ**
       (`llm_theo_model(db, now=T0, …)`). Ca nào gọi qua **route** thì route
       không nhận `now`, nên nó đo bằng đồng hồ THẬT và phải truyền
       `moc=datetime.now(timezone.utc)`. Xem `test_ops_jobs_metrics…`.
    """
    moc = moc or T0
    from platform_core.models import LlmWaiter

    w = LlmWaiter(resource=resource, model=model, cua="stream", lop=lop,
                  user_id="u", request_id=f"rq{id(model)}{tuoi_s}{nhip_s}{lop}",
                  token_dat_truoc=1000, token_prefill_moi=100,
                  created_at=moc - timedelta(seconds=tuoi_s),
                  heartbeat_at=moc - timedelta(seconds=nhip_s),
                  cho_residency_s=cho_residency_s, trang_thai=trang_thai)
    db.add(w)
    db.flush()
    return w


def _job_anh(db, *, resource, admitted_at, job_id):
    from platform_core.models import JOB_DONE, Job

    j = Job(id=job_id, user_id="u", app_slug="anh", job_type="ve",
            status=JOB_DONE, admission_resource=resource,
            created_at=admitted_at, admitted_at=admitted_at,
            started_at=admitted_at, finished_at=admitted_at)
    db.add(j)
    db.flush()
    return j


# ══════════════════════════════════════════════════════════════════════════
#  1. Phòng chờ THEO MODEL
# ══════════════════════════════════════════════════════════════════════════

def test_do_sau_phong_cho_tach_theo_model_va_theo_lop(db):
    from platform_core import job_metrics

    _cho(db, model=M38, lop="tuong_tac", tuoi_s=12.0)
    _cho(db, model=M38, lop="tuong_tac", tuoi_s=3.0)
    _cho(db, model=M38, lop="nen", tuoi_s=1.0)
    _cho(db, model=M35, lop="tuong_tac", tuoi_s=40.0)
    db.commit()

    k = job_metrics.llm_theo_model(db, now=T0, cutoff=T0 - timedelta(days=7))

    # 🔴 Người chờ của 3.5 KHÔNG được làm phồng con số của 3.8.
    assert k["sau_theo_model"] == {M38: 3, M35: 1}
    assert k["sau_theo_model_lop"][M38] == {"nen": 1, "tuong_tac": 2}
    assert k["sau_theo_model_lop"][M35] == {"tuong_tac": 1}
    # Tuổi lâu nhất cũng theo model: 40 s của 3.5 không được thành tuổi của 3.8.
    assert k["tuoi_lau_nhat_s_theo_model"][M38] == pytest.approx(12.0)
    assert k["tuoi_lau_nhat_s_theo_model"][M35] == pytest.approx(40.0)


def test_doi_chung_gop_hai_model_lam_mot_thi_do(db, monkeypatch):
    """Đối chứng: một bản `llm_theo_model` GỘP hai model ⇒ phép kiểm trên phải đỏ.

    ⭐ Đây là nửa chứng minh còn thiếu. Phép kiểm trên một mình không phân biệt
       được "đếm theo model" với "đếm tổng rồi gán cho model đầu tiên"; chỉ một
       bản cài đặt **sai có chủ ý** mới chỉ ra nó thật sự đo điều nó nói.
    """
    from platform_core import job_metrics

    _cho(db, model=M38, lop="tuong_tac", tuoi_s=12.0)
    _cho(db, model=M35, lop="tuong_tac", tuoi_s=40.0)
    db.commit()

    that = job_metrics.llm_theo_model(db, now=T0, cutoff=T0 - timedelta(days=7))

    def gop(db_, *, now, cutoff):
        k = that
        tong = sum(k["sau_theo_model"].values())
        return dict(k, sau_theo_model={m: tong for m in k["sau_theo_model"]})

    monkeypatch.setattr(job_metrics, "llm_theo_model", gop)
    k = job_metrics.llm_theo_model(db, now=T0, cutoff=T0 - timedelta(days=7))
    assert k["sau_theo_model"] != {M38: 1, M35: 1}, (
        "ban GOP phai lam phep kiem tren do; neu no van xanh thi phep kiem "
        "khong do dieu no tuyen bo")


def test_dong_mat_nhip_khong_nam_trong_do_sau(db):
    """Một dòng `cho` mất nhịp là tiến trình đã chết — đếm riêng, không phải tải.

    Cùng phép lọc mà `phong_cho.chup_nguoi_cho` dùng để **quyết định**, nên sổ
    và quyết định nói cùng một con số.
    """
    from platform_core import job_metrics
    from platform_core.llm.phong_cho import HAN_NHIP_CHO_S

    _cho(db, model=M38, tuoi_s=5.0, nhip_s=0.0)
    _cho(db, model=M38, tuoi_s=600.0, nhip_s=HAN_NHIP_CHO_S + 5)
    db.commit()

    k = job_metrics.llm_theo_model(db, now=T0, cutoff=T0 - timedelta(days=7))
    assert k["sau_theo_model"] == {M38: 1}
    assert k["mat_nhip_theo_model"] == {M38: 1}
    # Và tuổi lâu nhất KHÔNG lấy tuổi của cái xác: 600 s ấy là thời gian một
    # tiến trình đã chết nằm đó, không phải thời gian ai đó đang chờ.
    assert k["tuoi_lau_nhat_s_theo_model"][M38] == pytest.approx(5.0)


def test_phong_cho_vao_ghi_that_cot_model(db):
    """⛔ CỘT KHÔNG AI GHI LÀ MỘT CỘT CHẾT, và một khối metrics đọc nó sẽ vĩnh
    viễn rỗng trong khi mọi phép kiểm vẫn xanh.

    Ca này đi qua **bên ghi thật** (`phong_cho.vao`), không dựng `LlmWaiter` bằng
    tay như các ca trên: nó chứng minh đường từ `YeuCauCho.model` tới cột có nối.
    """
    from platform_core.llm import luat_nhan, phong_cho

    yc = phong_cho.YeuCauCho(
        resource="ltt_38_3090", slots=3, token_pool=221_184, user_id="u",
        mode="stream", holder_id="rq-1", request_id="rq-1", cua="stream",
        lop=luat_nhan.TUONG_TAC, token_dat_truoc=1000, model=M38)
    wid = phong_cho.vao(db, yc, now=T0)
    db.commit()

    from platform_core.models import LlmWaiter

    assert db.get(LlmWaiter, wid).model == M38

    from platform_core import job_metrics

    k = job_metrics.llm_theo_model(db, now=T0, cutoff=T0 - timedelta(days=7))
    assert k["sau_theo_model"] == {M38: 1}


def test_luot_khong_khai_model_vao_o_rieng_chu_khong_gop(db):
    from platform_core import job_metrics

    _cho(db, model="", tuoi_s=4.0)
    _cho(db, model=M38, tuoi_s=4.0)
    db.commit()

    k = job_metrics.llm_theo_model(db, now=T0, cutoff=T0 - timedelta(days=7))
    assert k["sau_theo_model"] == {job_metrics.KHONG_KHAI: 1, M38: 1}


def test_gio_cho_vi_cu_tru_tach_theo_model(db):
    """Cột `cho_residency_s` (rev `d91f6c37ab24`) chiếu ra theo model."""
    from platform_core import job_metrics

    _cho(db, model=M38, trang_thai="xong", cho_residency_s=30.0, tuoi_s=100)
    _cho(db, model=M38, trang_thai="xong", cho_residency_s=12.5, tuoi_s=90)
    _cho(db, model=M35, trang_thai="xong", cho_residency_s=0.0, tuoi_s=80)
    db.commit()

    k = job_metrics.llm_theo_model(db, now=T0, cutoff=T0 - timedelta(days=7))
    assert k["cho_residency_theo_model"][M38] == {
        "so_luot": 2, "tong_s": 42.5, "lau_nhat_s": 30.0}
    # 3.5 không chờ vì cư trú lần nào ⇒ **không có ô**, chứ không phải một ô 0
    # trông như đã đo. 5060 Ti không có trọng tài cư trú nào.
    assert M35 not in k["cho_residency_theo_model"]


# ══════════════════════════════════════════════════════════════════════════
#  2. `residency_3090` — dẫn xuất, không bộ đếm ghi tay
# ══════════════════════════════════════════════════════════════════════════

def _nhom(db, *, trang_thai, tu_luc, cua_so=None, lan_nap_loi=0, nhom="rtx3090"):
    from platform_core.models import GpuResidency

    row = GpuResidency(nhom=nhom, trang_thai=trang_thai, tu_luc=tu_luc,
                       cua_so_bat_dau=cua_so, lan_nap_loi=lan_nap_loi)
    db.add(row)
    db.flush()
    return row


def test_trang_thai_va_thoi_gian_trong_trang_thai(db):
    from platform_core import job_metrics
    from platform_core.llm import residency

    _nhom(db, trang_thai=residency.ANH, tu_luc=T0 - timedelta(seconds=75),
          cua_so=T0 - timedelta(seconds=200))
    db.commit()

    k = job_metrics.residency_3090(db, now=T0, tai_nguyen_theo_lo=())["nhom"]
    assert k["rtx3090"]["trang_thai"] == residency.ANH
    assert k["rtx3090"]["giay_trong_trang_thai"] == pytest.approx(75.0)
    assert k["rtx3090"]["cua_so_anh_mo"] is True
    assert k["rtx3090"]["giay_trong_cua_so"] == pytest.approx(200.0)


def test_khong_khai_tai_nguyen_theo_lo_thi_so_lan_la_None_khong_phai_0(db):
    """⛔ Số 0 ở đây nói "hôm nay 3090 không đổi cư trú lần nào" — một câu SAI
    về phía trấn an. Chưa app ảnh nào khai vai trò `theo_lo` (Task 5.5) thì câu
    trả lời đúng là *"không đo được"*.
    """
    from platform_core import job_metrics
    from platform_core.llm import residency

    _nhom(db, trang_thai=residency.LLM, tu_luc=T0)
    db.commit()

    nl = job_metrics.residency_3090(
        db, now=T0, tai_nguyen_theo_lo=())["nhom"]["rtx3090"]["nap_lai_hom_nay"]
    assert nl["so_lan"] is None and nl["giay_uoc"] is None
    assert nl["cach_do"] == "khong_khai_tai_nguyen_theo_lo"


def test_so_lan_nap_lai_dan_xuat_tu_jobs_theo_hai_tham_so_da_khai(db):
    """Hai cửa sổ ảnh cách nhau xa ⇒ hai lần nạp lại; và một dải dài hơn trần
    của một cửa sổ **buộc** phải là nhiều cửa sổ.

    Cả hai con số dùng để chia đều đọc từ `residency.ThamSoResidency` — không gõ
    lại ở đây, nên đổi tham số là phép kiểm đi theo chứ không hoá sai.
    """
    from platform_core import job_metrics
    from platform_core.llm import residency

    ts = residency.ThamSoResidency()
    _nhom(db, trang_thai=residency.LLM, tu_luc=T0)

    goc = T0.replace(hour=1, minute=0)
    # Cụm 1: đúng `cua_so_anh_toi_da` job sát nhau ⇒ đúng 1 cửa sổ.
    for i in range(int(ts.cua_so_anh_toi_da)):
        _job_anh(db, resource="anh_3090", job_id=f"a{i}",
                 admitted_at=goc + timedelta(seconds=10 * i))
    # Cụm 2: cách cụm 1 hơn trần thời lượng một cửa sổ ⇒ không thể cùng cửa sổ.
    _job_anh(db, resource="anh_3090", job_id="b0",
             admitted_at=goc + timedelta(seconds=ts.cua_so_anh_s + 600))
    db.commit()

    nl = job_metrics.residency_3090(
        db, now=T0.replace(hour=23),
        tai_nguyen_theo_lo=("anh_3090",))["nhom"]["rtx3090"]["nap_lai_hom_nay"]
    assert nl["so_lan"] == 2
    assert nl["cach_do"] == "can_duoi_tu_jobs"
    # Thời gian nạp lại là **ước** từ `t_nap_llm_s` (§G4/§G5) — đọc từ tham số.
    assert nl["giay_uoc"] == pytest.approx(2 * ts.t_nap_llm_s)


def test_job_anh_cua_hom_qua_khong_tinh_vao_hom_nay(db):
    from platform_core import job_metrics
    from platform_core.llm import residency

    _nhom(db, trang_thai=residency.LLM, tu_luc=T0)
    _job_anh(db, resource="anh_3090", job_id="cu",
             admitted_at=T0 - timedelta(days=1))
    db.commit()

    nl = job_metrics.residency_3090(
        db, now=T0, tai_nguyen_theo_lo=("anh_3090",))["nhom"]["rtx3090"][
            "nap_lai_hom_nay"]
    assert nl["so_lan"] == 0


def test_anh_da_nhan_trong_cua_so_dem_tu_jobs(db):
    """⛔ Đếm từ bảng `jobs`, không từ một bộ đếm trong `gpu_residency`."""
    from platform_core import job_metrics
    from platform_core.llm import residency

    mo = T0 - timedelta(seconds=300)
    _nhom(db, trang_thai=residency.ANH, tu_luc=mo, cua_so=mo)
    _job_anh(db, resource="anh_3090", job_id="trong1",
             admitted_at=mo + timedelta(seconds=10))
    _job_anh(db, resource="anh_3090", job_id="trong2",
             admitted_at=mo + timedelta(seconds=20))
    _job_anh(db, resource="anh_3090", job_id="ngoai",
             admitted_at=mo - timedelta(seconds=60))
    db.commit()

    k = job_metrics.residency_3090(
        db, now=T0, tai_nguyen_theo_lo=("anh_3090",))["nhom"]["rtx3090"]
    assert k["anh_da_nhan_trong_cua_so"] == 2


# ══════════════════════════════════════════════════════════════════════════
#  3. `snapshot` mang cả hai khối
# ══════════════════════════════════════════════════════════════════════════

def test_snapshot_mang_ca_hai_khoi_moi(db):
    from platform_core import job_metrics
    from platform_core.llm import residency

    _cho(db, model=M38, tuoi_s=4.0)
    _nhom(db, trang_thai=residency.LLM, tu_luc=T0 - timedelta(seconds=9))
    db.commit()

    s = job_metrics.snapshot(db, now=T0, tai_nguyen_theo_lo=())
    assert s["llm_theo_model"]["sau_theo_model"] == {M38: 1}
    assert s["residency_3090"]["nhom"]["rtx3090"]["trang_thai"] == residency.LLM
    # Khối cũ không được suy suyển — `test_277`/`test_378` đang đọc chúng.
    assert "queue_depth_by_resource" in s and "stale_jobs" in s


def test_ops_jobs_metrics_chieu_ra_hai_khoi_moi(db, monkeypatch):
    """`/ops/jobs-metrics` — chốt trên chính hàm route, không mô phỏng lại nó.

    ⭐ Gọi thẳng `jobs_metrics(...)` thay vì dựng cả ứng dụng: thứ đang kiểm là
       *route có chiếu hai khối ra không*, và một `TestClient` đầy đủ sẽ kéo theo
       đăng nhập, `discover()` và mọi app — tức nó sẽ đo mười thứ khác rồi đỏ vì
       một thứ không liên quan.
    """
    from platform_core import job_metrics
    from platform_core.llm import residency
    from server.routes import jobs as route_jobs

    # 🔴 GIEO THEO ĐỒNG HỒ THẬT, không theo `T0`.
    #
    #    Ca này gọi **route**, mà route không nhận `now` — `job_metrics.snapshot`
    #    dùng `datetime.now(timezone.utc)`. Neo hạt giống vào hằng `T0` (09:00 UTC
    #    ngày 12/09) biến phép kiểm thành một **quả bom hẹn giờ**: nhịp tim
    #    của người chờ già dần theo giờ treo tường, và khi nó vượt
    #    `HAN_NHIP_CHO_S` thì `job_metrics` xếp người chờ sang `mat_nhip`, nên
    #    `sau_theo_model` rỗng.
    #
    # ⭐ Đo được 12/09: gate lúc 09:04 UTC **XANH** (mốc mới 4 phút), gate lúc
    #    10:36 UTC **ĐỎ** (mốc đã 1,7 giờ) — cùng một commit, không một dòng mã
    #    nào đổi. Một phép kiểm hết hạn lúc 09:00 UTC.
    #
    # ⚠️ 28 chỗ dùng `T0` khác trong tệp này **đúng như cũ**: chúng tiêm
    #    `now=T0` vào `job_metrics`, nên mốc giả và đồng hồ giả khớp nhau.
    #    Chỉ ca **đi qua route** là lệch, và chỉ ca đó được sửa.
    bay_gio = datetime.now(timezone.utc)
    _cho(db, model=M35, tuoi_s=2.0, moc=bay_gio)
    _nhom(db, trang_thai=residency.NAP_LLM, tu_luc=bay_gio)
    db.commit()

    # Danh sách app rỗng: phép kiểm này hỏi *route có chiếu hai khối ra không*,
    # không hỏi *kho có bao nhiêu app*. Khối toàn cục vẫn đi qua `snapshot` thật.
    import platform_core.registry as registry

    monkeypatch.setattr(registry, "discover", lambda *a, **k: [])

    ra = route_jobs.jobs_metrics(None, _operator="op")
    assert ra["metrics"]["llm_theo_model"]["sau_theo_model"] == {M35: 1}
    assert (ra["metrics"]["residency_3090"]["nhom"]["rtx3090"]["trang_thai"]
            == residency.NAP_LLM)


# ══════════════════════════════════════════════════════════════════════════
#  4. Vòng bảo trì gọi `phong_cho.don_het_han` (Multi-Job T12)
# ══════════════════════════════════════════════════════════════════════════

def test_bao_tri_goi_don_het_han_cua_phong_cho(db, monkeypatch):
    """Bánh cóc cho một dây đã nối: `_don_du_lieu_het_han` phải gọi hàm THẬT.

    ⛔ Không grep vào mã nguồn. `test_981`/bộ nhớ dự án đã ghi vì sao: một bộ dò
       quét văn bản trừng phạt việc giải thích và bỏ lọt việc đổi tên. Ở đây phép
       kiểm gọi chính vòng bảo trì rồi **đếm số lần hàm được gọi** — một mệnh đề
       dương, nên xoá lời gọi đi là nó đỏ.
    """
    from platform_core import job_runner
    from platform_core.llm import phong_cho

    da_goi = []
    that = phong_cho.don_het_han

    def theo_doi(db_, **kw):
        da_goi.append(1)
        return that(db_, **kw)

    monkeypatch.setattr(phong_cho, "don_het_han", theo_doi)
    job_runner._don_du_lieu_het_han()
    assert da_goi, ("vong bao tri khong con goi phong_cho.don_het_han -- so "
                    "luot LLM se noi 'dang cho' mai mai")


def test_don_het_han_chot_dong_mat_nhip_va_giu_dong_con_song(db):
    """Và nó phải làm **đúng một việc**: chốt cái chết, giữ cái sống.

    Đối chứng nằm ngay trong cùng một ca: nếu `don_het_han` chốt tất, dòng còn
    sống cũng thành `het_han` và khẳng định thứ hai đỏ.
    """
    from platform_core.llm import phong_cho

    song = _cho(db, model=M38, tuoi_s=5.0, nhip_s=0.0)
    chet = _cho(db, model=M38, tuoi_s=3600.0,
                nhip_s=phong_cho.HAN_CHO_MO_COI.total_seconds() + 60)
    db.commit()

    phong_cho.don_het_han(db, now=T0)
    db.commit()
    db.refresh(song)
    db.refresh(chet)
    assert chet.trang_thai == "het_han" and chet.ket_qua == "mat_nhip"
    assert song.trang_thai == "cho"
