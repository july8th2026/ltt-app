"""Hợp đồng của LTT VOICE: văn bản, audio vào, cổng sidecar, và manifest."""
from __future__ import annotations

import io
import json
import struct
import wave

import pytest

from apps.ltt_voice import audio_input, features, sidecar_client, text_pipeline
from apps.ltt_voice.manifest import MANIFEST
from apps.ltt_voice.tham_so_cong_khai import (TRAN_KY_TU_CONG_KHAI,
                                             TRAN_MOI_LUOT_SINH)


# ── tham số dùng chung hai venv ──────────────────────────────────────────────

def test_tran_MOT_LUOT_khop_giua_app_va_sidecar():
    """🔴 Hai bản sao của một hằng số, và đây là phép kiểm giữ chúng khớp.

    `apps/ltt_voice/` chạy trong venv nền tảng; `voice_sidecar/` chạy trong venv
    cách ly có torch. App **không được** import sidecar, nên hằng số phải nằm hai
    chỗ. Hai bản sao không có phép kiểm là hai bản sao sẽ lệch.

    ⚠️ Phép kiểm này trước 03/09 chốt `TRAN_KY_TU_CONG_KHAI`, và nó ĐÚNG lúc ấy
       vì hai trần là một con số. Khi trần công khai được nới lên 100.000 thì nó
       đỏ — không phải vì hợp đồng vỡ, mà vì **nó đang gọi tên sai hằng số**.
       Thứ phải khớp với sidecar là trần MỘT LƯỢT SINH, và nó vẫn khớp.
    """
    from voice_sidecar import tham_so
    assert TRAN_MOI_LUOT_SINH == tham_so.TRAN_KY_TU_MOT_LUOT


def test_tran_mot_luot_nam_duoi_nguong_troi_giong_cua_upstream():
    """Q119 — trần MỘT LƯỢT là trần CHẤT LƯỢNG, lấy từ upstream #168 (~3.000).

    Đo 30/08 cho thấy 3.000 ký tự vẫn sinh ra được (17,6 giây, không lỗi), nên
    con số này KHÔNG đến từ giới hạn kỹ thuật. Nó đến từ chỗ chất lượng bắt đầu
    tụt, và nới nó phải qua cổng V10.
    """
    assert TRAN_MOI_LUOT_SINH <= 3000 // 2


def test_tran_cong_khai_KHONG_con_bi_buoc_vao_tran_model():
    """⭐ Chốt chính điều làm nên đường tài liệu dài: hai trần được phép KHÁC nhau.

    Trần model nói *"model đọc liền được bao nhiêu trước khi trôi"*; trần công
    khai nói *"khách gửi được bao nhiêu trong một lần"*. Buộc chúng bằng nhau
    chính là lỗi đã làm bài 3.000 ký tự **bị từ chối** trong khi thông điệp lỗi
    của cổng đã nói *"phải đi đường long-form nhiều lượt sinh"*.

    ⛔ Nếu ai đó sau này gán lại `TRAN_KY_TU_CONG_KHAI = TRAN_MOI_LUOT_SINH` cho
       "gọn", phép kiểm này đỏ và nói thẳng vì sao đừng làm thế.
    """
    assert TRAN_KY_TU_CONG_KHAI > TRAN_MOI_LUOT_SINH


