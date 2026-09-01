"""
du_an.py — nghiệp vụ của màn DỰ ÁN.

⭐ VÌ SAO KHÔNG NHÉT VÀO `features.py`.

   `features.py` là nghiệp vụ của **một lượt đọc**: chuẩn hoá, giải giọng, kiểm
   quyền, tính tiền. Ba cửa (web, worker, Public API) đều gọi vào đó, và mỗi
   dòng thêm vào nó là một dòng chạy trên đường đi của worker.

   Dự án là nghiệp vụ của **một tài liệu**: khối, thứ tự, trạng thái soạn thảo.
   Worker không biết dự án là gì và không cần biết — nó nhận một job sinh tiếng
   như mọi job khác.

🔴 KHÔNG CÓ LOẠI JOB MỚI. Sinh một khối = một `ltt_voice.synthesize` bình
   thường, kèm `nguon="du_an"` + `project_id` + `block_id` trong `params`.

   ⇒ Toàn bộ phần khó đã có sẵn và **không phải viết lại**: giữ credit, quyết
     toán theo giây thật, một-GPU-một-việc (`admission_resource`), thử lại,
     huỷ, hoàn tiền, lịch sử. Một loại job riêng cho dự án sẽ phải chép lại tất
     cả — và bản chép sẽ lệch ở chỗ đắt nhất.

⚠️ ĐÁNH ĐỔI ĐÃ BIẾT, ghi ra vì nó là chuyện chất lượng chứ không phải kỹ thuật:
   mỗi khối là một lượt inference riêng, tức **một ranh giới chunk**. Upstream
   issue #142, tác giả trả lời: *"việc gọi API cho từng chunk riêng lẻ làm mất
   đi tính liên tục của trạng thái cảm xúc và nhịp điệu từ đoạn trước đó."*

   Đó là lý do `xuat_mot_luot()` tồn tại: khi cả dự án dùng **một** giọng, đọc
   liền một lượt cho ra bản mượt hơn hẳn ghép N tệp. Ghép chỉ là đường lui khi
   các khối dùng giọng khác nhau — và lúc đó ranh giới là **có chủ ý**, vì đổi
   người nói thì tai người mong đợi một chỗ nối.
"""
from __future__ import annotations

import logging

from platform_core.i18n import _ as _t
from platform_core.jobs import LoiNguoiGoi

log = logging.getLogger(__name__)

#: Trần khối cho một dự án. Không phải giới hạn kỹ thuật — là giới hạn để một
#: màn hình còn dùng được và một lần "sinh tất cả" không nộp vài trăm job.
TRAN_KHOI = 200

#: Khoảng cách thứ tự khi thêm vào cuối. Rộng để chèn giữa còn chỗ.
BUOC_THU_TU = 10.0


class LoiDuAn(LoiNguoiGoi):
    """Lỗi của yêu cầu, đưa thẳng ra cho khách. Không thử lại."""


# ── tra cứu ──────────────────────────────────────────────────────────────────

def danh_sach(db, owner_id: str) -> list:
    """Dự án của một khách. **Không** gồm Lô.

    🔴 PHÉP LỌC `loai` LÀ THỨ DUY NHẤT GIỮ HAI MÀN TÁCH NHAU, và bản đầu của hàm
       này quên nó. Hệ quả đo được: mọi lô hiện ra trong danh sách Dự án, mang
       badge "Nháp", và bấm vào thì mở bằng giao diện sai.

       Chính chú thích đầu `tables_du_an.py` cảnh báo đúng điều này — tôi viết
       nó rồi vi phạm nó trong cùng một đợt. Dùng chung bảng là một lựa chọn
       đúng, nhưng nó **dời** chi phí sang chỗ khác: mọi truy vấn danh sách từ
       nay phải mang vế `loai`, và quên một chỗ là đủ.
    """
    from sqlalchemy import select

    from .tables_du_an import LOAI_DU_AN, VoiceProject
    return list(db.execute(
        select(VoiceProject)
        .where(VoiceProject.owner_id == str(owner_id),
               VoiceProject.loai == LOAI_DU_AN)
        .order_by(VoiceProject.sua_luc.desc())
    ).scalars())


