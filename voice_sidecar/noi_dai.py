r"""
noi_dai.py — ghép nhiều lượt sinh thành MỘT bản đọc liền mạch.

## Bài toán thật, sau khi đã đo

Văn bản dài hơn `TRAN_KY_TU_MOT_LUOT` phải chia thành nhiều lượt `infer` riêng.
Ba câu hỏi hay bị gộp làm một, nhưng chúng khác hẳn nhau:

  ① **Có còn là một người nói không?**
     ✅ ĐÃ TRẢ LỜI BẰNG SỐ ĐO, không phải suy luận
     (`voice_sidecar/do_giu_giong_nhieu_luot.py`, 31/08/2026, giọng mặc định):

         hai nửa của CÙNG một lượt (sàn nhiễu) : 0,8524   (thấp nhất 0,8271)
         giữa các LƯỢT GỌI riêng               : 0,9254   (thấp nhất 0,8800)

     Giữa các lượt còn giống nhau **hơn** hai nửa của một lượt. Giọng mặc định
     ổn định qua các lượt, nên chia lượt **không** làm đổi người nói và không
     cần ghim tham chiếu để giữ danh tính.

  ② **Mối nối nghe có liền không?** ← việc của tệp này
  ③ Ngữ điệu có lệch giữa các đoạn không? — upstream #173 nói `temperature` gây
     lệch tông. Không sửa được ở tầng ghép; nó thuộc cổng V10.

## Ba việc tệp này làm, và vì sao từng việc

**1. Cắt im ở mối nối.** Mỗi lượt sinh đã tự mang im ở đầu và cuối. Nối thẳng
   thì hai khoảng im cộng lại, và người nghe nghe thấy một quãng ngắt bất
   thường đúng chỗ ta cắt — tức chỗ cắt **tự khai ra**.

**2. Nhịp nghỉ ĐO ĐƯỢC, không phải hằng số gõ tay.**

   ⭐ Đây là chỗ dễ làm sai nhất. Một hằng số như `0,35 giây` nghe hợp lý và
      **không có nguồn nào cả**: nó không đến từ model, không đến từ ngữ âm
      tiếng Việt, chỉ đến từ cảm giác của người viết mã.

      Model đã biết nghỉ bao lâu giữa hai câu — nó làm việc đó suốt, **bên
      trong** mỗi lượt, vì engine tự chia chunk 256 ký tự và tự ghép
      (`tham_so.MAX_CHARS_CHUNK`). Nên nhịp nghỉ đúng ở mối nối của TA chính là
      nhịp nghỉ mà model tự đặt ở mối nối của NÓ. Đo trung vị các khoảng lặng
      giữa trong chính các đoạn vừa sinh, rồi dùng lại đúng con số đó.

      Tự hiệu chuẩn theo từng bản đọc, và không có con số nào phải bảo vệ.

**3. Cân độ to, có kẹp.** Mỗi lượt sinh độc lập nên mức có thể lệch nhau; mối
   nối khi đó nghe như đổi micro. Cân từng đoạn về **trung vị** của cả bản.

   ⛔ Kẹp ở `±KEP_CHINH_DB`. Không kẹp thì một đoạn vốn nhỏ tiếng **vì nội dung
      của nó** (câu thì thầm, câu kết) sẽ bị kéo to bằng phần còn lại — tức ta
      sửa đúng thứ model cố ý làm. Kẹp biến phép cân thành "sửa trôi mức", chứ
      không thành "san phẳng diễn cảm".

⛔ KHÔNG chuẩn hoá về một mốc LUFS tuyệt đối ở đây. Bản đo 31/08 cho −18,6 LUFS,
   nằm trong dung sai đã công bố; kéo nó về một mốc là thêm một tầng xử lý mà
   không ai yêu cầu, và nó sẽ che mất việc model đang trôi mức thật.
"""
from __future__ import annotations

import numpy as np

#: Ngưỡng coi là im. Cùng con số với `do_chat_luong.NGUONG_IM_DBFS` — hai
#: ngưỡng khác nhau cho hai công cụ nói về cùng một thứ là hai kết luận không
#: đối chiếu được.
NGUONG_IM_DBFS = -50.0

#: Khung phân tích. 20 ms là khung tiêu chuẩn cho RMS tiếng nói.
KHUNG_MS = 20.0

#: Nhịp nghỉ dùng khi **không đo được** (bản đọc chỉ có một câu mỗi đoạn, nên
#: không có khoảng lặng giữa nào để lấy trung vị). Lấy đúng biên dưới của
#: khoảng nghỉ câu trong tiếng nói tự nhiên; nó là lối lui, không phải mặc định.
NGHI_LUI_S = 0.30

