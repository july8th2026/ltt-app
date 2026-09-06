"""ghi_nho.py — bốn phép trên kho ghi nhớ, và cửa quyền của chúng. (H44 B4 bước 2)

## 🔴 Bốn phép, không phải hai — và phép thứ ba mới là lý do tệp này tồn tại

Đọc `mem0/configs/prompts.py::DEFAULT_UPDATE_MEMORY_PROMPT` (06/09):

    Add · Update · Delete · No Change

Phản xạ đầu tiên khi làm ghi nhớ là `them()` + `liet_ke()`. Một kho **chỉ biết
thêm** tích luỹ mâu thuẫn: *"khách thích cà phê"* nằm mãi cạnh *"khách bỏ cà
phê"*, và model càng dùng lâu càng trả lời tệ đi.

⭐ Đó là loại lỗi đắt nhất: **im lặng và tăng dần**. Không có ngày nào nó hỏng
   để ai đó đi sửa; chỉ có một sản phẩm dở đi mà không ai chỉ được ra vì sao.

⇒ `thay()` và `quen()` không phải tiện ích CRUD cho đẹp. Chúng là cơ chế duy
  nhất giữ cho kho **không mâu thuẫn với chính nó**.

## Hai trục quyền, và vì sao chúng KHÔNG được gộp

* `pham_vi` — mẩu này ảnh hưởng tới **lượt nào**.
* `nguon`   — ai viết, tức ai **sửa được**.

Người sửa được mọi mẩu (kể cả mẩu model ghi — đó chính là lời hứa *"bạn sửa
được"*). Model chỉ thay được mẩu **do chính model ghi**, trong **đúng phạm vi
lượt đang chạy**.

## ⛔ Model không được nêu ĐỊA CHỈ. Nó được nêu ĐỘ BỀN, và bên gọi đặt trần.

Đây là bản sắc hơn của luật `thi_hanh(boi_canh=…)` (P05), và phân biệt ấy quan
trọng vì bản thô của nó dẫn tới một tính năng vô dụng:

| model nêu | được không | vì sao |
|---|---|---|
| *"nhớ cho hội thoại `cv_abc`"* | ⛔ **không bao giờ** | đó là **địa chỉ** — kẻ tấn công viết nó vào một tệp đính kèm là ghi được sang chỗ khác |
| *"nhớ cho người dùng `u-9`"* | ⛔ **không bao giờ** | như trên, và nặng hơn |
| *"nhớ lâu dài"* / *"chỉ ở đây"* | ✅ **đề nghị được** | đó là **độ bền**, một lựa chọn sản phẩm, và bên gọi có quyền hạ xuống |

⇒ `ghi_boi_model()` **không** nhận `user_id`/`conv_id`/`pham_vi` từ đối số của
  model — chúng đến từ bối cảnh thi hành. Nó nhận đúng một cờ `lau_dai`, và
  `cho_phep_lau_dai` của bên gọi là **trần** cho cờ ấy.

⭐ Hạ trần thì **nói ra** bằng `pham_vi` của hàng trả về, không im lặng. Một hệ
   bảo model *"đã nhớ"* trong khi nó nhớ hẹp hơn model tưởng sẽ khiến model
   khẳng định với khách một điều không đúng.

## Trần: một khoản thuế lặp lại, không phải một hàng nằm im

Ghi nhớ đi vào ngữ cảnh của **mọi** lượt trong phạm vi. Không trần ⇒ khoản thuế
token ấy tăng mãi và khách trả nó mãi.

⚠️ Nhưng trần đặt **dưới** nhu cầu thường biến thất bại thành **mặc định** (bài
   học đã ghi: *"phanh luôn ăn tệ hơn không có phanh"*). Nên trần ở đây tính
   bằng **ký tự**, không bằng số mẩu, và đủ cho ~25 mẩu ngắn.
"""
from __future__ import annotations

import hashlib
import logging
import re

from sqlalchemy import select

from apps.chatltt.tables import (NGUON, PHAM_VI, TRAN_KY_TU_MOT_BAN,
                                 ChatlttConversation, ChatlttGhiNho)

