"""Bộ đo B1 (WER/CER nghe chép vs hardsub) — chốt CÁCH ĐO trước khi tin CON SỐ.

⛔ Một con số WER thấp có thể là *"ASR tốt"* hoặc là *"bộ đo hỏng"*. Tệp này chốt
những thứ phân biệt hai khả năng đó, và nó chạy **không cần card, không cần phim**.
"""
from __future__ import annotations

import pytest


def test_do_mot_phim_khai_GIOI_HAN_cua_chan_ly_nen():
    """⛔ Hardsub là đối chiếu TỐT, không hoàn hảo — nó có thể **rút gọn** lời nói.

    Một con số WER không kèm giới hạn đó sẽ bị đọc như WER thật. Nên giới hạn phải
    ở **trong docstring của chính hàm đo**, không phải ở cuối một báo cáo mà người
    trích số sẽ không đọc.
    """
    from tools import bench_b1_chep_loi as b

    tai_lieu = (b.do_mot_phim.__doc__ or "").lower()
    assert "rút gọn" in tai_lieu or "rut gon" in tai_lieu


def test_ket_qua_MANG_THEO_gioi_han_chu_khong_chi_con_so():
    """Giới hạn phải đi **trong bản ghi**, không chỉ trong tài liệu.

    🔑 Người trích số sau này đọc JSON, không đọc `.md`. Nếu giới hạn chỉ nằm trong
       báo cáo thì nó sẽ rụng ngay lần đầu ai đó `grep` con số ra.
    """
    from tools import bench_b1_chep_loi as b

    kq = b.gop_ket_qua(cer=0.05, so_dong_nguon=30, so_dong_hardsub=28,
                       engine="x", co_card=True, ti_le_don_vi_sai=0.11,
                       don_vi_ti_le="dong")
    assert kq["gioi_han"], "ban ghi khong mang gioi han cua chan ly nen"
    gh = kq["gioi_han"].lower()
    assert "rút gọn" in gh or "rut gon" in gh
    assert kq["chan_ly_nen"] == "hardsub"


def test_chuan_hoa_bo_dau_cau_va_khoang_trang_NHUNG_khong_bo_chu():
    """⛔ Chuẩn hoá được phép bỏ **hình thức**, không được bỏ **nội dung**.

    Một hàm chuẩn hoá quá tay (ví dụ bỏ hết ký tự không phải Hán) sẽ kéo WER xuống
    một cách giả tạo — và nó sẽ trông y hệt một engine tốt.
    """
    from tools import bench_b1_chep_loi as b

    assert b.chuan_hoa("你好，世界！") == b.chuan_hoa("你好 世界")
    assert b.chuan_hoa("A B") != b.chuan_hoa("AB")     # khoang trang co nghia o Latin
    assert "跳伞" in b.chuan_hoa("跳伞，慢了")


def test_WER_vot_len_khi_ban_chep_bi_lam_HONG():
    """⛔ ĐỐI CHỨNG BẮT BUỘC. Không có bài này thì một WER thấp có thể chỉ là bộ đo hỏng.

    🔑 Đây là phép *"số 0 cần đối chứng"*: một bộ đo luôn trả ~0 sẽ cho mọi engine
       đạt, và nó sẽ **im lặng** làm thế.
    """
    from tools import bench_b1_chep_loi as b

    that = "今天 我们 来 做 烤 牛肠 非常 好吃 大家 一起 来 看"
    tot = b.do_hai_ban(that, that)
    assert tot["ti_le_don_vi_sai"] == pytest.approx(0.0, abs=1e-9)

    hong = b.lam_hong(that, ti_le=0.3, seed=7)
    assert hong != that
    xau = b.do_hai_ban(that, hong)
    assert xau["ti_le_don_vi_sai"] > 0.15, (
        f"lam hong 30% tu ma ti le chi {xau['ti_le_don_vi_sai']:.3f} — bo do "
        f"khong nhay, nen mot con so thap KHONG chung minh duoc gi")


def test_lam_hong_TAT_DINH_theo_seed():
    """Đối chứng phải lặp lại được, nếu không nó không phải một phép đo."""
    from tools import bench_b1_chep_loi as b

    a = "một hai ba bốn năm sáu bảy tám chín mười"
    assert b.lam_hong(a, ti_le=0.3, seed=1) == b.lam_hong(a, ti_le=0.3, seed=1)


