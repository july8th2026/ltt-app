r"""
do_on_dinh.py — bốn phép đo bịt đúng bốn điểm mù đã ĐO được của cổng chất lượng.

## Vì sao đúng bốn phép này, không phải ba hay năm

Pha K3 vốn đặt ra là "mang HNR · jitter · shimmer từ hệ cũ sang". Tra cộng đồng
xong thì tiền đề ấy lung lay ở bốn chỗ:

  · Jitter/shimmer là chỉ số **lâm sàng**, đo trên nguyên âm kéo dài để đánh giá
    bệnh lý thanh quản. Cộng đồng đo TTS bằng **bộ dự đoán MOS** — UTMOS, NISQA,
    DNSMOS — chứ không dùng chúng.
  · Bản của hệ cũ **không phải** định nghĩa lâm sàng: nó lấy chu kỳ trên các
    khung cách nhau 10 ms chứ không phải hai chu kỳ thanh môn liền kề. Gọi nó là
    "jitter" rồi so với ngưỡng lâm sàng (< 1%) là so hai thứ khác nhau.
  · `NISQA-TTS` — đúng công cụ cho việc này, 968 sao — có trọng số
    **CC BY-NC-SA**, tức **không dùng được** trong một sản phẩm thương mại.
  · `UTMOS` (MIT) dùng được nhưng trọng số **411 MB** và huấn luyện trên tiếng
    Anh; giá trị tuyệt đối trên tiếng Việt là một ẩn số.

⇒ Nên câu hỏi đổi từ *"thêm gì"* sang **"cổng đang bỏ sót gì"**, và câu ấy đo
  được: `tools/do_diem_mu_cong.py` tiêm từng hỏng hóc đã biết vào tiếng thật rồi
  xem chỉ số nào nhúc nhích, so với **sàn nhiễu giữa hai lượt sinh bình thường**.

## Kết quả (01/09/2026, ngưỡng "thấy" = 4σ trên sàn nhiễu, n = 24)

    hỏng hóc tiêm vào     chỉ số bắt được nó         σ    trạng thái
    nhiễu 15 dB           vat_99_hz                29,4   THẤY  <- K3
    vỡ tiếng              true_peak_dbtp            8,5   THẤY
    đứt quãng 1,5 s       im_giua_dai_nhat_s       18,8   THẤY
    đục (lọc 3,5 kHz)     db_dai_cao                8,6   THẤY  <- K3
    lặp 0,5 s ở GIỮA      khop_cuc_bo_dinh          4,4   THẤY  <- K3
    run giọng 6%          (cao nhất 2,5σ)                 🔴 CÒN MÙ
    lệch tông nửa sau     (cao nhất 2,1σ)                 🔴 CÒN MÙ

⭐ `dut_quang_1s5` nay có **hai** chỉ số độc lập cùng bắt được nó
   (`im_giua_dai_nhat_s` 18,8σ và `khop_cuc_bo_tai_s` 4,6σ) — không phải mục
   tiêu của K3, nhưng là thứ đáng giữ: một hỏng hóc chỉ có một người canh thì
   mất người ấy là mất luôn.

⭐ Bốn điều học được ở đây đắt hơn bốn phép đo, và ba trong bốn là về **cái
   thước**, không về thứ được đo:

   ① **Sai số của chính cái thước.** Sàn nhiễu ban đầu lấy từ **n = 4** lượt
      sinh. Độ lệch chuẩn ước từ 4 mẫu có sai số tương đối **41%**, nên ranh
      giới 4σ nằm gọn bên trong sai số. Đo được — cùng hỏng hóc, cùng bản gốc,
      **không đổi một dòng mã** giữa hai lượt: `duc_3k5` 12,1σ → 7,9σ;
      `lap_o_giua` 4,1σ → 3,2σ, tức *"đã đóng"* → *"còn mù"*. Tôi đã sửa chỉ số
      suốt hai lượt để đuổi theo những con số ấy. n = 24 đưa sai số về ~15%.

   ② **Với `lap_o_giua`, CER không những không tăng mà GIẢM** (0,0332 →
      0,0156) — bộ ASR nuốt gọn đoạn thừa. Niềm tin *"sai lệch văn bản sẽ lộ ra
      ở CER"* sai, và sai theo hướng trấn an.

   ③ **Một chỉ số chỉ chạy trên máy có GPU thì không phải một phần của cổng.**
      Nhánh F0 ban đầu gọi `librosa.pyin`; `librosa` không có ở python chạy
      gate, nên nhánh ấy trả `{}` **im lặng** và bánh cóc canh nó xanh cả khi
      tôi cố tình phá. Nay F0 tự cài bằng numpy.

   ④ **Khuôn thử tự tạo ra đúng hỏng hóc nó phải bắt — hai lần.** Tín hiệu giả
      dùng nhịp tuần hoàn ⇒ `khop_cuc_bo_dinh` = 1,0 ở bản NỀN; rồi dùng chung
      một bộ sóng hài cho mọi âm tiết ⇒ 0,99 ở bản nền. Tránh được cái bẫy
      "nhiễu trắng" rồi rơi vào cái bẫy đối xứng của nó: quá đều.

🔴 HAI ĐIỂM MÙ CÒN NGUYÊN, và cả hai đóng lại như **giới hạn đã đo**, không
   phải việc còn dở — vì cả hai đều nằm **dưới sàn nhiễu tự nhiên của giọng**:

     · **lệch tông 6%** — trong lượt sinh BÌNH THƯỜNG, cao độ nửa sau đã lệch
       nửa đầu **21%** (ngữ điệu, giọng xuống cuối câu). Hỏng hóc nhỏ hơn ngữ
       điệu ba lần rưỡi. Thêm chỉ số không cứu được; phải đợi nó lớn hơn.
     · **rung giọng 6% @ 5,5 Hz** — 5,5 Hz **trùng nhịp âm tiết** tiếng Việt.
       Ba cơ chế đã thử (năng lượng dải · độ nhọn trên bao · độ nhọn trên log
       bao), cao nhất 1,7σ. Và không có bằng chứng nào rằng VieNeu **sinh ra**
       hỏng hóc này — nó là hỏng hóc tôi nghĩ ra để biện minh cho jitter/shimmer.
       Upstream #159 báo lặp và trôi, không báo rung.

⇒ Nên cổng nói được: *"bắt được đục, nhiễu, vỡ tiếng, đứt quãng, lặp"*. Nó
  **không** nói được *"bắt được trôi tông"* — và ghi đúng như vậy đáng giá hơn
  một chỉ số nghe hay mà chưa từng vượt ngưỡng.

⚠️ TẤT CẢ đều là chỉ số **tương đối**. Chúng vào cổng V10 qua baseline ghim theo
   phiên bản, không qua một ngưỡng tuyệt đối — không có ngưỡng tuyệt đối nào
   đúng cho "độ sáng" của một giọng, vì một giọng trầm vốn tối hơn một giọng cao.
"""
from __future__ import annotations

