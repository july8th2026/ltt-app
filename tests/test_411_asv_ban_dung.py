"""Auto Scan Video — COMPOSE: bản dựng là DỮ LIỆU, và mọi tham chiếu được soi trước.

  §1 hình dạng bản dựng
  §2 đối chiếu tham chiếu trước khi tốn render   <- việc thật của giai đoạn này
  §3 tất định và vân tay
  §4 ranh giới composer ≠ renderer
  §5 cổng thoát

⛔ Prompt 14 cấm: không render FFmpeg cuối cùng trong composer.
"""
from __future__ import annotations

import json

import pytest


def _ke_hoach(so=3, *, cat_mot=False):
    doan = []
    for i in range(so):
        doan.append({
            "ma": f"seg_{i:04d}",
            "dat_tai_ms": i * 2000,
            "dai_ms": 0 if (cat_mot and i == 1) else 1500,
            "he_so_toc": 1.0,
            "cat_bot_ms": 1500 if (cat_mot and i == 1) else 0,
            "troi_sau_ms": 0,
            "ngan_sach_ms": 2000,
            "khoang_lang_ms": 500,
        })
    return {"schema": 1, "che_do": "fit_original", "tong_ms": so * 2000,
            "ket_cuoi_ms": (so - 1) * 2000 + 1500, "so_doan": so,
            "so_doan_bi_cat": 1 if cat_mot else 0, "troi_toi_da_ms": 0,
            "doan": doan}


def _ban_ke(so=3):
    return {"schema": 1, "doan": [
        {"ma": f"seg_{i:04d}", "khoa": f"asv/uA/r1/voice_synthesis/vt{i}.wav",
         "giay": 1.5} for i in range(so)]}


def _dung(**kw):
    from apps.auto_scan_video import ban_dung
    goc = dict(khoa_video="asv/uA/nguon/a.mp4",
               khoa_nen="asv/uA/r1/audio_prepare/bed.wav",
               # ⚠️ Pha 22: `master` la truong trinh render THUC SU doc, va
               #    `kiem` doi no tu khi mot lan chay that giao ra video mang
               #    nhac nen thay vi ban long tieng.
               khoa_master="asv/uA/r1/timing_align/master.wav",
               ke_hoach=_ke_hoach(), ban_ke_tieng=_ban_ke(),
               phien_ban_ffmpeg="8.0.1", tong_giay=6.0)
    goc.update(kw)
    return ban_dung.dung(**goc)


# ══════════════════════════════════════════════════════════════════════════════
#  §1 Hình dạng
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_dung_la_DU_LIEU_khong_phai_chuoi_lenh():
    """⭐ Cách dễ hơn là sinh sẵn chuỗi `ffmpeg -i ... -filter_complex ...`.

    Nhưng như thế là đính quyết định biên tập vào một **phiên bản ffmpeg**: đổi
    cú pháp bộ lọc là phải chạy lại cả chuỗi AI ở thượng nguồn chỉ để sinh lại
    một chuỗi lệnh.
    """
    ban = _dung()
    goi = json.dumps(ban)
    # ⚠️ Chốt **cú pháp lệnh**, không chốt chữ "ffmpeg". Bản đầu của phép kiểm
    #    này cấm cả chuỗi `ffmpeg` và đỏ ngay — vì bản dựng **phải** ghi phiên
    #    bản công cụ (`cong_cu.ffmpeg`), đúng thứ Prompt 14 mục 6 bắt buộc.
    #    Một danh sách dấu hiệu quá rộng bắt nhầm chính thứ nó nên bảo vệ.
    for dau in ("-filter_complex", "-map ", "atempo", "amix", "-c:v", "-c:a"):
        assert dau not in goi, f"bản dựng chứa cú pháp lệnh: {dau}"
    assert isinstance(ban["tieng"]["lop"], list)


def test_hinh_luon_la_COPY():
    """🔑 D-ASV-03. Một bản dựng khai chế độ khác `copy` là một bản dựng sẽ mã
    hoá lại hình của khách — tiêu GPU và mất chất lượng cho một việc họ không
    yêu cầu."""
    from apps.auto_scan_video import ban_dung

    assert _dung()["hinh"]["che_do"] == "copy"

    xau = _dung()
    xau["hinh"]["che_do"] = "libx264"
    with pytest.raises(ban_dung.BanDungError) as loi:
        ban_dung.kiem(xau)
    assert "copy" in str(loi.value)


