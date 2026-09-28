"""B10-4 — tầng OCR là tầng CHÍNH, và ba trạng thái ⛔ không được gộp.

🔴 **Ca thật (28/09).** Chủ dự án nhìn bản giao và hỏi: *"nó nhận diện text
   trong ảnh hay mặc định khu vực che? nó che đoạn timeline có text thôi hay
   che full timeline? có vẻ nó che 2 dòng từ đầu đến cuối, trong khi có cảnh
   text 1 dòng."* Cả ba đều đúng.

   `do_dai_chu` ⛔ không đọc chữ — nó tính `mean(axis=0) × std(axis=0)` theo
   hàng, tức **suy từ biến thiên điểm ảnh**, và hồ sơ ấy là **hợp trên thời
   gian**: hàng nào có chữ ở *một số* khung đều góp điểm.

**Đo trên phim nghiệm thu** (`1024×576`, 275 s), qua chính `_dai_chu_nhieu_tang`:

    tầng lùi   y 0,8264..0,9809  cao 15,5 %  ·  x 0..1      rộng 100 %
    tầng OCR   y 0,8707..0,9782  cao 10,7 %  ·  x 0,09..0,90  rộng 80,8 %
    ⇒ diện tích che NHỎ HƠN 1,78 lần

⭐ **Phép kiểm ở đây ⛔ không gọi OCR.** Chúng nạp thẳng hộp giả vào các hàm
   thuần (`_gom_cum`, `_chon_cum`, `_bao`) và vào chỗ rẽ nhánh ba trạng thái.
   Gọi OCR thật sẽ biến một bài kiểm **tất định** thành một bài phụ thuộc mô
   hình, máy, và 9 giây — và nó sẽ đo **chất lượng mô hình** thay vì **luật
   của ta**.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import do_vung, do_vung_ocr as ocr


def _h(giay: float, y0: float, y1: float, x0: float, x1: float) -> ocr.Hop:
    return ocr.Hop(giay, y0, y1, x0, x1)


# ── Gom cụm: hai dòng phụ đề ⛔ KHÔNG được gộp làm một ───────────────────────

def test_hai_DONG_phu_de_ra_HAI_cum_chu_khong_phai_mot():
    """🔑 Đây là gốc của *"che 2 dòng dù cảnh chỉ 1 dòng"*.

    Gộp mọi hộp làm một dải là đúng cách bộ dò cũ cho ra 15,5 %.
    """
    hop = [_h(t, 0.88, 0.92, 0.2, 0.8) for t in (1, 2, 3)] + \
          [_h(t, 0.93, 0.97, 0.2, 0.8) for t in (1, 2, 3)]
    assert len(ocr._gom_cum(hop)) == 2


def test_gom_theo_TAM_chu_khong_theo_MEP():
    """⛔ Hai dòng kề nhau có mép **chạm nhau** nhưng tâm cách một chiều cao dòng.

    Gom theo mép sẽ dính chúng lại; gom theo tâm thì ⛔ không.
    """
    hop = [_h(t, 0.880, 0.920, 0.2, 0.8) for t in (1, 2)] + \
          [_h(t, 0.920, 0.960, 0.2, 0.8) for t in (1, 2)]
    assert len(ocr._gom_cum(hop)) == 2


# ── Chọn cụm: hai điều kiện bắt HAI thứ khác nhau ───────────────────────────

def test_cum_HEP_bi_loai_du_xuat_hien_MOI_khung():
    """⚠️ Watermark tĩnh có mặt ở **mọi** khung — điều kiện *"nhiều khung"* một
    mình ⛔ không loại được nó. Điều kiện *"đủ rộng"* mới loại.

    ⭐ Thiếu bài này thì ai đó bỏ một trong hai điều kiện và bộ kiểm vẫn xanh.
    """
    hep = [_h(t, 0.90, 0.94, 0.86, 0.96) for t in range(10)]
    assert ocr._chon_cum(ocr._gom_cum(hep), 10) == []


def test_cum_HIEM_bi_loai_du_RONG():
    """Một dòng chữ xuất hiện đúng một lần là tấm biển trong cảnh, ⛔ không
    phải phụ đề."""
    hiem = [_h(1.0, 0.90, 0.94, 0.1, 0.9)]
    assert ocr._chon_cum(ocr._gom_cum(hiem), 20) == []


def test_cum_RONG_va_LAP_thi_duoc_chon():
    """⭐ Vế đối chứng. ⛔ Không có nó thì `return []` cũng qua hai bài trên."""
    tot = [_h(t, 0.90, 0.94, 0.1, 0.9) for t in range(10)]
    assert len(ocr._chon_cum(ocr._gom_cum(tot), 10)) == 1


# ── BB-7: cổng an toàn ───────────────────────────────────────────────────────

def test_BB7_dai_QUA_CAO_thi_KHONG_che():
    """Dải > 22 % chiều cao ⛔ **không** phải phụ đề — đó là giao diện hay một
    cảnh nhiều chữ. Che nó là **làm hỏng video của khách**.

    ⭐ *"Đo sai nguy hơn ⛔ không đo"* — chính docstring `de_xuat` của ta.
    """
    assert ocr.CAO_TOI_DA == 0.22
    cao = ocr._bao([_h(1, 0.60, 0.98, 0.1, 0.9)])
    assert (cao["y1"] - cao["y0"]) > ocr.CAO_TOI_DA


# ── BB-4: ba trạng thái, ba hành động ────────────────────────────────────────

def test_BB4_loi_KY_THUAT_thi_LUI_TANG(monkeypatch):
    """🔴 Gộp *"chưa quét được"* với *"quét rồi ⛔ không thấy"* là lỗi kho tham
    chiếu ghi 31/07: nuốt một lỗi kỹ thuật thành *"video ⛔ không có sub cứng"*
    ⇒ ⛔ không che ⇒ **lộ chữ Hán**.
    """
    goi = []
    monkeypatch.setattr(ocr, "co_san", lambda: True)
    monkeypatch.setattr(ocr, "do_dai_chu_ocr", lambda *a, **k: (_ for _ in ()).throw(
        ocr.OcrLoiKyThuat("chua cai")))
    monkeypatch.setattr(do_vung, "do_dai_chu",
                        lambda *a, **k: goi.append(1) or do_vung.KetQua((), 7))
    assert do_vung._dai_chu_nhieu_tang("x.mp4").so_khung == 7
    assert goi == [1], "loi KY THUAT phai LUI ve tang cu"


def test_BB4_quet_that_KHONG_THAY_thi_DUNG_LAI(monkeypatch):
    """⭐ Vế ngược, và nó là vế dễ mất nhất.

    *"Đã quét, ⛔ không thấy chữ"* phải được **TIN** — lùi tầng ở đây nghĩa là
    để bộ dò yếu hơn đoán bừa lên một video ⛔ không có phụ đề cứng, đúng ca
    kho tham chiếu ghi: *"video Whisper ⛔ không hardsub vẫn bị che to"*.
    """
    goi = []
    monkeypatch.setattr(ocr, "co_san", lambda: True)
    monkeypatch.setattr(ocr, "do_dai_chu_ocr",
                        lambda *a, **k: do_vung.KetQua((), 24))
    monkeypatch.setattr(do_vung, "do_dai_chu",
                        lambda *a, **k: goi.append(1) or do_vung.KetQua((), 7))
    kq = do_vung._dai_chu_nhieu_tang("x.mp4")
    assert kq.vung == () and kq.so_khung == 24
    assert goi == [], "'da quet, ⛔ khong thay' ⛔ KHONG duoc lui tang"


def test_BB4_CHUA_CAI_thi_lui_tang_chu_khong_ket_luan(monkeypatch):
    """⛔ Chưa cài = **CHƯA QUÉT**, cùng lý lẽ với `OcrLoiKyThuat`."""
    goi = []
    monkeypatch.setattr(ocr, "co_san", lambda: False)
    monkeypatch.setattr(do_vung, "do_dai_chu",
                        lambda *a, **k: goi.append(1) or do_vung.KetQua((), 7))
    assert do_vung._dai_chu_nhieu_tang("x.mp4").so_khung == 7
    assert goi == [1]


def test_chi_bat_DUNG_loai_ngoai_le(monkeypatch):
    """⛔ `except OcrLoiKyThuat`, ⛔ không bắt rộng hơn.

    Một `MemoryError` hay một lỗi lập trình ⛔ không được biến thành *"lùi
    tầng"* — đó là nuốt lỗi, và nó làm một hồi quy thật trông như một lượt dò
    bình thường.
    """
    monkeypatch.setattr(ocr, "co_san", lambda: True)
    monkeypatch.setattr(ocr, "do_dai_chu_ocr", lambda *a, **k: (_ for _ in ()).throw(
        ValueError("loi lap trinh")))
    with pytest.raises(ValueError):
        do_vung._dai_chu_nhieu_tang("x.mp4")


# ── Hình dạng trả về của RapidOCR ────────────────────────────────────────────

def test_doc_dung_hinh_dang_hop_du_dat_use_rec_False():
    """⚠️ Đo được: `use_rec=False` **VẪN** trả `[hộp4điểm, văn_bản, điểm]` —
    tên bài giữ nguyên (B10-4), nhưng B13 D1 (28/09) đã đổi `_hop_cua_khung`
    sang gọi `use_rec=True` thật; bài này chỉ chốt HÌNH DẠNG phần tử trả về
    (hộp + văn bản), không phụ thuộc `use_rec` truyền vào — `_May` giả ở đây
    nuốt mọi đối số.

    Bản đầu của tôi lặp thẳng trên kết quả và nó ném *"float() argument must
    be a string or a real number, not 'list'"*.

    ⭐ Một cờ ⛔ không phải một lời hứa về **hình dạng** trả về.
    """
    class _May:
        def __call__(self, *a, **k):
            return ([[[[10.0, 20.0], [90.0, 20.0], [90.0, 40.0], [10.0, 40.0]],
                      "chu tieng Trung", "0.9"]], None)

    hop = ocr._hop_cua_khung(_May(), object(), 100, 100, 1.0)
    assert len(hop) == 1
    assert hop[0].y0 == pytest.approx(0.2) and hop[0].y1 == pytest.approx(0.4)
    assert hop[0].x0 == pytest.approx(0.1) and hop[0].x1 == pytest.approx(0.9)
    # "chu tieng Trung" khong co ky tu Han nao (no la chu La Tinh khong dau,
    # chi la NHAN placeholder trong test) -> chuan hoa ra RONG. Dung hanh vi:
    # _chuan_hoa_van_ban chi giu 一-鿿 + so.
    assert hop[0].van_ban == ""


def test_gọi_may_that_voi_use_rec_True():
    """🔴 B13 D1 — `_hop_cua_khung` phải gọi `use_rec=True` THẬT, ⛔ không chỉ
    đọc được hình dạng khi giả lập trả `use_rec=False`. Đây là phép kiểm
    CHÍNH của D1: chốt ĐÚNG đối số được truyền, không phải hình dạng kết quả."""
    goi: dict = {}

    class _May:
        def __call__(self, *a, **k):
            goi.update(k)
            return ([], None)

    ocr._hop_cua_khung(_May(), object(), 100, 100, 1.0)
    assert goi.get("use_rec") is True, (
        "D1 doi use_rec sang True that — chu du an da dao lenh 28/09")
    assert goi.get("use_det") is True and goi.get("use_cls") is False


def test_van_ban_HAN_duoc_chuan_hoa_giu_lai():
    """Vế đối chứng cho bài trên: chữ Hán THẬT phải sống sót qua chuẩn hoá,
    ⛔ không như chuỗi La Tinh ở bài trước."""
    class _May:
        def __call__(self, *a, **k):
            return ([[[[10.0, 20.0], [90.0, 20.0], [90.0, 40.0], [10.0, 40.0]],
                      "你好，世界！123", "0.9"]], None)

    hop = ocr._hop_cua_khung(_May(), object(), 100, 100, 1.0)
    assert hop[0].van_ban == "你好世界123", (
        "chuan hoa phai giu HAN + so, bo dau cau/khoang trang")


def test_mot_khung_HONG_tra_None_chu_KHONG_tra_rong():
    """⛔ Ném ở một khung lỗi sẽ biến một sự cố nhỏ thành một quyết định kiến
    trúc (*"chưa quét được"* ⇒ lùi tầng).

    🔴 **Nhưng `None` chứ ⛔ KHÔNG phải `[]`** (sửa 28/09). `[]` nghĩa là *chạy
       được, ⛔ không thấy hộp nào*; `None` nghĩa là *máy OCR ném*. Bản đầu trả
       `[]` cho cả hai và đó là một lỗ thật — xem bài dưới.
    """
    class _May:
        def __call__(self, *a, **k):
            raise RuntimeError("khung hong")

    assert ocr._hop_cua_khung(_May(), object(), 100, 100, 1.0) is None


def test_khung_SACH_tra_RONG_chu_khong_None():
    """⭐ Vế đối chứng: ⛔ không có nó thì `return None` vô điều kiện cũng qua."""
    class _May:
        def __call__(self, *a, **k):
            return ([], None)

    assert ocr._hop_cua_khung(_May(), object(), 100, 100, 1.0) == []


def test_MOI_khung_hong_thi_NEM_chu_khong_bao_KHONG_CO_CHU(monkeypatch):
    """🔴 **Lỗ thật, do bánh cóc tìm ra chứ ⛔ không phải bộ test này.**

    Bản đầu: máy OCR ném ở **mọi** khung ⇒ mọi lượt trả `[]` ⇒ `doc_duoc` vẫn
    đếm đủ 24 (khung **đọc** được) ⇒ hàm trả *"đã quét, ⛔ không thấy chữ"* ⇒
    người gọi **TIN** ⇒ **⛔ không che** ⇒ **lộ chữ Hán**.

    ⇒ Đúng cái gộp mà docstring đầu `do_vung_ocr` **cấm**, do chính tệp ấy
      phạm. Và nó gộp **về phía IM LẶNG** — phía đắt hơn hàng bậc.

    ⚠️ Bài `test_mot_khung_HONG_*` ở trên chốt đúng hành vi **một** khung và
       **⛔ không bao giờ hỏi** *"nếu MỌI khung hỏng thì sao"*. Một bài kiểm
       đúng ở cấp phần tử ⛔ không nói gì về cấp tập hợp.
    """
    class _CapGia:
        def set(self, *a):
            return True

        def read(self):
            return True, object()

        def release(self):
            pass

    class _Cv2Gia:
        CAP_PROP_POS_MSEC = 0

    monkeypatch.setattr(ocr, "_may", _MayNem)
    monkeypatch.setattr(do_vung, "_cv2", lambda: (_Cv2Gia(), object()))
    monkeypatch.setattr(do_vung, "_mo", lambda *a: (_CapGia(), 100, 100, 99, 10.0))
    with pytest.raises(ocr.OcrLoiKyThuat):
        ocr.do_dai_chu_ocr("x.mp4", so_khung=5)


def _MayNem():
    """Máy OCR ném ở MỌI khung."""
    class _M:
        def __call__(self, *a, **k):
            raise RuntimeError("engine chet")
    return _M()


# ── B10-3: che ĐỘNG theo từng đoạn ──────────────────────────────────────────

def _chuoi(cac: list[tuple[float, float, float]]) -> list[ocr.Hop]:
    """`(giây, y0, y1)` → hộp, bề ngang cố định cho gọn."""
    return [_h(t, y0, y1, 0.2, 0.8) for t, y0, y1 in cac]


def test_BB2_doan_KHONG_co_chu_thi_KHONG_co_o_mo_nao():
    """🔴 Câu của chủ dự án: *"nó che đoạn timeline có text thôi hay che full
    timeline?"* Trước B10-3 câu trả lời là **full**.

    Chữ ở `0–10 s` rồi `40–50 s`; khoảng `10–40 s` phải **⛔ không** bị che.
    """
    hop = _chuoi([(t, 0.90, 0.94) for t in (0, 5, 10)]
                 + [(t, 0.90, 0.94) for t in (40, 45, 50)])
    ra = ocr._theo_doan(hop, dai=60.0, nhip=5.0)
    assert len(ra) == 2, [(_["tu_giay"], _["den_giay"]) for _ in ra]
    # Đoạn 1 kết thúc TRƯỚC khi đoạn 2 bắt đầu ⇒ có một quãng trống thật.
    assert ra[0]["den_giay"] < ra[1]["tu_giay"]


def test_BB1_hai_doan_KHAC_chieu_cao_thi_ra_HAI_hop_khac_nhau():
    """🔴 Câu của chủ dự án: *"trên video mẫu nó che 2 dòng từ đầu đến cuối,
    trong khi có cảnh text 1 dòng."*

    ⭐ Một phép kiểm chỉ chốt **một** đoạn sẽ xanh cả khi dải vẫn là hợp-trên-
       thời-gian. Phải chốt rằng **hai** đoạn cho **hai** chiều cao.
    """
    hop = (_chuoi([(t, 0.90, 0.94) for t in (0, 5, 10)])          # 1 dòng
           + _chuoi([(t, 0.86, 0.94) for t in (40, 45, 50)]))     # 2 dòng
    ra = ocr._theo_doan(hop, dai=60.0, nhip=5.0)
    assert len(ra) == 2
    cao = [round(v["y1"] - v["y0"], 3) for v in ra]
    assert cao[0] < cao[1], cao


def test_BB3_hop_NGANG_theo_doan_chu_khong_phai_0_1():
    """Bộ dò cũ luôn trả `x 0..1`. Hộp phải bám bề ngang chữ thật."""
    hop = [_h(t, 0.90, 0.94, 0.30, 0.70) for t in (0, 5, 10)]
    ra = ocr._theo_doan(hop, dai=20.0, nhip=5.0)
    assert len(ra) == 1
    assert ra[0]["x0"] > 0.0 and ra[0]["x1"] < 1.0
    assert (ra[0]["x1"] - ra[0]["x0"]) < 0.6


def test_KEP_DIEM_GIUA_hai_doan_ke_KHONG_chong_thoi_gian():
    """⛔ **Vế dễ bỏ sót nhất.**

    Nới biên mỗi đoạn để ⛔ không hở ở mép là đúng; nhưng thiếu phép kẹp ở
    **điểm giữa** thì hai đoạn kề **chồng thời gian**, và ở chỗ chồng có **hai**
    ô mờ đè nhau ⇒ vệt mờ **phình ra đúng lúc chuyển câu**, tức đúng lúc người
    xem đang nhìn.

    ⭐ Hai đoạn ĐẶT SÁT nhau (hở đúng bằng một nhịp) là ca ép phép kẹp phải
       chạy — hở rộng thì nới biên ⛔ không chạm tới nhau và bài sẽ xanh giả.
    """
    hop = _chuoi([(0, 0.90, 0.94), (5, 0.90, 0.94),
                  (30, 0.70, 0.74), (35, 0.70, 0.74)])
    ra = ocr._theo_doan(hop, dai=60.0, nhip=5.0)
    assert len(ra) == 2
    assert ra[0]["den_giay"] <= ra[1]["tu_giay"], (
        "hai doan CHONG thoi gian: %.3f > %.3f"
        % (ra[0]["den_giay"], ra[1]["tu_giay"]))


def test_doan_CUOI_phu_toi_HET_video():
    """⭐ Một câu sát cuối mà cắt đúng mốc mẫu cuối sẽ **hở đuôi**, và cái hở
    ấy nằm ở chỗ người xem dừng lại lâu nhất."""
    hop = _chuoi([(t, 0.90, 0.94) for t in (50, 55, 58)])
    ra = ocr._theo_doan(hop, dai=60.0, nhip=5.0)
    assert ra[-1]["den_giay"] == 60.0


def test_MOT_khung_truot_giua_cau_KHONG_cat_cau_lam_doi():
    """⛔ `HE_SO_HO = 1,5` chứ ⛔ không `1,0`: OCR trượt đúng một khung giữa câu
    là chuyện thường, và nó ⛔ không được biến một câu thành hai đoạn."""
    # Mốc 10 s bị thiếu (OCR không đọc được) ⇒ hở đúng 2 nhịp... nhưng
    # `1,5 × 5 = 7,5 s` > hở 10 s? Không — hở là 10 s nên PHẢI tách.
    # Ca trượt MỘT khung: hở = 2 nhịp = 10 s với nhịp 5 ⇒ tách. Dùng nhịp 8:
    hop = _chuoi([(0, 0.90, 0.94), (8, 0.90, 0.94), (24, 0.90, 0.94)])
    ra = ocr._theo_doan(hop, dai=40.0, nhip=12.0)   # hở 16 s <= 1,5 × 12 = 18
    assert len(ra) == 1, "mot khung truot da cat cau lam doi"


def test_hai_cau_CACH_XA_thi_van_tach():
    """⭐ Vế đối chứng cho bài trên: ⛔ không có nó thì `HE_SO_HO = 1000` cũng
    qua, và khi đó **⛔ không bao giờ** tách đoạn — tức quay về hành vi cũ."""
    hop = _chuoi([(0, 0.90, 0.94), (5, 0.90, 0.94),
                  (50, 0.90, 0.94), (55, 0.90, 0.94)])
    assert len(ocr._theo_doan(hop, dai=60.0, nhip=5.0)) == 2


# ── B13 D1 (28/09): chữ CHỈ để phát hiện ĐỔI ĐOẠN — tín hiệu thứ ba ─────────

def test_chuan_hoa_giu_han_va_so_bo_het_con_lai():
    assert ocr._chuan_hoa_van_ban("你好，世界！2025") == "你好世界2025"
    assert ocr._chuan_hoa_van_ban("hello world") == ""
    assert ocr._chuan_hoa_van_ban("") == ""
    assert ocr._chuan_hoa_van_ban(None) == ""  # type: ignore[arg-type]


def test_van_ban_giong_khop_tuyet_doi_hoac_tien_hau_to():
    assert ocr._van_ban_giong("你好世界", "你好世界") is True
    # OCR doc DAN mot cau qua nhieu khung — ban ngan la tien/hau to ban dai.
    assert ocr._van_ban_giong("你好", "你好世界") is True
    assert ocr._van_ban_giong("世界", "你好世界") is True


def test_van_ban_giong_ti_le_ky_tu_chung_cao_van_tinh_la_giong():
    # Sai lech nho (OCR doc lem 1 ky tu) - ti le chung con >= 0,6.
    assert ocr._van_ban_giong("你好世界的人们", "你好世界的人") is True


def test_van_ban_giong_KHAC_han_thi_False():
    assert ocr._van_ban_giong("你好世界", "再见朋友") is False


def test_van_ban_giong_MOT_ben_rong_la_KHAC_ca_hai_rong_la_giong():
    """⚠️ Bất đối xứng có Ý: rỗng-rỗng KHÔNG kết luận được gì (không phải bằng
    chứng "đổi"), một-rỗng-một-có LÀ khác — nhưng `_theo_doan` không bao giờ
    dùng nhánh sau vì nó đòi CẢ HAI có chữ trước khi tin tín hiệu (xem
    `test_mot_ben_OCR_doc_HUT_KHONG_cat_cau`)."""
    assert ocr._van_ban_giong("", "") is True
    assert ocr._van_ban_giong("你好", "") is False
    assert ocr._van_ban_giong("", "你好") is False


def _chuoi_chu(cac: list[tuple[float, float, float, str]]) -> list[ocr.Hop]:
    """`(giây, y0, y1, văn_bản)` → hộp, bề ngang cố định — như `_chuoi`."""
    return [ocr.Hop(t, y0, y1, 0.2, 0.8, chu) for t, y0, y1, chu in cac]


def test_chu_DOI_cat_doan_du_hinh_hoc_KHONG_doi():
    """🔴 Bài CHÍNH của D1: cùng vị trí Y, hở thời gian NHỎ (không đủ tách
    theo `HE_SO_HO`) — chỉ tín hiệu CHỮ ĐỔI mới tách được. Đây đúng ca
    `dai_sub_rapid.py:1524` sửa: "6 câu khác nhau bị gộp 1 box do x đều căn
    giữa không phân biệt được câu"."""
    hop = _chuoi_chu([
        (0, 0.90, 0.94, "你好世界"), (1, 0.90, 0.94, "你好世界"),
        (2, 0.90, 0.94, "再见朋友"), (3, 0.90, 0.94, "再见朋友"),
    ])
    ra = ocr._theo_doan(hop, dai=10.0, nhip=1.0)
    assert len(ra) == 2, "chu doi han nhung khong tach doan"