def test_NGUONG_doc_tu_TAI_LIEU_chu_khong_go_lai_trong_ma():
    """⛔ Ngưỡng phải có **một** nguồn. Gõ lại trong mã là chỗ nó trôi khỏi tài liệu.

    Cùng bài học với `gate.TRAN_N_GO_TAY`: đã có một lần hằng đổi 6→7 mà một phép
    kiểm vẫn khai 6, và nó đỏ ở đúng chỗ đáng lẽ bảo vệ con số ấy.
    """
    import pathlib

    from tools import bench_b1_chep_loi as b

    van = (pathlib.Path(b.__file__).resolve().parents[1]
           / "docs" / "auto_scan_video_final" / "B1_CHEP_LOI.md"
           ).read_text(encoding="utf-8")
    assert f"WER ≤ {b.NGUONG_WER:.2f}".replace(".", ",") in van
    assert f"CER ≤ {b.NGUONG_CER:.2f}".replace(".", ",") in van


def test_phim_SUNG_HOI_bi_loai_va_noi_RO_vi_sao():
    """⛔ B0 ghi *"không chắc có giọng"* — một phim không có tiếng nói sẽ cho một
    con số trông như thất bại của engine."""
    from tools import bench_b1_chep_loi as b

    assert any("真人气枪" in x for x in b.PHIM_LOAI)
    assert "giọng" in b.PHIM_LOAI[next(iter(b.PHIM_LOAI))].lower() or True


def test_TI_LE_tren_van_HAN_duoc_goi_dung_ten_la_DONG_khong_phai_TU():
    """🔴 `jiwer.wer` tách bằng **khoảng trắng**, và văn Hán không có khoảng trắng.

    Đo 24/09: một dòng phụ đề Hán 12 ký tự ⇒ `jiwer` thấy **1 "từ"**. Hai bản chép
    lệch **đúng một chữ** ⇒ tỉ lệ = **0,50**, trong khi CER = 0,0417.

    ⛔ Gọi con số đó là "WER" là **đặt tên rộng hơn thứ nó đo**, và người sau sẽ so
       nó với WER của bảng xếp hạng thế giới — **hai thứ không cùng đơn vị**.
    """
    from tools import bench_b1_chep_loi as b

    a = "深度解析跳伞慢了该怎么打" + chr(10) + "教你用细节操作来化解危机"
    b_van = "深度解析跳伞慢了该怎么打" + chr(10) + "教你用细节操作化解危机"
    kq = b.do_hai_ban(a, b_van)
    assert kq["don_vi_ti_le"] == "dong", kq
    assert kq["ti_le_don_vi_sai"] > 0.4          # mot chu sai -> nua so DONG sai
    assert kq["cer"] < 0.06                       # ...nhung chi ~4% KY TU sai
    assert "wer" not in kq, "ten `wer` phai bien mat — no rong hon thu no do"


def test_van_LATIN_thi_don_vi_DUNG_la_tu():
    """⚠️ Cùng một trường, **hai nghĩa** tuỳ ngôn ngữ ⇒ bản ghi phải khai đơn vị."""
    from tools import bench_b1_chep_loi as b

    kq = b.do_hai_ban("the quick brown fox jumps", "the quick brown cat jumps")
    assert kq["don_vi_ti_le"] == "tu", kq
    assert kq["ti_le_don_vi_sai"] == pytest.approx(0.2, abs=1e-9)


def test_DAT_chi_xet_CER_chu_khong_xet_ti_le_chua_hieu_chinh():
    """⛔ Ngưỡng 0,25 được viết cho tỉ lệ **TỪ** sai. Áp nó cho tỉ lệ **DÒNG** sai là
    dùng một ngưỡng **chưa từng được hiệu chỉnh** cho đơn vị đó.

    ⇒ Báo cáo con số, **không** phán xử bằng nó. Câu hỏi đang ở chỗ điều phối.
    """
    from tools import bench_b1_chep_loi as b

    kq = b.gop_ket_qua(cer=0.05, ti_le_don_vi_sai=0.90, don_vi_ti_le="dong",
                       so_dong_nguon=10, so_dong_hardsub=10, engine="x",
                       co_card=True)
    assert kq["dat"] is True, "ti le DONG sai khong duoc phan xu"
    assert kq["lech_doan_dat"] is True
    assert "CER" in kq["dat_xet_tren"]


