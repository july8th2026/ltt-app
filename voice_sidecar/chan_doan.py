r"""
chan_doan.py — diễn giải SỐ thành PHÁT HIỆN. (K4, tầng CHẨN ĐOÁN.)

## ⛔ TẦNG NÀY KHÔNG ĐƯỢC IMPORT numpy, soundfile, torch

Đó là luật của hệ cũ (`VOICE_DIAGNOSTICS_RULES.md`, Rule 2), và nó là thứ đáng
mang sang nhất trong cả hệ ấy:

    metrics/   → CHỈ tính số. Không diễn giải, không phán "tốt/xấu".
    diagnosis/ → CHỈ diễn giải số. Không xử lý âm thanh.
    report/    → CHỈ định dạng.

⭐ Vì sao ranh giới ấy đáng cưỡng chế chứ không chỉ đáng khuyên: khi một tệp
   vừa đo vừa phán, **không ai còn tách được "số đo sai" khỏi "cách đọc sai"**.
   Cả K3 mất hai lượt đo vì đúng chuyện đó — tôi sửa chỉ số để đuổi theo một
   ngưỡng, trong khi thứ hỏng là cái thước.

   Tách ra thì hai câu hỏi tách ra: *số này đúng chưa* (metrics) và *đọc thế
   này đúng chưa* (diagnosis). Và tầng dưới **chạy được ở mọi nơi** — không GPU,
   không thư viện âm thanh — nên nó test được rẻ và nhiều.

Bánh cóc canh ranh giới: `tests/test_388_chan_doan.py`.

## ⛔ NGƯỠNG ĐẾN TỪ BASELINE ĐÃ ĐO, KHÔNG TỪ HẰNG SỐ GÕ TAY

Hệ cũ có `delta_brightness < -3`, `delta_f0_mean < -5`, `delta_hnr < -3`. Đó là
ngưỡng đã hiệu chuẩn cho **F5-TTS**, trên dữ liệu của hệ ấy. Chép sang đây là
có một cổng trông chín chắn mà không ai biết nó bắt được gì.

⇒ Mọi luật ở đây nhận `san` — một dict `{ten_chi_so: {"tb", "lech"}}` do
  `tools/do_lech_tham_chieu.py` đo trên chính hệ này — và phát hiện khi giá trị
  lệch quá `HE_SO_LECH` lần độ lệch chuẩn. Không có `san` thì **không phán gì**,
  và nói ra là chưa đo, chứ không im lặng cho qua.

⭐ VÀ LẦN NÀY CÓ BẰNG CHỨNG TRỰC TIẾP, không phải một lời khuyên chung.

   Baseline đo 01/09 trên 8 giọng × 3 câu (`voice_sidecar/baseline_lech.json`):

       delta_db_dai_cao            tb  **-3,65 dB**   lech 3,38
       delta_vat_95_hz_ti_le       tb    -0,249       lech 0,188
       delta_trong_tam_hz_ti_le    tb    -0,153       lech 0,149
       delta_f0_tan_tuong_doi      tb    -0,072       lech 0,042
       delta_f0_trung_vi_hz_ti_le  tb    -0,003       lech 0,047
       delta_lufs                  tb    -0,112       lech 1,130

   Ngưỡng của hệ cũ là `delta_brightness < -3`. **Lệch hệ thống của ta là
   -3,65.** Chép con số ấy sang thì R12a nổ ở **100% số bản khoẻ mạnh** — một
   cổng kêu ở mọi bản là một cổng bị tắt trong một tuần, và nó kéo theo cả
   những luật đúng nằm cạnh.

🔴 Và bảng trên nói một điều về chính engine, không chỉ về ngưỡng: bản sinh ra
   **tối hơn và đơn điệu hơn clip nguồn một cách hệ thống** — mất ~3,6 dB trên
   4 kHz, vắt-95% tụt 25%, độ tản F0 giảm 7%. Đó là chữ ký quen thuộc của một
   codec neural, không phải một lỗi. Nhưng nó cũng có nghĩa: **`delta_f0_trung_vi`
   gần như bằng 0 (-0,003)** — tâm cao độ được giữ rất tốt. Nhân bản đúng
   *người*, chỉ hơi mất *độ trong*.
"""
from __future__ import annotations

