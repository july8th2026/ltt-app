"""Auto Scan Video V4 — tach canh + lay khung mau (pha 10).

**§1 tat dinh** — cung tep + cung nguong => cung danh sach moc. Khong ngau nhien,
     khong thoi gian thuc, khong phu thuoc so nhan CPU.

**§2 chan bo nho** — 🔴 mot video 40 phut la ~60.000 khung; giai ma tung khung
     vao Python la 350 GB di qua RAM. `ffmpeg` doc chung va chi in ra MOC; ta
     khong cham mot pixel nao.

**§3 chan so khung** — pha 11 gui chung cho VLM, va cua so thi giac chi 65.536
     token (mot nua ban van ban). Tran nam o cho SINH ra khung, khong o cho tieu
     thu — mot cua chan dat sau cho tieu tien la mot cua chan dat sai cho.

**§4 phu HET nguon, dung THU TU** — mot chi muc lech thu tu se lam moi quyet dinh
     bien tap phia sau tro vao sai cho.

⛔ Khong phep kiem nao o day can ffmpeg. Phan goi nhi phan duoc tach rieng khoi
   phan tinh toan chinh vi ly do do: mot bo do phu thuoc mot nhi phan ben ngoai
   la mot bo do khong chay tren may khong co no, va luc do no im lang thay vi do.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.auto_scan_video import canh as c

GOC = pathlib.Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "auto_scan_video"

#: Dau ra `metadata=print` that cua ffmpeg, rut gon.
FFMPEG_STDERR = """
[Parsed_metadata_1 @ 000001] frame:0    pts:12288   pts_time:0.256
lavfi.scene_score=0.612
[Parsed_metadata_1 @ 000001] frame:1    pts:57344   pts_time:5.200
lavfi.scene_score=0.884
[Parsed_metadata_1 @ 000001] frame:2    pts:98304   pts_time:12.750
lavfi.scene_score=0.451
"""


def _chi_muc(khoang, thoi_luong) -> c.ChiMucCanh:
    return c.ChiMucCanh(
        tuple(c.Canh(f"canh_{i:04d}", b, e, tuple(c.moc_khung_mau(b, e)))
              for i, (b, e) in enumerate(khoang, start=1)),
        thoi_luong)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Tat dinh
# ══════════════════════════════════════════════════════════════════════════════

def test_cung_dau_vao_ra_cung_moc():
    a = c.doc_moc_tu_ffmpeg(FFMPEG_STDERR)
    b = c.doc_moc_tu_ffmpeg(FFMPEG_STDERR)
    assert a == b == [0.256, 5.2, 12.75]


def test_moc_TRUNG_bi_gop_va_ket_qua_da_sap():
    """Ffmpeg co the in mot moc hai lan khi hai bo loc cung bao. Ket qua phai
    on dinh bat ke thu tu xuat hien."""
    xao = "pts_time:9.0\npts_time:1.0\npts_time:9.0\npts_time:4.0"
    assert c.doc_moc_tu_ffmpeg(xao) == [1.0, 4.0, 9.0]


def test_moc_khung_mau_KHONG_ngau_nhien():
    a = c.moc_khung_mau(0.0, 9.0)
    b = c.moc_khung_mau(0.0, 9.0)
    assert a == b == [3.0, 6.0]


def test_khung_mau_TRANH_hai_dau_canh():
    """⚠️ Khung ngay tai ranh gioi thuong la khung chuyen canh (mo, den, chong
    hinh) — no khong dai dien cho canh nao ca."""
    for m in c.moc_khung_mau(10.0, 20.0):
        assert 10.0 < m < 20.0


def test_van_tay_doi_khi_NGUONG_doi():
    """Doi nguong la doi ket qua, nen no phai nam trong van tay.

    ⭐ Chot o day bang cach: hai nguong khac nhau phai cho ra hai chi muc khac
       nhau tren cung mot dau vao — neu khong, nguong khong phai mot tham so ma
       la mot thu trang tri.
    """
    moc = [2.0, 8.0]
    a = _chi_muc(c.gop_canh_ngan(moc, 20.0, ngan_nhat=1.0), 20.0)
    b = _chi_muc(c.gop_canh_ngan(moc, 20.0, ngan_nhat=7.0), 20.0)
    assert len(a.canh) != len(b.canh)


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Chan bo nho — khong doc pixel nao vao Python
# ══════════════════════════════════════════════════════════════════════════════

def test_KHONG_giai_ma_khung_hinh_trong_Python():
    """🔴 Mot video 40 phut la ~60.000 khung; o dang tho do la ~350 GB.

    Chot bang su VANG MAT cua moi thu vien doc pixel.
    """
    cay = ast.parse((APP / "canh.py").read_text(encoding="utf-8"))
    cam = {"cv2", "PIL", "numpy", "imageio", "av", "decord", "skimage"}
    thay = []
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            thay += [a.name.split(".")[0] for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            thay.append((n.module or "").split(".")[0])
    assert not (set(thay) & cam), f"doc pixel trong Python: {set(thay) & cam}"


def test_ffmpeg_KHONG_ghi_tep_ra_khi_do_canh():
    """`-f null -` : chay bo loc, vut dau ra. Ghi mot ban sao video ra dia chi
    de dem moc la tra ca dung luong dia cho mot phep dem."""
    van = (APP / "canh.py").read_text(encoding="utf-8")
    assert '"-f", "null"' in van and '"-an"' in van


def test_mot_lan_goi_ffmpeg_cho_CA_video():
    """⛔ Goi mot lan moi canh se la N lan mo tep + N lan giai ma tu dau."""
    cay = ast.parse((APP / "canh.py").read_text(encoding="utf-8"))
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "phan_tich"][0]
    goi_run = [n for n in ast.walk(ham)
               if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "run"]
    assert len(goi_run) == 1, f"{len(goi_run)} lan goi subprocess trong `phan_tich`"


def test_video_RAT_dai_van_ra_chi_muc_hop_le():
    """Mot gio video, 900 moc. Phep tinh phai chay trong bo nho hang so."""
    moc = [float(i) * 4.0 for i in range(1, 900)]
    khoang = c.gop_canh_ngan(moc, 3600.0)
    ci = _chi_muc(khoang, 3600.0)
    ci = c.ChiMucCanh(tuple(c.chan_so_khung(list(ci.canh))), 3600.0)
    c.kiem_chi_muc(ci)
    # ⚠️ 899 MOC chia truc thoi gian thanh 900 KHOANG. Ban dau toi viet 899 va
    #    do la mot loi so hoc cua phep kiem, khong phai cua ma — dung kieu lech
    #    mot don vi ma mot con so go tay de mac va kho thay lai.
    assert len(ci.canh) == 900
    # Va khung phai rai deu tren CA gio video, khong don ve dau.
    nua_sau = sum(len(x.khung) for x in ci.canh[450:])
    assert nua_sau > 0, "nua sau cua mot gio video khong co khung nao"


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Chan so khung va kich thuoc
# ══════════════════════════════════════════════════════════════════════════════

def test_tong_so_khung_KHONG_vuot_tran_du_bao_nhieu_canh():
    """⛔ Tran moi canh khong du: 300 canh x 2 van ra 600 khung."""
    khoang = [(float(i) * 2, float(i) * 2 + 2) for i in range(300)]
    ci = _chi_muc(khoang, 600.0)
    sau = c.chan_so_khung(list(ci.canh))
    assert sum(len(x.khung) for x in sau) <= c.KHUNG_TOI_DA


def test_ha_so_khung_DEU_TAY_chu_khong_cat_duoi():
    """🔑 Cat duoi lam nua sau video khong co khung nao, va mot ho so noi dung
    dung tren nua dau la mot ho so sai ve ca video."""
    khoang = [(float(i) * 2, float(i) * 2 + 2) for i in range(100)]
    sau = c.chan_so_khung(list(_chi_muc(khoang, 200.0).canh))

    nua_dau = sum(len(x.khung) for x in sau[:50])
    nua_sau = sum(len(x.khung) for x in sau[50:])
    assert nua_sau > 0, "nua sau video khong co khung nao"
    assert abs(nua_dau - nua_sau) <= max(2, c.KHUNG_TOI_DA // 10)


def test_khung_bi_chan_KICH_THUOC_va_giu_ti_le():
    """⚠️ Ep ca hai canh se lam meo hinh, va mot khung meo la mot khung model
    doc sai."""
    lenh = c.lenh_rut_khung("a.mp4", 3.0, "ra.jpg")
    vf = lenh[lenh.index("-vf") + 1]
    assert f"min({c.CANH_DAI_KHUNG},iw)" in vf
    assert vf.endswith(":-2"), "phai de ffmpeg tu tinh canh kia de giu ti le"


def test_tim_NHANH_truoc_khi_mo_tep():
    """⭐ `-ss` TRUOC `-i` la tim nhanh. Voi video dai do la khac biet giua vai
    giay va vai phut moi khung."""
    lenh = c.lenh_rut_khung("a.mp4", 30.0, "ra.jpg")
    assert lenh.index("-ss") < lenh.index("-i")


def test_tran_khung_hop_ly_so_voi_cua_so_THI_GIAC():
    """🔑 Trần ở đây phải có liên hệ với cửa sổ của model thị giác, không phải
    một con số tự do.

    🔴 DÒNG SO SÁNH HAI MODEL ĐÃ BỎ (12/09/2026, dual-model).

       Bản trước kết bằng `cua_so_ngu_canh(DOC_CANH) < cua_so_ngu_canh(DICH_THUAT)`.
       Nó canh một mối nguy có thật **của thời đó**: hai hồ sơ là hai bản của
       **cùng một model** (`qwen38-api` 131.072 so với `qwen38-vision` 65.536).
       Nay hai thao tác đi tới **hai model khác nhau trên hai card khác nhau**,
       thị giác (262.144) **lớn hơn** văn bản (221.184) — quan hệ đã lật và mối
       nguy cũ biến mất cùng nó.

    ⛔ Đảo dấu cho xanh lại là ghim ngược một quan hệ **ngẫu nhiên** giữa hai con
       số; nó sẽ lật lần nữa ngày ai đó đổi ngữ cảnh một model. Một phép đo lệch
       chiều thì phải bỏ. Quan hệ giữa hai model nay do
       `test_434::test_cua_so_ngu_canh_LAY_DUNG_MODEL_CUA_TUNG_THAO_TAC` canh,
       bằng một câu hỏi bất biến với việc model nào lớn hơn.
    """
    from apps.auto_scan_video import ai

    from apps.ltt_llm.ngan_sach import TOKEN_MOI_ANH

    # ⭐ Ràng buộc THẬT, và nay đo được thay vì ước: một lô `KHUNG_TOI_DA` khung
    #    hình tốn `KHUNG_TOI_DA × TOKEN_MOI_ANH` token vào, và nó phải lọt cửa
    #    sổ của **chính model thị giác** — kèm chỗ cho lời nhắc và câu trả lời.
    #    `TOKEN_MOI_ANH` = 770, đo ở cổng G4 (12/09) bằng HIỆU giữa cùng một câu
    #    hỏi có ảnh và không ảnh, chứ không ước bằng công thức patch.
    ton = c.KHUNG_TOI_DA * TOKEN_MOI_ANH
    cua = ai.cua_so_ngu_canh(ai.DOC_CANH)
    assert 0 < ton <= cua // 2, (
        f"mot lo {c.KHUNG_TOI_DA} khung ton {ton} token, cua so thi giac {cua} "
        f"— giu duoi mot nua de con cho cho loi nhac va cau tra loi")



# ══════════════════════════════════════════════════════════════════════════════
#  §4  Phu het nguon, dung thu tu
# ══════════════════════════════════════════════════════════════════════════════

def test_chi_muc_phu_HET_nguon():
    ci = _chi_muc(c.gop_canh_ngan([5.0, 12.0], 30.0), 30.0)
    c.kiem_chi_muc(ci)
    assert ci.canh[0].bat == 0.0
    assert abs(ci.canh[-1].ket - 30.0) < 1e-6


def test_canh_KHONG_chong_lan_va_dung_thu_tu():
    ci = _chi_muc(c.gop_canh_ngan([3.0, 7.0, 11.0], 20.0), 20.0)
    c.kiem_chi_muc(ci)
    for a, b in zip(ci.canh, ci.canh[1:]):
        assert a.ket == b.bat


def test_canh_NGAN_bi_gop_chu_khong_bi_BO():
    """⛔ Bo mot khoang la lam mat mot doan cua nguon, va chi muc se khong con
    phu het video."""
    moc = [0.2, 0.4, 0.6, 10.0]        # ba moc rat sat nhau o DAU
    khoang = c.gop_canh_ngan(moc, 20.0)
    assert khoang[0][0] == 0.0
    assert abs(khoang[-1][1] - 20.0) < 1e-6
    # Khong khoang nao ngan hon nguong, tru khi chi co dung mot khoang.
    if len(khoang) > 1:
        assert all((e - b) >= c.CANH_NGAN_NHAT_S - 1e-9 for b, e in khoang)


def test_canh_ngan_o_GIUA_cung_bi_gop_chu_khong_bi_BO():
    """🔴 Phep kiem tren mot minh KHONG du, va kiem dot bien chi ra dieu do.

    Voi cac moc o DAU video, phep gop-dau (`ra[1] = (ra[0][0], ra[1][1])`) vo
    tinh va lai moi khe ho — nen mot ban do BO khoang ngan thay vi GOP van di
    qua duoc. Mot canh ngan o GIUA thi khong duoc va nao ca.

    ⛔ Bo mot khoang la lam mat mot doan cua nguon: chi muc khong con phu het
       video, va moi quyet dinh bien tap phia sau tro vao sai cho.
    """
    moc = [5.0, 5.2, 10.0]             # (5.0, 5.2) ngan, nam GIUA
    khoang = c.gop_canh_ngan(moc, 20.0)

    # Lien tuc: het khoang nay la dau khoang kia, khong khe ho nao.
    for (b1, e1), (b2, e2) in zip(khoang, khoang[1:]):
        assert abs(e1 - b2) < 1e-9, f"khe ho {e1} -> {b2}"
    assert khoang[0][0] == 0.0 and abs(khoang[-1][1] - 20.0) < 1e-9

    # Va chi muc dung tu no phai qua duoc phep kiem hinh dang.
    c.kiem_chi_muc(_chi_muc(khoang, 20.0))


def test_chi_muc_HONG_bi_tu_choi():
    hong = c.ChiMucCanh((c.Canh("a", 0.0, 5.0), c.Canh("b", 7.0, 10.0)), 10.0)
    with pytest.raises(c.CanhError):
        c.kiem_chi_muc(hong)         # co khe ho 5.0 -> 7.0


def test_khung_ngoai_canh_bi_tu_choi():
    hong = c.ChiMucCanh((c.Canh("a", 0.0, 5.0, (9.0,)),), 5.0)
    with pytest.raises(c.CanhError):
        c.kiem_chi_muc(hong)


def test_chi_muc_khong_phu_het_video_bi_tu_choi():
    hong = c.ChiMucCanh((c.Canh("a", 0.0, 5.0),), 30.0)
    with pytest.raises(c.CanhError):
        c.kiem_chi_muc(hong)


def test_ma_canh_on_dinh_theo_THU_TU():
    ci = _chi_muc(c.gop_canh_ngan([4.0, 9.0], 15.0), 15.0)
    assert [x.ma for x in ci.canh] == ["canh_0001", "canh_0002", "canh_0003"]


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Dang luu tru + huy
# ══════════════════════════════════════════════════════════════════════════════

def test_dang_JSON_tat_dinh():
    ci = _chi_muc(c.gop_canh_ngan([4.0, 9.0], 15.0), 15.0)
    assert c.sang_json(ci) == c.sang_json(ci)
    import json
    d = json.loads(c.sang_json(ci))
    assert d["nguong"] == c.NGUONG_DOI_CANH
    assert len(d["canh"]) == 3


def test_phan_tich_TON_TRONG_lenh_huy(monkeypatch):
    """Bam huy roi thi khong duoc di tiep sang buoc rut khung."""
    import subprocess as sp

    from platform_core import media

    monkeypatch.setattr(media, "duration_seconds", lambda p: 30.0)
    monkeypatch.setattr(media, "ffmpeg_bin", lambda: "ffmpeg")

    class _Kq:
        stderr = FFMPEG_STDERR.encode()
        returncode = 0

    monkeypatch.setattr(sp, "run", lambda *a, **k: _Kq())
    with pytest.raises(c.CanhError):
        c.phan_tich("a.mp4", hoi_huy=lambda: True)


def test_phan_tich_chay_duoc_voi_ffmpeg_gia(monkeypatch):
    """Duong day du, khong cham nhi phan that."""
    import subprocess as sp

    from platform_core import media

    monkeypatch.setattr(media, "duration_seconds", lambda p: 30.0)
    monkeypatch.setattr(media, "ffmpeg_bin", lambda: "ffmpeg")

    class _Kq:
        stderr = FFMPEG_STDERR.encode()
        returncode = 0

    monkeypatch.setattr(sp, "run", lambda *a, **k: _Kq())
    ci = c.phan_tich("a.mp4")
    c.kiem_chi_muc(ci)
    assert ci.thoi_luong == 30.0
    assert ci.tom_tat()["so_canh"] == len(ci.canh)


def test_ffmpeg_hong_thi_NEM_chu_khong_tra_chi_muc_rong(monkeypatch):
    """⛔ Mot chi muc rong di tiep se lam pha 11 doc mot video khong co canh nao
    va ket luan "khong co gi de xem"."""
    import subprocess as sp

    from platform_core import media

    monkeypatch.setattr(media, "duration_seconds", lambda p: 30.0)
    monkeypatch.setattr(media, "ffmpeg_bin", lambda: "ffmpeg")
    monkeypatch.setattr(sp, "run", lambda *a, **k: (_ for _ in ()).throw(
        OSError("khong tim thay ffmpeg")))
    with pytest.raises(c.CanhError):
        c.phan_tich("a.mp4")


def test_thoi_luong_khong_doc_duoc_thi_NEM(monkeypatch):
    from platform_core import media

    monkeypatch.setattr(media, "duration_seconds", lambda p: 0.0)
    with pytest.raises(c.CanhError):
        c.phan_tich("a.mp4")


# ══════════════════════════════════════════════════════════════════════════════
#  §6  Chua goi model nao, chua cat gi
# ══════════════════════════════════════════════════════════════════════════════

def test_pha_10_KHONG_goi_VLM_va_KHONG_cat_gi():
    """Pham vi pha nay: tien xu ly thi giac TAT DINH. Khong AI, khong bien tap."""
    cay = ast.parse((APP / "canh.py").read_text(encoding="utf-8"))
    goi = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            f = n.func
            goi.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    for cam in ("goi", "doc_json", "model_cho", "cat", "reframe"):
        assert cam not in goi, f"canh.py goi {cam!r} — ngoai pham vi pha 10"