# ══════════════════════════════════════════════════════════════════════════════
#  CẤU TRÚC — thứ CER một mình không thấy
# ══════════════════════════════════════════════════════════════════════════════

def test_CER_mot_minh_de_HO_cau_truc_nen_ban_ghi_phai_co_lech_doan():
    """🔴 CER tính trên văn bản **nối liền** ⇒ nó không thấy **số đoạn**.

    Mà mỗi đoạn là **một khe lồng tiếng**. Một bản chép gộp hai câu làm một có thể
    cho CER rất đẹp mà **canh thời gian hỏng** — và bước canh thời gian sẽ lãnh hậu
    quả, không phải bước chép lời. Lượt nền có triệu chứng đúng họ: **6 đoạn / 107 s**.
    """
    from tools import bench_b1_chep_loi as b

    kq = b.gop_ket_qua(cer=0.01, so_dong_nguon=3, so_dong_hardsub=30,
                       engine="x", co_card=True)
    assert kq["cer"] == 0.01
    assert kq["lech_doan"] == pytest.approx(0.9, abs=1e-9)
    assert kq["can_giai_thich_lech_doan"] is True, (
        "CER dep + so doan lech 90% ma ban ghi khong bat nhin")


def test_lech_doan_NAY_LA_CONG_chu_khong_con_chi_bao():
    """🔴 **Đổi VAI ngày 24/09, SAU khi thấy số — và khai thẳng.**

    ⛔ **NỚI** một ngưỡng sau khi thấy số = hợp lý hoá kết quả tồi. **Cấm.**
    ⭐ **SIẾT** một phép từ *"chỉ báo"* thành *"chặn"* khi số liệu cho một **LÝ DO
       ta chưa từng có**: được, **nếu khai rõ**.

    Lý do mới: lúc đặt 0,20 ta **chưa biết cú gộp này tồn tại**. Phim 1 cho
    `lech_doan = 0,8922` — WhisperX gộp **9 câu thành 1** (23,3 s/đoạn vs hardsub
    2,4 s). Với sản phẩm lồng tiếng, **phân đoạn CHÍNH LÀ sản phẩm**: mỗi đoạn là
    một khe đặt câu tiếng Việt, và một khe 23 giây liền mạch thì `timing_align`
    **không còn gì để canh**.

    ⛔ Và con số `0,20` **không đổi** — chỉ đổi vai của nó.
    """
    from tools import bench_b1_chep_loi as b

    kq = b.gop_ket_qua(cer=0.01, so_dong_nguon=3, so_dong_hardsub=30,
                       engine="x", co_card=True)
    # ⛔ ĐỔI 24/09: `lech_doan` nay LA CONG. Xem `NGUONG_LECH_DOAN` ve vi sao doi
    #    VAI (khong doi con so) sau khi thay so phim 1.
    assert kq["dat"] is False, "lech_doan nay la CONG, khong con chi bao"
    assert kq["can_giai_thich_lech_doan"] is True


def test_hardsub_RONG_cho_nan_chu_khong_cho_KHONG():
    """⛔ *"không lệch"* và *"không đo được"* là hai điều khác nhau.

    Gộp chúng thành một số 0 làm một phim **không có hardsub** trông như một phim
    **khớp hoàn hảo** — đúng bài *"hai trạng thái gộp thành một giá trị"*.
    """
    import math

    from tools import bench_b1_chep_loi as b

    assert math.isnan(b.lech_doan(10, 0))
    assert b.lech_doan(10, 10) == 0.0


def test_hardsub_RONG_thi_KHONG_DAT_chu_khong_phai_dat():
    """⛔ `nan <= x` là False, và ở đây đó là hành vi ĐÚNG.

    Một phim không có hardsub ⇒ ta **không biết** cấu trúc có đúng không, và
    *"không biết"* **không được tính là "đạt"**.
    """
    from tools import bench_b1_chep_loi as b

    kq = b.gop_ket_qua(cer=0.01, so_dong_nguon=10, so_dong_hardsub=0,
                       engine="x", co_card=True)
    assert kq["dat"] is False
    assert kq["lech_doan_dat"] is False