#: Trần cho nhịp nghỉ đo được. Một bản đọc có sẵn quãng nghỉ dài (đoạn xuống
#: dòng, danh sách) sẽ đẩy trung vị lên; nhân đôi nó ở mọi mối nối biến bản đọc
#: thành rời rạc.
NGHI_TOI_DA_S = 0.80

#: Kẹp chỉnh độ to, dB. Xem lý do ở đầu tệp.
KEP_CHINH_DB = 3.0

#: 🔴 TRẦN ĐỈNH THẬT. Cùng con số với `do_chat_luong.TRAN_TRUE_PEAK_DBTP` —
#:    EBU R128 / ITU-R BS.1770-4.
#:
#:    ĐÂY LÀ MỘT BẢO ĐẢM, KHÔNG PHẢI MỘT LỰA CHỌN THẨM MỸ, và tệp này là nơi
#:    duy nhất còn cầm cả tín hiệu nên nó là nơi duy nhất bảo đảm được.
#:
#: ⚠️ Vì sao nó có mặt: đo 31/08/2026, bản ghép 4.920 ký tự (4 đoạn) ra
#:    **−0,65 dBTP** — VƯỢT trần, trong khi bản một đoạn cùng ngày là −1,10.
#:    Phép cân độ to ở trên kéo một đoạn lên tới +3 dB mà không hề nhìn khoảng
#:    dư còn lại. Nó **không** lộ ra ở bản ngắn: một đoạn thì không có gì để
#:    cân, nên lỗi chỉ xuất hiện đúng ở cấu hình mới xây.
TRAN_TRUE_PEAK_DBTP = -1.0


def dinh_that(wav) -> float:
    """Đỉnh thật (dBTP): đỉnh của tín hiệu sau khi tăng mẫu 4 lần.

    Đỉnh giữa hai mẫu có thể cao hơn mọi mẫu — đó chính là thứ BS.1770 đo, và
    là thứ làm vỡ tiếng ở bộ chuyển đổi của người nghe dù tệp trông sạch. Thiếu
    scipy thì lui về đỉnh mẫu và **báo thấp hơn thật**; đó là lối lui an toàn
    hơn là bỏ qua phép kiểm.
    """
    if not len(wav):
        return -np.inf
    try:
        from scipy.signal import resample_poly
        dinh = float(np.max(np.abs(resample_poly(wav, 4, 1))))
    except Exception:      # noqa: BLE001 - khong co scipy thi bao dinh mau
        dinh = float(np.max(np.abs(wav)))
    if dinh <= 0:
        return -np.inf
    return 20.0 * float(np.log10(dinh))


def _khung_rms(wav, sr: int):
    n = max(1, int(sr * KHUNG_MS / 1000.0))
    du = len(wav) % n
    x = wav[:len(wav) - du] if du else wav
    if not len(x):
        return np.zeros(0, dtype=np.float64), n
    return np.sqrt((x.reshape(-1, n).astype(np.float64) ** 2).mean(axis=1)), n


def _mat_na_im(wav, sr: int):
    rms, n = _khung_rms(wav, sr)
    return rms < (10 ** (NGUONG_IM_DBFS / 20.0)), n


def khoang_lang_giua(wav, sr: int) -> list:
    """Độ dài (giây) của từng khoảng lặng **giữa**, bỏ im đầu và im cuối."""
    im, n = _mat_na_im(wav, sr)
    if not len(im):
        return []
    giay_khung = n / float(sr)
    dau = 0
    while dau < len(im) and im[dau]:
        dau += 1
    cuoi = 0
    while cuoi < len(im) and im[len(im) - 1 - cuoi]:
        cuoi += 1
    if dau + cuoi >= len(im):
        return []
    ra, hien = [], 0
    for v in im[dau:len(im) - cuoi]:
        if v:
            hien += 1
        else:
            if hien:
                ra.append(hien * giay_khung)
            hien = 0
    if hien:
        ra.append(hien * giay_khung)
    return ra


def cat_im_hai_dau(wav, sr: int):
    """Bỏ im ở đầu và cuối. Trả mảng đã cắt (có thể rỗng nếu toàn im)."""
    im, n = _mat_na_im(wav, sr)
    if not len(im):
        return wav
    dau = 0
    while dau < len(im) and im[dau]:
        dau += 1
    cuoi = len(im)
    while cuoi > dau and im[cuoi - 1]:
        cuoi -= 1
    if dau >= cuoi:
        return wav[:0]
    return wav[dau * n:cuoi * n]


