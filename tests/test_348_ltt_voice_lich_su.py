"""Màn Lịch sử: lọc đúng, đếm đúng, và **nói ra** chỗ nó cắt bớt.

## Ba thứ tệp này canh

1. **Lọc theo nguồn thực sự hoạt động.** `nguon` được ghi từ P1 và là thứ duy
   nhất trả lời "lượt này đến từ đâu". Nếu bộ lọc lặng lẽ không khớp thì màn
   hình trả rỗng và người dùng kết luận sai rằng họ chưa từng dùng API.

2. **Con số tóm tắt tính đúng mẫu số.** Tỉ lệ lỗi tính trên số lượt **đã kết
   thúc**, không trên tổng — một lượt đang chạy chưa hỏng, và đếm nó vào mẫu số
   làm tỉ lệ trông đẹp lên một cách sai.

3. 🔴 **Trần đọc phải được nói ra.** `doc_man_lich_su.TRAN_DOC` cắt danh sách ở
   500 lượt. Một cái trần **không nói ra** tệ hơn không có trần: màn hình trông
   như đã liệt kê hết trong khi nó cắt bớt, và người dùng đi tìm một lượt cũ rồi
   kết luận nó đã bị xoá.
"""
from __future__ import annotations

import datetime as dt
import re
from types import SimpleNamespace

import pytest

from apps.ltt_voice import doc_man_lich_su as dls


def _job(**kw):
    """Một job giả, đủ hình dạng cho `doc_man_lich_su`."""
    return SimpleNamespace(
        id=kw.get("id", "job-1"),
        status=kw.get("status", "done"),
        params=kw.get("params", {}),
        result=kw.get("result", {}),
        created_at=kw.get("created_at", dt.datetime(2026, 8, 31, 10, 0)),
    )


# ── Lọc ──────────────────────────────────────────────────────────────────────

def test_loc_theo_nguon():
    ds = [_job(params={"nguon": "studio"}), _job(params={"nguon": "api"}),
          _job(params={"nguon": "api"})]
    assert len(dls.loc(ds, nguon="api")) == 2
    assert len(dls.loc(ds, nguon="studio")) == 1
    assert len(dls.loc(ds)) == 3, "khong loc gi ma van mat dong"


def test_loc_theo_giong_gom_ca_hai_loai():
    """Giọng nhân bản đi qua `voice_id`, giọng mẫu đi qua `preset`.

    ⭐ Hai trường khác nhau ở tầng dưới, nhưng với người xem lịch sử chúng là
       **cùng một câu hỏi**: "lượt này đọc bằng giọng nào". Nên bộ lọc phải
       nhìn cả hai; nhìn một cái thì một nửa lịch sử biến mất khỏi bộ lọc.
    """
    ds = [_job(params={"preset": "Adam"}),
          _job(params={"voice_id": "vc_abc"}),
          _job(params={"preset": "Trúc Ly"})]
    assert len(dls.loc(ds, giong="Adam")) == 1
    assert len(dls.loc(ds, giong="vc_abc")) == 1


def test_loc_gia_tri_la_tra_rong_chu_khong_no():
    """Tham số lọc là chuỗi khách gửi. Giá trị lạ ⇒ rỗng, không ngoại lệ."""
    ds = [_job(params={"nguon": "studio"})]
    assert dls.loc(ds, nguon="'; DROP TABLE jobs; --") == []


def test_job_cu_khong_co_nguon_thi_khong_doan():
    """⛔ Job nộp TRƯỚC P1 không mang `nguon`. Trả rỗng, đừng đoán.

    Đoán một nguồn cho dữ liệu lịch sử là bịa ra một sự thật mà sau đó không ai
    kiểm lại được — và nó sẽ được đọc như thật.
    """
    assert dls._nguon_cua(_job(params={"text": "cu"})) == ""
    # Và job cũ không được lọt vào bất kỳ bộ lọc nguồn nào.
    for n in dls.NGUON:
        assert dls.loc([_job(params={"text": "cu"})], nguon=n) == []


