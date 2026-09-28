"""Dò dải chữ gốc bằng **RapidOCR det-only** + gom cụm — tầng CHÍNH của `do_vung`.

## 🔴 Vì sao tệp này tồn tại (B10-4, 28/09/2026)

`do_vung.do_dai_chu` **⛔ không đọc chữ**. Nó tính một hồ sơ theo hàng —
`mean(axis=0) × std(axis=0)`, *"mạnh VÀ đổi"* — tức suy từ **biến thiên điểm
ảnh**. Ba hệ quả, cả ba chủ dự án nhìn ra trên bản giao thật:

1. Hồ sơ là **hợp trên thời gian**: hàng nào có chữ ở *một số* khung đều góp
   điểm ⇒ dải = bao của **mọi** khung ⇒ một cảnh 2 dòng kéo dải cao gấp đôi
   cho **cả video**.
2. Nó trả `x0=0, x1=1` ⇒ **che hết chiều ngang**.
3. Nó trả **một** hộp, ⛔ không có trường thời gian ⇒ che **cả video**, kể cả
   những đoạn ⛔ không có chữ nào.

**Đo trên chính phim nghiệm thu** (`真人气枪游戏…`, 1024×576, 275 s):

| | `do_dai_chu` | RapidOCR det |
|---|---|---|
| chiều cao | **15,5 %** khung, cả video | **5,5 %** trung bình mỗi hộp |
| bề ngang | **100 %** | **18,2 %** |
| khung ⛔ không chữ | ⛔ không biết | **3/24** nhận ra |
| số hộp mỗi khung | ⛔ không biết | **1 → 8** |
| thời gian | 1,1 s | 7,6 s (0,32 s/khung) |

⇒ Che mờ đang gấp **~2,8 lần** chiều cao và **~5,5 lần** bề ngang cần thiết.

## ⭐ Kiến trúc lấy từ `D:/Viral` (CHỈ ĐỌC), và lý do họ xếp như vậy

> `manual → RapidOCR(clustering) → OpenCV(phat_hien_dai) → none`

Họ **hạ** cách suy-theo-điểm-ảnh xuống hạng chót, ghi rõ: *"đoán qua biến thiên
pixel, ⛔ không đọc chữ thật → nhầm animation/đồ hoạ động thành 'dải sub', user
báo video Whisper ⛔ không hardsub vẫn bị che to"*.

⚠️ **Chính ta đã đo được giới hạn ấy** (25/09, `do_vung.de_xuat`): *"V4b ⛔
không phân biệt được dải phụ đề với bảng tên HUD của game… là GIỚI HẠN CỦA
PHƯƠNG PHÁP, ⛔ không phải chuyện tinh chỉnh ngưỡng."* Ta biết nó yếu và chốt
nó chỉ là *đề xuất* — nhưng ⛔ không thêm tầng mạnh hơn.

## 🔑 Ba trạng thái, ⛔ ĐỪNG gộp

| trả về | nghĩa | người gọi làm gì |
|---|---|---|
| ném `OcrLoiKyThuat` | chưa cài / crash / ⛔ không mở được tệp | **lùi** tầng sau |
| `KetQua(vung=(), so_khung>0)` | quét thật, ⛔ không thấy chữ | **TIN**, ⛔ không che |
| `KetQua(vung=(...))` | thấy | che |

🔴 Gộp hai cái đầu là đúng lỗi kho tham chiếu ghi 31/07: nuốt một lỗi kỹ thuật
thành *"video ⛔ không có sub cứng"* ⇒ **⛔ không che ⇒ lộ chữ Hán**.

⭐ Và đây là ca *"gộp về phía IM LẶNG"*: gộp về *"⛔ không thấy chữ"* thì hỏng
**âm thầm** và khách nhận video lộ chữ; gộp về *"chưa quét được"* thì chỉ tốn
thêm một tầng dò. **Cùng một phép gộp, hai cái giá lệch hàng bậc.**

## ⛔ `use_rec=False` — chỉ cần HỘP

Chủ dự án chốt 28/09: ⛔ **không** dùng văn bản OCR để đối chiếu với bản chép
lời. Ta chỉ hỏi *"chữ ở đâu"*, ⛔ không hỏi *"chữ là gì"*.

⚠️ Đo được: RapidOCR **vẫn trả** văn bản kể cả khi đặt `use_rec=False`, nên
đừng đọc cờ ấy như một lời hứa về nội dung trả về — ta **bỏ qua** trường văn
bản, đó là lựa chọn của ta chứ ⛔ không phải bảo đảm của thư viện.
"""
from __future__ import annotations