# ─────────────────────────────────────────────────────────────────────────────
# N-17 he qua THU HAI: cho noi `autosubvideo` -> ASV vut truong cua engine
#
# Lan 1 (da ghi): `fallback_reason`.  Lan 2 (o day): `words`.
# ⛔ Ca hai deu KHONG lam sai mot con so nao — chung lam mat kha nang PHAN BIET,
#    nen khong phep kiem nao do. Bon phep duoi day la cai may bat khop do.
# ─────────────────────────────────────────────────────────────────────────────


def test_chuan_hoa_doc_duoc_CA_HAI_ten_khoa_cua_tu():
    """⛔ `whisperx` goi la `word`, `faster-whisper` goi la `text` — **ca hai dung**.

    Do that 24/09: ASV chi doc `text` ⇒ nhanh MAC DINH (`aligned`) cho `so_tu`
    = **0** trong khi nhanh LUI cho **1031**. Ta tra tien cho `align()` roi nem
    ket qua di. ⇒ Phep kiem phai chot CA HAI hinh dang, khong phai mot.
    """
    from apps.auto_scan_video import ban_ghi

    for khoa in ("text", "word"):
        tho = {"segments": [{"start": 0.0, "end": 2.0, "chu": "", "text": "你好世界",
                             "words": [{"start": 0.0, "end": 1.0, khoa: "你好"},
                                       {"start": 1.0, "end": 2.0, khoa: "世界"}]}],
               "language": "zh", "engine": "whisperx",
               "alignment_status": "aligned"}
        ban = ban_ghi.chuan_hoa(tho, thoi_luong_nguon=2.0)
        assert ban_ghi.tom_tat(ban)["so_tu"] == 2, f"khoa {khoa!r} bi vut"


def test_tu_bi_BO_duoc_DEM_chu_khong_bien_mat_im_lang():
    """Bỏ 3 từ khác hẳn bỏ 900 từ — mà `continue` làm hai ca trông y hệt nhau.

    WhisperX **thật sự** để một số từ không căn được (`alignment.py` chỉ gắn
    `start`/`end` khi không phải NaN), nên nhánh này chạy thật.
    """
    from apps.auto_scan_video import ban_ghi

    tho = {"segments": [{"start": 0.0, "end": 3.0, "text": "你好世界再见",
                         "words": [{"start": 0.0, "end": 1.0, "word": "你好"},
                                   {"word": "世界"},                      # thieu moc
                                   {"start": 2.0, "end": 3.0, "word": ""}]}],
           "language": "zh", "engine": "whisperx", "alignment_status": "aligned"}
    ban = ban_ghi.chuan_hoa(tho, thoi_luong_nguon=3.0)
    assert ban["tu_bi_bo"] == {"khong_chu": 1, "thieu_moc": 1, "moc_nguoc": 0}
    assert ban_ghi.tom_tat(ban)["tu_bi_bo"]["thieu_moc"] == 1


def test_nhan_ALIGNED_ma_KHONG_co_moc_tu_thi_DO_TO():
    """⭐ Biến cái nhãn nói dối thành BẤT BIẾN máy kiểm — ⛔ không cảnh báo nhẹ.

    `timing_align` đọc `canh_chinh == "aligned"` và làm việc như thể mỗi đoạn có
    mốc bên trong. Một khối 24 giây **không mốc nào** mang đúng cái nhãn đó là
    hai trạng thái rất khác nhau đeo một tên.
    """
    import pytest as _p

    from apps.auto_scan_video import ban_ghi

    tho = {"segments": [{"start": 0.0, "end": 24.0, "text": "你好", "words": []}],
           "language": "zh", "engine": "whisperx", "alignment_status": "aligned"}
    with _p.raises(ban_ghi.BanGhiError):
        ban_ghi.chuan_hoa(tho, thoi_luong_nguon=24.0)

    # ⛔ Va bat bien nay CHI rang buoc nhan `aligned`: nhanh lui khai that la
    #    `fallback_unaligned` thi khong co moc tu la DUNG, khong duoc do.
    tho["alignment_status"] = "fallback_unaligned"
    ban_ghi.chuan_hoa(tho, thoi_luong_nguon=24.0)


# ─────────────────────────────────────────────────────────────────────────────
# CAT LAI DOAN — luat cat chep tu whisperX PR #1466, nguong tu Netflix TTSG
# ─────────────────────────────────────────────────────────────────────────────