def tim(db, public_id: str, *, owner_id: str, loai: str | None = "du_an"):
    """Tìm theo `public_id` **và** chủ sở hữu **và** loại, trong MỘT truy vấn.

    ⛔ Đừng tách thành "tìm theo id rồi so owner": giữa hai bước có một khoảng
       trống mà một bản vá sau này rất dễ quên bước hai. Cùng khuôn
       `tham_chieu.tim_profile`.

    `loai=None` bỏ qua vế loại — chỉ dùng khi bên gọi tự kiểm (xem `lo.tim`).
    Mặc định là `du_an` vì đó là bên gọi đông nhất, và một mặc định **an toàn**
    tốt hơn một mặc định trung lập: quên truyền thì lọc chặt hơn, không lỏng hơn.
    """
    from sqlalchemy import select

    from .tables_du_an import VoiceProject
    if not public_id or not owner_id:
        return None
    q = select(VoiceProject).where(
        VoiceProject.public_id == str(public_id),
        VoiceProject.owner_id == str(owner_id))
    if loai is not None:
        q = q.where(VoiceProject.loai == loai)
    return db.execute(q).scalar_one_or_none()


def cac_khoi(db, project_id: int) -> list:
    from sqlalchemy import select

    from .tables_du_an import VoiceBlock
    return list(db.execute(
        select(VoiceBlock).where(VoiceBlock.project_id == int(project_id))
        .order_by(VoiceBlock.thu_tu, VoiceBlock.id)
    ).scalars())


def duong_tieng(db, cac, tien_to: str) -> dict:
    """`id khối → URL nghe`. Khối mà tệp tiếng đã hết hạn thì KHÔNG có URL.

    🔴 VÌ SAO PHẢI HỎI SANG BẢNG `jobs`. `voice_block.audio_key` chỉ là con trỏ;
       tệp thật nằm trong vùng của job sinh ra nó, và `jobs` là CONTENT/30 ngày.
       Sau 30 ngày `job_content.purge_expired` xoá tệp và đặt
       `content_expired_at` — nhưng `audio_key` trên khối vẫn còn nguyên. Đọc
       thẳng `audio_key` thì trang dựng một trình phát trỏ vào hư không: khách
       bấm play, không có gì xảy ra, không có câu nào giải thích.

    ⛔ VÀ VÌ SAO NÓ LÀ MỘT HÀM chứ không phải một điều kiện chép ở mỗi chỗ. Có
       NĂM chỗ dựng đường nghe (hai ở Dự án, ba ở Chạy lô, kể cả nút tải ZIP).
       Trước hàm này cả năm đều viết `if k.audio_key` — tức để sửa đúng thì phải
       nhớ đủ năm, và chỗ thứ sáu sẽ lại quên. Một luật cho cả lớp.

    ⚠️ Một truy vấn cho cả danh sách, không một truy vấn mỗi khối: một lô 500
       dòng sẽ thành 500 lượt hỏi CSDL trên đúng con đường được hỏi lại mỗi vài
       giây.
    """
    from sqlalchemy import select

    from platform_core.models import Job

    co_khoa = [k for k in cac if k.audio_key]
    if not co_khoa:
        return {}
    ma_job = {str(k.job_id) for k in co_khoa if k.job_id}
    het_han = set()
    if ma_job:
        het_han = {
            str(x) for (x,) in db.execute(
                select(Job.id).where(Job.id.in_(ma_job),
                                     Job.content_expired_at.is_not(None)))
        }
    return {k.id: f"{tien_to}/audio/{k.audio_key}"
            for k in co_khoa if str(k.job_id or "") not in het_han}


def tim_khoi(db, project_id: int, block_id: int):
    from .tables_du_an import VoiceBlock
    k = db.get(VoiceBlock, int(block_id))
    # Kiểm khối có thuộc ĐÚNG dự án không. Route đã kiểm dự án thuộc khách,
    # nên hai phép này ghép lại là một chuỗi quyền đầy đủ.
    return k if (k is not None and k.project_id == int(project_id)) else None


# ── sửa đổi ──────────────────────────────────────────────────────────────────

def tao(db, *, owner_id: str, ten: str, giong: str = ""):
    from .tables_du_an import VoiceProject

    ten = (ten or "").strip()
    if not ten:
        raise LoiDuAn(_t("Hãy đặt tên cho dự án."))
    da = VoiceProject(owner_id=str(owner_id), ten=ten[:200],
                      giong_mac_dinh=(giong or "")[:64])
    db.add(da)
    db.flush()
    return da