import contextlib
import logging
from typing import NamedTuple

from platform_core.i18n import _ as _t

_log = logging.getLogger(__name__)

#: Số khung lấy mẫu. Kho tham chiếu dùng ~2 fps cho che động; ở đây ta còn ở
#: chặng ĐỀ XUẤT (một dải cho khách xác nhận) nên lấy thưa hơn nhiều.
#:
#: ⭐ `24` chứ ⛔ không `18` của `do_dai_chu`: bộ dò cũ cần khung **dày** để `std`
#:    theo thời gian có nghĩa; bộ dò này đọc **từng khung độc lập**, nên số
#:    khung chỉ quyết định độ phủ thời gian, ⛔ không quyết định chất lượng một
#:    phép đo.
SO_KHUNG_OCR = 24

#: Chỉ xét hộp có tâm y từ đây trở xuống. Phụ đề gốc nằm ở nửa dưới.
#:
#: ⛔ ⛔ Không đặt `0.5`: một khung có chữ ở **đúng** giữa (bảng điểm, HUD) sẽ
#:    lọt. `0.60` là chỗ kho tham chiếu dùng cho cùng câu hỏi.
TAM_Y_TOI_THIEU = 0.60

#: Hai hộp cách nhau (theo tâm y) không quá chừng này = **cùng một hàng chữ**.
GOM_CUM_Y = 0.03

#: Một cụm phải xuất hiện ở ít nhất phần này của số khung ĐÃ ĐỌC mới được coi
#: là phụ đề. Watermark tĩnh cũng qua được cửa này, nên nó ⛔ không đủ một mình
#: — xem `_chon_cum`.
PHAN_KHUNG_TOI_THIEU = 0.25

#: Hộp hẹp hơn chừng này (phần bề ngang khung) ⛔ không phải một dòng phụ đề.
#: Tên tài khoản / logo góc rơi ở đây.
RONG_TOI_THIEU = 0.12

#: 🔴 **Cổng an toàn.** Dải cao hơn chừng này ⛔ **không** phải phụ đề — đó là
#:    giao diện, đồ hoạ, hay một cảnh nhiều chữ. Che nó là **làm hỏng video của
#:    khách**, và *"đo sai nguy hơn ⛔ không đo"* (docstring `de_xuat` của ta).
#:
#: ⭐ Lấy từ kho tham chiếu: *"Dải RapidOCR quá RỘNG (> 22 %) — video có thể ⛔
#:    KHÔNG có phụ đề cứng → ⛔ KHÔNG blur"*.
CAO_TOI_DA = 0.22

#: Nới mỗi mép hộp chừng này (phần khung) để vệt mờ ⛔ không hở viền chữ.
NOI_MEP = 0.006

#: Hở thời gian lớn hơn `nhịp lấy mẫu × hệ số này` ⇒ **đoạn mới** (B10-3).
#:
#: ⭐ Đo theo **nhịp lấy mẫu** chứ ⛔ không theo một số giây tuyệt đối: ta chỉ
#:    nhìn `SO_KHUNG_OCR` khung trên cả video, nên "hở" chỉ có nghĩa **tương
#:    đối với khoảng cách giữa hai khung mẫu**. Một hằng số giây sẽ đúng cho
#:    video 5 phút và sai cho video 60 phút.
#:
#: ⛔ `1.5` chứ ⛔ không `1.0`: đúng một khung trượt (OCR không đọc được một
#:    khung giữa câu) ⛔ không được cắt câu làm đôi.
HE_SO_HO = 1.5