log = logging.getLogger(__name__)

NGUOI_DUNG = "nguoi_dung"
DU_AN = "du_an"
HOI_THOAI = "hoi_thoai"

NGUOI = "nguoi"
MODEL = "model"

#: Trần ký tự cho MỘT phạm vi. Ba phạm vi ⇒ tối đa 6.000 ký tự tiêm mỗi lượt.
#:
#: ## Con số 2.000 đến từ đâu — nói rõ nó là NEO, không phải phép đo
#:
#: Tôi **không đo được** mặc định của letta (kho `letta-ai/letta` nay chỉ là
#: trang giới thiệu — xem `10_KE_HOACH_B4_GHI_NHO.md` §0.1), nên không viện dẫn
#: nó. Neo tự suy: 2.000 = **4 × `TRAN_KY_TU_MOT_BAN`**, tức ít nhất bốn mẩu dài
#: hết cỡ, hoặc ~25 mẩu ngắn (80 ký tự) — trên hẳn nhu cầu thường (một người
#: dùng nặng sau nhiều tháng có chừng 10–20 mẩu).
#:
#: ⚠️ Phải đo lại sau 20–50 người dùng thật rồi chốt, cùng luật `gia_trich`.
TRAN_KY_TU_MOI_PHAM_VI = 2000

#: Trần cho CẢ khối tiêm. Đây là một **khẳng định phòng thủ**, không phải một
#: cái kéo: trần theo phạm vi ở trên đã chặn trước, nên nếu số này bị chạm thì
#: có một đường ghi nào đó đã đi vòng qua `them()`.
#:
#: ⛔ Chạm trần thì **cắt và ghi log ERROR**, không im lặng. Một khối bị cắt âm
#:    thầm làm model quên một nửa thứ nó vừa được bảo là phải nhớ.
TRAN_KY_TU_TIEM = 3 * TRAN_KY_TU_MOI_PHAM_VI

#: Thứ tự tiêm. Rộng trước, hẹp sau — mẩu hẹp hơn đứng gần câu hỏi hơn.
THU_TU_TIEM = (NGUOI_DUNG, DU_AN, HOI_THOAI)

TIEU_DE = {
    NGUOI_DUNG: "Ghi nho ve nguoi dung nay",
    DU_AN: "Ghi nho trong du an nay",
    HOI_THOAI: "Ghi nho trong hoi thoai nay",
}


class ThamSoSai(ValueError):
    """Phạm vi lạ, nguồn lạ, hoặc mục tiêu không khớp phạm vi."""


class KhongDuocPhep(Exception):
    """Người gọi không sở hữu mục tiêu, hoặc không được sửa mẩu này."""


class KhoDay(Exception):
    """Phạm vi đã chạm trần ký tự.

    ⭐ Ném chứ **không** lặng lẽ đẩy mẩu cũ nhất ra. Một kho tự quên là một kho
       nói dối: người dùng thấy mình đã dạy máy một điều, và điều đó biến mất
       mà không ai báo. Đầy thì nói đầy, rồi để người ấy chọn xoá cái nào.
    """


_KHOANG = re.compile(r"\s+")


def _chuan(noi_dung: str) -> str:
    """Gộp khoảng trắng, cắt hai đầu. **Không** đổi chữ hoa/thường.

    Chữ hoa mang nghĩa (tên riêng), nên bản lưu giữ nguyên; chỉ **khoá chống
    trùng** mới bỏ qua hoa/thường — xem `_bam`.
    """
    return _KHOANG.sub(" ", (noi_dung or "").strip())


def _bam(noi_dung: str) -> str:
    """sha256 của bản đã chuẩn hoá + `casefold`. Khoá chống trùng, không phải
    kiểm toàn vẹn — nên `casefold`: *"Cà Phê"* và *"cà phê"* là **một** mẩu."""
    return hashlib.sha256(_chuan(noi_dung).casefold().encode("utf-8")).hexdigest()


