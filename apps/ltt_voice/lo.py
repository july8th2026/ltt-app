"""
lo.py — nghiệp vụ của màn CHẠY LÔ.

⭐ Dùng chung bảng với Dự án (`tables_du_an.py`, cột `loai`), và dùng lại
   `du_an.py` cho mọi thứ hai bên giống nhau: tra quyền, thêm đơn vị, gán kết
   quả, tách giọng. Tệp này chỉ chứa thứ **chỉ Lô có**: đọc danh sách vào, kiểm
   hợp lệ trước khi thu tiền, và đóng gói đầu ra.

🔴 LUẬT LỚN NHẤT CỦA MÀN NÀY: **KIỂM TOÀN BỘ DANH SÁCH TRƯỚC KHI GIỮ MỘT ĐỒNG.**

   Một lô là chỗ duy nhất trong sản phẩm mà một thao tác của khách sinh ra hàng
   trăm job. Nếu dòng thứ 47 có `voice_id` gõ sai, hai cách xử lý cho hai kết
   quả rất khác nhau:

     · kiểm dần khi chạy  -> 46 job đã giữ tiền, dòng 47 hỏng, khách phải đoán
                             xem những gì đã chạy và những gì chưa;
     · kiểm hết trước     -> 0 đồng bị giữ, một bảng nói rõ dòng nào sai và sai
                             gì, khách sửa rồi chạy lại.

   Ảnh tham chiếu 04 vẽ đúng điều này bằng dòng `5 / 5 rows valid` **nằm trên**
   nút `Start Batch`. Đó không phải trang trí — đó là thứ tự.
"""
from __future__ import annotations

import csv
import io
import logging
import re

from platform_core.i18n import _ as _t

from . import du_an, giong_mau

log = logging.getLogger(__name__)

#: Trần dòng cho một lô. Cao hơn Dự án (200) vì một lô là danh sách máy sinh,
#: không phải thứ ai đó gõ tay — nhưng vẫn phải có trần: 5.000 dòng là 5.000
#: lượt xếp hàng và một trang không dựng nổi.
TRAN_DONG = 500

#: Tên cột CSV được nhận. Nhiều tên cho một ý vì khách xuất CSV từ chỗ khác
#: nhau, và ta không có quyền bắt họ đổi tiêu đề.
#:
#: 🔴 KHÔNG DẤU, và đó không phải sự lười — tiêu đề được so **sau khi bỏ dấu và
#:    hạ chữ thường** (`_khoa_cot`). Nên một dòng ở đây khớp được cả `Nội dung`,
#:    `NỘI DUNG`, `noi dung`, `noi_dung`.
#:
#: ⭐ Và nó giải một vấn đề thật ngoài chuyện gọn: `tools/check_i18n.py` đếm mọi
#:    chuỗi tiếng Việt chưa bọc `_()`, và nó **đúng khi làm vậy**. Nhưng đây là
#:    **tiêu đề cột người ta gõ vào**, không phải chữ ta hiện ra — dịch chúng là
#:    sai theo hướng ngược lại: một CSV tiếng Anh sẽ thôi khớp khi khách đổi
#:    ngôn ngữ giao diện. Bỏ dấu làm chúng thành ASCII, nên bánh cóc im **vì
#:    đúng lý do**, không phải vì bị nới.
COT_TEXT = ("text", "noi dung", "noi_dung", "cau", "content", "cau thoai")
COT_GIONG = ("voice", "voice id", "voice_id", "giong", "preset")
COT_NHAN = ("id", "ten", "name", "file", "filename", "nhan", "ten tep")


class LoiLo(du_an.LoiDuAn):
    """Lỗi của yêu cầu. Thông điệp phải nói được cách sửa."""


def _khoa_cot(s: str) -> str:
    """Tiêu đề cột -> khoá so sánh: bỏ dấu, hạ chữ thường, gộp khoảng trắng.

    ⭐ Một khách Việt xuất CSV từ Excel sẽ có tiêu đề `Nội dung`, `NỘI DUNG`,
       hoặc `Nội Dung` — ba chuỗi khác nhau, một ý. Liệt kê hết là một danh sách
       không bao giờ đủ; bỏ dấu là một phép so đúng một lần.

    `NFD` tách dấu thành ký tự tổ hợp (category `Mn`), rồi bỏ chúng đi. Chữ `đ`
    không phải tổ hợp nên phải thay riêng.
    """
    import unicodedata
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d")
    return re.sub(r"[\s_]+", " ", s).strip()