#: Tâm y nhảy hơn chừng này giữa hai khung liền ⇒ **đoạn mới**.
#: Cùng bậc với `GOM_CUM_Y` vì hỏi cùng một câu — *"còn là một hàng chữ ⛔
#: không"* — chỉ khác trục: `GOM_CUM_Y` hỏi trong một khung, cái này hỏi qua
#: thời gian.
NHAY_Y = 0.03


#: Trần LÕI cho một lượt dò OCR. 🔴 **Đây là một bản vá SỰ CỐ, ⛔ không phải
#: một tinh chỉnh** — nó gỡ nguyên nhân làm treo máy HAI lần ngày 28/09.
#:
#: ## Sự cố, đo từ hộp đen
#:
#:     12:37:26 -> 12:59:43   TRỐNG 22,3 phút · cpu 99 % · 577 tiến trình
#:     13:12:56 -> 13:21:19   TRỐNG  8,4 phút · cpu 91 % · 338 tiến trình
#:     cả hai lần, tiến trình dẫn đầu:  `-c inline` **1075 %** và **1164 %**
#:
#: Một tiến trình Python ăn ~11 lõi trên 20. Đo lại trên chính máy này:
#:
#:     RapidOCR mặc định  ->  67 luồng · **1519 % = 15,2 lõi** · 1,2 giây
#:
#: 🔑 **`onnxruntime` đặt `intra_op_num_threads = 0`, tức TỰ CHỌN = số lõi vật
#:    lý**, và `rapidocr_onnxruntime.utils.OrtInferSession` dựng `SessionOptions()`
#:    mà ⛔ **không bao giờ** đặt lại — thư viện cũng ⛔ không nhận tham số đó.
#:
#: ## ⛔ `OMP_NUM_THREADS` KHÔNG ăn — đo rồi mới biết
#:
#:     mặc định              15,2 lõi · 1,2 giây
#:     OMP_NUM_THREADS = 4   **12,9 lõi** · 1,4 giây   <- gần như KHÔNG đổi
#:     cpu_affinity([0..3])   **4,2 lõi** · 7,3 giây   <- ăn thật
#:
#: Bản `onnxruntime` này ⛔ không dựng theo OpenMP, nên cần gạt hiển nhiên nhất
#: lại là cần gạt ⛔ không nối vào đâu cả. ⭐ Chỉ phép chặn lõi ở tầng **hệ điều
#: hành** mới cưỡng chế được — cùng lý lẽ với *"chỉ giết thứ mình khởi động"*:
#: luật do OS thi hành, ⛔ không phải do ta nhớ.
#:
#: ## Vì sao 6
#:
#:     N=2   2,1 lõi · 13,1 giây
#:     N=4   4,2 lõi ·  6,5 giây
#:     N=6   6,3 lõi ·  4,9 giây   <- CHỌN
#:     N=8   8,4 lõi ·  3,1 giây
#:
#: ⚠️ Trần phải **chừa biên cho Windows Defender** — nó ăn tới **5,45 lõi** và
#:    nằm **ngoài mọi khoá của ta** (đo 25/09). `6 + 5,45 ≈ 11,5` trên 20 lõi,
#:    còn dư cho gate chạy song song. `N=8` nhanh hơn 1,8 giây nhưng `8 + 5,45
#:    ≈ 13,5` thì một lượt gate 8 bước song song lại chạm trần.
CPU_TRAN_LOI = 6


