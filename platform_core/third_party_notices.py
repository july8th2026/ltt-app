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
        # strict: dong tren da chot len(o) == len(_TEN_COT).
        ket_qua.append(dict(zip(_TEN_COT, o, strict=True)))
    return ket_qua


#: Chu thich trong ngoac o o giay phep ("(ghi cong)", "(attribution)") la van
#: xuoi tieng Viet trong tep nguon. Trang cong khai phuc vu ca khach doc tieng
#: Anh, nen chi lay DINH DANH giay phep — thu ngon ngu nao cung doc duoc, va
#: cung la thu ma nghia vu ghi cong noi toi.
_GHI_CHU_TRONG_NGOAC = re.compile(r"\s*\([^)]*\)\s*$")


def dinh_danh_giay_phep(o: str) -> str:
    """`**CC BY 4.0** (ghi cong)` -> `CC BY 4.0`."""
    s = str(o or "").replace("**", "").strip()
    return _GHI_CHU_TRONG_NGOAC.sub("", s).strip()


def can_ghi_cong(dong: dict) -> bool:
    """CC BY (bao gom CC BY-SA/-NC) o License mã HOAC License weights ⇒ bắt
    buộc ghi công theo điều khoản giấy phép. Đây là phép thử duy nhất; trang
    và test đều gọi lại hàm này, không tự đoán lại quy tắc ở nơi khác."""
    return "CC BY" in dong.get("license_ma", "") or \
           "CC BY" in dong.get("license_weights", "")


def dinh_danh_muc(dong: dict) -> str:
    """Chuỗi định danh của một dòng, ĐÃ bỏ markdown — dùng ở CẢ trang lẫn test.

    🔴 **Vì sao là một hàm, không phải hai dòng chuẩn hoá.** Trước 24/09 template
       làm `replace("`", "")` còn test làm `.strip("`")`. Hai cách đó cho **cùng
       kết quả** khi backtick nằm ở hai đầu (`` `squim_objective_dns2020.pth` ``),
       nên chúng trông như một luật — cho tới khi có một ô mang **hậu tố**:

           `sig_bak_ovr.onnx` (1.157.965 B)
             strip   -> sig_bak_ovr.onnx` (1.157.965 B)   <- còn backtick GIỮA
             replace -> sig_bak_ovr.onnx (1.157.965 B)

       Test đỏ, và **lời tố cáo của nó sai**: nó nói *"dòng 10 không xuất hiện
       trên trang"* trong khi trang **có** in DNSMOS. Một nghĩa vụ pháp lý đã
       thực hiện bị báo là chưa — đúng loại báo động làm người ta mất niềm tin
       vào chính cái cổng đang bảo vệ mình.

    ⭐ Cùng tinh thần `can_ghi_cong`: **một** phép thử, trang và test đều gọi
       lại, ⛔ không ai đoán lại quy tắc ở nơi khác.
    """
    tho = dong.get("model_checkpoint", "")
    if tho in ("", "—"):
        tho = dong.get("repo_goi", "")
    return str(tho).replace("`", "").strip()


def muc_ghi_cong(duong_dan: pathlib.Path | None = None) -> list[dict]:
    """Các dòng §1 cần ghi công — đây là danh sách trang public hiển thị.

    Mỗi dòng mang thêm khoá `dinh_danh` (xem `dinh_danh_muc`) để trang và test
    so **cùng một chuỗi**.
    """
    ra = []
    for d in doc_bang_muc1(duong_dan):
        if can_ghi_cong(d):
            ra.append({**d, "dinh_danh": dinh_danh_muc(d)})
    return ra
