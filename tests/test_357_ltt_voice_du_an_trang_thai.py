r"""
Trạng thái DỰ ÁN suy ra từ khối — không phải một cột trôi được (D005/SC-11).

🔴 LỖI ĐÃ TÌM RA (`ca6a00ce`, số cũ `test_351`): `ltt_voice_du_an.html` vẽ huy
   hiệu theo `voice_project.trang_thai`. Nhưng KHÔNG chỗ nào đặt dự án sang
   `xong`, và cột đó cũng không biết tệp đã mất (xoá ở Lịch sử, hết hạn 30
   ngày) — một khối "xong" theo cột có thể không còn tệp nghe được. Task 8 đã
   dựng `du_an.trang_thai_hien`/`tom_tat(..., duong_tieng=...)` cho MỨC KHỐI
   (`test_525`); tệp này chốt MỨC DỰ ÁN: `du_an.trang_thai_suy`.

⭐ 5 TRẠNG THÁI, không còn 3 như `ca6a00ce`:
   `{"trong", "dang_lam", "can_tao_lai", "loi", "xong"}` — xem thứ tự các
   nhánh ở chính docstring của `trang_thai_suy`. ĐỔI so với bản cũ: một dự án
   đã có khối nhưng CHƯA khối nào được đọc (`moi`) nay rơi vào `dang_lam`,
   không còn là `nhap`/`trong` — `trong` CHỈ dành cho dự án không khối nào.
   Đây là thay đổi có chủ ý của Task 9, không phải sót khi port.

Bốn thứ tệp này canh:
  1. `du_an.trang_thai_suy` phân loại đúng 5 trạng thái, đúng THỨ TỰ ưu tiên.
  2. Huy hiệu SỐNG QUA RELOAD: dựng từ CSDL mỗi lần mở, nên không trôi.
  3. Khối của dự án khác không với tới được qua URL của dự án này (cross-project).
  4. T-10/T-06: mọi lỗi 400 của `_p_du_an.py` kèm `ma_loi`; `/doc` một khối
     chặn nộp trùng bằng cả trạng thái khối (409) lẫn `dedupe_key`.
"""
from __future__ import annotations

import re

import pytest

from apps.ltt_voice import du_an


# ── 1. phân loại (đơn vị, không CSDL) ────────────────────────────────────────

class _K:
    """Khối giả TỐI GIẢN — đủ thuộc tính `tom_tat()`/`trang_thai_hien()` cần.

    ⛔ `id` và `audio_key` KHÔNG có trong `_K` của `ca6a00ce` (test_351 cũ):
       bản đó ra đời TRƯỚC `tom_tat()` mang `khoi_hien` (Task 8). Thiếu hai
       thuộc tính này thì `tom_tat()` hiện tại ném `AttributeError` ngay ở
       `k.id` — đây là phần "port lên tệp hiện tại" mà brief Task 9 dặn.

    `audio_key` mặc định KHÔNG rỗng khi `tt="xong"`: một khối "xong" bình
    thường có tệp thật (đó là điều `gan_ket_qua` làm). Test nào cần mô phỏng
    "xong nhưng mất tệp" (D005) thì tự truyền `audio_key=""`.
    """

    def __init__(self, tt="moi", text="co chu", giong="", *, id=0, audio_key=None):
        self.id = id
        self.trang_thai, self.text, self.giong = tt, text, giong
        self.giay, self.credit = 0.0, 0
        self.audio_key = (audio_key if audio_key is not None
                          else ("k" if tt == "xong" else ""))


def test_trang_thai_suy_khong_khoi_la_trong():
    assert du_an.trang_thai_suy(du_an.tom_tat([])) == "trong"


def test_trang_thai_suy_khoi_chua_sinh_gi_la_dang_lam():
    """⚠️ THAY ĐỔI HÀNH VI CÓ CHỦ Ý so với `ca6a00ce` (coi mọi khối `moi` là
    "nhap"): xem docstring đầu tệp + `du_an.trang_thai_suy`."""
    assert du_an.trang_thai_suy(
        du_an.tom_tat([_K("moi"), _K("moi")])) == "dang_lam"