def test_tran_cong_khai_nam_TRONG_ngan_sach_thoi_gian_job():
    """🔴 Trần công khai và `max_runtime_s` là HAI ĐẦU CỦA CÙNG MỘT NGÂN SÁCH.

    Trần mới không đến từ model — nó đến từ tài nguyên. Đo 03/09
    (`tools/do_bai_dai.py`): 19,86 ký tự mỗi giây audio, RTF 0,152
    ⇒ **0,00763 giây GPU mỗi ký tự**.

    Nâng một đầu mà quên đầu kia thì hỏng theo kiểu tệ nhất: job chạy gần xong
    rồi bị giết vì hết giờ — tức đã tiêu gần trọn phần GPU của nó rồi mới vứt
    kết quả đi, và đúng ở những tài liệu dài nhất.

    ⚠️ Đòi biên **2 lần**, không đòi vừa khít: GPU có thể chậm gấp đôi khi đang
       chia việc với một job khác, và `max_runtime_s` là chốt chặn cho job TREO
       chứ không phải hạn mức hiệu năng.
    """
    GIAY_GPU_MOI_KY_TU = 0.00763          # do 03/09, xem tham_so_cong_khai.py
    tran_giay = MANIFEST.max_runtime_s["ltt_voice.synthesize"]
    can = TRAN_KY_TU_CONG_KHAI * GIAY_GPU_MOI_KY_TU
    assert tran_giay >= can * 2, (
        f"tran {TRAN_KY_TU_CONG_KHAI} ky tu can ~{can:.0f}s GPU nhung "
        f"max_runtime_s chi {tran_giay}s — bien duoi 2 lan")


def test_tran_cong_khai_nam_duoi_tran_dinh_dang_WAV():
    """⛔ RIFF/WAV tràn ở ~2 GiB, và nó hỏng IM LẶNG.

    Trình phát vẫn mở được phần đầu, nên một bản đọc bị cắt trông y hệt một bản
    đọc bình thường cho tới khi ai đó nghe tới cuối. Không có lỗi nào được ném,
    không có gì đỏ.

    ⇒ Trần ký tự phải nằm dưới ngưỡng ấy cho tới khi có RF64/WAVE64.
    """
    BYTE_MOI_GIAY = 48_000 * 2            # 48 kHz PCM16 mono
    KY_TU_MOI_GIAY_AUDIO = 19.86          # do 03/09
    giay_toi_da = (2 * 1024 ** 3) / BYTE_MOI_GIAY
    ky_tu_toi_da = giay_toi_da * KY_TU_MOI_GIAY_AUDIO
    assert TRAN_KY_TU_CONG_KHAI < ky_tu_toi_da, (
        f"tran {TRAN_KY_TU_CONG_KHAI} vuot nguong tran WAV "
        f"(~{ky_tu_toi_da:.0f} ky tu)")


def test_tham_so_sinh_mau_khong_ra_hop_dong_cong_khai():
    """🔴 Q119 — `temperature`/`top_k`/`top_p` KHÔNG được lộ ra khách.

    Hai lý do độc lập: cache CUDA graph của upstream khoá theo
    `(B, temperature, top_k, top_p)` nên mỗi tổ hợp mới tốn một graph trên card;
    và temperature cao làm lệch tông giữa các đoạn (#173).
    """
    tool = MANIFEST.tools[0]
    cam = {"temperature", "top_k", "top_p", "repetition_penalty",
           "repetition_window", "max_new_frames", "seed"}
    assert not (set(tool.params_schema) & cam)
    assert not (set(tool.api_contract.get("params", {})) & cam)


# ── chuẩn hoá văn bản ────────────────────────────────────────────────────────

@pytest.mark.parametrize("vao,phai_co", [
    ("Giảm 25% hôm nay", "phần trăm"),
    ("Giá 50000₫", "đồng"),
    ("Giá 50000 VNĐ", "đồng"),
    ("Nhiệt độ 30°C", "độ C"),
    ("Nặng 5kg", "ki lô gam"),
])
def test_ky_hieu_luon_thanh_chu(vao, phai_co):
    """Một ký hiệu KHÔNG có cách đọc — nó phải thành chữ, không có ngoại lệ."""
    ra = text_pipeline.chuan_hoa(vao)
    assert phai_co in ra


def test_ngay_va_gio_doc_ra_chu():
    ra = text_pipeline.chuan_hoa("Họp ngày 12/08/2026 lúc 14h30.")
    assert "mười hai" in ra and "tháng tám" in ra
    assert "mười bốn giờ" in ra and "ba mươi" in ra


def test_ngay_khong_hop_le_thi_de_nguyen():
    """Đoán bừa còn tệ hơn để nguyên: 45/99/2026 không phải một ngày."""
    assert "45/99/2026" in text_pipeline.chuan_hoa("Mã 45/99/2026")


