r"""
test_383 — bánh cóc cho `voice_sidecar/do_on_dinh.py` (K3).

Bốn phép đo trong module ấy không phải bốn ý hay. Mỗi phép sinh ra để bịt **một
điểm mù đã đo được** của cổng chất lượng, và mỗi phép đã có **ít nhất một bản
sai** trước bản hiện tại — bản sai ấy chạy trơn tru, trả ra số đẹp, và mù.

Tệp này chốt đúng những chỗ đã sai, bằng tín hiệu **tổng hợp** (không cần GPU,
không cần sidecar) nên nó chạy trong gate như mọi test khác:

  · `do_sang`   — đo TRÊN góc cắt, ở thang **dB**
  · `do_lap_bat_ky` — khớp **cục bộ**, không chỉ tương quan toàn cục
  · `do_on_dinh_bien_do` — phổ của **log** bao, không phải của bao
  · `do_on_dinh_f0` — **một** lần pyin cho cả bản, không phải mỗi cửa sổ một lần

⭐ Mỗi phép kiểm dưới đây đã được chứng minh ĐỎ bằng cách hoàn nguyên đúng chỗ
   đã sửa. Một bánh cóc chưa từng đỏ thì không chốt gì cả.
"""
from __future__ import annotations

import numpy as np
import pytest

from voice_sidecar import do_on_dinh

SR = 24000
DAI_NHIP = do_on_dinh.DAI_NHIP_HZ