import numpy as np

#: Khung phân tích chung. 20 ms là khung tiêu chuẩn cho RMS tiếng nói, cùng con
#: số `noi_dai.KHUNG_MS` dùng — hai khung khác nhau cho cùng một tín hiệu là hai
#: kết luận không đối chiếu được.
KHUNG_MS = 20.0

#: Ngưỡng coi một khung là CÓ TIẾNG, so với RMS lớn nhất của clip.
#: Mọi phép dưới đây chỉ tính trên khung có tiếng — tính cả khoảng lặng thì một
#: bản đọc nhiều nhịp nghỉ sẽ có "bao biên độ" dao động khủng khiếp mà không có
#: gì bất thường cả.
TY_LE_CO_TIENG = 0.12

#: Dải "sáng" — năng lượng TRÊN mốc này. 4 kHz, không phải 2 kHz.
#:
#: 🔴 Bản đầu để 2 kHz và MÙ HOÀN TOÀN với một bộ lọc thông thấp 3,5 kHz (1,4σ):
#:    dải tôi đo nằm **dưới** chỗ bị cắt nên còn nguyên vẹn. Một phép đo độ sáng
#:    chỉ thấy được thứ bị cắt khi nó nhìn **trên** chỗ cắt.
CAT_SANG_HZ = 4000.0

#: Ngưỡng năng lượng tích luỹ cho "tần số vắt". Dùng cả hai: 95% bám phần thân
#: phổ, 99% bám cái đuôi — và một bộ lọc thông thấp giết cái đuôi trước tiên.
VAT_TICH_LUY = (0.95, 0.99)

#: Dải nhịp điệu xét khi tìm rung giọng, Hz.
#: ⛔ Nhịp âm tiết tiếng Việt nằm ~4–7 Hz, tức TRÙNG dải rung giọng của người.
#:    Nên KHÔNG tách được rung khỏi nhịp nói bằng năng lượng dải — phải tách
#:    bằng **hình dạng đỉnh**: rung là một hình sin (đỉnh nhọn, một bin), nhịp
#:    nói là ngẫu nhiên (phổ tãi rộng).
DAI_NHIP_HZ = (2.0, 10.0)