def test_phan_cach_hang_nghin_bi_go():
    """Dấu chấm hàng nghìn không được sống sót — nếu không nó đọc thành 'chấm'.

    ⚠️ Bản đầu của phép kiểm này chốt `"1500000" in ra`. Từ 01/09/2026 số từ
       một triệu trở lên được đọc THÀNH CHỮ (engine đọc rời từng chữ số ở
       ngưỡng ấy — xem `_doc_so_lon`), nên chữ số không còn ở đó nữa.

    ⭐ Nên phép kiểm nay chốt đúng thứ nó vốn muốn canh — **dấu chấm biến mất**
       — thay vì chốt một dạng biểu diễn trung gian. Chốt vào dạng biểu diễn là
       lý do nó đỏ khi hành vi được cải thiện.
    """
    ra = text_pipeline.chuan_hoa("Giá 1.500.000 đồng")
    assert "1.500" not in ra and "500.000" not in ra, ra
    assert "một triệu năm trăm nghìn" in ra, ra

    # Dưới một triệu thì engine đọc đúng, nên ta CHỈ gỡ dấu chấm và để yên.
    duoi = text_pipeline.chuan_hoa("Giá 990.000 đồng")
    assert "990000" in duoi, duoi


def test_so_thu_tu_dau_dong_thanh_chu():
    """Ô mà pack V2 nêu đích danh. '1.' đọc thành 'một chấm' là hỏng nguyên câu."""
    ra = text_pipeline.chuan_hoa("1. Mở ứng dụng.\n2. Chọn giọng.")
    assert ra.startswith("Một.")
    assert "Hai." in ra


def test_url_va_email_khong_doc_nguyen():
    ra = text_pipeline.chuan_hoa("Xem https://a.b/c hoặc gửi x@y.com nhé")
    assert "https" not in ra and "@" not in ra


def test_viet_tat_phan_biet_hoa_thuong():
    """🔴 'AI' là viết tắt; 'ai' là đại từ tiếng Việt.

    Khớp không phân biệt hoa-thường sẽ biến "ai cũng biết" thành "ây ai cũng
    biết" — một lỗi nghe thấy ngay và rất khó truy về từ điển.
    """
    assert "ây ai" in text_pipeline.chuan_hoa("Dùng AI để làm")
    assert "ây ai" not in text_pipeline.chuan_hoa("ai cũng biết điều đó")


def test_doc_so_tran_mac_dinh_tat():
    """Chưa đo thì không sửa: `sea-g2p` có thể đã đọc số đúng sẵn."""
    assert "27" in text_pipeline.chuan_hoa("Có 27 người")
    assert "hai mươi bảy" in text_pipeline.chuan_hoa("Có 27 người",
                                                     doc_so_tran=True)


def test_tu_dien_rieng_thang_bang_chung():
    ra = text_pipeline.chuan_hoa("Công ty Plenx", tu_dien_rieng={"Plenx": "Ple-nít"})
    assert "Ple-nít" in ra


# ── chia đoạn ────────────────────────────────────────────────────────────────

def test_chia_doan_khong_cat_giua_cau():
    cau = "Câu một ngắn. Câu hai cũng ngắn. Câu ba dài hơn một chút nữa."
    for d in text_pipeline.chia_doan(cau, tran_moi_doan=30):
        assert d.strip()
        assert len(d) <= 30 or "," not in d


def test_chia_doan_ton_trong_tran():
    dai = "Một câu rất dài không có dấu chấm nào cả " * 20
    for d in text_pipeline.chia_doan(dai, tran_moi_doan=100):
        assert len(d) <= 100


def test_chia_doan_giu_du_noi_dung():
    """Chia đoạn không được LÀM MẤT chữ — ghép lại phải còn đủ số từ."""
    goc = "Một hai ba. Bốn năm sáu! Bảy tám chín? Mười."
    doan = text_pipeline.chia_doan(goc, tran_moi_doan=20)
    assert len(" ".join(doan).split()) == len(goc.replace(".", " ")
                                              .replace("!", " ")
                                              .replace("?", " ").split())


