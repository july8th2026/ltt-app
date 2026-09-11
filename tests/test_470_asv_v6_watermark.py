"""ASV V6 pha 13 — nhan dien watermark/logo tinh.

🔑 **Chan ly nen la thu ta TU CAY VAO.** Moi khung hinh o day do `numpy` sinh,
   nen bai kiem biet chinh xac dau nam o dau — khac han mot bo anh mau, noi ta
   chi biet *"co ai do da gan nhan"*.

⭐ Va khong bai nao cham ffmpeg. `do_tu_khung` nhan mot mang, nen ca tep chay
   trong vai tram mili giay va **khong co duong nao doc mot ban ghi cu** —
   `chay-rieng-tren-may-ranh-chi-la-bac-mot` ghi lai mot phep do 1,65 giay hoa
   ra chi la mot lan doc tep.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import sys
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
from tools import do_watermark as wm

N, CAO, RONG = 12, 270, 480


def _canh_dong(seed: int = 7) -> np.ndarray:
    """Canh doi lien tuc: nhieu ngau nhien moi khung."""
    r = np.random.default_rng(seed)
    return r.integers(0, 255, size=(N, CAO, RONG), dtype=np.uint8)


def _cay_dau(a: np.ndarray, y0: int, y1: int, x0: int, x1: int,
             seed: int = 99) -> tuple[float, float, float, float]:
    """Cay mot dau TINH co CHI TIET. Tra ve hop chuan hoa lam chan ly nen."""
    r = np.random.default_rng(seed)
    a[:, y0:y1, x0:x1] = r.integers(0, 255, size=(y1 - y0, x1 - x0),
                                    dtype=np.uint8)
    return (x0 / RONG, y0 / CAO, x1 / RONG, y1 / CAO)


def _chong(a, b) -> float:
    """Ti le dien tich giao / hop. 1.0 la trung khit."""
    gx = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    gy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    giao = gx * gy
    hop = ((a[2] - a[0]) * (a[3] - a[1])
           + (b[2] - b[0]) * (b[3] - b[1]) - giao)
    return giao / hop if hop > 0 else 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Tim dung dau, va KHONG tim ra dau khong co
# ══════════════════════════════════════════════════════════════════════════════

def test_tim_dung_MOT_dau_dung_cho():
    a = _canh_dong()
    that = _cay_dau(a, 15, 55, 380, 460)
    kq = wm.do_tu_khung(a)
    assert kq.do_duoc and len(kq.ds) == 1, (
        f"mong doi dung 1 dau, nhan {len(kq.ds)}")
    d = kq.ds[0]
    assert _chong((d.x0, d.y0, d.x1, d.y1), that) > 0.4, (
        f"hop tim duoc {(d.x0, d.y0, d.x1, d.y1)} lech qua xa {that}")


def test_canh_dong_KHONG_dau_thi_khong_bia_ra_dau():
    """⛔ Nua AM, va no la nua de mat nhat. Mot bo do luon tra ve mot cai gi do
    thi vo dung — nhung no **trong nhu dang lam viec**."""
    kq = wm.do_tu_khung(_canh_dong(11))
    assert kq.do_duoc
    assert kq.ds == (), f"bia ra {len(kq.ds)} dau tren mot canh khong co dau nao"


def test_tim_duoc_HAI_dau_rieng_biet():
    a = _canh_dong(9)
    t1 = _cay_dau(a, 200, 250, 20, 120, seed=1)
    t2 = _cay_dau(a, 15, 50, 380, 450, seed=2)
    kq = wm.do_tu_khung(a)
    assert len(kq.ds) == 2, f"mong doi 2 dau, nhan {len(kq.ds)}"
    hop = [(d.x0, d.y0, d.x1, d.y1) for d in kq.ds]
    for that in (t1, t2):
        assert max(_chong(h, that) for h in hop) > 0.4, f"khong khop {that}"


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Hai rao, va chung phai TU CHOI chu khong doan bua
# ══════════════════════════════════════════════════════════════════════════════

def test_canh_VON_DI_TINH_thi_TU_CHOI_ket_luan():
    """🔴 Mot anh tinh lap lai: **moi** o deu dung im, nen mot bo do khong co rao
    se bao ca khung hinh la watermark.

    ⭐ Mot bo do biet noi *"toi khong do duoc"* la mot bo do dung duoc; mot bo do
       luon tra loi thi khong.
    """
    r = np.random.default_rng(7)
    t = np.repeat(r.integers(0, 255, size=(1, CAO, RONG), dtype=np.uint8),
                  N, axis=0)
    kq = wm.do_tu_khung(t)
    assert kq.do_duoc is False
    assert kq.ly_do == wm.LY_DO_CANH_TINH
    assert kq.ds == ()
    assert kq.ti_le_o_tinh > wm.TRAN_TI_LE_TINH


def test_canh_TOI_bi_tu_choi_voi_ly_do_KHAC_canh_tinh():
    """⛔ Hai the gioi khac han cung cho `ti_le_o_tinh = 1,0`, va gop chung vao
    mot nhan la bao khach *"video cua ban la anh tinh"* trong khi su that la
    *"video cua ban qua toi de bo do nay noi duoc gi"*.

    Cau thu nhat SAI. Cau thu hai con goi y duoc mot viec lam duoc.
    """
    r = np.random.default_rng(5)
    toi = (r.integers(0, 255, size=(N, CAO, RONG)) * 0.06).astype(np.uint8)
    kq = wm.do_tu_khung(toi)
    assert kq.do_duoc is False
    assert kq.ly_do == wm.LY_DO_TUONG_PHAN_THAP, (
        f"ly do {kq.ly_do!r} — hai chan doan nay phai phan biet duoc")


def test_LETTERBOX_khong_duoc_coi_la_dau():
    """Hai thanh den tuyet doi dung im — nhung chung **khong co chi tiet**.
    Truc khong gian phan biet duoc, va no phai duoc hoi RIENG."""
    a = _canh_dong(3)
    a[:, :40, :] = 0
    a[:, -40:, :] = 0
    kq = wm.do_tu_khung(a)
    assert kq.do_duoc
    assert kq.ds == (), f"nham {len(kq.ds)} thanh vien den thanh dau"


def test_thieu_khung_thi_noi_THIEU_KHUNG():
    for a in (np.zeros((0, 0, 0), dtype=np.uint8),
              np.zeros((2, CAO, RONG), dtype=np.uint8)):
        kq = wm.do_tu_khung(a)
        assert kq.do_duoc is False
        assert kq.ly_do == wm.LY_DO_THIEU_KHUNG


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Ket qua phai TU GIAI THICH
# ══════════════════════════════════════════════════════════════════════════════

def test_ds_rong_KHONG_mo_ho_giua_hai_nghia():
    """⛔ *\"Da do, khong co dau nao\"* va *\"khong do duoc\"* la hai the gioi
    khac nhau. Gop ca hai vao mot danh sach rong la dung cai loi ma
    `khong-doi-chung-thi-so-khong-khong-phai-phat-hien` mo ta: mot so 0 trong
    giong het mot phat hien."""
    khong_co = wm.do_tu_khung(_canh_dong(11))
    khong_do = wm.do_tu_khung(np.zeros((0, 0, 0), dtype=np.uint8))
    assert khong_co.ds == khong_do.ds == ()
    assert khong_co.do_duoc is True and khong_co.ly_do == ""
    assert khong_do.do_duoc is False and khong_do.ly_do


def test_dau_doi_sang_VUNG_CHE_duoc_ngay():
    """⭐ Cung he toa do voi `vung_che` — co chu dinh. Mot dau tim duoc phai dan
    thang vao duoc o "vung che" khach da co, khong phai mot he toa do thu hai."""
    a = _canh_dong()
    _cay_dau(a, 15, 55, 380, 460)
    d = wm.do_tu_khung(a).ds[0]
    v = d.sang_vung()
    assert set(v) == {"loai", "x0", "y0", "x1", "y1"}
    assert all(0.0 <= v[k] <= 1.0 for k in ("x0", "y0", "x1", "y1"))
    assert v["x0"] < v["x1"] and v["y0"] < v["y1"]

    from apps.auto_scan_video import vung_che
    vung_che.chuan_hoa_mot(v)      # nem neu khong hop le


def test_bao_cao_json_on_dinh_va_tu_khai_schema():
    a = _canh_dong()
    _cay_dau(a, 15, 55, 380, 460)
    kq = wm.do_tu_khung(a)
    d = kq.sang_dict()
    assert d["schema"] == wm.SCHEMA and d["phien_ban"] == wm.PHIEN_BAN_DO
    assert wm.bao_cao_json(kq) == wm.bao_cao_json(kq)


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Lenh ffmpeg — kiem duoc ma khong chay ffmpeg
# ══════════════════════════════════════════════════════════════════════════════

def test_ss_phai_dung_TRUOC_i():
    """🔑 `-ss` **trước** `-i` là tìm-đến-ĐẦU-VÀO: ffmpeg nhảy tới khung khoá gần
    mốc rồi giải mã một khung. Chi phí là một hằng số — một lần nhảy cộng một
    GOP — **không phụ thuộc thời lượng video**.

    ⛔ Đặt `-ss` SAU `-i` biến nó thành tìm-đến-ĐẦU-RA: ffmpeg giải mã từ đầu tệp
       rồi vứt bỏ, tức chi phí tỉ lệ với mốc. Cùng một cờ, hai bên của `-i`, hai
       hạng độ phức tạp — và không có lỗi nào báo ra, chỉ là chậm dần theo mốc.
    """
    lenh = wm._lenh_mot_khung("v.mp4", giay=900.0, rong=480, ffmpeg="ffmpeg")
    assert "-ss" in lenh and "-i" in lenh
    assert lenh.index("-ss") < lenh.index("-i"), (
        "`-ss` nam sau `-i` — chi phi se ti le voi moc thay vi la hang so")
    assert lenh[lenh.index("-frames:v") + 1] == "1"


def test_moc_lay_mau_TRAI_DEU_chu_khong_dua_ve_dau_video():
    """🔴 Khiếm khuyết đã sửa, và nó **im lặng** trước khi sửa.

    Bản đầu dùng `-skip_frame nokey ... -frames:v 12`, mà `-frames:v` làm ffmpeg
    **dừng ngay khi đủ 12 khung ra**. Với `g=60` ở 30fps đó là 12 khung khoá đầu
    tiên — tức toàn bộ mẫu đến từ **~24 giây đầu**.

    Hai hệ quả, cả hai đều không báo lỗi:
      · một watermark xuất hiện từ phút thứ 5 **không bao giờ được nhìn thấy**;
      · một video mở đầu bằng thẻ tiêu đề tĩnh làm rào ① bắn, và bộ dò trả
        `canh_tinh` cho một video thật ra rất động.

    ⚠️ Và nó **trông như đang chạy đúng**: 12 khung, 0,171 giây, kết quả hợp lý.
       Đúng hình dạng `pham-vi-phep-do-hep-hon-loi-tuyen-bo`.
    """
    moc = wm._moc_lay_mau(600.0, 12)
    assert len(moc) == 12
    assert moc == sorted(moc)
    # Mẫu cuối phải nằm ở nửa sau của video — nếu tất cả dồn về đầu thì hỏng.
    assert moc[-1] > 300.0, f"mau cuoi o {moc[-1]:.1f}s — van dồn ve dau video"
    # ⭐ Cat hai lat CUNG do dai roi moi `zip(..., strict=True)`. Cach nay
    #    tot hon `zip(moc, moc[1:])`: no khong chi lam `ruff B905` im, no lam
    #    menh de *"hai ve cung do dai"* thanh mot dieu DUNG thay vi mot dieu ta
    #    hua. `test_467` cam zip mu chinh vi mot lech do dai bat ngo lam hai
    #    mang so le nhau ma khong ai bao loi.
    truoc, sau = moc[:-1], moc[1:]
    khoang = [b - a for a, b in zip(truoc, sau, strict=True)]
    assert max(khoang) - min(khoang) < 1e-6, f"khong deu: {khoang[:3]}"


def test_moc_lay_mau_TRANH_hai_dau_mut():
    """⚠️ Tránh mút vì hai lý do cụ thể: khung đầu thường là một thẻ tiêu đề
    tĩnh, khung cuối thường là một màn hình đen. Cả hai đều làm rào ① bắn nhầm —
    tức bộ dò trả `canh_tinh` cho một video hoàn toàn bình thường."""
    moc = wm._moc_lay_mau(100.0, 10)
    assert moc[0] > 0.0, "mau dau tien o dung 0s — hay dinh the tieu de tinh"
    assert moc[-1] < 100.0, "mau cuoi o dung cuoi tep — hay dinh man hinh den"


def test_thoi_luong_khong_biet_thi_van_lay_duoc_mot_mau():
    """`thoi_luong=0` xảy ra thật khi `soi` không đọc được độ dài. Bộ dò phải
    trả về **một** mốc dùng được chứ không phải một danh sách rỗng — rỗng nghĩa
    là không khung nào được lấy, và bộ dò sẽ báo `thieu_khung` thay vì báo
    thứ nó thật sự gặp."""
    assert wm._moc_lay_mau(0.0, 12) == [0.0]
    assert wm._moc_lay_mau(-5.0, 12) == [0.0]


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Cong tai nguyen cho viec XOA
# ══════════════════════════════════════════════════════════════════════════════

def test_cong_xoa_TU_CHOI_khi_chua_co_so_do():
    """⛔ Khong co phep do thi cong phai dong. Mo mot tinh nang dua tren mot uoc
    luong muon o dau do la dung cai ma `doi-chieu-cong-dong-truoc-moi-pha` cam:
    muon nguong thi phai do lai."""
    c = wm.cong_xoa(giay_moi_khung=0.0, so_khung_video=1000)
    assert c.mo is False and c.ly_do == "chua_do"


@pytest.mark.parametrize("giay_moi_khung,so_khung,mong_mo", [
    (0.0001, 54_000, True),    # 5,4 s cho 30 phut o 30fps — thoai mai
    (0.02, 54_000, False),     # 1.080 s — gap doi phan ngan sach cho phep
])
def test_cong_xoa_phan_quyet_theo_SO_chu_khong_theo_y_kien(
        giay_moi_khung, so_khung, mong_mo):
    c = wm.cong_xoa(giay_moi_khung=giay_moi_khung, so_khung_video=so_khung)
    assert c.mo is mong_mo
    assert c.giay_uoc == pytest.approx(giay_moi_khung * so_khung)
    assert c.tran_giay == pytest.approx(
        wm.TRAN_JOB_GIAY * wm.PHAN_NGAN_SACH_TOI_DA)


def test_cong_xoa_KHONG_duoc_an_het_ngan_sach_job():
    """⛔ Xoa watermark la mot buoc PHU. Mot buoc phu an het ngan sach cua buoc
    chinh thi lan chay hong, va no hong o giai doan SAU — tuc sau khi khach da
    cho xong phan dat tien nhat."""
    assert 0.0 < wm.PHAN_NGAN_SACH_TOI_DA < 0.5, (
        "phan ngan sach cho mot buoc phu khong duoc chiem qua nua job")
def test_bien_cua_ngan_sach_la_mot_QUYET_DINH_chu_khong_phai_tai_nan():
    """Dung o dung tran thi MO — "toi da 15%" bao gom ca 15%.

    🔴 Bai nay ton tai vi mot TAI NAN. Ban dau toi chon `0,01 x 54.000 = 540 s`
       lam ca "vuot tran" — ma tran la `3.600 x 0,15 = **dung** 540 s`. Bai kiem
       do, va cai do lo ra rang **nghia cua bien chua he duoc ai quyet**:
       no dang la bat cu thu gi ma toan tu `<=` tinh co viet ra.

    ⭐ Nen thay vi sua con so cho khoi cham bien, ta CHOT bien. Mot nguong khong
       co bai kiem o dung diem bien la mot nguong se bi doi am tham, va khong ai
       biet no da o phia nao.
    """
    tran = wm.TRAN_JOB_GIAY * wm.PHAN_NGAN_SACH_TOI_DA
    dung_tran = wm.cong_xoa(giay_moi_khung=tran / 1000.0, so_khung_video=1000)
    assert dung_tran.giay_uoc == pytest.approx(tran)
    assert dung_tran.mo is True, "dung o tran phai duoc MO"

    tren_tran = wm.cong_xoa(giay_moi_khung=(tran + 1.0) / 1000.0,
                            so_khung_video=1000)
    assert tren_tran.mo is False and tren_tran.ly_do == "vuot_ngan_sach"
# ══════════════════════════════════════════════════════════════════════════════
#  §6  PHAM VI — bo do nay bat duoc gi, va KHONG bat duoc gi
# ══════════════════════════════════════════════════════════════════════════════

def test_duong_phan_quyet_CHI_dung_truc_mot():
    """⛔ Truc 2 (do doc anh trung binh) da duoc dung, do, va **go bo**. Bai nay
    ton tai de mot ban "cai tien" khong lang le mang no tro lai.

    Do duoc khi truc 2 con trong duong phan quyet, watermark `white@0.55`:

        mandelbrot       2 dau — mot hop **125 o** phu gan het khung
        life             2 dau — dung cho nhung vo manh
        smptebars+xoay   **17 dau**

    🔴 Mot bo do de nghi 17 vung che sai con TE HON mot bo do khong tim thay gi.
       Vung che la nang luc **doi diem anh**: mot de nghi sai khong phien ha, no
       **pha hinh** cua khach vinh vien trong tep ra.

    ⭐ Da thu loc bang truc thu BA (`doc(mean)/mean(doc)` — *"bien o cho nay co
       dung yen khong"*) va no **khong tach duoc**: trong hop 0,763-0,987 so voi
       trung vi khung 0,620-0,946, va p90 cua khung da la 0,825-1,000.

    ⇒ Ai muon mo lai truc 2 thi phai xoa bai nay — va de xoa duoc thi phai doc
      ba con so tren. Do la toan bo muc dich cua no.
    """
    import inspect

    than = inspect.getsource(wm.do_tu_khung)
    # Bo chu thich: mot dong GIAI THICH khong phai mot dong THI HANH.
    ma = "\n".join(d for d in than.splitlines()
                   if not d.lstrip().startswith("#"))
    assert "TI_LE_DOC_TOI_THIEU" not in ma, (
        "truc 2 da tro lai duong phan quyet — doc so do o docstring cua hang so "
        "do truoc khi giu no")
    assert "tot = tinh & (chi_tiet >= NGUONG_CHI_TIET)" in ma


def test_hang_so_cua_truc_2_van_CON_va_van_mang_so_do():
    """Nua doi chung. Xoa sach hang so + so do se lam bai tren xanh, va nguoi doc
    sau se co cung y tuong ay — no la y tuong tu nhien nhat — roi di lai dung ba
    vong do nay.

    ⭐ `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`: mot ket qua AM co gia
       tri dung bang mot ket qua duong, mien la no kem phep do.
    """
    assert hasattr(wm, "TI_LE_DOC_TOI_THIEU")
    tai_lieu = (Path(wm.__file__).read_bytes().decode("utf-8"))
    for so in ("125 o", "17 dau", "0,763-0,987"):
        assert so in tai_lieu, f"mat so do {so!r} — ket qua am khong con bang chung"


def test_dau_BAN_TRONG_SUOT_tren_nen_dong_la_gioi_han_DA_BIET():
    """Chot gioi han bang mot phep do tai cho, khong bang mot cau van.

    Cay mot lop phu `0,55*trang + 0,45*nen` len mot canh dong. Truc 1 **khong**
    bat duoc no, va do la hanh vi DA BIET — khong phai mot loi chua ai thay.

    ⛔ Bai nay se DO neu ai do lam bo do bat duoc ca dau ban trong suot ma quen
       cap nhat tai lieu pham vi. Do la mot cai do DUNG: pham vi rong ra thi
       `PHA13_*.md` va `hop_dong_v4` phai biet.
    """
    a = _canh_dong(21).astype(np.float32)
    a[:, 15:55, 380:460] = 0.55 * 255.0 + 0.45 * a[:, 15:55, 380:460]
    kq = wm.do_tu_khung(a.astype(np.uint8))
    assert kq.do_duoc, "canh nay du dong de do duoc"
    that = (380 / RONG, 15 / CAO, 460 / RONG, 55 / CAO)
    trung = [d for d in kq.ds
             if _chong((d.x0, d.y0, d.x1, d.y1), that) > 0.2]
    assert not trung, (
        "bo do nay GIO bat duoc dau ban trong suot — mot tin tot, nhung pham vi "
        "da doi: cap nhat PHA13_NHAN_DIEN_WATERMARK.md va bo hang so "
        "TI_LE_DOC_TOI_THIEU khoi trang thai 'da go'")