#: Cửa sổ so khớp cục bộ khi tìm đoạn lặp, giây.
CUA_SO_LAP_S = 0.3

#: Khoảng độ trễ tìm đoạn lặp, giây. Dưới 0,25 s là bên trong một âm tiết; trên
#: 4 s thì hai đoạn xa nhau tới mức trùng lặp là ngẫu nhiên chứ không phải kẹt.
TRE_MIN_S = 0.25
TRE_MAX_S = 4.0

#: Cửa sổ đo F0 theo thời gian. Đủ dài để có nhiều chu kỳ, đủ ngắn để thấy trôi.
CUA_SO_F0_S = 1.0
F0_MIN, F0_MAX = 70.0, 400.0


def _khung_rms(wav, sr: int):
    n = max(1, int(sr * KHUNG_MS / 1000.0))
    du = len(wav) % n
    x = wav[:len(wav) - du] if du else wav
    if not len(x):
        return np.zeros(0, dtype=np.float64), n
    return np.sqrt((x.reshape(-1, n).astype(np.float64) ** 2).mean(axis=1)), n


def _mat_na_co_tieng(wav, sr: int):
    rms, n = _khung_rms(wav, sr)
    if not len(rms):
        return np.zeros(0, dtype=bool), rms, n
    return rms >= TY_LE_CO_TIENG * float(rms.max()), rms, n


def do_sang(wav, sr: int) -> dict:
    """Độ sáng phổ — bịt điểm mù **đục**.

    Ba số, và mỗi số hỏng theo một kiểu khác nhau:

      · `trong_tam_hz` — trọng tâm phổ. Dịch khi phổ **nghiêng** đi.
      · `vat_95_hz` / `vat_99_hz` — tần số mà dưới nó chứa 95% / 99% năng lượng.
        Bám thẳng **góc cắt** của một bộ lọc thông thấp.
      · `db_dai_cao` — năng lượng trên `CAT_SANG_HZ`, tính bằng **dB**.

    ⭐ `db_dai_cao` để ở thang dB chứ không phải tỉ lệ, và đó là điều làm nó
       dùng được. Năng lượng trên 4 kHz của tiếng nói vốn nhỏ (cỡ 1e-3); một
       bộ lọc kéo nó xuống 1e-6. Ở thang tuyến tính hai số ấy đều "gần 0" và
       khoảng cách bị sàn nhiễu nuốt; ở thang dB đó là **30 dB**.

    ⛔ Trọng tâm phổ MỘT MÌNH không đủ, và đây là số đo: với bộ lọc 3,5 kHz nó
       chỉ nhúc nhích 1,4σ, vì nó là trung bình có **trọng số năng lượng** và
       năng lượng tiếng nói dồn dưới 1 kHz. Nó bắt rất tốt một hỏng hóc khác
       (nhiễu trắng, 20,5σ) — nên giữ, nhưng đừng giao cho nó việc này.
    """
    x = np.asarray(wav, dtype=np.float64)
    if x.size < 2 or not sr:
        return {}
    co_tieng, _, n = _mat_na_co_tieng(x, sr)
    if not co_tieng.any():
        return {}
    kh = x[:len(co_tieng) * n].reshape(-1, n)[co_tieng].ravel()
    if kh.size < 256:
        return {}
    pho = np.abs(np.fft.rfft(kh * np.hanning(kh.size))) ** 2
    tan = np.fft.rfftfreq(kh.size, 1.0 / sr)
    tong = float(pho.sum())
    if tong <= 0:
        return {}
    ra = {"trong_tam_hz": round(float((pho * tan).sum() / tong), 1)}
    tich = np.cumsum(pho) / tong
    for m in VAT_TICH_LUY:
        i = int(np.searchsorted(tich, m))
        ra[f"vat_{int(m * 100)}_hz"] = round(
            float(tan[min(i, tan.size - 1)]), 1)
    cao = float(pho[tan >= CAT_SANG_HZ].sum())
    ra["db_dai_cao"] = round(float(10.0 * np.log10(cao / tong + 1e-12)), 3)
    return ra