# ── chia đoạn CÂN BẰNG (đường bản đọc) ──────────────────────────────────────

def _bai(n_cau: int) -> str:
    return " ".join(f"Day la cau so {i} trong mot bai doc thu nghiem kha dai."
                    for i in range(n_cau))


def test_can_bang_khong_them_doan_va_khong_vuot_tran():
    """Hai bất biến của phép cân bằng. Vi phạm cái nào cũng là một hồi quy.

    ⛔ `_can_bang` tìm trần nhỏ nhất còn cho ra ngần ấy đoạn bằng phép nhị phân,
       và phép ấy dựa trên giả định "trần lớn hơn thì đoạn ít hơn" — đúng trong
       mọi ca thật nhưng KHÔNG phải một định lý. Nên hai bất biến này phải được
       kiểm, không được suy ra.
    """
    for n in (5, 20, 60, 200):
        goc = _bai(n)
        goi = text_pipeline.chia_doan(goc, tran_moi_doan=300)
        deu = text_pipeline.chia_doan(goc, tran_moi_doan=300, can_bang=True)
        assert len(deu) <= len(goi)
        assert max(len(d) for d in deu) <= 300


def test_can_bang_giu_du_noi_dung():
    goc = _bai(40)
    deu = text_pipeline.chia_doan(goc, tran_moi_doan=300, can_bang=True)
    assert " ".join(deu).split() == goc.split()


def test_can_bang_xoa_duoc_duoi_cut():
    """🔴 CA BỆNH LÝ ĐÃ ĐO — đây là lý do phép cân bằng tồn tại.

    Phép gói tới trần nhồi đầy đoạn trước rồi để phần thừa rơi vào đoạn cuối.
    Đo 03/09 trên corpus của `tools/do_bai_dai.py` ở trần 1.500: một bài 1.591
    ký tự ra **1.462 + 128** — đuôi cụt lệch 11,4 lần, mà vẫn tốn trọn một lượt
    `infer`. Phép cân bằng cho 2 đoạn ~795.

    ⚠️ Chốt bằng TỈ LỆ, không bằng con số tuyệt đối: corpus đổi thì số đổi, còn
       mệnh đề "đuôi không được cụt hơn một nửa đoạn dài nhất" thì không đổi.
    """
    goc = _bai(46)
    goi = text_pipeline.chia_doan(goc, tran_moi_doan=1500)
    assert len(goi) > 1, "ca thu phai chia ra nhieu doan moi co nghia"
    deu = text_pipeline.chia_doan(goc, tran_moi_doan=1500, can_bang=True)
    assert len(deu) == len(goi)
    assert min(len(d) for d in deu) / max(len(d) for d in deu) > 0.5


def test_chuan_bi_dung_phep_can_bang():
    """Đường BẢN ĐỌC cân bằng; `du_an.nhap_van_ban` thì KHÔNG.

    ⭐ Hai người gọi, hai nhu cầu — `du_an.py` đã ghi rõ: khối biên tập muốn gói
       tới trần (một kịch bản ngắn thật sự là MỘT khối), bản đọc muốn các đoạn
       đều nhau. Phép kiểm này chốt rằng chúng không bị gộp lại làm một.
    """
    goc = _bai(46)
    doan = text_pipeline.chuan_bi(goc, tran_moi_doan=1500).doan
    assert min(len(d) for d in doan) / max(len(d) for d in doan) > 0.5


def test_chuan_bi_giu_ca_ban_goc():
    """Lịch sử job phải ghi được CẢ text gốc lẫn text đã chuẩn hoá.

    Không có điều đó thì một lượt đọc sai không bao giờ truy được là do model hay
    do chính phép chuẩn hoá của ta.
    """
    kq = text_pipeline.chuan_bi("Giảm 25%.", tran_moi_doan=256)
    assert kq.goc == "Giảm 25%."
    assert "phần trăm" in kq.da_chuan_hoa
    assert kq.doan


