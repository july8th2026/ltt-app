"""
Hardening đường inference — chốt **double-submit ở màn Studio**.

`test_375` đã chốt màn **Dự án**: bấm "Đọc tất cả" hai lần không sinh việc trùng,
vì trạng thái khối (`dang_tao`) tự nó là khoá. Nhưng màn **Studio** (`POST
/ltt-voice/tao`) đi một đường khác: nó nộp thẳng một job `synthesize`, không có
trạng thái khối nào che, và `submit_with_credit` chỉ chống trùng khi được truyền
`dedupe_key`.

🔴 VÌ SAO ĐÂY LÀ CHUYỆN TIỀN, KHÔNG PHẢI TIỆN LỢI:

   Khách gõ một đoạn, bấm "Tạo". Job vào hàng đợi, màn hình chưa đổi gì ngay
   (`admission_resource=vieneu_gpu, slots=1` nên nó có thể đứng chờ một job
   khác). Khách bấm lại, hoặc mở hai tab, hoặc F5 một POST. Không có `dedupe_key`
   thì **mỗi lần bấm là một job mới + một lần giữ credit mới** — khách trả tiền
   hai lần cho đúng một đoạn, và nhận về hai tệp giống nhau.

⛔ Vô hiệu hoá nút ở trình duyệt KHÔNG phải bản vá: nó chặn được một tab, không
   chặn được hai tab hay một lần tải lại. Chốt phải ở phía máy chủ — đúng câu
   `platform_core/job_submit.py` đã nói: *"Mọi route submit NÊN truyền khoá này
   để chặn double-submit."* Public API đã truyền (`public_api/invocation.py`);
   Dự án dùng trạng thái khối; chỉ Studio bỏ trống.

⭐ VÀ NÓ KHÔNG PHÁ TÍNH NĂNG "PHIÊN BẢN" (V1/V2/V3):

   `jobs.submit` chỉ dedupe với job **chưa kết thúc** (queued/running) của cùng
   khách. Khách chờ job xong rồi tạo lại **cùng văn bản** để lấy một bản đọc
   khác vẫn ra job mới — vì job cũ đã `done`, không còn khớp. Chỉ những lần bấm
   trùng **khi job trước còn đang chạy** mới bị gộp. Đó đúng là ranh giới ta
   muốn.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một khách đã đăng nhập, có credit, trên SQLite tạm. Cổng giọng được giả
    là 'đã cấu hình' nhưng KHÔNG job nào thật sự chạy — chúng đứng `queued` trong
    suốt bài kiểm, đúng cảnh 'khách bấm lại khi job trước chưa xong'."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-studio-trung.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-studio-trung")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="voice-studio@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 500, note="test_502")
        db.commit()
        uid = str(u.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    login = client.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', login.text)
    assert m
    client.post("/login", data={"username": "voice-studio@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf(client) -> str:
    r = client.get("/ltt-voice")
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    assert m, "khong lay duoc csrf_token — xem `vo.ngu_canh`"
    return m.group(1)


def _so_job(uid: str) -> int:
    import platform_core.db as dbmod
    from platform_core.models import Job

    gen = dbmod.get_session()
    db = next(gen)
    try:
        return db.query(Job).filter(Job.user_id == str(uid)).count()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _so_giu(uid: str) -> int:
    """Tổng credit ĐANG bị giữ cho mọi job của khách (số dương)."""
    import platform_core.db as dbmod
    from platform_core.credit import CREDIT_HOLD
    from platform_core.models import CreditEntry

    gen = dbmod.get_session()
    db = next(gen)
    try:
        rows = db.query(CreditEntry).filter(
            CreditEntry.user_id == str(uid),
            CreditEntry.kind == CREDIT_HOLD).all()
        return -int(sum(r.delta for r in rows))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_bam_TAO_hai_lan_lien_tiep_chi_sinh_MOT_job(khach):
    """🔴 Hai POST /tao giống hệt nhau khi job đầu chưa xong ⇒ MỘT job, MỘT hold."""
    client, uid = khach
    data = {"text": "Xin chao, day la mot doan doc thu de kiem dedupe.",
            "preset": "Adam", "toc_do": "1.0", "csrf_token": _csrf(client)}

    r1 = client.post("/ltt-voice/tao", data=dict(data, csrf_token=_csrf(client)))
    assert r1.status_code == 200, r1.text
    assert r1.json()["ok"], r1.json()
    job1 = r1.json()["job_id"]
    sau_1 = _so_job(uid)
    assert sau_1 == 1, f"lan 1 sinh {sau_1} job"
    giu_1 = _so_giu(uid)
    assert giu_1 > 0, "lan 1 phai giu credit"

    # Bấm lại NGAY — job đầu vẫn `queued` (không worker nào chạy trong test).
    r2 = client.post("/ltt-voice/tao", data=dict(data, csrf_token=_csrf(client)))
    assert r2.status_code == 200, r2.text
    assert r2.json()["ok"], r2.json()
    job2 = r2.json()["job_id"]

    assert job2 == job1, (
        f"lan 2 sinh job khac ({job2} != {job1}) — double-submit khong bi chan")
    assert _so_job(uid) == 1, (
        f"co {_so_job(uid)} job cho mot doan — khach bi tinh tien hai lan")
    assert _so_giu(uid) == giu_1, (
        f"credit giu tang tu {giu_1} len {_so_giu(uid)} — giu cho lan hai")


def test_van_ban_KHAC_nhau_van_sinh_hai_job(khach):
    """⭐ Đối chứng: dedupe không được nuốt nhầm hai yêu cầu THẬT SỰ khác nhau."""
    client, uid = khach
    r1 = client.post("/ltt-voice/tao", data={
        "text": "Doan mot, hoan toan rieng biet.",
        "preset": "Adam", "toc_do": "1.0", "csrf_token": _csrf(client)})
    r2 = client.post("/ltt-voice/tao", data={
        "text": "Doan hai, mot noi dung khac han.",
        "preset": "Adam", "toc_do": "1.0", "csrf_token": _csrf(client)})
    assert r1.json()["ok"] and r2.json()["ok"]
    assert r1.json()["job_id"] != r2.json()["job_id"]
    assert _so_job(uid) == 2, "hai van ban khac nhau phai ra hai job"
