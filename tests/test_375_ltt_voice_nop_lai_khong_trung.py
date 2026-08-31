"""
V9 · hai chốt cuối: **nộp trùng không sinh việc trùng**, và **chạy lại không
bắt đầu từ 0**.

`docs/LTT_VOICE/00_PHUONG_AN_VA_LO_TRINH.md` đặt chúng thành điều kiện qua V9.
Cả hai đều là chuyện TIỀN, không phải chuyện tiện lợi:

  · nộp trùng ⇒ khách bị thu **hai lần** cho một dòng, và nhận về hai tệp giống
    nhau mà không hiểu vì sao;
  · chạy lại từ 0 ⇒ một bài hai mươi khối mà worker chết ở khối mười chín sẽ
    tính tiền lại **cả hai mươi**.

⭐ Hình dạng của lời giải nằm ở `du_an.khoi_can_tao` + trạng thái khối: một khối
   vừa nộp chuyển sang `dang_tao`, và `khoi_can_tao` chỉ nhặt `moi` / `loi` /
   `can_tao_lai`. Nên "nộp lại" tự nó là "nộp phần còn thiếu".

⛔ Nhưng lập luận đó **không phải bằng chứng**, và nó phụ thuộc vào hai thứ nằm ở
   hai tệp khác nhau (bộ lọc ở `du_an.py`, phép gán trạng thái ở `_p_du_an.py`).
   Ai đó sửa một trong hai mà không biết cái kia là mở lại cả hai lỗ. Đây là
   phép kiểm đứng giữa.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một khách đã đăng nhập, có credit, trên SQLite tạm."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-nop.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-nop-lai")
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
        u = tao_nguoi_dung(db, email="voice-nop@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 500, note="test_375")
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
    client.post("/login", data={"username": "voice-nop@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf(client) -> str:
    r = client.get("/ltt-voice/du-an")
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    assert m, "khong lay duoc csrf_token — xem `vo.ngu_canh`"
    return m.group(1)


def _tao_du_an(client, so_khoi: int) -> str:
    r = client.post("/ltt-voice/du-an/tao",
                    data={"ten": "Bai doc thu", "giong": "m:Adam",
                          "csrf_token": _csrf(client)})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]

    # ⛔ Ngăn bằng DÒNG TRỐNG, không phải dấu cách. `nhap_van_ban` tôn trọng
    #    đoạn văn của tác giả và gói các câu ngắn vào **một** khối cho tới trần
    #    1.500 ký tự — nên năm câu nối bằng dấu cách ra đúng MỘT khối, và phép
    #    kiểm sẽ đo một thứ khác hẳn thứ nó định đo.
    cau = "\n\n".join(f"Day la cau thu {i + 1} cua bai doc thu."
                      for i in range(so_khoi))
    r = client.post(f"/ltt-voice/du-an/{pid}/nhap",
                    data={"text": cau, "csrf_token": _csrf(client)})
    assert r.status_code == 200, r.text
    return pid


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


def _cac_khoi(pid: str, uid: str):
    import platform_core.db as dbmod

    from apps.ltt_voice import du_an

    gen = dbmod.get_session()
    db = next(gen)
    try:
        d = du_an.tim(db, pid, owner_id=uid)
        assert d is not None
        return list(du_an.cac_khoi(db, d.id))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_nop_HAI_LAN_lien_tiep_khong_sinh_job_thu_hai(khach):
    """🔴 Khách bấm "Đọc tất cả" hai lần thì phải trả tiền MỘT lần.

    Bấm hai lần là chuyện bình thường: lần đầu không thấy gì đổi ngay (job đang
    xếp hàng), nên người ta bấm lại. Nếu mỗi lần bấm sinh một bộ job mới thì
    khách trả tiền gấp đôi cho **cùng một bài**, và nhận về hai bộ tệp giống
    nhau mà không có gì giải thích.

    ⛔ Và nó không tự sửa được ở tầng giao diện. Vô hiệu hoá cái nút sau lần bấm
       đầu chỉ chặn được **một** trình duyệt; hai tab, hoặc một lần tải lại
       trang, là qua ngay. Chốt phải nằm ở phía máy chủ.
    """
    client, uid = khach
    pid = _tao_du_an(client, 4)

    truoc = _so_job(uid)
    r1 = client.post(f"/ltt-voice/du-an/{pid}/doc-tat-ca",
                     data={"csrf_token": _csrf(client)})
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["ok"] and d1["so_nop"] == 4, d1
    sau_lan_1 = _so_job(uid)
    assert sau_lan_1 - truoc == 4, f"lan 1 sinh {sau_lan_1 - truoc} job, can 4"

    # Bấm lại NGAY, chưa khối nào xong.
    r2 = client.post(f"/ltt-voice/du-an/{pid}/doc-tat-ca",
                     data={"csrf_token": _csrf(client)})
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["so_nop"] == 0, f"lan 2 nop them {d2['so_nop']} khoi — trung viec"
    assert _so_job(uid) == sau_lan_1, (
        f"lan 2 sinh them {_so_job(uid) - sau_lan_1} job cho cung mot bai")


def test_chay_lai_sau_khi_MOT_PHAN_da_xong_chi_nop_phan_con_THIEU(khach):
    """🔴 Worker chết ở khối 19/20 thì chạy lại KHÔNG được tính tiền lại cả 20.

    Đây là chốt "chạy lại không bắt đầu từ 0" của V9. Mô phỏng đúng thứ xảy ra
    thật: một phần khối đã xong, một khối **hỏng**, phần còn lại chưa chạm tới.

    ⭐ Khối `loi` PHẢI được nộp lại — nó là thứ khách đang chờ. Khối `xong` thì
       KHÔNG. Hai điều đó là hai vế của cùng một phép lọc, và một phép kiểm chỉ
       chốt một vế sẽ xanh với một bộ lọc trả về rỗng.
    """
    import platform_core.db as dbmod

    from apps.ltt_voice import du_an

    client, uid = khach
    pid = _tao_du_an(client, 5)

    r = client.post(f"/ltt-voice/du-an/{pid}/doc-tat-ca",
                    data={"csrf_token": _csrf(client)})
    assert r.json()["so_nop"] == 5
    sau_lan_1 = _so_job(uid)

    # Ba khối xong, một khối lỗi, một khối vẫn đang tạo.
    khoi = _cac_khoi(pid, uid)
    assert len(khoi) == 5
    gen = dbmod.get_session()
    db = next(gen)
    try:
        d = du_an.tim(db, pid, owner_id=uid)
        cac = list(du_an.cac_khoi(db, d.id))
        for k in cac[:3]:
            k.trang_thai = "xong"
            k.audio_key = f"gia/{k.id}.wav"
        cac[3].trang_thai = "loi"
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = client.post(f"/ltt-voice/du-an/{pid}/doc-tat-ca",
                    data={"csrf_token": _csrf(client)})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["so_nop"] == 1, (
        f"nop lai {d['so_nop']} khoi; chi khoi `loi` phai duoc nop lai "
        f"(3 khoi `xong` va 1 khoi `dang_tao` thi khong)")
    assert _so_job(uid) - sau_lan_1 == 1

    # Ba khối `xong` phải còn nguyên tệp — nộp lại không được xoá kết quả cũ.
    con = {k.trang_thai for k in _cac_khoi(pid, uid) if k.audio_key}
    assert "xong" in con, "khoi da xong bi mat ket qua sau khi nop lai"


def test_bo_loc_KHOI_CAN_TAO_khong_bao_gio_tra_khoi_DANG_TAO(khach):
    """Bánh cóc cho chính phép lọc, ở tầng dưới HTTP.

    Hai phép kiểm trên đi qua HTTP nên chúng chứng minh **hành vi**. Phép kiểm
    này chốt **cơ chế**: nếu ai đó thêm `"dang_tao"` vào danh sách trạng thái
    được nhặt lại, hai phép trên vẫn có thể xanh trong một cấu hình nào đó,
    còn phép này thì không.
    """
    from apps.ltt_voice import du_an

    class _K:
        def __init__(self, tt, text="co chu"):
            self.trang_thai, self.text = tt, text

    cac = [_K("moi"), _K("dang_tao"), _K("xong"), _K("loi"),
           _K("can_tao_lai"), _K("moi", "   ")]
    ra = {k.trang_thai for k in du_an.khoi_can_tao(cac)}
    assert ra == {"moi", "loi", "can_tao_lai"}, ra
    assert len(du_an.khoi_can_tao(cac)) == 3, "khoi rong phai bi bo"