def nhip_nghi(wavs, sr: int, so_cau=None) -> tuple:
    """Nhịp nghỉ nên đặt ở mối nối, ĐO từ chính các đoạn. Trả `(giây, nguồn)`.

    🔴 LẤY TRUNG VỊ MỌI KHOẢNG LẶNG LÀ SAI, VÀ SAI RẤT XA.

       Bản đầu làm đúng thế. Đo 31/08/2026 trên bản 2.907 ký tự: trung vị của
       **214** khoảng lặng ra **0,04 giây**. Bốn mươi mili-giây không phải nhịp
       nghỉ giữa hai câu — đó là khe giữa hai TỪ. Ở ngưỡng −50 dBFS với khung
       20 ms, đại đa số khoảng lặng trong một bản đọc là khe từ, nên trung vị bị
       chúng nuốt trọn. Đặt 0,04 s ở mối nối là nối gần như dính liền.

       ⭐ Con số trông "đo được" nên nó qua được mắt tôi — chỉ có bản in ra mới
          nói thật. Đây chính là lý do hồ sơ phép ghép được đưa vào header.

    ⭐ Cách sửa KHÔNG dùng thêm một ngưỡng gõ tay ("chỉ tính khoảng > 150 ms" là
       đổi một con số vô căn cứ lấy một con số vô căn cứ khác). Dùng thứ đã biết
       chắc: đoạn được chia **theo ranh giới câu**, nên một đoạn có `S` câu thì
       có đúng `S − 1` ranh giới câu bên trong nó — và chúng là `S − 1` khoảng
       lặng DÀI NHẤT của đoạn đó. Lấy trung vị riêng nhóm ấy.

    `so_cau` là số câu của từng đoạn. Không truyền thì lui về trung vị toàn bộ,
    kèm cảnh báo trong `nguon` — vì con số đó gần như chắc chắn quá ngắn.
    """
    ranh_gioi = []
    tat_ca = []
    for i, w in enumerate(wavs):
        lang = sorted(khoang_lang_giua(w, sr), reverse=True)
        tat_ca.extend(lang)
        if so_cau is None or i >= len(so_cau):
            continue
        k = max(0, int(so_cau[i]) - 1)
        ranh_gioi.extend(lang[:k])

    if ranh_gioi:
        tv = float(np.median(ranh_gioi))
        mo_ta = f"do duoc tu {len(ranh_gioi)} ranh gioi cau"
    elif tat_ca:
        tv = float(np.median(tat_ca))
        mo_ta = (f"UOC THO tu {len(tat_ca)} khoang lang bat ky (khong biet so "
                 f"cau) — con so nay thien ve khe TU, thuong qua ngan")
    else:
        return NGHI_LUI_S, "lui (khong do duoc khoang lang giua nao)"

    if tv > NGHI_TOI_DA_S:
        return NGHI_TOI_DA_S, f"{mo_ta}: {tv:.3f}s, kep xuong tran"
    if tv < NGHI_LUI_S:
        # Ngắn hơn cả lối lui thì gần như chắc chắn ta đang đo nhầm loại khoảng
        # lặng. Lui, và nói ra — im lặng ở đây là cách một mối nối dính liền đi
        # thẳng tới tai khách.
        return NGHI_LUI_S, f"{mo_ta}: {tv:.3f}s < loi lui, dung loi lui"
    return tv, mo_ta


def _rms_hieu_dung(wav, sr: int) -> float:
    """RMS của phần **có tiếng** thôi. Tính cả phần im thì một đoạn nhiều
    khoảng nghỉ sẽ bị coi là nhỏ tiếng và bị kéo to lên oan."""
    im, n = _mat_na_im(wav, sr)
    if not len(im) or im.all():
        return 0.0
    rms, _ = _khung_rms(wav, sr)
    co_tieng = rms[~im]
    return float(np.sqrt((co_tieng ** 2).mean())) if len(co_tieng) else 0.0


def can_do_to(wavs, sr: int) -> tuple:
    """Cân các đoạn về trung vị, kẹp ±`KEP_CHINH_DB`. Trả `(wavs, [dB đã chỉnh])`."""
    muc = [_rms_hieu_dung(w, sr) for w in wavs]
    hop_le = [m for m in muc if m > 0]
    if len(hop_le) < 2:
        return list(wavs), [0.0] * len(wavs)
    dich = float(np.median(hop_le))
    ra, da_chinh = [], []
    for w, m in zip(wavs, muc):
        if m <= 0:
            ra.append(w)
            da_chinh.append(0.0)
            continue
        db = 20.0 * np.log10(dich / m)
        db = float(np.clip(db, -KEP_CHINH_DB, KEP_CHINH_DB))
        ra.append((w * (10.0 ** (db / 20.0))).astype(np.float32))
        da_chinh.append(round(db, 2))
    return ra, da_chinh


