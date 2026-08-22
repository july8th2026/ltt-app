"""
test_255 — bộ sinh nửa đối chứng Gemini cho G6b. (H37)

Không mạng, không GPU, **không tiêu một đồng nào**.

Mỗi test chốt một thứ mà nếu sai thì hoặc là **mất tiền oan**, hoặc là ra một con
số trông có vẻ đúng nhưng đo nhầm thứ.
"""
from __future__ import annotations

import json

import pytest

from tools import doi_chung_gemini as G

PNG = (bytes.fromhex("89504e47") + bytes.fromhex("0d0a1a0a")
       + bytes.fromhex("0000000d") + b"IHDR")


def _png(rong: int, cao: int) -> bytes:
    import struct
    return PNG + struct.pack(">II", rong, cao) + bytes(30)


class _Resp:
    def __init__(self, status, than):
        self.status_code, self._than = status, than

    def json(self):
        return self._than


def _jpeg(rong: int, cao: int) -> bytes:
    """JPEG toi thieu: SOI + APP0 + mot khung SOF0 mang kich thuoc.

    Viet bang HEX chu khong bang escape: nhung tep test nay doi khi duoc sinh ra
    bang script, va mot tang thoat chuoi nua bien chung thanh byte that - luc do
    ca tep khong parse duoc. Da dinh dung loi nay hai lan trong mot phien.
    """
    import struct
    sof = (bytes.fromhex("ffc0") + struct.pack(">HBHHB", 17, 8, cao, rong, 3)
           + bytes(9))
    app0 = bytes.fromhex("ffe0") + struct.pack(">H", 16) + b"JFIF" + bytes(10)
    return bytes.fromhex("ffd8") + app0 + sof


def _anh_gemini(rong=1376, cao=768, kieu="jpg"):
    """⚠️ Mặc định là **JPEG 1376×768** vì đó là thứ Gemini trả THẬT (đo 22/08).
    Mặc định cũ là PNG 2560×1440 — một giả định, và nó đã sai."""
    import base64
    d = _jpeg(rong, cao) if kieu == "jpg" else _png(rong, cao)
    return {"candidates": [{"content": {"parts": [
        {"inlineData": {"data": base64.b64encode(d).decode()}}]}}]}


def _goi(ket_qua):
    goi = []

    def http(url, *, json=None, headers=None, timeout=None):
        goi.append({"url": url, "json": json, "headers": headers})
        v = ket_qua(len(goi) - 1) if callable(ket_qua) else ket_qua
        return _Resp(*v) if isinstance(v, tuple) else _Resp(200, v)

    http.goi = goi          # type: ignore[attr-defined]
    return http


# ═══════════ ① mặc định KHÔNG được tiêu tiền ════════════════════════════════
def test_khong_co_co_that_thi_KHONG_goi_mang(tmp_path):
    """⛔ Một lệnh gõ nhầm không được phép thành một hoá đơn."""
    http = _goi(_anh_gemini())
    kq = G.chay(tmp_path, that=False, prompts=G.doc_prompt(), goi=http,
                lay_key=lambda: "khong-duoc-dung")
    assert kq["thu_kho"] is True
    assert http.goi == []
    assert list(tmp_path.glob("*.png")) == []


def test_thu_kho_KHONG_lay_ca_khoa(tmp_path):
    """Lấy khoá là chạm CSDL và ghi telemetry. Chạy thử không được để lại dấu vết."""
    def no():
        pytest.fail("thu kho ma van lay khoa")
    G.chay(tmp_path, that=False, prompts=G.doc_prompt()[:2], lay_key=no)


# ═══════════ ② cùng một văn bản cho cả hai bên ══════════════════════════════
def test_gui_DUNG_van_ban_cua_bo_prompt_chung(tmp_path):
    """⛔ So hai model bằng hai prompt khác nhau thì con số đo được là khác biệt
    giữa hai **prompt**, không phải giữa hai **model**."""
    p = G.doc_prompt()[:3]
    http = _goi(_anh_gemini())
    G.chay(tmp_path, that=True, prompts=p, goi=http, lay_key=lambda: "k")
    da_gui = [g["json"]["contents"][0]["parts"][0]["text"] for g in http.goi]
    assert da_gui == [m["text"] for m in p]


