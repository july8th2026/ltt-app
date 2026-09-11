"""test_525 — XOÁ một lượt Lịch sử, và trạng thái KHỐI suy ra đúng sau đó (D005).

Ba việc mới nằm ngoài phần `27baa1a8`/`31878cc2` đã chốt (hai commit đó lo
HẾT HẠN + soft-delete + chip "Đã tải" — xem `test_351`):

1. **Hộp xác nhận phải nói TRƯỚC hậu quả.** Bấm Xoá không được xoá ngay rồi để
   khách tự phát hiện dự án gãy — `GET /lich-su/{id}/anh-huong` liệt kê những
   khối Dự án đang dùng đúng audio này, TRƯỚC khi khách xác nhận.

2. **T-11 — khoá lưu trữ CŨ cũng phải bị dọn.** `0a07a49e` đổi khuôn khoá từ
   `voice/out/{owner}/{job_id}.wav` sang `voice/out/{owner}/{job_id}/tieng.wav`
   vì `job_content.content_keys` nhận diện theo đoạn đường dẫn `/{job_id}/` —
   khoá KHÔNG có dấu `/` sau job id thì `expire_content` bỏ sót, im lặng. Job
   sinh TRƯỚC ngày đó vẫn mang khoá cũ; `xoa_luot` phải tự dọn thêm khoá đó.

3. **`trang_thai_hien` — trạng thái HIỂN của khối, không phải cột đã ghi.**
   Sau khi xoá, `VoiceBlock.trang_thai` trong CSDL vẫn là `"xong"` (không ai
   quay lại cập nhật cột đó khi tệp mất ở một lượt khác); nhưng với khách khối
   đã mất tiếng và cần tạo lại. `du_an.trang_thai_hien(khoi, co_tieng)` là hàm
   THUẦN suy ra điều đó từ việc có URL nghe hay không (`du_an.duong_tieng`).
   Mức DỰ ÁN (gộp trạng thái nhiều khối, `trang_thai_suy`) là việc của Task 9
   — `test_357`. Tệp này chỉ chốt mức KHỐI.

Và một chốt không đổi (SC-8): `doc_lai` vẫn phải đi qua CẢ HAI cổng kiểm trước
khi tiêu tiền (`features.chuan_hoa` + `features.giai_giong` — hotfix `dc6d9c6b`,
sự cố production 31/08/2026), và giờ còn mang `dedupe_key` để chặn double-submit
(cùng khuôn `test_519`/`test_502`).
"""
from __future__ import annotations

import io
import re
import struct

import pytest