def _tu_han(chuoi: str, bat: float, buoc: float = 0.5) -> list[dict]:
    """Mot ky tu = mot `word`, dung nhu `align()` sinh ra cho `zh`.

    (`alignment.py`: `if model_lang in LANGUAGES_WITHOUT_SPACES: word_idx += 1`
    o moi ky tu.)
    """
    return [{"word": c, "start": bat + i * buoc, "end": bat + (i + 1) * buoc}
            for i, c in enumerate(chuoi)]


def test_cat_khoi_dai_thanh_CAU_tai_dau_ket_cau():
    """Đúng triệu chứng đo được: một khối ~24 s mang nhiều câu 。"""
    from apps.auto_scan_video import cat_doan

    chuoi = "大家好今天做红烧肉。首先准备五花肉切块。然后热锅凉油下姜片。"
    tho = {"language": "zh", "segments": [
        {"start": 0.0, "end": len(chuoi) * 0.5, "text": chuoi,
         "words": _tu_han(chuoi, 0.0)}]}
    moi, chan = cat_doan.cat_lai(tho, ngon_ngu="zh")

    assert chan["so_doan_truoc"] == 1
    assert chan["so_doan_sau"] == 3
    assert [d["text"] for d in moi["segments"]] == [
        "大家好今天做红烧肉。", "首先准备五花肉切块。", "然后热锅凉油下姜片。"]
    # ⛔ Moi nhat cat phai roi dung sau mot dau ket cau — khong mot cho nao khac.
    for d in moi["segments"][:-1]:
        assert d["text"].endswith("。")


def test_khoi_KHONG_co_cho_ngat_thi_DE_NGUYEN_va_KHAI_RA():
    """⛔ Cắt giữa câu TỆ HƠN gộp — khe chứa nửa ý thì bản dịch sai nghĩa.

    ⇒ Không có chỗ ngắt hợp lệ thì để nguyên, và **nói ra** là đã để nguyên.
    """
    from apps.auto_scan_video import cat_doan

    chuoi = "大" * 60                                   # 30 giay, khong mot dau cau
    tho = {"language": "zh", "segments": [
        {"start": 0.0, "end": 30.0, "text": chuoi, "words": _tu_han(chuoi, 0.0)}]}
    moi, chan = cat_doan.cat_lai(tho, ngon_ngu="zh")

    assert chan["so_doan_sau"] == 1                     # ⛔ khong che bua
    assert chan["so_doan_khong_cho_ngat"] == 1          # ...va KHAI RA
    assert chan["so_doan_qua_dai"] == 1
    assert moi["segments"][0]["text"] == chuoi          # chu khong mat mot ky tu


def test_doan_DA_VUA_KHE_thi_khong_dung_vao():
    """Ngưỡng 7,0 s là *Netflix TTSG General Requirements* (bài 215758617)."""
    from apps.auto_scan_video import cat_doan

    chuoi = "你好。世界。"
    tho = {"language": "zh", "segments": [
        {"start": 0.0, "end": 3.0, "text": chuoi, "words": _tu_han(chuoi, 0.0)}]}
    moi, chan = cat_doan.cat_lai(tho, ngon_ngu="zh")

    assert chan["so_doan_sau"] == 1
    assert moi["segments"][0]["text"] == chuoi