def do_on_dinh_bien_do(wav, sr: int) -> dict:
    """Độ ổn định của bao biên độ — bịt điểm mù **run giọng**.

    Đây là phép gần nhất với "shimmer", và **cố ý không mang tên đó**: shimmer
    lâm sàng đo dao động biên độ giữa hai chu kỳ thanh môn liền kề trên một
    nguyên âm kéo dài. Đây đo trên tiếng nói chạy. Cùng ý tưởng, khác thang, và
    mang tên kia thì sẽ có người so nó với ngưỡng lâm sàng của phép đo khác.

    🔴 BÀI HỌC ĐẮT NHẤT CỦA K3 NẰM Ở ĐÂY. Bản đầu đo **năng lượng dải 3–8 Hz**
       của bao biên độ, vì đó là dải rung giọng của người. Nó mù hoàn toàn với
       một rung 6% tiêm ở 5,5 Hz (2,0σ, và nhúc nhích **sai chiều**). Hai lý do,
       cả hai đều mang tính nguyên tắc chứ không phải chỉnh tham số:

       ① 5,5 Hz **chính là nhịp âm tiết** tiếng Việt. Năng lượng trong dải ấy
          không phân biệt được "giọng run" với "đang nói". Không có mốc dải nào
          cứu được điều đó — chúng chồng lên nhau về mặt vật lý.
       ② Tôi ghép các khung **có tiếng** rời rạc lại rồi lấy phổ. Việc ấy **cắt
          bỏ các quãng lặng và dán hai đầu vào nhau**, tức phá trục thời gian —
          một hình sin đi qua đó không còn là hình sin.

    ⇒ Tách bằng **hình dạng đỉnh**, không bằng năng lượng dải: rung giọng là
      một hình sin (đỉnh cao, hẹp một hai bin), nhịp nói là ngẫu nhiên (phổ tãi
      rộng, không đỉnh trội). `do_nhon_nhip` = đỉnh / trung vị nền quanh nó.

    Trả `dao_dong_khung` (dao động khung-liền-khung, khung có tiếng — phép này
    không cần trục thời gian nên vẫn dùng mặt nạ), `do_nhon_nhip` và
    `nhip_troi_hz` (tần số của đỉnh, để đọc chẩn đoán).
    """
    x = np.asarray(wav, dtype=np.float64)
    co_tieng, rms, _ = _mat_na_co_tieng(x, sr)
    v = rms[co_tieng] if co_tieng.any() else np.zeros(0)
    ra: dict = {}
    if v.size >= 8 and float(v.mean()) > 0:
        ra["dao_dong_khung"] = round(
            float(np.abs(np.diff(v)).mean() / float(v.mean())), 5)

    # ⛔ Từ đây dùng bao LIÊN TỤC (mọi khung, giữ nguyên trục thời gian), KHÔNG
    #    dùng mặt nạ có-tiếng — xem lý do ② ở docstring.
    #
    # 🔴 VÀ DÙNG **LOGARIT** CỦA BAO, KHÔNG DÙNG BAO. Đây là chỗ bản thứ hai
    #    vẫn trượt (0 chỉ số qua ngưỡng) và lý do là toán học, không phải tham
    #    số:
    #
    #    Rung giọng là một hệ số NHÂN: `bao(t) · (1 + ε·sin ωt)`. Trên thang
    #    tuyến tính, biên độ của thành phần rung tại mỗi thời điểm tỉ lệ với
    #    chính `bao(t)` — tức hình sin bị **điều biên bởi nhịp nói**, và phổ của
    #    nó là tích chập của một vạch với cả dải nhịp âm tiết. Vạch bị **trải
    #    mỏng ra khắp dải**, đúng dải đông đúc nhất. Không có cách nào nhặt lại.
    #
    #    Lấy log thì phép nhân thành phép cộng: `log bao + log(1+ε sin) ≈
    #    log bao + ε·sin`. Thành phần rung trở lại là một vạch **biên độ hằng**,
    #    không dính gì tới nhịp nói. Không trải, không tích chập.
    #
    # ⚠️ Cần một SÀN trước khi lấy log: `log 0 = -inf`, và quãng lặng có rms ≈ 0.
    #    Sàn theo tỉ lệ với đỉnh nên nó bất biến với độ to.
    if rms.size >= 64 and float(rms.max()) > 0:
        lg = np.log(rms + 0.05 * float(rms.max()))
        # Bỏ phần chậm (nhịp câu, lên xuống giọng) bằng cách trừ trung bình
        # trượt — nếu không, năng lượng ở vài bin đầu át hết phần còn lại.
        m = max(3, int(0.4 / (KHUNG_MS / 1000.0)))
        if m % 2 == 0:
            m += 1
        cham = np.convolve(lg, np.ones(m) / m, mode="same")
        nhanh = lg - cham
        p = np.abs(np.fft.rfft(nhanh * np.hanning(nhanh.size)))
        f = np.fft.rfftfreq(nhanh.size, KHUNG_MS / 1000.0)
        dai = (f >= DAI_NHIP_HZ[0]) & (f <= DAI_NHIP_HZ[1])
        if dai.sum() >= 8:
            idx = np.flatnonzero(dai)
            j = int(idx[int(np.argmax(p[dai]))])
            # Nền = trung vị của dải, BỎ hai bin quanh đỉnh. Trung vị chứ không
            # phải trung bình: trung bình bị chính cái đỉnh kéo lên, làm tỉ số
            # tự bóp nhỏ đúng lúc nó cần lớn.
            nen_idx = idx[np.abs(idx - j) > 2]
            if nen_idx.size >= 4:
                nen = float(np.median(p[nen_idx]))
                ra["do_nhon_nhip"] = round(float(p[j] / max(nen, 1e-9)), 4)
                ra["nhip_troi_hz"] = round(float(f[j]), 2)
    return ra