def test_doan_BI_CAT_o_TIMING_khong_vao_ban_dung():
    """Đoạn `dai_ms == 0` đã bị cắt vì vượt trần trôi. Bỏ qua ở đây, nhưng
    `so_doan_bi_cat` của kế hoạch vẫn giữ dấu vết cho QC (T12)."""
    ban = _dung(ke_hoach=_ke_hoach(cat_mot=True))
    ma = [l["ma"] for l in ban["tieng"]["lop"]]
    assert ma == ["seg_0000", "seg_0002"]


def test_doan_co_ke_hoach_ma_THIEU_TIENG_bi_tu_choi():
    from apps.auto_scan_video import ban_dung

    thieu = _ban_ke(3)
    thieu["doan"] = [d for d in thieu["doan"] if d["ma"] != "seg_0001"]
    with pytest.raises(ban_dung.BanDungError) as loi:
        _dung(ban_ke_tieng=thieu)
    assert "seg_0001" in str(loi.value)


def test_he_so_toc_NHO_HON_1_bi_tu_choi():
    """Chậm lại không nằm trong mô hình: ADR-003 chỉ dùng tăng tốc để **trả nợ**.
    Một hệ số < 1 là một phép biến đổi không ai quyết định."""
    from apps.auto_scan_video import ban_dung

    ban = _dung()
    ban["tieng"]["lop"][0]["he_so_toc"] = 0.9
    with pytest.raises(ban_dung.BanDungError):
        ban_dung.kiem(ban)


def test_ban_dung_KHONG_chua_bi_mat():
    """Prompt 14 mục 4. Bản dựng được lưu bền vững và đọc lại được, nên mọi thứ
    trong nó là thứ chịu được việc bị đọc."""
    from apps.auto_scan_video import ban_dung

    ban = _dung()
    ban["cong_cu"]["api_key"] = "sk-gia-dinh"
    with pytest.raises(ban_dung.BanDungError) as loi:
        ban_dung.kiem(ban)
    assert "api_key" in str(loi.value)


def test_ban_dung_KHONG_chua_duong_dan_tuyet_doi():
    """⛔ Một lần chạy lại có thể rơi vào worker khác, và `C:\\...\\tmp\\abc` của
    máy khác là một bản dựng hỏng theo kiểu "tệp không tồn tại" — chỉ vào sai chỗ.
    """
    goi = json.dumps(_dung())
    assert ":\\" not in goi and ":/" not in goi
    assert "/tmp/" not in goi and "\\tmp\\" not in goi


def test_phien_ban_cong_cu_duoc_DONG_BANG():
    """Prompt 14 mục 6. Một bản dựng không ghi phiên bản công cụ là một bản dựng
    không tái lập được: nâng ffmpeg rồi render lại có thể ra tệp khác, và không
    có gì trong hồ sơ nói vì sao."""
    assert _dung(phien_ban_ffmpeg="7.1.2")["cong_cu"]["ffmpeg"] == "7.1.2"


# ══════════════════════════════════════════════════════════════════════════════
#  §2 Đối chiếu tham chiếu — việc thật của giai đoạn này
# ══════════════════════════════════════════════════════════════════════════════

def test_tham_chieu_KHONG_TON_TAI_bi_bat_TRUOC_khi_render():
    """🔑 Mục 5. Một bản dựng trỏ tới một artifact không còn là một lần render
    thất bại ở phút thứ mười — sau khi đã chiếm suất, đã tải tệp, đã giải mã.
    Bắt ở đây tốn vài mili giây."""
    from apps.auto_scan_video import ban_dung

    ban = _dung()
    # ⚠️ `master` nam trong tap doi chieu tu pha 22 — trinh render doc no, nen
    #    thieu no la mot lan render hong o giua chung.
    du = {ban["hinh"]["khoa"], ban["tieng"]["nen"]["khoa"],
          ban["tieng"]["master"]["khoa"]}
    du |= {l["khoa"] for l in ban["tieng"]["lop"]}

    ban_dung.kiem(ban, khoa_hop_le=du)          # đủ -> qua

    thieu = du - {ban["tieng"]["lop"][1]["khoa"]}
    with pytest.raises(ban_dung.BanDungError) as loi:
        ban_dung.kiem(ban, khoa_hop_le=thieu)
    assert "1" in str(loi.value)