class OcrLoiKyThuat(RuntimeError):
    """Lỗi KỸ THUẬT — chưa cài, crash, ⛔ không mở được tệp.

    ⛔ **KHÁC** *"quét thật, ⛔ không thấy chữ"* (trả `KetQua` rỗng). Xem bảng
    ba trạng thái ở đầu tệp: hai ca này dẫn tới **hai hành động khác nhau**.
    """


class Hop(NamedTuple):
    """Một hộp chữ trên một khung, toạ độ PHÂN SỐ khung."""

    giay: float
    y0: float
    y1: float
    x0: float
    x1: float


@contextlib.contextmanager
def chan_loi(tran: int = CPU_TRAN_LOI):
    """Chặn tiến trình này xuống `tran` lõi trong lúc chạy OCR, rồi **trả lại**.

    🔴 Xem `CPU_TRAN_LOI`: thiếu phép chặn này, một lượt dò ăn **15,2 lõi trên
       20** và đã làm treo máy hai lần trong một ngày.

    ⛔ **`finally` trả lại đúng tập lõi cũ**, ⛔ không phải `range(cpu_count())`:
       tiến trình có thể ĐÃ bị chặn từ trước (worker chạy dưới một trần khác, hay
       một lượt dò lồng nhau). Trả về *"toàn bộ lõi"* là **nới** một giới hạn của
       người khác — đúng hình dạng *"chốt thay cho người vắng mặt"*.

    ⚠️ Chặn lõi là **per-process**, nên nó cũng chạm mọi thứ khác trong tiến
       trình này. Chấp nhận được vì khối bên trong chỉ có OCR; ⛔ đừng mở rộng
       khối ra ngoài phần TÍNH.

    ⭐ Thiếu `psutil`, hay hệ ⛔ không cho đặt: **đi tiếp mà ⛔ không chặn**, và
       GHI LẠI. Một phép dò chậm còn hơn một phép dò ⛔ không chạy — nhưng im
       lặng bỏ qua thì lần sau ⛔ không ai biết vì sao máy nghẹt lại.
    """
    cu = None
    try:
        import psutil

        me = psutil.Process()
        cu = me.cpu_affinity()
        if cu and len(cu) > tran:
            me.cpu_affinity(cu[:tran])
        else:
            cu = None          # ⛔ Không đặt gì thì ⛔ không phải trả lại gì.
    except Exception as exc:  # noqa: BLE001
        _log.warning("do vung OCR: ⛔ khong chan duoc loi (%s) — luot do nay "
                     "co the an toi ~15 loi", exc)
    try:
        yield
    finally:
        if cu is not None:
            try:
                psutil.Process().cpu_affinity(cu)
            except Exception as exc:  # noqa: BLE001
                _log.warning("do vung OCR: ⛔ khong tra lai duoc tap loi (%s)",
                             exc)


def co_san() -> bool:
    """RapidOCR có dùng được ⛔ không. ⛔ Không ném — người gọi rẽ nhánh."""
    import importlib.util

    return importlib.util.find_spec("rapidocr_onnxruntime") is not None


def _may():
    """Máy OCR, tạo MỘT lần cho cả tiến trình.

    ⚠️ Khởi tạo nạp mô hình ONNX (~10 MB) và mất vài trăm mili giây; tạo lại
       mỗi khung sẽ làm phép đo chậm gấp nhiều lần mà ⛔ không đổi kết quả.
    """
    global _MAY
    try:
        return _MAY
    except NameError:
        pass
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:  # noqa: BLE001
        raise OcrLoiKyThuat(
            _t('Chưa cài bộ đọc chữ trên máy chủ.')) from exc
    try:
        _MAY = RapidOCR()
    except Exception as exc:  # noqa: BLE001
        raise OcrLoiKyThuat(
            _t('Không khởi động được bộ đọc chữ.')) from exc
    return _MAY