def them_khoi(db, du_an, *, text: str = "", giong: str = "", sau: float | None = None):
    """Thêm một khối. `sau=None` nghĩa là thêm vào cuối.

    ⭐ `thu_tu` là số thực nên chèn vào giữa là **một** lượt ghi, không phải
       đánh số lại cả dự án.
    """
    from .tables_du_an import VoiceBlock

    hien = cac_khoi(db, du_an.id)
    if len(hien) >= TRAN_KHOI:
        raise LoiDuAn(_t(
            "Dự án đã đạt {n} khối — giới hạn hiện tại. Hãy tách thành hai dự án."
        ).format(n=TRAN_KHOI))

    if sau is None:
        thu_tu = (hien[-1].thu_tu + BUOC_THU_TU) if hien else BUOC_THU_TU
    else:
        # Chèn vào giữa `sau` và khối kế tiếp. Không có khối kế thì nối tiếp.
        ke = next((k.thu_tu for k in hien if k.thu_tu > sau), None)
        thu_tu = (sau + ke) / 2.0 if ke is not None else sau + BUOC_THU_TU

    k = VoiceBlock(project_id=du_an.id, thu_tu=thu_tu,
                   text=(text or "").strip(), giong=(giong or "")[:64])
    db.add(k)
    db.flush()
    return k


def sua_khoi(db, khoi, *, text=None, giong=None) -> None:
    """Sửa nội dung hoặc giọng.

    🔴 ĐỔI VĂN BẢN THÌ KHỐI CHUYỂN SANG `can_tao_lai`, KHÔNG PHẢI `moi`.

       Hai trạng thái đó khác nhau ở chỗ quan trọng: `can_tao_lai` nghĩa là
       **vẫn còn tệp tiếng cũ nghe được**, chỉ là nó không còn khớp văn bản.
       Gộp vào `moi` thì màn hình vứt bản cũ đi trong khi khách có thể vẫn muốn
       nghe lại nó để so — và họ mất nó mà không bấm gì cả.
    """
    doi = False
    if text is not None:
        t = (text or "").strip()
        if t != khoi.text:
            khoi.text = t
            doi = True
    if giong is not None:
        g = (giong or "")[:64]
        if g != khoi.giong:
            khoi.giong = g
            doi = True
    if doi and khoi.trang_thai == "xong":
        khoi.trang_thai = "can_tao_lai"


#: Cỡ một khối khi kịch bản KHÔNG có ngắt đoạn.
#:
#: 🔴 VÌ SAO NÓ KHÁC `TRAN_KY_TU_CONG_KHAI` (1.500), VÀ ĐÂY LÀ MỘT LỖI ĐÃ ĐO.
#:
#:    Bản đầu của `nhap_van_ban` gọi `chia_doan(tran_moi_doan=1500)` — đúng con
#:    số mà một **lượt inference** chịu được. Đo thật trên trình duyệt: một kịch
#:    bản năm câu (253 ký tự) nhập vào ra **đúng một khối**.
#:
#:    Và như thế là hỏng cả tính năng: toàn bộ điểm của Dự án là sửa một đoạn
#:    rồi đọc lại **mình nó**. Một khối chứa cả bài thì mỗi lần sửa một chữ là
#:    đọc lại cả bài — tức đúng thứ Dự án sinh ra để tránh.
#:
#: ⭐ Bài học tổng quát: **1.500 trả lời "một lượt đọc gánh được bao nhiêu",
#:    không trả lời "một đơn vị biên tập nên to bằng nào".** Hai câu hỏi khác
#:    nhau dùng chung một con số là cách một hằng số đi lạc sang chỗ nó không
#:    thuộc về.
#:
#: Đo trên một kịch bản liền mạch 2.000 ký tự / 30 câu:
#:     trần 1500  ->  2 khối, trung bình 999 ký tự   (quá to để sửa)
#:     trần  400  ->  6 khối, trung bình 332 ký tự   ✅ hai tới ba câu
#:     trần  300  ->  8 khối, trung bình 249 ký tự
#:
#: ⚠️ NÓI CHO ĐÚNG: đây là phép **gói tới trần**, không phải phép chia đều. Một
#:    kịch bản ngắn hơn 400 ký tự vẫn ra **một** khối — và như thế là đúng: nó
#:    thật sự là một đoạn. Người viết muốn mịn hơn thì để dòng trống, và nhánh
#:    trên tôn trọng ngay.
TRAN_KHOI_KHI_NHAP = 400