def test_chu_GIONG_KHONG_cat_doan_du_OCR_doc_dan():
    """Vế đối chứng: chữ đọc DẦN một câu (tiền/hậu tố) ⛔ không bị tách oan."""
    hop = _chuoi_chu([
        (0, 0.90, 0.94, "你"), (1, 0.90, 0.94, "你好"),
        (2, 0.90, 0.94, "你好世界"),
    ])
    ra = ocr._theo_doan(hop, dai=10.0, nhip=1.0)
    assert len(ra) == 1, "chu doc dan mot cau bi tach oan thanh nhieu doan"


def test_mot_ben_OCR_doc_HUT_KHONG_cat_cau():
    """🔴 Vế dễ bỏ sót nhất: một khung OCR đọc HỤT (`van_ban` rỗng, chữ VẪN ở
    đó nhưng recognition trượt) ⛔ không được hiểu là "câu mới" — đúng cách
    `dai_sub_rapid.py:1527` đòi cả hai bên `txt`/`seg[6]` khác rỗng trước khi
    tin tín hiệu "đổi"."""
    hop = _chuoi_chu([
        (0, 0.90, 0.94, "你好世界"), (1, 0.90, 0.94, ""),
        (2, 0.90, 0.94, "你好世界"),
    ])
    ra = ocr._theo_doan(hop, dai=10.0, nhip=1.0)
    assert len(ra) == 1, "mot khung doc hut (van_ban rong) da cat oan mot cau"