def _tieng_gia(giay=6.0, f0=110.0, sr=SR, seed=7):
    """Tín hiệu giống tiếng nói: sóng hài có F0, đóng ngắt theo âm tiết KHÔNG ĐỀU.

    ⛔ KHÔNG dùng nhiễu trắng làm bản nền. Ba trong bốn phép ở đây đo **hình
       dạng** (dốc phổ, chu kỳ nhịp, đường F0); nhiễu trắng không có hình dạng
       nào, nên chúng sẽ "đạt" trên nhiễu mà vẫn hỏng trên tiếng nói.

    🔴 Và KHÔNG dùng nhịp tuần hoàn. Bản đầu của khuôn này đóng ngắt bằng một
       hình sin 5 Hz, và hai phép kiểm đỏ ngay: `khop_cuc_bo_dinh` = **1,0** ở
       bản NỀN (một tín hiệu tuần hoàn hoàn hảo thì mọi cửa sổ khớp mọi cửa sổ),
       `do_nhon_nhip` = **8503** ở bản nền (một hình sin thì đỉnh phổ vô địch).
       Tức khuôn thử tự tạo ra đúng hai hỏng hóc mà nó phải phân biệt.

    ⭐ Tránh được nhiễu trắng rồi rơi vào cái bẫy đối xứng của nó. Tiếng nói
       thật nằm giữa: có cấu trúc, nhưng **không đều**. Nên độ dài âm tiết và
       quãng nghỉ ở đây đều ngẫu nhiên, và F0 đi bộ ngẫu nhiên nhẹ.
    """
    rng = np.random.default_rng(seed)
    n = int(sr * giay)
    x = np.zeros(n)

    # 🔴 Dựng TỪNG ÂM TIẾT một, mỗi âm tiết một PHỔ RIÊNG. Bản thứ ba của khuôn
    #    này dùng chung một bộ sóng hài cho cả bản và chỉ đổi đường bao — nên
    #    mọi khung có cùng hình phổ, và `khop_cuc_bo_dinh` ở bản NỀN là 0,99.
    #    Tức khuôn thử lại tự tạo ra đúng hỏng hóc nó phải bắt, lần thứ hai,
    #    trên một trục khác.
    #
    # ⭐ Cái mà tiếng nói có và hai bản trước thiếu là: âm tiết khác nhau nghe
    #    KHÁC NHAU, không chỉ to nhỏ khác nhau. /ba/ và /ma/ cùng độ to vẫn phân
    #    biệt được — bằng phổ. Nên biên độ từng sóng hài ở đây ngẫu nhiên theo
    #    từng âm tiết, đóng vai formant.
    i = 0
    while i < n:
        d = int(sr * rng.uniform(0.12, 0.26))
        d = min(d, n - i)
        if d < int(sr * 0.03):
            break
        t = np.arange(d) / sr
        f = f0 * rng.uniform(0.94, 1.06)          # cao độ nhích theo âm tiết
        bien = rng.uniform(0.2, 1.0, 25) / np.arange(1, 26)
        am = sum(b * np.sin(2 * np.pi * f * k * t)
                 for k, b in enumerate(bien, start=1))
        # phụ âm xát: nhiễu băng rộng ở đầu âm tiết -> năng lượng TẦN CAO thật,
        # và đó là thứ một bộ lọc thông thấp giết trước tiên.
        xat = np.zeros(d)
        nx = int(sr * rng.uniform(0.02, 0.05))
        xat[:nx] = rng.standard_normal(nx) * rng.uniform(0.1, 0.5)
        cua = np.hanning(min(d, max(8, int(sr * 0.02))))
        vo = np.ones(d)
        vo[:cua.size // 2] = cua[:cua.size // 2]
        vo[-(cua.size // 2):] = cua[-(cua.size // 2):]
        x[i:i + d] = (am / max(np.abs(am).max(), 1e-9)
                      * rng.uniform(0.6, 1.0) + xat) * vo
        i += d + int(sr * rng.uniform(0.03, 0.12))

    x = x + 0.02 * np.convolve(np.abs(x), np.ones(240) / 240,
                               mode="same") * rng.standard_normal(n)
    x += 0.001 * rng.standard_normal(n)
    return (x / np.abs(x).max() * 0.5).astype("float32")


def test_khuon_thu_khong_tu_tao_ra_hong_hoc():
    """Bản NỀN phải sạch với chính hai phép nó dùng để bắt hỏng hóc.

    Nếu phép kiểm này đỏ thì mọi phép kiểm khác trong tệp vô nghĩa: chúng đang
    so một hỏng hóc với một bản nền đã hỏng sẵn.
    """
    w = _tieng_gia()
    assert do_on_dinh.do_lap_bat_ky(w, SR)["khop_cuc_bo_dinh"] < 0.9
    assert do_on_dinh.do_on_dinh_bien_do(w, SR)["do_nhon_nhip"] < 20.0


# ── do_sang ─────────────────────────────────────────────────────────────────

def test_db_dai_cao_thay_loc_thong_thap():
    """Bộ lọc 3,5 kHz phải làm `db_dai_cao` sụt ÍT NHẤT 10 dB.

    🔴 Bản đầu cắt dải ở **2 kHz** — tức HOÀN TOÀN NẰM DƯỚI góc cắt 3,5 kHz,
       nên bộ lọc không chạm tới nó. Bộ dò điểm mù chấm bản ấy **1,4σ**: mù.
       `CAT_SANG_HZ` phải nằm TRÊN góc cắt của thứ ta muốn phát hiện.
    """
    sos = pytest.importorskip("scipy.signal").butter(
        6, 3500.0 / (SR / 2), btype="low", output="sos")
    from scipy.signal import sosfilt

    w = _tieng_gia()
    a = do_on_dinh.do_sang(w, SR)
    b = do_on_dinh.do_sang(np.asarray(sosfilt(sos, w), dtype="float32"), SR)
    assert "db_dai_cao" in a and "db_dai_cao" in b
    assert a["db_dai_cao"] - b["db_dai_cao"] >= 10.0, (
        f"loc thong thap 3,5 kHz chi lam db_dai_cao sut "
        f"{a['db_dai_cao'] - b['db_dai_cao']:.1f} dB — CAT_SANG_HZ "
        f"({do_on_dinh.CAT_SANG_HZ} Hz) co nam TREN goc cat khong?")


def test_cat_sang_nam_tren_goc_loc_thuong_gap():
    """`CAT_SANG_HZ` phải > 3,5 kHz, và điều đó là một RÀNG BUỘC, không phải sở thích."""
    assert do_on_dinh.CAT_SANG_HZ > 3500.0


def test_db_dai_cao_o_thang_db_khong_phai_ti_le():
    """Phải là dB (âm, cỡ hàng chục), không phải một tỉ lệ trong [0, 1].

    ⭐ Không phải chuyện thẩm mỹ: năng lượng trên 4 kHz của tiếng nói cỡ 1e-3,
       và một bộ lọc kéo nó xuống 1e-6. Ở thang tuyến tính hai số ấy cách nhau
       0,001 — nằm gọn trong sàn nhiễu. Ở thang dB chúng cách nhau 30.
    """
    v = do_on_dinh.do_sang(_tieng_gia(), SR)["db_dai_cao"]
    assert v < 0.0 and v > -200.0


# ── do_lap_bat_ky ───────────────────────────────────────────────────────────

def test_khop_cuc_bo_thay_doan_lap_ngan_giua_bai():
    """Chèn 0,5 s lặp vào GIỮA phải đẩy `khop_cuc_bo_dinh` lên gần 1,0.

    🔴 Đây là phép mà tương quan TOÀN CỤC không làm được, và lý do là số học:
       0,5 giây trong 6 giây là ~8% tín hiệu, nên phép lấy trung bình pha loãng
       nó còn vài phần trăm. Phép cục bộ lấy CỰC ĐẠI nên không bị pha loãng.
    """
    w = _tieng_gia()
    n = int(SR * 0.5)
    i = len(w) // 2
    lap = np.concatenate([w[:i], w[i - n:i], w[i:]]).astype("float32")

    a = do_on_dinh.do_lap_bat_ky(w, SR)
    b = do_on_dinh.do_lap_bat_ky(lap, SR)
    assert "khop_cuc_bo_dinh" in b, "thieu phep khop cuc bo"
    assert b["khop_cuc_bo_dinh"] > a.get("khop_cuc_bo_dinh", 0.0), (a, b)
    # ⭐ Tín hiệu MẠNH nhất không phải điểm số mà là ĐỘ TRỄ: đo trên bốn hạt
    #    giống khác nhau, điểm nhích 0,75-0,80 -> 0,78-0,91 (khác nhau tuỳ hạt),
    #    nhưng độ trễ chỉ đúng 0,49 s ở **cả bốn**. Một cổng đọc điểm sẽ lung
    #    lay; một cổng đọc "có một đoạn khớp tại đúng độ trễ X" thì không.
    assert abs(b["khop_cuc_bo_tre_s"] - 0.5) <= 0.06, b


def test_khop_cuc_bo_bo_qua_cua_so_chu_yeu_la_im_lang():
    """Nhiều quãng nghỉ dài KHÔNG được đẩy `khop_cuc_bo_dinh` lên.

    ⛔ Im lặng khớp im lặng một cách hoàn hảo, và phép lấy CỰC ĐẠI thì cực đại
       ấy thắng mọi thứ khác. Trên tiếng thật (n=24) bản chưa lọc cho nền
       **0,9706** — gần kịch trần, nên một đoạn lặp thật không còn chỗ hiện ra.

    ⭐ Phép kiểm này tồn tại vì lần chứng minh-đỏ đầu tiên cho thấy bộ lọc quãng
       lặng **không được phép kiểm nào che**: gỡ nó ra mà cả tệp vẫn xanh. Một
       dòng mã không có bánh cóc là một dòng mã sẽ bị ai đó dọn đi.
    """
    rng = np.random.default_rng(5)
    sr = SR
    manh = []
    for k in range(6):
        manh.append(_tieng_gia(giay=0.45, seed=100 + k))
        manh.append(np.zeros(int(sr * 0.8), dtype="float32"))   # nghỉ DÀI
    w = np.concatenate(manh).astype("float32")
    w += (0.0005 * rng.standard_normal(w.size)).astype("float32")
    r = do_on_dinh.do_lap_bat_ky(w, sr)
    assert r.get("khop_cuc_bo_dinh", 0.0) < 0.95, (
        f"im lang dang khop im lang: {r} — bo loc cua so im lang con khong?")


def test_khop_cuc_bo_tru_trung_binh_tung_cua_so():
    """Hai quãng cùng độ to nhưng khác hình dạng KHÔNG được khớp cao.

    ⛔ Nếu bỏ bước trừ trung bình theo từng cửa sổ, mọi bản đọc đều đều sẽ báo
       động, vì "cùng to" bị đọc thành "giống nhau".
    """
    rng = np.random.default_rng(3)
    t = np.arange(int(SR * 6)) / SR
    # hai nua cung bien do RMS nhung noi dung ngau nhien doc lap
    w = (0.3 * rng.standard_normal(t.size)).astype("float32")
    r = do_on_dinh.do_lap_bat_ky(w, SR)
    assert r.get("khop_cuc_bo_dinh", 0.0) < 0.9, r


# ── do_on_dinh_bien_do ──────────────────────────────────────────────────────

def test_do_nhon_nhip_KHONG_hua_bat_duoc_rung_6_phan_tram():
    """Ghi lại một điểm mù CÒN NGUYÊN, chứ không giả vờ đã bịt.

    🔴 `run_giong_6pc` — rung biên độ 6% ở 5,5 Hz — là hỏng hóc duy nhất trong
       bảy hỏng hóc mà cổng **vẫn không thấy**, sau ba lần thử ba cơ chế khác
       nhau: năng lượng dải 3–8 Hz, độ nhọn đỉnh trên bao tuyến tính, độ nhọn
       đỉnh trên **log** bao. Cao nhất từng đạt: 1,4σ. Ngưỡng là 4σ.

    Hai lý do, và chỉ một trong hai sửa được:

      ① 5,5 Hz **trùng nhịp âm tiết** tiếng Việt. Trên trục điều biên, rung
         giọng và nhịp nói ở cùng một chỗ. Lấy log gỡ được phép NHÂN nhưng
         không gỡ được sự trùng dải — nó là trùng thật.
      ② Không có bằng chứng nào rằng VieNeu **sinh ra** hỏng hóc này. Nó là
         hỏng hóc tôi tự nghĩ ra để biện minh cho jitter/shimmer, chứ không
         phải một lỗi ai đó gặp. Upstream #159 báo lặp và trôi, không báo rung.

    ⇒ Đóng nó ở đây như một **giới hạn đã đo và đã ghi**, không phải một việc
      còn dở. Đuổi theo một hỏng hóc chưa từng xảy ra bằng một chỉ số không
      tách được nó khỏi nhịp nói là hai sai lầm nhân với nhau.

    ⛔ Phép kiểm này CHỐT lời hứa đó. Nếu ai đó sau này làm `do_nhon_nhip` tách
       được rung 6%, phép kiểm sẽ đỏ và buộc họ sửa lại lời văn ở đây thay vì
       để tài liệu nói sai theo hướng bi quan.
    """
    w = _tieng_gia()
    t = np.arange(len(w)) / SR
    rung = (w * (1.0 + 0.06 * np.sin(2 * np.pi * 5.5 * t))).astype("float32")
    a = do_on_dinh.do_on_dinh_bien_do(w, SR)["do_nhon_nhip"]
    b = do_on_dinh.do_on_dinh_bien_do(rung, SR)["do_nhon_nhip"]
    assert b < a * 1.5, (
        f"do_nhon_nhip nay TACH duoc rung 6% ({a} -> {b}). Tot — nhung phai "
        f"cap nhat lai loi van o day va o do_on_dinh.py, dung de tai lieu noi "
        f"sai theo huong bi quan.")


def test_do_nhon_nhip_van_do_duoc_va_on_dinh():
    """Vẫn giữ phép đo — nó nhúc nhích cho hỏng hóc khác (lặp: 3,9σ) và rẻ."""
    for seed in (7, 21, 33):
        r = do_on_dinh.do_on_dinh_bien_do(_tieng_gia(seed=seed), SR)
        assert 1.0 < r["do_nhon_nhip"] < 20.0, (seed, r)
        assert DAI_NHIP[0] <= r["nhip_troi_hz"] <= DAI_NHIP[1], (seed, r)


# ── do_on_dinh_f0 ───────────────────────────────────────────────────────────

def test_f0_lech_nua_thay_doi_tong_o_nua_sau():
    """Nửa sau cao hơn 6% phải hiện ra ở `f0_lech_nua` ≈ 0,06."""
    a = _tieng_gia(giay=3.0, f0=110.0, seed=11)
    b = _tieng_gia(giay=3.0, f0=110.0 * 1.06, seed=11)
    w = np.concatenate([a, b]).astype("float32")
    r = do_on_dinh.do_on_dinh_f0(w, SR)
    assert "f0_lech_nua" in r, r
    assert 0.03 <= r["f0_lech_nua"] <= 0.12, r


def test_f0_khong_phu_thuoc_librosa():
    """Nhánh F0 phải chạy được ở python của GATE, nơi `librosa` không có.

    🔴 Bản đầu gọi `librosa.pyin`. Nó chạy tốt trên máy có GPU và trả `{}` ở
       gate — im lặng, không lỗi. Hậu quả đo được: `test_khong_tra_ra_cai_dem`
       XANH ngay cả khi tôi cố tình nhét một cái đếm trở lại vào dict, vì cái
       đếm ấy nằm trong nhánh không bao giờ chạy.

    ⛔ Một bánh cóc không chạy trông giống hệt một bánh cóc đã đạt.
    """
    import sys
    assert "librosa" not in sys.modules or True     # khong quan tam co hay khong
    r = do_on_dinh.do_on_dinh_f0(_tieng_gia(giay=6.0, f0=140.0), SR)
    assert r and "f0_trung_vi_hz" in r, r
    # tu tuong quan luong tu hoa theo do tre nguyen => lech he thong vai %
    assert abs(r["f0_trung_vi_hz"] - 140.0) / 140.0 < 0.05, r


def test_f0_bam_dung_cao_do_o_nhieu_giong():
    for dat in (90.0, 110.0, 180.0, 240.0):
        r = do_on_dinh.do_on_dinh_f0(_tieng_gia(giay=6.0, f0=dat), SR)
        assert abs(r["f0_trung_vi_hz"] - dat) / dat < 0.05, (dat, r)


# ── hợp đồng chung ──────────────────────────────────────────────────────────

def test_khong_tra_ra_cai_dem():
    """Không chỉ số nào được là một CÁI ĐẾM.

    🔴 `f0_so_cua_so` từng có mặt. Sàn nhiễu của nó bằng 0 (văn bản cố định ⇒
       độ dài cố định), nên bộ dò điểm mù chia cho ~0 và in **1.000.000σ** cho
       `lap_o_giua`, tuyên bố đã thấy trong khi vẫn mù hoàn toàn. Một cái đếm
       không đo chất lượng — nó đo độ dài.
    """
    r = do_on_dinh.do_tat_ca(_tieng_gia(), SR)
    assert r, "khong do duoc gi"
    for k, v in r.items():
        assert not isinstance(v, bool)
        assert float(v) == float(v)
        assert "so_cua_so" not in k and not k.startswith("so_"), k


def test_vang_mat_khac_khong():
    """Clip quá ngắn ⇒ chỉ số **vắng mặt**, không phải bằng 0.

    ⛔ Cùng bài học với `snr_db` từng bị `or 0.0` biến "không đo được" thành
       "đo được, bằng 0" — một giá trị giả đi thẳng vào baseline.
    """
    r = do_on_dinh.do_tat_ca(np.zeros(300, dtype="float32"), SR)
    assert "f0_trung_vi_hz" not in r
    assert "khop_cuc_bo_dinh" not in r


def test_mot_phep_hong_khong_lam_hong_ba_phep_kia(monkeypatch):
    monkeypatch.setattr(do_on_dinh, "do_sang",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    r = do_on_dinh.do_tat_ca(_tieng_gia(), SR)
    assert "db_dai_cao" not in r
    assert "khop_cuc_bo_dinh" in r