def ghep(wavs, sr: int, so_cau=None) -> tuple:
    """Ghép các đoạn thành một mảng float32. Trả `(wav, chi_tiet)`.

    `chi_tiet` là hồ sơ của phép ghép — nhịp nghỉ dùng, nó đến từ đâu, và mỗi
    đoạn bị chỉnh bao nhiêu dB. Nó đi vào header phản hồi để khi một bản đọc
    nghe lạ thì còn truy được, thay vì phải chạy lại rồi đoán.
    """
    ds = [np.asarray(w, dtype=np.float32) for w in wavs if w is not None and len(w)]
    if not ds:
        return np.zeros(0, dtype=np.float32), {"so_doan": 0}
    if len(ds) == 1:
        return ds[0], {"so_doan": 1, "nghi_s": 0.0, "nguon_nghi": "khong can ghep"}

    nghi, nguon = nhip_nghi(ds, sr, so_cau=so_cau)
    can, da_chinh = can_do_to(ds, sr)
    da_cat = [cat_im_hai_dau(w, sr) for w in can]
    da_cat = [w for w in da_cat if len(w)]
    if not da_cat:
        return np.zeros(0, dtype=np.float32), {"so_doan": 0}

    lang = np.zeros(int(round(nghi * sr)), dtype=np.float32)
    manh, moc, cho = [], [], 0
    for i, w in enumerate(da_cat):
        if i:
            manh.append(lang)
            cho += len(lang)
        # 🔴 MỐC BẮT ĐẦU CỦA TỪNG ĐOẠN TRONG BẢN ĐÃ GHÉP.
        #
        #    Hàm này biết chính xác từng đoạn nằm ở đâu — nó vừa xếp chúng —
        #    nhưng trước 01/09 nó không nói ra. Hệ quả: bất cứ ai muốn đo lại
        #    **từng đoạn** trong bản ghép đều phải **chia đều** mà đoán, và chia
        #    đều thì sai LUỸ TIẾN vì mỗi mối nối chèn thêm `nghi` giây.
        #
        # ⛔ Cái sai đó không hiền: nó lệch dần theo chỉ số đoạn, nên nó sinh ra
        #    đúng hình dạng một **xu hướng đơn điệu**. Phép đo trôi tông đầu tiên
        #    (01/09) đọc ra "−5,05 Hz mỗi đoạn, có hướng, vượt sàn nhiễu" — một
        #    kết luận nghe rất chắc, và nó có thể hoàn toàn là hiện vật của phép
        #    cắt. Một dụng cụ hỏng cho ra thứ **đọc lên y hệt một phát hiện**.
        moc.append(cho / float(sr) if sr else 0.0)
        manh.append(w)
        cho += len(w)
    ra = np.concatenate(manh).astype(np.float32)

    # ── bảo đảm trần đỉnh, SAU khi đã ghép ──────────────────────────────────
    #
    # Hạ cả bản một lượng duy nhất, không nén, không kẹp từng đoạn: hạ đều giữ
    # nguyên tương quan giữa các đoạn — tức giữ nguyên thứ phép cân ở trên vừa
    # làm — còn nén hay kẹp thì tạo méo mới ngay tại chỗ ồn nhất.
    tp = dinh_that(ra)
    ha_db = 0.0
    if np.isfinite(tp) and tp > TRAN_TRUE_PEAK_DBTP:
        ha_db = TRAN_TRUE_PEAK_DBTP - tp
        ra = (ra * (10.0 ** (ha_db / 20.0))).astype(np.float32)

    return ra, {
        "so_doan": len(da_cat),
        # Mốc bắt đầu + mốc kết thúc, `len+1` phần tử — cùng khuôn với một mảng
        # ranh giới, để người đọc cắt được `[moc[i], moc[i+1]]` mà không phải
        # cộng độ dài lấy từ nơi khác.
        "moc_s": [round(float(x), 4) for x in moc] +
                 [round(len(ra) / float(sr), 4) if sr else 0.0],
        "nghi_s": round(float(nghi), 3),
        "nguon_nghi": nguon,
        "chinh_do_to_db": da_chinh,
        "dinh_truoc_dbtp": round(float(tp), 2) if np.isfinite(tp) else None,
        "ha_tran_db": round(ha_db, 2),
    }