def _wav(giay: float = 0.3, sr: int = 8000) -> bytes:
    n = int(sr * giay)
    d = b"\x00\x00" * n
    return (b"RIFF" + struct.pack("<I", 36 + len(d)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16)
            + b"data" + struct.pack("<I", len(d)) + d)


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một khách đã đăng nhập, có credit, trên SQLite tạm. Chép từ `test_519`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-lichsu-xoa.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-lichsu-xoa")
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
        u = tao_nguoi_dung(db, email="voice-lichsu-xoa@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 500, note="test_525")
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
    client.post("/login", data={"username": "voice-lichsu-xoa@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf_ls(client) -> str:
    r = client.get("/ltt-voice/lich-su")
    m = re.search(r'id="lv-ls-csrf" value="([^"]+)"', r.text)
    assert m, "trang Lich su khong co csrf_token"
    return m.group(1)


def _job_xong(uid: str, *, co_khoi: bool = False, khoa_cu: bool = False) -> str:
    """Một `Job` `done` có TỆP THẬT trong kho.

    `khoa_cu=True` ghi theo đúng khuôn khoá CŨ đọc từ `0a07a49e`:
    `voice/out/{owner_id}/{job_id}.wav` — job id nằm CUỐI, không có `/` theo
    sau (khác khuôn hiện hành `voice/out/{owner}/{job_id}/tieng.wav`).

    `co_khoi=True` gắn thêm một `VoiceProject` + một `VoiceBlock` trỏ tới
    đúng job/khoá này, để kiểm trạng thái HIỂN của khối sau khi xoá.
    """
    import platform_core.db as dbmod
    from platform_core.models import Job
    from platform_core.storage import get_storage

    khoa = None
    gen = dbmod.get_session()
    db = next(gen)
    try:
        j = Job(user_id=uid, app_slug="ltt_voice",
                job_type="ltt_voice.synthesize",
                params={"nguon": "studio", "text": "cau thu nghiem doc",
                        "preset": "Adam"},
                status="done",
                result={"duration_s": 1.0, "credit_cost": 1, "audio_key": ""})
        db.add(j)
        db.flush()
        jid = str(j.id)
        khoa = (f"voice/out/{uid}/{jid}.wav" if khoa_cu
               else f"voice/out/{uid}/{jid}/tieng.wav")
        j.result = {"duration_s": 1.0, "credit_cost": 1, "audio_key": khoa}

        if co_khoi:
            from apps.ltt_voice.tables_du_an import VoiceBlock, VoiceProject
            p = VoiceProject(owner_id=uid, ten="Du an test_525", loai="du_an")
            db.add(p)
            db.flush()
            db.add(VoiceBlock(project_id=p.id, thu_tu=1.0,
                              text="cau thu nghiem doc", trang_thai="xong",
                              job_id=jid, audio_key=khoa))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    get_storage().put(khoa, io.BytesIO(_wav()), content_type="audio/wav")
    return jid


def _tom_tat_du_an_cua_job(uid: str, jid: str) -> dict:
    """Dựng lại đúng đường mà màn Dự án đi qua (`cac_khoi` + `duong_tieng`) rồi
    gọi `du_an.tom_tat(..., duong_tieng=...)` — vì `trang_thai_hien` là hàm
    THUẦN, nó cần người gọi tính sẵn `co_tieng` cho từng khối.
    """
    import platform_core.db as dbmod
    from sqlalchemy import select

    from apps.ltt_voice import du_an
    from apps.ltt_voice.tables_du_an import VoiceProject

    gen = dbmod.get_session()
    db = next(gen)
    try:
        p = db.execute(select(VoiceProject).where(
            VoiceProject.owner_id == str(uid))).scalars().first()
        assert p is not None, "khong tim thay du an cua job (gieo du lieu hong?)"
        khoi = du_an.cac_khoi(db, p.id)
        duong = du_an.duong_tieng(db, khoi, "/ltt-voice")
        return du_an.tom_tat(khoi, duong_tieng=duong)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ═══════════════════ 1. HỘP XÁC NHẬN NÓI TRƯỚC HẬU QUẢ ═══════════════════════

def test_xoa_liet_ke_khoi_bi_anh_huong_TRUOC(khach):
    client, uid = khach
    jid = _job_xong(uid, co_khoi=True)
    r = client.get(f"/ltt-voice/lich-su/{jid}/anh-huong")
    assert r.status_code == 200 and len(r.json()["khoi"]) == 1


def test_khong_co_khoi_thi_anh_huong_RONG(khach):
    """Đối chứng: một lượt Studio thường (không dùng trong Dự án nào) không có
    khối nào bị ảnh hưởng — hộp xác nhận không được bịa ra hậu quả không có."""
    client, uid = khach
    jid = _job_xong(uid, co_khoi=False)
    r = client.get(f"/ltt-voice/lich-su/{jid}/anh-huong")
    assert r.status_code == 200
    assert r.json()["khoi"] == []


def test_anh_huong_cua_job_NGUOI_KHAC_la_RONG(khach):
    """Không lộ hình dạng dữ liệu của người khác qua chính cửa hỏi hậu quả —
    job của A hỏi bằng phiên B thì B thấy như job không tồn tại/không có khối
    nào, không phải một lỗi tiết lộ có/không có job đó."""
    client_a, uid_a = khach
    jid_a = _job_xong(uid_a, co_khoi=True)

    import re as _re

    import platform_core.db as dbmod
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session()
    db = next(gen)
    try:
        tao_nguoi_dung(db, email="b-test525@test.com",
                       password="matkhau-tot-12", is_verified=True)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    client_b = TestClient(create_app(), base_url="https://testserver",
                          follow_redirects=False)
    try:
        login = client_b.get("/login")
        m = _re.search(r'name="csrf_token" value="([^"]+)"', login.text)
        assert m
        client_b.post("/login", data={"username": "b-test525@test.com",
                                      "password": "matkhau-tot-12",
                                      "csrf_token": m.group(1)})
        r = client_b.get(f"/ltt-voice/lich-su/{jid_a}/anh-huong")
        assert r.status_code == 404 or r.json()["khoi"] == []
    finally:
        client_b.close()


# ═══════════════════ 2. T-11 — KHOÁ LƯU TRỮ CŨ CŨNG BỊ DỌN ══════════════════

def test_xoa_that_su_xoa_tep_ke_ca_KHOA_CU(khach):
    client, uid = khach
    jid = _job_xong(uid, khoa_cu=True)
    r = client.post(f"/ltt-voice/lich-su/{jid}/xoa",
                    data={"csrf_token": _csrf_ls(client)})
    assert r.status_code in (200, 303)
    from platform_core.storage import get_storage
    # Khoá CŨ thật, đọc từ `0a07a49e`: `voice/out/{owner}/{job_id}.wav`.
    assert not get_storage().exists(f"voice/out/{uid}/{jid}.wav")


def test_xoa_khong_dong_toi_tep_cua_NGUOI_KHAC(khach):
    """Đối chứng chiều ngược: xoá lượt của A không được đụng một khoá cũ của B
    dù hai khoá đó trông giống nhau về hình dạng đuôi `.wav`."""
    client_a, uid_a = khach
    jid_a = _job_xong(uid_a, khoa_cu=True)

    uid_b_khoa = f"voice/out/nguoi-khac-gia/{jid_a}.wav"
    from platform_core.storage import get_storage
    get_storage().put(uid_b_khoa, io.BytesIO(_wav()),
                      content_type="audio/wav")

    client_a.post(f"/ltt-voice/lich-su/{jid_a}/xoa",
                 data={"csrf_token": _csrf_ls(client_a)})
    assert get_storage().exists(uid_b_khoa), (
        "xoa lam mat ca tep cua mot chu khac chi vi trung ten job")


# ═══════════════════ 3. TRẠNG THÁI HIỂN CỦA KHỐI, SAU KHI MẤT TIẾNG ═════════

def test_khoi_mat_tep_hien_CAN_TAO_LAI_khong_hien_XONG(khach):
    client, uid = khach
    jid = _job_xong(uid, co_khoi=True)
    r = client.post(f"/ltt-voice/lich-su/{jid}/xoa",
                    data={"csrf_token": _csrf_ls(client)})
    assert r.status_code in (200, 303)

    from apps.ltt_voice import du_an
    tt = _tom_tat_du_an_cua_job(uid, jid)
    # Mức KHỐI ở đây; mức DỰ ÁN (`trang_thai_suy`) là Task 9 — test_357.
    assert tt["khoi"][0]["trang_thai_hien"] == du_an.TT_CAN_TAO_LAI


def test_khoi_con_tep_van_hien_XONG_doi_chung(khach):
    """Đối chứng: một khối CHƯA bị xoá/hết hạn vẫn hiện `"xong"` — phép suy
    không được đổi trạng thái của những khối bình thường."""
    client, uid = khach
    jid = _job_xong(uid, co_khoi=True)

    from apps.ltt_voice import du_an
    tt = _tom_tat_du_an_cua_job(uid, jid)
    assert tt["khoi"][0]["trang_thai_hien"] == "xong"


def test_trang_thai_hien_la_HAM_THUAN():
    """`trang_thai_hien(khoi, co_tieng)` không đọc DB, không có tác dụng phụ —
    chỉ suy từ `khoi.trang_thai` + `co_tieng` đã tính sẵn."""
    from types import SimpleNamespace

    from apps.ltt_voice import du_an

    xong_con_tieng = SimpleNamespace(trang_thai="xong")
    xong_mat_tieng = SimpleNamespace(trang_thai="xong")
    dang_tao = SimpleNamespace(trang_thai="dang_tao")
    loi = SimpleNamespace(trang_thai="loi")

    assert du_an.trang_thai_hien(xong_con_tieng, True) == "xong"
    assert du_an.trang_thai_hien(xong_mat_tieng, False) == du_an.TT_CAN_TAO_LAI
    # Khối chưa từng "xong" thì `co_tieng` không đổi trạng thái của nó — chỉ
    # khối XONG-mà-mất-tiếng mới bị suy lại.
    assert du_an.trang_thai_hien(dang_tao, False) == "dang_tao"
    assert du_an.trang_thai_hien(loi, False) == "loi"


# ═══════════════════ 4. SC-8 — doc_lai VẪN qua cổng, VÀ giờ có dedupe ═══════

def test_doc_lai_VAN_qua_cong_va_CO_dedupe(khach):
    import ast
    import inspect

    from apps.ltt_voice.routes import _p_lich_su
    src = inspect.getsource(_p_lich_su.doc_lai)
    goi = {getattr(n.func, "id", "") or getattr(n.func, "attr", "")
          for n in ast.walk(ast.parse(src.lstrip())) if isinstance(n, ast.Call)}
    assert {"chuan_hoa", "giai_giong"} <= goi       # SC-8: hotfix dc6d9c6b còn
    kw = {k.arg for n in ast.walk(ast.parse(src.lstrip())) if isinstance(n, ast.Call)
          and (getattr(n.func, "id", "") or getattr(n.func, "attr", "")) == "submit_with_credit"
          for k in n.keywords}
    assert "dedupe_key" in kw