def chuan_hoa_giong(s: str) -> str:
    """Ô giọng trong CSV -> dạng có tiền tố mà cả app dùng (`m:` / `v:`).

    🔴 VÌ SAO CẦN, VÀ ĐÂY LÀ MỘT LỖI ĐÃ ĐO — LỖI TIỀN.

       Khách viết cột giọng là `Adam` hoặc `vc_bfa9…`. **Không ai gõ `m:Adam`**
       — tiền tố đó là quy ước nội bộ của bộ chọn giọng, không phải thứ ta có
       quyền bắt một tệp CSV tuân theo.

       Bản đầu đưa thẳng ô đó cho `du_an.tach_giong`, và hàm ấy trả `("", "")`
       cho mọi chuỗi không có tiền tố — tức **"dùng giọng mặc định"**. Hệ quả đo
       được: một CSV ghi `KHONG-CO-GIONG` qua phép kiểm với `0 dòng hỏng`, rồi
       cả lô chạy bằng **giọng mặc định** thay vì giọng khách ghi.

       Đó là lỗi tệ nhất trong ba lớp có thể xảy ra ở đây: không báo lỗi, vẫn
       thu tiền, và **giao sai thứ khách đặt**. Một tên giọng gõ sai đáng lẽ
       phải chặn được ở bảng xem trước — chỗ nó không tốn gì.

    ⭐ Nhận dạng bằng tiền tố `vc_` của `tables.sinh_public_id`: đó là danh tính
       giọng nhân bản, và nó không thể trùng tên một giọng dựng sẵn.
    """
    s = (s or "").strip()
    if not s or s.startswith(("m:", "v:")):
        return s
    return f"v:{s}" if s.startswith("vc_") else f"m:{s}"


def _sach_ten_tep(s: str) -> str:
    """Nhãn -> tên tệp an toàn.

    ⛔ Nhãn đến từ CSV của khách, và nó sẽ thành **tên tệp trong một zip**. Một
       nhãn `../../etc/passwd` hay `C:\\Windows\\x` là một lối thoát thư mục nếu
       ta chép thẳng. Giữ đúng chữ, số, gạch — bỏ hết phần còn lại.
    """
    s = re.sub(r"[^\w\s.-]", "", (s or "").strip(), flags=re.UNICODE)
    s = re.sub(r"[\s/\\]+", "_", s).strip("._")
    return s[:80]


def co_ve_csv(noi_dung: str) -> bool:
    """Dòng đầu có phải một hàng tiêu đề CSV không.

    🔴 VÌ SAO PHẢI TỰ NHẬN DẠNG, VÀ ĐÂY LÀ MỘT LỖI ĐÃ ĐO.

       Bản đầu chỉ coi là CSV khi khách **tải tệp lên**. Nhưng người ta hay mở
       CSV, bôi đen, rồi **dán** — và lúc đó:

         · dòng tiêu đề `text,voice,name` bị đọc thành **một câu để đọc**;
         · cột giọng không bao giờ được nhìn tới, nên một `voice_id` gõ sai
           **qua được phép kiểm** và chỉ hỏng ở worker.

       Đo thật: một CSV ba dòng dán vào cho ra `4 dòng, 0 hỏng`. Cả hai con số
       đều sai, và cái sai thứ hai làm hỏng đúng lời hứa lớn nhất của màn này.

    ⭐ Phép nhận dạng cố ý **hẹp**: phải có dấu phân cách **và** một tên cột đã
       biết trên dòng đầu. Đoán rộng hơn thì một danh sách câu tình cờ chứa dấu
       phẩy sẽ bị hiểu nhầm thành bảng — và mất luôn dòng đầu.
    """
    dong_dau = (noi_dung or "").strip().splitlines()[:1]
    if not dong_dau:
        return False
    d = dong_dau[0]
    if not any(x in d for x in (",", ";", "\t")):
        return False
    # So SAU KHI BỎ DẤU, cùng phép chuẩn hoá mà `doc_danh_sach` dùng để khớp
    # cột. Hai chỗ so tiêu đề bằng hai luật khác nhau là một chỗ để nhận dạng
    # nói "có CSV" rồi phần đọc lại bảo "không thấy cột nội dung".
    o = {_khoa_cot(c.strip('"')) for c in re.split(r"[,;\t]", d)}
    return bool(o & {_khoa_cot(x) for x in COT_TEXT})