#: Lệch quá bao nhiêu lần độ lệch chuẩn thì thành một phát hiện.
#:
#: ⭐ 4, cùng con số bộ dò điểm mù K3 dùng, và cố ý cùng: hai công cụ đọc cùng
#:    một loại dữ liệu bằng hai ngưỡng khác nhau thì không đối chiếu được với
#:    nhau, và người đọc sẽ phải nhớ cái nào là cái nào.
HE_SO_LECH = 4.0

#: Sàn tuyệt đối cho từng chỉ số — dùng khi độ lệch chuẩn đo được quá nhỏ.
#:
#: ⛔ KHÔNG phải ngưỡng phát hiện. Nó là **sàn** cho dải dung sai: một chỉ số
#:    tình cờ rất ổn định trong lô đo baseline sẽ có `lech` bé xíu, và 4×lech
#:    thành một dải hẹp tới mức mọi bản đều "bất thường". Cùng vai trò với
#:    `SAN_DUNG_SAI` của cổng V10.
SAN = {
    "delta_trong_tam_hz_ti_le": 0.08,
    "delta_vat_95_hz_ti_le": 0.15,
    "delta_vat_99_hz_ti_le": 0.15,
    "delta_f0_trung_vi_hz_ti_le": 0.04,
    "delta_db_dai_cao": 2.0,
    "delta_f0_tan_tuong_doi": 0.03,
    "delta_dao_dong_khung": 0.05,
    "delta_lufs": 1.5,
}

#: Luật: `(ma, chi_so, chieu, nhan, khuyen_nghi)`.
#:
#: `chieu`: `-1` chỉ báo khi lệch ÂM · `+1` chỉ khi DƯƠNG · `0` cả hai phía.
#:
#: ⭐ Mã luật giữ nguyên số của hệ cũ (R11–R17) **có chủ ý**: ai đọc báo cáo của
#:    hệ cũ sẽ nhận ra ngay, và ai đi tìm "R12 là gì" sẽ tìm thấy cùng một khái
#:    niệm ở cả hai nơi. Đổi số cho gọn là vứt đi phần duy nhất của hệ cũ mà
#:    người dùng đã thuộc.
LUAT = (
    ("R12a", "delta_db_dai_cao", -1,
     "Bản sinh ra ĐỤC hơn tham chiếu",
     "Clip tham chiếu có thể đang bị lọc/nén. Thử một clip thu sạch hơn."),
    ("R12b", "delta_db_dai_cao", +1,
     "Bản sinh ra CHÓI hơn tham chiếu",
     "Thường đi cùng nhiễu nền trong bản sinh ra. Xem `dnsmos_bak`."),
    ("R12c", "delta_trong_tam_hz_ti_le", 0,
     "Trọng tâm phổ lệch so với tham chiếu",
     "Âm sắc đã dịch. Nếu kèm R12a/R12b thì đó là cùng một hiện tượng."),
    ("R13", "delta_f0_trung_vi_hz_ti_le", -1,
     "Bản sinh ra TRẦM hơn tham chiếu",
     "Kiểm clip tham chiếu có bị lẫn giọng thứ hai trầm hơn không."),
    ("R14", "delta_f0_trung_vi_hz_ti_le", +1,
     "Bản sinh ra CAO hơn tham chiếu",
     "Kiểm clip tham chiếu có đoạn thều thào hoặc hụt hơi không."),
    ("R15", "delta_f0_tan_tuong_doi", -1,
     "Bản sinh ra ĐƠN ĐIỆU hơn tham chiếu",
     "Ngữ điệu bị san phẳng. Thử một clip tham chiếu có nhiều lên xuống hơn."),
    ("R16", "delta_dao_dong_khung", +1,
     "Biên độ bản sinh ra DAO ĐỘNG mạnh hơn tham chiếu",
     "Có thể là rung giọng hoặc nhiễu. Nghe lại trước khi kết luận."),
    ("R17", "delta_lufs", 0,
     "Độ to lệch so với tham chiếu",
     "Không phải lỗi chất lượng: đường sinh có chuẩn hoá độ to riêng."),
)