def _hop_cua_khung(may, anh, rong: int, cao: int, giay: float
                   ) -> list[Hop] | None:
    """Các hộp chữ trên MỘT khung (mảng BGR của OpenCV).

    Trả `None` = **máy OCR ném ở khung này**. Trả `[]` = **chạy được, ⛔ không
    thấy hộp nào**. ⛔ Hai thứ khác nhau — xem bảng ba trạng thái ở đầu tệp; đây
    là chính bảng ấy, thu nhỏ xuống cấp một khung.

    ⛔ **Một khung hỏng ⛔ không được giết cả lượt dò.** Một khung giải mã lỗi
       giữa 24 khung là chuyện thường; ném ở đây sẽ biến nó thành *"chưa quét
       được"* và đẩy cả lượt xuống tầng lùi — tức đổi một sự cố nhỏ thành một
       quyết định kiến trúc.

    🔴 **Nhưng bản đầu trả `[]` cho CẢ HAI, và đó là một lỗ thật (sửa 28/09).**

       Nếu máy OCR ném ở **mọi** khung thì mọi lượt trả `[]`, `doc_duoc` vẫn
       đếm đủ 24 (khung **đọc** được, ⛔ không phải OCR chạy được), nên
       `do_dai_chu_ocr` trả *"đã quét, ⛔ không thấy chữ"*. Người gọi **TIN** →
       **⛔ không che** → **lộ chữ Hán**.

       ⇒ Đúng cái gộp mà docstring đầu tệp này cấm, do **chính tệp này** phạm.
       Và nó **gộp về phía IM LẶNG** — phía đắt hơn hàng bậc.

    ⚠️ Bánh cóc `check_silent_except` bắt được, ⛔ không phải bộ test của tôi:
       bài `test_mot_khung_HONG_khong_giet_ca_luot` chốt đúng hành vi một khung
       và **⛔ không bao giờ hỏi** *"nếu MỌI khung hỏng thì sao"*.
    """
    try:
        kq, _ = may(anh, use_det=True, use_cls=False, use_rec=False)
    except Exception as exc:  # noqa: BLE001
        # ⛔ `debug` chứ ⛔ không `warning`: một khung hỏng là chuyện thường và
        #    24 dòng cảnh báo cho một lượt dò là nhiễu. Ca **đáng báo** — mọi
        #    khung đều hỏng — do `do_dai_chu_ocr` phát hiện và NÉM.
        _log.debug("do vung OCR: khung %.3f s nem (%s: %s)",
                   giay, type(exc).__name__, exc)
        return None
    ra: list[Hop] = []
    for muc in (kq or ()):
        # ⚠️ Đọc THẬT: `use_rec=False` VẪN trả `[hộp4điểm, văn_bản, điểm]`.
        #    Bản đầu lặp thẳng trên `kq` và nó ném *"float() argument must be
        #    ... not 'list'"*. ⭐ Cờ ấy ⛔ không phải một lời hứa về hình dạng.
        box = muc[0] if isinstance(muc, (list, tuple)) and muc else muc
        try:
            xs = [float(q[0]) for q in box]
            ys = [float(q[1]) for q in box]
        except (TypeError, ValueError, IndexError):
            continue
        if not xs or not ys or rong <= 0 or cao <= 0:
            continue
        ra.append(Hop(giay, min(ys) / cao, max(ys) / cao,
                      min(xs) / rong, max(xs) / rong))
    return ra


def _gom_cum(hop: list[Hop]) -> list[list[Hop]]:
    """Gom hộp thành CỤM theo tâm y — mỗi cụm = một hàng chữ lặp qua các khung.

    🔑 **Gom theo y chứ ⛔ không gộp tất cả làm một.** Gộp hết sẽ dính tên tài
       khoản, watermark và tiêu đề vào cùng một dải — đó chính là cách bộ dò cũ
       cho ra một dải cao 15,5 %.

    ⛔ Gom theo **tâm** chứ ⛔ không theo mép: hai dòng phụ đề kề nhau có mép
       chạm nhau nhưng tâm cách nhau đúng một chiều cao dòng.
    """
    if not hop:
        return []
    theo_tam = sorted(hop, key=lambda h: (h.y0 + h.y1) / 2)
    cum: list[list[Hop]] = [[theo_tam[0]]]
    for h in theo_tam[1:]:
        truoc = cum[-1][-1]
        if abs((h.y0 + h.y1) / 2 - (truoc.y0 + truoc.y1) / 2) <= GOM_CUM_Y:
            cum[-1].append(h)
        else:
            cum.append([h])
    return cum


