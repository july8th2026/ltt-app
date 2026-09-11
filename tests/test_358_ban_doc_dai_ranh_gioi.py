r"""
Bản đọc dài — RANH GIỚI văn bản: không mất câu, không lặp câu, đúng thứ tự.

`test_396` đếm **sidecar được hỏi đoạn nào** (đọc tiếp / hỏng từng đoạn).
`test_342` kiểm **âm thanh** của phép ghép. Còn thiếu một tầng ở giữa: khi một
tài liệu thật — dài, đa ngôn ngữ, có ranh giới đoạn — đi qua `chia_doan` rồi
`ban_doc_dai.dung`, thì **mọi câu phải tới đầu ra đúng một lần và đúng thứ tự**.

⛔ KHÔNG dựng một bộ chia thứ hai ở đây. Mọi phép kiểm gọi thẳng
   `text_pipeline.chia_doan` / `dem_cau` — thứ production thật sự chạy. Một bộ
   chia thứ hai trong test là hai cách hiểu "một câu là gì", đúng cái bẫy
   `du_an.nhap_van_ban` đã cảnh báo.

Các mệnh đề ở đây đều là "việc gì KHÔNG xảy ra" (không mất, không lặp, không đảo)
nên chúng không tự lộ ra trong một lượt chạy thành công — phải đếm mới thấy.
"""
from __future__ import annotations

import os
import re
import shutil
import wave

import pytest

from apps.ltt_voice import text_pipeline

# Mỗi câu mang một dấu duy nhất "S<nnn>" nên có thể dựng lại THỨ TỰ và phát hiện
# mất/lặp bằng cách quét dấu ấy trên đầu ra.
_DAU = re.compile(r"S(\d{4})")


def _cau_vi(i: int) -> str:
    return (f"Cau S{i:04d} noi ve mot y tuong cu the trong bai doc dai nay.")


def _cau_en(i: int) -> str:
    return (f"Sentence S{i:04d} carries one concrete idea for this long read.")


def _dau_trong(doan: list) -> list:
    """Danh sách các dấu S theo đúng thứ tự chúng xuất hiện qua các đoạn."""
    ra = []
    for d in doan:
        ra.extend(_DAU.findall(d))
    return ra


# ── 1. không mất, không lặp, đúng thứ tự (VI / EN / Unicode) ──────────────────

@pytest.mark.parametrize("cau_fn,ten", [(_cau_vi, "VI"), (_cau_en, "EN")])
def test_khong_mat_khong_lap_dung_thu_tu(cau_fn, ten):
    """🔴 Câu số i phải tới đầu ra đúng MỘT lần, và đúng vị trí i.

    Đây là ba lỗi gộp làm một phép kiểm: câu bị mất, câu bị lặp, câu bị đảo —
    cả ba đều cho ra một tệp WAV "nghe cũng được" nên tai không bắt được.
    """
    n = 60
    van = " ".join(cau_fn(i) for i in range(1, n + 1))
    doan = text_pipeline.chia_doan(van, tran_moi_doan=200)

    assert len(doan) > 1, f"{ten}: 60 cau ma khong chia ra (tran 200)"
    thu_tu = [int(x) for x in _dau_trong(doan)]
    assert thu_tu == list(range(1, n + 1)), (
        f"{ten}: thu tu/so luong cau sai — mat, lap hoac dao.\n{thu_tu}")


def test_unicode_dau_tieng_viet_va_emoji_giu_nguyen():
    """Dấu thanh tiếng Việt và emoji không được rơi rụng khi chia đoạn."""
    cau = [
        "Đây là câu một với đầy đủ dấu: ằ ẵ ệ ợ ự ỹ.",
        "Câu hai có biểu tượng 🎧 và 🌿 nằm giữa dòng.",
        "Câu ba kết thúc bằng chữ tiếng Việt: nghĩ.",
    ]
    doan = text_pipeline.chia_doan("\n\n".join(cau), tran_moi_doan=400)
    gop = " ".join(doan)
    for k in ("ệ", "ợ", "ỹ", "🎧", "🌿", "nghĩ"):
        assert k in gop, f"ky tu {k!r} bien mat sau khi chia doan"


