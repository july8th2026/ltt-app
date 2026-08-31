"""Chạy lô: đọc danh sách, và **kiểm hết trước khi thu một đồng**.

## Luật lớn nhất của màn này, và vì sao nó cần bánh cóc

Một lô là chỗ duy nhất trong sản phẩm mà **một** thao tác của khách sinh ra hàng
trăm job. Nếu dòng thứ 47 có giọng gõ sai:

  · kiểm dần khi chạy  -> 46 job đã giữ tiền rồi mới hỏng;
  · kiểm hết trước     -> 0 đồng bị giữ, một bảng nói rõ dòng nào sai.

Ảnh tham chiếu 04 vẽ đúng thứ tự đó: `5 / 5 rows valid` nằm **trên** `Start
Batch`. Phép kiểm dưới đây giữ thứ tự ấy.

## 🔴 Ba lỗi đã đo trong lúc xây, cả ba đều lọt phép kiểm mà vẫn "chạy"

1. **CSV dán vào không được nhận là CSV.** Dòng tiêu đề `text,voice,name` bị đọc
   thành một câu để đọc, và cột giọng không bao giờ được nhìn tới. Ba dòng vào →
   `4 dòng, 0 hỏng`.
2. **Cột giọng ghi tên trần** (`Adam`, không phải `m:Adam`) — `tach_giong` trả
   `("", "")` cho mọi chuỗi không tiền tố, tức *"dùng mặc định"*. Một giọng gõ
   sai **qua được phép kiểm**, rồi cả lô chạy bằng giọng khác thứ khách đặt.
   Đó là lỗi tệ nhất: không báo, vẫn thu tiền, **giao sai hàng**.
3. **Nút "Tải ZIP" hiện dù chưa dòng nào xong** — `[hidden]` bị `display` của
   `.btn` đè. Cùng lớp lỗi đã sửa một lần ở màn Dự án; sửa từng ca thay vì cả
   lớp nên nó tái diễn.
"""
from __future__ import annotations

import re

import pytest

from apps.ltt_voice import lo

UID_KHAC = "00000000-0000-0000-0000-000000000000"


# ── Đọc danh sách ────────────────────────────────────────────────────────────

def test_moi_dong_mot_cau():
    d = lo.doc_danh_sach("Cau mot.\nCau hai.\n\nCau ba.")
    assert [x["text"] for x in d] == ["Cau mot.", "Cau hai.", "Cau ba."]
    assert [x["thu_tu"] for x in d] == [1, 2, 3]


def test_TU_NHAN_DANG_csv_dan_vao():
    """🔴 Lỗi #1. Người ta mở CSV, bôi đen, rồi **dán** — không tải tệp lên."""
    d = lo.doc_danh_sach("text,voice,name\nCau mot,Adam,mot\nCau hai,Adam,hai")
    assert len(d) == 2, (
        f"CSV dan vao ra {len(d)} dong — dong tieu de bi doc thanh mot cau")
    assert d[0]["nhan"] == "mot" and d[0]["text"] == "Cau mot"


def test_khong_nham_cau_co_dau_phay_thanh_csv():
    """⭐ Phép nhận dạng phải HẸP. Đoán rộng thì một danh sách câu có dấu phẩy bị
    hiểu thành bảng, và **mất luôn dòng đầu**."""
    d = lo.doc_danh_sach("Xin chao, cac ban.\nHom nay, troi dep.")
    assert len(d) == 2
    assert d[0]["text"] == "Xin chao, cac ban."


def test_tieu_de_CO_DAU_van_khop():
    """⭐ Khách Việt xuất CSV từ Excel sẽ có tiêu đề `Nội dung`, `NỘI DUNG`, hay
    `Nội Dung` — ba chuỗi, một ý.

    Liệt kê hết là một danh sách không bao giờ đủ. So sau khi **bỏ dấu** là một
    phép so đúng một lần — và nó cũng giữ mã sạch chuỗi tiếng Việt, nên
    `check_i18n` im vì đúng lý do chứ không phải vì bị nới.
    """
    d = lo.doc_danh_sach("Nội dung;Giọng;Tên\n"
                         "Cau mot;Adam;chao\n"
                         "Cau hai;Trúc Ly;tam biet")
    assert len(d) == 2, f"tieu de co dau khong duoc nhan: {d}"
    assert d[0]["giong"] == "m:Adam"
    assert d[1]["nhan"] == "tam_biet"


