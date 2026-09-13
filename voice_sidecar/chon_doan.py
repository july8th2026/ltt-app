r"""
chon_doan.py — chọn ĐOẠN 8 GIÂY tốt nhất trong một clip dài để nhân bản giọng.

## Vấn đề

SDK cắt **8 giây đầu, một cách mù**. Đọc trong mã thật
(`vieneu/_v3_turbo_engine/inference_v3_turbo.py`)::

    _MAX_REF_SECONDS = 8.0
    if wav.shape[-1] > int(max_seconds * sr):
        wav = wav[..., : int(max_seconds * sr)]

Một clip 30 giây thì 22 giây sau **không bao giờ được dùng**. Nếu 8 giây đầu rơi
vào chỗ khách còn lấy hơi hay đọc câu tệ nhất thì giọng nhân bản dựng từ đúng chỗ
đó, trong khi phần hay nằm im. Ta có thứ SDK không có — **cả clip** — nên ta chọn
trước rồi đưa nó đúng 8 giây ta chọn.

⭐ Và việc này đáng làm hơn với v3: README của GPT-SoVITS ghi *"V3/V4 合成的声音更
   偏向参考音频, 而不是整体训练集的风格"* — bản mới **bám clip tham chiếu** hơn là
   phong cách tập huấn luyện. Clip càng quan trọng thì chọn sai càng đắt.

═══════════════════════════════════════════════════════════════════════════════
 NGUỒN — ba bước dưới đây theo THỰC HÀNH CỘNG ĐỒNG, không phải tự nghĩ
═══════════════════════════════════════════════════════════════════════════════

**Bước 1 · cắt đoạn** — `openvpi/audio-slicer` (883★), chính là bộ cắt mà
`GPT-SoVITS` (61k★) dùng trong quy trình chuẩn bị dữ liệu. Thuật toán họ công bố:

    RMS mỗi khung; khung dưới `threshold` là im. Khi phần CÓ TIẾNG đã đủ
    `min_length` và gặp một vùng im dài hơn `min_interval` thì cắt tại khung
    có RMS THẤP NHẤT trong vùng im đó.

🔴 Đây là chỗ bản đầu của tệp này SAI. Tôi trượt một lưới 0,5 giây và chấm điểm
   từng cửa sổ — nghe hợp lý, và nó **cắt giữa từ**. Một clip tham chiếu bắt đầu
   ở giữa một âm tiết đưa cho bộ mã hoá một phụ âm cụt, và phép cắt im hai đầu
   của SDK **không sửa được** vì nó chỉ cắt im, không cắt chữ.

   Cắt ở đáy vùng im thì không bao giờ cắt giữa từ. Đó là lý do bộ cắt của cộng
   đồng làm thế, và lý do đó không hiện ra nếu chỉ ngồi nghĩ.

**Bước 2 · chấm chất lượng** — quy trình `Emilia` (trong `open-mmlab/Amphion`,
10k★) chấm từng đoạn bằng **DNSMOS P.835** (`sig_bak_ovr.onnx`, Microsoft
DNS-Challenge) rồi lọc theo ngưỡng.

✅ TA ĐÃ DÙNG DNSMOS (31/08/2026). Lý do hoãn trước đây — "một model ONNX phải
   tải thêm" — không đứng vững khi đo: model **1,16 MB**, giấy phép CC-BY-4.0,
   chạy trên `onnxruntime` ta đã có. Xem `dnsmos.py` và `tai_dnsmos.py`.

   Đo trên tiếng nói THẬT (không phải âm tổng hợp — DNSMOS huấn luyện trên tiếng
   người và cho số vô nghĩa trên sóng sin):

       tiếng sạch    SIG 2,764  BAK 3,977  OVRL 2,555
       nhiễu nhẹ                BAK 2,917  OVRL 2,040
       nhiễu vừa                BAK 1,920  OVRL 1,562
       vỡ tiếng      SIG 2,244  BAK 4,024  OVRL 2,127

   `BAK` bám nhiễu đơn điệu, và `SIG` bắt được **vỡ tiếng** trong khi `BAK` vẫn
   cao — vì vỡ tiếng không phải nhiễu nền. SNR mù hẳn chỗ đó.

⚠️ Nhưng IM LẶNG ăn OVRL 1,840, cao hơn tiếng nhiễu. DNSMOS không thay được cổng
   tỉ lệ tiếng — nó bổ sung, không thay thế.

**Bước 3 · chọn một** — chỗ này **không có tiền lệ trực tiếp**, và nói thẳng:
   các quy trình cộng đồng LỌC MỘT KHO (giữ mọi đoạn qua ngưỡng), còn ta phải
   CHỌN ĐÚNG MỘT. Tiêu chí của ta: **đại diện** — `cosine(emb(đoạn), emb(cả
   clip))`. Cả clip là ước lượng tốt nhất ta có về giọng người này, nên đoạn tốt
   nhất là đoạn lệch ít nhất khỏi chính họ. Chạy trong đúng `OnnxSpeakerEncoder`
   mà `prepare_reference` của SDK dùng, nên nó nói về thứ model thật sự nhìn.

⛔ NGUYÊN TẮC: KHÔNG BAO GIỜ TỆ HƠN HÔM NAY. Không chọn được gì thì trả về
   `(0, 8s)` — đúng hành vi SDK. Một bộ chọn có thể **từ chối** là một bộ chọn
   thêm một đường hỏng mới vào chỗ trước đây vẫn chạy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

#: ⛔ ĐỌC TỪ SDK, không gõ lại. Upstream đổi `_MAX_REF_SECONDS` mà ta gõ cứng 8.0
#: thì ta chọn một cửa sổ rồi SDK vẫn cắt tiếp — im lặng. `test_367` chốt khớp.
try:                                        # pragma: no cover - phụ thuộc venv
    from vieneu._v3_turbo_engine.inference_v3_turbo import (
        _MAX_REF_SECONDS as CUA_SO_S,
    )
except Exception:                           # noqa: BLE001 - venv nền tảng không có vieneu
    CUA_SO_S = 8.0

# ── tham số bộ cắt, lấy nguyên của `openvpi/audio-slicer` ────────────────────
#
# Giữ đúng giá trị mặc định họ công bố. Đổi một con số ở đây là rời khỏi một cấu
# hình đã được 61k sao dùng thật, nên phải có số đo mới được đổi.
NGUONG_IM_DB = -40.0      #: khung dưới mức này là im
KHUNG_MS = 10.0           #: `hop_size`
IM_TOI_THIEU_MS = 300.0   #: `min_interval` — vùng im ngắn hơn thì không cắt
DOAN_TOI_THIEU_MS = 1000.0  #: đoạn ngắn hơn thì gộp vào đoạn kế

#: Tỉ lệ mẫu chạm trần tối đa. Cùng con số `do_chat_luong.TY_LE_CHAM_TRAN_TOI_DA`.
TY_LE_CHAM_TRAN_TOI_DA = 0.001

#: Ứng viên ngắn hơn mức này thì bỏ: bộ mã hoá cần đủ tín hiệu. README của
#: VieNeu ghi khoảng dùng được là **3–8 giây**, nên 3 là sàn của chính tài liệu.
UNG_VIEN_TOI_THIEU_S = 3.0

#: Sàn tỉ lệ CÓ TIẾNG trong một ứng viên.
#:
#: ⚠️ Đây là một CỔNG LOẠI, không phải một ngưỡng xếp hạng: nó vứt cửa sổ gần
#:    như toàn im, không dùng để chấm điểm. Nhiều tiếng hơn **không** đơn điệu
#:    tốt hơn — một cửa sổ kín tiếng từ đoạn đọc gấp tệ hơn một cửa sổ có nhịp
#:    nghỉ tự nhiên, và phép đại diện đã bắt được điều đó.
#:
#: 🔴 Bản viết lại của tệp này ĐÁNH RƠI cổng đó, và phép kiểm bắt được: một clip
#:    toàn im vẫn "chọn" ra 8 giây im lặng, rồi đưa cho bộ mã hoá một cửa sổ
#:    không có tín hiệu nào. `apps/ltt_voice/audio_input.py` có chặn clip quá 60 %
#:    im, nhưng bộ chọn không được dựa vào một phép kiểm ở tầng khác.
TY_LE_TIENG_TOI_THIEU = 0.50


@dataclass
class KetQuaChon:
    """Đoạn đã chọn, kèm đủ số để giải thích vì sao — không chỉ một cặp mốc."""
    bat_dau_s: float
    ket_thuc_s: float
    diem_dai_dien: float | None = None
    snr_db: float | None = None
    so_ung_vien: int = 0
    #: Thang nào đã chấm chất lượng: `"dnsmos_ovrl"` | `"snr_db"` | `""`.
    #:
    #: 🔴 THIẾU TRƯỜNG NÀY LÀ MỘT LỖI THẬT, ĐO ĐƯỢC TRÊN PRODUCTION 31/08.
    #:    `diem_chat_luong` tính đúng tên thang và docstring của nó hứa hẳn là
    #:    *"nói ra là đã lui"* — rồi người gọi **vứt** giá trị thứ hai đi. Nên
    #:    báo cáo của một lượt ghi danh thật không có cách nào nói DNSMOS có
    #:    chạy hay đã lui về SNR, và tôi phải mở venv của sidecar ra hỏi tay.
    #:
    #: ⛔ Vì sao nó không chỉ là bất tiện: `dnsmos.cham` trả `None` **im lặng**
    #:    khi thiếu `onnxruntime`, thiếu `scipy`, hay thiếu tệp model. Một lần
    #:    deploy làm rơi một trong ba thứ đó sẽ hạ chất lượng bộ chọn xuống
    #:    thang SNR — và **không một dòng nào ở đâu đổi**. Trường này là thứ
    #:    duy nhất làm việc đó nhìn thấy được.
    thang_chat_luong: str = ""
    ly_do: str = ""
    bang_diem: list = field(default_factory=list)

    @property
    def da_chon_that(self) -> bool:
        """Có thật sự chọn, hay đã lui về hành vi mặc định của SDK."""
        return self.so_ung_vien > 0


def _khung_rms(wav, sr: int, khung_ms: float = KHUNG_MS):
    from ._dsp_chung import khung_rms
    return khung_rms(wav, sr, khung_ms)


def ranh_gioi_im(wav, sr: int) -> list:
    """Các mốc cắt (chỉ số mẫu), tại ĐÁY của mỗi vùng im đủ dài.

    Thuật toán của `openvpi/audio-slicer`: tìm vùng im dài hơn `min_interval`,
    rồi cắt tại khung có RMS **thấp nhất** trong vùng đó — nên nhát cắt luôn rơi
    vào chỗ yên nhất, không rơi vào giữa một âm tiết.
    """
    rms, n = _khung_rms(wav, sr)
    if not len(rms):
        return []
    im = rms < (10 ** (NGUONG_IM_DB / 20.0))
    toi_thieu = max(1, int(IM_TOI_THIEU_MS / KHUNG_MS))

    moc, i = [], 0
    while i < len(im):
        if not im[i]:
            i += 1
            continue
        j = i
        while j < len(im) and im[j]:
            j += 1
        if j - i >= toi_thieu:
            day = i + int(np.argmin(rms[i:j]))
            moc.append(day * n)
        i = j
    return moc


def _doan_tho(wav, sr: int) -> list:
    """Cắt clip thành các đoạn tại ranh giới im. Trả `[(dau, cuoi)]` theo mẫu."""
    moc = ranh_gioi_im(wav, sr)
    canh = [0, *moc, len(wav)]
    toi_thieu = int(DOAN_TOI_THIEU_MS / 1000.0 * sr)
    ra = []
    for a, b in zip(canh, canh[1:]):
        if b - a < toi_thieu and ra:
            ra[-1] = (ra[-1][0], b)     # đoạn quá ngắn thì gộp vào đoạn trước
        elif b > a:
            ra.append((a, b))
    return ra


def ung_vien(wav, sr: int) -> list:
    """Mọi cụm đoạn liên tiếp có tổng độ dài ≤ `CUA_SO_S`.

    Ghép các đoạn liền nhau thay vì lấy từng đoạn một: một câu ngắn 2 giây không
    đủ cho bộ mã hoá, nhưng ba câu liền nhau thì đủ — và ghép ở ranh giới im thì
    vẫn không cắt vào chữ.
    """
    doan = _doan_tho(wav, sr)
    tran = int(CUA_SO_S * sr)
    san = int(UNG_VIEN_TOI_THIEU_S * sr)
    ra = []
    for i in range(len(doan)):
        for j in range(i, len(doan)):
            a, b = doan[i][0], doan[j][1]
            if b - a > tran:
                break
            if b - a >= san:
                ra.append((a, b))

    # 🔴 ĐOẠN DÀI HƠN CỬA SỔ VẪN PHẢI DÙNG ĐƯỢC.
    #
    #    Bản đầu chỉ ghép các đoạn nguyên vẹn, nên một đoạn nói liền 9 giây bị
    #    **loại hẳn** — và trên clip thử, ứng viên duy nhất còn lại hoá ra là 6
    #    giây nhiễu ở đầu, tức đúng đoạn tệ nhất. Bộ chọn khi đó tệ hơn cả việc
    #    không chọn.
    #
    #    Người nói liền 9 giây không có khoảng nghỉ 300 ms thì cắt vào giữa lời
    #    là **không tránh được**. Nhưng vẫn cắt ở chỗ YÊN NHẤT có thể: lấy các
    #    cực tiểu cục bộ của đường RMS trong đoạn làm mốc bắt đầu, thay vì một
    #    lưới đều. Cùng nguyên tắc với `openvpi/audio-slicer`, chỉ hạ ngưỡng
    #    "im" xuống mức tương đối vì trong một đoạn nói liền thì không có im
    #    tuyệt đối nào cả.
    for a, b in doan:
        if b - a <= tran:
            continue
        ra.extend(_cat_trong_doan_dai(wav, sr, a, b, tran))
    return ra


def _cat_trong_doan_dai(wav, sr: int, a: int, b: int, tran: int) -> list:
    """Cửa sổ bên trong một đoạn dài, mốc bắt đầu snap vào cực tiểu RMS."""
    rms, n = _khung_rms(wav[a:b], sr)
    if not len(rms):
        return []
    cua_khung = max(1, tran // n)
    if len(rms) <= cua_khung:
        return []

    # Cực tiểu cục bộ của đường RMS: một khung yên hơn cả hai láng giềng. Đó là
    # chỗ gần nhất với một ranh giới từ khi không có khoảng lặng thật.
    day = [k for k in range(1, len(rms) - 1)
           if rms[k] <= rms[k - 1] and rms[k] <= rms[k + 1]]
    if not day:
        day = list(range(0, len(rms) - cua_khung, max(1, cua_khung // 8)))

    # Giữ những mốc còn đủ chỗ cho một cửa sổ đầy, và thưa ra để không sinh hàng
    # nghìn ứng viên gần trùng nhau (mỗi ứng viên là một lượt mã hoá).
    hop_le = [k for k in day if k + cua_khung <= len(rms)]
    ra, cuoi = [], -(10 ** 9)
    thua = max(1, int(0.25 * sr / n))       # tối thiểu 0,25 s giữa hai mốc
    for k in hop_le:
        if k - cuoi < thua:
            continue
        cuoi = k
        ra.append((a + k * n, a + (k + cua_khung) * n))
    # Luôn kèm mốc cuối cùng có thể, để phần đuôi của đoạn không bị bỏ quên.
    k = len(rms) - cua_khung
    if k >= 0 and (not ra or ra[-1][0] != a + k * n):
        ra.append((a + k * n, a + (k + cua_khung) * n))
    return ra


def _ty_le_tieng(wav, sr: int) -> float:
    """Tỉ lệ khung có tiếng. Cùng ngưỡng im với bộ cắt."""
    rms, _ = _khung_rms(wav, sr)
    if not len(rms):
        return 0.0
    return float(np.mean(rms >= 10 ** (NGUONG_IM_DB / 20.0)))


def _ty_le_cham_tran(wav) -> float:
    return 0.0 if not len(wav) else float(np.mean(np.abs(wav) >= 0.999))


def diem_chat_luong(wav, sr: int) -> tuple[float, str]:
    """Điểm chất lượng của một đoạn, `(điểm, nguồn)`. Càng cao càng sạch.

    DNSMOS OVRL nếu có model; không thì lui về SNR và **nói ra là đã lui** —
    hai thang khác nhau không so được với nhau, nên phải biết đang đọc thang nào.
    """
    from . import dnsmos
    d = dnsmos.cham(wav, sr)
    if d is not None:
        return float(d["ovrl"]), "dnsmos_ovrl"
    return float(_snr_db(wav, sr) or -99.0), "snr_db"


def _lam_tron(x: float | None) -> float | None:
    """Làm tròn mà GIỮ `None`.

    🔴 `round(_snr_db(...) or 0.0, 2)` biến "không đo được" thành `0.0`, và
       `0.0` đọc lên là "đã đo, và bằng 0 dB". Hai câu đó khác nhau hoàn toàn.

    ⭐ Nó vừa xảy ra thật: lượt ghi danh production 31/08 báo `"snr_db": 0.0`.
       Không phải một bản thu tệ — clip do TTS sinh nên khoảng lặng là **số 0
       tuyệt đối**, `_snr_db` trả `None` đúng như nó phải làm (SNR so với im
       lặng tuyệt đối không có nghĩa), rồi `or 0.0` nuốt mất chữ "không biết".

    ⛔ Đừng "sửa" `_snr_db` để nó trả 0 hay 99. `None` là câu trả lời đúng.
    """
    return None if x is None else round(float(x), 2)


def _snr_db(wav, sr: int) -> float | None:
    """SNR ước lượng: 25 % khung to nhất so với 10 % khung yên nhất.

    ⚠️ LỐI LUI khi không có DNSMOS. Nó đo tương phản mức, không đo chất lượng
       cảm nhận — một bản thu méo đều hay vỡ tiếng vẫn ra SNR đẹp.
    """
    rms, _ = _khung_rms(wav, sr)
    if len(rms) < 10:
        return None
    sap = np.sort(rms)
    yen = float(np.mean(sap[:max(1, len(sap) // 10)]))
    to = float(np.mean(sap[-max(1, len(sap) // 4):]))
    return None if yen <= 0 or to <= 0 else 20.0 * math.log10(to / yen)


def _cosine(a, b) -> float:
    from ._dsp_chung import cosine
    return cosine(a, b)


def chon(wav, sr: int, *, bo_ma_hoa=None) -> KetQuaChon:
    """Chọn đoạn ≤`CUA_SO_S` giây đại diện nhất. Không chọn được thì lui về đầu clip.

    `bo_ma_hoa` để test tiêm một bộ giả — phép chọn phải kiểm được mà không cần
    tải một model 28 MB.
    """
    wav = np.asarray(wav, dtype=np.float32)
    tong_s = len(wav) / float(sr) if sr else 0.0

    if tong_s <= CUA_SO_S:
        return KetQuaChon(0.0, round(tong_s, 3), snr_db=_snr_db(wav, sr),
                          ly_do="clip ngan hon cua so — dung nguyen")

    uv = [(a, b) for a, b in ung_vien(wav, sr)
          if _ty_le_cham_tran(wav[a:b]) <= TY_LE_CHAM_TRAN_TOI_DA
          and _ty_le_tieng(wav[a:b], sr) >= TY_LE_TIENG_TOI_THIEU]

    if not uv:
        # ⛔ LUI VỀ HÀNH VI CŨ, không từ chối.
        n = int(CUA_SO_S * sr)
        return KetQuaChon(0.0, CUA_SO_S, snr_db=_snr_db(wav[:n], sr),
                          ly_do="khong ung vien nao qua cong — lui ve 8 giay dau "
                                "(dung hanh vi mac dinh cua SDK)")

    if bo_ma_hoa is None:
        bo_ma_hoa = _bo_ma_hoa_mac_dinh()

    if bo_ma_hoa is None:
        a, b = max(uv, key=lambda x: (_snr_db(wav[x[0]:x[1]], sr) or 0.0, x[1] - x[0]))
        return KetQuaChon(round(a / sr, 3), round(b / sr, 3),
                          snr_db=_lam_tron(_snr_db(wav[a:b], sr)),
                          so_ung_vien=len(uv),
                          ly_do="khong nap duoc bo ma hoa giong — chon theo SNR, "
                                "KHONG theo dai dien")

    emb_ca_clip, thang = _moc_ben_vung(wav, sr, uv, bo_ma_hoa)
    diem = [(_cosine(bo_ma_hoa(wav[a:b], sr), emb_ca_clip), a, b) for a, b in uv]
    diem.sort(key=lambda x: (round(x[0], 4), x[2] - x[1]), reverse=True)
    d, a, b = diem[0]
    return KetQuaChon(
        bat_dau_s=round(a / sr, 3), ket_thuc_s=round(b / sr, 3),
        diem_dai_dien=round(d, 4), snr_db=_lam_tron(_snr_db(wav[a:b], sr)),
        so_ung_vien=len(uv), thang_chat_luong=thang,
        ly_do="chon theo dai dien (cosine voi ca clip)",
        bang_diem=[(round(x[1] / sr, 2), round(x[2] / sr, 2), round(x[0], 4))
                   for x in diem[:10]])


def _moc_ben_vung(wav, sr: int, uv: list, bo_ma_hoa):
    """Embedding MỐC + tên thang đã chấm. Ước lượng BỀN VỮNG, không phải clip thô.

    🔴 ĐÂY LÀ LỖI THỨ HAI CỦA CHÍNH TỆP NÀY, và phép thử tổng hợp mới lộ ra.

       Bản đầu lấy `emb(cả clip)` làm mốc: *"cả clip là ước lượng tốt nhất ta có
       về giọng người này"*. Nghe vững, và **sai khi clip có vùng xấu** — vì mốc
       đó bị chính phần xấu kéo lệch. Trên một clip thử gồm một phần ba nhiễu,
       một phần ba sạch, một phần ba vỡ tiếng, nó chọn đúng **đoạn nhiễu**:
       0,8745 so với 0,8674 của đoạn sạch. Đoạn "đại diện nhất" cho một clip bẩn
       chính là đoạn bẩn.

    ⭐ Sửa bằng thống kê bền vững, không bằng một ngưỡng gõ tay: lấy **nửa ứng
       viên có SNR cao hơn** làm mốc. Cùng tinh thần với bước lọc DNSMOS của quy
       trình `Emilia` — lọc chất lượng TRƯỚC rồi mới so — nhưng dùng phân vị nên
       không cần một con số tuyệt đối nào cả.

    ⚠️ Nó thu hẹp chứ không đóng được: một clip mà **phần lớn** là xấu thì nửa
       tốt hơn vẫn xấu. Không có cách nào chọn ra một đoạn tốt từ một bản thu
       không có đoạn nào tốt, và bộ chọn không nên giả vờ có.
    """
    cham = [(diem_chat_luong(wav[a:b], sr), a, b) for a, b in uv]
    thang = cham[0][0][1] if cham else ""
    diem = [(d, a, b) for (d, _), a, b in cham]
    if len(diem) < 3:
        return bo_ma_hoa(wav, sr), thang
    nguong = float(np.median([x[0] for x in diem]))
    tot = [(a, b) for d, a, b in diem if d >= nguong] or [(a, b) for _, a, b in diem]
    cac = [np.asarray(bo_ma_hoa(wav[a:b], sr), dtype=np.float64).ravel()
           for a, b in tot]
    tb = np.mean(cac, axis=0)
    chuan = np.linalg.norm(tb)
    return (tb / chuan if chuan else tb), thang


def _bo_ma_hoa_mac_dinh():
    """Bộ mã hoá giọng của CHÍNH SDK, hoặc `None` nếu không nạp được.

    ⭐ Dùng đúng `OnnxSpeakerEncoder` mà `prepare_reference` dùng, nên điểm đại
       diện nằm trong không gian model thật sự nhìn — không phải một không gian
       thứ hai chỉ ta hiểu.
    """
    try:                                    # pragma: no cover - cần venv giọng
        from .do_chat_luong import _bo_ma_hoa_giong, _embed
        bo = _bo_ma_hoa_giong()
        return None if bo is None else (lambda w, s: _embed(bo, w, s))
    except Exception:                       # noqa: BLE001
        return None


#: Số cửa sổ tối đa trong một kho tham chiếu. Hệ cũ dùng 5–7 (`pool.count_ideal_range`).
KHO_TOI_DA = 5
#: Tỉ lệ chồng lấn cho phép giữa hai cửa sổ trong kho.
#:
#: 🔴 ĐÂY LÀ ĐIỀU KIỆN KHIẾN GỘP CÓ NGHĨA. `ung_vien()` sinh **mọi cụm đoạn liên
#:    tiếp**, nên hai ứng viên điểm cao nhất gần như luôn chồng lấn — chúng là
#:    cùng một chỗ tốt, cắt lệch nhau một câu. Trung bình hai embedding của cùng
#:    một đoạn không thêm thông tin nào; nó chỉ làm ta tưởng đã gộp.
CHONG_LAN_TOI_DA = 0.25


def chon_kho(wav, sr: int, *, so_luong: int = KHO_TOI_DA, bo_ma_hoa=None) -> list:
    r"""Chọn tới `so_luong` cửa sổ **không chồng lấn nhau**, tốt nhất trước.

    Trả `[KetQuaChon, ...]`, phần tử đầu là cửa sổ đại diện nhất — đúng thứ
    `chon()` trả về, nên đường một-cửa-sổ vẫn là trường hợp `so_luong=1`.

    ## Vì sao một kho chứ không phải một cửa sổ (K2)

    Hệ cũ (`D:\Voiceclone_TTS`) tuyển **5–7 clip** cho mỗi giọng và ghi thẳng
    vào `configs/ref_quality_rules.yaml` rằng dưới 3 clip thì phép trung bình
    phổ không còn ý nghĩa. Ta đang lấy **một** cửa sổ 8 giây, nên một bản thu có
    đúng một chỗ tốt là hết may.

    ⭐ Nhưng kho ở đây **không** dùng như hệ cũ dùng. `prepare_reference` của
       VieNeu trả hai thứ khác bản chất:

         · `speaker_emb` — vector 192 chiều → **trung bình được**, và trung bình
           nhiều lượt phát chính là cách hệ nhận dạng người nói vẫn ghi danh;
         · `ref_codes`   — chuỗi token codec của clip → **không** trung bình
           được; nó là điều kiện âm học theo ngữ cảnh, phải là một đoạn liền
           mạch.

       ⇒ Gộp `speaker_emb` qua cả kho, giữ `ref_codes` của cửa sổ tốt nhất.
         Cùng nước đi mà XTTS làm khi nhận một danh sách `speaker_wav`.

    ⛔ CHƯA CHỨNG MINH LÀ TỐT HƠN. Hàm này chỉ *cho phép* đo; quyết định bật hay
       không nằm ở số đo biên nhân bản trên 24 giọng
       (`tools/do_nhan_ban_tu_kho_cu.py`). Một thay đổi nghe hợp lý mà không đo
       là đúng thứ dự án này đã trả giá nhiều lần.
    """
    wav = np.asarray(wav, dtype=np.float32)
    dau = chon(wav, sr, bo_ma_hoa=bo_ma_hoa)
    if so_luong <= 1 or not dau.da_chon_that or not dau.bang_diem:
        return [dau]

    ra = [dau]
    da_lay = [(dau.bat_dau_s, dau.ket_thuc_s)]
    for bat_dau_s, ket_thuc_s, diem in dau.bang_diem:
        if len(ra) >= so_luong:
            break
        if any(_chong_lan(bat_dau_s, ket_thuc_s, a, b) > CHONG_LAN_TOI_DA
               for a, b in da_lay):
            continue
        a, b = int(bat_dau_s * sr), int(ket_thuc_s * sr)
        ra.append(KetQuaChon(
            bat_dau_s=bat_dau_s, ket_thuc_s=ket_thuc_s,
            diem_dai_dien=diem, snr_db=_lam_tron(_snr_db(wav[a:b], sr)),
            so_ung_vien=dau.so_ung_vien,
            thang_chat_luong=dau.thang_chat_luong,
            ly_do="cua so bo sung cho kho tham chieu"))
        da_lay.append((bat_dau_s, ket_thuc_s))
    return ra


def _chong_lan(a1: float, b1: float, a2: float, b2: float) -> float:
    """Tỉ lệ chồng lấn của hai khoảng, trên khoảng NGẮN hơn.

    Chia cho khoảng ngắn hơn chứ không cho hợp: một cửa sổ 3 giây nằm trọn
    trong một cửa sổ 8 giây là **chồng hoàn toàn** — nó không thêm gì cả — nhưng
    tính theo hợp thì chỉ ra 0,375 và lọt qua.
    """
    giao = max(0.0, min(b1, b2) - max(a1, a2))
    ngan = min(b1 - a1, b2 - a2)
    return giao / ngan if ngan > 0 else 0.0
