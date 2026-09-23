"""test_307 — ⛔ GIỮ CHỖ TREO: tiền khách bị giữ mà không ai còn kết sổ được.

Không mạng, không GPU.

## ⭐ VÌ SAO TỆP NÀY TỒN TẠI — nó không phòng xa, nó dọn một vụ đã xảy ra

Đo trên CSDL production 2026-08-26: **hai** bút toán `hold` ngày 24/08 không có
`settle`, không có `refund`, và không có hàng `Job` nào để chỉ vào.

    ms:de4cc565…   1 credit   2026-08-24 22:28:06
    ms:84e9b141…   1 credit   2026-08-24 23:58:10

Số dư khách bị trừ vĩnh viễn — sổ credit là **chỉ ghi thêm**, nên nó không tự
lành.

## ⛔ ĐIỀU ĐÁNG SỢ HƠN CẢ SỐ TIỀN

Máy dò **đã tồn tại** trước khi có tệp này: `public_api/usage.reconcile()` đếm
`holds_without_job`. Nhưng vị ngữ của nó là `job_id == ""` — **rỗng** — trong khi
cả bốn đường giữ chỗ trong-request đều truyền id **khác rỗng** (`request_id`,
`umsg_id`, `run.id`), và `thanh_toan.giu_cho_luot` còn `raise ValueError` nếu id
rỗng.

⇒ Máy dò bắt **0/2** trên chính dữ liệu thật. Chuông đã đúc, chưa ai treo, và nó
được chỉnh để nghe đúng thứ âm thanh không bao giờ phát ra.

Và trong hai lần đó, **chỉ một** được người ghi lại. Tỉ lệ phát hiện thủ công
1/2 — nghĩa là con số thật **≥** con số biết, không bao giờ nhỏ hơn.

## 💡 CHỖ DỄ VIẾT SAI, GHI RA VÌ NÓ LÀ CHỖ YẾU NHẤT

Cám dỗ là báo mọi `hold` chưa kết sổ. Làm vậy thì mỗi job đang nằm trong hàng đợi
đều thành một báo động — và một máy dò kêu suốt ngày là một máy dò bị tắt trong
tuần đầu. Nên `test_job_dang_cho_thi_khong_phai_treo` là phép kiểm quan trọng
ngang phép kiểm bắt được lỗi thật: nó chốt rằng cái chuông **im khi phải im**.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'treo.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def _hold(db, *, user_id: str, job_id: str, credit: int, gio_truoc: float = 0.0):
    """Ghi thẳng một bút toán `hold` với tuổi tuỳ ý."""
    from platform_core.models import CREDIT_HOLD, CreditEntry
    row = CreditEntry(
        user_id=user_id, delta=-int(credit), kind=CREDIT_HOLD, job_id=job_id,
        note="test",
        created_at=datetime.now(timezone.utc) - timedelta(hours=gio_truoc))
    db.add(row); db.commit()
    return row


# ── Cái chuông phải KÊU ────────────────────────────────────────────────────────

def test_giu_cho_khong_co_khoa_bi_bat_ngay_khong_can_cho_het_han(db):
    """`job_id` rỗng = không ai còn kết sổ được, vì khoá kết sổ không tồn tại.

    `quyet_toan` và `hoan` đều tra theo `job_id`. Một bút toán không có khoá thì
    hỏng **ngay từ lúc sinh** — chờ thêm 6 tiếng không làm nó bớt hỏng.
    """
    from platform_core import credit

    _hold(db, user_id="u1", job_id="", credit=5, gio_truoc=0)
    treo = credit.giu_cho_treo(db)
    assert len(treo) == 1
    assert treo[0].ly_do == "khong_co_khoa"
    assert treo[0].credit == 5


def test_bat_duoc_dung_ca_da_xay_ra_that_tren_production(db):
    """Ca `ms:84e9b141…` — id KHÁC RỖNG, không có hàng Job, quá hạn.

    Đây chính là ca mà vị ngữ cũ (`job_id == ""`) bắt hụt. Nếu test này đỏ thì
    lỗi 24/08 đã quay lại.
    """
    from platform_core import credit

    _hold(db, user_id="u1", job_id="ms:84e9b141", credit=1, gio_truoc=48)
    treo = credit.giu_cho_treo(db)
    assert [t.job_id for t in treo] == ["ms:84e9b141"]
    assert treo[0].ly_do == "khong_ai_ket_so"


def test_giu_cho_theo_ma_LUOT_CHAY_khong_phai_job_van_bi_bao(db):
    """Không có vòng quét nào thu hồi một **lượt chạy** treo (đã kiểm 2026-08-26).

    Nên tiền của nó đúng là tiền không có đường về, và phải được báo.

    🗑️ 23/09 (plan 01b Task 9): bài này từng mang tên `AgentRun`. Model đó đã
       được gỡ — nhưng nó **chưa bao giờ** là đối tượng của bài: bài chỉ dựng
       một bút toán `hold` có khoá là mã một **lượt chạy**, không phải mã một
       `Job`. Hình dạng ấy còn nguyên ở v3 (`platform_core/workflow/tien.py:61`
       giữ chỗ theo `run.id`), nên tính chất còn sống và bài chỉ đổi tên.
    """
    from platform_core import credit

    _hold(db, user_id="u1", job_id="run-abc", credit=20, gio_truoc=12)
    assert len(credit.giu_cho_treo(db)) == 1


# ── Cái chuông phải IM ─────────────────────────────────────────────────────────

def test_job_dang_cho_thi_khong_phai_treo(db):
    """⛔ Hàng đợi tắc **không phải** tiền treo — nó chỉ là hàng đợi tắc.

    Một máy dò kêu vì công việc bình thường là một máy dò sẽ bị tắt.
    """
    from platform_core import credit
    from platform_core.models import JOB_QUEUED, Job

    db.add(Job(id="job-1", user_id="u1", app_slug="thu", job_type="thu.x",
               status=JOB_QUEUED, params={}))
    db.commit()
    _hold(db, user_id="u1", job_id="job-1", credit=9, gio_truoc=48)

    assert credit.giu_cho_treo(db) == []


def test_con_trong_han_thi_chua_ket_luan(db):
    """Một luồng LLM đo được 119 giây. Báo động sau 2 phút là báo động về chính
    công việc đang chạy đúng."""
    from platform_core import credit

    _hold(db, user_id="u1", job_id="ms:dang-chay", credit=3, gio_truoc=0.05)
    assert credit.giu_cho_treo(db) == []


def test_da_quyet_toan_thi_khong_treo(db):
    from platform_core import credit
    from platform_core.models import CREDIT_SETTLE, CreditEntry

    _hold(db, user_id="u1", job_id="ms:xong", credit=7, gio_truoc=48)
    db.add(CreditEntry(user_id="u1", delta=7, kind=CREDIT_SETTLE,
                       job_id="ms:xong", note="test"))
    db.commit()
    assert credit.giu_cho_treo(db) == []


def test_da_hoan_thi_khong_treo(db):
    from platform_core import credit
    from platform_core.models import CREDIT_REFUND, CreditEntry

    _hold(db, user_id="u1", job_id="ms:hoan", credit=7, gio_truoc=48)
    db.add(CreditEntry(user_id="u1", delta=7, kind=CREDIT_REFUND,
                       job_id="ms:hoan", note="test"))
    db.commit()
    assert credit.giu_cho_treo(db) == []


def test_khong_bao_gio_sua_gi(db):
    """Hàm này CHỈ ĐỌC. Tự hoàn tiền là một quyết định tiền, thuộc chủ sản phẩm.

    Chốt bằng số dư trước/sau, không bằng lời hứa trong docstring.
    """
    from platform_core import credit

    _hold(db, user_id="u1", job_id="", credit=5, gio_truoc=48)
    truoc = credit.so_du(db, "u1")
    credit.giu_cho_treo(db)
    assert credit.so_du(db, "u1") == truoc


def test_tran_chan_khong_cho_tai_ca_so_ve(db):
    from platform_core import credit

    for i in range(12):
        _hold(db, user_id="u1", job_id=f"ms:{i}", credit=1, gio_truoc=48)
    assert len(credit.giu_cho_treo(db, tran=5)) == 5


# ── Cái chuông phải ĐƯỢC TREO ─────────────────────────────────────────────────
#
# ⭐ Ba phép kiểm dưới đây tồn tại vì **P-01**: trong kho này đã có HAI cái
#    chuông được đúc rồi bỏ đó.
#
#    ① `usage.reconcile` đếm giữ chỗ mồ côi — chỉ được gọi từ test và một lệnh
#       CLI thủ công; vòng bảo trì không đụng tới.
#    ② `costing.scan_for_alerts` báo biên lợi nhuận âm cho người trực — có test,
#       có trong `__all__`, và **không gì gọi nó** ngoài chính test của nó.
#
#    Một hàm cảnh báo không được cắm vào đâu thì trông y hệt một hàm cảnh báo
#    đang chạy, cho tới ngày cần nó. Nên "có hàm" không phải điều đáng chốt —
#    "hàm được GỌI" mới là.

def test_chuong_duoc_cam_vao_vong_bao_tri():
    """Chốt bằng mã nguồn: quét treo phải được vòng bảo trì gọi thật.

    Không chốt bằng "hàm tồn tại" — đó chính là cái bẫy P-01.
    """
    import inspect

    from platform_core import job_runner

    bao_tri = inspect.getsource(job_runner._mot_luot_bao_tri)
    assert "_quet_giu_cho_treo()" in bao_tri, (
        "quet giu cho treo khong duoc goi tu vong bao tri — chuong chua duoc treo")


def test_chay_duoi_lease_bao_tri_nen_khong_bao_N_lan():
    """`_mot_luot_bao_tri` chạy dưới lease `bao_tri`, nên toàn cụm một lần.

    Nếu đặt nhầm vào vòng job thì mỗi tiến trình worker gửi một thư về **cùng
    một khoản tiền** — số tiến trình mặc định bằng số GPU.
    """
    import inspect

    from platform_core import job_runner

    vong = inspect.getsource(job_runner._vong_bao_tri)
    assert "leases.acquire" in vong and "leases.MAINTENANCE" in vong


def test_bao_cao_va_khu_trung_lap_theo_tung_khoan(db, monkeypatch):
    """Báo một lần cho mỗi khoản; lượt sau im. Và khoản MỚI vẫn được báo.

    Khử trùng lặp theo `subject` = khoá của chính khoản đó, nên một khoản đang
    chờ xử lý không làm im lặng một khoản khác vừa xuất hiện.
    """
    from platform_core import job_runner
    from platform_core.models import User
    from platform_core.public_api.tables import ApiNotification

    db.add(User(id="admin-1", email="ops@x.test", password_hash="x",
                role="admin", is_active=True))
    db.commit()

    _hold(db, user_id="u1", job_id="ms:treo-1", credit=4, gio_truoc=48)

    # `_one_session` mở session riêng; trỏ nó về đúng CSDL test của fixture.
    monkeypatch.setattr(job_runner, "_one_session", lambda: iter([db]))
    monkeypatch.setattr(
        "platform_core.public_api.notifications.send_email_for",
        lambda *a, **k: None)

    assert job_runner._quet_giu_cho_treo() == 1
    assert job_runner._quet_giu_cho_treo() == 0        # cooldown — im

    _hold(db, user_id="u1", job_id="ms:treo-2", credit=6, gio_truoc=48)
    assert job_runner._quet_giu_cho_treo() == 1        # khoản MỚI vẫn kêu

    chu_de = {r.subject for r in db.execute(
        __import__("sqlalchemy").select(ApiNotification)).scalars().all()}
    assert chu_de == {"hold:ms:treo-1", "hold:ms:treo-2"}


def test_quet_khong_bao_gio_dong_vao_tien(db, monkeypatch):
    """⛔ Bước này CHỈ BÁO. Tự ghi bút toán bù là quyết định của chủ sản phẩm."""
    from platform_core import credit, job_runner
    from platform_core.models import User

    db.add(User(id="admin-1", email="ops@x.test", password_hash="x",
                role="admin", is_active=True))
    db.commit()
    _hold(db, user_id="u1", job_id="ms:treo-1", credit=4, gio_truoc=48)

    monkeypatch.setattr(job_runner, "_one_session", lambda: iter([db]))
    monkeypatch.setattr(
        "platform_core.public_api.notifications.send_email_for",
        lambda *a, **k: None)

    truoc = credit.so_du(db, "u1")
    job_runner._quet_giu_cho_treo()
    assert credit.so_du(db, "u1") == truoc
    assert credit.giu_cho_treo(db)          # vẫn treo — chưa ai sửa gì cả


def test_chuong_bien_loi_nhuan_am_cung_da_duoc_treo():
    """M-02 — ca thứ hai của cùng loại lỗi, tìm ra trong lúc sửa ca thứ nhất.

    `costing.scan_for_alerts` có docstring, có test (`test_207`), có tên trong
    `__all__` — và cho tới 2026-08-26 **không gì gọi nó** ngoài chính test của
    nó. Nghĩa là cảnh báo "nền tảng đang bán lỗ" chưa từng nổ trên production,
    trong khi `docs/PHAN_TICH_MVP_2026-08-23.md` đo được ảnh bán ở 45–57 % giá
    vốn suốt 22 ngày.

    Hai ca, một hình dạng. Nếu chỉ sửa ca đầu thì đã bỏ lỡ điều nó đang nói.
    """
    import inspect

    from platform_core import job_runner

    src = inspect.getsource(job_runner._quet_canh_bao)
    assert "costing.scan_for_alerts(db)" in src, (
        "canh bao bien loi nhuan am van chua duoc cam vao vong bao tri")


def test_viec_bao_tri_cua_app_chay_duoi_lease_nen_khong_tru_tien_N_lan():
    """M-03 — `credit.tru()` là TRỪ THẲNG, không giữ chỗ. Chạy hai lần trong một
    chu kỳ là trừ khách hai lần.

    Hai chỗ dùng nó đều là mô hình thuê bao và đều chạy qua
    `AppManifest.bao_tri`: `apps/vps/services/billing.py` và
    `platform_core/nexus/billing.py`.

    ⭐ Bất biến bảo vệ chúng **không** nằm trong hai tệp đó — nó nằm ở chỗ
       `_bao_tri_cac_app` được gọi từ **bên trong** `_mot_luot_bao_tri`, mà cả
       khối đó chạy dưới lease `bao_tri`. Nên đây mới là chỗ đáng chốt.

    ⛔ `CLAUDE.md` ghi thẳng cái giá của việc đặt sai chỗ: *"app tự dựng vòng lặp
       sẽ trừ tiền khách N lần mỗi chu kỳ"* — số tiến trình worker mặc định bằng
       số GPU.
    """
    import inspect

    from platform_core import job_runner

    bao_tri = inspect.getsource(job_runner._mot_luot_bao_tri)
    assert "_bao_tri_cac_app(moc)" in bao_tri, (
        "viec bao tri cua app khong con chay trong `_mot_luot_bao_tri` => no da "
        "ra ngoai lease `bao_tri`, va moi tien trinh worker se chay no mot lan")