def doc_danh_sach(noi_dung: str, *, la_csv: bool | None = None) -> list:
    """Chuỗi vào -> `[{thu_tu, text, giong, nhan}]`. **Chưa kiểm hợp lệ.**

    `la_csv=None` (mặc định) thì **tự nhận dạng** — xem `co_ve_csv`. Truyền
    tường minh chỉ khi đã biết chắc, ví dụ tệp tải lên có đuôi `.csv`.

    ⭐ Hai định dạng, một hàm: CSV có tiêu đề, hoặc mỗi dòng một câu. Tách thành
       hai hàm thì phần chung (bỏ dòng trống, cắt trần, đánh số) sẽ được chép
       hai lần.

    ⚠️ Nhận cả `,` và `;` — Excel bản tiếng Việt xuất CSV bằng dấu chấm phẩy, và
       một khách dán tệp đó vào sẽ thấy "một cột" nếu ta chỉ biết dấu phẩy.
    """
    noi_dung = (noi_dung or "").strip()
    if not noi_dung:
        raise LoiLo(_t("Chưa có danh sách để đọc."))

    if la_csv is None:
        la_csv = co_ve_csv(noi_dung)

    dong: list = []
    if la_csv:
        try:
            phuong_ngu = csv.Sniffer().sniff(noi_dung[:2000], delimiters=",;\t")
        except csv.Error:
            phuong_ngu = csv.excel
        doc = csv.DictReader(io.StringIO(noi_dung), dialect=phuong_ngu)
        if not doc.fieldnames:
            raise LoiLo(_t("Không đọc được tiêu đề cột của tệp CSV."))
        khoa = {_khoa_cot(k): k for k in doc.fieldnames}

        def lay(hang, ten_co_the):
            for t in ten_co_the:
                k = _khoa_cot(t)
                if k in khoa:
                    return str(hang.get(khoa[k]) or "").strip()
            return ""

        if not any(_khoa_cot(t) in khoa for t in COT_TEXT):
            raise LoiLo(_t(
                "Tệp CSV không có cột nội dung. Cần một cột tên: {ds}."
            ).format(ds=", ".join(COT_TEXT[:4])))

        for hang in doc:
            dong.append({"text": lay(hang, COT_TEXT),
                         "giong": chuan_hoa_giong(lay(hang, COT_GIONG)),
                         "nhan": lay(hang, COT_NHAN)})
    else:
        for d in noi_dung.splitlines():
            d = d.strip()
            if d:
                dong.append({"text": d, "giong": "", "nhan": ""})

    dong = [d for d in dong if d["text"]]
    if not dong:
        raise LoiLo(_t("Danh sách không có dòng nào có nội dung."))
    if len(dong) > TRAN_DONG:
        raise LoiLo(_t(
            "Danh sách có {n} dòng, vượt giới hạn {t} cho một lô."
        ).format(n=len(dong), t=TRAN_DONG))

    for i, d in enumerate(dong, 1):
        d["thu_tu"] = i
        d["nhan"] = _sach_ten_tep(d["nhan"]) or f"{i:03d}"
    return dong