def _kiem_pham_vi(pham_vi: str, muc_tieu_id: str) -> str:
    """Phạm vi hợp lệ, và mục tiêu **khớp** phạm vi. Trả về mục tiêu đã chuẩn hoá.

    🔴 `nguoi_dung` phải đi với mục tiêu **rỗng**, không phải `NULL` và cũng
       không phải một id nào đó. Xem docstring bảng: `NULL` làm `UNIQUE` mất
       tác dụng, còn một id thừa làm mẩu *"áp cho mọi hội thoại"* im lặng thành
       mẩu chỉ áp cho một hội thoại.
    """
    if pham_vi not in PHAM_VI:
        raise ThamSoSai(f"pham vi la: {pham_vi!r}")
    muc_tieu_id = (muc_tieu_id or "").strip()
    if pham_vi == NGUOI_DUNG:
        if muc_tieu_id:
            raise ThamSoSai("pham vi 'nguoi_dung' khong duoc co muc tieu")
        return ""
    if not muc_tieu_id:
        raise ThamSoSai(f"pham vi {pham_vi!r} phai co muc tieu")
    return muc_tieu_id


def _kiem_so_huu(db, *, user_id: str, pham_vi: str, muc_tieu_id: str) -> None:
    """Mục tiêu có thuộc người gọi không.

    ⛔ Kiểm ở **tầng service**, không ở route — cùng luật `kho_tep`: route có thể
       quên, một hàm tự kiểm thì không quên.
    """
    if pham_vi != HOI_THOAI:
        return                      # `du_an` cho B5; `nguoi_dung` khong co muc tieu
    hoi_thoai = db.get(ChatlttConversation, muc_tieu_id)
    if hoi_thoai is None or hoi_thoai.user_id != user_id:
        raise KhongDuocPhep("hoi thoai khong thuoc nguoi goi")


def da_dung(db, *, user_id: str, pham_vi: str, muc_tieu_id: str = "") -> int:
    """Số ký tự đang dùng của một phạm vi."""
    return sum(len(r.noi_dung) for r in liet_ke(
        db, user_id=user_id, pham_vi=pham_vi, muc_tieu_id=muc_tieu_id))


def them(db, *, user_id: str, pham_vi: str, noi_dung: str,
         muc_tieu_id: str = "", nguon: str = NGUOI,
         meta: dict | None = None) -> tuple[ChatlttGhiNho, str]:
    """Thêm một mẩu. Trả `(hàng, "them" | "bo_qua")`.

    ⭐ Trùng thì trả về hàng cũ với `"bo_qua"` — **không** ném. Mượn hành vi
       `apply_memory_operations` của Open WebUI (`status='skipped'`,
       `reason='duplicate'`): ghi lại đúng thứ máy đã biết là một việc **bình
       thường**, không phải một sự cố.
    """
    if nguon not in NGUON:
        raise ThamSoSai(f"nguon la: {nguon!r}")
    muc_tieu_id = _kiem_pham_vi(pham_vi, muc_tieu_id)
    _kiem_so_huu(db, user_id=user_id, pham_vi=pham_vi, muc_tieu_id=muc_tieu_id)

    van = _chuan(noi_dung)
    if not van:
        raise ThamSoSai("noi dung rong")
    if len(van) > TRAN_KY_TU_MOT_BAN:
        raise ThamSoSai(
            f"mau dai {len(van)} ky tu, tran {TRAN_KY_TU_MOT_BAN}")

    bam = _bam(van)
    cu = db.execute(select(ChatlttGhiNho).where(
        ChatlttGhiNho.user_id == user_id,
        ChatlttGhiNho.pham_vi == pham_vi,
        ChatlttGhiNho.muc_tieu_id == muc_tieu_id,
        ChatlttGhiNho.bam == bam,
    )).scalar_one_or_none()
    if cu is not None:
        return cu, "bo_qua"

    dang_dung = da_dung(db, user_id=user_id, pham_vi=pham_vi,
                        muc_tieu_id=muc_tieu_id)
    if dang_dung + len(van) > TRAN_KY_TU_MOI_PHAM_VI:
        raise KhoDay(
            f"pham vi {pham_vi!r} da dung {dang_dung}/{TRAN_KY_TU_MOI_PHAM_VI} "
            f"ky tu; them {len(van)} nua thi vuot")

    mau = ChatlttGhiNho(user_id=user_id, pham_vi=pham_vi,
                        muc_tieu_id=muc_tieu_id, nguon=nguon,
                        noi_dung=van, bam=bam, meta=meta or None)
    db.add(mau)
    db.flush()
    return mau, "them"