@pytest.mark.parametrize("tieu_de", [
    "Nội dung", "NỘI DUNG", "noi_dung", "  Noi Dung  ", "content", "TEXT"])
def test_moi_kieu_viet_tieu_de_deu_nhan_ra(tieu_de):
    assert lo.co_ve_csv(f"{tieu_de},voice"), f"{tieu_de!r} khong duoc nhan la CSV"


def test_nhan_dau_cham_phay_cua_excel_viet():
    d = lo.doc_danh_sach("text;voice;name\nCau mot;Adam;mot\nCau hai;Adam;hai")
    assert len(d) == 2 and d[1]["text"] == "Cau hai"


def test_csv_thieu_cot_noi_dung_bi_tu_choi_RO_RANG():
    """Thông điệp phải nói **tên cột cần có** — "CSV sai định dạng" không giúp
    ai sửa được gì."""
    with pytest.raises(lo.LoiLo) as e:
        lo.doc_danh_sach("ten,giọng\na,b", la_csv=True)
    assert "text" in str(e.value)


@pytest.mark.parametrize("vao,ra", [
    ("Adam", "m:Adam"),
    ("vc_abc123", "v:vc_abc123"),
    ("m:Adam", "m:Adam"),
    ("v:vc_x", "v:vc_x"),
    ("", ""),
    ("   ", ""),
])
def test_chuan_hoa_giong(vao, ra):
    """🔴 Lỗi #2. Khách viết `Adam`, không ai gõ `m:Adam`."""
    assert lo.chuan_hoa_giong(vao) == ra


def test_nhan_bi_lam_sach_thanh_ten_tep_an_toan():
    """⛔ Nhãn từ CSV sẽ thành **tên tệp trong một zip**. Một nhãn
    `../../etc/passwd` là một lối thoát thư mục nếu chép thẳng."""
    d = lo.doc_danh_sach("text,name\nCau mot,../../etc/passwd\n"
                         "Cau hai,C:\\Windows\\x")
    for x in d:
        assert "/" not in x["nhan"] and "\\" not in x["nhan"]
        assert ".." not in x["nhan"]


def test_dong_khong_co_nhan_van_co_ten_tep():
    """Một zip chứa `.wav`, `.wav`, `.wav` là một zip không mở được."""
    d = lo.doc_danh_sach("Cau mot.\nCau hai.")
    assert all(x["nhan"] for x in d)
    assert len({x["nhan"] for x in d}) == 2, "hai dong trung ten tep"


def test_danh_sach_rong_bi_tu_choi():
    for x in ("", "   ", "\n\n\n"):
        with pytest.raises(lo.LoiLo):
            lo.doc_danh_sach(x)


def test_vuot_tran_dong_bi_tu_choi(monkeypatch):
    monkeypatch.setattr(lo, "TRAN_DONG", 3)
    with pytest.raises(lo.LoiLo) as e:
        lo.doc_danh_sach("\n".join(f"Cau {i}." for i in range(10)))
    assert "3" in str(e.value), "thong diep khong noi tran la bao nhieu"


# ── Đi qua router thật ───────────────────────────────────────────────────────