def _chon_cum(cum: list[list[Hop]], so_khung: int) -> list[list[Hop]]:
    """Cụm nào là phụ đề. Ba điều kiện, và cả ba đều cần.

    - **xuất hiện nhiều khung** — một dòng chữ xuất hiện đúng một lần là một
      tấm biển trong cảnh, ⛔ không phải phụ đề;
    - **đủ rộng** — tên tài khoản / logo góc thì hẹp;
    - **nằm dưới** — đã lọc ở `TAM_Y_TOI_THIEU` trước khi gom.

    ⚠️ Điều kiện *"nhiều khung"* một mình ⛔ **không** loại được watermark tĩnh
       (nó có mặt ở **mọi** khung). Điều kiện *"đủ rộng"* mới loại. Hai điều
       kiện bắt hai thứ khác nhau — bỏ một cái là mở lại một lớp lỗi.
    """
    can = max(2, int(round(so_khung * PHAN_KHUNG_TOI_THIEU)))
    ra = []
    for c in cum:
        if len({round(h.giay, 3) for h in c}) < can:
            continue
        if sum(h.x1 - h.x0 for h in c) / len(c) < RONG_TOI_THIEU:
            continue
        ra.append(c)
    return ra


def _bao(cum: list[Hop]) -> dict:
    """Hộp BAO của một cụm, đã nới mép và kẹp vào khung."""
    return {"y0": round(max(0.0, min(h.y0 for h in cum) - NOI_MEP), 4),
            "y1": round(min(1.0, max(h.y1 for h in cum) + NOI_MEP), 4),
            "x0": round(max(0.0, min(h.x0 for h in cum) - NOI_MEP), 4),
            "x1": round(min(1.0, max(h.x1 for h in cum) + NOI_MEP), 4)}


def do_dai_chu_ocr(duong: str, *, so_khung: int = SO_KHUNG_OCR, tranh=()):
    """Dải chữ gốc bằng OCR. Trả `do_vung.KetQua`.

    ⛔ Ném `OcrLoiKyThuat` khi ⛔ không quét được — xem bảng ba trạng thái ở đầu
    tệp. `KetQua` rỗng nghĩa là **đã quét thật và ⛔ không thấy chữ**.
    """
    # 🔴 Chặn lõi bao TRỌN phần TÍNH — xem `CPU_TRAN_LOI`. Đặt ở đây chứ
    #    ⛔ không trong `_may()`: máy OCR tạo MỘT lần cho cả tiến trình,
    #    còn trần lõi phải sống đúng bằng LƯỢT DÒ.
    with chan_loi():
        return _do_dai_chu_ocr(duong, so_khung=so_khung, tranh=tranh)


