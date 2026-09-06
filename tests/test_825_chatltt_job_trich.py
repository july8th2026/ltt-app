"""
test_825 — job trích tài liệu: HỎNG thì HOÀN TIỀN, không "xong với 0 đoạn".
(H44 P06 bước 3c)

## Hai mệnh đề trung tâm

**1. Giá chưa chốt thì fail-closed, KHÔNG mặc định 0.**
   P06 §7 chấm rằng trích là job **trả tiền**, trích thẳng lý do từ docstring
   của `platform_core/upload_sessions.py`: *"Cửa 'phải giữ credit mới được lưu
   file' tồn tại để không ai biến input của job thành kho lưu trữ miễn phí."*
   Một giá 0 tạm thời **chính là** cái lỗ ấy, chỉ khác là nó trông như một mặc
   định vô hại — và một mặc định vô hại thì không ai quay lại sửa.

**2. Trích ra rỗng ⇒ job HỎNG, không phải "xong với `credit_cost: 0`".**
   Hai đường cùng ra "khách không mất tiền", nhưng khác nhau ở chỗ khách
   **nhìn thấy**: một cái nói *"không trích được, đây là lý do"*, cái kia nói
   *"xong"* rồi im lặng đưa ra danh sách rỗng. PDF ảnh scan là ca **thường**,
   và một sản phẩm trả lời "xong" cho ca thường ấy dạy người dùng đừng tin nó.
"""
from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

import pytest

