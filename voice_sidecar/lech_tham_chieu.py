r"""
lech_tham_chieu.py — đo bản sinh ra LỆCH bao nhiêu so với chính clip tham chiếu
của giọng đó. (K4, tầng SỐ LIỆU.)

## Vì sao đây là một trục MỚI, không phải một con số nữa

Cổng chất lượng V10 hiện so bản sinh ra với một **baseline corpus** — một mức
trung bình của hệ thống. Nó trả lời *"bản này có bất thường so với hệ thống
không"*.

Nó **không** trả lời câu hỏi trung tâm của một sản phẩm nhân bản giọng:
*"bản này có giống giọng nó nhận là nhân bản không?"*

Ta mới có **một** phần của câu ấy — `do_chat_luong.do_giu_giong` tính cosine
giữa hai embedding người nói. Và chính nó tự khai giới hạn của mình:

    "Dùng CHÍNH bộ mã hoá của VieNeu, nên đây là phép TỰ ĐỐI CHIẾU: nó đo đúng
     thứ model coi là 'cùng một giọng', và vì thế KHÔNG thấy được chỗ chính bộ
     mã hoá mù."

⭐ Đó là lập luận cho tệp này, và nó cụ thể chứ không phải "đo thêm cho chắc":
   các phép dưới đây đo **tính chất âm học** — độ sáng phổ, cao độ, nhịp nghỉ —
   **độc lập với embedding**. Nếu embedding nói "cùng người" trong khi độ sáng
   tụt 6 dB thì có một thứ nó không nhìn thấy, và ta thấy.

## Kế thừa từ hệ cũ, và ba phần bị BỎ

Hệ cũ (`D:\Voiceclone_TTS/src/diagnostics`) có 25 luật R01–R25. Đối chiếu từng
luật với VieNeu:

    nhóm                         luật              dùng được?
    sức khoẻ checkpoint vocoder  R01a/b/c          ❌ ta không train
    kho tham chiếu nhiều clip    R02–R04, R06      ❌ K2 đã đo: gộp LÀM HỎNG
    dữ liệu huấn luyện           R08–R10           ❌ zero-shot
    núm chỉnh của F5             R21, R22          ❌ v3 Turbo bỏ `style`
    rò chú thích tham chiếu      R24               ❌ VieNeu không nhận văn bản
    **lệch so với tham chiếu**   **R11–R17**       ✅ tệp này
    tín hiệu đầu ra              R18–R20, R23, R25 ✅ đã có (K1 + cổng V10)

⛔ Bỏ nhóm R02–R04 không phải vì lười: **K2 đã đo và chứng minh** rằng gộp
   nhiều clip tham chiếu làm biên nhân bản tụt từ +0,4352 xuống +0,1303, và số
   lần nhận đúng người nói từ 24/24 xuống 7/21. Kinh nghiệm của hệ cũ đúng cho
   F5 và **không chuyển sang được**.

## ⛔ NGƯỠNG PHẢI ĐO, KHÔNG ĐƯỢC CHÉP

Hệ cũ có những con số rất cụ thể: `delta_brightness < -3`, `delta_f0_mean < -5`,
`delta_hnr < -3`. Chúng là ngưỡng **đã hiệu chuẩn cho F5-TTS**, trên dữ liệu của
hệ ấy, với thang đo của hệ ấy.

Chép sang đây thì ta có một cổng trông rất chín chắn mà không ai biết nó bắt
được gì. Bài học ấy đã trả giá hai lần trong dự án này:

  · K1: ngưỡng lặp 0,92 KHÔNG mượn của upstream — đo tương quan đuôi trên tiếng
    thật (cao nhất 0,103) rồi mới đặt, và biên hoá ra là 17–20σ.
  · K3: sàn nhiễu lấy từ n=4 có sai số **41%**, và tôi đã sửa chỉ số suốt hai
    lượt để đuổi theo những con số tự co giãn.

⇒ Nên tệp này **chỉ đo và trả số có dấu**. Việc phán "lệch bao nhiêu là nhiều"
  thuộc về `chan_doan.py`, và nó đọc ngưỡng từ một baseline **đã đo**, không từ
  hằng số gõ tay.

## Ranh giới ba tầng (kế thừa nguyên vẹn — đây mới là tinh tuý)

Hệ cũ cưỡng chế ba tầng bằng luật import, và đó là thứ đáng mang sang nhất:

    metrics/   → CHỈ tính số. Không diễn giải, không phán "tốt/xấu".
    diagnosis/ → CHỈ diễn giải số. KHÔNG được import numpy/soundfile/torch.
    report/    → CHỈ định dạng.

Tệp này là tầng **metrics**: nó được dùng numpy, và nó **không được** nói câu
nào về tốt/xấu. `chan_doan.py` là tầng diagnosis: nó không được import numpy.
Bánh cóc canh đúng ranh giới ấy: `tests/test_388_chan_doan.py`.
"""
from __future__ import annotations

import numpy as np