def _do_dai_chu_ocr(duong: str, *, so_khung: int, tranh):
    """Thân của `do_dai_chu_ocr`, chạy BÊN TRONG trần lõi."""
    from . import do_vung

    may = _may()
    # ⭐ Dùng LẠI `do_vung._mo`: cùng một cách mở video với tầng lùi, nên hai
    #    tầng ⛔ không thể bất đồng về kích thước khung hay số khung đọc được.
    cv2, _np = do_vung._cv2()
    try:
        cap, rong, cao, _tong, dai = do_vung._mo(cv2, duong)
    except do_vung.DoVungLoi as exc:
        raise OcrLoiKyThuat(str(exc)) from exc

    hop: list[Hop] = []
    doc_duoc = 0
    # ⭐ Hai bộ đếm RIÊNG, và đó là cả điểm: `doc_duoc` đếm khung ĐỌC
    #    được, `ocr_chay` đếm khung OCR CHẠY được. Gộp chúng là gộp
    #    *"đã quét"* với *"lấy được khung"* — hai đại lượng khác nhau.
    ocr_chay = 0
    ocr_hong = 0
    for i in range(so_khung):
        t = dai * (i + 0.5) / so_khung
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, khung = cap.read()
        if not ok or khung is None:
            continue
        doc_duoc += 1
        mot = _hop_cua_khung(may, khung, rong, cao, t)
        if mot is None:
            # ⛔ Máy OCR ném ở khung này — ⛔ KHÔNG tính là "đã quét".
            ocr_hong += 1
            continue
        ocr_chay += 1
        hop.extend(mot)

    if doc_duoc and ocr_chay == 0:
        # 🔴 **MỌI khung đều làm máy OCR ném = CHƯA QUÉT ĐƯỢC.**
        #
        #    Đây là chỗ bản đầu có một lỗ thật: nó đếm `doc_duoc` (khung **đọc**
        #    được) rồi coi đó là bằng chứng *"đã quét"*. Hai đại lượng khác
        #    nhau — đọc được khung ⛔ không có nghĩa OCR chạy được trên nó.
        #
        # ⇒ Ném để người gọi **LÙI TẦNG**, ⛔ không trả rỗng. Trả rỗng ở đây là
        #   nói *"video này ⛔ không có phụ đề cứng"* trong khi sự thật là *"ta
        #   ⛔ không đọc nổi"* — và hậu quả là ⛔ không che ⇒ **lộ chữ Hán**.
        cap.release()
        raise OcrLoiKyThuat(
            _t('Bộ đọc chữ lỗi trên mọi khung hình đã thử.'))

    if doc_duoc == 0:
        # ⛔ ⛔ Không đọc được khung nào = **chưa quét**, ⛔ không phải "không có
        #    chữ". Ném để người gọi lùi tầng — xem bảng ba trạng thái đầu tệp.
        raise OcrLoiKyThuat(_t('Không đọc được khung hình nào để dò vùng.'))

    cap.release()
    duoi = [h for h in hop if (h.y0 + h.y1) / 2 >= TAM_Y_TOI_THIEU]
    chon = _chon_cum(_gom_cum(duoi), doc_duoc)
    if not chon:
        return do_vung.KetQua(vung=(), so_khung=doc_duoc)

    # ⭐ Cổng an toàn đo trên hộp BAO của cả video, ⛔ không trên từng đoạn:
    #    câu hỏi *"video này có phụ đề cứng ⛔ không"* là câu hỏi về CẢ video.
    #    Một đoạn hẹp trong một video toàn chữ vẫn phải bị từ chối.
    bao_het = _bao([h for c in chon for h in c])
    if (bao_het["y1"] - bao_het["y0"]) > CAO_TOI_DA:
        # ⭐ Xem `CAO_TOI_DA`. Trả RỖNG (đã quét, ⛔ không kết luận được là phụ
        #    đề), ⛔ không ném: ta **đã** quét được.
        return do_vung.KetQua(vung=(), so_khung=doc_duoc)
    if do_vung._trung_vung_tay(bao_het["y0"], bao_het["y1"], tranh):
        return do_vung.KetQua(vung=(), so_khung=doc_duoc)

    ra = _theo_doan([h for c in chon for h in c], dai=float(dai),
                    nhip=float(dai) / max(1, so_khung))
    return do_vung.KetQua(vung=tuple(ra), so_khung=doc_duoc)