# ── 2. ranh giới câu & đoạn: đầu/cuối tài liệu, không cắt giữa câu ────────────

def test_giu_dau_va_cuoi_tai_lieu():
    """First/last words: đoạn đầu bắt đầu bằng câu đầu, đoạn cuối chứa câu cuối."""
    n = 40
    van = " ".join(_cau_vi(i) for i in range(1, n + 1))
    doan = text_pipeline.chia_doan(van, tran_moi_doan=200)
    assert doan[0].startswith("Cau S0001"), doan[0][:40]
    assert "S0040" in doan[-1], doan[-1][-40:]


def test_moi_doan_gom_TRON_cac_cau_khong_cat_giua_cau():
    """⛔ Cắt giữa câu là cắt giữa một mệnh đề ngữ điệu — nghe rõ ngay cả khi
    ghép liền. Với câu ngắn hơn trần, mọi đoạn phải kết thúc bằng dấu câu."""
    van = " ".join(_cau_vi(i) for i in range(1, 51))
    doan = text_pipeline.chia_doan(van, tran_moi_doan=220)
    for d in doan:
        assert d.rstrip().endswith("."), f"doan khong ket thuc o ranh gioi cau: {d!r}"


def test_PHAN_CONG_ranh_gioi_doan_van_o_tang_tren_khong_o_chia_doan():
    """⚠️ Ai giữ ranh giới đoạn văn — và ai KHÔNG.

    `chia_doan` GÓI TỚI TRẦN: nó coi `\\n` như khoảng trắng giữa câu, nên hai
    đoạn ngắn cộng lại dưới trần sẽ bị gói vào MỘT đoạn. Việc tôn trọng dòng
    trống của tác giả nằm ở TẦNG TRÊN — `du_an.nhap_van_ban` tách theo `\\n\\n`
    TRƯỚC rồi mới gọi `chia_doan` cho từng đoạn (đã chốt ở `test_350`).

    Chốt phân công này để không ai "sửa" `chia_doan` cho giữ ranh giới đoạn và
    vô tình phá phép gói-tới-trần mà bản đọc dài dựa vào.
    """
    nl = chr(10)
    hai_doan = "Đoạn một ngắn." + nl + nl + "Đoạn hai ngắn."
    assert text_pipeline.chia_doan(hai_doan, tran_moi_doan=400) == [
        "Đoạn một ngắn. Đoạn hai ngắn."], "chia_doan da doi hanh vi goi-toi-tran"


# ── 3. đếm câu: nền tảng của nhịp nghỉ khi ghép ──────────────────────────────

def test_tong_so_cau_bao_toan_qua_cac_doan():
    """`ghep_tep` phân biệt ranh giới câu với khe từ nhờ `dem_cau` mỗi đoạn.

    Nếu tổng `dem_cau` các đoạn lệch tổng câu thật thì nhịp nghỉ ở mối nối tính
    trên một mẫu sai — một lỗi phụ thuộc LỊCH SỬ CHẠY, khó truy nhất.
    """
    n = 45
    van = " ".join(_cau_vi(i) for i in range(1, n + 1))
    doan = text_pipeline.chia_doan(van, tran_moi_doan=200)
    tong = sum(text_pipeline.dem_cau(d) for d in doan)
    assert tong == n, f"tong dem_cau={tong}, that su co {n} cau"


# ── 4. quy mô: 5 phút, 15 phút, tài liệu rất dài ─────────────────────────────
#
# Xấp xỉ chữ: ~150 từ/phút, ~6 ký tự/từ (kể dấu cách) ⇒ 5' ≈ 4.500, 15' ≈ 13.500.
# Không chốt CON SỐ đoạn (nó trôi khi trần đổi); chốt TÍNH CHẤT: dài hơn ⇒ ít
# nhất bằng số đoạn, và không đoạn nào vượt trần.

def _van_theo_ky_tu(khoang: int) -> str:
    cau, d = [], 0
    i = 1
    while d < khoang:
        c = _cau_vi(i)
        cau.append(c)
        d += len(c) + 1
        i += 1
    return " ".join(cau)