def test_bo_prompt_chung_la_bo_TIENG_ANH_ma_phia_ta_dung():
    assert G.BO_PROMPT.name == "prompts_30_en.json"
    assert len(G.doc_prompt()) == 30


def test_ti_le_khung_khop_voi_phia_ta():
    """G3 chạy 2560×1440 = 16:9. Lệch tỉ lệ là so hai bố cục khác nhau."""
    assert G.TI_LE == "16:9"


def test_doi_thu_la_model_DANG_BAN(tmp_path):
    """Đối chứng quan trọng nhất là thứ khách đang trả tiền cho, không phải một
    model rẻ hơn cho dễ thắng."""
    assert G.MODEL == "gemini-3-pro-image"
    http = _goi(_anh_gemini())
    G.chay(tmp_path, that=True, prompts=G.doc_prompt()[:1], goi=http,
           lay_key=lambda: "k")
    assert "gemini-3-pro-image" in http.goi[0]["url"]


# ═══════════ ③ ghi lại kích thước thật ══════════════════════════════════════
def test_ghi_KICH_THUOC_that_cua_tung_anh(tmp_path):
    """Ảnh to hơn trông "nét hơn" bất kể model. Không ghi số thì bước dựng lô so mù
    không biết phải chuẩn hoá cái gì.

    Chốt này **đã đền công ngay hôm đầu**: nó lộ ra Gemini trả 1376×768 trong khi
    phía ta chạy 2560×1440 — lệch 1,86 lần chiều dài, và lệch **về phía có lợi cho
    ta**. So mù mà bỏ qua thì kết luận "model nhà đẹp hơn" là do độ phân giải."""
    http = _goi(_anh_gemini(1024, 576))
    kq = G.chay(tmp_path, that=True, prompts=G.doc_prompt()[:2], goi=http,
                lay_key=lambda: "k")
    assert all(a["rong"] == 1024 and a["cao"] == 576 for a in kq["anh"])


# ═══════════ nhận dạng theo BYTE THẬT, không theo giả định ══════════════════
def test_JPEG_duoc_dat_dung_duoi_va_doc_duoc_kich_thuoc(tmp_path):
    """⛔ SỰ CỐ THẬT 22/08 23:30: bản đầu giả định Gemini trả PNG, đặt đuôi `.png`
    cho 30 tệp JPEG, và cái chốt đọc kích thước **không chạy một lần nào** — nó chỉ
    in "không rõ kích thước" 30 lần."""
    http = _goi(_anh_gemini(1376, 768, "jpg"))
    kq = G.chay(tmp_path, that=True, prompts=G.doc_prompt()[:1], goi=http,
                lay_key=lambda: "k")
    assert kq["anh"][0]["tep"].endswith(".jpg")
    assert kq["anh"][0]["dinh_dang"] == "jpg"
    assert (kq["anh"][0]["rong"], kq["anh"][0]["cao"]) == (1376, 768)
    assert list(tmp_path.glob("*.png")) == []


def test_PNG_van_nhan_dung(tmp_path):
    http = _goi(_anh_gemini(800, 600, "png"))
    kq = G.chay(tmp_path, that=True, prompts=G.doc_prompt()[:1], goi=http,
                lay_key=lambda: "k")
    assert kq["anh"][0]["dinh_dang"] == "png"
    assert (kq["anh"][0]["rong"], kq["anh"][0]["cao"]) == (800, 600)


def test_nhan_dang_doc_duoc_ca_hai_dinh_dang():
    assert G.nhan_dang(_jpeg(1376, 768)) == ("jpg", (1376, 768))
    assert G.nhan_dang(_png(2560, 1440)) == ("png", (2560, 1440))
    assert G.nhan_dang(b"khong phai anh gi ca") == ("bin", None)


