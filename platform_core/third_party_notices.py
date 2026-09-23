"""Ghi công bên thứ ba — sinh TỪ `docs/auto_scan_video_final/THIRD_PARTY_METRICS.md`.

⭐ VÌ SAO ĐỌC TỆP TÀI LIỆU THAY VÌ CHÉP TAY (F-09, luật §18 đề bài): một số
   phụ thuộc runtime của Auto Scan Video (SQUIM_OBJECTIVE, torchaudio) mang
   trọng số cấp phép **CC BY 4.0** — giấy phép này BẮT BUỘC ghi công khi phát
   hành. Nếu bảng ghi công trên trang public bị gõ tay riêng, nó và bảng
   nghiên cứu giấy phép (`THIRD_PARTY_METRICS.md`) sẽ lệch nhau ngay lần đầu
   một làn thêm/đổi một dòng — đúng loại lỗi "hai chỗ khai một điều, không ai
   bắt khớp" mà dự án đã trả giá trước đây. Đọc thẳng bảng §1 ở đây là MỘT
   nguồn chân lý; trang chỉ hiển thị, không giữ bản sao.

`docs/` được `git archive` chép nguyên vẹn vào bản deploy (mọi commit trên
`main`, xem `docs/16_CAP_NHAT_VA_DEPLOY.md`), nên đọc tệp này ở runtime an
toàn trên production y như trên máy phát triển.
"""
from __future__ import annotations

import pathlib
import re

_GOC = pathlib.Path(__file__).resolve().parent.parent
TEP_NGUON = _GOC / "docs" / "auto_scan_video_final" / "THIRD_PARTY_METRICS.md"

#: Cột của bảng §1, ĐÚNG thứ tự tiêu đề trong `THIRD_PARTY_METRICS.md`. Đổi
#: thứ tự cột trong tài liệu mà không sửa đây ⇒ `_cot` bên dưới phát hiện lệch
#: bằng `KeyError` thay vì âm thầm đọc sai cột.
_TEN_COT = (
    "so", "dung_de", "repo_goi", "phien_ban", "model_checkpoint",
    "license_ma", "license_weights", "thuong_mai", "phan_phoi_lai",
    "nguon_tai", "checksum", "lan",
)

_TIEU_DE_MUC1 = re.compile(r"^## §1\.")
_TIEU_DE_MUC_TIEP = re.compile(r"^## §")


def _tach_dong_bang(dong: str) -> list[str]:
    """`| a | b |` -> `["a", "b"]`. Bỏ ô đầu/cuối rỗng do `|` biên."""
    o = [c.strip() for c in dong.strip().split("|")]
    if o and o[0] == "":
        o = o[1:]
    if o and o[-1] == "":
        o = o[:-1]
    return o


def doc_bang_muc1(duong_dan: pathlib.Path | None = None) -> list[dict]:
    """Đọc TOÀN BỘ bảng §1 của `THIRD_PARTY_METRICS.md` -> list[dict theo _TEN_COT].

    Không có tệp / không có bảng ⇒ `[]` — trang ghi công hiện rỗng thay vì
    500; test riêng chốt tệp+bảng phải tồn tại thật.
    """
    duong = duong_dan or TEP_NGUON
    try:
        text = duong.read_text(encoding="utf-8")
    except OSError:
        return []

    dong_bang: list[str] = []
    trong_muc1 = False
    trong_bang = False
    for dong in text.splitlines():
        if _TIEU_DE_MUC1.match(dong):
            trong_muc1 = True
            continue
        if trong_muc1 and _TIEU_DE_MUC_TIEP.match(dong):
            break
        if not trong_muc1:
            continue
        if dong.strip().startswith("|"):
            trong_bang = True
            dong_bang.append(dong)
        elif trong_bang:
            break   # het bang dau tien cua muc (dong trong hoac van xuoi)

    if len(dong_bang) < 2:
        return []

    # dong_bang[0] = tieu de, dong_bang[1] = "|---|---|..." (gach ngan)
    ket_qua = []
    for dong in dong_bang[2:]:
        o = _tach_dong_bang(dong)
        if len(o) != len(_TEN_COT):
            continue    # dong khong dung khuon (vd. bi vo tinh chen) - bo qua, khong doan
        ket_qua.append(dict(zip(_TEN_COT, o)))
    return ket_qua


def can_ghi_cong(dong: dict) -> bool:
    """CC BY (bao gom CC BY-SA/-NC) o License mã HOAC License weights ⇒ bắt
    buộc ghi công theo điều khoản giấy phép. Đây là phép thử duy nhất; trang
    và test đều gọi lại hàm này, không tự đoán lại quy tắc ở nơi khác."""
    return "CC BY" in dong.get("license_ma", "") or \
           "CC BY" in dong.get("license_weights", "")


def muc_ghi_cong(duong_dan: pathlib.Path | None = None) -> list[dict]:
    """Các dòng §1 cần ghi công — đây là danh sách trang public hiển thị."""
    return [d for d in doc_bang_muc1(duong_dan) if can_ghi_cong(d)]