# ── Tóm tắt ──────────────────────────────────────────────────────────────────

def test_ti_le_loi_tinh_tren_luot_DA_KET_THUC():
    """🔴 Mẫu số là done+error, không phải tổng.

    Ba xong, một lỗi, sáu đang chạy: tỉ lệ lỗi là 1/4 = 25%, **không** phải
    1/10 = 10%. Dùng tổng làm mẫu số khiến tỉ lệ lỗi tụt xuống mỗi khi có nhiều
    việc đang xếp hàng — tức nó đẹp nhất đúng lúc hệ thống tắc nhất.
    """
    ds = ([_job(status="done") for _ in range(3)]
          + [_job(status="error")]
          + [_job(status="queued") for _ in range(6)])
    assert dls.tom_tat(ds)["ti_le_loi"] == 25.0


def test_ti_le_loi_khong_chia_cho_khong():
    ds = [_job(status="queued"), _job(status="running")]
    assert dls.tom_tat(ds)["ti_le_loi"] == 0.0


def test_tom_tat_cong_don_giay_va_credit():
    ds = [_job(result={"duration_s": 30.0, "credit_cost": 2}),
          _job(result={"duration_s": 30.0, "credit_cost": 3})]
    t = dls.tom_tat(ds)
    assert t["phut"] == 1.0
    assert t["credit"] == 5


def test_tom_tat_khong_vo_vi_du_lieu_ban():
    """Một `result` méo không được làm sập màn hình."""
    ds = [_job(result={"duration_s": "khong-phai-so", "credit_cost": None}),
          _job(result=None)]
    t = dls.tom_tat(ds)
    assert t["phut"] == 0.0 and t["credit"] == 0


def test_giong_hay_dung():
    ds = ([_job(params={"preset": "Adam"}) for _ in range(3)]
          + [_job(params={"preset": "Trúc Ly"})])
    t = dls.tom_tat(ds)
    assert t["giong_hay_dung"] == "Adam" and t["giong_hay_dung_so"] == 3


# ── Trần đọc phải nói ra ─────────────────────────────────────────────────────