def test_trang_thai_suy_dang_tao_thang_moi_thu_khac():
    assert du_an.trang_thai_suy(
        du_an.tom_tat([_K("xong"), _K("dang_tao")])) == "dang_lam"
    assert du_an.trang_thai_suy(
        du_an.tom_tat([_K("dang_tao"), _K("can_tao_lai")])) == "dang_lam"


def test_trang_thai_suy_co_khoi_can_tao_lai_thi_CAN_TAO_LAI():
    assert du_an.trang_thai_suy(
        du_an.tom_tat([_K("xong"), _K("can_tao_lai")])) == du_an.TT_CAN_TAO_LAI


def test_trang_thai_suy_mot_phan_loi_mot_phan_xong_la_dang_lam():
    """Đối chứng cho lượng từ MỌI: một khối `loi` + một khối `xong` không phải
    "mọi khối loi" cũng không phải "mọi khối xong"."""
    assert du_an.trang_thai_suy(
        du_an.tom_tat([_K("loi"), _K("xong")])) == "dang_lam"


def test_trang_thai_suy_moi_khoi_xong_la_XONG():
    assert du_an.trang_thai_suy(
        du_an.tom_tat([_K("xong"), _K("xong")])) == "xong"


# ── Step 1 của brief Task 9 — chốt lỗi CHÍNH (D005 ở mức dự án) ─────────────

def test_du_an_co_khoi_MAT_TEP_khong_bao_gio_XONG():
    """🔴 Khối "xong" theo cột NHƯNG mất tệp (`trang_thai_hien` đã suy thành
    `TT_CAN_TAO_LAI`) phải kéo CẢ DỰ ÁN xuống "cần tạo lại" — không được để
    khối kia (thật sự xong) che mất, và tuyệt đối không hiện "xong"."""
    tt = {"khoi": [{"trang_thai": "xong", "trang_thai_hien": "xong"},
                   {"trang_thai": "xong", "trang_thai_hien": du_an.TT_CAN_TAO_LAI}]}
    assert du_an.trang_thai_suy(tt) == du_an.TT_CAN_TAO_LAI


def test_moi_khoi_loi_thi_LOI():
    tt = {"khoi": [{"trang_thai": "loi", "trang_thai_hien": "loi"}] * 2}
    assert du_an.trang_thai_suy(tt) == "loi"


# ── router thật: huy hiệu sống qua reload ────────────────────────────────────