def test_doi_chieu_kiem_TOAN_VEN_chu_khong_tin_cot_da_luu(tmp_path, monkeypatch):
    """⭐ Bản ghi nói `ok` từ lần kiểm trước, còn tệp thì có thể đã biến mất
    trong khoảng giữa. Đối chiếu phải đo lại tệp thật."""
    import platform_core.db as dbmod
    from platform_core.storage import LocalStorage, set_storage
    from tests.conftest import bao_dam_user

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    kho = LocalStorage(str(tmp_path / "kho")); set_storage(kho)
    try:
        import io

        from platform_core import credit
        from apps.auto_scan_video import assets, features, giai_doan_ban_dung

        bao_dam_user(db, "uA"); credit.nap(db, "uA", 100)
        run = features.tao_run(db, owner_id="uA", source_key="asv/uA/x.mp4",
                               settings={"giong_id": "Minh Đức"}, uoc_luong_credit=0)
        db.commit()

        tam = assets.khoa_staging(owner_id="uA", run_id=run.id, stage="compose",
                                  van_tay="vt", duoi="json")
        kho.put(tam, io.BytesIO(b'{"a":1}'), content_type="application/json")
        a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id=run.id,
                                  stage="compose", van_tay="vt", kind="json",
                                  duoi="json", staging_key=tam)
        db.commit()
        assert a.storage_key in giai_doan_ban_dung._khoa_con_dung(db, kho, run)

        kho.delete(a.storage_key)      # bản ghi vẫn nói `ok`, tệp đã mất
        assert a.storage_key not in giai_doan_ban_dung._khoa_con_dung(db, kho, run)
    finally:
        db.close(); set_storage(None); dbmod.reset_engine()


# ══════════════════════════════════════════════════════════════════════════════
#  §3 Tất định và vân tay
# ══════════════════════════════════════════════════════════════════════════════

def test_cung_dau_vao_ra_cung_mot_ban_dung():
    """Prompt 14: "deterministic same-input generation"."""
    a = json.dumps(_dung(), sort_keys=True)
    b = json.dumps(_dung(), sort_keys=True)
    assert a == b


def test_van_tay_doi_theo_moi_dau_vao_va_chinh_sach():
    from apps.auto_scan_video import ban_dung

    goc = dict(checksum_ke_hoach="aaa", khoa_video="v", khoa_nen="n",
               phien_ban_ffmpeg="8.0")
    nen = ban_dung.van_tay_ban_dung(**goc)
    for ten, moi in (("checksum_ke_hoach", "bbb"), ("khoa_video", "v2"),
                     ("khoa_nen", "n2"), ("phien_ban_ffmpeg", "7.1")):
        assert ban_dung.van_tay_ban_dung(**{**goc, ten: moi}) != nen, ten


@pytest.mark.parametrize("ten", [
    "CODEC_TIENG", "BITRATE_TIENG", "TAN_SO_RA", "SO_KENH_RA",
    "PHIEN_BAN_BAN_DUNG",
])
def test_doi_CHINH_SACH_dau_ra_cung_doi_van_tay(monkeypatch, ten):
    """O13 — đổi chính sách đầu ra là đổi tệp giao cho khách."""
    from apps.auto_scan_video import ban_dung

    goc = dict(checksum_ke_hoach="aaa", khoa_video="v", khoa_nen="n",
               phien_ban_ffmpeg="8.0")
    truoc = ban_dung.van_tay_ban_dung(**goc)
    cu = getattr(ban_dung, ten)
    monkeypatch.setattr(ban_dung, ten, cu * 2 if isinstance(cu, int) else cu + "x")
    assert ban_dung.van_tay_ban_dung(**goc) != truoc, f"{ten} không vào vân tay"


def test_thoi_luong_mong_doi_duoc_ghi_de_render_doi_chieu():
    """Trình render đối chiếu bản thật với số này; lệch quá ngưỡng là một lỗi,
    không phải một ghi chú."""
    assert _dung(tong_giay=12.5)["ra"]["thoi_luong_giay"] == 12.5


# ══════════════════════════════════════════════════════════════════════════════
#  §4 Ranh giới composer ≠ renderer
# ══════════════════════════════════════════════════════════════════════════════

def test_composer_KHONG_sinh_media(monkeypatch):
    """⛔ Prompt 14 mục 7 + G9. Trộn biên tập vào thi hành nghĩa là một lần đổi
    công cụ render kéo theo một lần chạy lại cả chuỗi AI ở thượng nguồn."""
    import inspect

    from apps.auto_scan_video import ban_dung, giai_doan_ban_dung
    from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

    # ⚠️ `"run"` KHÔNG nằm trong danh sách, dù nó là tên hàm chạy tiến trình con.
    #    Bản đầu có nó và đỏ ngay — vì `chay(db, kho, *, run, ctx)` có một tham
    #    số tên `run`. Một dấu hiệu ngắn tới mức khớp cả tên biến thường gặp thì
    #    không đo được thứ nó định đo; nó chỉ đo rằng ai đó đã đặt tên như thế.
    for mod in (ban_dung, giai_doan_ban_dung):
        ma = inspect.getsource(mod)
        assert _vi_pham(ma, ("subprocess", "ffmpeg_bin", "ffprobe_bin",
                             "Popen", "check_output")) == [], (
            f"{mod.__name__} có dấu hiệu chạy tiến trình con")