def ghi_boi_model(db, *, user_id: str, conv_id: str, noi_dung: str,
                  lau_dai: bool = False, cho_phep_lau_dai: bool = False,
                  meta: dict | None = None) -> tuple[ChatlttGhiNho, str]:
    """Đường ghi DUY NHẤT của model. Xem đầu tệp: địa chỉ do bối cảnh, độ bền
    do model đề nghị và bên gọi đặt trần.

    ⛔ Không có tham số `pham_vi`, `muc_tieu_id`, và **không thể** thêm vào bằng
       cách khai thêm trường trong schema tool: hàm này không nhận `**kwargs`.
       `test_830` chốt bằng **chữ ký hàm đọc qua `inspect`**, không bằng khớp
       chuỗi trong tài liệu.

    ⭐ `nguon` luôn là `MODEL`, cũng không nhận từ đối số. Một mẩu model ghi mà
       khai là người ghi sẽ khoá luôn quyền sửa của chính model (xem `thay`) và
       nói dối người dùng ở giao diện.
    """
    if lau_dai and cho_phep_lau_dai:
        pham_vi, muc_tieu_id = NGUOI_DUNG, ""
    else:
        pham_vi, muc_tieu_id = HOI_THOAI, conv_id
    return them(db, user_id=user_id, pham_vi=pham_vi, muc_tieu_id=muc_tieu_id,
                noi_dung=noi_dung, nguon=MODEL, meta=meta)


def mot(db, *, user_id: str, ghi_nho_id: str) -> ChatlttGhiNho | None:
    """Một mẩu theo id. `None` cho người lạ — **không** ném.

    ⛔ Không phân biệt *"không có"* với *"không phải của bạn"*. Open WebUI cũng
       vậy (`Memory not found` cho cả hai ca), và lý do là một API phân biệt hai
       ca đó cho phép dò id của người khác.
    """
    mau = db.get(ChatlttGhiNho, ghi_nho_id)
    return mau if mau is not None and mau.user_id == user_id else None


def thay(db, *, user_id: str, ghi_nho_id: str, noi_dung: str,
         boi: str = NGUOI) -> ChatlttGhiNho:
    """Thay nội dung một mẩu. `boi=MODEL` chỉ thay được mẩu do model ghi.

    🔴 Đây là phép giải mâu thuẫn (`Update` của mem0). Không có nó thì kho chỉ
       biết lớn lên, và xem đầu tệp về vì sao điều đó tệ dần đi trong im lặng.
    """
    if boi not in NGUON:
        raise ThamSoSai(f"boi la: {boi!r}")
    mau = mot(db, user_id=user_id, ghi_nho_id=ghi_nho_id)
    if mau is None:
        raise KhongDuocPhep("khong tim thay mau ghi nho")
    if boi == MODEL and mau.nguon != MODEL:
        raise KhongDuocPhep("model khong duoc sua mau do nguoi dung ghi")

    van = _chuan(noi_dung)
    if not van:
        raise ThamSoSai("noi dung rong")
    if len(van) > TRAN_KY_TU_MOT_BAN:
        raise ThamSoSai(f"mau dai {len(van)} ky tu, tran {TRAN_KY_TU_MOT_BAN}")

    dang_dung = da_dung(db, user_id=user_id, pham_vi=mau.pham_vi,
                        muc_tieu_id=mau.muc_tieu_id)
    if dang_dung - len(mau.noi_dung) + len(van) > TRAN_KY_TU_MOI_PHAM_VI:
        raise KhoDay(f"thay bang ban dai hon se vuot tran "
                     f"{TRAN_KY_TU_MOI_PHAM_VI} ky tu cua pham vi")

    mau.noi_dung = van
    mau.bam = _bam(van)
    db.flush()
    return mau


