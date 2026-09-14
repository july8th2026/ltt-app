"""Ba họ lỗi còn lại phải nói CÙNG một thứ tiếng và mang CÙNG những trường.

Rà 14/09/2026 (chiến dịch AUDIT API) đo được: bốn cửa công khai cùng báo "hết
credit" bằng **hai hợp đồng khác nhau**.

    jobs.py       -> "Not enough credit for this call." + required_credit + balance
    chat.py       -> str(e) = "Khong du credit: can 1234, con 56."
    streaming.py  -> str(e) = "so du khong du cho phan giu cho cua luot nay"
    workflows.py  -> str(loi)

Ba cửa dưới trả cho khách một câu **tiếng Việt không dấu của nội bộ**, và khách
muốn biết phải nạp bao nhiêu thì chỉ còn cách phân tích chuỗi.

⛔ VÌ SAO ĐỌC AST CHỨ KHÔNG QUÉT VĂN BẢN. Một phép kiểm `"str(e)" not in
   nguon` khớp luôn vào chính đoạn chú thích ở trên — đúng cái bẫy "bộ dò phạt
   việc giải thích" đã cắn trong phiên này. Ở đây ta hỏi cây cú pháp: đối số thứ
   nhất của mỗi lượt gọi `insufficient_credit` là TÊN `THIEU_CREDIT_LOI` hay là
   một lời gọi `str(...)`.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from platform_core import credit
from platform_core.public_api import errors, limits
from platform_core.runtime_noi_bo import luong

GOC = pathlib.Path(__file__).resolve().parents[1]
#: Mọi cửa `/api/v1` có nhánh "hết credit". Thêm cửa mới thì thêm vào đây —
#: danh sách rỗng đi là phép kiểm chết, nên có mệnh đề đếm ở dưới.
CUA = ("server/api/chat.py", "server/api/streaming.py",
       "server/api/workflows.py", "server/api/jobs.py")


def _goi_insufficient(tep: str) -> list[ast.Call]:
    cay = ast.parse((GOC / tep).read_text(encoding="utf-8"))
    return [n for n in ast.walk(cay)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "insufficient_credit"]


def test_moi_cua_deu_co_nhanh_het_credit():
    """Đối chứng cho ba ca dưới: chúng vô nghĩa nếu tập hợp rỗng đi."""
    tong = sum(len(_goi_insufficient(t)) for t in CUA)
    assert tong >= 5, f"chi tim thay {tong} luot goi — danh sach CUA da cu?"


@pytest.mark.parametrize("tep", CUA)
def test_khong_cua_nao_tra_str_e_cho_khach(tep):
    for goi in _goi_insufficient(tep):
        assert goi.args, f"{tep}: insufficient_credit() khong doi so"
        d = goi.args[0]
        la_str = isinstance(d, ast.Call) and isinstance(d.func, ast.Name) \
            and d.func.id == "str"
        assert not la_str, (
            f"{tep} dong {d.lineno}: tra `str(e)` cho khach — do la loi noi bo, "
            "tieng Viet khong dau, va khong mang so nao")


@pytest.mark.parametrize("tep", CUA)
def test_moi_cua_dung_dung_MOT_cau(tep):
    for goi in _goi_insufficient(tep):
        d = goi.args[0]
        ten = isinstance(d, ast.Name) and d.id == "THIEU_CREDIT_LOI"
        chuoi = isinstance(d, ast.Constant) and d.value == errors.THIEU_CREDIT_LOI
        assert ten or chuoi, (
            f"{tep} dong {d.lineno}: cau bao het credit phai la "
            "`THIEU_CREDIT_LOI` — hai ban van se troi khoi nhau")


def test_thieu_credit_chi_tiet_dich_hai_so():
    e = credit.ThieuCreditError("x", can=1234, con=56)
    assert errors.thieu_credit_chi_tiet(e) == {"required_credit": 1234,
                                               "balance": 56}


def test_thieu_credit_chi_tiet_tra_rong_khi_khong_biet():
    """Đối chứng: không có số thì phải ra `{}`, không phải `{a: None}`.

    Bên gọi `**` thẳng vào `insufficient_credit`, nên một khoá mang `None` sẽ
    thành một trường công khai `"required_credit": null` — tệ hơn là vắng mặt.
    """
    assert errors.thieu_credit_chi_tiet(credit.ThieuCreditError("x")) == {}
    assert errors.thieu_credit_chi_tiet(None) == {}
    assert errors.thieu_credit_chi_tiet(ValueError("khong lien quan")) == {}


def test_luong_boc_lai_thi_GIU_hai_so():
    """`luong.ThieuCredit` hay bọc `credit.ThieuCreditError`; bọc không được rơi.

    Rơi thì cửa stream trả một lỗi nghèo hơn cửa job cho CÙNG một sự việc — đúng
    thứ đợt rà này tìm ra.
    """
    goc = credit.ThieuCreditError("Khong du credit: can 900, con 10.",
                                  can=900, con=10)
    boc = luong.ThieuCredit.tu_loi(goc)
    assert errors.thieu_credit_chi_tiet(boc) == {"required_credit": 900,
                                                 "balance": 10}


def test_dang_ban_khong_duoc_bia_retry_after():
    """`DangBan` mang sẵn `thu_lai_sau_s`; cửa phải dùng nó, không dùng 15."""
    loi = limits.execution_busy("ltt_38_3090", retry_after=42, reason="suat")
    assert loi.extra["resource"] == "ltt_38_3090"
    assert loi.extra["reason"] == "suat"
    assert loi.extra["retry_after"] == 42, f"Retry-After bi bo: {loi.extra}"


def test_dang_ban_khong_co_nguon_thi_khong_them_truong_rong():
    loi = limits.execution_busy("x")
    assert "reason" not in loi.extra


def test_cua_stream_chuyen_tiep_thu_lai_sau_s_va_nguon():
    """Cơ học: lượt gọi `execution_busy` ở cửa stream phải truyền CẢ HAI."""
    cay = ast.parse((GOC / "server/api/streaming.py").read_text(encoding="utf-8"))
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and n.func.attr == "execution_busy"]
    assert goi, "khong con luot goi execution_busy nao — phep kiem da chet"
    for g in goi:
        kw = {k.arg for k in g.keywords}
        assert {"retry_after", "reason"} <= kw, (
            f"dong {g.lineno}: thieu {{'retry_after','reason'}} - {kw}")