def nhap_van_ban(db, du_an, van_ban: str, *, tran_moi_khoi: int) -> int:
    """Cắt một kịch bản dài thành khối. Trả số khối đã thêm.

    ⭐ TÔN TRỌNG ĐOẠN VĂN CỦA TÁC GIẢ TRƯỚC. Người viết kịch bản đã tự chia ý
       bằng dòng trống; đó là **phân đoạn tốt nhất có thể có**, vì nó do người
       hiểu nội dung làm chứ không do một con số ký tự làm.

       Chỉ khi cả kịch bản là một khối chữ liền — dán từ một trang web, hay gõ
       một mạch — mới cắt theo câu, với cỡ `TRAN_KHOI_KHI_NHAP`.

    ⚠️ Một đoạn văn dài hơn `tran_moi_khoi` vẫn phải cắt: đó là trần kỹ thuật
       của một lượt đọc, không phải một lựa chọn thẩm mỹ.

    ⭐ Cả hai nhánh đều gọi `text_pipeline.chia_doan` — **một** phép cắt, hai
       tham số. Viết một phép cắt thứ hai ở đây là tạo ra hai cách hiểu "một
       đoạn là gì", và chúng sẽ lệch nhau.
    """
    import re

    from . import text_pipeline

    van_ban = (van_ban or "").strip()
    if not van_ban:
        raise LoiDuAn(_t("Chưa có văn bản để nhập."))

    doan_van = [p.strip() for p in re.split(r"\n\s*\n", van_ban) if p.strip()]
    if len(doan_van) > 1:
        doan = []
        for p in doan_van:
            doan.extend(text_pipeline.chia_doan(p, tran_moi_doan=tran_moi_khoi))
    else:
        doan = text_pipeline.chia_doan(van_ban,
                                       tran_moi_doan=TRAN_KHOI_KHI_NHAP)
    con_cho = TRAN_KHOI - len(cac_khoi(db, du_an.id))
    if len(doan) > con_cho:
        raise LoiDuAn(_t(
            "Văn bản này chia ra {n} khối nhưng dự án chỉ còn chỗ cho {c}."
        ).format(n=len(doan), c=max(0, con_cho)))

    for d in doan:
        them_khoi(db, du_an, text=d)
    return len(doan)


# ── sinh tiếng ───────────────────────────────────────────────────────────────

def tach_giong(chon: str) -> tuple:
    """`"m:Adam"` / `"v:vc_…"` / `""` -> `(voice_id, preset)`.

    ⛔ Đúng một trong hai được khác rỗng. `features.chuan_hoa` **từ chối** nếu
       cả hai cùng có — hai nguồn giọng cùng lúc là một yêu cầu không có câu trả
       lời đúng.
    """
    c = (chon or "").strip()
    if c.startswith("v:"):
        return c[2:], ""
    if c.startswith("m:"):
        return "", c[2:]
    return "", ""


def khoi_can_tao(cac: list) -> list:
    """Khối nào cần sinh: chưa có tiếng, hỏng, hoặc văn bản đã đổi sau khi sinh.

    ⛔ Bỏ khối rỗng. Nộp một job cho một khối không có chữ là tiêu một suất GPU
       và một vòng xếp hàng để nhận về một lỗi biết trước.
    """
    return [k for k in cac
            if k.text.strip() and k.trang_thai in ("moi", "loi", "can_tao_lai")]


def gan_ket_qua(db, khoi, job) -> None:
    """Chép kết quả job vào khối. Gọi khi màn hình thấy job đã xong.

    ⚠️ Đây là một BẢN SAO của sự thật (`job.result` mới là gốc). Nó tồn tại để
       màn Dự án không phải tra N job cho mỗi lần dựng trang. Sao chép thì phải
       chấp nhận nó có thể cũ — nên chỗ nào cần chắc chắn thì đọc job.
    """
    kq = (job.result or {}) if job is not None else {}
    if job is None:
        return
    khoi.job_id = str(job.id)
    if job.status == "done" and kq.get("audio_key"):
        khoi.trang_thai = "xong"
        khoi.audio_key = str(kq.get("audio_key") or "")
        try:
            khoi.giay = float(kq.get("duration_s") or 0.0)
        except (TypeError, ValueError):
            khoi.giay = 0.0
        try:
            khoi.credit = int(kq.get("credit_cost") or 0)
        except (TypeError, ValueError):
            khoi.credit = 0
    elif job.status in ("error", "cancelled"):
        khoi.trang_thai = "loi"
    else:
        khoi.trang_thai = "dang_tao"