#: 🔴 CHẨN ĐOÁN LÀ TƯ VẤN, KHÔNG PHẢI PHÁN QUYẾT. `do_chat_luong.phan_quyet`
#:    KHÔNG đọc kết quả ở đây, và đó là một quyết định chứ không phải một thiếu
#:    sót.
#:
#:    Lý do: phần lớn các luật R11–R17 chỉ ra một vấn đề ở **clip tham chiếu
#:    của khách**, không phải ở đầu ra của ta. R12a nói "clip tham chiếu có thể
#:    đang bị lọc"; R13 nói "clip có thể lẫn giọng thứ hai". Đánh trượt lượt
#:    sinh của ta vì đầu vào của khách là bắt khách trả tiền cho một lượt bị
#:    chặn mà họ không sửa được từ phía ta.
#:
#: ⭐ Ranh giới đúng: **phán quyết** dựa trên hợp đồng tuyệt đối của ta (độ to,
#:    đỉnh thật, toàn vẹn, dễ hiểu); **chẩn đoán** nói cho khách biết vì sao
#:    giọng nghe không giống như họ mong, và phải đổi gì ở clip nguồn.
#:
#: Mức nghiêm trọng theo bội số của dải dung sai.
MUC = ((8.0, "nang"), (4.0, "vua"), (0.0, "nhe"))


def _muc(ti_le: float) -> str:
    for nguong, ten in MUC:
        if ti_le >= nguong:
            return ten
    return "nhe"


def chan_doan(lech: dict, san: dict | None) -> dict:
    """`{da_do, phat_hien: [...], ly_do_khong_do}`.

    ⛔ KHÔNG có `san` thì trả `da_do=False` và NÓI RA. Một tầng chẩn đoán im
       lặng khi thiếu ngưỡng trông y hệt một tầng chẩn đoán không thấy gì bất
       thường — và hai câu ấy dẫn tới hai hành động ngược nhau.
    """
    if not san:
        return {"da_do": False, "phat_hien": [],
                "ly_do_khong_do": ("chua co baseline cho cac chi so lech — "
                                   "chay `tools/do_lech_tham_chieu.py --ghim`")}
    if not lech:
        return {"da_do": False, "phat_hien": [],
                "ly_do_khong_do": "khong do duoc chi so lech nao"}

    ra = []
    for ma, chi_so, chieu, nhan, khuyen in LUAT:
        v = lech.get(chi_so)
        s = san.get(chi_so)
        if v is None or not s:
            continue
        tb = float(s.get("tb", 0.0))
        dung = max(HE_SO_LECH * float(s.get("lech", 0.0)), SAN.get(chi_so, 0.0))
        if dung <= 0:
            continue
        cach = float(v) - tb
        if chieu < 0 and cach >= -dung:
            continue
        if chieu > 0 and cach <= dung:
            continue
        if chieu == 0 and abs(cach) <= dung:
            continue
        ra.append({
            "ma": ma, "chi_so": chi_so, "gia_tri": round(float(v), 5),
            "nen": round(tb, 5), "dung_sai": round(dung, 5),
            "muc": _muc(abs(cach) / dung),
            "nhan": nhan, "khuyen_nghi": khuyen,
        })
    # Nặng trước: một danh sách không xếp hạng thì người đọc phải tự xếp, và họ
    # sẽ xếp theo thứ tự nó tình cờ được in ra.
    thu_tu = {"nang": 0, "vua": 1, "nhe": 2}
    ra.sort(key=lambda x: (thu_tu.get(x["muc"], 9), x["ma"]))
    return {"da_do": True, "phat_hien": ra, "ly_do_khong_do": ""}


def tom_tat(kq: dict) -> str:
    """Một dòng cho log. Tầng report tối giản."""
    if not kq.get("da_do"):
        return f"chan doan: KHONG DO ({kq.get('ly_do_khong_do')})"
    pf = kq.get("phat_hien") or []
    if not pf:
        return "chan doan: khong lech gi qua nguong"
    return "chan doan: " + " | ".join(
        f"{p['ma']} {p['muc']} ({p['chi_so']}={p['gia_tri']})" for p in pf)