def quen(db, *, user_id: str, ghi_nho_id: str) -> bool:
    """Xoá một mẩu. Trả `False` khi không có/không phải của người gọi.

    Trả `bool` chứ không ném vì xoá hai lần (bấm đúp, F5) là ca thường — cùng
    luật `kho_tep.danh_dau`.
    """
    mau = mot(db, user_id=user_id, ghi_nho_id=ghi_nho_id)
    if mau is None:
        log.info("quen bi tu choi: id=%r nguoi=%r", ghi_nho_id, user_id)
        return False
    db.delete(mau)
    db.flush()
    return True


def liet_ke(db, *, user_id: str, pham_vi: str | None = None,
            muc_tieu_id: str | None = None) -> list[ChatlttGhiNho]:
    """Các mẩu của một người. Lọc thêm theo phạm vi/mục tiêu nếu khai.

    ⛔ `user_id` luôn là **điều kiện**, không phải bộ lọc tuỳ chọn.
    """
    q = select(ChatlttGhiNho).where(ChatlttGhiNho.user_id == user_id)
    if pham_vi is not None:
        q = q.where(ChatlttGhiNho.pham_vi == pham_vi)
    if muc_tieu_id is not None:
        q = q.where(ChatlttGhiNho.muc_tieu_id == muc_tieu_id)
    return list(db.execute(q.order_by(ChatlttGhiNho.created_at)).scalars())


def ap_dung(db, *, user_id: str, conv_id: str = "",
            du_an_id: str = "") -> list[ChatlttGhiNho]:
    """Mọi mẩu **áp cho một lượt** — rộng trước, hẹp sau.

    ⭐ Đây là truy vấn nóng nhất của cả tính năng: nó chạy **mỗi lượt**. Chỉ số
       `ix_chatltt_ghi_nho_tiem` tồn tại đúng cho nó.
    """
    ra = liet_ke(db, user_id=user_id, pham_vi=NGUOI_DUNG, muc_tieu_id="")
    if du_an_id:
        ra += liet_ke(db, user_id=user_id, pham_vi=DU_AN, muc_tieu_id=du_an_id)
    if conv_id:
        ra += liet_ke(db, user_id=user_id, pham_vi=HOI_THOAI,
                      muc_tieu_id=conv_id)
    return ra


def khoi_ngu_canh(db, *, user_id: str, conv_id: str = "",
                  du_an_id: str = "") -> str:
    """Khối chữ tiêm vào tin `system`. Rỗng khi không có mẩu nào.

    ⛔ Trả **chuỗi rỗng**, không phải một khối *"(chua co ghi nho)"*. Một khối
       rỗng vẫn tốn token mỗi lượt và vẫn dạy model rằng nó **có** một kho ghi
       nhớ để viện dẫn — rồi nó viện dẫn một kho trống.
    """
    theo: dict = {}
    for mau in ap_dung(db, user_id=user_id, conv_id=conv_id, du_an_id=du_an_id):
        theo.setdefault(mau.pham_vi, []).append(mau)
    if not theo:
        return ""

    dong: list = []
    for pham_vi in THU_TU_TIEM:
        mau_list = theo.get(pham_vi)
        if not mau_list:
            continue
        dong.append(f"[{TIEU_DE[pham_vi]}]")
        dong += [f"- {m.noi_dung}" for m in mau_list]
    khoi = "\n".join(dong)

    if len(khoi) > TRAN_KY_TU_TIEM:
        # Xem hằng số: chạm được tới đây nghĩa là có đường ghi đi vòng qua
        # `them()`. Cắt để lượt vẫn chạy, nhưng ghi ERROR để nó không im.
        log.error("khoi ghi nho %d ky tu, vuot tran %d — co duong ghi bo qua "
                  "`them()`? nguoi=%r conv=%r",
                  len(khoi), TRAN_KY_TU_TIEM, user_id, conv_id)
        khoi = khoi[:TRAN_KY_TU_TIEM]
    return khoi