# ── audio vào ────────────────────────────────────────────────────────────────

def _wav(giay: float, sr: int = 16000, bien: float = 0.5) -> bytes:
    import math
    n = int(giay * sr)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack(
            "<%dh" % n,
            *[int(bien * 32767 * math.sin(i / 20.0)) for i in range(n)]))
    return buf.getvalue()


def test_mime_doc_tu_byte_that_khong_tu_trinh_duyet():
    """🔴 Trình duyệt gửi `Content-Type` gì cũng được."""
    gia_mao = b"MZ\x90\x00" + b"\x00" * 100
    with pytest.raises(audio_input.LoiAudio):
        audio_input.kiem(gia_mao, "audio/wav")


def test_wav_hop_le_qua_duoc():
    kq = audio_input.kiem(_wav(5.0), "audio/wav")
    assert kq["mime"] == "audio/wav"
    assert 4.8 < kq["giay"] < 5.2


def test_clip_qua_ngan_bi_tu_choi_kem_cach_sua():
    with pytest.raises(audio_input.LoiAudio) as e:
        audio_input.kiem(_wav(1.0), "audio/wav")
    assert "giây" in str(e.value)


def test_clip_qua_dai_bi_tu_choi():
    with pytest.raises(audio_input.LoiAudio):
        audio_input.kiem(_wav(45.0), "audio/wav")


def test_clip_vo_tieng_duoc_canh_bao_chu_khong_bi_chan():
    """Vỡ tiếng là cảnh báo, không phải từ chối — người dùng vẫn có quyền dùng."""
    kq = audio_input.kiem(_wav(5.0, bien=1.0), "audio/wav")
    assert any("vỡ tiếng" in c for c in kq["canh_bao"])


def test_clip_qua_nho_duoc_canh_bao():
    kq = audio_input.kiem(_wav(5.0, bien=0.01), "audio/wav")
    assert kq["canh_bao"]


def test_tep_rong_bi_tu_choi():
    with pytest.raises(audio_input.LoiAudio):
        audio_input.kiem(b"", "audio/wav")


# ── cổng sidecar ─────────────────────────────────────────────────────────────

class _Loi(Exception):
    def __init__(self, code, body=b"{}", headers=None):
        self.code = code
        self._body = body
        self.headers = headers or {}

    def read(self):
        return self._body


def test_429_thanh_ban_khong_thanh_hong(monkeypatch):
    """🔴 D-005 — bận KHÔNG phải hỏng.

    Coi 429 là hỏng sẽ dẫn tới cooldown rồi vô hiệu hoá cả đường gọi; một buổi
    tối nhiều việc là đủ để tự tắt sản phẩm. Và một job bị coi là hỏng sẽ TRỪ
    CREDIT cho việc chưa từng chạy.
    """
    import urllib.error
    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "x")

    def _no(*a, **k):
        raise urllib.error.HTTPError(
            "u", 429, "busy", {"Retry-After": "7"},
            io.BytesIO(json.dumps({"retry_after_s": 7.0}).encode()))

    monkeypatch.setattr("urllib.request.urlopen", _no)
    with pytest.raises(sidecar_client.SidecarBan) as e:
        sidecar_client.noi("xin chào")
    assert e.value.retry_after_s == 7.0


def test_413_thanh_van_ban_qua_dai(monkeypatch):
    import urllib.error
    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "x")

    def _no(*a, **k):
        raise urllib.error.HTTPError(
            "u", 413, "too long", {},
            io.BytesIO(json.dumps({"detail": "qua dai"}).encode()))

    monkeypatch.setattr("urllib.request.urlopen", _no)
    with pytest.raises(sidecar_client.VanBanQuaDai):
        sidecar_client.noi("x" * 9000)


def test_ban_khong_bi_boc_thanh_loi_giong_noi(monkeypatch):
    """`features.goi_cong` phải để `DangBanTam` bay lên, không đổi thành lỗi."""
    def _ban(*a, **k):
        raise sidecar_client.SidecarBan(retry_after_s=3.0)

    monkeypatch.setattr(sidecar_client, "noi", _ban)
    with pytest.raises(features.DangBanTam):
        features.goi_cong("xin chào")