@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một khách đã đăng nhập, có credit, trên SQLite tạm. Chép từ `test_519`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-tt.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-trang-thai")
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
        u = tao_nguoi_dung(db, email="voice-tt@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 500, note="test_357")
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
    client.post("/login", data={"username": "voice-tt@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf_da(client) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"',
                  client.get("/ltt-voice/du-an").text)
    assert m
    return m.group(1)


def _tao_du_an(client, ten="Du an TT") -> str:
    """POST /ltt-voice/du-an/tao — giọng mặc định `m:Adam` (làn `vi`), để các
    test nộp job (ma_loi lệch làn, chặn nộp trùng) có sẵn một giọng hợp lệ."""
    r = client.post("/ltt-voice/du-an/tao",
                    data={"ten": ten, "giong": "m:Adam", "csrf_token": _csrf_da(client)})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _them_khoi(client, pid, text) -> int:
    """POST /ltt-voice/du-an/{pid}/khoi/them — MỘT khối, trả `id` (int)."""
    r = client.post(f"/ltt-voice/du-an/{pid}/khoi/them",
                    data={"text": text, "csrf_token": _csrf_da(client)})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _them_n_khoi(client, pid, n: int) -> None:
    for i in range(n):
        _them_khoi(client, pid, f"Cau so {i}.")


def _dat_trang_thai_khoi(pid, uid, gia_tri: list, *, mat_tep_o: list | None = None):
    """Đặt trạng thái CỘT từng khối trực tiếp trong CSDL — mô phỏng job đã
    xong. `mat_tep_o`: chỉ số (0-based, trong `gia_tri`) của khối "xong" mà
    KHÔNG gán `audio_key` — mô phỏng tệp đã mất (D005): cột vẫn "xong", chỉ
    `trang_thai_hien`/`trang_thai_suy` mới thấy được sự khác biệt.
    """
    mat_tep_o = set(mat_tep_o or ())
    import platform_core.db as dbmod

    gen = dbmod.get_session()
    db = next(gen)
    try:
        d = du_an.tim(db, pid, owner_id=uid)
        cac = list(du_an.cac_khoi(db, d.id))
        for i, (k, tt) in enumerate(zip(cac, gia_tri, strict=False)):
            k.trang_thai = tt
            if tt == "xong" and i not in mat_tep_o:
                k.audio_key = f"voice/out/{uid}/j{k.id}/tieng.wav"
                k.giay = 3.0
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_badge_XONG_hien_sau_khi_moi_khoi_xong_va_song_qua_reload(khach):
    """🔴 Chốt lỗi cũ: dự án đọc xong hết phải hiện "Xong", không kẹt "Đang
    làm". Reload = GET lại trang danh sách — mỗi request mở phiên CSDL mới và
    dựng lại huy hiệu từ khối, nên nếu đúng ở đây thì không trôi theo thời gian.
    """
    client, uid = khach
    pid = _tao_du_an(client)
    _them_n_khoi(client, pid, 2)
    _dat_trang_thai_khoi(pid, uid, ["xong", "xong"])

    html = client.get("/ltt-voice/du-an").text
    assert "b-ok" in html and "Xong" in html, (
        "du an moi khoi da xong nhung khong hien huy hieu Xong")
    assert "b-warn" not in html, "van con hien 'Dang lam' du da xong het"


def test_badge_DANG_LAM_khi_mot_phan_xong(khach):
    client, uid = khach
    pid = _tao_du_an(client)
    _them_n_khoi(client, pid, 2)
    _dat_trang_thai_khoi(pid, uid, ["xong", "moi"])

    html = client.get("/ltt-voice/du-an").text
    assert "b-warn" in html, "mot phan xong phai hien 'Dang lam'"
    assert "b-ok" not in html, "chua xong het ma da hien 'Xong'"


def test_badge_TRONG_khi_khong_co_khoi(khach):
    client, uid = khach
    _tao_du_an(client, ten="Rong")
    html = client.get("/ltt-voice/du-an").text
    assert "b-grey" in html, "du an khong khoi nao phai hien 'Nhap'"


def test_badge_LOI_khi_moi_khoi_loi(khach):
    client, uid = khach
    pid = _tao_du_an(client)
    _them_n_khoi(client, pid, 2)
    _dat_trang_thai_khoi(pid, uid, ["loi", "loi"])
    html = client.get("/ltt-voice/du-an").text
    assert "b-err" in html, "moi khoi loi phai hien huy hieu Loi"


def test_badge_CAN_TAO_LAI_khi_mot_khoi_XONG_nhung_MAT_TEP(khach):
    """🔴 D005/SC-11 ở tầng router: cột `trang_thai` của khối vẫn "xong" (job
    đã xong thật) nhưng `audio_key` KHÔNG được đặt — mô phỏng tệp đã hết hạn/
    bị xoá ở Lịch sử. Huy hiệu dự án phải hiện "Cần tạo lại", KHÔNG "Xong"."""
    client, uid = khach
    pid = _tao_du_an(client)
    _them_n_khoi(client, pid, 2)
    _dat_trang_thai_khoi(pid, uid, ["xong", "xong"], mat_tep_o=[1])

    html = client.get("/ltt-voice/du-an").text
    assert "Cần tạo lại" in html, "khoi mat tep phai keo huy hieu xuong 'Can tao lai'"
    assert "b-ok" not in html, "khong duoc hien 'Xong' khi mot khoi da mat tep"


def test_dem_va_thanh_tien_do_theo_TRANG_THAI_HIEN_khong_theo_cot_tho(khach):
    """🔴 Đợt sửa cuối RC1 (item 2): huy hiệu ĐÃ đúng từ Task 8/9 (đọc
    `tt["khoi"]`), nhưng các ĐẾM GỘP của `tom_tat()` (`xong`/`can_tao_lai`,
    và `giay`/`credit` suy từ đó) vẫn đọc cột `k.trang_thai` thô. Một dự án
    MỘT khối "xong" theo cột mà đã mất tệp (xoá ở Lịch sử/hết hạn 30 ngày)
    từng hiện đồng thời huy hiệu "Cần tạo lại" CẠNH dòng "1 đã đọc" và thanh
    tiến độ 100% — hai tín hiệu mâu thuẫn trên cùng một thẻ dự án (SC-11 ở
    tầng đếm, không chỉ tầng badge)."""
    client, uid = khach
    pid = _tao_du_an(client)
    _them_n_khoi(client, pid, 1)
    _dat_trang_thai_khoi(pid, uid, ["xong"], mat_tep_o=[0])

    html = client.get("/ltt-voice/du-an").text
    assert "Cần tạo lại" in html
    assert "1 đã đọc" not in html, "khoi da mat tep khong duoc tinh vao 'da doc'"
    assert 'aria-valuenow="100"' not in html, (
        "thanh tien do khong duoc hien 100% khi khoi duy nhat da mat tep")
    assert 'aria-valuenow="0"' in html

    # Cùng câu chuyện ở tầng hàm thuần, không qua HTTP/HTML.
    duong = {}  # không khối nào có URL tiếng còn dùng được — mô phỏng mất tệp
    k = _K("xong", id=1, audio_key="")
    tt = du_an.tom_tat([k], duong_tieng=duong)
    assert tt["xong"] == 0
    assert tt["can_tao_lai"] == 1
    assert tt["giay"] == 0.0
    assert tt["credit"] == 0


def _dat_khoi_het_han(pid, uid, idx: int = 0) -> None:
    """Khối tại `idx` có một `Job` THẬT, `status="done"`, `audio_key` THẬT —
    nhưng `Job.content_expired_at` đã đặt (mô phỏng hết hạn 30 ngày thật,
    khác `mat_tep_o` của `_dat_trang_thai_khoi` — ở đó khối chưa từng có
    `job_id`/`audio_key` nên `duong_tieng()` không có gì để hỏi bảng `jobs`;
    ở đây nó PHẢI hỏi `jobs` mới thấy `content_expired_at` và loại khối này
    ra khỏi kết quả — đúng đường mà `du_an.duong_tieng()` thật sự đi."""
    import datetime as dt

    import platform_core.db as dbmod
    from platform_core.models import Job

    gen = dbmod.get_session()
    db = next(gen)
    try:
        d = du_an.tim(db, pid, owner_id=uid)
        k = list(du_an.cac_khoi(db, d.id))[idx]
        khoa = f"voice/out/{uid}/j{k.id}/tieng.wav"
        j = Job(user_id=uid, app_slug="ltt_voice", job_type="ltt_voice.synthesize",
               params={"nguon": "du_an", "text": k.text},
               status="done",
               result={"duration_s": 1.0, "credit_cost": 1, "audio_key": khoa})
        db.add(j)
        db.flush()
        j.content_expired_at = dt.datetime.now(dt.timezone.utc)
        k.trang_thai = "xong"
        k.job_id = str(j.id)
        k.audio_key = khoa
        k.giay = 1.0
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_trang_chi_tiet_khong_hien_DA_DOC_khi_khoi_da_HET_HAN(khach):
    """🔴 Fix round 1/5 (controller ruling — INV-TRANG-THAI-1). Trước bản vá:
    `trang_mot_du_an` truyền thẳng `k.trang_thai` (cột thô) vào template, nên
    một khối "xong" theo cột mà tệp đã hết hạn hiện badge XANH "Đã đọc" ngay
    TRÊN dòng "Tệp tiếng đã hết hạn sau 30 ngày…" bên dưới nó — hai câu MÂU
    THUẪN trên cùng một màn hình. Route giờ truyền `trang_thai_hien()`."""
    client, uid = khach
    pid = _tao_du_an(client)
    _them_khoi(client, pid, "Mot cau doc thu de kiem tra badge.")
    _dat_khoi_het_han(pid, uid, 0)

    html = client.get(f"/ltt-voice/du-an/{pid}").text
    assert "Đã đọc" not in html, (
        "khong duoc hien badge 'Da doc' cho khoi da mat tep (het han)")
    assert "Cần tạo lại" in html, (
        "phai hien badge 'Can tao lai' cho khoi da mat tep (het han)")
    assert "Tệp tiếng đã hết hạn sau 30 ngày" in html, (
        "dong giai thich het han phai con, khong bi nhanh moi che mat")


def test_trang_chi_tiet_hien_VAN_BAN_DOI_khi_can_tao_lai_la_VI_SUA_CHU(khach):
    """🔴 Task 10, extra item (review Task 9). `trang_thai_hien()` gộp HAI
    nguyên nhân khác nhau vào cùng chuỗi `can_tao_lai`:

      · cột thô đã là `can_tao_lai` NGAY TỪ LƯỢT SỬA (`du_an.sua_khoi`,
        khách đổi văn bản — KHÔNG hề mất tệp, xem docstring của nó);
      · cột thô là `xong` nhưng tệp đã hết hạn/bị xoá (D005 — ca đã chốt ở
        `test_trang_chi_tiet_khong_hien_DA_DOC_khi_khoi_da_HET_HAN` ngay trên).

    Trước bản vá này, CẢ HAI đều hiện dòng "Tệp tiếng đã hết hạn sau 30
    ngày…" — sai cho ca thứ nhất: không có tệp nào hết hạn, khách chỉ vừa
    sửa chữ. Route nay truyền thêm cột THÔ (`trang_thai_tho`) để template
    phân biệt được hai nguyên nhân."""
    client, uid = khach
    pid = _tao_du_an(client)
    _them_khoi(client, pid, "Mot cau doc thu de kiem tra badge.")
    # Đặt cột thô = "can_tao_lai" TRỰC TIẾP (không qua `_dat_khoi_het_han`,
    # thứ mô phỏng tệp mất). Không audio_key ⇒ không audio_url ⇒ rơi vào
    # đúng nhánh giải thích ở cột phải.
    _dat_trang_thai_khoi(pid, uid, ["can_tao_lai"])

    html = client.get(f"/ltt-voice/du-an/{pid}").text
    assert "Cần tạo lại" in html, "badge van phai hien 'Can tao lai'"
    assert "Văn bản đã đổi" in html, (
        "khoi bi can_tao_lai vi SUA CHU phai noi ro nguyen nhan la van ban doi")
    assert "Tệp tiếng đã hết hạn sau 30 ngày" not in html, (
        "khong duoc noi 'het han' khi khong co tep nao het han — chi la van "
        "ban vua doi")


def test_trang_chi_tiet_hien_HET_HAN_khi_can_tao_lai_la_VI_MAT_TEP(khach):
    """Đối chứng của phép kiểm trên, viết lại tường minh: khi nguyên nhân là
    tệp hết hạn (cột thô vẫn `xong`), dòng "hết hạn" phải hiện và dòng "văn
    bản đã đổi" KHÔNG được hiện."""
    client, uid = khach
    pid = _tao_du_an(client)
    _them_khoi(client, pid, "Mot cau doc thu de kiem tra badge.")
    _dat_khoi_het_han(pid, uid, 0)

    html = client.get(f"/ltt-voice/du-an/{pid}").text
    assert "Tệp tiếng đã hết hạn sau 30 ngày" in html
    assert "Văn bản đã đổi" not in html, (
        "khong duoc noi 'van ban doi' khi nguyen nhan that la tep het han")


def test_poll_du_an_cung_tra_CAN_TAO_LAI_cho_khoi_da_HET_HAN(khach):
    """Cùng chốt trên, ở cửa poll (`/trang-thai`) — `voice.js::motDuAn` dùng
    đúng trường `khoi[i].trang_thai` này để SỬA badge mỗi vài giây; nếu cửa
    này vẫn trả cột thô thì trang mở sẵn tự sửa đúng rồi bị poll ghi đè sai."""
    client, uid = khach
    pid = _tao_du_an(client)
    _them_khoi(client, pid, "Mot cau doc thu de kiem tra badge.")
    _dat_khoi_het_han(pid, uid, 0)

    r = client.get(f"/ltt-voice/du-an/{pid}/trang-thai")
    assert r.status_code == 200, r.text
    khoi_ra = r.json()["khoi"]
    assert len(khoi_ra) == 1
    assert khoi_ra[0]["trang_thai"] == du_an.TT_CAN_TAO_LAI, khoi_ra[0]


def test_poll_tra_ve_trang_thai_du_an_suy(khach):
    """Cửa poll cũng trả trạng thái dự án suy ra, để giao diện cập nhật huy
    hiệu mà không phải tải lại cả trang."""
    client, uid = khach
    pid = _tao_du_an(client)
    _them_n_khoi(client, pid, 1)
    _dat_trang_thai_khoi(pid, uid, ["xong"])
    r = client.get(f"/ltt-voice/du-an/{pid}/trang-thai")
    assert r.status_code == 200, r.text
    assert r.json()["tom_tat"]["trang_thai"] == "xong", r.json()["tom_tat"]


def test_poll_tra_ve_CAN_TAO_LAI_khi_khoi_mat_tep(khach):
    client, uid = khach
    pid = _tao_du_an(client)
    _them_n_khoi(client, pid, 1)
    _dat_trang_thai_khoi(pid, uid, ["xong"], mat_tep_o=[0])
    r = client.get(f"/ltt-voice/du-an/{pid}/trang-thai")
    assert r.status_code == 200, r.text
    assert r.json()["tom_tat"]["trang_thai"] == du_an.TT_CAN_TAO_LAI, r.json()["tom_tat"]


# ── cô lập cross-project: khối của dự án khác không với tới được ────────────

def test_khoi_cua_du_an_khac_la_404_qua_du_an_nay(khach):
    """`tim_khoi` kiểm khối thuộc ĐÚNG dự án. Một `block_id` có thật của dự án
    A truyền vào URL của dự án B (cùng chủ) phải là 404 ở mọi cửa khối — nếu
    không, ranh giới giữa hai dự án chỉ là trang trí."""
    client, uid = khach
    pa = _tao_du_an(client, ten="A")
    pb = _tao_du_an(client, ten="B")
    bid_a = _them_khoi(client, pa, "Khoi cua A.")
    c = _csrf_da(client)

    for duong, du_lieu in (
            (f"/ltt-voice/du-an/{pb}/khoi/{bid_a}/sua", {"text": "trom"}),
            (f"/ltt-voice/du-an/{pb}/khoi/{bid_a}/xoa", {}),
            (f"/ltt-voice/du-an/{pb}/khoi/{bid_a}/doc", {})):
        rr = client.post(duong, data=dict(du_lieu, csrf_token=c))
        assert rr.status_code == 404, f"{duong} tra {rr.status_code}, phai 404"

    # Va khoi van con nguyen trong du an A.
    r = client.get(f"/ltt-voice/du-an/{pb}/khoi/{bid_a}/phien-ban")
    assert r.status_code == 404


# ── T-10 — mọi 400 của `_p_du_an.py` mang `ma_loi` ──────────────────────────

def test_cua_du_an_tra_MA_LOI_khi_lech_lan(khach):     # fixture từ test_519
    client, uid = khach
    pid = _tao_du_an(client, "Du an A")                  # helper POST /ltt-voice/du-an
    bid = _them_khoi(client, pid, "The quick brown fox jumps over the lazy dog that we know.")
    r = client.post(f"/ltt-voice/du-an/{pid}/khoi/{bid}/doc",
                    data={"preset": "Adam", "csrf_token": _csrf_da(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400 and r.json()["ma_loi"] == "voice_language_mismatch"


def test_tao_du_an_rong_ten_co_truong_ma_loi(khach):
    client, uid = khach
    r = client.post("/ltt-voice/du-an/tao",
                    data={"ten": "", "csrf_token": _csrf_da(client)})
    assert r.status_code == 400
    assert "ma_loi" in r.json(), "loi 400 cua /du-an/tao thieu truong ma_loi"


def test_sua_khoi_qua_dai_co_ma_loi(khach):
    client, uid = khach
    pid = _tao_du_an(client)
    bid = _them_khoi(client, pid, "ngan")

    from apps.ltt_voice.tham_so_cong_khai import TRAN_MOI_LUOT_SINH
    qua_dai = "a" * (TRAN_MOI_LUOT_SINH + 1)
    r = client.post(f"/ltt-voice/du-an/{pid}/khoi/{bid}/sua",
                    data={"text": qua_dai, "csrf_token": _csrf_da(client)})
    assert r.status_code == 400
    assert r.json()["ma_loi"] == "van_ban_qua_dai"


def test_doc_khoi_rong_van_ban_co_ma_loi(khach):
    client, uid = khach
    pid = _tao_du_an(client)
    bid = _them_khoi(client, pid, "   ")  # rong sau khi strip
    r = client.post(f"/ltt-voice/du-an/{pid}/khoi/{bid}/doc",
                    data={"csrf_token": _csrf_da(client)})
    assert r.status_code == 400
    assert r.json()["ma_loi"] == "khoi_rong"


# ── T-06 — chống nộp trùng khối ─────────────────────────────────────────────

def test_khoi_dang_tao_bi_chan_nop_lai(khach):
    """🔴 Chốt THỨ NHẤT: đọc trạng thái khối NGAY TẠI CỬA. Job đầu chưa xong
    (không worker nào chạy trong test) nên khối vẫn `dang_tao` khi bấm lại."""
    client, uid = khach
    pid = _tao_du_an(client, "Du an C")
    bid = _them_khoi(client, pid, "Cau tieng Viet binh thuong de doc thu nay.")

    r1 = client.post(f"/ltt-voice/du-an/{pid}/khoi/{bid}/doc",
                     data={"csrf_token": _csrf_da(client)})
    assert r1.status_code == 200, r1.text

    r2 = client.post(f"/ltt-voice/du-an/{pid}/khoi/{bid}/doc",
                     data={"csrf_token": _csrf_da(client)})
    assert r2.status_code == 409, r2.text
    assert r2.json()["ma_loi"] == "khoi_dang_tao"


def test_nop_mot_khoi_truyen_dedupe_key():
    """Chốt THỨ HAI (đua giữa hai request gần như đồng thời, xem chú thích ở
    `_nop_mot_khoi`): đọc CÂY CÚ PHÁP, không khớp chuỗi — cùng khuôn
    `test_525::test_doc_lai_VAN_qua_cong_va_CO_dedupe`."""
    import ast
    import inspect

    from apps.ltt_voice.routes import _p_du_an
    src = inspect.getsource(_p_du_an._nop_mot_khoi)
    tree = ast.parse(src.lstrip())
    kw = {k.arg for n in ast.walk(tree) if isinstance(n, ast.Call)
          and (getattr(n.func, "id", "") or getattr(n.func, "attr", "")) == "submit_with_credit"
          for k in n.keywords}
    assert "dedupe_key" in kw, "_nop_mot_khoi khong truyen dedupe_key cho submit_with_credit"