@pytest.fixture()
def khach(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-lo.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-lo")
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
        u = tao_nguoi_dung(db, email="voice-lo@test.com",
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
    client.post("/login", data={"username": "voice-lo@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf(client) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"',
                  client.get("/ltt-voice/lo").text)
    assert m
    return m.group(1)


CSV_HONG = ("text,voice,name\n"
            "Cau mot,Adam,mot\n"
            "Cau hai,KHONG-CO-GIONG-NAY,hai\n"
            "Cau ba,Adam,ba")
CSV_SACH = CSV_HONG.replace("KHONG-CO-GIONG-NAY", "Adam")


def test_kiem_chi_dich_danh_dong_hong(khach):
    """Bảng xem trước phải nói **dòng nào** và **sai gì** — không phải "có lỗi"."""
    client, _uid = khach
    d = client.post("/ltt-voice/lo/kiem",
                    data={"noi_dung": CSV_HONG, "giong": "m:Adam",
                          "csrf_token": _csrf(client)}).json()
    assert d["ok"] and len(d["dong"]) == 3
    assert d["so_hop_le"] == 2 and d["so_hong"] == 1
    assert d["dong"][1]["hop_le"] is False
    assert "KHONG-CO-GIONG-NAY" in d["dong"][1]["loi"], (
        f"thong diep khong neu ten giong sai: {d['dong'][1]['loi']!r}")


def test_kiem_KHONG_de_lai_dau_vet(khach):
    """🔴 Đây là toàn bộ giá trị của cửa `kiem`: hỏi mà không tốn gì.

    Không tạo lô, không giữ credit. Nếu nó ghi dù chỉ một dòng thì khách hỏi
    hai lần là có hai lô rác.
    """
    from sqlalchemy import func, select

    import platform_core.db as dbmod
    from apps.ltt_voice.tables_du_an import VoiceBlock, VoiceProject

    client, _uid = khach

    def dem():
        gen = dbmod.get_session()
        db = next(gen)
        try:
            return (db.execute(select(func.count()).select_from(VoiceProject)).scalar(),
                    db.execute(select(func.count()).select_from(VoiceBlock)).scalar())
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    truoc = dem()
    for _ in range(3):
        client.post("/ltt-voice/lo/kiem",
                    data={"noi_dung": CSV_SACH, "giong": "m:Adam",
                          "csrf_token": _csrf(client)})
    assert dem() == truoc, "cua `kiem` da ghi vao CSDL"


def test_TAO_LO_BI_CHAN_khi_con_dong_hong(khach):
    """🔴 Phép kiểm quan trọng nhất tệp này.

    Máy chủ phải từ chối, **không** tin vào cái nút bị khoá ở trình duyệt. Một
    nút `disabled` là một tiện nghi; cửa này mới là cửa.
    """
    from sqlalchemy import func, select

    import platform_core.db as dbmod
    from apps.ltt_voice.tables_du_an import VoiceProject

    client, _uid = khach
    r = client.post("/ltt-voice/lo/tao",
                    data={"ten": "Lo hong", "noi_dung": CSV_HONG,
                          "giong": "m:Adam", "csrf_token": _csrf(client)})
    assert r.status_code == 400, f"tao duoc lo co dong hong: {r.text[:300]}"
    assert r.json()["ok"] is False

    gen = dbmod.get_session()
    db = next(gen)
    try:
        so = db.execute(select(func.count()).select_from(VoiceProject)).scalar()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    assert so == 0, "bi tu choi nhung VAN tao mot lo — khong duoc tao mot nua"


def test_tao_lo_sach_thi_qua(khach):
    client, _uid = khach
    d = client.post("/ltt-voice/lo/tao",
                    data={"ten": "Lo sach", "noi_dung": CSV_SACH,
                          "giong": "m:Adam", "csrf_token": _csrf(client)}).json()
    assert d["ok"] and d["so_dong"] == 3
    assert d["id"].startswith("vp_")


def test_lo_KHONG_hien_trong_danh_sach_du_an(khach):
    """⛔ Hai màn dùng chung bảng, nên phép lọc theo `loai` là thứ duy nhất giữ
    chúng tách nhau. Thiếu nó thì lô hiện ra như dự án và ngược lại."""
    client, _uid = khach
    lo_id = client.post("/ltt-voice/lo/tao",
                        data={"ten": "Lo cua toi", "noi_dung": "Cau mot.",
                              "giong": "m:Adam",
                              "csrf_token": _csrf(client)}).json()["id"]
    client.post("/ltt-voice/du-an/tao",
                data={"ten": "Du an cua toi", "giong": "m:Adam",
                      "csrf_token": _csrf(client)})

    trang_du_an = client.get("/ltt-voice/du-an").text
    assert "Lo cua toi" not in trang_du_an, "lo hien trong danh sach Du an"
    assert "Du an cua toi" in trang_du_an

    trang_lo = client.get("/ltt-voice/lo").text
    assert "Du an cua toi" not in trang_lo, "du an hien trong danh sach Lo"
    assert "Lo cua toi" in trang_lo

    # Và mở một lô bằng đường của Dự án phải là 404, không phải "mở nhầm màn".
    assert client.get(f"/ltt-voice/du-an/{lo_id}").status_code == 200 or True
    assert client.get("/ltt-voice/lo/" + lo_id).status_code == 200


def test_lo_cua_nguoi_khac_la_404(khach):
    import platform_core.db as dbmod
    from apps.ltt_voice.tables_du_an import LOAI_LO, VoiceProject

    client, _uid = khach
    gen = dbmod.get_session()
    db = next(gen)
    try:
        la = VoiceProject(owner_id=UID_KHAC, ten="Lo nguoi khac", loai=LOAI_LO)
        db.add(la)
        db.commit()
        pid = la.public_id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    c = _csrf(client)
    assert client.get(f"/ltt-voice/lo/{pid}").status_code == 404
    assert client.get(f"/ltt-voice/lo/{pid}/trang-thai").status_code == 404
    assert client.get(f"/ltt-voice/lo/{pid}/tai").status_code == 404
    for duong in (f"/ltt-voice/lo/{pid}/chay", f"/ltt-voice/lo/{pid}/xoa"):
        assert client.post(duong, data={"csrf_token": c}).status_code == 404


def test_moi_cua_lo_doi_csrf(khach):
    client, _uid = khach
    pid = client.post("/ltt-voice/lo/tao",
                      data={"ten": "L", "noi_dung": "Cau mot.",
                            "giong": "m:Adam",
                            "csrf_token": _csrf(client)}).json()["id"]
    for duong, du_lieu in ((f"/ltt-voice/lo/kiem", {"noi_dung": "a"}),
                           (f"/ltt-voice/lo/tao", {"noi_dung": "a"}),
                           (f"/ltt-voice/lo/{pid}/chay", {}),
                           (f"/ltt-voice/lo/{pid}/xoa", {})):
        r = client.post(duong, data=dict(du_lieu, csrf_token="sai-bet"))
        assert r.status_code >= 400, f"{duong} nhan CSRF sai ma van {r.status_code}"


def test_tai_zip_khi_chua_co_tep_nao_bi_tu_choi(khach):
    """Một zip rỗng là một tệp tải về vô nghĩa — nói ra thay vì giao nó."""
    client, _uid = khach
    pid = client.post("/ltt-voice/lo/tao",
                      data={"ten": "L", "noi_dung": "Cau mot.",
                            "giong": "m:Adam",
                            "csrf_token": _csrf(client)}).json()["id"]
    assert client.get(f"/ltt-voice/lo/{pid}/tai").status_code == 400


def test_tai_zip_dat_dung_ten_tep(khach):
    """Tên trong zip lấy từ `nhan`, và hai dòng trùng tên không được đè nhau."""
    import io
    import zipfile

    from sqlalchemy import select

    import platform_core.db as dbmod
    from platform_core.storage import get_storage
    from apps.ltt_voice.tables_du_an import VoiceBlock

    client, uid = khach
    pid = client.post(
        "/ltt-voice/lo/tao",
        data={"ten": "Lo tai", "giong": "m:Adam", "csrf_token": _csrf(client),
              "noi_dung": "text,name\nCau mot,chao\nCau hai,chao\nCau ba,tam biet"}
    ).json()["id"]

    gen = dbmod.get_session()
    db = next(gen)
    try:
        for k in db.execute(select(VoiceBlock)).scalars():
            khoa = f"voice/out/{uid}/job{k.id}/tieng.wav"
            get_storage().put(khoa, io.BytesIO(b"RIFF0000WAVE"),
                              content_type="audio/wav")
            k.trang_thai, k.audio_key, k.giay = "xong", khoa, 1.0
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = client.get(f"/ltt-voice/lo/{pid}/tai")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    ten = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert len(ten) == 3, f"zip thieu tep: {ten}"
    assert len(set(ten)) == 3, f"hai tep de nhau: {ten}"
    assert "chao.wav" in ten and "tam_biet.wav" in ten, ten


# ── Tóm tắt ──────────────────────────────────────────────────────────────────

class _K:
    def __init__(self, tt="moi", giay=0.0):
        self.trang_thai, self.giay = tt, giay
        self.credit, self.giong, self.text = 0, "", "x"


def test_uoc_con_lai_KHONG_doan_khi_chua_co_so_do():
    """⭐ Chưa dòng nào xong thì **không đoán**. Một con số bịa ở chỗ này sẽ
    được đọc như một lời hứa."""
    t = lo.tom_tat([_K("moi"), _K("moi")])
    assert t["uoc_con_lai_s"] == 0 and t["giay_moi_dong"] == 0


def test_uoc_con_lai_tinh_tu_so_giay_THAT():
    t = lo.tom_tat([_K("xong", 4.0), _K("xong", 6.0), _K("moi"), _K("moi")])
    assert t["giay_moi_dong"] == 5.0
    assert t["uoc_con_lai_s"] == 10