def test_thieu_token_thi_tu_choi_chu_khong_goi_bua(monkeypatch):
    monkeypatch.delenv("LTT_VOICE_SIDECAR_TOKEN", raising=False)
    assert not sidecar_client.san_sang()
    with pytest.raises(sidecar_client.LoiSidecar):
        sidecar_client.nang_luc()


# ── nghiệp vụ ────────────────────────────────────────────────────────────────

def test_khong_cho_vua_voice_id_vua_preset():
    """Hai nguồn giọng cùng lúc là một yêu cầu không có câu trả lời đúng."""
    with pytest.raises(features.LoiGiongNoi):
        features.chuan_hoa({"text": "a", "voice_id": "vc_1", "preset": "Adam"})


def test_van_ban_rong_bi_tu_choi():
    with pytest.raises(features.LoiGiongNoi):
        features.chuan_hoa({"text": "   "})


def test_public_api_tu_choi_vua_voice_id_vua_preset_TRUOC_khi_tinh_tien(monkeypatch):
    """🔴 XOR phải chặn Ở CỬA VÀO API, trước khi báo giá/giữ credit.

    `features.chuan_hoa` (worker) đã từ chối cặp này — nhưng qua Public API lượt
    gọi đã được báo giá, giữ credit và xếp job TRƯỚC khi worker chạm tới nó, rồi
    hỏng với "The job could not be completed." (có hoàn tiền, nhưng phí một vòng
    và một job hỏng khó hiểu). `manifest` khai `exclusive_with` và
    `invocation.validate_public_input` cưỡng chế nó — hàm ấy chạy ở CẢ `/quotes`
    lẫn `/jobs` trước `price()`, nên phán quyết về đúng chỗ: miễn phí, rõ, tức thì.

    ⛔ Không đụng hợp đồng công khai: `exclusive_with` ở `params_schema` nội bộ,
       `project_tool` không phát nó ra, nên `contract_hash` không đổi.
    """
    monkeypatch.setenv("LTT_PUBLIC_API", "1")
    monkeypatch.setenv("LTT_PUBLIC_API_TOOLS", "speech.ltt")

    from platform_core.public_api import errors, invocation
    from platform_core.public_api.catalog import build_catalog, require_tool
    from platform_core.public_api.config import load_public_api_config

    tool = require_tool(build_catalog(load_public_api_config()), "speech.ltt")

    # Một nguồn giọng — hợp lệ ở cả hai chiều.
    invocation.validate_public_input(tool, {"text": "a", "preset": "Adam"})
    invocation.validate_public_input(tool, {"text": "a", "voice_id": "vc_x"})

    # Cả hai — 400 ngay tại cửa vào, trước mọi bước tiền.
    with pytest.raises(errors.ApiError) as e:
        invocation.validate_public_input(
            tool, {"text": "a", "voice_id": "vc_x", "preset": "Adam"})
    assert e.value.status == 400
    assert "only one" in str(e.value.detail).lower()


def test_giong_khong_thuoc_ve_minh_bao_giong_nhu_khong_ton_tai(monkeypatch):
    """🔴 IDOR — thông điệp phải GIỐNG NHAU cho hai trường hợp.

    Phân biệt "không tồn tại" với "không phải của bạn" là cho phép dò xem
    `voice_id` nào có thật trong hệ thống.
    """
    from apps.ltt_voice import tham_chieu
    monkeypatch.setattr(tham_chieu, "tim_profile", lambda *a, **k: None)
    yc = features.chuan_hoa({"text": "a", "voice_id": "vc_cua_nguoi_khac",
                             "owner_id": 1})
    with pytest.raises(features.LoiGiongNoi) as e:
        features.giai_giong(object(), yc)
    assert "tài khoản của bạn" in str(e.value)


# ── manifest ─────────────────────────────────────────────────────────────────