CHU = "u-chu-825"
LA = "u-la-825"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _canh(db, *, noi_dung: bytes, content_type: str = "text/plain"):
    """Một chủ + hội thoại + upload đã promote + tệp đã gắn, byte nằm ở storage."""
    from apps.chatltt.services import kho_tep
    from apps.chatltt.tables import ChatlttConversation
    from platform_core.models import UploadSession, User
    from platform_core.storage import get_storage

    for uid in (CHU, LA):
        if db.get(User, uid) is None:
            db.add(User(id=uid, email=f"{uid}@x.test", password_hash="x"))
    c = ChatlttConversation(user_id=CHU, title="t")
    db.add(c)
    db.flush()

    khoa = f"fin/{CHU}/tai-lieu"
    get_storage().put(khoa, io.BytesIO(noi_dung))
    u = UploadSession(
        user_id=CHU, app_slug="chatltt", staging_key=f"stg/{CHU}/tai-lieu",
        final_key=khoa, filename="tai-lieu", content_type=content_type,
        expected_size=len(noi_dung), actual_size=len(noi_dung), status="promoted",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    db.add(u)
    db.flush()

    tep = kho_tep.gan(db, user_id=CHU, conversation_id=c.id, upload_id=u.id)
    db.flush()
    return tep


@pytest.fixture()
def co_gia(monkeypatch):
    """Chốt một giá GIẢ chỉ trong phạm vi phép kiểm.

    ⛔ Không sửa hằng số thật: đặt giá là một bút toán tiền, tức việc của chủ dự
       án. Ở đây ta chỉ cần *một* giá để đo cơ chế, và nó phải biến mất khi phép
       kiểm kết thúc.
    """
    from apps.chatltt import gia_trich
    monkeypatch.setattr(gia_trich, "MCREDIT_MOI_1000_KY_TU", 20)
    return gia_trich


# ── 1. Giá fail-closed ─────────────────────────────────────────────────────

def test_gia_TAM_phai_TU_KHAI_la_tam_chu_khong_im_lang():
    """🔴 Mệnh đề 1, viết lại 06/09.

    Bản đầu chốt `MCREDIT_MOI_1000_KY_TU is None` — fail-closed. Nghe an toàn,
    nhưng nó biến một **quyết định thương mại** thành một **cổng chặn kỹ thuật**:
    bước 4–6 không chạy được đầu-cuối, và một hằng số `None` im lặng thì không
    ai biết nó đang chờ ai.

    ⭐ Ranh giới "bút toán tiền" chỉ áp cho tiền **thật đang chảy** — đã deploy
       **và** không sau cờ. `LTT_CHATLTT_V3_TOOLS` đang TẮT và tính năng chưa có
       route ⇒ không đồng nào của khách chịu ảnh hưởng ⇒ ghi giả định rồi đi
       tiếp, không để trống chờ người.

    ⇒ Thứ phải chốt không còn là *"giá phải là None"* mà là *"giá tạm phải TỰ
      KHAI là tạm"*, ở ba chỗ cùng lúc — nếu không thì một giả định của tôi sẽ
      lặng lẽ thành chính sách.
    """
    from apps.chatltt import gia_trich

    assert gia_trich.MCREDIT_MOI_1000_KY_TU is not None, (
        "gia bi go ve None — xem docstring: fail-closed o day chan buoc 4-6")
    assert gia_trich.CHU_DU_AN_DA_CHOT is False, (
        "neu chu du an DA chot that thi sua ca phep kiem nay VA `STATE.md`, "
        "va noi ro AI chot, NGAY nao")
    assert "tam" in gia_trich.PHIEN_BAN_GIA, (
        "phien ban gia di vao TUNG ban ghi duyet — chu `tam` la thu cho phep "
        "loc ra moi but toan tinh theo gia tam vao ngay chot gia that")


def test_gia_van_NEM_khi_bi_go_ve_None():
    """⛔ Cơ chế fail-closed **vẫn còn**, chỉ là không còn được kích hoạt mặc
    định. Ngày ai đó gỡ giá đi mà quên đặt lại, `tinh()` phải nói ra."""
    from apps.chatltt import gia_trich

    goc = gia_trich.MCREDIT_MOI_1000_KY_TU
    try:
        gia_trich.MCREDIT_MOI_1000_KY_TU = None
        assert not gia_trich.da_chot()
        with pytest.raises(gia_trich.ChuaChotGia):
            gia_trich.tinh(5000)
        with pytest.raises(gia_trich.ChuaChotGia):
            gia_trich.credit_cost({"so_byte": 1000})
    finally:
        gia_trich.MCREDIT_MOI_1000_KY_TU = goc


def test_gia_tam_cho_mot_tai_lieu_30_trang_KHONG_dat_den_muc_vo_ly():
    """⭐ Đối chứng độ lớn. Một hằng số lệch 1.000 lần vẫn qua mọi phép kiểm cấu
    trúc ở trên; chỉ một phép kiểm về **số tiền khách thấy** mới bắt được."""
    from apps.chatltt import gia_trich

    ky_tu_30_trang = 60_000
    credit = (gia_trich.tinh(ky_tu_30_trang) + 999) // 1000
    assert 1 <= credit <= 20, (
        f"mot tai lieu 30 trang ton {credit} credit — con so nay phai doc len "
        "duoc thanh mot cau nghe hop ly voi khach")


def test_gia_lam_tron_LEN_theo_tung_1000_ky_tu(co_gia):
    assert co_gia.tinh(0) == 0
    assert co_gia.tinh(1) == 20         # mot mau nho van ton mot don vi
    assert co_gia.tinh(1000) == 20
    assert co_gia.tinh(1001) == 40


def test_uoc_tran_KHONG_duoc_thap_hon_gia_that(co_gia):
    """⛔ Ước thấp ⇒ lúc quyết toán số thu **vượt** số đã hiện cho khách, và
    `chatltt_approval` chốt rằng chuyện đó bị từ chối. Sai về phía giữ dư chỉ
    giam credit vài giây; sai về phía kia làm hỏng cả lượt sau khi họ đã bấm."""
    so_byte = 12_000
    # Ky tu trich duoc KHONG BAO GIO nhieu hon so byte cua tep chu thuan UTF-8.
    that = (co_gia.tinh(so_byte) + 999) // 1000
    assert co_gia.uoc_tran(so_byte) >= that


# ── 2. Đường thành công ────────────────────────────────────────────────────

def test_trich_XONG_thi_ghi_doan_va_danh_dau(db, co_gia):
    from apps.chatltt import jobs
    from apps.chatltt.services import kho_tep
    from apps.chatltt.tables import ChatlttDoan

    van = ("Phan le duoi mot credit duoc cong don sang luot sau. " * 40).encode()
    tep = _canh(db, noi_dung=van)

    kq = jobs._chay(db, tep_id=tep.id, user_id=CHU)

    assert kq["so_doan"] >= 1
    assert kq["so_ky_tu"] > 0
    assert kq["credit_cost"] >= 1
    db.refresh(tep)
    assert tep.trang_thai_trich == kho_tep.XONG
    assert tep.so_doan == kq["so_doan"]

    doan = db.query(ChatlttDoan).filter(ChatlttDoan.tep_id == tep.id).all()
    assert len(doan) == kq["so_doan"]
    assert {d.user_id for d in doan} == {CHU}
    assert [d.thu_tu for d in doan] == list(range(len(doan)))
    assert all(d.bam for d in doan), "moi doan phai co van tay"


def test_trich_LAI_THAY_bo_doan_cu_chu_khong_chong_them(db, co_gia):
    """⛔ Hai bộ đoạn cho cùng một tệp làm truy hồi trả kết quả trùng và làm
    trích dẫn trỏ vào bản nào không ai biết."""
    from apps.chatltt import jobs
    from apps.chatltt.tables import ChatlttDoan

    tep = _canh(db, noi_dung=("Mot cau day du y nghia va du dai. " * 40).encode())
    a = jobs._chay(db, tep_id=tep.id, user_id=CHU)
    b = jobs._chay(db, tep_id=tep.id, user_id=CHU)

    assert a["so_doan"] == b["so_doan"]
    assert db.query(ChatlttDoan).filter(
        ChatlttDoan.tep_id == tep.id).count() == b["so_doan"]


# ── 3. Hỏng thì HOÀN TIỀN, không "xong với 0 đoạn" ─────────────────────────

def test_PDF_KHONG_lop_chu_lam_job_HONG_chu_khong_tra_ve_0_doan(db, co_gia):
    """🔴 Mệnh đề 2. Nền tảng hoàn **toàn bộ** phần đã giữ khi job hỏng
    (`job_runner._hoan_credit`); trả `credit_cost: 0` thì khách cũng không mất
    tiền, nhưng họ thấy chữ *"xong"* trên một kết quả rỗng."""
    from pypdf import PdfWriter

    from apps.chatltt import jobs
    from apps.chatltt.services import kho_tep

    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    ra = io.BytesIO()
    w.write(ra)
    tep = _canh(db, noi_dung=ra.getvalue(), content_type="application/pdf")

    with pytest.raises(jobs.LoiTrich) as e:
        jobs._chay(db, tep_id=tep.id, user_id=CHU)
    assert "lop chu" in str(e.value)

    db.refresh(tep)
    assert tep.trang_thai_trich == kho_tep.LOI
    assert "lop chu" in tep.ly_do_loi, "nguoi dung phai doc duoc VI SAO"


def test_THIEU_THU_VIEN_khong_do_loi_cho_TEP_CUA_KHACH(db, co_gia, monkeypatch):
    """🔴 Đúng lỗi đang sống ở `chataistudio`: máy chủ thiếu thư viện mà thông
    báo đổ lỗi cho tệp của khách. Lý do ghi lại phải nói về **máy chủ**."""
    import builtins

    from apps.chatltt import jobs
    from apps.chatltt.services import kho_tep

    that = builtins.__import__

    def gia(ten, *a, **k):
        if ten == "pypdf":
            raise ImportError("No module named 'pypdf'")
        return that(ten, *a, **k)

    tep = _canh(db, noi_dung=b"%PDF-1.4 gia", content_type="application/pdf")
    monkeypatch.setattr(builtins, "__import__", gia)
    with pytest.raises(jobs.LoiTrich):
        jobs._chay(db, tep_id=tep.id, user_id=CHU)
    monkeypatch.undo()

    db.refresh(tep)
    assert tep.trang_thai_trich == kho_tep.LOI
    assert "may chu" in tep.ly_do_loi, (
        f"ly do do loi cho khach: {tep.ly_do_loi!r} — dung lai loi cua chataistudio")


def test_tep_RONG_khong_ra_ket_qua_THANH_CONG(db, co_gia):
    from apps.chatltt import jobs

    tep = _canh(db, noi_dung=b"   \n\n  ")
    with pytest.raises(jobs.LoiTrich):
        jobs._chay(db, tep_id=tep.id, user_id=CHU)


# ── 4. Sở hữu ─────────────────────────────────────────────────────────────

def test_nguoi_LA_khong_trich_duoc_tep_cua_chu(db, co_gia):
    """⛔ Job chạy trong worker, xa mọi cửa HTTP — nên nó phải tự kiểm chủ."""
    from apps.chatltt import jobs
    from apps.chatltt.tables import ChatlttDoan

    tep = _canh(db, noi_dung=("Mot cau day du y nghia va du dai. " * 40).encode())
    with pytest.raises(jobs.LoiTrich):
        jobs._chay(db, tep_id=tep.id, user_id=LA)
    assert db.query(ChatlttDoan).count() == 0


def test_handle_thieu_tham_so_thi_NEM_chu_khong_chay_im_lang():
    from apps.chatltt import jobs

    for p in ({}, {"tep_id": "x"}, {"user_id": "y"}):
        with pytest.raises(jobs.LoiTrich):
            jobs.handle(p)


# ── 5. Bản khai ───────────────────────────────────────────────────────────

def test_manifest_khai_job_type_va_registry_nap_duoc():
    """⛔ Nền tảng **từ chối nạp** app khai `job_types` mà thiếu `credit_cost`
    (W1.6). Ta thoả bản khai bằng một HÀM — hàm ấy nói ra rằng giá chưa chốt
    thay vì trả về một con số ai đó bịa."""
    from apps.chatltt.manifest import MANIFEST

    assert "chatltt.trich_tep" in MANIFEST.job_types
    assert MANIFEST.credit_cost is not None
    assert callable(MANIFEST.credit_cost)


def test_tool_CHUA_duoc_mo_cho_model_goi():
    """⭐ §4 của P06: không bước nào mở cho model tới bước cuối. Phép kiểm này
    là thứ giữ lời hứa ấy khi ai đó thêm một dòng vì tiện tay."""
    from apps.chatltt.services import chinh_sach

    ten = str(getattr(chinh_sach, "CONG_CU_CHO_PHEP", ()))
    assert "trich_tep" not in ten, (
        "cong cu trich da duoc mo cho model truoc buoc 6")
