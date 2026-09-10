r"""PHÁT DẦN (U-07) — và bất biến của nó là TIỀN, không phải âm thanh.

Mô hình β (chốt 09/09/2026): giữ chỗ trước, quyết toán theo **số byte PCM đã
thật sự gửi đi**. Khách ngắt giữa chừng trả đúng phần đã nghe.

## ⛔ Vì sao tệp này soi định dạng byte kỹ đến thế

Đường job đo thời lượng bằng `ffprobe` trên tệp đã sinh. Đường phát dần **không
có tệp** lúc tính tiền, nên nó đo bằng byte. Hai thước đo cho cùng một đại lượng
là một rủi ro thật: ngày chúng lệch nhau là ngày một hoá đơn không giải thích
được.

⇒ Tệp này ghim **hợp đồng byte** giữa `voice_sidecar/server.py::_wav_header_mo`
  và `apps/ltt_voice/gia.py::doc_sample_rate`. Đổi một bên mà không đổi bên kia
  thì đỏ ở đây, chứ không đỏ ở hoá đơn của khách.
"""
from __future__ import annotations

import io
import uuid
import wave

import pytest

from apps.ltt_voice import gia


# ── 1. Hợp đồng byte với sidecar ────────────────────────────────────────────

def _header_nhu_sidecar(sr: int = 48_000) -> bytes:
    """Dựng header **đúng cách** `voice_sidecar/server.py::_wav_header_mo` dựng.

    ⛔ Chép cách dựng, không import sidecar: bộ test không được đòi
       `voice_sidecar` nạp được (nó kéo theo torch). Cái được ghim ở đây là
       **hình dạng byte**, và đó đúng là thứ chung giữa hai bên.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.setnframes(1_000_000_000)
    return buf.getvalue()


def test_header_sidecar_dai_dung_bang_hang_so_da_ghim():
    assert len(_header_nhu_sidecar()) == gia.DAI_HEADER_WAV


@pytest.mark.parametrize("sr", [16_000, 24_000, 48_000])
def test_doc_duoc_sample_rate_tu_header_that(sr):
    assert gia.doc_sample_rate(_header_nhu_sidecar(sr)) == sr


def test_header_ngan_thi_NEM_chu_khong_doan():
    with pytest.raises(gia.DinhDangLa):
        gia.doc_sample_rate(_header_nhu_sidecar()[:20])


def test_khong_phai_RIFF_thi_NEM():
    with pytest.raises(gia.DinhDangLa):
        gia.doc_sample_rate(b"\x00" * gia.DAI_HEADER_WAV)


def test_STEREO_thi_NEM_chu_khong_thu_sai_mot_nua():
    """🔴 Stereo mà tính như mono ⇒ số giây gấp đôi ⇒ **thu gấp đôi**.

    Đây là lý do `doc_sample_rate` kiểm số kênh chứ không chỉ đọc sample rate.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(48_000)
        w.setnframes(1000)
    with pytest.raises(gia.DinhDangLa):
        gia.doc_sample_rate(buf.getvalue())


# ── 2. Byte -> giây -> tiền ─────────────────────────────────────────────────

@pytest.mark.parametrize("byte_pcm,sr,giay", [
    (96_000, 48_000, 1.0),
    (48_000, 48_000, 0.5),
    (0, 48_000, 0.0),
    (96_000, 24_000, 2.0),
])
def test_giay_tu_pcm(byte_pcm, sr, giay):
    assert gia.giay_tu_pcm(byte_pcm, sr) == pytest.approx(giay)


def test_byte_le_lam_tron_XUONG_mau_khong_lam_tron_len():
    """Một byte lẻ không thành một mẫu. Làm tròn lên ở đây là thu cho thứ chưa gửi."""
    assert gia.giay_tu_pcm(1, 48_000) == 0.0
    assert gia.giay_tu_pcm(3, 48_000) == pytest.approx(1 / 48_000)


def test_sample_rate_0_thi_NEM():
    with pytest.raises(gia.DinhDangLa):
        gia.giay_tu_pcm(96_000, 0)


# ── 3. Quyết toán: thu ĐÚNG phần đã gửi, hoàn phần dư ───────────────────────

@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "phatdan511.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield
    dbmod.reset_engine()