def test_composer_khong_goi_lai_giai_doan_AI_nao():
    """Cổng thoát: bản dựng phải định nghĩa đủ một lần render **mà không chạy
    lại giai đoạn AI nào ở thượng nguồn**."""
    import inspect

    from apps.auto_scan_video import ban_dung, giai_doan_ban_dung
    from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

    for mod in (ban_dung, giai_doan_ban_dung):
        assert _vi_pham(inspect.getsource(mod),
                        ("dich_thuat", "giong_noi", "chep_loi",
                         "tach_tieng", "transcribe_file")) == [], mod.__name__


# ══════════════════════════════════════════════════════════════════════════════
#  §5 Cổng thoát
# ══════════════════════════════════════════════════════════════════════════════

def test_cong_thoat_ban_dung_dinh_nghia_du_MOT_LAN_RENDER():
    """Bản dựng đọc lại từ kho phải đủ để render: nguồn hình, nhạc nền, từng lớp
    tiếng kèm vị trí và hệ số tốc độ, chính sách đầu ra, và phiên bản công cụ."""
    from apps.auto_scan_video import ban_dung

    ban = json.loads(json.dumps(_dung()))     # vòng qua JSON như đọc từ kho
    ban_dung.kiem(ban)

    assert ban["hinh"]["khoa"] and ban["hinh"]["che_do"] == "copy"
    assert ban["tieng"]["nen"]["khoa"]
    assert ban["tieng"]["tan_so"] == 48000 and ban["tieng"]["so_kenh"] == 2
    for lop in ban["tieng"]["lop"]:
        assert lop["khoa"] and lop["dat_tai_ms"] >= 0 and lop["he_so_toc"] >= 1.0
    assert ban["ra"]["codec_tieng"] == "aac" and ban["ra"]["faststart"] is True
    assert ban["ra"]["thoi_luong_giay"] > 0
    assert ban["cong_cu"]["ffmpeg"]


# ══════════════════════════════════════════════════════════════════════════════
#  Pha 22 — ban phoi la truong TRINH RENDER DOC, nen `kiem` phai doi no
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_dung_THIEU_ban_phoi_bi_tu_choi():
    """🔴 Truoc pha 22 `kiem` doi `nen` nhung khong doi `master`, trong khi thu
    trinh render doc la `master`.

    Hau qua do duoc tren mot lan chay that: `giai_doan_ket_xuat` tai ve `nen` —
    nhac nen tach ra tu ban goc — va giao cho khach mot video **khong co mot cau
    long tieng nao**. Am luong tep ra noi ro no chua he di qua chuan hoa:
    -18,69 LUFS (dich -14) va dinh that **+4,1 dB** (tran -1,5).

    ⭐ Mot truong ma trinh render bat buoc phai co thi phai duoc kiem o day —
       khong phai o giua mot luot ffmpeg da chiem suat va da tai vai tram MB.
    """
    from apps.auto_scan_video import ban_dung

    ban = _dung()
    ban["tieng"]["master"]["khoa"] = ""
    with pytest.raises(ban_dung.BanDungError) as loi:
        ban_dung.kiem(ban)
    assert "phối" in str(loi.value)


def test_ban_phoi_KHONG_CON_TRONG_KHO_bi_bat_truoc_khi_render():
    """⛔ Khoa ban phoi phai nam trong tap doi chieu tai nguyen.

    Neu khong, mot ban phoi da bi don dep van cho ra mot ban dung "hop le", va
    lan render hong o giua chung — sau khi da tai luong hinh ve dia.
    """
    from apps.auto_scan_video import ban_dung

    ban = _dung()
    du = {ban["hinh"]["khoa"], ban["tieng"]["nen"]["khoa"],
          ban["tieng"]["master"]["khoa"]}
    du |= {l["khoa"] for l in ban["tieng"]["lop"]}
    ban_dung.kiem(ban, khoa_hop_le=du)                    # du -> qua

    with pytest.raises(ban_dung.BanDungError):
        ban_dung.kiem(ban, khoa_hop_le=du - {ban["tieng"]["master"]["khoa"]})
