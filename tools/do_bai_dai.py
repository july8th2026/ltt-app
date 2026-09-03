r"""
do_bai_dai.py — BẢN ĐỌC GHÉP có giữ được chất lượng của bản một lượt không?

    powershell -ExecutionPolicy Bypass -File .\setup\do_bai_dai.ps1

## Câu hỏi, và vì sao nó là điều kiện DUY NHẤT còn lại

`apps/ltt_voice/tham_so_cong_khai.py` nói thẳng: đường văn bản dài **đã xây
xong** — `chia_doan` chia, `/v1/speech-dai` sinh nhiều lượt rồi ghép — nhưng
`TRAN_KY_TU_CONG_KHAI` vẫn giữ 1.500 *"cho tới khi đo được chất lượng bản GHÉP ở
3.000 và 5.000 ký tự"*. Hạ tầng sẵn sàng không phải bằng chứng chất lượng.

Một chiều đã đo (01/09, `tools/do_troi_tong.py`): **trôi tông không có**. Nhưng
chính tệp ấy cảnh báo đừng đọc điều đó thành "nới được rồi" — V10 còn CER/WER,
tương đồng người nói, clipping, tỉ lệ hỏng. Tệp này đo những chiều còn lại, trên
**cùng một bản ghép**, ở nhiều độ dài.

## Cách đo, và vì sao ĐỐI CHỨNG nằm bên trong chính phép đo

⛔ Không có ngưỡng tuyệt đối nào cho CER hay cosine người nói. Cùng lý do
   `tools/cong_chat_luong_voice.py` đã ghi: con số duy nhất có nghĩa là **so với
   chính hệ thống này**. Nên phép đo này mang theo hai đối chứng:

    ① ĐỐI CHỨNG ĐỘ DÀI — bài 1.500 ký tự đi đường MỘT LƯỢT (`/v1/speech`).
       Đó đúng là thứ sản phẩm đang bán hôm nay. Mọi bài dài hơn phải được so
       với nó, không so với một hằng số.

    ② SÀN NHIỄU NGƯỜI NÓI — cắt đôi từng đoạn rồi so hai nửa với nhau. Hai nửa
       của một đoạn chắc chắn là cùng người, nên cosine của chúng là mức "giống
       nhau nhất có thể đạt" của thước đo này. Cùng thủ pháp mà
       `voice_sidecar/do_giu_giong_nhieu_luot.py` đã dùng.

⭐ VÀ MỘT ĐỐI CHỨNG THỨ BA, RẺ, đến từ chính cách dựng bài: corpus được **lặp
   vòng** để đạt độ dài mục tiêu. Nên đoạn thứ k và đoạn thứ k+len(CORPUS) có
   **cùng văn bản** ở **hai vị trí khác nhau trong bài**. Chênh lệch giữa chúng
   không thể do nội dung — nó chỉ có thể do VỊ TRÍ. Đó chính xác là thứ #168 mô
   tả ("lỗi xuất hiện nhiều khi xử lý text dài"), và nó tách được khỏi cái nhiễu
   "câu này khó đọc hơn câu kia" mà mọi phép đo CER đều dính.

## ⛔ Không phán quyết ĐẠT/HỎNG ở đây

Cùng nguyên tắc `do_chat_luong.py` và `do_troi_tong.py` đã chốt: báo SỐ kèm SÀN,
người đọc quyết định. Một tệp đo tự tuyên bố "PASS" là một tệp đo sẽ được trích
ra khỏi ngữ cảnh.

⚠️ Chạm GPU thật, không chạm sổ tiền (gọi thẳng cổng giọng).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ⛔ `reconfigure`, KHÔNG bọc lại `sys.stdout` bằng một TextIOWrapper mới —
#    `test_353` chốt việc này, và một lượt đo dài PHẢI theo dõi được khi log đi
#    ra tệp (đệm khối làm tệp nằm im ở 0 byte hàng chục phút).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

#: Giọng người lớn nằm gọn trong khoảng này. Hẹp hơn mặc định của librosa để
#: `pyin` không đi lạc lên hoà âm bậc hai — xem `tools/do_troi_tong.py`.
F0_MIN, F0_MAX = 70.0, 400.0

#: Độ dài bài cần đo.
#:
#: 🔴 1.400 CHỨ KHÔNG PHẢI 1.500 CHO ĐỐI CHỨNG, và con số ấy là một phép đo.
#:
#:    Đối chứng phải là đường MỘT LƯỢT — thứ sản phẩm đang bán hôm nay. Nhưng
#:    `dung_bai(1500)` cho 1.584 ký tự thô, chuẩn hoá nở lên 1.591, và thế là
#:    nó **vượt** trần một lượt: `chuan_bi` chia nó thành 2 đoạn. Một "đối
#:    chứng" đã đi qua phép ghép thì không còn là đối chứng của phép ghép.
#:
#:    `dung_bai(1400)` cho 1.462 ký tự sau chuẩn hoá ⇒ đúng 1 đoạn. Đã kiểm.
#:
#: ⚠️ Vẫn giữ 1.500 trong danh sách: nó là ca ghép NHỎ NHẤT có thể có (2 đoạn),
#:    tức chỗ một mối nối đơn độc lộ ra rõ nhất, không bị pha loãng bởi 40 mối
#:    nối khác. 3.000 và 5.000 là hai mốc `tham_so_cong_khai.py` đòi đích danh;
#:    10.000 để xem xu hướng có tiếp tục ngoài hai mốc ấy không.
DO_DAI = (1400, 1500, 3000, 5000, 10000)

#: Mười hai đoạn văn xuôi tiếng Việt, chủ đề khác nhau, độ khó khác nhau (có số,
#: có tên riêng, có câu dài câu ngắn). Bài dài được dựng bằng cách LẶP VÒNG danh
#: sách này — xem đối chứng ③ ở đầu tệp.
CORPUS = [
    "Chào các bạn, hôm nay tôi muốn kể một câu chuyện về nghề làm gốm ở làng "
    "Bát Tràng, nơi mà những người thợ vẫn giữ cách nung củi từ hàng trăm năm "
    "trước.",
    "Buổi sáng ở chợ nổi Cái Răng bắt đầu từ lúc bốn giờ, khi những chiếc ghe "
    "chở đầy trái cây từ các cù lao đổ về, và tiếng máy nổ vang khắp một khúc "
    "sông rộng.",
    "Một nghiên cứu công bố năm 2019 cho thấy trẻ em đọc sách cùng cha mẹ mỗi "
    "ngày mười lăm phút có vốn từ vựng nhiều hơn đáng kể so với nhóm không "
    "được đọc cùng.",
    "Anh Nam mở quán cà phê nhỏ trên đường Nguyễn Huệ từ năm 2015, và đến nay "
    "vẫn tự tay rang từng mẻ hạt vào mỗi sáng thứ bảy.",
    "Khi nước sông dâng cao, người dân vùng đồng bằng phải kê giường lên cao "
    "hơn mặt sàn khoảng năm mươi phân, một thói quen được truyền lại qua nhiều "
    "thế hệ.",
    "Chiếc cầu dài 1.250 mét bắc qua sông được khánh thành vào tháng ba, rút "
    "ngắn quãng đường đi lại giữa hai huyện từ bốn mươi cây số xuống còn "
    "mười hai.",
    "Bà tôi thường nói rằng muốn nấu được nồi canh chua ngon thì phải chọn cá "
    "còn tươi, me phải là me chín cây, và quan trọng nhất là đừng vội.",
    "Trong buổi họp, giám đốc trình bày kế hoạch mở rộng nhà máy với tổng vốn "
    "đầu tư khoảng 1.500.000.000 đồng, dự kiến hoàn thành trong hai năm.",
    "Mùa lúa chín, cả cánh đồng ngả sang màu vàng óng, và từ trên đê nhìn "
    "xuống người ta chỉ thấy một tấm thảm trải dài tới tận chân trời.",
    "Chương trình đào tạo kéo dài sáu tháng, gồm ba mươi buổi lý thuyết và "
    "hai mươi buổi thực hành, dành cho học viên đã tốt nghiệp trung học phổ "
    "thông.",
    "Ông cụ ngồi bên hiên nhà, tay cầm chiếc quạt nan đã sờn, kể lại chuyện "
    "ngày xưa đi bộ mấy chục cây số chỉ để mua một quyển sách.",
    "Nhóm tình nguyện viên đã trồng được hơn hai nghìn cây con dọc bờ biển "
    "trong ba tháng, và tỉ lệ cây sống sau mùa mưa đầu tiên đạt gần chín "
    "mươi phần trăm.",
]


class ThieuTruong(RuntimeError):
    """Dụng cụ đo thiếu một thứ nó CẦN. Không lui về đường đoán."""


# ══════════════════════════════════════════════════════ dựng bài và đo ════

def dung_bai(muc_tieu: int) -> str:
    """Ghép các đoạn của CORPUS (lặp vòng) cho tới khi đủ dài.

    Cắt ở RANH GIỚI ĐOẠN, không cắt giữa đoạn: một bài kết thúc bằng nửa câu sẽ
    làm đoạn cuối có CER cao vì lý do chẳng liên quan gì tới độ dài bài.
    """
    manh, tong = [], 0
    i = 0
    while tong < muc_tieu:
        d = CORPUS[i % len(CORPUS)]
        manh.append(d)
        tong += len(d) + 1
        i += 1
    return " ".join(manh)


def _doc_wav(raw: bytes):
    import io

    import soundfile as sf
    w, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
    if getattr(w, "ndim", 1) > 1:
        w = w.mean(axis=1)
    return w, int(sr)


def _f0_trung_vi(wav, sr: int):
    """`(trung_vi, lech)` của F0 trên các khung CÓ TIẾNG. `None` khi không có."""
    import librosa
    import numpy as np
    f0, co_tieng, _ = librosa.pyin(
        np.asarray(wav, dtype=np.float32), sr=sr,
        fmin=F0_MIN, fmax=F0_MAX, frame_length=2048)
    v = [float(x) for x, c in zip(f0, co_tieng) if c and x == x]
    if len(v) < 2:
        return None
    return statistics.median(v), statistics.pstdev(v)


def _do_mot_doan(bo, wav, sr: int, text: str, giu_asr: bool) -> dict:
    """Mọi số đo của MỘT đoạn đã cắt ra từ bản ghép."""
    from voice_sidecar import do_chat_luong

    ra: dict = {"so_ky_tu": len(text), "giay": len(wav) / float(sr) if sr else 0.0}

    ra["tin_hieu"] = do_chat_luong.do_tin_hieu(wav, sr)

    f0 = _f0_trung_vi(wav, sr)
    ra["f0_trung_vi"] = round(f0[0], 2) if f0 else None
    ra["f0_lech_trong_doan"] = round(f0[1], 2) if f0 else None

    # ── embedding người nói, + SÀN NHIỄU của chính đoạn này ─────────────────
    #
    # ⛔ Sàn phải đo trên CÙNG đoạn, không lấy một hằng số từ lượt đo khác: nó
    #    phụ thuộc độ dài đoạn và nội dung, nên một sàn mượn là một sàn sai.
    ra["emb"] = None
    ra["san_nhieu_nua_doan"] = None
    if bo is not None:
        e = do_chat_luong._embed(bo, wav, sr)
        ra["emb"] = None if e is None else [float(x) for x in e]
        nua = len(wav) // 2
        if nua > sr:                       # mỗi nửa ít nhất một giây
            a = do_chat_luong._embed(bo, wav[:nua], sr)
            b = do_chat_luong._embed(bo, wav[nua:], sr)
            if a is not None and b is not None:
                ra["san_nhieu_nua_doan"] = round(do_chat_luong._cosine(a, b), 4)

    if giu_asr:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        try:
            import soundfile as sf
            sf.write(tmp.name, wav, sr)
            tmp.close()
            ra["de_hieu"] = do_chat_luong.do_de_hieu(tmp.name, text)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
    else:
        ra["de_hieu"] = {"co": False, "ly_do": "bo qua theo yeu cau"}
    return ra


def do_mot_bai(muc_tieu: int, *, giu_asr: bool = True) -> dict:
    """Sinh một bài dài `muc_tieu` ký tự qua ĐÚNG đường sản phẩm, rồi đo."""
    from apps.ltt_voice import text_pipeline
    from apps.ltt_voice import sidecar_client
    from apps.ltt_voice.tham_so_cong_khai import TRAN_MOI_LUOT_SINH
    from voice_sidecar import do_chat_luong

    tho = dung_bai(muc_tieu)

    # ⭐ ĐÚNG đường sản phẩm: cùng hàm chuẩn hoá, cùng trần một lượt mà
    #    `jobs._tao_tieng` dùng. Đo một đường khác đường bán là đo nhầm thứ.
    chuan = text_pipeline.chuan_bi(tho, tran_moi_doan=TRAN_MOI_LUOT_SINH)
    doan = chuan.doan or [chuan.da_chuan_hoa]

    print(f"\n{'=' * 68}\n[bai {muc_tieu} ky tu] tho {len(tho)} -> chuan hoa "
          f"{len(chuan.da_chuan_hoa)} -> {len(doan)} doan")

    duong = "mot luot" if len(doan) == 1 else "ghep nhieu luot"
    print(f"  duong: {duong}")

    hong = 0
    try:
        if len(doan) == 1:
            raw, dau = sidecar_client.noi(doan[0])
        else:
            raw, dau = sidecar_client.noi_dai(list(doan))
    except Exception as e:                              # noqa: BLE001
        print(f"  [HONG] {type(e).__name__}: {e}")
        return {"muc_tieu": muc_tieu, "hong": True, "loi": f"{type(e).__name__}: {e}"}

    w, sr = _doc_wav(raw)
    doc = {str(k).lower(): v for k, v in dict(dau or {}).items()}

    # ── cắt lại theo MỐC THẬT ───────────────────────────────────────────────
    #
    # ⛔ KHÔNG lui về chia đều khi thiếu mốc. Bản ghép chèn nghỉ giữa các đoạn,
    #    nên chia đều sai LUỸ TIẾN và tự sinh ra một xu hướng đơn điệu — đúng
    #    hình dạng của thứ ta đang đi tìm. `do_troi_tong.py` đã dính đúng bẫy
    #    này ngày 01/09 và cho ra một "phát hiện" rất thuyết phục nhưng là giả.
    if len(doan) == 1:
        moc = [0.0, len(w) / float(sr)]
    else:
        raw_moc = (doc.get("x-moc-s") or "").strip()
        if not raw_moc:
            raise ThieuTruong(
                "dau phan hoi thieu X-Moc-S. Chia deu se cat lech luy tien va "
                f"sinh ra mot xu huong GIA. Dau co: {sorted(doc)}")
        moc = [float(x) for x in raw_moc.split(",") if x.strip()]
        if len(moc) != len(doan) + 1:
            raise ThieuTruong(
                f"X-Moc-S co {len(moc)} moc cho {len(doan)} doan; can "
                f"{len(doan) + 1}")

    bo = do_chat_luong._bo_ma_hoa_giong()
    if bo is None:
        print("  [!] khong nap duoc bo ma hoa nguoi noi — bo qua tuong dong")

    ho_so = []
    for i, t in enumerate(doan):
        seg = w[int(moc[i] * sr):int(moc[i + 1] * sr)]
        if len(seg) < sr // 2:
            hong += 1
            print(f"  doan {i + 1:3d}: [HONG] chi {len(seg)} mau")
            ho_so.append({"hong": True, "so_ky_tu": len(t)})
            continue
        d = _do_mot_doan(bo, seg, sr, t, giu_asr)
        d["chi_so"] = i
        ho_so.append(d)
        dh = d.get("de_hieu") or {}
        print(f"  doan {i + 1:3d}: {d['giay']:6.2f}s  "
              f"F0 {d['f0_trung_vi'] or 0:6.1f}Hz  "
              f"CER {dh.get('cer', float('nan')):.4f}  "
              f"phu {dh.get('ty_le_phu', float('nan')):.3f}")

    return {
        "muc_tieu": muc_tieu,
        "hong": False,
        "so_ky_tu_tho": len(tho),
        "so_ky_tu_chuan": len(chuan.da_chuan_hoa),
        "so_doan": len(doan),
        "duong": duong,
        "giay_tong": len(w) / float(sr) if sr else 0.0,
        "x_gen_s": doc.get("x-gen-s"),
        "x_rtf": doc.get("x-rtf"),
        "x_nghi_s": doc.get("x-nghi-s"),
        "x_nguon_nghi": doc.get("x-nguon-nghi"),
        "ty_le_hong": hong / float(max(1, len(doan))),
        "doan": ho_so,
    }


# ══════════════════════════════════════════════════════════ tổng hợp ════

def _do_doc(v: list) -> dict:
    """min / p05 / trung vị / max — KHÔNG chỉ trung bình.

    Một trung bình giấu đúng thứ ta đi tìm: một đoạn hỏng trong bốn mươi đoạn
    tốt vẫn cho một trung bình đẹp, mà người nghe thì nghe thấy đoạn hỏng ấy.
    """
    v = [float(x) for x in v if x is not None and x == x]
    if not v:
        return {}
    s = sorted(v)
    return {
        "n": len(s),
        "min": round(s[0], 4),
        "p05": round(s[max(0, int(0.05 * (len(s) - 1)))], 4),
        "trung_vi": round(statistics.median(s), 4),
        "max": round(s[-1], 4),
        "lech": round(statistics.pstdev(s), 4) if len(s) > 1 else 0.0,
    }


def _doc_dinh(y: list) -> float:
    """Độ dốc hồi quy tuyến tính theo CHỈ SỐ ĐOẠN. Dấu cho biết chiều trôi."""
    y = [float(v) for v in y if v is not None and v == v]
    n = len(y)
    if n < 3:
        return 0.0
    x = list(range(n))
    mx, my = sum(x) / n, sum(y) / n
    tu = sum((a - mx) * (b - my) for a, b in zip(x, y))
    mau = sum((a - mx) ** 2 for a in x)
    return round(tu / mau, 6) if mau else 0.0


def tong_hop(bai: dict) -> dict:
    """Gộp các đoạn của một bài thành bảng số đọc được."""
    if bai.get("hong"):
        return {"hong": True}
    ok = [d for d in bai["doan"] if not d.get("hong")]
    if not ok:
        return {"hong": True, "ly_do": "khong doan nao do duoc"}

    cer = [(d.get("de_hieu") or {}).get("cer") for d in ok]
    wer = [(d.get("de_hieu") or {}).get("wer") for d in ok]
    phu = [(d.get("de_hieu") or {}).get("ty_le_phu") for d in ok]
    f0 = [d.get("f0_trung_vi") for d in ok]
    tp = [(d.get("tin_hieu") or {}).get("true_peak_dbtp") for d in ok]
    tran = [(d.get("tin_hieu") or {}).get("ty_le_cham_tran") for d in ok]
    san = [d.get("san_nhieu_nua_doan") for d in ok]

    # ── tương đồng người nói: ba trục, và mỗi trục trả lời một câu khác nhau ──
    #
    #   voi_dau     đoạn i so với đoạn 1  -> trôi TÍCH LUỸ (thứ #168 mô tả)
    #   ke_nhau     đoạn i so với đoạn i-1 -> đứt gãy ĐỘT NGỘT ở một mối nối
    #   dau_cuoi    đoạn 1 so với đoạn N  -> tổng khoảng cách hai đầu bài
    from voice_sidecar import do_chat_luong
    import numpy as np

    embs = [np.asarray(d["emb"], dtype=np.float32) if d.get("emb") else None
            for d in ok]
    voi_dau, ke_nhau = [], []
    if embs and embs[0] is not None:
        for i, e in enumerate(embs):
            if e is None:
                continue
            if i:
                voi_dau.append(do_chat_luong._cosine(embs[0], e))
            if i and embs[i - 1] is not None:
                ke_nhau.append(do_chat_luong._cosine(embs[i - 1], e))
    dau_cuoi = None
    if len(embs) > 1 and embs[0] is not None and embs[-1] is not None:
        dau_cuoi = round(do_chat_luong._cosine(embs[0], embs[-1]), 4)

    # ── đối chứng ③: cùng văn bản, hai vị trí khác nhau trong bài ────────────
    theo_van_ban: dict = {}
    for d in ok:
        theo_van_ban.setdefault(d["so_ky_tu"], []).append(d)
    lap = {}
    for _, ds in theo_van_ban.items():
        if len(ds) < 2:
            continue
        c = [(x.get("de_hieu") or {}).get("cer") for x in ds]
        c = [v for v in c if v is not None]
        if len(c) >= 2:
            lap.setdefault("cer_cung_van_ban_bien_thien", []).append(
                round(max(c) - min(c), 4))

    return {
        "so_doan": len(ok),
        "cer": _do_doc(cer),
        "wer": _do_doc(wer),
        "ty_le_phu": _do_doc(phu),
        "f0_trung_vi": _do_doc(f0),
        "true_peak_dbtp": _do_doc(tp),
        "ty_le_cham_tran": _do_doc(tran),
        "san_nhieu_nua_doan": _do_doc(san),
        "nguoi_noi_voi_dau": _do_doc(voi_dau),
        "nguoi_noi_ke_nhau": _do_doc(ke_nhau),
        "nguoi_noi_dau_cuoi": dau_cuoi,
        "doc_cer_theo_doan": _doc_dinh(cer),
        "doc_f0_theo_doan": _doc_dinh(f0),
        "doc_nguoi_noi_theo_doan": _doc_dinh(voi_dau),
        "cung_van_ban_khac_vi_tri": lap,
        "ty_le_hong": bai.get("ty_le_hong"),
    }


def _in_bang(kq: dict) -> None:
    print(f"\n{'=' * 68}\nTONG HOP\n{'=' * 68}")
    hang = ("cer", "wer", "ty_le_phu", "nguoi_noi_voi_dau",
            "nguoi_noi_ke_nhau", "san_nhieu_nua_doan", "f0_trung_vi",
            "true_peak_dbtp")
    dai = sorted(kq["bai"], key=lambda x: int(x))
    print(f"{'chi so':<26}" + "".join(f"{d + ' ky tu':>16}" for d in dai))
    for h in hang:
        dong = f"{h:<26}"
        for d in dai:
            t = (kq["bai"][d].get("tong_hop") or {}).get(h) or {}
            dong += (f"{t.get('trung_vi', float('nan')):>16.4f}"
                     if t else f"{'-':>16}")
        print(dong)
    print(f"\n{'(min cua chi so)':<26}" + "".join(
        f"{((kq['bai'][d].get('tong_hop') or {}).get('nguoi_noi_voi_dau') or {}).get('min', float('nan')):>16.4f}"
        for d in dai) + "   <- nguoi_noi_voi_dau MIN")
    for h in ("doc_cer_theo_doan", "doc_nguoi_noi_theo_doan", "ty_le_hong"):
        dong = f"{h:<26}"
        for d in dai:
            v = (kq["bai"][d].get("tong_hop") or {}).get(h)
            dong += f"{v:>16.6f}" if isinstance(v, (int, float)) else f"{'-':>16}"
        print(dong)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--do-dai", default=",".join(str(x) for x in DO_DAI),
                    help="danh sach do dai bai, ngan bang dau phay")
    ap.add_argument("--bo-asr", action="store_true",
                    help="bo qua CER/WER (nhanh hon nhieu, dung de thu duong di)")
    ap.add_argument("--json", default="tmp/do_bai_dai.json")
    a = ap.parse_args(argv)

    # ⛔ TỰ KIỂM DỤNG CỤ Ở DÒNG ĐẦU, trước khi chạm GPU một lần nào. Bản đầu của
    #    `do_troi_tong.py` sinh mười hai lượt rồi mới chết ở `import soundfile`.
    thieu = []
    for ten in ("numpy", "soundfile", "librosa"):
        try:
            __import__(ten)
        except ImportError:
            thieu.append(ten)
    if thieu:
        print(f"THIEU {thieu} — chay bang python cua `vieneu-venv` "
              f"(LTT_VIENEU_PYTHON), khong phai venv nen tang.", file=sys.stderr)
        return 2

    from apps.ltt_voice import sidecar_client
    if not sidecar_client.san_sang():
        print("Cong giong CHUA san sang (thieu LTT_VOICE_SIDECAR_TOKEN).",
              file=sys.stderr)
        return 2

    do_dai = [int(x) for x in a.do_dai.split(",") if x.strip()]
    print(f"do {len(do_dai)} bai: {do_dai}")
    print("lam am cong giong…")
    sidecar_client.noi(CORPUS[0])

    kq = {"bai": {}, "corpus_n": len(CORPUS)}
    for d in do_dai:
        bai = do_mot_bai(d, giu_asr=not a.bo_asr)
        bai["tong_hop"] = tong_hop(bai)
        # Bỏ embedding khỏi JSON: mỗi cái là 192–512 số float, và chúng đã được
        # dùng xong ở `tong_hop`. Giữ lại thì tệp phình lên hàng chục MB.
        for x in bai.get("doan", []):
            x.pop("emb", None)
        kq["bai"][str(d)] = bai

    _in_bang(kq)

    duong = a.json
    os.makedirs(os.path.dirname(os.path.abspath(duong)), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as f:
        json.dump(kq, f, ensure_ascii=False, indent=2)
    print(f"\nJSON: {duong}")

    # ⛔ KHÔNG in "PASS". Xem đầu tệp: phán quyết là việc của người đọc, và một
    #    dòng PASS ở đây sẽ được trích ra khỏi mọi ngữ cảnh đã dựng nên nó.
    print("\nDoc bang tren theo thu tu nay:")
    print("  1. `nguoi_noi_voi_dau` MIN co tut duoi `san_nhieu_nua_doan` khong?")
    print("  2. `doc_*_theo_doan` co CHIEU ro rang, hay chi la dao dong?")
    print("  3. cot 3000/5000/10000 co lech khoi cot 1500 (doi chung) khong?")
    print("  4. `cung_van_ban_khac_vi_tri` — cung chu, khac cho, chenh bao nhieu?")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