def _phien():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _dong(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _nap_credit(uid: str, so: int) -> None:
    from platform_core import credit
    gen, db = _phien()
    try:
        credit.nap(db, uid, so, note="thu nghiem 511")
        db.commit()
    finally:
        _dong(gen)


def _so_du(uid: str) -> int:
    from platform_core import credit
    gen, db = _phien()
    try:
        return credit.so_du(db, uid)
    finally:
        _dong(gen)


def test_quyet_toan_thu_theo_BYTE_DA_GUI_va_hoan_phan_du(moi_truong):
    """Bất biến trung tâm của mô hình β."""
    from platform_core import credit
    from apps.ltt_voice.routes import _p_phat_dan

    uid = "u-" + uuid.uuid4().hex[:8]
    ma_phien = "stream:" + uuid.uuid4().hex
    _nap_credit(uid, 1000)

    # Giữ chỗ cho một bài ~1.000 ký tự.
    giu = gia.uoc_tran(so_ky_tu=1000)
    gen, db = _phien()
    try:
        credit.giu_cho(db, uid, giu, ma_phien)
        db.commit()
    finally:
        _dong(gen)
    assert _so_du(uid) == 1000 - giu, "giu cho phai tru ngay"

    # Khách nghe được 10 giây rồi ngắt.
    byte_10s = 10 * 48_000 * 2
    _p_phat_dan._quyet_toan(uid, ma_phien, byte_10s, 48_000)

    that = gia.tinh(10.0)
    assert _so_du(uid) == 1000 - that, (
        f"phai thu {that} cho 10 giay, khong phai giu {giu}")
    assert that < giu, "10 giay phai re hon giu cho cua bai 1.000 ky tu"


def test_ngat_NGAY_LAP_TUC_thi_thu_0_va_hoan_DU(moi_truong):
    """0 byte đã gửi = 0 giây = **thu 0**. Cùng luật với `jobs.py` khi ffprobe hỏng."""
    from platform_core import credit
    from apps.ltt_voice.routes import _p_phat_dan

    uid = "u-" + uuid.uuid4().hex[:8]
    ma_phien = "stream:" + uuid.uuid4().hex
    _nap_credit(uid, 500)
    giu = gia.uoc_tran(so_ky_tu=1000)
    gen, db = _phien()
    try:
        credit.giu_cho(db, uid, giu, ma_phien)
        db.commit()
    finally:
        _dong(gen)

    _p_phat_dan._quyet_toan(uid, ma_phien, 0, 48_000)

    assert _so_du(uid) == 500, "ngat ngay lap tuc van bi thu"


# ── 4. Cờ tắt ⇒ KHÔNG có bề mặt ────────────────────────────────────────────
#
# `manifest.py`: *"một tab dẫn tới 404 tệ hơn không có tab, vì nó biến một lời
# hứa thành một lỗi."* Cùng luật cho nút này.

def test_co_TAT_mac_dinh(monkeypatch):
    from apps.ltt_voice.routes import _p_phat_dan
    monkeypatch.delenv("LTT_VOICE_STREAM", raising=False)
    assert _p_phat_dan.bat_phat_dan() is False


@pytest.mark.parametrize("gia_tri,mong", [
    ("1", True), ("0", False), ("", False), ("true", False), ("  1  ", True),
])
def test_co_chi_bat_boi_dung_chuoi_1(monkeypatch, gia_tri, mong):
    """⛔ Chỉ `"1"`. `"true"` KHÔNG bật — sidecar cũng đọc y hệt vậy, và hai
    phía hiểu cờ khác nhau là cách sinh ra trạng thái *web mở, cổng đóng*."""
    from apps.ltt_voice.routes import _p_phat_dan
    monkeypatch.setenv("LTT_VOICE_STREAM", gia_tri)
    assert _p_phat_dan.bat_phat_dan() is mong


def test_template_GAC_nut_sau_co_chu_khong_hien_vo_dieu_kien():
    """Nút phải nằm trong `{% if phat_dan_bat %}`, và route phải nhận cùng cờ."""
    import pathlib
    goc = pathlib.Path(__file__).resolve().parents[1]
    tpl = (goc / "apps/ltt_voice/templates/ltt_voice_studio.html").read_text(
        encoding="utf-8")
    assert "lv-nut-phat" in tpl, "template chua co nut phat dan"
    truoc = tpl[:tpl.index("lv-nut-phat")]
    assert "{% if phat_dan_bat %}" in truoc, \
        "nut phat dan khong nam sau co — no se hien ca khi cua tra 404"

    tao = (goc / "apps/ltt_voice/routes/_p_tao.py").read_text(encoding="utf-8")
    assert "phat_dan_bat=_p_phat_dan.bat_phat_dan()" in tao, \
        "trang Studio khong truyen co — Jinja se coi `phat_dan_bat` la rong"


def test_js_doc_sample_rate_tu_HEADER_chu_khong_go_tay():
    """🔴 Gõ `48000` vào JS là hằng số thứ ba cạnh hai hằng số đã có.

    Ngày engine đổi tần số, tiếng phát ra sai cao độ mà **không lỗi nào báo**.
    """
    import pathlib
    js = (pathlib.Path(__file__).resolve().parents[1]
          / "server/static/voice.js").read_text(encoding="utf-8")
    i = js.index("function ganPhatDan")
    than = js[i:js.index("function csrfCua", i)]
    assert "getUint32(24, true)" in than, "khong doc sample rate tu header"
    assert "48000" not in than, "sample rate bi go tay vao JS"


# ── 4b. Cảnh báo lùi giọng phải tới khách, NGUYÊN VĂN ──────────────────────

def test_canh_bao_lui_giong_ma_hoa_duoc_qua_dau_HTTP():
    """🔴 Hai lỗi trong một, và cả hai đều im lặng.

    ① Bản đầu của tôi đặt `X-Canh-Bao: "1"` — một **lá cờ**. Khách biết *"có gì
       đó đã đổi"* mà không biết **đổi thành giọng nào**. `lui_giong.py` sinh ra
       để chống lùi im lặng; một lá cờ là im một nửa.

    ② Nhét chuỗi thô vào đầu HTTP thì **cả phản hồi thành 500**: đầu HTTP chỉ
       nhận latin-1, câu cảnh báo thì luôn có dấu tiếng Việt.
       `voice_sidecar/server.py::_dau` đã ghi đúng kiểu hỏng ấy — *"việc đã làm
       xong rồi mới bị vứt đi"*: model sinh đủ tiếng, rồi cả lượt tan vì một
       chuỗi GIẢI THÍCH.
    """
    from urllib.parse import quote, unquote
    from apps.ltt_voice import lui_giong

    u = lui_giong.UngVien(ma="vc_abc", gioi="nu", ngon_ngu="en", nhan="Amelia")
    cau = lui_giong.dien_canh_bao(lui_giong.CANH_BAO, u)

    assert "Amelia" in cau, "cau canh bao khong noi giong thay la ai"
    with pytest.raises(UnicodeEncodeError):
        cau.encode("latin-1")          # <- chung minh (2) la that

    ma = quote(cau, safe="")
    ma.encode("latin-1")               # khong duoc nem
    assert unquote(ma) == cau, "vong ve khong khop — khach doc duoc chu la"


def test_route_phat_dan_MA_HOA_canh_bao_chu_khong_dat_co():
    """Chốt hình dạng: route phải `quote(...)`, không phải gán `"1"`."""
    import ast
    import pathlib
    goc = pathlib.Path(__file__).resolve().parents[1]
    src = (goc / "apps/ltt_voice/routes/_p_phat_dan.py").read_text(encoding="utf-8")
    assert "quote(canh_bao[0]" in src, "canh bao khong duoc ma hoa"
    assert 'dau["X-Canh-Bao"] = "1"' not in src, "van dat co thay vi cau"
    ast.parse(src)


def test_js_GIAI_MA_canh_bao_va_hien_ra():
    import pathlib
    js = (pathlib.Path(__file__).resolve().parents[1]
          / "server/static/voice.js").read_text(encoding="utf-8")
    i = js.index("function ganPhatDan")
    than = js[i:js.index("function csrfCua", i)]
    assert "X-Canh-Bao" in than, "JS khong doc dau canh bao"
    assert "decodeURIComponent" in than, "JS khong giai ma — khach doc ra %C3%..."
    assert "baoTin(" in than, "JS giai ma roi khong hien ra"


# ── 4c. `/phat-dan` phải ở bậc rate-limit ĐẮT ──────────────────────────────

def test_phat_dan_nam_o_bac_DAT_chu_khong_phai_bac_chung():
    """🔴 Cửa này giữ suất `vieneu_gpu` DUY NHẤT suốt cả lượt phát.

    Và mô hình β thu theo **byte đã gửi**, nên ngắt trước byte đầu thu **0**.
    Hai điều đó cộng lại thành một vòng lặp không tốn tiền mà vẫn chiếm card.

    Bậc chung là **120/phút** — quá rộng cho một cửa giữ GPU. Bậc đắt là
    **30/phút**. `nghe_thu_cua_toi` chặn đúng lớp ấy cho đường miễn phí bằng
    `MOI_GIO=6`; đường trả tiền thì credit lo phần kinh tế, còn phần **tài
    nguyên** cần bậc này.

    ⚠️ Đây là một trong hai chỗ chiến dịch chạm `server/` (CLAUDE.md luật 20).
       Lý do nó KHÔNG thuộc `apps/`: chính module ấy khai *"Trung tâm ở
       middleware → KHÔNG sửa từng app"*. Danh sách bậc **là** điểm mở rộng đã
       thiết kế; thêm một bộ đếm riêng trong app mới là đi ngược nó.
    """
    from server.usage_rate_limit import _EXPENSIVE_SUFFIXES as DAT

    assert "/ltt-voice/phat-dan".endswith(DAT), \
        "/phat-dan roi xuong bac chung 120/phut — qua rong cho mot cua giu GPU"
    # Đối chứng: cửa tạo thường KHÔNG được kéo theo vào bậc đắt.
    assert not "/ltt-voice/tao".endswith(DAT), \
        "/tao bi keo vao bac dat — that chat nham mot cua khong giu GPU"


# ── 5. Trần luồng CPU của sidecar (QĐ-V02) ─────────────────────────────────
#
# Đo 09/09: lõi vật lý 10, `torch.get_num_threads()` = 10 ⇒ một lượt sinh lấy
# TRỌN số lõi cho phần CPU. Cùng khuyết tật CLAUDE.md ghi cho `demucs_runner.py`.
#
# ⛔ Đọc bằng AST, KHÔNG import `voice_sidecar.engine` — nó kéo theo torch, và
#    bộ test không được đòi thứ đó. Cùng kỹ thuật `test_504` dùng.

def _cay_engine():
    import ast
    import pathlib
    goc = pathlib.Path(__file__).resolve().parents[1]
    return ast.parse((goc / "voice_sidecar/engine.py").read_text(encoding="utf-8"))


def test_tran_luong_mac_dinh_la_4_va_DAN_XUAT_duoc():
    """4 = 10 lõi vật lý − 6 (trần `-n 6` của CLAUDE.md). Không phải số đặt bừa."""
    import ast
    for n in _cay_engine().body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == \
                "TRAN_LUONG_MAC_DINH":
            assert n.value.value == 4, "doi mac dinh thi phai doi ca luan cu"
            return
    pytest.fail("khong thay TRAN_LUONG_MAC_DINH")


def test_tran_luong_GOI_TRUOC_khi_nap_model():
    """🔴 Chốt "có đường VÀ có xe": trần phải được GỌI, và gọi ĐÚNG CHỖ.

    `set_num_threads` sau khi model nạp là vô nghĩa — pool luồng của torch dựng
    lúc nạp và không thu lại được. Nên phép kiểm này đo **thứ tự**, không chỉ
    đo sự tồn tại của hàm.
    """
    import ast
    nap = next(n for n in ast.walk(_cay_engine())
               if isinstance(n, ast.FunctionDef) and n.name == "nap")

    dong_tran = dong_nap = None
    for n in ast.walk(nap):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Attribute) and \
                    n.func.attr == "_dat_tran_luong":
                dong_tran = n.lineno
        if isinstance(n, ast.ImportFrom) and n.module == "vieneu":
            dong_nap = n.lineno

    assert dong_tran, "`nap()` khong goi `_dat_tran_luong()` — nang luc co, khong ai di"
    assert dong_nap, "khong thay `from vieneu import ...` trong nap()"
    assert dong_tran < dong_nap, (
        f"dat tran o dong {dong_tran} nhung model nap o dong {dong_nap} — "
        "dat SAU khi nap thi torch da dung xong pool luong")


def test_dat_ca_OMP_NUM_THREADS_chu_khong_chi_torch():
    """ONNX Runtime và BLAS đọc biến môi trường, không đọc `torch.set_num_threads`.

    Đặt một thứ mà quên thứ kia là để nửa số luồng thoát ra ngoài trần.
    """
    import ast
    ham = next(n for n in ast.walk(_cay_engine())
               if isinstance(n, ast.FunctionDef) and n.name == "_dat_tran_luong")
    than = ast.dump(ham)
    assert "OMP_NUM_THREADS" in than, "quen OMP_NUM_THREADS"
    assert "set_num_threads" in than, "quen torch.set_num_threads"


def test_quyet_toan_KHONG_NEM_khi_so_hong(moi_truong):
    """Nhánh dọn dẹp: phản hồi đã gửi xong, ném ở đây chỉ che mất lỗi thật."""
    from apps.ltt_voice.routes import _p_phat_dan
    # `ma_phien` chưa từng có bút toán `hold` nào -> quyết toán không có gì để kết.
    _p_phat_dan._quyet_toan("u-khong-ton-tai", "stream:khong-co", 96_000, 48_000)