def _f0_khung(x, sr: int):
    """F0 từng khung bằng tự tương quan chuẩn hoá. `(f0, huu_thanh)`.

    🔴 Tự cài thay vì gọi `librosa.pyin`, và lý do là một khuyết tật ĐÃ ĐO chứ
       không phải sở thích: `librosa` **không có** trong python chạy gate. Nhánh
       F0 vì thế trả `{}` khi chạy test, nên `test_khong_tra_ra_cai_dem` xanh cả
       khi tôi cố tình nhét lại một cái đếm vào — một bánh cóc rỗng nghĩa.

    ⛔ Một chỉ số chất lượng chỉ đo được trên máy có GPU thì không phải một phần
       của cổng chất lượng; nó là một ghi chú. Cổng phải chạy được ở mọi nơi
       hoặc nó không chốt được gì.

    Đây là phép đơn giản hơn pyin nhiều (không có bước Viterbi, không hậu
    nghiệm), và điều đó chấp nhận được vì ta chỉ dùng **trung vị** của những
    khung hữu thanh — một phép thống kê bền với khung sai lẻ tẻ.
    """
    n = int(sr * 0.040)
    h = int(sr * 0.010)
    if x.size < n + h or n < 32:
        return np.zeros(0), np.zeros(0, dtype=bool)
    lo = max(2, int(sr / F0_MAX))
    hi = min(n - 2, int(sr / F0_MIN))
    if hi <= lo:
        return np.zeros(0), np.zeros(0, dtype=bool)

    so = 1 + (x.size - n) // h
    idx = np.arange(n)[None, :] + h * np.arange(so)[:, None]
    K = x[idx].astype(np.float64)
    K -= K.mean(axis=1, keepdims=True)
    nl = (K ** 2).sum(axis=1)

    # tự tương quan qua FFT cho cả loạt khung một lần
    m = 1 << int(np.ceil(np.log2(2 * n)))
    A = np.fft.irfft(np.abs(np.fft.rfft(K, m, axis=1)) ** 2, m, axis=1)[:, :hi + 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        A = A / np.maximum(nl[:, None], 1e-12)
    A[:, :lo] = 0.0
    j = A.argmax(axis=1)
    dinh = A[np.arange(so), j]
    huu = (dinh >= 0.35) & (j > 0) & (nl > 1e-9)
    f0 = np.where(j > 0, sr / np.maximum(j, 1), 0.0)
    return f0, huu


def do_on_dinh_f0(wav, sr: int) -> dict:
    """Độ ổn định cao độ theo thời gian.

    ⭐ Vì sao có nó khi đã có `on_dinh_giong`: cosine giữa hai embedding người
       nói khá **bất biến với cao độ** — đó là mục đích của embedding ấy — nên
       một bản đổi tông chỉ làm nó nhúc nhích. F0 thấy thẳng.

    ⚠️ NHƯNG NÓ **KHÔNG** ĐÓNG ĐƯỢC ĐIỂM MÙ MÀ NÓ SINH RA ĐỂ ĐÓNG, và con số
       nói rõ vì sao. Đo trên tiếng thật, n = 24 lượt sinh bình thường:

           f0_lech_nua (nửa sau so nửa đầu), lượt BÌNH THƯỜNG:  **0,2109**

       Tức trong một lượt sinh **không có lỗi gì**, cao độ nửa sau đã lệch nửa
       đầu **21%** — đó là ngữ điệu, giọng xuống ở cuối câu. Hỏng hóc tiêm vào
       là 6%. Nó nhỏ hơn ngữ điệu bình thường ba lần rưỡi, và nó chỉ đẩy chỉ số
       lên 1,4σ trong khi ngưỡng là 4σ.

    ⇒ Giữ lại vì nó là phép đo cao độ trực tiếp duy nhất và rẻ, nhưng **đừng
      ghi vào tài liệu rằng cổng bắt được trôi tông 6%**. Cổng bắt được trôi
      tông khi nó lớn hơn ngữ điệu, chứ không phải khi nó nhỏ hơn.

    ⛔ Trung vị, không phải trung bình: F0 của khung vô thanh là rác, và một
       khung rác kéo trung bình đi rất xa.
    """
    x = np.asarray(wav, dtype=np.float64)
    if x.size < sr * 2 or not sr:
        return {}
    f0, huu = _f0_khung(x, sr)
    if huu.sum() < 24:
        return {}
    tb = float(np.median(f0[huu]))
    if tb <= 0:
        return {}
    ra = {"f0_trung_vi_hz": round(tb, 1)}

    nua = f0.size // 2
    a1, a2 = f0[:nua][huu[:nua]], f0[nua:][huu[nua:]]
    if a1.size >= 12 and a2.size >= 12:
        ra["f0_lech_nua"] = round(
            float(abs(np.median(a2) - np.median(a1)) / tb), 5)

    nk = max(1, int(round(CUA_SO_F0_S / 0.010)))
    tv = [float(np.median(f0[i:i + nk][huu[i:i + nk]]))
          for i in range(0, f0.size - nk + 1, nk)
          if huu[i:i + nk].sum() >= 8]
    if len(tv) >= 3:
        k = len(tv)
        xm = (k - 1) / 2.0
        mau = sum((i - xm) ** 2 for i in range(k))
        mtb = float(np.mean(tv))
        doc = (sum((i - xm) * (tv[i] - mtb) for i in range(k)) / mau) if mau else 0.0
        # Chuẩn hoá theo chính F0 của giọng: 5 Hz trên một giọng 90 Hz là nhiều,
        # trên một giọng 220 Hz là ít.
        ra["f0_tan_tuong_doi"] = round(float(np.std(tv) / tb), 5)
        ra["f0_doc_tuong_doi"] = round(float(doc / tb), 5)
    return ra


def do_lap_bat_ky(wav, sr: int) -> dict:
    """Đoạn nào trong bản lặp lại đoạn nào — bịt điểm mù **lặp ở giữa**.

    `chot_sinh.chot_lap_duoi` chỉ so hai cửa sổ **cuối**, vì lỗi kinh điển của
    model tự hồi quy là kẹt ở đuôi. Nhưng upstream `pnnbao97/VieNeu-TTS` #159
    báo **hai** kiểu: lặp câu, và *"chèn thêm câu không liên quan vào GIỮA"*.

    ⛔ Và `cer` không đỡ được kiểu thứ hai. Đo 01/09: chèn 0,5 s lặp vào giữa
       làm CER **giảm** (0,0332 → 0,0156) — bộ ASR nuốt gọn đoạn thừa. Niềm tin
       "sai lệch văn bản sẽ lộ ra ở CER" sai, và sai theo hướng trấn an.

    Hai phép, vì hai hiện tượng khác nhau:

      · `tu_tuong_quan_dinh` — tự tương quan **toàn cục** của bao biên độ. Bắt
        thay đổi ở **hình dạng tổng thể** (đứt quãng 1,5 s: 10,6σ).
      · `khop_cuc_bo_dinh` — độ khớp **cục bộ** cao nhất giữa hai cửa sổ
        `CUA_SO_LAP_S` giây cách nhau `[TRE_MIN_S, TRE_MAX_S]`.

    🔴 Phải có phép thứ hai, và lý do là số học: một đoạn trùng 0,5 s trong một
       bản 6 giây chỉ chiếm ~8% tín hiệu. Tương quan toàn cục **trung bình hoá**
       nó với 92% còn lại, nên một bản sao y nguyên chỉ nhích tương quan lên vài
       phần trăm. Đo bằng phép toàn cục, `lap_o_giua` nằm im dưới ngưỡng. Phép
       cục bộ lấy **cực đại** thay vì trung bình, nên một đoạn trùng dù ngắn vẫn
       đẩy nó về gần 1,0.

    ⚠️ Tiếng nói tự nhiên lặp nhịp (nhịp âm tiết), nên cả hai số KHÔNG bao giờ
       bằng 0. Chúng chỉ có nghĩa khi so với sàn nhiễu của chính giọng ấy — đúng
       lý do chúng vào cổng qua baseline ghim, không qua ngưỡng gõ tay.
    """
    x = np.asarray(wav, dtype=np.float64)
    rms, _ = _khung_rms(x, sr)
    if rms.size < 32 or not sr:
        return {}
    v = rms - rms.mean()
    chuan = float(np.dot(v, v))
    if chuan <= 0:
        return {}
    khung_s = KHUNG_MS / 1000.0
    lo = max(1, int(TRE_MIN_S / khung_s))
    hi = min(v.size - 8, int(TRE_MAX_S / khung_s))
    if hi <= lo:
        return {}

    tot, tre = 0.0, 0
    for d in range(lo, hi):
        c = float(np.dot(v[:-d], v[d:]) / chuan)
        if c > tot:
            tot, tre = c, d
    ra = {"tu_tuong_quan_dinh": round(tot, 5),
          "tre_dinh_s": round(tre * khung_s, 3)}

    ra.update(_khop_cuc_bo(x, sr))
    return ra


def _pho_bang(x, sr: int, so_dai: int = 24):
    """Phổ theo băng log, mỗi khung chuẩn hoá về vector đơn vị. `(B, buoc_s)`.

    Tự cài bằng numpy chứ không gọi `librosa`, vì phép này phải chạy được trong
    gate — nơi `librosa` không có. Một chỉ số chỉ đo được ở máy có GPU thì không
    phải một phần của cổng chất lượng, nó là một ghi chú.
    """
    n = int(sr * 0.025)
    h = int(sr * 0.010)
    if x.size < n + h or n < 16:
        return None, 0.0
    so = 1 + (x.size - n) // h
    idx = np.arange(n)[None, :] + h * np.arange(so)[:, None]
    P = np.abs(np.fft.rfft(x[idx] * np.hanning(n), axis=1)) ** 2
    f = np.fft.rfftfreq(n, 1.0 / sr)
    canh = np.geomspace(80.0, min(8000.0, sr / 2 * 0.95), so_dai + 1)
    B = np.zeros((so, so_dai))
    for i in range(so_dai):
        m = (f >= canh[i]) & (f < canh[i + 1])
        if m.any():
            B[:, i] = P[:, m].sum(axis=1)
    nl = B.sum(axis=1)                      # năng lượng mỗi khung, TRƯỚC log
    B = np.log(B + 1e-10)
    # 🔴 TRỪ HÌNH PHỔ TRUNG BÌNH THEO THỜI GIAN trước đã. Không có dòng này thì
    #    thứ chi phối mỗi vector khung là **độ nghiêng phổ chung của tiếng nói**
    #    — năng lượng giảm dần theo tần số — và mọi khung đều mang nó. Đo được:
    #    cosine giữa **hai khung bất kỳ** là **0,87**, nên mọi cửa sổ khớp mọi
    #    cửa sổ và phép đo không còn phân giải nào.
    #
    #    Đây chính là phép trừ trung bình cepstral (CMN) mà nhận dạng tiếng nói
    #    dùng, và vì đúng lý do ấy: cái chung không mang thông tin phân biệt.
    co = nl >= TY_LE_CO_TIENG ** 2 * float(nl.max() or 1.0)
    # ⛔ Lấy trung bình trên khung CÓ TIẾNG, không trên mọi khung. Quãng lặng
    #    chiếm ~30% và có hình phổ rất khác, nên nó kéo lệch cái trung bình; trừ
    #    một trung bình lệch thì mọi khung có tiếng vẫn còn chung một phần lớn.
    #    Đo được: trừ trung bình toàn cục thì cosine giữa hai khung **có tiếng**
    #    bất kỳ vẫn là **0,804**; trừ trung bình của riêng khung có tiếng thì nó
    #    về gần 0 và đoạn lặp mới nổi lên trên nền.
    B -= B[co].mean(axis=0, keepdims=True) if co.any() else B.mean(axis=0, keepdims=True)
    B -= B.mean(axis=1, keepdims=True)
    B /= np.maximum(np.linalg.norm(B, axis=1, keepdims=True), 1e-9)
    return B, h / float(sr), co


def _khop_cuc_bo(wav, sr: int) -> dict:
    """Độ khớp cục bộ cao nhất giữa hai đoạn cách nhau `[TRE_MIN_S, TRE_MAX_S]`.

    🔴 So bằng **PHỔ**, không bằng bao biên độ — và đây là bản thứ hai, vì bản
       đầu (bao biên độ) hỏng theo một kiểu rất dễ tưởng là đã chạy:

           `khop_cuc_bo_dinh` trên lượt sinh BÌNH THƯỜNG = **0,9706**

       Tức tiếng nói thật tự khớp gần như hoàn hảo ở đâu đó, và một đoạn lặp
       thật chỉ đẩy nó lên 1,0 — không còn chỗ để phân biệt. Nguyên nhân: hai
       âm tiết **khác hẳn nhau** nhưng cùng đường lên-xuống độ to thì bao biên
       độ của chúng giống nhau. Bao biên độ đo *nhịp*, không đo *nội dung*.

    ⇒ Phổ theo băng log phân biệt được /ba/ với /ma/; bao biên độ thì không.
      Một đoạn lặp nguyên văn khớp ở **cả hai**, nên chỉ phổ mới có biên độ
      động để nói lên điều đó.

    ⛔ Chuẩn hoá **từng khung** về vector đơn vị sau khi trừ trung bình băng:
       không làm vậy thì hai quãng cùng to lại khớp cao chỉ vì cùng to — đúng
       cái bẫy đã làm hỏng bản đầu, chỉ chuyển sang trục khác.
    """
    B, buoc, co = _pho_bang(np.asarray(wav, dtype=np.float64), sr)
    if B is None or B.shape[0] < 40:
        return {}
    m = max(8, int(CUA_SO_LAP_S / buoc))
    lo, hi = int(TRE_MIN_S / buoc), int(TRE_MAX_S / buoc)
    if B.shape[0] < m + lo:
        return {}
    # 🔴 CHỈ SO NHỮNG CỬA SỔ CHỦ YẾU LÀ TIẾNG. Đây là bản thứ ba, và hai bản
    #    trước đều hỏng vì cùng một điều bị bỏ qua: **quãng lặng khớp quãng lặng
    #    một cách hoàn hảo.** Nó không nói gì cả — nhưng nó thắng phép lấy cực
    #    đại, nên `khop_cuc_bo_dinh` ở lượt sinh bình thường bám 0,97 và không
    #    còn biên độ động cho một đoạn lặp thật.
    #
    #    Đo được: bản không lọc cho nền 0,9706 trên tiếng thật (n=24) và 0,975
    #    trên khuôn thử. Cả hai đều là "im lặng so với im lặng", không phải
    #    "giọng tự lặp".
    buoc_cs = max(1, m // 4)
    dau = [i for i in range(0, B.shape[0] - m + 1, buoc_cs)
           if co[i:i + m].mean() >= 0.7]
    if len(dau) < 2:
        return {}
    tot, cap = -1.0, None
    for i in dau:
        a = B[i:i + m]
        for j in dau:
            d = j - i
            if d < lo or d > hi or j + m > B.shape[0]:
                continue
            c = float((a * B[j:j + m]).sum() / m)
            if c > tot:
                tot, cap = c, (i, d)
    if cap is None:
        return {}
    return {"khop_cuc_bo_dinh": round(tot, 5),
            "khop_cuc_bo_tai_s": round(cap[0] * buoc, 3),
            "khop_cuc_bo_tre_s": round(cap[1] * buoc, 3)}


def do_tat_ca(wav, sr: int) -> dict:
    """Cả bốn phép, làm phẳng thành một dict số. Phép nào không đo được thì vắng.

    ⛔ Vắng mặt KHÁC 0. Một phép không đo được (clip quá ngắn, thiếu `librosa`)
       phải **không có trong dict**, để tầng trên phân biệt được "đo rồi, bằng
       0" với "chưa đo". Cùng bài học với `snr_db` từng bị `or 0.0` biến "không
       đo được" thành "đo được, bằng 0".
    """
    ra: dict = {}
    for ham in (do_sang, do_on_dinh_bien_do, do_on_dinh_f0, do_lap_bat_ky):
        try:
            ra.update(ham(wav, sr) or {})
        except Exception:                    # noqa: BLE001
            # Một phép hỏng không được làm hỏng ba phép kia, nhưng nó cũng
            # không được im lặng thành 0 — nó đơn giản vắng mặt.
            continue
    return ra
