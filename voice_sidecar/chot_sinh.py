r"""
chot_sinh.py — bốn chốt kiểm một lượt sinh **trước khi trả về cho khách**.

## Vì sao có tệp này (K1)

Mọi model tự hồi quy đều có lúc kẹt: nó sinh xong một câu rồi **lặp lại đuôi**
thay vì dừng. Nó cũng có lúc trả về gần như im lặng, hoặc `NaN`, hoặc một bản
dài gấp ba lần thứ đáng lẽ phải có.

Trước 01/09/2026 hệ này **tin model**: `noi()` trả về bất cứ thứ gì engine đưa,
và tầng job chỉ bắt được ngoại lệ. Không ngoại lệ nào được ném cho một bản đọc
lặp — nó là một mảng float hợp lệ.

⛔ Và nó chạm tiền theo hướng tệ nhất. Quyết toán tính theo **giây tiếng sinh ra
   được**, mà tiếng lặp vẫn là tiếng: một bản kẹt lặp dài gấp đôi thì khách bị
   thu **gấp đôi** cho một sản phẩm hỏng.

Khuôn lấy từ `src/inference/retry_policy.py` của hệ cũ (`D:\Voiceclone_TTS`),
đã chạy thật trên F5-TTS + XTTS. Bốn chốt, thứ tự cố định.

## ⛔ BA THỨ PHẢI ĐO LẠI, KHÔNG ĐƯỢC CHÉP

Bản gốc viết cho F5-TTS ở 24 kHz. Chép nguyên sang đây thì hỏng ở ba chỗ, và cả
ba đều hỏng **im lặng**:

  ① **Tần số lấy mẫu.** Bản gốc ghim `SR = 24000` làm hằng số module. VieNeu v3
     Turbo ra **48 kHz**. Một cửa sổ 0,6 giây tính bằng hằng số sai là một cửa
     sổ 0,3 giây — chốt vẫn chạy, vẫn trả số, chỉ là nó nhìn nửa lượng dữ liệu.
     ⇒ `sr` là **tham số**, không phải hằng số.

  ② **Mô hình ước thời lượng.** Bản gốc dùng `số_từ × 0,4 giây` — một hằng số
     cho tiếng Anh. Tiếng Việt tính theo **ký tự** và ta đã đo được mô hình
     riêng; xem `GOC_S` / `KY_TU_MOI_GIAY` bên dưới.

  ③ **KHÔNG dùng `gia.giay_uoc`** dù nó sẵn có và cùng dạng công thức. Hàm ấy
     **cố ý ước THỪA** (1,5 s khởi động + 18 ký tự/giây, so với 20,8 đo được)
     vì nó phục vụ việc **giữ chỗ credit** — ước thiếu thì khách tiêu quá số dư.

     Dùng một ước thừa làm "kỳ vọng" ở đây thì tỉ lệ `thật/kỳ_vọng` tụt khoảng
     16% trên mọi lượt, và hệ quả đi **hai hướng cùng lúc**: chốt *quá ngắn*
     báo động nhầm dễ hơn, còn chốt *quá dài* — thứ bắt lặp đuôi — trở nên
     **kém nhạy hơn**. Một con số đúng cho việc tính tiền là một con số sai cho
     việc chẩn đoán.

## Số đo (01/09/2026, `tools/do_gia_von_voice.py`, 4 bậc × 3 lượt)

     36 ký tự ->  2,00 s        496 ký tự -> 23,69 s
    167 ký tự ->  8,51 s      1.498 ký tự -> 71,23 s

Khớp tuyến tính: `giây ≈ 0,396 + ký_tự / 21,16`. Tỉ lệ thật/mô hình trên cả 12
lượt nằm trong **0,954 – 1,062**, độ lệch chuẩn **0,0305**.

⇒ Ngưỡng `2,0×` cách trung bình **33 σ**; ngưỡng `0,5×` cách **16 σ**. Đó là lý
  do giữ nguyên hai con số rộng của hệ cũ thay vì siết chúng: chúng đã rộng hơn
  nhiễu hàng chục lần, và một chốt báo động nhầm sẽ bị tắt trong một tuần.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

#: Mô hình ước thời lượng TRUNG TÂM — không phải mô hình tính tiền. Xem ③.
GOC_S = 0.396
KY_TU_MOI_GIAY = 21.16

#: Cửa sổ so đuôi, giây. Con số của hệ cũ; nó là một khoảng đủ dài để chứa một
#: cụm từ và đủ ngắn để hai cụm liền nhau không tình cờ giống nhau.
CUA_SO_DUOI_S = 0.6
#: Tương quan trên mức này thì coi là lặp. 0,92 rất cao — tiếng nói tự nhiên
#: không lặp lại chính nó ở mức đó trong hai cửa sổ liền kề.
NGUONG_LAP = 0.92
#: Dưới mức này thì không xét lặp: đoạn quá ngắn thì hai cửa sổ chồng lấn ngữ
#: điệu của cùng một từ và cho tương quan cao một cách vô hại.
TOI_THIEU_XET_LAP_S = 2.0

#: Gần như im lặng. Hai ngưỡng biên độ, không phụ thuộc tần số lấy mẫu.
DINH_TOI_THIEU = 0.005
RMS_TOI_THIEU = 0.003

#: Tỉ lệ thời lượng thật trên thời lượng mô hình.
TRAN_QUA_DAI = 2.0
SAN_QUA_NGAN = 0.5
#: Không xét thời lượng cho văn bản ngắn hơn mức này: phí khởi động cố định
#: chiếm phần lớn một câu vài chữ, nên tỉ lệ ở đó rất nhiễu.
KY_TU_TOI_THIEU_XET_DAI = 40


@dataclass
class PhanQuyet:
    """Kết luận về một lượt sinh."""

    can_thu_lai: bool
    #: `False` = âm thanh này **không dùng được** kể cả khi thử lại cũng hỏng.
    nhan: bool
    ly_do: str = ""
    chan_doan: dict = field(default_factory=dict)

    @property
    def dat(self) -> bool:
        return not self.can_thu_lai and self.nhan


def giay_mo_hinh(so_ky_tu: int) -> float:
    """Thời lượng **kỳ vọng** của một lượt, giây. Ước TRUNG TÂM, không ước thừa."""
    return GOC_S + max(0, int(so_ky_tu)) / KY_TU_MOI_GIAY


def chot_toan_ven(wav) -> PhanQuyet:
    """`NaN` / `Inf` / rỗng.

    ⛔ PHẢI CHẠY ĐẦU TIÊN. `NaN` lan qua mọi phép tính phía sau mà không ném:
       `max(abs(x))` ra `NaN`, so sánh với ngưỡng ra `False`, và mọi chốt sau
       đều **im lặng cho qua**. Một mảng toàn `NaN` sẽ đi thẳng tới khách.
    """
    cd = {"chot": "toan_ven"}
    if wav is None:
        return PhanQuyet(True, False, "wav la None", cd)
    x = np.asarray(wav)
    if not x.size:
        return PhanQuyet(True, False, "wav rong", {**cd, "so_mau": 0})
    xau = int(x.size - np.count_nonzero(np.isfinite(x)))
    if xau:
        return PhanQuyet(True, False, f"{xau}/{x.size} mau NaN hoac Inf",
                         {**cd, "so_mau_xau": xau, "so_mau": int(x.size)})
    return PhanQuyet(False, True, "", cd)


def chot_gan_im(wav) -> PhanQuyet:
    """Model chạy xong nhưng không phát ra tiếng nào đáng kể."""
    cd = {"chot": "gan_im"}
    x = np.asarray(wav, dtype=np.float64)
    if not x.size:
        return PhanQuyet(True, False, "wav rong", {**cd, "so_mau": 0})
    dinh = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x ** 2)))
    if not (np.isfinite(dinh) and np.isfinite(rms)):
        # Phòng khi ai đó gọi chốt này mà bỏ qua `chot_toan_ven`.
        return PhanQuyet(True, False, f"so do khong huu han: dinh={dinh} rms={rms}", cd)
    cd.update({"dinh": round(dinh, 5), "rms": round(rms, 5)})
    if dinh < DINH_TOI_THIEU and rms < RMS_TOI_THIEU:
        return PhanQuyet(True, False,
                         f"gan im: dinh {dinh:.5f}, rms {rms:.5f}", cd)
    return PhanQuyet(False, True, "", cd)


def chot_lap_duoi(wav, sr: int) -> PhanQuyet:
    """Đuôi bản đọc có phải bản sao của đoạn ngay trước nó không.

    Cách đo: chuẩn hoá hai cửa sổ liền kề ở cuối rồi lấy tích vô hướng — tức
    tương quan chéo ở độ trễ 0. Hai đoạn tiếng khác nhau cho khoảng 0,1–0,4;
    một đoạn lặp cho trên 0,9.

    ⭐ Đây là chốt **duy nhất** trong bốn chốt bắt được lỗi mà tai nghe ra ngay
       còn mọi phép đo tín hiệu khác đều nói "bình thường": bản lặp có SNR đẹp,
       LUFS đẹp, không vỡ tiếng, không im. Nó chỉ sai ở chỗ nó nói lại.
    """
    cd = {"chot": "lap_duoi"}
    x = np.asarray(wav, dtype=np.float64)
    if not x.size or not sr:
        return PhanQuyet(False, True, "", {**cd, "bo_qua": "rong"})
    giay = x.size / float(sr)
    if giay < TOI_THIEU_XET_LAP_S:
        return PhanQuyet(False, True, "", {**cd, "bo_qua": f"ngan_{giay:.1f}s"})
    n = int(sr * CUA_SO_DUOI_S)
    if x.size < 2 * n:
        return PhanQuyet(False, True, "", {**cd, "bo_qua": "khong_du_mau"})

    truoc, sau = x[-2 * n:-n], x[-n:]

    def _chuan(v):
        return float(np.sqrt(np.sum(v ** 2))) + 1e-12

    tuong_quan = float(np.dot(truoc / _chuan(truoc), sau / _chuan(sau)))
    cd.update({"tuong_quan": round(tuong_quan, 4),
               "cua_so_s": CUA_SO_DUOI_S, "nguong": NGUONG_LAP})
    if tuong_quan > NGUONG_LAP:
        return PhanQuyet(True, True,
                         f"lap duoi: tuong quan {tuong_quan:.3f} giua hai cua so "
                         f"{CUA_SO_DUOI_S}s cuoi", cd)
    return PhanQuyet(False, True, "", cd)


def chot_thoi_luong(wav, sr: int, so_ky_tu: int) -> PhanQuyet:
    """Thời lượng thật có khớp mô hình không.

    Bắt hai kiểu hỏng khác nhau bằng cùng một phép chia: **quá dài** thường là
    lặp mà chốt trên bỏ sót (lặp ở giữa chứ không ở đuôi), **quá ngắn** là bản
    bị cụt.
    """
    cd = {"chot": "thoi_luong"}
    x = np.asarray(wav)
    that = x.size / float(sr) if (x.size and sr) else 0.0
    cd["that_s"] = round(that, 2)
    if int(so_ky_tu) < KY_TU_TOI_THIEU_XET_DAI:
        return PhanQuyet(False, True, "",
                         {**cd, "bo_qua": f"van_ban_ngan_{so_ky_tu}"})
    ky_vong = giay_mo_hinh(so_ky_tu)
    if ky_vong <= 0:
        return PhanQuyet(False, True, "", {**cd, "bo_qua": "khong_uoc_duoc"})
    ti_le = that / ky_vong
    cd.update({"ky_vong_s": round(ky_vong, 2), "ti_le": round(ti_le, 3),
               "tran": TRAN_QUA_DAI, "san": SAN_QUA_NGAN})
    if ti_le > TRAN_QUA_DAI:
        return PhanQuyet(True, True,
                         f"qua dai: {that:.1f}s so voi ky vong {ky_vong:.1f}s "
                         f"({ti_le:.2f}x)", cd)
    if ti_le < SAN_QUA_NGAN:
        return PhanQuyet(True, True,
                         f"qua ngan: {that:.1f}s so voi ky vong {ky_vong:.1f}s "
                         f"({ti_le:.2f}x)", cd)
    return PhanQuyet(False, True, "", cd)


def kiem_het(wav, sr: int, so_ky_tu: int) -> PhanQuyet:
    """Chạy cả bốn chốt theo THỨ TỰ, trả phán quyết hỏng đầu tiên.

    ⛔ Thứ tự không phải chuyện gọn gàng: `chot_toan_ven` phải chạy trước vì
       `NaN` làm mọi chốt sau im lặng cho qua. Xem docstring của nó.

    🔴 TRẢ VỀ SỐ ĐO CỦA **MỌI** CHỐT ĐÃ CHẠY, kể cả khi tất cả đều đạt.

       Bản đầu chỉ trả `chan_doan` của chốt hỏng đầu tiên, và khi mọi chốt đạt
       thì trả `{"chot": "deu_dat"}` — không con số nào. Hệ quả đo được ngay
       trên production: dòng telemetry ghi `tuong_quan_duoi` **không bao giờ
       chạy**, vì trên một lượt khoẻ `tuong_quan` không có trong `chan_doan`.

    ⛔ Và đó là kiểu hỏng tệ nhất của một phép đo: log rỗng đọc lên y hệt "không
       phát hiện lặp nào", trong khi sự thật là **chưa đo gì cả**. Một bộ đếm
       bằng 0 vì mọi thứ đều ổn, và một bộ đếm bằng 0 vì nó không chạy, in ra
       giống hệt nhau.
    """
    da_chay: dict = {}
    for ham, doi_so in ((chot_toan_ven, ()),
                        (chot_gan_im, ()),
                        (chot_lap_duoi, (sr,)),
                        (chot_thoi_luong, (sr, so_ky_tu))):
        pq = ham(wav, *doi_so)
        da_chay[str(pq.chan_doan.get("chot") or ham.__name__)] = pq.chan_doan
        if not pq.dat:
            pq.chan_doan = {**pq.chan_doan, "da_chay": da_chay}
            return pq
    return PhanQuyet(False, True, "", {"chot": "deu_dat", "da_chay": da_chay})


def so_do(pq: PhanQuyet, chot: str, ten: str):
    """Một số đo cụ thể từ một phán quyết, dù chốt ấy đạt hay hỏng.

    Có mặt để người gọi không phải biết `da_chay` nằm ở đâu — và để một bản vá
    sau này đổi cấu trúc ấy thì chỉ phải sửa một chỗ.
    """
    cd = pq.chan_doan or {}
    if cd.get("chot") == chot and ten in cd:
        return cd[ten]
    return ((cd.get("da_chay") or {}).get(chot) or {}).get(ten)