def _theo_doan(hop: list[Hop], *, dai: float, nhip: float) -> list[dict]:
    """Các hộp theo TỪNG ĐOẠN thời gian, mỗi đoạn một `tu_giay`/`den_giay`.

    🔴 **B10-3 (28/09) — chủ dự án nhìn bản giao và hỏi đúng chỗ này:** *"nó
       che đoạn timeline có text thôi hay che full timeline? trên video mẫu nó
       che 2 dòng từ đầu đến cuối, trong khi có cảnh text 1 dòng."*

       Trước B10-3 ta trả **một** hộp ⛔ không có trường thời gian ⇒ bộ lọc che
       **cả video**, và hộp ấy là **bao của mọi khung** nên cảnh 1 dòng vẫn bị
       che theo dải 2 dòng.

    ⭐ Cơ học để che theo giờ thì **ĐÃ CÓ SẴN** và chưa ai đi qua:
       `vung_che.chuan_hoa` nhận `tu_giay`/`den_giay` (`hinh_hoc.khoang_thoi_gian`),
       `che_do_render._bat_khi` sinh `enable=between(t,…)`, và giao diện có ô
       *"Từ giây"/"Đến giây"*. Thiếu đúng một thứ: **ai điền hai trường đó.**

    ## Cách gom — lấy từ kho tham chiếu, và vì sao từng vế

    Duyệt các khung theo thời gian. Mở đoạn mới khi **một trong ba**:

    - **hở thời gian** > `nhip × HE_SO_HO` — hai lần xuất hiện cách nhau quá
      xa là hai câu khác nhau, ⛔ không phải một câu kéo dài;
    - **nhảy dọc** > `NHAY_Y` — chữ đổi chỗ thì đó là một đoạn khác;
    - ⛔ (⛔ không tách theo `x`: câu căn giữa có `x` gần như nhau, nên tách
      theo `x` chỉ sinh nhiễu — kho tham chiếu đã bỏ vế này.)

    Trong một đoạn thì **hợp** hộp: đoạn hẹp được phủ như đoạn rộng nhất.

    ## ⛔ KẸP Ở ĐIỂM GIỮA hai đoạn kề — vế dễ bỏ sót nhất

    Nới biên mỗi đoạn ra `nhip/2` để ⛔ không hở ở mép, **nhưng** kẹp lại ở
    **điểm giữa** hai đoạn kề. Thiếu vế kẹp thì hai đoạn **chồng thời gian**,
    và ở chỗ chồng có **hai** ô mờ đè nhau — vệt mờ phình ra đúng lúc chuyển
    câu, tức đúng lúc người xem đang nhìn.
    """
    if not hop:
        return []
    theo_gio = sorted(hop, key=lambda h: h.giay)
    tho: list[list[Hop]] = [[theo_gio[0]]]
    for h in theo_gio[1:]:
        truoc = tho[-1][-1]
        tam_truoc = (truoc.y0 + truoc.y1) / 2
        tam = (h.y0 + h.y1) / 2
        if (h.giay - truoc.giay > nhip * HE_SO_HO
                or abs(tam - tam_truoc) > NHAY_Y):
            tho.append([h])
        else:
            tho[-1].append(h)

    ra: list[dict] = []
    for k, doan in enumerate(tho):
        dau, cuoi = doan[0].giay, doan[-1].giay
        bat = max(0.0, dau - nhip / 2)
        ket = min(dai, cuoi + nhip / 2)
        if k > 0:
            bat = max(bat, (tho[k - 1][-1].giay + dau) / 2)
        if k < len(tho) - 1:
            ket = min(ket, (cuoi + tho[k + 1][0].giay) / 2)
        else:
            # ⭐ Đoạn CUỐI phủ tới hết video: một câu sát cuối mà ta cắt đúng
            #    mốc mẫu cuối sẽ **hở đuôi**, và cái hở ấy nằm ở chỗ người xem
            #    dừng lại lâu nhất.
            ket = dai
        if ket - bat <= 0:
            continue
        ra.append({**_bao(doan), "tu_giay": round(bat, 3),
                   "den_giay": round(ket, 3)})
    return ra