@pytest.fixture()
def khach(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-ls.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-ls")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="voice-ls@test.com",
                           password="matkhau-tot-12", is_verified=True)
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
    client.post("/login", data={"username": "voice-ls@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf(client) -> str:
    import re
    m = re.search(r'id="lv-ls-csrf" value="([^"]+)"',
                  client.get("/ltt-voice/lich-su").text)
    assert m, "trang Lich su khong co csrf_token — nut Doc lai se hong"
    return m.group(1)


def _gieo(uid: str, so: int, **kw) -> None:
    import platform_core.db as dbmod
    from platform_core.models import Job

    gen = dbmod.get_session()
    db = next(gen)
    try:
        for i in range(so):
            db.add(Job(user_id=uid, app_slug="ltt_voice",
                       job_type="ltt_voice.synthesize",
                       params={"text": f"cau {i}", "nguon": kw.get("nguon", "studio"),
                               "preset": "Adam"},
                       status=kw.get("status", "done"),
                       result={"duration_s": 1.0, "credit_cost": 1,
                               "audio_key": f"voice/out/{uid}/j{i}/tieng.wav"}))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_khi_cham_tran_thi_MAN_HINH_PHAI_NOI(khach, monkeypatch):
    """🔴 Cắt bớt trong im lặng là nói dối bằng cách bỏ sót.

    Hạ trần xuống 5 rồi gieo 6 lượt: trang phải mang cờ `bi_cat` và in ra câu
    giải thích, chứ không chỉ hiện 5 dòng như thể đó là tất cả.
    """
    monkeypatch.setattr(dls, "TRAN_DOC", 5)
    client, uid = khach
    _gieo(uid, 6)

    html = client.get("/ltt-voice/lich-su").text
    assert "lv-ls-cat" in html, (
        "cham tran ma trang KHONG noi gi — nguoi dung se tuong day la tat ca")


def test_khi_chua_cham_tran_thi_khong_doa_nguoi_dung(khach, monkeypatch):
    """Và ngược lại: chưa cắt gì thì đừng hiện cảnh báo. Một cảnh báo luôn hiện
    là một cảnh báo không ai đọc."""
    monkeypatch.setattr(dls, "TRAN_DOC", 50)
    client, uid = khach
    _gieo(uid, 3)
    assert "lv-ls-cat" not in client.get("/ltt-voice/lich-su").text


# ── Đi qua router thật ───────────────────────────────────────────────────────

def test_loc_qua_url(khach):
    client, uid = khach
    _gieo(uid, 2, nguon="studio")
    _gieo(uid, 3, nguon="api")

    def dem(url):
        return len(re.findall(r'class="lv-ls-dong"', client.get(url).text))

    assert dem("/ltt-voice/lich-su") == 5
    assert dem("/ltt-voice/lich-su?nguon=api") == 3
    assert dem("/ltt-voice/lich-su?nguon=studio") == 2
    assert dem("/ltt-voice/lich-su?nguon=khong-co-that") == 0


def test_lich_su_khong_lo_khoa_kho_tran(khach):
    """URL phát phải đi qua cửa `/audio/` của app, không lộ khoá kho.

    Khoá kho là chi tiết nội bộ; hiện nó ra là mời người ta thử ghép tay một
    khoá khác.
    """
    client, uid = khach
    _gieo(uid, 1)
    html = client.get("/ltt-voice/lich-su").text
    assert 'src="/ltt-voice/audio/voice/out/' in html
    assert 'src="voice/out/' not in html


# ═══════════════════ mã giọng phải hiện thành TÊN, không phải băm ════════════
#
# Tìm ra 01/09/2026 bằng cách mở màn Lịch sử trên production: mọi chỗ nhắc tới
# giọng đều in `vc_fceeabc6…50db7` — ô lọc, dòng của mỗi lượt,
# và cả dòng "Giọng dùng nhiều nhất".
#
# ⛔ Và nó không phải chuyện của kho giọng chung: template in thẳng `{{ d.giong }}`
#    với class `mono`, tức KHÔNG có bước tra tên nào cả, cho MỌI loại giọng.
#    Một giọng do chính khách đặt tên cũng hiện ra là một chuỗi băm — trong khi
#    cái tên ấy đang nằm sẵn trong CSDL, cách đó một câu truy vấn.
#
# ⭐ Class `mono` được GIỮ khi không tra được tên. Một mã thô vẫn nên trông như
#    mã; đổi cả hai thành cùng một kiểu chữ là làm mất thông tin.

def _gieo_giong_va_luot(uid: str, ten: str = "Giong dat ten thu"):
    """Một giọng nhân bản + một lượt đọc dùng nó."""
    import platform_core.db as dbmod
    from platform_core.models import Job

    from apps.ltt_voice.tables import VoiceProfile
    ma = "vc_lichsuthu0000000000000000000a"
    gen = dbmod.get_session()
    db = next(gen)
    try:
        db.add(VoiceProfile(public_id=ma, owner_id=uid, ten_hien_thi=ten,
                            ngon_ngu="vi", trang_thai="active"))
        db.add(Job(user_id=uid, app_slug="ltt_voice",
                   job_type="ltt_voice.synthesize",
                   params={"text": "cau thu", "nguon": "studio",
                           "voice_id": ma},
                   status="done",
                   result={"duration_s": 2.0, "credit_cost": 1,
                           "audio_key": f"voice/out/{uid}/jx/tieng.wav"}))
        db.commit()
        return ma, ten
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_lich_su_hien_TEN_giong_o_CA_BA_cho(khach):
    """Ô lọc · dòng của mỗi lượt · "Giọng dùng nhiều nhất" — cả ba.

    ⛔ Bản đầu của phép kiểm này chỉ hỏi `ten in r.text`, và nó XANH kể cả khi
       tôi hoàn nguyên phần sửa của DÒNG — vì cái tên vẫn hiện ở ô lọc. Một
       chốt xanh vì lý do sai còn tệ hơn không có chốt: nó khiến ta tin là đã
       canh cái mình chưa canh.

    Nên nó đếm `>{ten}<` (tên là NỘI DUNG THẤY ĐƯỢC) và đòi đủ ba lượt, đồng
    thời cấm mã băm xuất hiện dưới dạng chữ. Mã vẫn được phép nằm trong
    `value="…"` và `data-giong="…"` — đó là định danh của biểu mẫu, không phải
    thứ khách đọc.
    """
    client, uid = khach
    ma, ten = _gieo_giong_va_luot(uid)
    r = client.get("/ltt-voice/lich-su")
    assert r.status_code == 200
    assert r.text.count(f">{ten}<") >= 3, (
        f"chi thay ten o {r.text.count(f'>{ten}<')}/3 cho — o loc, dong cua "
        "moi luot, va 'Giong dung nhieu nhat' deu phai tra ten")
    assert f">{ma}<" not in r.text, (
        f"ma bam {ma} van hien ra nhu CHU — khach doc mot chuoi bam thay vi "
        "cai ten chinh ho dat")


def test_ma_KHONG_tra_duoc_van_giu_kieu_chu_ma(khach):
    """Giọng đã gỡ vẫn còn trong lịch sử — và vẫn phải đọc được LÀ một mã.

    Bút toán trỏ về giọng cũ nên `VoiceProfile` không bao giờ bị xoá thật; nhưng
    một lượt cũ hoàn toàn có thể trỏ tới một mã không tra được. Khi đó đừng giả
    vờ nó là một cái tên: giữ kiểu chữ mã để người đọc biết đây là định danh.
    """
    import platform_core.db as dbmod
    from platform_core.models import Job

    client, uid = khach
    mo_coi = "vc_khongcontrongbang00000000000a"
    gen = dbmod.get_session()
    db = next(gen)
    try:
        db.add(Job(user_id=uid, app_slug="ltt_voice",
                   job_type="ltt_voice.synthesize",
                   params={"text": "cau mo coi", "nguon": "studio",
                           "voice_id": mo_coi},
                   status="done",
                   result={"duration_s": 1.0, "credit_cost": 1,
                           "audio_key": f"voice/out/{uid}/jy/tieng.wav"}))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = client.get("/ltt-voice/lich-su")
    assert r.status_code == 200
    assert f'class="mono">{mo_coi}<' in r.text, (
        "ma khong tra duoc phai VAN hien ra VA giu kieu chu ma — "
        "khong nuot no, cung khong gia vo no la mot cai ten")


def test_moi_dong_lich_su_deu_TAI_VE_duoc(khach):
    """🔴 Dòng mô tả trên đầu trang hứa "nghe lại và **tải về** được".

    Trước 01/09 màn này không có một đường tải nào — khách nghe lại được nhưng
    không lưu được. Một lời hứa trong phần mô tả mà giao diện không giữ.

    ⚠️ Và chốt này chốt cả `d.id`: `dong_cho_trang` đặt tên trường là `id`, chứ
       không phải `job_id`. Jinja trả RỖNG cho một trường không có, nên gõ nhầm
       tên cho ra một nút **biến mất** chứ không phải một lỗi — kiểu hỏng im
       lặng mà chỉ một phép kiểm nhìn vào HTML mới bắt được.
    """
    client, uid = khach
    _gieo(uid, 2)
    r = client.get("/ltt-voice/lich-su")
    assert r.status_code == 200
    assert r.text.count('download') >= 4, "moi dong phai co WAV va MP3"
    assert "?mp3=1" in r.text, "thieu duong tai MP3"
    assert '/jobs/' in r.text, "thieu duong mo chi tiet job (kiem ca ten truong `d.id`)"


# ══════════════════ Lọc theo ngày · Đọc lại — hai việc còn đọng ══════════════

def test_loc_theo_ngay_chay_o_SQL_khong_o_python(khach):
    """⚠️ Trần `TRAN_DOC` cắt TRƯỚC khi lọc.

    Lọc `so_ngay` trong Python sẽ cho ra "7 ngày qua" tính trên một tập ĐÃ BỊ
    CẮT — sai theo hướng khó thấy nhất, vì nó chỉ sai với người dùng nhiều.
    """
    import inspect

    from apps.ltt_voice import doc_man_lich_su

    src = inspect.getsource(doc_man_lich_su.doc)
    assert "start=" in src, (
        "`so_ngay` phai di vao `list_owned(start=...)`, khong loc sau khi da cat")


def test_moc_ngay_LA_lua_chon_ROI_RAC(khach):
    """Giá trị lạ không được thành một truy vấn lạ."""
    client, uid = khach
    _gieo(uid, 2)
    for xau in ("999", "-1", "abc"):
        r = client.get(f"/ltt-voice/lich-su?ngay={xau}")
        assert r.status_code == 200, (xau, r.text[:120])
    r = client.get("/ltt-voice/lich-su?ngay=7")
    assert r.status_code == 200
    assert "ngày qua" in r.text


def test_doc_lai_NOP_MOT_JOB_MOI(khach):
    """🔴 Khác hẳn `Lưu vào dự án`: engine chạy lại toàn bộ nên phải tính tiền.

    Cám dỗ ngược cũng có thật ("khách đã trả cho câu này rồi") — nhưng tệp cũ
    vẫn còn và vẫn nghe được; họ bấm đọc lại là vì muốn một BẢN KHÁC.
    """
    import platform_core.db as dbmod
    from platform_core.models import Job

    client, uid = khach
    _gieo(uid, 1)

    def dem():
        gen = dbmod.get_session()
        db = next(gen)
        try:
            return db.query(Job).filter(Job.user_id == uid).count()
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    gen = dbmod.get_session()
    db = next(gen)
    try:
        jid = str(db.query(Job).filter(Job.user_id == uid).first().id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # ⭐ Nạp credit TRONG phép kiểm, không ở fixture: lượt đầu tiên chạy trước
    #    khi nạp đã CHỨNG MINH route từ chối đúng khi thiếu tiền, và thông điệp
    #    ấy tới thẳng khách thay vì thành một lỗi 500 vô nghĩa.
    from platform_core import credit as _credit
    gen = dbmod.get_session()
    db = next(gen)
    try:
        thieu = client.post(f"/ltt-voice/lich-su/{jid}/doc-lai",
                            data={"csrf_token": _csrf(client)})
        assert thieu.status_code == 400 and "credit" in thieu.json()["loi"], (
            "thieu tien phai bao ro, khong duoc thanh mot loi chung chung")
        _credit.nap(db, uid, 50, note="test doc lai")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    truoc = dem()
    r = client.post(f"/ltt-voice/lich-su/{jid}/doc-lai",
                    data={"csrf_token": _csrf(client)})
    assert r.status_code == 200, r.text
    assert r.json()["ok"], r.text
    assert dem() == truoc + 1, "doc lai phai NOP mot job moi"


def test_doc_lai_job_cua_NGUOI_KHAC_la_404(khach):
    import platform_core.db as dbmod
    from platform_core.models import Job

    client, _uid = khach
    gen = dbmod.get_session()
    db = next(gen)
    try:
        j = Job(user_id="nguoi-khac", app_slug="ltt_voice",
                job_type="ltt_voice.synthesize",
                params={"text": "bi mat", "preset": "Adam"}, status="done",
                result={"audio_key": "x", "duration_s": 1.0, "credit_cost": 1})
        db.add(j)
        db.commit()
        jid = str(j.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    r = client.post(f"/ltt-voice/lich-su/{jid}/doc-lai",
                    data={"csrf_token": _csrf(client)})
    assert r.status_code == 404, r.text