def tom_tat(cac: list) -> dict:
    xong = [k for k in cac if k.trang_thai == "xong"]
    return {
        "so_khoi": len(cac),
        "xong": len(xong),
        "dang_tao": len([k for k in cac if k.trang_thai == "dang_tao"]),
        "loi": len([k for k in cac if k.trang_thai == "loi"]),
        "can_tao_lai": len([k for k in cac if k.trang_thai == "can_tao_lai"]),
        "giay": round(sum(float(k.giay or 0) for k in xong), 1),
        "credit": sum(int(k.credit or 0) for k in xong),
        "so_ky_tu": sum(len(k.text or "") for k in cac),
        # ⭐ Một giọng cho cả dự án ⇒ xuất được MỘT LƯỢT LIỀN MẠCH. Nhiều giọng
        #    thì không — và đó là câu trả lời cho việc có hiện nút đó hay không.
        "mot_giong": len({(k.giong or "") for k in cac}) <= 1 if cac else True,
    }


def cac_phien_ban(db, owner_id: str, block_id: int, *, tran: int = 10) -> list:
    """Mọi lượt sinh ĐÃ XONG của một khối, mới nhất trước.

    ## Vì sao đọc từ lịch sử job chứ KHÔNG dựng bảng `block_version`

    Ảnh tham chiếu 03 vẽ V1/V2/V3 cho mỗi khối, và `tables_du_an.py` đã từ chối
    một bảng riêng cho chúng — **đúng**, và tệp này giữ nguyên quyết định ấy:

        ⛔ KHÔNG có bảng `block_version`. Lịch sử job đã giữ đủ mọi lượt sinh
           (mỗi lượt là một `Job` có `result`), nên một bảng phiên bản thứ hai
           là một nguồn chân lý thứ hai cho cùng một sự thật — và hai nguồn chân
           lý là một chỗ để chúng lệch nhau.

    ⭐ Nhưng "không có bảng" bị đọc nhầm thành "không có tính năng". Dữ liệu đã
       nằm sẵn: mỗi job của một khối mang `params["block_id"]`. Cái thiếu chỉ là
       một phép đọc — và đó là thứ tệp này bổ sung.

    ## ⚠️ Lọc JSON bằng PYTHON, không bằng SQL

    `Job.params` khai kiểu `JSON` (không phải `JSONB`), và cú pháp truy vấn vào
    trong nó **khác nhau giữa PostgreSQL và SQLite** — production là PostgreSQL
    còn test chạy SQLite, nên một truy vấn JSON viết cho một bên sẽ xanh ở một
    bên và đỏ ở bên kia. Đúng lớp lỗi mà `KHOA_CHINH` trong `tables_du_an.py` đã
    trả giá và ghi lại.

    ⇒ Lọc theo `app_slug` + `owner` ở SQL (có chỉ mục), rồi lọc `block_id` trong
      Python trên một tập ĐÃ BỊ CHẶN. `tran` nhân với một hệ số nhỏ vì một khối
      chỉ chiếm một phần các job gần đây.
    """
    from platform_core import job_history

    cac, _ = job_history.list_owned(db, owner_id, app_slug="ltt_voice",
                                    limit=max(tran, 1) * 20)
    ra = []
    for j in cac:
        p = j.params or {}
        if str(p.get("block_id") or "") != str(block_id):
            continue
        if j.status != "done":
            continue
        kq = j.result or {}
        if not kq.get("audio_key"):
            continue
        ra.append({
            "job_id": str(j.id),
            "giay": float(kq.get("duration_s") or 0.0),
            "credit": int(kq.get("credit_cost") or 0),
            "audio_key": str(kq.get("audio_key") or ""),
            "luc": j.created_at,
        })
        if len(ra) >= tran:
            break
    return ra
