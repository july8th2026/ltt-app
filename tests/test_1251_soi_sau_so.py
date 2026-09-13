"""test_1251 — sau so quan sat. Moi so phai TU KHAI khi no khong doc duoc.

🔴 Bo nay sinh ra tu mot loi THAT ngay 13/09/2026. Phep do `requests_processing`
   tra `-1` suot mot luot do 16 kich ban, vi hai chi tiet deu im lang:

     · `/metrics` KHONG o cong 8299 (gateway tra 404) ma o cong cua chinh
       `llama-server` — 8282 cho ltt-3.8, 8281 cho ltt-3.5
     · ten chi so mang TIEN TO: `llamacpp:requests_processing`, nen mot phep loc
       `startswith("requests_processing")` khong bao gio khop

⛔ **`-1` trong y het `0`.** Mot bo do mu mot mat van in ra so, va ca luot do
   chay xong roi moi lo ra. `MauSo.doc_duoc` ton tai de dieu do khong lap lai:
   so nao khong doc duoc thi **tu khai**, khong tra mot con so.

## ⛔ Phep kiem nay KHONG duoc goi production

Duong that chi chay o Pha 0 (`tu_kiem`), tren may that, do nguoi bam. O day moi
so duoc thay bang mot ban gia — va ban gia dong vai MOT VIEC (tra van ban), chu
khong dong vai chu ky day du.
"""
import pytest

from tools.nghiem_thu_van_hanh import soi

_METRICS = """\
# HELP llamacpp:requests_processing Number of requests processing
# TYPE llamacpp:requests_processing gauge
llamacpp:requests_processing 3
llamacpp:requests_deferred 1
"""

#: Ban ghi THIEU tien to — dung thu mot phep loc ngay tho se khop nham.
_METRICS_KHONG_TIEN_TO = "requests_processing 9\n"


# ── so slot (may B) ───────────────────────────────────────────────────────
def test_so_slot_doc_dung_ten_co_TIEN_TO(monkeypatch):
    monkeypatch.setattr(soi, "_curl_may_b", lambda cong: _METRICS)
    m = soi.so_slot(8282)
    assert m.doc_duoc is True
    assert m.gia_tri == 3


def test_so_slot_KHONG_doc_duoc_thi_TU_KHAI_chu_khong_tra_so(monkeypatch):
    """⛔ Khong duoc tra -1. Mot so am se bi doc thanh 'slot da nha'."""
    monkeypatch.setattr(soi, "_curl_may_b", lambda cong: "")
    m = soi.so_slot(8282)
    assert m.doc_duoc is False
    assert m.ly_do, "khong doc duoc thi phai NOI vi sao"
    assert not isinstance(m.gia_tri, int) or m.gia_tri is None, (
        "tra ve mot so khi khong doc duoc la dung cai bay 13/09")


def test_so_slot_BO_QUA_dong_thieu_tien_to(monkeypatch):
    """🔴 Doi chung cho chinh phep loc: `requests_processing` tran KHONG phai no.

    Thieu ve nay thi mot phep loc ngay tho (`"requests_processing" in dong`)
    van XANH o hai ve tren, va ta khong biet minh dang khop nham dong nao.
    """
    monkeypatch.setattr(soi, "_curl_may_b", lambda cong: _METRICS_KHONG_TIEN_TO)
    m = soi.so_slot(8282)
    assert m.doc_duoc is False, (
        "dong khong co tien to `llamacpp:` da bi doc thanh chi so that")


# ── tu kiem ───────────────────────────────────────────────────────────────
def test_tu_kiem_NEM_khi_mot_so_khong_doc_duoc(monkeypatch):
    """Pha 0 phai chan lo do lai, khong duoc canh bao roi chay tiep.

    ⛔ Mot bo do tu nhan minh mu roi van do la te hon mot bo do khong chay.
    """
    monkeypatch.setattr(soi, "so_lease", lambda *_a, **_k: soi.MauSo("lease", 0, True))
    monkeypatch.setattr(soi, "so_jobs", lambda *_a, **_k: soi.MauSo("jobs", 0, True))
    monkeypatch.setattr(soi, "so_credit", lambda *_a, **_k: soi.MauSo("credit", 0, True))
    monkeypatch.setattr(soi, "so_residency",
                        lambda *_a, **_k: soi.MauSo("residency", "llm", True))
    monkeypatch.setattr(soi, "so_http", lambda *_a, **_k: soi.MauSo("http", "abc", True))
    monkeypatch.setattr(soi, "so_slot",
                        lambda *_a, **_k: soi.MauSo("slot", None, False, "cong sai"))

    with pytest.raises(soi.SoMu) as e:
        soi.tu_kiem("sqlite://", "http://127.0.0.1:8100")
    assert "slot" in str(e.value)


def test_tu_kiem_tra_DU_SAU_so_khi_lanh(monkeypatch):
    for ten in ("lease", "jobs", "credit", "residency", "http", "slot"):
        monkeypatch.setattr(soi, f"so_{ten}",
                            (lambda t: lambda *_a, **_k: soi.MauSo(t, 1, True))(ten))
    ds = soi.tu_kiem("sqlite://", "http://127.0.0.1:8100")
    assert {m.ten for m in ds} == {"lease", "jobs", "credit",
                                   "residency", "http", "slot"}, (
        "Pha 0 phai hoi DU sau so. Them so thu bay ma quen noi vao day thi no "
        "khong bao gio duoc kiem, va ta lai mu mot mat.")


def test_MauSo_bat_bien():
    """Ban ghi quan sat khong duoc sua sau khi chup.

    ⚠️ Bat DUNG loai (`FrozenInstanceError`), khong phai `Exception` tran: mot
       `pytest.raises(Exception)` se XANH ngay ca khi `m.gia_tri = 4` that bai
       vi mot ly do khac han — vi du `MauSo` doi thanh mot lop khong co truong
       ay nua. Ve rong nhu the chot duoc rat it ma trong nhu chot duoc nhieu.
    """
    import dataclasses

    m = soi.MauSo("lease", 3, True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.gia_tri = 4        # type: ignore[misc]