def test_manifest_khai_du_de_xep_cho_gpu():
    """VRAM đo thật 641 MB allocated / 1.288 MB reserved -> khai 2.000 MB."""
    for jt in MANIFEST.job_types:
        assert MANIFEST.vram_for(jt) >= 1288, "phai tren muc reserved da do"
        assert MANIFEST.vram_for(jt) < 12000, "khong duoc giu cho nhu upscale"


def test_manifest_co_tran_thoi_gian_chay():
    """Job TREO mà vẫn đập nhịp sẽ giữ slot vô hạn và không ai được báo."""
    for jt in MANIFEST.job_types:
        assert MANIFEST.runtime_limit_for(jt) > 0


def test_tool_giu_cho_mot_suat_thuc_thi():
    """Q114 — cả ba cửa job/sync/stream phải giành cùng một slot."""
    tool = MANIFEST.tools[0]
    assert tool.admission_resource
    assert tool.admission_slots == 1


def test_tool_tra_audio_don_khong_phai_mang():
    """Public API chưa có `audio[]` (`invocation._MEDIA_TYPES`).

    Thiết kế một tool trả mảng audio rồi phát hiện ở cuối là mất cả vòng.
    """
    assert MANIFEST.tools[0].returns.get("audio_key") == "audio"


def test_app_khong_import_vieneu():
    """🔴 App chạy trong venv NỀN TẢNG — nó không có torch và không được có.

    Một `import vieneu` lọt vào đây sẽ kéo cả cây phụ thuộc cách ly vào tiến
    trình web và worker, tức phá đúng thứ mà venv cách ly sinh ra để tránh.
    """
    import pathlib
    goc = pathlib.Path(__file__).resolve().parents[1] / "apps" / "ltt_voice"
    for f in goc.glob("*.py"):
        src = f.read_text(encoding="utf-8")
        assert "import vieneu" not in src, f"{f.name} import vieneu"
        assert "import torch" not in src, f"{f.name} import torch"


def test_handler_phan_nhanh_dung_theo_job_type():
    """🔴 Nền tảng LUÔN gọi `handle`, bất kể `job_type`.

    `platform_core/jobs.py::resolve_handler` tra app sở hữu rồi
    `getattr(mod, "handle")` — hết. Một app nhiều loại job mà đặt tên hàm theo
    loại (`handle_enroll`, …) thì những hàm đó **không bao giờ được gọi**, và
    triệu chứng là job ghi danh chạy nhầm nhánh tạo tiếng rồi hỏng vì thiếu
    `text` — một thông điệp trỏ sai chỗ hoàn toàn.
    """
    from types import SimpleNamespace

    from apps.ltt_voice import jobs
    from platform_core.jobs import resolve_handler

    for jt in MANIFEST.job_types:
        assert resolve_handler(jt) is jobs.handle

    goi = []
    truoc = (jobs._tao_tieng, jobs._ghi_danh)
    jobs._tao_tieng = lambda p, c=None: goi.append("tao") or {}
    jobs._ghi_danh = lambda p, c=None: goi.append("ghi_danh") or {}
    try:
        jobs.handle({}, SimpleNamespace(job_type="ltt_voice.enroll"))
        jobs.handle({}, SimpleNamespace(job_type="ltt_voice.synthesize"))
        # ctx thiếu job_type: rơi về params, cho lời gọi trực tiếp trong test.
        jobs.handle({"_job_type": "ltt_voice.enroll"}, None)
    finally:
        jobs._tao_tieng, jobs._ghi_danh = truoc

    assert goi == ["ghi_danh", "tao", "ghi_danh"]