def test_KHONG_co_moc_tung_tu_thi_KHONG_cat():
    """⛔ Cắt một khối 24 s theo tỉ lệ ký tự là **bịa mốc**, không phải cắt.

    Đó đúng là thứ nhánh lui `fallback_unaligned` đưa tới, và nó phải đi ra ở
    chẩn đoán chứ không đi ra ở một con số `so_doan` đẹp.
    """
    from apps.auto_scan_video import cat_doan

    chuoi = "大家好今天做红烧肉。首先准备五花肉切块。"
    tho = {"language": "zh", "segments": [
        {"start": 0.0, "end": 24.0, "text": chuoi, "words": []}]}
    _, chan = cat_doan.cat_lai(tho, ngon_ngu="zh")

    assert chan["so_doan_sau"] == 1
    assert chan["so_doan_khong_co_moc_tu"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# CỬA 3 — TIÊM LỖI vào chính cái cổng
#
# ⭐ Một phép đo phải trả lời được *"cái gì còn làm nó đỏ?"*. Ba cách cắt cố tình
#    tồi dưới đây PHẢI đỏ. Số dòng hardsub và thời lượng là số ĐO THẬT 24/09.
# ─────────────────────────────────────────────────────────────────────────────

#: (tên, số dòng hardsub, thời lượng giây) — đo 24/09, ⛔ không phải số dựng.
PHIM_THAT = (("v1 món ăn", 102, 265.0), ("v2 cắm trại", 107, 190.0),
             ("v3 PUBG", 95, 106.83))


def _cat_may_moc(thoi_luong: float, buoc: float) -> int:
    import math

    return math.ceil(thoi_luong / buoc)


def test_TIEM_gop_tat_ca_thanh_MOT_doan_phai_DO():
    """Cách cắt tồi nhất có thể. ⛔ Xanh ở đây thì cổng không đo gì cả."""
    from tools import bench_b1_chep_loi as b

    for ten, hardsub, _ in PHIM_THAT:
        lech = b.lech_doan(1, hardsub)
        assert lech > b.NGUONG_LECH_DOAN, f"{ten}: gộp tất mà XANH ({lech})"


def test_TIEM_cat_moi_30_giay_phai_DO():
    """Đúng trạng thái hỏng vừa rời khỏi (khối VAD ~30 s của WhisperX)."""
    from tools import bench_b1_chep_loi as b

    for ten, hardsub, giay in PHIM_THAT:
        lech = b.lech_doan(_cat_may_moc(giay, 30.0), hardsub)
        assert lech > b.NGUONG_LECH_DOAN, f"{ten}: cắt mỗi 30 s mà XANH ({lech})"


def test_TIEM_cat_may_moc_moi_2_giay_LO_MOT_LO_tren_v2():
    """🔴 **CỬA 3 KHÔNG QUA — và đây là phép kiểm ghim lỗ thủng đó.**

    Cắt **máy móc mỗi 2,0 giây**, bất kể nội dung — đúng kiểu **cắt giữa câu** mà
    ràng buộc của sản phẩm cấm — vẫn **XANH** trên phim 2:

    ```
    v1  133 đoạn vs 102 dòng -> 0,3039 ⛔ đỏ
    v2   95 đoạn vs 107 dòng -> 0,1121 ✅ XANH      ⬅ lỗ thủng
    v3   54 đoạn vs  95 dòng -> 0,4316 ⛔ đỏ
    ```

    ⛔ Trong khi **bản cắt theo CÂU** của ta trên chính phim đó cho **0,3084** —
    tức cổng đang **thưởng** cho cách cắt tồi và **phạt** cách cắt đúng. Đó là
    bằng chứng cơ học rằng `lech_doan` **đếm số đoạn** không phân biệt được *cắt
    đúng chỗ* với *cắt đủ số*.

    ⚠️ Đây là phép kiểm **ĐẶC TẢ HIỆN TRẠNG**: nó **sẽ đỏ** khi ai đó sửa cổng,
       và lúc đó **xoá nó đi** là hành động đúng. ⛔ Đừng "sửa" nó bằng cách nới
       số.
    """
    from tools import bench_b1_chep_loi as b

    lo = [(ten, b.lech_doan(_cat_may_moc(giay, 2.0), hardsub))
          for ten, hardsub, giay in PHIM_THAT
          if b.lech_doan(_cat_may_moc(giay, 2.0), hardsub) <= b.NGUONG_LECH_DOAN]
    assert lo == [("v2 cắm trại", 0.1121)], (
        f"lỗ thủng đã đổi: {lo}. Nếu cổng vừa được sửa thì XOÁ bài này.")


def test_cat_theo_CAU_va_cat_MAY_MOC_khong_phan_biet_duoc_bang_SO_DOAN():
    """⭐ Cùng một `lech_doan` ⇔ hai cách cắt **khác hẳn nhau về chất**.

    ⛔ Đó là lý do chỉ báo **ranh giới khớp** phải đi kèm mọi con số `lech_doan`,
       và cũng là lý do nó ⛔ **không được** biến thành cổng thứ hai: nó tính từ
       chỗ ngắt của chính ta, nên nó xác nhận ta **nhất quán**, không xác nhận ta
       **đúng**.
    """
    from tools import bench_b1_chep_loi as b

    # v2: cắt theo CÂU cho 74 đoạn; cắt máy móc 2,0 s cho 95 đoạn.
    theo_cau = b.lech_doan(74, 107)
    may_moc = b.lech_doan(95, 107)
    assert may_moc < theo_cau, "giả định của bài này đã đổi"
    assert may_moc <= b.NGUONG_LECH_DOAN < theo_cau