def kiem(db, dong: list, *, owner_id: str, giong_mac_dinh: str,
         tran_ky_tu: int) -> dict:
    """Kiểm TOÀN BỘ danh sách. Trả `{dong, so_hop_le, so_hong}`.

    🔴 KHÔNG chạm CSDL để ghi, KHÔNG giữ credit, KHÔNG nộp job. Đây là bước duy
       nhất chạy **trước** khi khách bấm chạy, và toàn bộ giá trị của nó nằm ở
       chỗ nó không để lại dấu vết nào.

    Mỗi dòng nhận thêm `hop_le` (bool) và `loi` (câu nói được cách sửa).
    """
    from . import tham_chieu

    #: Cache giọng của khách: một lô 500 dòng dùng 3 giọng thì tra 3 lần, không
    #: 500 lần. Không có nó thì phép kiểm "an toàn" lại thành thứ chậm nhất màn.
    da_tra: dict = {}

    def giong_ok(chon: str) -> str:
        """Trả câu lỗi, hoặc `""` nếu dùng được."""
        if chon in da_tra:
            return da_tra[chon]
        voice_id, preset = du_an.tach_giong(chon)
        loi = ""
        if preset and not giong_mau.hop_le(preset):
            loi = _t("Không có giọng dựng sẵn tên {g}.").format(g=preset)
        elif voice_id:
            ho_so = tham_chieu.tim_profile(db, voice_id, owner_id=owner_id)
            if ho_so is None:
                # ⛔ Cùng một thông điệp cho "không tồn tại" và "không phải của
                #    bạn" — phân biệt hai câu đó là cho phép dò `voice_id`.
                loi = _t("Không tìm thấy giọng {g} trong tài khoản của bạn."
                         ).format(g=voice_id)
            elif ho_so.trang_thai != "active":
                loi = _t("Giọng {g} đang bị tắt.").format(g=voice_id)
        da_tra[chon] = loi
        return loi

    so_hop_le = 0
    for d in dong:
        loi = ""
        if len(d["text"]) > tran_ky_tu:
            loi = _t("Dài {n} ký tự, vượt giới hạn {t}."
                     ).format(n=len(d["text"]), t=tran_ky_tu)
        else:
            loi = giong_ok(d.get("giong") or giong_mac_dinh)
        d["hop_le"] = not loi
        d["loi"] = loi
        so_hop_le += 1 if not loi else 0

    return {"dong": dong, "so_hop_le": so_hop_le,
            "so_hong": len(dong) - so_hop_le}


def tao_lo(db, *, owner_id: str, ten: str, giong: str, dong: list):
    """Tạo lô + mọi dòng. Gọi **sau** khi `kiem` nói mọi dòng hợp lệ."""
    from .tables_du_an import LOAI_LO, VoiceBlock, VoiceProject

    ten = (ten or "").strip() or _t("Lô không tên")
    lo = VoiceProject(owner_id=str(owner_id), ten=ten[:200], loai=LOAI_LO,
                      giong_mac_dinh=(giong or "")[:64], trang_thai="nhap")
    db.add(lo)
    db.flush()

    for d in dong:
        db.add(VoiceBlock(project_id=lo.id, thu_tu=float(d["thu_tu"]),
                          text=d["text"], giong=(d.get("giong") or "")[:64],
                          nhan=(d.get("nhan") or "")[:120]))
    db.flush()
    return lo


def danh_sach(db, owner_id: str) -> list:
    from sqlalchemy import select

    from .tables_du_an import LOAI_LO, VoiceProject
    return list(db.execute(
        select(VoiceProject)
        .where(VoiceProject.owner_id == str(owner_id),
               VoiceProject.loai == LOAI_LO)
        .order_by(VoiceProject.tao_luc.desc())
    ).scalars())


def tim(db, public_id: str, *, owner_id: str):
    """Tra một lô. Trả `None` nếu không phải của khách **hoặc không phải lô**.

    ⛔ Phải kiểm cả `loai`: hai màn dùng chung bảng, nên không kiểm thì một
       `public_id` của Dự án mở được bằng đường của Lô — và màn Lô sẽ dựng một
       dự án bằng giao diện sai.
    """
    from .tables_du_an import LOAI_LO
    return du_an.tim(db, public_id, owner_id=owner_id, loai=LOAI_LO)


def tom_tat(cac: list) -> dict:
    t = du_an.tom_tat(cac)
    t["cho"] = len([k for k in cac if k.trang_thai == "moi"])
    # Ước thời gian còn lại, dựa trên số giây THẬT đã đo của những dòng đã xong.
    # Chưa dòng nào xong thì **không đoán** — một con số bịa ở đây sẽ được đọc
    # như một lời hứa.
    xong = [k for k in cac if k.trang_thai == "xong" and (k.giay or 0) > 0]
    t["giay_moi_dong"] = round(sum(k.giay for k in xong) / len(xong), 1) if xong else 0
    con = t["cho"] + t["dang_tao"]
    t["uoc_con_lai_s"] = round(t["giay_moi_dong"] * con) if xong and con else 0
    return t