def test_5_phut_va_15_phut_deu_chia_va_khong_vuot_tran():
    tran = 400
    nam = text_pipeline.chia_doan(_van_theo_ky_tu(4500), tran_moi_doan=tran)
    muoi_lam = text_pipeline.chia_doan(_van_theo_ky_tu(13500), tran_moi_doan=tran)

    assert len(nam) > 1 and len(muoi_lam) > len(nam), (
        f"5' -> {len(nam)} doan, 15' -> {len(muoi_lam)} doan")
    for nhom in (nam, muoi_lam):
        assert all(len(d) <= tran for d in nhom), "co doan vuot tran ky thuat"


def test_tai_lieu_rat_dai_khong_mat_cau():
    """50.000 ký tự: quét dấu S để chắc không câu nào rơi giữa đường."""
    n = 800
    van = " ".join(_cau_vi(i) for i in range(1, n + 1))
    doan = text_pipeline.chia_doan(van, tran_moi_doan=400)
    thu_tu = [int(x) for x in _dau_trong(doan)]
    assert thu_tu == list(range(1, n + 1)), "mat/dao cau trong tai lieu rat dai"


# ════════════ tích hợp: chia_doan -> ban_doc_dai giữ nguyên thứ tự ═══════════
#
# Nối phép chia thật với bộ dựng bản đọc dài: một tài liệu thật, chia bằng
# `chia_doan`, chạy qua `ban_doc_dai.dung`. Cổng giọng phải được hỏi từng đoạn
# ĐÚNG MỘT LẦN, ĐÚNG THỨ TỰ, và bộ ghép nhận đủ N đoạn với số câu mỗi đoạn khớp
# `dem_cau`. `test_396` chốt điều này trên đoạn dựng tay; ở đây là đoạn THẬT.

class _Kho:
    def __init__(self, goc: str):
        self.goc = goc
        self.da_put: list = []

    def _p(self, khoa: str) -> str:
        return os.path.join(self.goc, *khoa.split("/"))

    def local_path(self, khoa: str):
        p = self._p(khoa)
        return p if os.path.exists(p) else None

    def put(self, khoa: str, stream, content_type: str = ""):
        p = self._p(khoa)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            shutil.copyfileobj(stream, f)
        self.da_put.append(khoa)


def _wav(duong: str) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    with wave.open(duong, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b"\x00\x01" * 8000)


class _Cong:
    class SidecarBan(Exception):
        pass

    def __init__(self):
        self.da_hoi: list = []
        self.ghep_voi = None

    def lo_ra_tep(self, texts, duong_ra, *, ref_b64=None, preset=None):
        self.da_hoi.extend(texts)
        for d in duong_ra:
            _wav(d)
        return {"items": [{"duong": d} for d in duong_ra]}

    def ghep_tep(self, duong_vao, duong_ra, *, so_cau=None):
        self.ghep_voi = (list(duong_vao), list(so_cau or []))
        _wav(duong_ra)
        return {"so_doan": len(duong_vao), "giay": float(len(duong_vao))}


def test_chia_doan_qua_ban_doc_dai_giu_thu_tu_va_so_cau(tmp_path, monkeypatch):
    from apps.ltt_voice import ban_doc_dai

    van = " ".join(_cau_vi(i) for i in range(1, 61))
    doan = text_pipeline.chia_doan(van, tran_moi_doan=200)
    assert len(doan) > 3

    kho = _Kho(str(tmp_path / "kho"))
    cong = _Cong()
    monkeypatch.setattr(ban_doc_dai, "sidecar_client", cong)
    import platform_core.storage as st
    monkeypatch.setattr(st, "get_storage", lambda: kho)
    thu_muc = tmp_path / "tam"
    thu_muc.mkdir()

    ban_doc_dai.dung(doan, thu_muc=str(thu_muc), owner_id="u1", job_id="j",
                     so_moi_lo=8)

    # Cổng thấy đúng từng đoạn, đúng thứ tự, không lặp.
    assert cong.da_hoi == doan, "ban_doc_dai hoi sidecar sai thu tu/so luong"
    # Bộ ghép nhận đủ N đoạn với số câu mỗi đoạn = dem_cau(doan_i).
    duong_vao, so_cau = cong.ghep_voi
    assert len(duong_vao) == len(doan)
    assert so_cau == [text_pipeline.dem_cau(d) for d in doan], so_cau