def test_hai_tep_du_lieu_ngu_am_khong_chua_chuoi_giao_dien():
    """🔴 Canh cái mà `check_i18n.BO_QUA_FILE` đã thôi canh.

    `text_pipeline.py` và `tu_dien.py` được bỏ qua khỏi phép đếm i18n vì chúng
    chứa **dữ liệu ngữ âm tiếng Việt** — bảng thay ký hiệu, bảng số đọc thành
    chữ, bảng phát âm. Đó là **văn bản model đọc lên**, không phải nhãn giao
    diện; bọc `_()` rồi dịch sẽ khiến một người dùng đặt giao diện tiếng Anh
    nghe giọng Việt đọc "day five month three".

    ⚠️ Nhưng bỏ qua một tệp nghĩa là **mất một người canh**. Nếu sau này ai đó
       đặt một thông điệp lỗi vào đó, nó sẽ không bao giờ được dịch và không ai
       biết. Phép kiểm này thay chỗ người canh đã mất: hai tệp đó không được
       ném lỗi và không được nói với người dùng.

    Thông điệp cho người dùng thuộc về `features.py` và `audio_input.py` — cả
    hai vẫn nằm trong phép đếm i18n.

    *(Gợi ý của `lttstudiosapp-a5` khi duyệt thay đổi `check_i18n.py`.)*
    """
    import pathlib

    goc = pathlib.Path(__file__).resolve().parents[1] / "apps" / "ltt_voice"
    for ten in ("text_pipeline.py", "tu_dien.py"):
        src = (goc / ten).read_text(encoding="utf-8")
        # Bỏ docstring và chú thích: chúng nói VỀ lỗi, không NÉM lỗi.
        ma = "\n".join(d for d in src.splitlines()
                       if not d.lstrip().startswith("#"))
        for cam in ("raise ", "_t(", "flash(", "HTTPException"):
            assert cam not in ma, (
                f"{ten} chứa {cam!r} — nếu đây là chuỗi hiện cho người dùng thì "
                f"nó phải chuyển sang features.py hoặc audio_input.py, vì "
                f"{ten} đã bị check_i18n bỏ qua và sẽ không ai canh nó.")


def test_check_i18n_van_dem_hai_tep_co_thong_diep_nguoi_dung():
    """Mặt còn lại của phép kiểm trên: chỗ ĐÁNG canh thì vẫn được canh."""
    # Đọc bằng AST chứ không `import`: `check_i18n` bọc lại `sys.stdout` lúc
    # import, và một test không được đổi stdout của cả lượt chạy.
    import ast
    import pathlib

    goc = pathlib.Path(__file__).resolve().parents[1]
    cay = ast.parse((goc / "tools" / "check_i18n.py").read_text(encoding="utf-8"))
    bo_qua = ()
    for n in ast.walk(cay):
        if (isinstance(n, ast.Assign)
                and any(getattr(t, "id", "") == "BO_QUA_FILE" for t in n.targets)):
            bo_qua = tuple(ast.literal_eval(n.value))
    assert bo_qua, "khong doc duoc BO_QUA_FILE"

    for phai_dem in ("apps/ltt_voice/features.py", "apps/ltt_voice/audio_input.py",
                     "apps/ltt_voice/routes.py", "apps/ltt_voice/gia.py"):
        assert not any(phai_dem.startswith(b) for b in bo_qua), phai_dem


def test_dem_cau_khop_voi_bo_ghep_o_sidecar():
    """🔴 Hai bản sao của MỘT luật đếm câu, và đây là phép kiểm giữ chúng khớp.

    `text_pipeline._KET_CAU` (venv nền tảng) và `voice_sidecar.server._KET_CAU`
    (venv cách ly) phải cùng một biểu thức. Lệch nhau thì `/v1/speech-dai` và
    đường đoạn-rời tính ra hai nhịp nghỉ khác nhau cho cùng một bài — và triệu
    chứng là mối nối nghe khác nhau tuỳ đường đi, thứ không phép đo hợp đồng
    nào bắt được.
    """
    from voice_sidecar.server import _KET_CAU as O_SIDECAR

    assert text_pipeline._KET_CAU.pattern == O_SIDECAR.pattern

    for t, n in (("Mot cau.", 1), ("Mot. Hai! Ba?", 3), ("Khong co dau ket", 1),
                 ("", 1), ("A... B.", 2)):
        assert text_pipeline.dem_cau(t) == n, t
        assert text_pipeline.dem_cau(t) == max(1, len(O_SIDECAR.findall(t)) or 1)