def test_ban_ke_NEU_TEN_ca_hai_bien_gay_nhieu(tmp_path):
    """Bản kê phải tự nói ra cả kích thước lẫn định dạng. Gemini trả JPEG (nén mất
    mát), phía ta trả PNG — khác định dạng cũng là một biến gây nhiễu."""
    http = _goi(_anh_gemini())
    G.chay(tmp_path, that=True, prompts=G.doc_prompt()[:1], goi=http,
           lay_key=lambda: "k")
    d = json.loads((tmp_path / "ban_ke.json").read_text(encoding="utf-8"))
    assert d["dinh_dang"] == ["jpg"] and d["kich_co"] == ["1376x768"]
    assert "DINH DANG" in d["_doc"] and "KICH THUOC" in d["_doc"]


def test_ban_ke_CANH_BAO_ve_chuan_hoa(tmp_path):
    """Bản kê là thứ người sau đọc. Nó phải tự nói ra cái bẫy."""
    http = _goi(_anh_gemini())
    G.chay(tmp_path, that=True, prompts=G.doc_prompt()[:1], goi=http,
           lay_key=lambda: "k")
    d = json.loads((tmp_path / "ban_ke.json").read_text(encoding="utf-8"))
    assert "chuan hoa" in d["_doc"].lower()


def test_doc_duoc_kich_thuoc_PNG_that():
    assert G.kich_thuoc_png(_png(2560, 1440)) == (2560, 1440)
    assert G.kich_thuoc_png(b"khong phai png") is None
    assert G.kich_thuoc_png(b"") is None


# ═══════════ ④ chạy lại được, không sinh trùng ══════════════════════════════
def test_anh_DA_CO_thi_khong_goi_lai(tmp_path):
    """Một lượt hỏng giữa chừng không được bắt trả tiền lại cho phần đã xong.

    Kiểm theo **mọi đuôi**: ảnh đã có là `.jpg`, mà chỉ dò `.png` thì lần chạy sau
    tưởng chưa có và **trả tiền lại một lần nữa**."""
    p = G.doc_prompt()[:3]
    (tmp_path / f"{p[0]['id']}.jpg").write_bytes(_jpeg(64, 64))
    http = _goi(_anh_gemini())
    G.chay(tmp_path, that=True, prompts=p, goi=http, lay_key=lambda: "k")
    assert len(http.goi) == 2, "da goi lai anh da co"


def test_mot_prompt_hong_KHONG_lam_hong_ca_lo(tmp_path):
    """29 ảnh kia đã trả tiền rồi."""
    def kb(i):
        return (500, {}) if i == 1 else _anh_gemini()

    kq = G.chay(tmp_path, that=True, prompts=G.doc_prompt()[:3], goi=_goi(kb),
                lay_key=lambda: "k")
    assert kq["so_thanh_cong"] == 2 and kq["so_hong"] == 1
    assert kq["hong"][0]["id"] == G.doc_prompt()[1]["id"]


def test_bi_chan_an_toan_bao_ro_chu_khong_ghi_tep_rong(tmp_path):
    http = _goi((200, {"promptFeedback": {"blockReason": "SAFETY"}}))
    kq = G.chay(tmp_path, that=True, prompts=G.doc_prompt()[:1], goi=http,
                lay_key=lambda: "k")
    assert kq["so_thanh_cong"] == 0
    assert list(tmp_path.glob("*.png")) == []


# ═══════════ rò rỉ khoá ═════════════════════════════════════════════════════
def test_loi_HTTP_khong_vong_lai_than_phan_hoi(tmp_path):
    """⛔ Thân lỗi của Gemini có thể vọng lại chính khoá vừa gửi. In nguyên nó ra
    log là làm lộ khoá vào một tệp ai cũng đọc được."""
    bi_mat = "AIza-BI-MAT-KHONG-DUOC-LO"
    http = _goi((400, {"error": {"message": f"API key not valid: {bi_mat}"}}))
    kq = G.chay(tmp_path, that=True, prompts=G.doc_prompt()[:1], goi=http,
                lay_key=lambda: bi_mat)
    assert bi_mat not in json.dumps(kq, ensure_ascii=False)


def test_bo_prompt_thieu_truong_thi_TU_CHOI_ngay(tmp_path):
    import pathlib
    tep = tmp_path / "xau.json"
    tep.write_text(json.dumps({"prompts": [{"id": "p1"}]}), encoding="utf-8")
    with pytest.raises(G.LoiDoiChung):
        G.doc_prompt(pathlib.Path(tep))