#: Những phép đo được lấy hiệu cho cả hai bên. Tên ở đây là tên trong dict do
#: `do_on_dinh.do_tat_ca` và `do_chat_luong.do_tin_hieu` trả về.
#:
#: ⛔ CHỈ những phép có nghĩa khi lấy HIỆU. `khop_cuc_bo_dinh` (độ tự lặp) không
#:    nằm đây: bản tham chiếu tự lặp bao nhiêu là chuyện của bản tham chiếu, nó
#:    không nói gì về việc bản sinh ra có lặp hay không. Một cái hiệu vô nghĩa
#:    vẫn ra một con số, và một con số vô nghĩa trong bảng sẽ được ai đó dùng.
LAY_HIEU = (
    "trong_tam_hz",      # R12 — độ sáng phổ
    "vat_95_hz",
    "vat_99_hz",
    "db_dai_cao",        # R12 — năng lượng dải cao
    "f0_trung_vi_hz",    # R13/R14 — cao độ
    "f0_tan_tuong_doi",  # R15 — độ đơn điệu
    "dao_dong_khung",    # ổn định biên độ
    "lufs",              # độ to
)

#: Những phép lấy hiệu ở thang **tương đối** (chia cho giá trị tham chiếu) thay
#: vì hiệu tuyệt đối. Lý do: 20 Hz lệch trên một giọng 90 Hz là nhiều, trên một
#: giọng 220 Hz là ít — cùng một con số tuyệt đối mang hai ý nghĩa khác nhau.
TUONG_DOI = frozenset({"trong_tam_hz", "vat_95_hz", "vat_99_hz",
                       "f0_trung_vi_hz",
                       # 🔴 `f0_tan_tuong_doi` PHẢI ở đây, và lý do là một luật
                       #    **không bao giờ với tới được** nếu nó ở thang tuyệt
                       #    đối.
                       #
                       #    `f0_tan_tuong_doi` là độ tản F0 chuẩn hoá, giá trị
                       #    thực tế ~0,15 và **không âm được**. Nên hiệu tuyệt
                       #    đối `ra − ref` bị chặn dưới ở khoảng **−0,15**: một
                       #    bản đọc PHẲNG LÌ HOÀN TOÀN cũng chỉ tới đó.
                       #
                       #    Dung sai đo được của nó là 4×0,042 = **0,168**.
                       #    Lớn hơn giá trị cực đại có thể đạt. Tức R15 (đơn
                       #    điệu hơn) **không thể nổ dưới bất kỳ đầu vào nào** —
                       #    và một luật như vậy tệ hơn không có luật, vì nó tạo
                       #    ra ảo giác đã canh.
                       #
                       # ⭐ Ở thang tương đối thì "bản sinh ra chỉ còn 40% độ
                       #    tản của tham chiếu" = −0,6, và "phẳng lì" = −1,0.
                       #    Dải giá trị mở ra đủ để một dung sai có nghĩa.
                       "f0_tan_tuong_doi"})


def _gop(wav, sr: int) -> dict:
    """Mọi phép đo dùng được cho việc lấy hiệu, gộp thành một dict phẳng."""
    from voice_sidecar import do_chat_luong, do_on_dinh

    ra = dict(do_on_dinh.do_tat_ca(wav, sr) or {})
    th = do_chat_luong.do_tin_hieu(wav, sr) or {}
    for k in ("lufs", "true_peak_dbtp", "snr_db"):
        if th.get(k) is not None:
            ra[k] = th[k]
    return ra


def do_lech(wav, sr: int, wav_ref, sr_ref: int) -> dict:
    """`{delta_*: số có dấu}` — bản sinh ra TRỪ bản tham chiếu.

    ⛔ DẤU CÓ NGHĨA, và nó luôn là **sinh ra − tham chiếu**. Âm = bản sinh ra
       thấp hơn/tối hơn/trầm hơn. Đảo dấu ở một phép là biến một luật chẩn đoán
       thành luật ngược lại, và nó sẽ xanh đúng lúc chất lượng tụt — cùng lớp
       lỗi với `on_dinh_giong` từng suýt bị đặt sai chiều trong cổng V10.

    ⛔ Chỉ số nào một bên không đo được thì **vắng mặt**, không phải bằng 0.
       Vắng mặt nghĩa là "chưa biết"; 0 nghĩa là "đã biết, không lệch". Hai câu
       ấy dẫn tới hai quyết định ngược nhau ở tầng chẩn đoán.
    """
    a = _gop(np.asarray(wav, dtype=np.float64), int(sr))
    b = _gop(np.asarray(wav_ref, dtype=np.float64), int(sr_ref))
    ra: dict = {}
    for k in LAY_HIEU:
        x, y = a.get(k), b.get(k)
        if x is None or y is None:
            continue
        if k in TUONG_DOI:
            if not y:
                continue
            ra[f"delta_{k}_ti_le"] = round(float((x - y) / y), 5)
        else:
            ra[f"delta_{k}"] = round(float(x - y), 5)
    # ⛔ KHÔNG kèm một cái ĐẾM ("so_phep_lech") vào dict này, dù nó tiện.
    #    Một cái đếm có sàn nhiễu bằng 0 với văn bản cố định, và bộ dò điểm mù
    #    của K3 đã từng in **1.000.000σ** cho một cái đếm rồi tuyên bố một điểm
    #    mù đã đóng trong khi nó còn nguyên. Muốn biết đo được mấy phép thì
    #    `len(ra)` ở nơi gọi — đừng để nó lẫn vào hàng ngũ chỉ số.
    return ra
